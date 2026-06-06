<?php

namespace App\Services\GeoFlow\ContentAgent;

use App\Models\ContentAgentRequest;
use App\Models\TaskRun;
use App\Models\UrlImportJob;
use App\Models\Task;
use App\Services\GeoFlow\ContentAgentMemoryService;
use App\Services\GeoFlow\ContentPipelinePublishBridge;
use App\Services\GeoFlow\JobQueueService;
use App\Services\GeoFlow\KnowledgeChunkSyncService;
use App\Services\GeoFlow\WorkerArticlePersistenceService;
use App\Services\GeoFlow\WorkerExecutionService;
use Illuminate\Support\Facades\Log;
use RuntimeException;

/** Content Agent 回调分发：按 workflow_type 落库。 */
final class ContentAgentCallbackHandler
{
    public function __construct(
        private readonly ContentAgentRequestRepository $requestRepository,
        private readonly WorkerArticlePersistenceService $articlePersistenceService,
        private readonly WorkerExecutionService $workerExecutionService,
        private readonly KnowledgeChunkSyncService $knowledgeChunkSyncService,
        private readonly JobQueueService $jobQueueService,
        private readonly ContentAgentMemoryService $memoryService,
        private readonly ContentPipelinePublishBridge $publishBridge,
    ) {}

    /**
     * @param  array<string, mixed>  $payload
     * @return array<string, mixed>
     */
    public function handle(array $payload): array
    {
        $requestId = trim((string) ($payload['request_id'] ?? ''));
        $workflowType = trim((string) ($payload['workflow_type'] ?? ''));
        $status = trim((string) ($payload['status'] ?? ''));
        $engine = trim((string) ($payload['engine'] ?? ''));

        if ($requestId === '' || $workflowType === '') {
            throw new RuntimeException('invalid_callback_payload');
        }

        $record = $this->requestRepository->findByRequestId($requestId);
        if (! $record) {
            throw new RuntimeException('unknown_request_id');
        }

        if ($record->status === 'completed') {
            return ['request_id' => $requestId, 'status' => 'already_completed'];
        }

        if ($status !== 'success') {
            $error = trim((string) ($payload['error'] ?? 'workflow_failed'));
            $this->requestRepository->markFailed($requestId, $error);
            $this->failCorrelation($record, $error);

            return ['request_id' => $requestId, 'status' => 'failed'];
        }

        $result = is_array($payload['result'] ?? null) ? $payload['result'] : [];
        $this->requestRepository->markCompleted($requestId, $result, $engine !== '' ? $engine : null);

        return match ($workflowType) {
            'content' => $this->handleContent($record, $result),
            'content_pipeline' => $this->handleContentPipeline($record, $result),
            'url_import' => $this->handleUrlImport($record, $result),
            'semantic_chunk' => $this->handleSemanticChunk($record, $result),
            default => throw new RuntimeException('unsupported_workflow_type'),
        };
    }

    /**
     * @param  array<string, mixed>  $result
     * @return array<string, mixed>
     */
    private function handleContent(ContentAgentRequest $record, array $result): array
    {
        $storedPayload = json_decode((string) ($record->payload_json ?? ''), true);
        if (! is_array($storedPayload)) {
            throw new RuntimeException('invalid_stored_payload');
        }

        $storedPayload['content'] = (string) ($result['content'] ?? '');
        if ($storedPayload['content'] === '') {
            throw new RuntimeException('empty_content');
        }

        $persisted = $this->workerExecutionService->completeContentGenerationFromCallback($storedPayload, $record);

        return [
            'request_id' => $record->request_id,
            'status' => 'completed',
            'article_id' => $persisted['article_id'] ?? null,
        ];
    }

    /**
     * @param  array<string, mixed>  $result
     * @return array<string, mixed>
     */
    private function handleContentPipeline(ContentAgentRequest $record, array $result): array
    {
        $storedPayload = json_decode((string) ($record->payload_json ?? ''), true);
        if (! is_array($storedPayload)) {
            throw new RuntimeException('invalid_stored_payload');
        }

        $storedPayload['content'] = (string) ($result['content'] ?? '');
        if ($storedPayload['content'] === '') {
            throw new RuntimeException('empty_content');
        }

        $contextData = is_array($storedPayload['generation_context'] ?? null) ? $storedPayload['generation_context'] : [];
        $contextData['generation_meta'] = array_merge(
            is_array($contextData['generation_meta'] ?? null) ? $contextData['generation_meta'] : [],
            [
                'pipeline_mode' => (string) ($result['pipeline_mode'] ?? ''),
                'cross_validation' => is_array($result['cross_validation'] ?? null) ? $result['cross_validation'] : [],
                'compliance' => is_array($result['compliance'] ?? null) ? $result['compliance'] : [],
                'content_workflow' => 'content_pipeline',
            ]
        );
        $storedPayload['generation_context'] = $contextData;

        $persisted = $this->workerExecutionService->completeContentGenerationFromCallback($storedPayload, $record);

        $taskId = (int) ($contextData['task_id'] ?? 0);
        if ($taskId > 0 && is_array($result['memory_patch'] ?? null)) {
            $this->memoryService->applyPatch($taskId, $result['memory_patch']);
        }

        $articleId = (int) ($persisted['article_id'] ?? 0);
        if ($taskId > 0 && $articleId > 0) {
            $task = Task::query()->find($taskId);
            if ($task) {
                $this->publishBridge->tryPublishAfterPipeline($articleId, $task);
            }
        }

        Log::channel('content_agent')->info('content_pipeline.callback_completed', [
            'request_id' => $record->request_id,
            'article_id' => $articleId,
            'pipeline_mode' => (string) ($result['pipeline_mode'] ?? ''),
        ]);

        return [
            'request_id' => $record->request_id,
            'status' => 'completed',
            'article_id' => $articleId > 0 ? $articleId : null,
        ];
    }

