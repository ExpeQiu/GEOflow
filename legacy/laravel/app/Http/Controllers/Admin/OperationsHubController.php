<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Models\Article;
use App\Models\ArticleDistribution;
use App\Models\DistributionChannel;
use App\Models\Task;
use App\Models\TaskRun;
use App\Support\AdminWeb;
use Illuminate\Http\Request;
use Illuminate\View\View;

class OperationsHubController extends Controller
{
    private const TABS = ['overview', 'tasks', 'articles', 'distribution'];

    public function __construct(
        private readonly TaskController $taskController,
        private readonly ArticleController $articleController,
        private readonly DistributionController $distributionController,
    ) {}

    public function index(Request $request): View
    {
        $tab = trim((string) $request->query('tab', 'overview'));
        if (! in_array($tab, self::TABS, true)) {
            $tab = 'overview';
        }

        $viewData = [
            'pageTitle' => __('admin.operations.hub_title'),
            'activeMenu' => 'operations_hub',
            'adminSiteName' => AdminWeb::siteName(),
            'tab' => $tab,
            'currentTab' => $tab,
            'stats' => $this->loadOverviewStats(),
        ];

        if ($tab === 'tasks') {
            $viewData = array_merge($viewData, $this->taskController->indexViewData());
        }

        if ($tab === 'articles') {
            $viewData = array_merge($viewData, $this->articleController->indexViewData($request));
        }

        if ($tab === 'distribution') {
            $viewData = array_merge($viewData, $this->distributionController->indexViewData());
        }

        return view('admin.operations.index', $viewData);
    }

    /**
     * @return array<string, int>
     */
    private function loadOverviewStats(): array
    {
        $jobStatusCounts = TaskRun::query()
            ->selectRaw('status, COUNT(*) as c')
            ->groupBy('status')
            ->pluck('c', 'status')
            ->all();

        $distributionPending = (int) ArticleDistribution::query()->whereIn('status', ['queued', 'sending'])->count();
        $distributionFailed = (int) ArticleDistribution::query()->where('status', 'failed')->count();

        return [
            'total_tasks' => (int) Task::query()->count(),
            'active_tasks' => (int) Task::query()->where('status', 'active')->count(),
            'running_jobs' => (int) ($jobStatusCounts['running'] ?? 0),
            'pending_jobs' => (int) ($jobStatusCounts['pending'] ?? 0),
            'failed_jobs' => (int) ($jobStatusCounts['failed'] ?? 0),
            'total_articles' => (int) Article::query()->whereNull('deleted_at')->count(),
            'published_articles' => (int) Article::query()->where('status', 'published')->whereNull('deleted_at')->count(),
            'pending_review' => (int) Article::query()->where('review_status', 'pending')->whereNull('deleted_at')->count(),
            'channels_total' => (int) DistributionChannel::query()->count(),
            'channels_active' => (int) DistributionChannel::query()->where('status', 'active')->count(),
            'distribution_pending' => $distributionPending,
            'distribution_failed' => $distributionFailed,
        ];
    }
}
