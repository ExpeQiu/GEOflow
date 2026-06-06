<?php

namespace App\Services\GeoEval;

use App\Models\Article;
use App\Models\ArticleEvaluation;
use App\Services\GeoEval\Contracts\GeoEvalClientInterface;
use App\Services\GeoEval\Simulation\OptimizationAdvisorService;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

final class ArticleEvaluationService
{
    public function __construct(
        private readonly GeoEvalClientInterface $client,
        private readonly GeoEvalStructuredLogger $logger,
        private readonly OptimizationAdvisorService $optimizationAdvisor,
    ) {}

    public function shouldEvaluateArticle(Article $article): bool
    {
        if (! config('geo_eval.enabled')) {
            return false;
        }

        $rollout = (int) config('geo_eval.gate_rollout_percent');
        if ($rollout >= 100) {
            return true;
        }
        if ($rollout <= 0) {
            return false;
        }

        return ((int) $article->id % 100) < $rollout;
    }

    public function initialEvalStatusForArticle(?int $articleId = null): string
    {
        if (! config('geo_eval.enabled')) {
            return 'skipped';
        }

        if ($articleId !== null && $articleId > 0) {
            $rollout = (int) config('geo_eval.gate_rollout_percent');
            if ($rollout < 100 && ((int) $articleId % 100) >= $rollout) {
                return 'skipped';
            }
        }

        return 'pending_eval';
    }

    public function queueEvaluation(int $articleId, ?int $taskRunId = null, ?int $taskId = null): void
    {
        if (! config('geo_eval.enabled')) {
            return;
        }

        $article = Article::query()->find($articleId);
        if (! $article) {
            return;
        }

        if (! $this->shouldEvaluateArticle($article)) {
            $this->markSkipped($article, 'gate_rollout_or_disabled');

            return;
        }

        Article::query()->whereKey($articleId)->update([
            'eval_status' => 'pending_eval',
            'updated_at' => now(),
        ]);

        \App\Jobs\EvaluateArticleJob::dispatch($articleId, $taskRunId, $taskId);
    }

    public function evaluateArticle(int $articleId, ?int $taskRunId = null, ?int $taskId = null): array
    {
        $requestId = $this->logger->newRequestId();
        $article = Article::query()->find($articleId);
        if (! $article) {
            throw new \RuntimeException('Article not found');
        }

        $idempotencyKey = $this->buildIdempotencyKey($articleId, $taskRunId);

        $this->logger->info('eval_started', [
            'request_id' => $requestId,
            'article_id' => $articleId,
            'task_id' => $taskId,
            'task_run_id' => $taskRunId,
            'eval_status' => 'pending_eval',
        ]);

        if (! config('geo_eval.enabled')) {
            return $this->finalize($article, $idempotencyKey, $taskRunId, $requestId, 'skipped', null, 'eval_disabled');
        }

        if (! $this->shouldEvaluateArticle($article)) {
            return $this->finalize($article, $idempotencyKey, $taskRunId, $requestId, 'skipped', null, 'gate_rollout');
        }

        $article->loadMissing('task');
        $knowledgeBaseId = (int) ($article->task?->knowledge_base_id ?? 0);
        if ($knowledgeBaseId <= 0) {
            return $this->finalize($article, $idempotencyKey, $taskRunId, $requestId, 'skipped', null, 'no_knowledge_base');
        }

        $simPayload = InternalGeoEvalEngine::payloadFromArticle($article);
        $simPayload['noise_ratio'] = (int) config('geo_eval.simulation.noise_ratio');
        $simPayload['mode'] = (string) config('geo_eval.simulation.mode');
        $simPayload['k'] = (int) config('geo_eval.simulation.k');

        try {
            $simulation = $this->client->runSimulation($simPayload, $requestId);

            $simData = is_array($simulation['data'] ?? null) ? $simulation['data'] : [];
            $metrics = is_array($simData['metrics'] ?? null) ? $simData['metrics'] : [];
            $answer = (string) ($simData['answer'] ?? '');

            $audit = $this->client->auditAnswer([
                'question' => $this->buildEvaluationQuestion($article),
                'answer' => $answer,
                'expected_facts' => [],
                'brand_keywords' => config('geo_eval.brand_keywords', []),
            ], $simulation['request_id'] ?? $requestId);

            $auditData = is_array($audit['data'] ?? null) ? $audit['data'] : [];
            $passed = $this->passesGate($metrics, $auditData);

            $recommendations = $this->optimizationAdvisor->advise(
                $this->buildEvaluationQuestion($article),
                $metrics,
                $auditData
            );

            $mergedMetrics = array_merge($metrics, [
                'audit_status' => $auditData['status'] ?? null,
                'audit' => $auditData,
                'recommendations' => $recommendations,
            ]);

            $status = $passed ? 'passed' : 'failed';
            $reason = $passed ? null : $this->buildFailureReason($metrics, $auditData);

            return $this->finalize(
                $article,
                $idempotencyKey,
                $taskRunId,
                $simulation['request_id'] ?? $requestId,
                $status,
                $mergedMetrics,
                $reason,
                array_merge($simData, ['audit' => $auditData])
            );
        } catch (\Throwable $e) {
            $onUnavailable = (string) config('geo_eval.on_unavailable', 'skip');
            $status = $onUnavailable === 'block' ? 'failed' : 'skipped';
            $this->logger->error('eval_unavailable', [
                'request_id' => $requestId,
                'article_id' => $articleId,
                'task_id' => $taskId,
                'eval_status' => $status,
                'message' => $e->getMessage(),
            ]);

            return $this->finalize(
                $article,
                $idempotencyKey,
                $taskRunId,
                $requestId,
                $status,
                null,
                $e->getMessage()
            );
        }
    }

