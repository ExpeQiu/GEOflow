<?php

namespace App\Jobs;

use App\Models\KnowledgeBase;
use App\Services\GeoFlow\ContentAgent\ContentAgentAsyncSubmittedException;
use App\Services\GeoFlow\KnowledgeChunkSyncService;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Support\Facades\Log;

class SyncKnowledgeChunksJob implements ShouldQueue
{
    use Queueable;

    public int $tries = 2;

    public int $timeout = 600;

    public function __construct(
        public readonly int $knowledgeBaseId,
        public readonly bool $requireRealEmbedding = false,
    ) {
        $this->onQueue('default');
    }

    /**
     * @return array<int, string>
     */
    public function tags(): array
    {
        return ['knowledge_sync', 'kb:'.$this->knowledgeBaseId];
    }

    public function handle(KnowledgeChunkSyncService $chunkSyncService): void
    {
        $knowledgeBase = KnowledgeBase::query()->whereKey($this->knowledgeBaseId)->first(['id', 'content']);
        if (! $knowledgeBase) {
            return;
        }

        $content = trim((string) ($knowledgeBase->content ?? ''));
        if ($content === '') {
            return;
        }

        try {
            $chunkSyncService->sync($this->knowledgeBaseId, $content, $this->requireRealEmbedding);
            Log::info('knowledge_chunks_synced', ['knowledge_base_id' => $this->knowledgeBaseId]);
        } catch (ContentAgentAsyncSubmittedException $exception) {
            Log::channel('content_agent')->info('knowledge_chunks_async_submitted', [
                'knowledge_base_id' => $this->knowledgeBaseId,
                'request_id' => $exception->requestId,
            ]);
        }
    }
}
