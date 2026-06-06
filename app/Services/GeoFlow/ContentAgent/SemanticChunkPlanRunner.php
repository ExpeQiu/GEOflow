<?php

namespace App\Services\GeoFlow\ContentAgent;

use App\Models\AiModel;
use App\Services\GeoFlow\ContentAgent\Dto\ContentAgentResult;
use App\Services\GeoFlow\KnowledgeChunkSyncService;

/** 语义切片规划（internal 路径）。 */
final class SemanticChunkPlanRunner
{
    public function __construct(
        private readonly KnowledgeChunkSyncService $knowledgeChunkSyncService,
    ) {}

    /**
     * @param  array<string, mixed>  $payload
     */
    public function run(array $payload): ContentAgentResult
    {
        $knowledgeBaseId = (int) ($payload['knowledge_base_id'] ?? 0);
        $blocks = is_array($payload['blocks'] ?? null) ? $payload['blocks'] : [];
        if ($knowledgeBaseId <= 0 || $blocks === []) {
            return new ContentAgentResult(false, [], 'knowledge_base_id 或 blocks 无效');
        }

        $chunks = $this->knowledgeChunkSyncService->planSemanticChunksWithAgent($knowledgeBaseId, $blocks);
        if ($chunks === []) {
            return new ContentAgentResult(false, [], '语义切片规划无效');
        }

        return new ContentAgentResult(true, [
            'chunks' => $chunks,
            'knowledge_base_id' => $knowledgeBaseId,
        ]);
    }
}
