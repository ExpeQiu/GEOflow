<?php

namespace App\Services\GeoFlow\ContentAgent;

use App\Ai\Agents\MarkdownContentWriterAgent;
use App\Models\AiModel;
use App\Services\GeoFlow\ContentAgent\Dto\ContentAgentDispatchResult;
use App\Services\GeoFlow\ContentAgent\Dto\ContentAgentResult;
use App\Services\GeoFlow\Contracts\ContentAgentClientInterface;
use App\Support\GeoFlow\OpenAiRuntimeProvider;
use Illuminate\Support\Facades\DB;
use RuntimeException;
use Throwable;

/** 进程内 Content Agent：Laravel AI SDK 同步执行。 */
final class InternalContentAgent implements ContentAgentClientInterface
{
    use DispatchesContentAgentWorkflows;

    public function __construct(
        private readonly AiModelRuntimeBuilder $runtimeBuilder,
        private readonly UrlImportAnalysisRunner $urlImportAnalysisRunner,
        private readonly SemanticChunkPlanRunner $semanticChunkPlanRunner,
    ) {}

    public function generateContent(array $payload): ContentAgentResult
    {
        $prompt = trim((string) ($payload['prompt'] ?? ''));
        if ($prompt === '') {
            return new ContentAgentResult(false, [], 'prompt 不能为空');
        }

        $model = $this->resolveModel($payload);
        $runtime = $this->runtimeBuilder->buildFromModel($model);
        $systemPrompt = trim((string) ($payload['system_prompt'] ?? '你是专业中文写作助手，请输出高质量、可发布的 Markdown 文章。'));

        try {
            $agent = new MarkdownContentWriterAgent($systemPrompt);
            $response = $agent->prompt($prompt, [], $runtime['provider'], $runtime['model_id']);
            $content = OpenAiRuntimeProvider::normalizeGeneratedText((string) ($response->text ?? ''));
            if ($content === '') {
                return new ContentAgentResult(false, [], 'AI 返回空内容');
            }

            $this->recordModelUsage((int) $model->id);

            return new ContentAgentResult(true, [
                'content' => $content,
                'citations' => is_array($payload['citations'] ?? null) ? $payload['citations'] : [],
            ], null, [
                'model_id' => (int) $model->id,
                'model_name' => (string) $model->name,
                'backend' => 'internal',
            ]);
        } catch (Throwable $exception) {
            return new ContentAgentResult(false, [], OpenAiRuntimeProvider::normalizeApiException(
                $exception,
                (string) ($runtime['provider_url'] ?? '')
            ));
        }
    }

    public function generateUrlImportAnalysis(array $payload): ContentAgentResult
    {
        return $this->urlImportAnalysisRunner->run($payload);
    }

    public function generateSemanticChunkPlan(array $payload): ContentAgentResult
    {
        return $this->semanticChunkPlanRunner->run($payload);
    }

    public function submitContentWorkflow(array $payload): string
    {
        $this->unsupportedAsync('content');
    }

    public function submitUrlImportWorkflow(array $payload): string
    {
        $this->unsupportedAsync('url_import');
    }

    public function submitSemanticChunkWorkflow(array $payload): string
    {
        $this->unsupportedAsync('semantic_chunk');
    }

    public function dispatchContentGeneration(array $payload): ContentAgentDispatchResult
    {
        return new ContentAgentDispatchResult('sync', null, $this->generateContent($payload));
    }

    public function dispatchUrlImportAnalysis(array $payload): ContentAgentDispatchResult
    {
        return new ContentAgentDispatchResult('sync', null, $this->generateUrlImportAnalysis($payload));
    }

    public function dispatchSemanticChunkPlan(array $payload): ContentAgentDispatchResult
    {
        return new ContentAgentDispatchResult('sync', null, $this->generateSemanticChunkPlan($payload));
    }

    public function healthCheck(): bool
    {
        return true;
    }

    public function supportedBackend(): string
    {
        return 'internal';
    }

    protected function usesExternalBackend(): bool
    {
        return false;
    }

    protected function externalClient(): ContentAgentClientInterface
    {
        return $this;
    }

    protected function internalClient(): ContentAgentClientInterface
    {
        return $this;
    }

    /**
     * @param  array<string, mixed>  $payload
     */
    private function resolveModel(array $payload): AiModel
    {
        $modelId = (int) ($payload['ai_model_id'] ?? $payload['model']['id'] ?? 0);
        if ($modelId <= 0) {
            throw new RuntimeException('未指定 AI 模型');
        }

        $model = AiModel::query()
            ->whereKey($modelId)
            ->where('status', 'active')
            ->where(function ($query): void {
                $query->whereNull('model_type')
                    ->orWhere('model_type', '')
                    ->orWhere('model_type', 'chat');
            })
            ->first();

        if (! $model) {
            throw new RuntimeException('AI 模型不可用');
        }

        return $model;
    }

    private function recordModelUsage(int $modelId): void
    {
        AiModel::query()->whereKey($modelId)->update([
            'used_today' => DB::raw('COALESCE(used_today,0)+1'),
            'total_used' => DB::raw('COALESCE(total_used,0)+1'),
            'updated_at' => now(),
        ]);
    }
}
