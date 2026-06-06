<?php

namespace App\Services\GeoFlow\ContentAgent;

use App\Ai\Agents\MarkdownContentWriterAgent;
use App\Models\AiModel;
use App\Models\ContentAgentRequest;
use App\Services\GeoFlow\ContentAgent\Dto\ContentAgentDispatchResult;
use App\Services\GeoFlow\ContentAgent\Dto\ContentAgentResult;
use App\Services\GeoFlow\Contracts\ContentAgentClientInterface;
use App\Support\GeoFlow\OpenAiRuntimeProvider;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;
use RuntimeException;
use Throwable;

/** Laravel 侧 Content Agent 统一入口：按配置路由 internal / external。 */
final class ContentAgentClient implements ContentAgentClientInterface
{
    use DispatchesContentAgentWorkflows;

    public function __construct(
        private readonly InternalContentAgent $internalContentAgent,
        private readonly ExternalContentAgentClient $externalContentAgentClient,
    ) {}

    public function generateContent(array $payload): ContentAgentResult
    {
        return $this->internalContentAgent->generateContent($payload);
    }

    public function generateUrlImportAnalysis(array $payload): ContentAgentResult
    {
        return $this->internalContentAgent->generateUrlImportAnalysis($payload);
    }

    public function generateSemanticChunkPlan(array $payload): ContentAgentResult
    {
        return $this->internalContentAgent->generateSemanticChunkPlan($payload);
    }

    public function submitContentWorkflow(array $payload): string
    {
        return $this->externalContentAgentClient->submitContentWorkflow($payload);
    }

    public function submitUrlImportWorkflow(array $payload): string
    {
        return $this->externalContentAgentClient->submitUrlImportWorkflow($payload);
    }

    public function submitSemanticChunkWorkflow(array $payload): string
    {
        return $this->externalContentAgentClient->submitSemanticChunkWorkflow($payload);
    }

    public function healthCheck(): bool
    {
        if ($this->usesExternalBackend()) {
            return $this->externalContentAgentClient->healthCheck();
        }

        return true;
    }

    public function supportedBackend(): string
    {
        return $this->usesExternalBackend() ? 'external' : 'internal';
    }

    protected function usesExternalBackend(): bool
    {
        return (string) config('geoflow.content_agent.backend', 'internal') === 'external';
    }

    protected function externalClient(): ContentAgentClientInterface
    {
        return $this->externalContentAgentClient;
    }

    protected function internalClient(): ContentAgentClientInterface
    {
        return $this->internalContentAgent;
    }
}
