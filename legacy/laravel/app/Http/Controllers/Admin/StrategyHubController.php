<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Models\Article;
use App\Models\Category;
use App\Models\DistributionChannel;
use App\Models\GeoAdminAlert;
use App\Models\GeoMonitorQuestion;
use App\Models\GeoMonitorRun;
use App\Models\GeoWebInsightReport;
use App\Models\GeoWebSource;
use App\Models\KeywordLibrary;
use App\Models\KnowledgeBase;
use App\Models\Task;
use App\Services\Admin\Analytics\AnalyticsFilter;
use App\Services\Admin\Analytics\AnalyticsLogQueryService;
use App\Services\Admin\Analytics\AnalyticsOverviewService;
use App\Services\Admin\Analytics\GeoEvalAnalyticsService;
use App\Services\GeoEval\Monitor\MonitorDashboardService;
use App\Services\GeoEval\Monitor\MonitorPlatformConfigService;
use App\Services\GeoEval\Monitor\MonitorSettingsService;
use App\Services\GeoEval\Monitor\MonitorTrendAnalyzer;
use App\Services\GeoEval\TechBrandMetricsService;
use App\Support\AdminWeb;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Schema;
use Illuminate\View\View;

class StrategyHubController extends Controller
{
    public function __construct(
        private readonly GeoEvalAnalyticsService $geoEvalAnalyticsService,
        private readonly MonitorTrendAnalyzer $monitorTrendAnalyzer,
        private readonly MonitorDashboardService $monitorDashboardService,
        private readonly MonitorPlatformConfigService $platformConfigService,
        private readonly MonitorSettingsService $monitorSettingsService,
        private readonly AnalyticsOverviewService $analyticsOverviewService,
        private readonly AnalyticsLogQueryService $analyticsLogQueryService,
        private readonly TechBrandMetricsService $techBrandMetricsService,
    ) {}

    public function index(Request $request): View|RedirectResponse
    {
        $tab = (string) $request->query('tab', 'overview');
        if ($tab === 'adoption') {
            return redirect()->route('admin.strategy.index', array_merge(
                $request->except('tab'),
                ['tab' => 'analytics']
            ));
        }

        $geoDays = max(7, min(90, (int) $request->query('geo_days', 30)));
        $geoPlatform = trim((string) $request->query('geo_platform', ''));

        $viewData = [
            'pageTitle' => __('admin.strategy.hub_title'),
            'activeMenu' => 'strategy_hub',
            'adminSiteName' => AdminWeb::siteName(),
            'tab' => $tab,
            'geoEvalSummary' => $this->geoEvalAnalyticsService->summary(),
            'geoAdoptionDashboard' => $this->geoEvalAnalyticsService->adoptionDashboard($geoDays, $tab === 'analytics' ? $geoPlatform : ''),
            'geoDays' => $geoDays,
            'geoPlatform' => $tab === 'analytics' ? $geoPlatform : '',
            'geoPlatformOptions' => $tab === 'analytics'
                ? DistributionChannel::query()->orderBy('name')->pluck('name', 'id')
                : [],
            'monitorQuestions' => Schema::hasTable('geo_monitor_questions')
                ? GeoMonitorQuestion::query()->orderByDesc('priority')->orderByDesc('id')->limit(50)->get()
                : collect(),
            'rankChanges' => $this->monitorTrendAnalyzer->rankChangeSummary(10),
            'recentRuns' => Schema::hasTable('geo_monitor_runs')
                ? GeoMonitorRun::query()->orderByDesc('id')->limit(5)->get()
                : collect(),
            'webSources' => Schema::hasTable('geo_web_sources')
                ? GeoWebSource::query()->orderByDesc('id')->limit(30)->get()
                : collect(),
            'webReports' => Schema::hasTable('geo_web_insight_reports')
                ? GeoWebInsightReport::query()->orderByDesc('id')->limit(10)->get()
                : collect(),
            'recentAlerts' => $this->recentAlerts(),
            'keywordLibraries' => KeywordLibrary::query()->orderBy('name')->get(['id', 'name']),
            'knowledgeBases' => KnowledgeBase::query()->orderBy('name')->get(['id', 'name']),
            'monitorDashboard' => $this->monitorDashboardService->summary(30),
            'monitorRankMatrix' => $this->monitorDashboardService->rankMatrix(12),
            'monitorBrandTrend' => $this->monitorDashboardService->brandRankTrend(14),
            'monitorRagTrend' => $this->monitorDashboardService->ragRankTrend(14),
            'monitorPlatformModels' => $this->platformConfigService->availableModels(),
            'monitorTechKeywords' => implode("\n", $this->monitorSettingsService->techKeywords()),
            'simulatorData' => $this->simulatorData(),
            'techBrandMetrics' => $this->techBrandMetricsService->summary(),
        ];

        if ($tab === 'analytics') {
            $viewData = array_merge($viewData, $this->analyticsViewData($request));
        }

        return view('admin.strategy.index', $viewData);
    }

