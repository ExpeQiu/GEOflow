<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Models\Article;
use App\Models\GeoAdminAlert;
use App\Services\Admin\Analytics\GeoEvalAnalyticsService;
use App\Services\GeoEval\ArticleEvaluationService;
use App\Support\AdminWeb;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Schema;
use Illuminate\View\View;

class GeoEvalDiagnosticsController extends Controller
{
    public function __construct(
        private readonly GeoEvalAnalyticsService $analyticsService,
        private readonly ArticleEvaluationService $evaluationService,
    ) {}

    public function index(): View
    {
        return view('admin.geo-eval.diagnostics', [
            'pageTitle' => __('admin.geo_eval.diagnostics_title'),
            'activeMenu' => 'geo_eval',
            'adminSiteName' => AdminWeb::siteName(),
            'summary' => $this->analyticsService->summary(),
            'gateConfig' => [
                'enabled' => (bool) config('geo_eval.enabled'),
                'gate_enabled' => (bool) config('geo_eval.gate_enabled'),
                'rollout_percent' => (int) config('geo_eval.gate_rollout_percent', 100),
            ],
            'failureTopN' => $this->analyticsService->failureTopN(),
            'recentFailures' => $this->analyticsService->recentFailures(),
            'recentEvents' => $this->analyticsService->recentEventLogs(),
            'recentAlerts' => $this->recentAlerts(),
        ]);
    }

    public function reevaluate(Request $request, int $articleId): RedirectResponse
    {
        $this->evaluationService->queueEvaluation($articleId);

        return redirect()
            ->route('admin.geo-eval.diagnostics')
            ->with('status', __('admin.geo_eval.reevaluate_queued', ['id' => $articleId]));
    }

    public function batchReevaluate(Request $request): RedirectResponse
    {
        $ids = Article::query()
            ->where('eval_status', 'failed')
            ->whereNull('deleted_at')
            ->orderByDesc('id')
            ->limit(20)
            ->pluck('id');

        foreach ($ids as $id) {
            $this->evaluationService->queueEvaluation((int) $id);
        }

        return redirect()
            ->route('admin.geo-eval.diagnostics')
            ->with('status', __('admin.geo_eval.batch_reevaluate_queued', ['count' => $ids->count()]));
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
                'alert_type' => (string) $row->alert_type,
                'severity' => (string) $row->severity,
                'threshold' => $row->threshold,
                'current_value' => $row->current_value,
                'message' => (string) ($row->message ?? ''),
                'notified_feishu' => (bool) $row->notified_feishu,
                'created_at' => optional($row->created_at)->format('Y-m-d H:i:s'),
            ])
            ->all();
    }
}
