<?php

namespace App\Services\GeoFlow;

use App\Models\Prompt;
use App\Models\Task;
use App\Services\GeoEval\InsightTemplateService;
use App\Services\GeoFlow\ContentAgent\AiModelRuntimeBuilder;
use App\Support\GeoFlow\KnowledgeEvidenceFormatter;

/** 组装 content_pipeline 侧车 payload（双 RAG + 记忆快照）。 */
final class ContentPipelineContextService
{
    public function __construct(
        private readonly KnowledgeRetrievalService $knowledgeRetrievalService,
        private readonly KnowledgeConfigService $knowledgeConfigService,
        private readonly InsightTemplateService $insightTemplateService,
        private readonly ContentAgentMemoryService $memoryService,
        private readonly AiModelRuntimeBuilder $aiModelRuntimeBuilder,
    ) {}

    /**
     * @param  array<string, mixed>  $generationContext
     * @return array<string, mixed>
     */
    public function buildPayload(
        Task $task,
        string $title,
        string $keyword,
        ?Prompt $prompt,
        string $styleAppendix,
        ?int $taskRunId,
        array $generationContext,
    ): array {
        $primaryModel = $this->resolvePrimaryModel($task);
        $promptContent = trim((string) ($prompt?->content ?? ''));
        if ($styleAppendix !== '') {
            $promptContent = trim($promptContent."\n\n".$styleAppendix);
        }

        $researchQuery = trim($title."\n".$keyword);
        $brandQuery = trim('品牌调性 产品卖点 '.$keyword.' '.$title);

        $kbId = (int) ($task->knowledge_base_id ?? 0);
        $retrievalLimit = $this->knowledgeConfigService->retrievalLimit();
        $retrievalMaxChars = $this->knowledgeConfigService->retrievalMaxChars();
        $candidateLimit = max($retrievalLimit * 4, 16);

        $researchContext = '';
        $researchEvidence = [];
        $brandEvidence = [];

        if ($kbId > 0) {
            $researchRows = $this->knowledgeRetrievalService->retrieveEvidence($kbId, $researchQuery, $candidateLimit);
            $researchContext = $this->knowledgeRetrievalService->retrieveContext(
                $kbId,
                $researchQuery,
                $retrievalLimit,
                $retrievalMaxChars
            );
            $researchEvidence = KnowledgeEvidenceFormatter::fromRetrievedRows($researchRows);

            $brandRows = $this->knowledgeRetrievalService->retrieveEvidence($kbId, $brandQuery, $candidateLimit);
            $brandEvidence = KnowledgeEvidenceFormatter::fromRetrievedRows($brandRows);
        }

        $userRequest = trim(implode("\n", array_filter([
            '标题：'.$title,
            $keyword !== '' ? '关键词：'.$keyword : '',
            $promptContent !== '' ? '任务说明：'.$promptContent : '',
        ])));

        $mergedEvidence = $this->mergeEvidence($researchEvidence, $brandEvidence);

        return [
            'user_request' => $userRequest,
            'prompt' => $userRequest,
            'research_pack' => [
                'query' => $researchQuery,
                'evidence' => $researchEvidence,
                'context_text' => $researchContext,
            ],
            'brand_pack' => [
                'query' => $brandQuery,
                'style_guide' => $styleAppendix,
                'evidence' => $brandEvidence,
            ],
            'memory_snapshot' => $this->memoryService->snapshotForTask((int) $task->id),
            'evidence' => $mergedEvidence,
            'style_guide' => $styleAppendix,
            'ai_model_id' => (int) $primaryModel->id,
            'model' => $this->aiModelRuntimeBuilder->buildForExternalPayload($primaryModel),
            'generation_context' => array_merge($generationContext, [
                'knowledge_context' => $researchContext,
                'pipeline_mode' => (string) ($task->content_pipeline_mode ?? 'pipeline'),
                'content_workflow' => 'content_pipeline',
            ]),
            'correlation' => $taskRunId !== null && $taskRunId > 0
                ? ['type' => 'task_run', 'id' => $taskRunId]
                : null,
        ];
    }

    /**
     * @param  list<array{id:string,content:string}>  $research
     * @param  list<array{id:string,content:string}>  $brand
     * @return list<array{id:string,content:string}>
     */
    private function mergeEvidence(array $research, array $brand): array
    {
        $merged = [];
        $seen = [];
        $index = 1;

        foreach (array_merge($research, $brand) as $item) {
            $content = trim((string) ($item['content'] ?? ''));
            if ($content === '' || isset($seen[$content])) {
                continue;
            }
            $seen[$content] = true;
            $merged[] = ['id' => 'K'.$index, 'content' => $content];
            $index++;
        }

        return $merged;
    }

    private function resolvePrimaryModel(Task $task): \App\Models\AiModel
    {
        $modelId = (int) ($task->ai_model_id ?? 0);
        if ($modelId <= 0) {
            throw new \RuntimeException('未指定 AI 模型');
        }

        $model = \App\Models\AiModel::query()
            ->whereKey($modelId)
            ->where('status', 'active')
            ->first();

        if (! $model) {
            throw new \RuntimeException('AI 模型不可用');
        }

        return $model;
    }
}
