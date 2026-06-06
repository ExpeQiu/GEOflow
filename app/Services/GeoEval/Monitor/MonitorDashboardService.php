<?php

namespace App\Services\GeoEval\Monitor;

use App\Models\GeoMonitorAiProbeResult;
use App\Models\GeoMonitorQuestion;
use App\Models\GeoMonitorResult;
use Illuminate\Support\Facades\Schema;

final class MonitorDashboardService
{
    /**
     * @return array{
     *   question_count: int,
     *   probe_count: int,
     *   avg_brand_rank: float|null,
     *   mention_rate: float,
     *   platform_summary: list<array{platform: string, avg_rank: float, mention_rate: float, probes: int}>
     * }
     */
    public function summary(int $days = 30): array
    {
        if (! Schema::hasTable('geo_monitor_ai_probe_results')) {
            return [
                'question_count' => 0,
                'probe_count' => 0,
                'avg_brand_rank' => null,
                'mention_rate' => 0.0,
                'platform_summary' => [],
            ];
        }

        $since = now()->subDays($days);
        $probes = GeoMonitorAiProbeResult::query()
            ->where('created_at', '>=', $since)
            ->where('status', 'completed')
            ->get();

        $questionCount = GeoMonitorQuestion::query()->where('is_active', true)->count();
        $mentionRate = $probes->isEmpty()
            ? 0.0
            : $probes->where('brand_mentioned', true)->count() / $probes->count();

        $ranks = $probes->where('brand_rank', '<', 99)->pluck('brand_rank');
        $avgRank = $ranks->isEmpty() ? null : round($ranks->avg(), 2);

        $platformSummary = [];
        foreach ($probes->groupBy('platform_label') as $label => $group) {
            $groupRanks = $group->where('brand_rank', '<', 99)->pluck('brand_rank');
            $platformSummary[] = [
                'platform' => (string) $label,
                'avg_rank' => $groupRanks->isEmpty() ? 0.0 : round((float) $groupRanks->avg(), 2),
                'mention_rate' => $group->isEmpty() ? 0.0 : round($group->where('brand_mentioned', true)->count() / $group->count(), 3),
                'probes' => $group->count(),
            ];
        }

        usort($platformSummary, static fn (array $a, array $b): int => ($a['avg_rank'] ?: 99) <=> ($b['avg_rank'] ?: 99));

        return [
            'question_count' => $questionCount,
            'probe_count' => $probes->count(),
            'avg_brand_rank' => $avgRank,
            'mention_rate' => round((float) $mentionRate, 3),
            'platform_summary' => $platformSummary,
        ];
    }

    /**
     * @return list<array{question_id: int, question_text: string, platforms: list<array{platform: string, brand_rank: int, mentioned: bool}>}>
     */
    public function rankMatrix(int $limit = 15): array
    {
        if (! Schema::hasTable('geo_monitor_ai_probe_results')) {
            return [];
        }

        $questions = GeoMonitorQuestion::query()
            ->where('is_active', true)
            ->orderByDesc('priority')
            ->limit($limit)
            ->get();

        $matrix = [];
        foreach ($questions as $question) {
            $latestByPlatform = [];
            $probes = GeoMonitorAiProbeResult::query()
                ->where('question_id', $question->id)
                ->where('status', 'completed')
                ->orderByDesc('id')
                ->get();

            foreach ($probes as $probe) {
                $key = (string) $probe->platform_label;
                if (! isset($latestByPlatform[$key])) {
                    $latestByPlatform[$key] = [
                        'platform' => $key,
                        'brand_rank' => (int) $probe->brand_rank,
                        'mentioned' => (bool) $probe->brand_mentioned,
                    ];
                }
            }

            $matrix[] = [
                'question_id' => (int) $question->id,
                'question_text' => \Illuminate\Support\Str::limit((string) $question->question_text, 60),
                'platforms' => array_values($latestByPlatform),
            ];
        }

        return $matrix;
    }

    /**
     * @return list<array{date: string, avg_rank: int, mention_pct: int}>
     */
    public function brandRankTrend(int $days = 14): array
    {
        if (! Schema::hasTable('geo_monitor_ai_probe_results')) {
            return [];
        }

        $since = now()->subDays($days)->startOfDay();
        $rows = GeoMonitorAiProbeResult::query()
            ->where('created_at', '>=', $since)
            ->where('status', 'completed')
            ->orderBy('created_at')
            ->get()
            ->groupBy(fn ($row) => optional($row->created_at)->format('Y-m-d') ?? '');

        $series = [];
        foreach ($rows as $date => $group) {
            $ranks = $group->where('brand_rank', '<', 99)->pluck('brand_rank');
            $series[] = [
                'date' => (string) $date,
                'avg_rank' => $ranks->isEmpty() ? 0 : (int) round((float) $ranks->avg()),
                'mention_pct' => $group->isEmpty()
                    ? 0
                    : (int) round(($group->where('brand_mentioned', true)->count() / $group->count()) * 100),
            ];
        }

        return $series;
    }

    /**
     * @return list<array{date: string, rank: int, accuracy: int}>
     */
    public function ragRankTrend(int $days = 14): array
    {
        if (! Schema::hasTable('geo_monitor_results')) {
            return [];
        }

        $since = now()->subDays($days);
        $rows = GeoMonitorResult::query()
            ->where('created_at', '>=', $since)
            ->orderBy('created_at')
            ->get()
            ->groupBy(fn ($row) => optional($row->created_at)->format('Y-m-d') ?? '');

        $series = [];
        foreach ($rows as $date => $group) {
            $series[] = [
                'date' => (string) $date,
                'rank' => $group->isEmpty() ? 0 : (int) round((float) $group->avg('rank')),
                'accuracy' => $group->isEmpty()
                    ? 0
                    : (int) round(((float) $group->avg('tech_accuracy')) * 100),
            ];
        }

        return $series;
    }
}