    /**
     * @param  array<string, mixed>  $result
     * @return array<string, mixed>
     */
    private function handleUrlImport(ContentAgentRequest $record, array $result): array
    {
        $job = UrlImportJob::query()->whereKey((int) $record->correlation_id)->first();
        if (! $job) {
            throw new RuntimeException('url_import_job_not_found');
        }

        $storedPayload = json_decode((string) ($record->payload_json ?? ''), true);
        $jobContext = is_array($storedPayload) && is_array($storedPayload['job_context'] ?? null)
            ? $storedPayload['job_context']
            : [];

        $fullResult = [
            'source' => is_array($jobContext['source'] ?? null) ? $jobContext['source'] : [],
            'page' => is_array($jobContext['page'] ?? null) ? $jobContext['page'] : [],
            'analysis' => $result,
            'import' => [
                'status' => 'preview',
                'summary' => null,
            ],
        ];

        $job->result_json = json_encode($fullResult, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_INVALID_UTF8_SUBSTITUTE);
        $job->status = 'completed';
        $job->current_step = 'completed';
        $job->progress_percent = 100;
        $job->page_title = (string) data_get($fullResult, 'page.title', $job->page_title);
        $job->finished_at = now();
        $job->save();

        return ['request_id' => $record->request_id, 'status' => 'completed', 'job_id' => (int) $job->id];
    }

    /**
     * @param  array<string, mixed>  $result
     * @return array<string, mixed>
     */
    private function handleSemanticChunk(ContentAgentRequest $record, array $result): array
    {
        $knowledgeBaseId = (int) ($result['knowledge_base_id'] ?? $record->correlation_id ?? 0);
        $chunks = is_array($result['chunks'] ?? null) ? $result['chunks'] : [];
        $storedPayload = json_decode((string) ($record->payload_json ?? ''), true);
        $requireRealEmbedding = is_array($storedPayload) && (bool) ($storedPayload['require_real_embedding'] ?? false);

        if ($knowledgeBaseId <= 0 || $chunks === []) {
            throw new RuntimeException('invalid_semantic_chunk_result');
        }

        try {
            $count = $this->knowledgeChunkSyncService->syncFromPlannedChunks($knowledgeBaseId, $chunks, $requireRealEmbedding);
        } catch (\Throwable $exception) {
            if ($requireRealEmbedding) {
                throw $exception;
            }
            throw $exception;
        }

        return [
            'request_id' => $record->request_id,
            'status' => 'completed',
            'chunk_count' => $count,
        ];
    }

    private function failCorrelation(ContentAgentRequest $record, string $error): void
    {
        if ($record->correlation_type === 'task_run' && (int) $record->correlation_id > 0) {
            $run = TaskRun::query()->whereKey((int) $record->correlation_id)->first(['id', 'task_id']);
            if ($run) {
                $this->jobQueueService->failJob((int) $run->id, (int) $run->task_id, $error, 0);
            }
        }

        if ($record->correlation_type === 'url_import_job' && (int) $record->correlation_id > 0) {
            UrlImportJob::query()->whereKey((int) $record->correlation_id)->update([
                'status' => 'failed',
                'current_step' => 'failed',
                'error_message' => $error,
                'finished_at' => now(),
            ]);
        }

        if ($record->correlation_type === 'knowledge_base' && (int) $record->correlation_id > 0) {
            Log::channel('content_agent')->warning('content_agent.knowledge_chunk_failed', [
                'request_id' => $record->request_id,
                'knowledge_base_id' => (int) $record->correlation_id,
                'workflow_type' => $record->workflow_type,
                'error' => $error,
            ]);
        }

        Log::channel('content_agent')->warning('content_agent.callback_failed', [
            'request_id' => $record->request_id,
            'workflow_type' => $record->workflow_type,
            'correlation_type' => $record->correlation_type,
            'correlation_id' => $record->correlation_id,
            'error' => $error,
        ]);
    }
}