    public function canPublish(Article $article): bool
    {
        if (! config('geo_eval.enabled') || ! config('geo_eval.gate_enabled')) {
            return true;
        }

        $status = (string) ($article->eval_status ?? 'skipped');

        return in_array($status, ['passed', 'skipped'], true);
    }

    /**
     * @param  array<string, mixed>|null  $metrics
     * @param  array<string, mixed>|null  $raw
     * @return array<string, mixed>
     */
    private function finalize(
        Article $article,
        string $idempotencyKey,
        ?int $taskRunId,
        string $requestId,
        string $status,
        ?array $metrics,
        ?string $failureReason,
        ?array $raw = null
    ): array {
        return DB::transaction(function () use ($article, $idempotencyKey, $taskRunId, $requestId, $status, $metrics, $failureReason, $raw): array {
            ArticleEvaluation::query()->updateOrCreate(
                [
                    'article_id' => (int) $article->id,
                    'idempotency_key' => $idempotencyKey,
                ],
                [
                    'task_run_id' => $taskRunId,
                    'eval_type' => 'simulation',
                    'status' => $status,
                    'request_id' => $requestId,
                    'metrics' => $metrics,
                    'failure_reason' => $failureReason,
                    'raw_response' => $raw,
                ]
            );

            $article->eval_status = $status;
            $article->eval_meta = [
                'request_id' => $requestId,
                'failure_reason' => $failureReason,
                'metrics' => $metrics,
                'evaluated_at' => now()->toIso8601String(),
            ];
            $article->save();

            $this->logger->info('eval_finished', [
                'request_id' => $requestId,
                'article_id' => (int) $article->id,
                'task_run_id' => $taskRunId,
                'eval_status' => $status,
                'message' => $failureReason ?? 'ok',
            ]);

            if (in_array($status, ['passed', 'skipped'], true)) {
                \App\Jobs\TryPublishAfterEvalJob::dispatch((int) $article->id)->afterCommit();
            }

            return [
                'article_id' => (int) $article->id,
                'status' => $status,
                'request_id' => $requestId,
                'failure_reason' => $failureReason,
            ];
        });
    }

    private function markSkipped(Article $article, string $reason): void
    {
        $article->eval_status = 'skipped';
        $article->eval_meta = ['reason' => $reason];
        $article->save();
    }

    private function buildIdempotencyKey(int $articleId, ?int $taskRunId): string
    {
        return sha1($articleId.':'.($taskRunId ?? 0).':v1');
    }

    private function buildTargetHtml(Article $article): string
    {
        $title = htmlspecialchars((string) $article->title, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
        $content = (string) $article->content;

        return '<article><h1>'.$title.'</h1><div>'.$content.'</div></article>';
    }

    private function buildEvaluationQuestion(Article $article): string
    {
        $keyword = trim((string) ($article->original_keyword ?? ''));

        return $keyword !== ''
            ? '请基于以下内容回答：'.$keyword
            : '请总结并评价以下文章的核心事实与品牌表达：'.(string) $article->title;
    }

    /**
     * @param  array<string, mixed>  $metrics
     * @param  array<string, mixed>  $auditData
     */
    private function passesGate(array $metrics, array $auditData): bool
    {
        $found = (bool) ($metrics['found'] ?? false);
        $rank = (int) ($metrics['rank'] ?? 99);
        $minRank = (int) config('geo_eval.simulation.min_rank', 1);

        if (! $found || $rank > $minRank) {
            return false;
        }

        $auditStatus = (string) ($auditData['status'] ?? 'pass');

        return ! in_array($auditStatus, ['fail', 'failed', 'reject'], true);
    }

    /**
     * @param  array<string, mixed>  $metrics
     * @param  array<string, mixed>  $auditData
     */
    private function buildFailureReason(array $metrics, array $auditData): string
    {
        $parts = [];
        if (! ($metrics['found'] ?? false)) {
            $parts[] = 'simulation_not_found';
        }
        $rank = (int) ($metrics['rank'] ?? 99);
        $minRank = (int) config('geo_eval.simulation.min_rank', 1);
        if ($rank > $minRank) {
            $parts[] = 'rank_below_threshold:'.$rank;
        }
        $auditStatus = (string) ($auditData['status'] ?? '');
        if (in_array($auditStatus, ['fail', 'failed', 'reject'], true)) {
            $parts[] = 'audit_'.$auditStatus;
        }

        return $parts !== [] ? implode(';', $parts) : 'eval_failed';
    }
}
