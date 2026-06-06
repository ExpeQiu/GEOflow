<?php

namespace App\Services\GeoFlow\ContentAgent;

use App\Services\GeoFlow\ContentAgent\Dto\ContentAgentDispatchResult;
use App\Services\GeoFlow\ContentAgent\Dto\ContentAgentResult;
use App\Services\GeoFlow\Contracts\ContentAgentClientInterface;
use App\Support\GeoFlow\OutboundHttpProxy;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;
use RuntimeException;
use Throwable;

/** 外部 Content Agent 侧车 HTTP 客户端（引擎无关契约）。 */
final class ExternalContentAgentClient implements ContentAgentClientInterface
{
    public function __construct(
        private readonly ContentAgentRequestRepository $requestRepository,
    ) {}

    public function generateContent(array $payload): ContentAgentResult
    {
        throw new RuntimeException('external backend 请使用 dispatchContentGeneration 异步提交');
    }

    public function generateUrlImportAnalysis(array $payload): ContentAgentResult
    {
        throw new RuntimeException('external backend 请使用 dispatchUrlImportAnalysis 异步提交');
    }

    public function generateSemanticChunkPlan(array $payload): ContentAgentResult
    {
        throw new RuntimeException('external backend 请使用 dispatchSemanticChunkPlan 异步提交');
    }

    public function submitContentWorkflow(array $payload): string
    {
        return $this->submitWorkflow('content', $payload, $payload['correlation'] ?? null);
    }

    public function submitUrlImportWorkflow(array $payload): string
    {
        return $this->submitWorkflow('url_import', $payload, $payload['correlation'] ?? null);
    }

    public function submitSemanticChunkWorkflow(array $payload): string
    {
        return $this->submitWorkflow('semantic_chunk', $payload, $payload['correlation'] ?? null);
    }

    public function submitContentPipelineWorkflow(array $payload): string
    {
        return $this->submitWorkflow('content_pipeline', $payload, $payload['correlation'] ?? null);
    }

    public function dispatchContentGeneration(array $payload): ContentAgentDispatchResult
    {
        return new ContentAgentDispatchResult('async', $this->submitContentWorkflow($payload));
    }

    public function dispatchUrlImportAnalysis(array $payload): ContentAgentDispatchResult
    {
        return new ContentAgentDispatchResult('async', $this->submitUrlImportWorkflow($payload));
    }

    public function dispatchSemanticChunkPlan(array $payload): ContentAgentDispatchResult
    {
        return new ContentAgentDispatchResult('async', $this->submitSemanticChunkWorkflow($payload));
    }

    public function dispatchContentPipelineGeneration(array $payload): ContentAgentDispatchResult
    {
        return new ContentAgentDispatchResult('async', $this->submitContentPipelineWorkflow($payload));
    }

    public function healthCheck(): bool
    {
        $baseUrl = $this->serviceBaseUrl();
        if ($baseUrl === '') {
            return false;
        }

        try {
            $response = Http::withOptions(OutboundHttpProxy::httpClientOptionsForUrl($baseUrl.'/v1/health'))
                ->timeout(5)
                ->get($baseUrl.'/v1/health');

            return $response->successful() && ($response->json('ok') === true || $response->json('ok') === 'true');
        } catch (Throwable) {
            return false;
        }
    }

    public function supportedBackend(): string
    {
        return 'external';
    }

    /**
     * @param  array<string, mixed>|null  $correlation
     */
    private function submitWorkflow(string $workflowType, array $payload, ?array $correlation = null): string
    {
        $baseUrl = $this->serviceBaseUrl();
        if ($baseUrl === '') {
            throw new RuntimeException('CONTENT_AGENT_SERVICE_URL 未配置');
        }

        $requestId = (string) ($payload['request_id'] ?? Str::uuid());
        $correlationType = is_array($correlation) ? (string) ($correlation['type'] ?? '') : '';
        $correlationId = is_array($correlation) ? (int) ($correlation['id'] ?? 0) : 0;

        $body = [
            'request_id' => $requestId,
            'contract_version' => (string) config('geoflow.content_agent.contract_version', '1.0'),
            'callback_url' => $this->callbackUrl(),
            'payload' => $payload,
        ];

        $this->requestRepository->createPending(
            $workflowType,
            'external',
            $payload,
            $correlationType !== '' ? $correlationType : null,
            $correlationId > 0 ? $correlationId : null,
            $requestId,
        );

        $url = $baseUrl.'/v1/workflows/'.$workflowType.'/run_async';
        try {
            $response = Http::withOptions(OutboundHttpProxy::httpClientOptionsForUrl($url))
                ->timeout((int) config('geoflow.content_agent.submit_timeout_seconds', 30))
                ->acceptJson()
                ->post($url, $body);

            if (! $response->successful()) {
                $this->requestRepository->markFailed($requestId, 'submit_http_'.$response->status());
                throw new RuntimeException('Content Agent 提交失败: HTTP '.$response->status());
            }

            $acceptedId = (string) ($response->json('request_id') ?? $requestId);
            $this->requestRepository->markRunning($acceptedId);

            Log::channel('content_agent')->info('content_agent.submit', [
                'request_id' => $acceptedId,
                'workflow_type' => $workflowType,
                'correlation_type' => $correlationType,
                'correlation_id' => $correlationId,
            ]);

            return $acceptedId;
        } catch (Throwable $exception) {
            $this->requestRepository->markFailed($requestId, $exception->getMessage());
            throw $exception;
        }
    }

    private function serviceBaseUrl(): string
    {
        return rtrim(trim((string) config('geoflow.content_agent.service_url', '')), '/');
    }

    private function callbackUrl(): string
    {
        $configured = trim((string) config('geoflow.content_agent.callback_url', ''));
        if ($configured !== '') {
            return rtrim($configured, '/');
        }

        return rtrim((string) config('app.url'), '/').ContentAgentCallbackSigningService::CALLBACK_PATH;
    }
}
