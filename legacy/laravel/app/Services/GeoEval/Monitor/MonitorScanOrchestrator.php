<?php

namespace App\Services\GeoEval\Monitor;

use App\Models\GeoMonitorQuestion;
use App\Models\GeoMonitorResult;
use App\Models\GeoMonitorRun;
use App\Services\GeoEval\Contracts\GeoEvalClientInterface;
use App\Services\GeoEval\GeoEvalStructuredLogger;
use App\Services\GeoEval\Simulation\OptimizationAdvisorService;
use Illuminate\Support\Str;

final class MonitorScanOrchestrator
{
    public function __construct(
        private readonly MonitorQuestionService $questionService,
        private readonly GeoEvalClientInterface $client,
        private readonly OptimizationAdvisorService $advisor,
        private readonly MonitorAiProbeService $aiProbeService,
        private readonly GeoEvalStructuredLogger $logger,
    ) {}

    /**
     * @return array{run_id: int, scanned: int, skipped: int, failed: int}
     */
    public function run(string $runType = 'scheduled', bool $async = false): array
    {
        if ($async) {
            \App\Jobs\RunMonitorScanJob::dispatch($runType);

            return ['run_id' => 0, 'scanned' => 0, 'skipped' => 0, 'failed' => 0, 'queued' => true];
        }

        $batchSize = (int) config('geo_eval.monitor.scan_batch_size', 50);
        $questions = $this->questionService->listActive($batchSize);

        $run = GeoMonitorRun::query()->create([
            'run_type' => $runType,
            'status' => 'running',
            'question_count' => $questions->count(),
            'started_at' => now(),
        ]);

        $scanned = 0;
        $skipped = 0;
        $failed = 0;
        $aiProbes = 0;

        foreach ($questions as $question) {
            try {
                $result = $this->scanQuestion($question, (int) $run->id);
                if ($result === null) {
                    $skipped++;
                } else {
                    $scanned++;
                }
                $aiProbes += count($this->aiProbeService->probeQuestion($question, (int) $run->id));
            } catch (\Throwable $e) {
                $failed++;
                $this->logger->error('monitor_scan_question_failed', [
                    'request_id' => (string) Str::uuid(),
                    'message' => $e->getMessage(),
                    'context' => ['question_id' => (int) $question->id],
                ]);
            }
        }

        $run->update([
            'status' => 'completed',
            'finished_at' => now(),
            'meta' => ['scanned' => $scanned, 'skipped' => $skipped, 'failed' => $failed, 'ai_probes' => $aiProbes],
        ]);

        $this->logger->info('monitor_scan_completed', [
            'request_id' => (string) Str::uuid(),
            'message' => "run={$run->id}",
            'context' => ['scanned' => $scanned, 'skipped' => $skipped, 'failed' => $failed],
        ]);

        return [
            'run_id' => (int) $run->id,
            'scanned' => $scanned,
            'skipped' => $skipped,
            'failed' => $failed,
        ];
    }

    /**
     * @return GeoMonitorResult|null
     */
    public function scanQuestion(GeoMonitorQuestion $question, int $runId): ?GeoMonitorResult
    {
        $target = $this->questionService->resolveTarget($question);
        $knowledgeBaseId = (int) ($target['knowledge_base_id'] ?? 0);
        $targetHtml = (string) ($target['target_html'] ?? '');

        if ($knowledgeBaseId <= 0 || $targetHtml === '') {
            return null;
        }

        $requestId = $this->logger->newRequestId();
        $questionText = (string) $question->question_text;

        $simulation = $this->client->runSimulation([
            'knowledge_base_id' => $knowledgeBaseId,
            'question' => $questionText,
            'target_html' => $targetHtml,
        ], $requestId);

        $simData = is_array($simulation['data'] ?? null) ? $simulation['data'] : [];
        $metrics = is_array($simData['metrics'] ?? null) ? $simData['metrics'] : [];
        $answer = (string) ($simData['answer'] ?? '');

        $audit = $this->client->auditAnswer([
            'question' => $questionText,
            'answer' => $answer,
            'brand_keywords' => config('geo_eval.brand_keywords', []),
        ], $simulation['request_id'] ?? $requestId);

        $auditData = is_array($audit['data'] ?? null) ? $audit['data'] : [];
        $recommendations = $this->advisor->advise($questionText, $metrics, $auditData);

        return GeoMonitorResult::query()->create([
            'question_id' => (int) $question->id,
            'run_id' => $runId,
            'article_id' => $target['article_id'],
            'rank' => (int) ($metrics['rank'] ?? 99),
            'found' => (bool) ($metrics['found'] ?? false),
            'target_score' => (float) ($metrics['target_score'] ?? 0),
            'top_k' => (int) ($metrics['top_k'] ?? 5),
            'audit_status' => (string) ($auditData['status'] ?? ''),
            'tech_accuracy' => (float) ($auditData['tech_accuracy'] ?? 0),
            'brand_consistency' => (float) ($auditData['brand_consistency'] ?? 0),
            'snapshot_json' => [
                'top_scores' => $metrics['top_scores'] ?? [],
                'doc_count' => $metrics['doc_count'] ?? 0,
            ],
            'recommendations' => $recommendations,
        ]);
    }
}
