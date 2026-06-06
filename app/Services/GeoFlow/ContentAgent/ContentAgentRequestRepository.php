<?php

namespace App\Services\GeoFlow\ContentAgent;

use App\Models\ContentAgentRequest;
use Illuminate\Support\Str;

final class ContentAgentRequestRepository
{
    /**
     * @param  array<string, mixed>  $payload
     */
    public function createPending(
        string $workflowType,
        string $backend,
        array $payload,
        ?string $correlationType = null,
        ?int $correlationId = null,
        ?string $requestId = null,
    ): ContentAgentRequest {
        $requestId = $requestId ?: (string) Str::uuid();

        return ContentAgentRequest::query()->create([
            'request_id' => $requestId,
            'workflow_type' => $workflowType,
            'backend' => $backend,
            'status' => 'pending',
            'correlation_type' => $correlationType,
            'correlation_id' => $correlationId,
            'contract_version' => (string) config('geoflow.content_agent.contract_version', '1.0'),
            'payload_json' => json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
            'submitted_at' => now(),
        ]);
    }

    public function markRunning(string $requestId): void
    {
        ContentAgentRequest::query()
            ->where('request_id', $requestId)
            ->whereIn('status', ['pending', 'running'])
            ->update(['status' => 'running', 'updated_at' => now()]);
    }

    /**
     * @param  array<string, mixed>  $result
     */
    public function markCompleted(string $requestId, array $result, ?string $engineHint = null): void
    {
        ContentAgentRequest::query()
            ->where('request_id', $requestId)
            ->update([
                'status' => 'completed',
                'result_json' => json_encode($result, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
                'engine_hint' => $engineHint,
                'completed_at' => now(),
                'updated_at' => now(),
            ]);
    }

    public function markFailed(string $requestId, string $errorMessage): void
    {
        ContentAgentRequest::query()
            ->where('request_id', $requestId)
            ->update([
                'status' => 'failed',
                'error_message' => $errorMessage,
                'completed_at' => now(),
                'updated_at' => now(),
            ]);
    }

    public function markExpired(string $requestId): void
    {
        ContentAgentRequest::query()
            ->where('request_id', $requestId)
            ->whereIn('status', ['pending', 'running'])
            ->update([
                'status' => 'expired',
                'error_message' => 'content_agent_request_expired',
                'completed_at' => now(),
                'updated_at' => now(),
            ]);
    }

    public function findByRequestId(string $requestId): ?ContentAgentRequest
    {
        return ContentAgentRequest::query()->where('request_id', $requestId)->first();
    }

    /**
     * @return array{pending:int,running:int,completed:int,failed:int,expired:int}
     */
    public function countByStatus(): array
    {
        return $this->countByStatusSince(null);
    }

    /**
     * @return array{pending:int,running:int,completed:int,failed:int,expired:int}
     */
    public function countByStatusSince(?\Illuminate\Support\Carbon $since): array
    {
        $totals = ['pending' => 0, 'running' => 0, 'completed' => 0, 'failed' => 0, 'expired' => 0];
        $query = ContentAgentRequest::query()->selectRaw('status, COUNT(*) as aggregate');
        if ($since !== null) {
            $query->where('submitted_at', '>=', $since);
        }
        foreach ($query->groupBy('status')->get() as $row) {
            $status = (string) ($row->status ?? '');
            if (array_key_exists($status, $totals)) {
                $totals[$status] = (int) ($row->aggregate ?? 0);
            }
        }

        return $totals;
    }

    /**
     * @return array<string, array{completed:int,failed:int,pending:int}>
     */
    public function countByWorkflowSince(\Illuminate\Support\Carbon $since): array
    {
        $result = [];
        foreach (['content', 'content_pipeline', 'url_import', 'semantic_chunk'] as $workflowType) {
            $result[$workflowType] = ['completed' => 0, 'failed' => 0, 'pending' => 0];
        }

        $rows = ContentAgentRequest::query()
            ->selectRaw('workflow_type, status, COUNT(*) as aggregate')
            ->where('submitted_at', '>=', $since)
            ->whereIn('workflow_type', array_keys($result))
            ->groupBy('workflow_type', 'status')
            ->get();

        foreach ($rows as $row) {
            $workflow = (string) ($row->workflow_type ?? '');
            $status = (string) ($row->status ?? '');
            if (! isset($result[$workflow])) {
                continue;
            }
            if ($status === 'completed') {
                $result[$workflow]['completed'] = (int) ($row->aggregate ?? 0);
            } elseif ($status === 'failed' || $status === 'expired') {
                $result[$workflow]['failed'] += (int) ($row->aggregate ?? 0);
            } elseif ($status === 'pending' || $status === 'running') {
                $result[$workflow]['pending'] += (int) ($row->aggregate ?? 0);
            }
        }

        return $result;
    }

    /**
     * @return list<array{request_id:string,workflow_type:string,error_message:string,submitted_at:?string}>
     */
    public function recentFailures(int $limit = 5): array
    {
        return ContentAgentRequest::query()
            ->whereIn('status', ['failed', 'expired'])
            ->orderByDesc('completed_at')
            ->limit($limit)
            ->get(['request_id', 'workflow_type', 'error_message', 'submitted_at'])
            ->map(static fn (ContentAgentRequest $request): array => [
                'request_id' => (string) $request->request_id,
                'workflow_type' => (string) $request->workflow_type,
                'error_message' => (string) ($request->error_message ?? ''),
                'submitted_at' => $request->submitted_at?->format('Y-m-d H:i'),
            ])
            ->all();
    }

    public function countPendingByCorrelation(string $correlationType): int
    {
        return ContentAgentRequest::query()
            ->where('correlation_type', $correlationType)
            ->whereIn('status', ['pending', 'running'])
            ->count();
    }

    /**
     * @return list<array{request_id:string,status:string,workflow_type:string,error_message:string,submitted_at:?string,correlation_id:int}>
     */
    public function recentByCorrelation(string $correlationType, int $limit = 5): array
    {
        return ContentAgentRequest::query()
            ->where('correlation_type', $correlationType)
            ->orderByDesc('submitted_at')
            ->limit($limit)
            ->get(['request_id', 'status', 'workflow_type', 'error_message', 'submitted_at', 'correlation_id'])
            ->map(static fn (ContentAgentRequest $request): array => [
                'request_id' => (string) $request->request_id,
                'status' => (string) $request->status,
                'workflow_type' => (string) $request->workflow_type,
                'error_message' => (string) ($request->error_message ?? ''),
                'submitted_at' => $request->submitted_at?->format('Y-m-d H:i'),
                'correlation_id' => (int) ($request->correlation_id ?? 0),
            ])
            ->all();
    }

    /**
     * @return list<array{request_id:string,status:string,workflow_type:string,error_message:string,submitted_at:?string}>
     */
    public function recentForKnowledgeBase(int $knowledgeBaseId, int $limit = 3): array
    {
        return ContentAgentRequest::query()
            ->where('correlation_type', 'knowledge_base')
            ->where('correlation_id', $knowledgeBaseId)
            ->orderByDesc('submitted_at')
            ->limit($limit)
            ->get(['request_id', 'status', 'workflow_type', 'error_message', 'submitted_at'])
            ->map(static fn (ContentAgentRequest $request): array => [
                'request_id' => (string) $request->request_id,
                'status' => (string) $request->status,
                'workflow_type' => (string) $request->workflow_type,
                'error_message' => (string) ($request->error_message ?? ''),
                'submitted_at' => $request->submitted_at?->format('Y-m-d H:i'),
            ])
            ->all();
    }
}

