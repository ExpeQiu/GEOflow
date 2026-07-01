<?php

namespace App\Services\Admin\Analytics;

use App\Models\Article;
use App\Models\ArticleEvaluation;
use App\Models\GeoEvalEventLog;
use App\Models\Task;
use App\Services\GeoEval\Adoption\AdoptionMetricsAggregator;
use App\Services\GeoEval\Contracts\GeoEvalClientInterface;
use Illuminate\Support\Facades\Schema;

final class GeoEvalAnalyticsService
{
    public function __construct(
        private readonly GeoEvalClientInterface $geoEvalClient,
        private readonly AdoptionMetricsAggregator $adoptionMetricsAggregator,
    ) {}

    /**
     * @return array<string, mixed>
     */
    public function summary(): array
    {
        $local = $this->localSummary();
        $remote = $this->remoteAdoptionSummary();

        return array_merge($local, [
            'remote_adoption' => $remote,
            'service_healthy' => config('geo_eval.enabled') ? $this->geoEvalClient->healthCheck() : null,
        ]);
    }

    /**
     * @return list<array<string, mixed>>
     */
    public function recentFailures(int $limit = 10): array
    {
        if (! Schema::hasTable('article_evaluations')) {
            return [];
        }

        $rows = ArticleEvaluation::query()
            ->where('status', 'failed')
            ->orderByDesc('id')
            ->limit($limit)
            ->get();

        if ($rows->isEmpty()) {
            return [];
        }

        $articleIds = $rows->pluck('article_id')->map(fn ($id): int => (int) $id)->unique()->values()->all();
        $articles = Article::query()
            ->whereIn('id', $articleIds)
            ->get(['id', 'task_id'])
            ->keyBy('id');

        $taskIds = $articles->pluck('task_id')->filter()->map(fn ($id): int => (int) $id)->unique()->values()->all();
        $tasks = $taskIds === []
            ? collect()
            : Task::query()
                ->whereIn('id', $taskIds)
                ->get(['id', 'name', 'knowledge_base_id', 'insight_template_id'])
                ->keyBy('id');

        return $rows
            ->map(function (ArticleEvaluation $row) use ($articles, $tasks): array {
                $metrics = is_array($row->metrics) ? $row->metrics : [];
                $article = $articles->get((int) $row->article_id);
                $task = $article ? $tasks->get((int) ($article->task_id ?? 0)) : null;

                return [
                    'id' => (int) $row->id,
                    'article_id' => (int) $row->article_id,
                    'task_id' => $task ? (int) $task->id : null,
                    'task_name' => $task ? (string) $task->name : '',
                    'knowledge_base_id' => $task && $task->knowledge_base_id ? (int) $task->knowledge_base_id : null,
                    'insight_template_id' => $task && $task->insight_template_id ? (int) $task->insight_template_id : null,
                    'request_id' => (string) ($row->request_id ?? ''),
                    'failure_reason' => (string) ($row->failure_reason ?? ''),
                    'rank' => (int) ($metrics['rank'] ?? 0),
                    'found' => (bool) ($metrics['found'] ?? false),
                    'audit_status' => (string) ($metrics['audit_status'] ?? ''),
                    'created_at' => optional($row->created_at)->format('Y-m-d H:i:s'),
                ];
            })
            ->all();
    }

    /**
     * @return array<string, mixed>
     */
    public function adoptionDashboard(int $days = 30, string $platform = ''): array
    {
        $stats = $this->adoptionMetricsAggregator->summary($days, $platform);
        $trend = $this->adoptionMetricsAggregator->dailySeries($days, $platform);
        $adoptionFloor = (float) config('geo_eval.alerts.adoption_rate_floor', 0.5);
        $adoptionRate = (float) ($stats['adoption_rate'] ?? 0);

        return [
            'kpis' => $stats,
            'trend' => $trend,
            'below_threshold' => $adoptionRate > 0 && $adoptionRate < $adoptionFloor,
            'days' => $days,
            'platform' => $platform,
        ];
    }

    /**
     * @return list<array<string, mixed>>
     */
    public function failureTopN(int $limit = 5): array
    {
        if (! Schema::hasTable('article_evaluations')) {
            return [];
        }

        return ArticleEvaluation::query()
            ->selectRaw('failure_reason, COUNT(*) as total')
            ->where('status', 'failed')
            ->whereNotNull('failure_reason')
            ->groupBy('failure_reason')
            ->orderByDesc('total')
            ->limit($limit)
            ->get()
            ->map(static fn ($row): array => [
                'failure_reason' => (string) $row->failure_reason,
                'total' => (int) $row->total,
            ])
            ->all();
    }

    /**
     * @return list<array<string, mixed>>
     */
    public function recentEventLogs(int $limit = 20): array
    {
        if (! Schema::hasTable('geo_eval_event_logs')) {
            return [];
        }

        return GeoEvalEventLog::query()
            ->orderByDesc('id')
            ->limit($limit)
            ->get()
            ->map(static fn (GeoEvalEventLog $row): array => [
                'id' => (int) $row->id,
                'request_id' => (string) $row->request_id,
                'event' => (string) $row->event,
                'level' => (string) $row->level,
                'eval_status' => (string) ($row->eval_status ?? ''),
                'article_id' => $row->article_id,
                'task_id' => $row->task_id,
                'message' => (string) ($row->message ?? ''),
                'created_at' => optional($row->created_at)->format('Y-m-d H:i:s'),
            ])
            ->all();
    }

    /**
     * @return array<string, mixed>
     */
    private function localSummary(): array
    {
        if (! Schema::hasColumn('articles', 'eval_status')) {
            return [
                'enabled' => false,
                'pending_eval' => 0,
                'passed' => 0,
                'failed' => 0,
                'skipped' => 0,
            ];
        }

        $base = Article::query()->whereNull('deleted_at');

        return [
            'enabled' => (bool) config('geo_eval.enabled'),
            'gate_enabled' => (bool) config('geo_eval.gate_enabled'),
            'engine' => 'internal',
            'pending_eval' => (int) (clone $base)->where('eval_status', 'pending_eval')->count(),
            'passed' => (int) (clone $base)->where('eval_status', 'passed')->count(),
            'failed' => (int) (clone $base)->where('eval_status', 'failed')->count(),
            'skipped' => (int) (clone $base)->where('eval_status', 'skipped')->count(),
        ];
    }

    /**
     * @return array<string, mixed>|null
     */
    private function remoteAdoptionSummary(): ?array
    {
        if (! config('geo_eval.enabled')) {
            return null;
        }

        try {
            $response = $this->geoEvalClient->getAdoptionStats(30);
            $data = is_array($response['data'] ?? null) ? $response['data'] : [];

            return is_array($data['stats'] ?? null) ? $data['stats'] : $data;
        } catch (\Throwable) {
            return ['error' => 'remote_unavailable'];
        }
    }
}
