<?php

namespace App\Services\GeoEval\Monitor;

use App\Models\AiModel;
use App\Models\GeoMonitorAiProbeResult;
use App\Models\GeoMonitorPlatformConfig;
use App\Models\GeoMonitorQuestion;
use App\Services\GeoEval\GeoEvalStructuredLogger;
use App\Support\GeoFlow\ApiKeyCrypto;
use App\Support\GeoFlow\OpenAiRuntimeProvider;
use Illuminate\Support\Collection;

use function Laravel\Ai\agent;

final class MonitorAiProbeService
{
    public function __construct(
        private readonly MonitorPlatformConfigService $platformConfigService,
        private readonly BrandRankingExtractor $brandRankingExtractor,
        private readonly MonitorSettingsService $monitorSettingsService,
        private readonly GeoEvalStructuredLogger $logger,
        private readonly ApiKeyCrypto $apiKeyCrypto,
    ) {}

    /**
     * @return list<GeoMonitorAiProbeResult>
     */
    public function probeQuestion(GeoMonitorQuestion $question, ?int $runId = null): array
    {
        $platforms = $this->platformConfigService->enabledPlatforms();
        if ($platforms->isEmpty()) {
            return [];
        }

        $targets = $this->monitorSettingsService->allBrandTargets($question);
        $results = [];

        foreach ($platforms as $platform) {
            $results[] = $this->probeOnPlatform($question, $platform, $runId, $targets);
        }

        return $results;
    }

    /**
     * @param  list<string>  $targetBrands
     */
    private function probeOnPlatform(
        GeoMonitorQuestion $question,
        GeoMonitorPlatformConfig $platform,
        ?int $runId,
        array $targetBrands
    ): GeoMonitorAiProbeResult {
        $model = AiModel::query()->find((int) $platform->ai_model_id);
        $label = (string) ($platform->label !== '' ? $platform->label : ($model?->name ?? 'platform'));

        if (! $model || (string) ($model->status ?? '') !== 'active') {
            return GeoMonitorAiProbeResult::query()->create([
                'question_id' => (int) $question->id,
                'run_id' => $runId,
                'ai_model_id' => (int) $platform->ai_model_id,
                'platform_label' => $label,
                'status' => 'skipped',
                'error_message' => 'model_inactive',
            ]);
        }

        try {
            $responseText = $this->askPlatform($model, (string) $question->question_text);
            $extracted = $this->brandRankingExtractor->extract($responseText, $targetBrands);

            $this->logger->info('monitor_ai_probe_completed', [
                'request_id' => $this->logger->newRequestId(),
                'message' => "q={$question->id} platform={$label}",
                'context' => [
                    'brand_rank' => $extracted['brand_rank'],
                    'brand_mentioned' => $extracted['brand_mentioned'],
                ],
            ]);

            return GeoMonitorAiProbeResult::query()->create([
                'question_id' => (int) $question->id,
                'run_id' => $runId,
                'ai_model_id' => (int) $model->id,
                'platform_label' => $label,
                'response_text' => mb_substr($responseText, 0, 4000, 'UTF-8'),
                'brand_rank' => (int) $extracted['brand_rank'],
                'brand_mentioned' => (bool) $extracted['brand_mentioned'],
                'brands_ordered' => $extracted['brands_ordered'],
                'metrics_json' => [
                    'mention_count' => $extracted['mention_count'],
                    'brands_count' => count($extracted['brands_ordered']),
                ],
                'status' => 'completed',
            ]);
        } catch (\Throwable $e) {
            $this->logger->error('monitor_ai_probe_failed', [
                'request_id' => $this->logger->newRequestId(),
                'message' => $e->getMessage(),
                'context' => ['question_id' => (int) $question->id, 'platform' => $label],
            ]);

            return GeoMonitorAiProbeResult::query()->create([
                'question_id' => (int) $question->id,
                'run_id' => $runId,
                'ai_model_id' => (int) $model->id,
                'platform_label' => $label,
                'status' => 'failed',
                'error_message' => mb_substr($e->getMessage(), 0, 500),
            ]);
        }
    }

    private function askPlatform(AiModel $model, string $question): string
    {
        if ((string) config('geo_eval.monitor.ai_probe_mode', 'live') === 'mock') {
            return "1. 竞品A\n2. 目标品牌\n3. 竞品B\n\n关于「{$question}」的简要说明。";
        }

        $providerUrl = OpenAiRuntimeProvider::resolveChatBaseUrl((string) ($model->api_url ?? ''));
        $apiKey = $this->apiKeyCrypto->decrypt((string) ($model->getRawOriginal('api_key') ?? ''));
        $modelId = trim((string) ($model->model_id ?? ''));

        if ($providerUrl === '' || $apiKey === '' || $modelId === '') {
            throw new \RuntimeException('incomplete_model_config');
        }

        $driver = OpenAiRuntimeProvider::resolveChatDriver($providerUrl, $modelId);
        $providerName = OpenAiRuntimeProvider::registerProvider(
            'monitor_probe_'.$model->id,
            $driver,
            $providerUrl,
            $apiKey
        );

        $systemPrompt = '你是客观中立的行业顾问。请直接回答用户问题；若涉及品牌或产品推荐，请用编号列表给出推荐顺序并简述理由。';
        $response = agent($systemPrompt)->prompt($question, [], $providerName, $modelId);

        return trim((string) ($response->text ?? ''));
    }

    /**
     * @param  Collection<int, GeoMonitorQuestion>  $questions
     * @return int 探测条数
     */
    public function probeBatch(Collection $questions, ?int $runId = null): int
    {
        $count = 0;
        foreach ($questions as $question) {
            $count += count($this->probeQuestion($question, $runId));
        }

        return $count;
    }
}
