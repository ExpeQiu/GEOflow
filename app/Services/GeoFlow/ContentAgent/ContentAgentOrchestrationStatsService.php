<?php

namespace App\Services\GeoFlow\ContentAgent;

use App\Services\GeoFlow\Contracts\ContentAgentClientInterface;
use Illuminate\Support\Carbon;

/** Production Hub 编排可观测性统计。 */
final class ContentAgentOrchestrationStatsService
{
    public function __construct(
        private readonly ContentAgentClientInterface $contentAgentClient,
        private readonly ContentAgentRequestRepository $requestRepository,
    ) {}

    /**
     * @return array<string, mixed>
     */
    public function load(): array
    {
        $backend = $this->contentAgentClient->supportedBackend();
        $since = Carbon::now()->subDay();

        return [
            'backend' => $backend,
            'sidecar_healthy' => $backend === 'external' ? $this->contentAgentClient->healthCheck() : true,
            'driver_hint' => (string) config('geoflow.content_agent.driver_hint', 'langgraph'),
            'totals' => $this->requestRepository->countByStatus(),
            'totals_24h' => $this->requestRepository->countByStatusSince($since),
            'by_workflow' => $this->requestRepository->countByWorkflowSince($since),
            'recent_failures' => $this->requestRepository->recentFailures(5),
            'knowledge_pending' => $this->requestRepository->countPendingByCorrelation('knowledge_base'),
            'knowledge_recent' => $this->requestRepository->recentByCorrelation('knowledge_base', 5),
        ];
    }
}