    /**
     * @return array<string, mixed>
     */
    private function analyticsViewData(Request $request): array
    {
        $filter = AnalyticsFilter::fromRequest($request->query());

        return [
            'filters' => $filter,
            'filterOptions' => $this->analyticsFilterOptions(),
            'globalOverview' => $this->analyticsOverviewService->globalOverview(),
            'kpis' => $this->analyticsOverviewService->kpis($filter),
            'publicationTrend' => $this->analyticsOverviewService->publicationTrend($filter),
            'taskTrend' => $this->analyticsOverviewService->taskTrend($filter),
            'contentFunnel' => $this->analyticsOverviewService->contentFunnel($filter),
            'distributionSummary' => $this->analyticsOverviewService->distributionSummary($filter),
            'topContent' => $this->analyticsOverviewService->topContent($filter),
            'aiUsageSummary' => $this->analyticsOverviewService->aiUsageSummary($filter),
            'categoryDistribution' => $this->analyticsOverviewService->categoryDistribution($filter),
            'performanceStats' => $this->analyticsOverviewService->performanceStats($filter),
            'latestArticles' => $this->analyticsOverviewService->latestArticles($filter),
            'taskHealth' => $this->analyticsOverviewService->taskHealth($filter),
            'materialHealth' => $this->analyticsOverviewService->materialHealth(),
            'aiHealth' => $this->analyticsOverviewService->aiHealth(),
            'urlImportHealth' => $this->analyticsOverviewService->urlImportHealth($filter),
            'logSummary' => $this->analyticsLogQueryService->summary($filter),
        ];
    }

    /**
     * @return array<string, mixed>
     */
    private function analyticsFilterOptions(): array
    {
        return [
            'channels' => DistributionChannel::query()
                ->orderBy('name')
                ->select('id', 'name')
                ->get(),
            'tasks' => Task::query()
                ->orderByDesc('created_at')
                ->select('id', 'name')
                ->limit(100)
                ->get(),
            'categories' => Category::query()
                ->orderBy('name')
                ->select('id', 'name')
                ->get(),
            'articles' => Article::query()
                ->whereNull('deleted_at')
                ->orderByDesc('created_at')
                ->select('id', 'title')
                ->limit(100)
                ->get(),
        ];
    }

    /**
     * @return array<string, mixed>
     */
    private function simulatorData(): array
    {
        return [
            'summary' => $this->geoEvalAnalyticsService->summary(),
            'failureTopN' => $this->geoEvalAnalyticsService->failureTopN(),
            'recentFailures' => $this->geoEvalAnalyticsService->recentFailures(),
            'recentEvents' => $this->geoEvalAnalyticsService->recentEventLogs(),
            'gateConfig' => [
                'enabled' => (bool) config('geo_eval.enabled'),
                'gate_enabled' => (bool) config('geo_eval.gate_enabled'),
                'rollout_percent' => (int) config('geo_eval.gate_rollout_percent', 100),
            ],
        ];
    }

    /**
     * @return list<array<string, mixed>>
     */
    private function recentAlerts(): array
    {
        if (! Schema::hasTable('geo_admin_alerts')) {
            return [];
        }

        return GeoAdminAlert::query()
            ->orderByDesc('id')
            ->limit(10)
            ->get()
            ->map(static fn (GeoAdminAlert $row): array => [
                'id' => (int) $row->id,
                'alert_type' => (string) $row->alert_type,
                'message' => (string) ($row->message ?? ''),
                'created_at' => optional($row->created_at)->format('Y-m-d H:i:s'),
            ])
            ->all();
    }
}
