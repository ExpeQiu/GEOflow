<?php

namespace App\Services\GeoEval\Adoption;

use App\Models\ArticleEvaluation;
use App\Models\GeoStrategyMetricSnapshot;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Schema;

final class AdoptionMetricsAggregator
{
    /**
     * @return array<string, mixed>
     */
    public function summary(int $days = 30, string $platform = ''): array
    {
        if (Schema::hasTable('geo_strategy_metric_snapshots')) {
            $latest = $this->latestSnapshot($days, $platform);
            if ($latest !== null) {
                return $latest;
            }
        }

        return $this->computeLiveSummary($days, $platform);
    }

    /**
     * @return list<array{date: string, adoption_rate: float, first_position_rate: float, sample_size: int}>
     */
    public function dailySeries(int $days = 30, string $platform = ''): array
    {
        if (Schema::hasTable('geo_strategy_metric_snapshots')) {
            $query = GeoStrategyMetricSnapshot::query()
                ->where('metric_date', '>=', now()->subDays($days)->toDateString())
                ->orderBy('metric_date');

            if ($platform !== '') {
                $query->where('platform', $platform);
            } else {
                $query->where('platform', '');
            }

            $rows = $query->get();
            if ($rows->isNotEmpty()) {
                return $rows->map(static fn (GeoStrategyMetricSnapshot $row): array => [
                    'date' => (string) $row->metric_date,
                    'adoption_rate' => (float) $row->adoption_rate,
                    'first_position_rate' => (float) $row->first_position_rate,
                    'sample_size' => (int) $row->sample_size,
                ])->all();
            }
        }

        return $this->computeLiveDailySeries($days);
    }

    public function aggregateAndStore(?Carbon $forDate = null): int
    {
        if (! Schema::hasTable('geo_strategy_metric_snapshots')) {
            return 0;
        }

        $date = ($forDate ?? now())->toDateString();
        $summary = $this->computeLiveSummary(1, '');
        $summaryFirst = $this->computeLiveSummary(1, '');

        GeoStrategyMetricSnapshot::query()->updateOrCreate(
            [
                'metric_date' => $date,
                'platform' => '',
            ],
            [
                'adoption_rate' => (float) ($summary['adoption_rate'] ?? 0),
                'first_position_rate' => (float) ($summary['first_position_rate'] ?? 0),
                'sample_size' => (int) ($summary['sample_size'] ?? 0),
                'passed_count' => (int) ($summary['passed_count'] ?? 0),
                'meta' => $summary,
            ]
        );

        return 1;
    }

    /**
     * @return array<string, mixed>|null
     */
    private function latestSnapshot(int $days, string $platform): ?array
    {
        $row = GeoStrategyMetricSnapshot::query()
            ->where('metric_date', '>=', now()->subDays($days)->toDateString())
            ->when($platform !== '', fn ($q) => $q->where('platform', $platform), fn ($q) => $q->where('platform', ''))
            ->orderByDesc('metric_date')
            ->first();

        if (! $row) {
            return null;
        }

        return [
            'total_records' => (int) $row->sample_size,
            'adoption_rate' => (float) $row->adoption_rate,
            'first_position_rate' => (float) $row->first_position_rate,
            'passed_count' => (int) $row->passed_count,
            'sample_size' => (int) $row->sample_size,
            'days' => $days,
            'platform' => $platform,
        ];
    }

    /**
     * @return array<string, mixed>
     */
    private function computeLiveSummary(int $days, string $platform): array
    {
        if (! Schema::hasTable('article_evaluations')) {
            return [
                'total_records' => 0,
                'adoption_rate' => 0.0,
                'first_position_rate' => 0.0,
                'passed_count' => 0,
                'sample_size' => 0,
            ];
        }

        $since = now()->subDays($days);
        $query = ArticleEvaluation::query()
            ->where('created_at', '>=', $since)
            ->whereIn('status', ['passed', 'failed']);

        if ($platform !== '') {
            $query->whereHas('article', function ($articleQuery) use ($platform): void {
                $articleQuery->whereHas('distributions', function ($distributionQuery) use ($platform): void {
                    $distributionQuery->whereHas('channel', function ($channelQuery) use ($platform): void {
                        $channelQuery->where('name', $platform);
                    });
                });
            });
        }

        $rows = $query->get(['status', 'metrics', 'article_id']);

        $total = $rows->count();
        if ($total === 0) {
            return [
                'total_records' => 0,
                'adoption_rate' => 0.0,
                'first_position_rate' => 0.0,
                'passed_count' => 0,
                'sample_size' => 0,
            ];
        }

        $passed = 0;
        $firstPosition = 0;
        $minRank = (int) config('geo_eval.simulation.min_rank', 1);

        foreach ($rows as $row) {
            if ((string) $row->status === 'passed') {
                $passed++;
            }
            $metrics = is_array($row->metrics) ? $row->metrics : [];
            $rank = (int) ($metrics['rank'] ?? 99);
            if ((string) $row->status === 'passed' && $rank <= $minRank && $rank === 1) {
                $firstPosition++;
            }
        }

        return [
            'total_records' => $total,
            'adoption_rate' => round($passed / $total, 4),
            'first_position_rate' => round($firstPosition / $total, 4),
            'passed_count' => $passed,
            'sample_size' => $total,
            'days' => $days,
            'platform' => $platform,
        ];
    }

    /**
     * @return list<array{date: string, adoption_rate: float, first_position_rate: float, sample_size: int}>
     */
    private function computeLiveDailySeries(int $days): array
    {
        if (! Schema::hasTable('article_evaluations')) {
            return [];
        }

        $series = [];
        for ($i = $days - 1; $i >= 0; $i--) {
            $day = now()->subDays($i)->startOfDay();
            $end = $day->copy()->endOfDay();
            $summary = ArticleEvaluation::query()
                ->whereBetween('created_at', [$day, $end])
                ->whereIn('status', ['passed', 'failed'])
                ->get(['status', 'metrics']);

            $total = $summary->count();
            $passed = $summary->where('status', 'passed')->count();
            $first = 0;
            foreach ($summary as $row) {
                $metrics = is_array($row->metrics) ? $row->metrics : [];
                if ((int) ($metrics['rank'] ?? 99) === 1 && (string) $row->status === 'passed') {
                    $first++;
                }
            }

            $series[] = [
                'date' => $day->toDateString(),
                'adoption_rate' => $total > 0 ? round($passed / $total, 4) : 0.0,
                'first_position_rate' => $total > 0 ? round($first / $total, 4) : 0.0,
                'sample_size' => $total,
            ];
        }

        return $series;
    }
}
