<?php

namespace Tests\Feature;

use App\Models\ContentAgentRequest;
use App\Services\GeoFlow\ContentAgent\ContentAgentCallbackSigningService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Str;
use Tests\TestCase;

class ContentAgentCallbackTest extends TestCase
{
    use RefreshDatabase;

    public function test_rejects_unsigned_callback(): void
    {
        config(['geoflow.content_agent.callback_secret' => 'test-secret']);

        $response = $this->postJson('/internal/content-agent/callback', [
            'request_id' => Str::uuid()->toString(),
            'workflow_type' => 'content',
            'status' => 'success',
        ]);

        $response->assertUnauthorized();
    }

    public function test_accepts_signed_callback_for_unknown_request(): void
    {
        config(['geoflow.content_agent.callback_secret' => 'test-secret']);

        $requestId = (string) Str::uuid();
        $payload = [
            'contract_version' => '1.0',
            'request_id' => $requestId,
            'workflow_type' => 'content',
            'status' => 'success',
            'engine' => 'langgraph',
            'result' => ['content' => 'hello'],
            'error' => null,
        ];
        $body = json_encode($payload, JSON_UNESCAPED_UNICODE);
        $headers = app(ContentAgentCallbackSigningService::class)->signHeaders('POST', (string) $body);

        $response = $this->call(
            'POST',
            '/internal/content-agent/callback',
            [],
            [],
            [],
            $this->transformHeadersToServerVars(array_merge(['CONTENT_TYPE' => 'application/json'], $headers)),
            $body,
        );

        $response->assertUnprocessable();
        $response->assertJsonPath('message', 'unknown_request_id');
    }

    public function test_idempotent_when_request_already_completed(): void
    {
        config(['geoflow.content_agent.callback_secret' => 'test-secret']);

        $requestId = (string) Str::uuid();
        ContentAgentRequest::query()->create([
            'request_id' => $requestId,
            'workflow_type' => 'content',
            'backend' => 'external',
            'status' => 'completed',
            'correlation_type' => 'task_run',
            'correlation_id' => 1,
            'contract_version' => '1.0',
            'submitted_at' => now(),
            'completed_at' => now(),
        ]);

        $payload = [
            'contract_version' => '1.0',
            'request_id' => $requestId,
            'workflow_type' => 'content',
            'status' => 'success',
            'engine' => 'langgraph',
            'result' => ['content' => 'hello'],
            'error' => null,
        ];
        $body = json_encode($payload, JSON_UNESCAPED_UNICODE);
        $headers = app(ContentAgentCallbackSigningService::class)->signHeaders('POST', (string) $body);

        $response = $this->call(
            'POST',
            '/internal/content-agent/callback',
            [],
            [],
            [],
            $this->transformHeadersToServerVars(array_merge(['CONTENT_TYPE' => 'application/json'], $headers)),
            $body,
        );

        $response->assertOk();
        $response->assertJsonPath('data.status', 'already_completed');
    }
}
