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
}
