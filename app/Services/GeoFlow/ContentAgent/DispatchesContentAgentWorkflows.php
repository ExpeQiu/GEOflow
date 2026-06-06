<?php

namespace App\Services\GeoFlow\ContentAgent;

use App\Services\GeoFlow\ContentAgent\Dto\ContentAgentDispatchResult;
use App\Services\GeoFlow\ContentAgent\Dto\ContentAgentResult;
use App\Services\GeoFlow\Contracts\ContentAgentClientInterface;
use RuntimeException;

/** 共享 dispatch 路由：按 backend 决定 sync / async。 */
trait DispatchesContentAgentWorkflows
{
    abstract protected function usesExternalBackend(): bool;

    abstract protected function externalClient(): ContentAgentClientInterface;

    abstract protected function internalClient(): ContentAgentClientInterface;

    public function dispatchContentGeneration(array $payload): ContentAgentDispatchResult
    {
        return $this->dispatchWorkflow(
            fn (): ContentAgentResult => $this->resolveSyncClient()->generateContent($payload),
            fn (): string => $this->resolveExternalClient()->submitContentWorkflow($payload),
        );
    }

    public function dispatchUrlImportAnalysis(array $payload): ContentAgentDispatchResult
    {
        return $this->dispatchWorkflow(
            fn (): ContentAgentResult => $this->resolveSyncClient()->generateUrlImportAnalysis($payload),
            fn (): string => $this->resolveExternalClient()->submitUrlImportWorkflow($payload),
        );
    }

    public function dispatchSemanticChunkPlan(array $payload): ContentAgentDispatchResult
    {
        return $this->dispatchWorkflow(
            fn (): ContentAgentResult => $this->resolveSyncClient()->generateSemanticChunkPlan($payload),
            fn (): string => $this->resolveExternalClient()->submitSemanticChunkWorkflow($payload),
        );
    }

    /**
     * @param  callable(): ContentAgentResult  $sync
     * @param  callable(): string  $async
     */
    private function dispatchWorkflow(callable $sync, callable $async): ContentAgentDispatchResult
    {
        if ($this->usesExternalBackend()) {
            try {
                return new ContentAgentDispatchResult('async', $async());
            } catch (\Throwable $exception) {
                if (! $this->shouldFallbackOnError()) {
                    throw $exception;
                }

                return new ContentAgentDispatchResult('sync', null, $sync());
            }
        }

        return new ContentAgentDispatchResult('sync', null, $sync());
    }

    private function resolveSyncClient(): ContentAgentClientInterface
    {
        return $this->internalClient();
    }

    private function resolveExternalClient(): ContentAgentClientInterface
    {
        return $this->externalClient();
    }

    private function shouldFallbackOnError(): bool
    {
        return (bool) config('geoflow.content_agent.fallback_on_error', true);
    }

    protected function unsupportedAsync(string $workflow): never
    {
        throw new RuntimeException($workflow.' 异步提交仅 external backend 可用');
    }
}
