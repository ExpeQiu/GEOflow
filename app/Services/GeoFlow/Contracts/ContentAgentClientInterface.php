<?php

namespace App\Services\GeoFlow\Contracts;

use App\Services\GeoFlow\ContentAgent\Dto\ContentAgentDispatchResult;
use App\Services\GeoFlow\ContentAgent\Dto\ContentAgentResult;

/** Content Agent 端口：Laravel 业务层不感知具体编排引擎（LangGraph / LangChain）。 */
interface ContentAgentClientInterface
{
    public function generateContent(array $payload): ContentAgentResult;

    public function generateUrlImportAnalysis(array $payload): ContentAgentResult;

    public function generateSemanticChunkPlan(array $payload): ContentAgentResult;

    public function submitContentWorkflow(array $payload): string;

    public function submitUrlImportWorkflow(array $payload): string;

    public function submitSemanticChunkWorkflow(array $payload): string;

    public function submitContentPipelineWorkflow(array $payload): string;

    public function dispatchContentGeneration(array $payload): ContentAgentDispatchResult;

    public function dispatchContentPipelineGeneration(array $payload): ContentAgentDispatchResult;

    public function dispatchUrlImportAnalysis(array $payload): ContentAgentDispatchResult;

    public function dispatchSemanticChunkPlan(array $payload): ContentAgentDispatchResult;

    public function healthCheck(): bool;

    public function supportedBackend(): string;
}
