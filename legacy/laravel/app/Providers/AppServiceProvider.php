<?php

namespace App\Providers;

use App\Models\Admin;
use App\Services\Admin\AdminUpdateMetadataService;
use App\Services\Admin\AdminWelcomeModalService;
use App\Services\GeoEval\Adoption\AdoptionMetricsAggregator;
use App\Services\GeoEval\Alerts\GeoAlertNotificationService;
use App\Services\GeoEval\ArticleEvaluationService;
use App\Services\GeoEval\Contracts\GeoEvalClientInterface;
use App\Services\GeoEval\GeoEvalStructuredLogger;
use App\Services\GeoEval\Insight\UrlInsightMinerService;
use App\Services\GeoEval\InsightTemplateService;
use App\Services\GeoEval\InternalGeoEvalEngine;
use App\Services\GeoEval\Simulation\AnswerAuditService;
use App\Services\GeoEval\Simulation\SimulationRagService;
use App\Services\GeoFlow\ArticleGeoFlowService;
use App\Services\GeoFlow\ArticlePublishService;
use App\Services\GeoFlow\KnowledgeConfigService;
use App\Services\GeoFlow\HorizonMetricsAdapter;
use App\Services\GeoFlow\JobQueueService;
use App\Services\GeoFlow\TaskLifecycleService;
use App\Services\GeoFlow\TaskMonitoringQueryService;
use App\Support\GeoFlow\OutboundHttpProxy;
use App\View\Composers\SiteLayoutComposer;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\View;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        $this->app->singleton(JobQueueService::class);
        $this->app->singleton(HorizonMetricsAdapter::class);
        $this->app->singleton(TaskMonitoringQueryService::class);
        $this->app->singleton(TaskLifecycleService::class);
        $this->app->singleton(ArticleGeoFlowService::class);
        $this->app->singleton(ArticlePublishService::class);
        $this->app->singleton(KnowledgeConfigService::class);
        $this->app->singleton(GeoEvalStructuredLogger::class);
        $this->app->singleton(SimulationRagService::class);
        $this->app->singleton(AnswerAuditService::class);
        $this->app->singleton(UrlInsightMinerService::class);
        $this->app->singleton(AdoptionMetricsAggregator::class);
        $this->app->singleton(GeoAlertNotificationService::class);
        $this->app->singleton(ArticleEvaluationService::class);
        $this->app->singleton(InsightTemplateService::class);

        $this->app->singleton(\App\Services\GeoFlow\ContentAgent\AiModelRuntimeBuilder::class);
        $this->app->singleton(\App\Services\GeoFlow\ContentAgent\UrlImportAnalysisRunner::class);
        $this->app->singleton(\App\Services\GeoFlow\ContentAgent\SemanticChunkPlanRunner::class);
        $this->app->singleton(\App\Services\GeoFlow\ContentAgent\InternalContentAgent::class);
        $this->app->singleton(\App\Services\GeoFlow\ContentAgent\ExternalContentAgentClient::class);
        $this->app->singleton(\App\Services\GeoFlow\ContentAgent\ContentAgentRequestRepository::class);
        $this->app->singleton(\App\Services\GeoFlow\ContentAgent\ContentAgentCallbackSigningService::class);
        $this->app->singleton(\App\Services\GeoFlow\ContentAgent\ContentAgentCallbackHandler::class);
        $this->app->singleton(\App\Services\GeoFlow\ContentAgent\ContentAgentClient::class);
        $this->app->singleton(\App\Services\GeoFlow\Contracts\ContentAgentClientInterface::class, \App\Services\GeoFlow\ContentAgent\ContentAgentClient::class);
        $this->app->singleton(\App\Services\GeoFlow\WorkerArticlePersistenceService::class);

        $this->app->singleton(GeoEvalClientInterface::class, InternalGeoEvalEngine::class);
        $this->app->singleton(InternalGeoEvalEngine::class);
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        Http::globalMiddleware(OutboundHttpProxy::middleware());

        View::composer(['site.layout', 'theme.*.layout'], SiteLayoutComposer::class);

        View::composer('admin.layouts.app', function ($view): void {
            $admin = auth('admin')->user();
            $view->with(
                'adminWelcomeModalPayload',
                $admin instanceof Admin ? app(AdminWelcomeModalService::class)->buildModalPayload($admin) : null
            );
            $view->with(
                'adminUpdateNotificationPayload',
                $admin instanceof Admin ? app(AdminUpdateMetadataService::class)->buildNotificationPayload() : null
            );
            $view->with(
                'geoAlertNotificationPayload',
                $admin instanceof Admin ? app(GeoAlertNotificationService::class)->headerPayload() : null
            );
        });
    }
}
