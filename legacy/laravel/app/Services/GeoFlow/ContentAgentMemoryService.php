<?php

namespace App\Services\GeoFlow;

use App\Models\ContentAgentMemory;
use Illuminate\Support\Facades\Log;

/** Content Pipeline 任务级轻量记忆。 */
final class ContentAgentMemoryService
{
    private const int MAX_RECENT_SUMMARIES = 5;

    /**
     * @return array<string, mixed>
     */
    public function snapshotForTask(int $taskId): array
    {
        if ($taskId <= 0) {
            return [];
        }

        $record = ContentAgentMemory::query()
            ->where('task_id', $taskId)
            ->where('scope', 'task')
            ->first();

        if (! $record || ! is_array($record->summary_json)) {
            return ['recent_summaries' => [], 'brand_notes' => []];
        }

        return $record->summary_json;
    }

    /**
     * @param  array<string, mixed>  $patch
     */
    public function applyPatch(int $taskId, array $patch): void
    {
        if ($taskId <= 0 || $patch === []) {
            return;
        }

        $summary = trim((string) ($patch['summary'] ?? ''));
        if ($summary === '') {
            return;
        }

        $record = ContentAgentMemory::query()->firstOrNew([
            'task_id' => $taskId,
            'scope' => 'task',
        ]);

        $existing = is_array($record->summary_json) ? $record->summary_json : [];
        $recent = is_array($existing['recent_summaries'] ?? null) ? $existing['recent_summaries'] : [];
        array_unshift($recent, [
            'summary' => $summary,
            'recorded_at' => now()->toIso8601String(),
        ]);
        $recent = array_slice($recent, 0, self::MAX_RECENT_SUMMARIES);

        $brandNotes = is_array($existing['brand_notes'] ?? null) ? $existing['brand_notes'] : [];
        if (is_array($patch['brand_notes'] ?? null)) {
            $brandNotes = array_values(array_unique(array_merge(
                $brandNotes,
                array_filter(array_map('strval', $patch['brand_notes']))
            )));
        }

        $record->summary_json = [
            'recent_summaries' => $recent,
            'brand_notes' => array_slice($brandNotes, 0, 10),
        ];
        $record->save();

        Log::channel('content_agent')->info('content_agent.memory_patch', [
            'task_id' => $taskId,
            'summary_length' => mb_strlen($summary, 'UTF-8'),
        ]);
    }
}
