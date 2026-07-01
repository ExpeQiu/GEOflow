<?php

namespace App\Services\GeoEval\Monitor;

use App\Models\GeoAdminAlert;
use App\Models\GeoMonitorQuestion;
use App\Models\GeoMonitorResult;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Str;

final class MonitorTrendAnalyzer
{
    /**
     * @return list<array{date: string, rank: int, tech_accuracy: float, found: bool}>
     */
    public function seriesForQuestion(int $questionId, int $days = 30): array
    {
        if (! Schema::hasTable('geo_monitor_results')) {
            return [];
        }

        $since = now()->subDays($days);

        return GeoMonitorResult::query()
            ->where('question_id', $questionId)
            ->where('created_at', '>=', $since)
            ->orderBy('created_at')
            ->get()
            ->map(static fn (GeoMonitorResult $row): array => [
                'date' => optional($row->created_at)->format('Y-m-d H:i'),
                'rank' => (int) $row->rank,
                'tech_accuracy' => (float) ($row->tech_accuracy ?? 0),
                'found' => (bool) $row->found,
            ])
            ->all();
    }

    /**
     * @return list<array{question_id: int, question_text: string, latest_rank: int, previous_rank: int|null, rank_delta: int|null, latest_accuracy: float}>
     */
    public function rankChangeSummary(int $limit = 20): array
    {
        if (! Schema::hasTable('geo_monitor_results')) {
            return [];
        }

        $questions = GeoMonitorQuestion::query()
            ->where('is_active', true)
            ->orderByDesc('priority')
            ->limit($limit)
            ->get();

        $out = [];
        foreach ($questions as $question) {
            $results = GeoMonitorResult::query()
                ->where('question_id', $question->id)
                ->orderByDesc('id')
                ->limit(2)
                ->get();

            if ($results->isEmpty()) {
                continue;
            }

            $latest = $results->first();
            $previous = $results->count() > 1 ? $results->get(1) : null;
            $rankDelta = $previous ? (int) $latest->rank - (int) $previous->rank : null;

            $out[] = [
                'question_id' => (int) $question->id,
                'question_text' => Str::limit((string) $question->question_text, 80),
                'latest_rank' => (int) $latest->rank,
                'previous_rank' => $previous ? (int) $previous->rank : null,
                'rank_delta' => $rankDelta,
                'latest_accuracy' => (float) ($latest->tech_accuracy ?? 0),
            ];
        }

        return $out;
    }

    /**
     * 检测排名下滑与准确率跌破阈值，写入 geo_admin_alerts。
     *
     * @return int 新增告警数
     */
    public function checkAndRecordAlerts(): int
    {
        if (! Schema::hasTable('geo_admin_alerts') || ! config('geo_eval.enabled')) {
            return 0;
        }

        $threshold = (int) config('geo_eval.monitor.rank_drop_threshold', 2);
        $accuracyFloor = (float) config('geo_eval.monitor.accuracy_floor', 0.5);
        $alerts = 0;

        foreach ($this->rankChangeSummary(100) as $row) {
            $delta = $row['rank_delta'];
            if ($delta !== null && $delta >= $threshold) {
                $alerts += $this->recordAlert(
                    'rank_drop',
                    (float) $threshold,
                    (float) $delta,
                    "问题 #{$row['question_id']} 排名下滑 {$delta} 位（{$row['previous_rank']} → {$row['latest_rank']}）"
                );
            }
            if ($row['latest_accuracy'] > 0 && $row['latest_accuracy'] < $accuracyFloor) {
                $alerts += $this->recordAlert(
                    'accuracy_below_floor',
                    $accuracyFloor,
                    $row['latest_accuracy'],
                    "问题 #{$row['question_id']} 准确率 {$row['latest_accuracy']} 低于阈值"
                );
            }
        }

        return $alerts;
    }

    private function recordAlert(string $type, float $threshold, float $current, string $message): int
    {
        $recent = GeoAdminAlert::query()
            ->where('alert_type', $type)
            ->where('message', 'like', '%'.explode(' ', $message)[1].'%')
            ->where('created_at', '>=', now()->subDay())
            ->exists();
        if ($recent) {
            return 0;
        }

        GeoAdminAlert::query()->create([
            'alert_type' => $type,
            'severity' => 'warning',
            'threshold' => $threshold,
            'current_value' => $current,
            'message' => $message,
            'channels' => ['admin' => true],
            'notified_feishu' => false,
            'created_at' => now(),
        ]);

        return 1;
    }
}
