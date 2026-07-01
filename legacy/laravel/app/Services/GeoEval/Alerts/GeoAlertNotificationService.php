<?php

namespace App\Services\GeoEval\Alerts;

use App\Models\GeoAdminAlert;
use Illuminate\Support\Facades\Schema;

final class GeoAlertNotificationService
{
    /**
     * @return array{count: int, latest: string|null, items: list<array<string, mixed>>}
     */
    public function headerPayload(): array
    {
        if (! config('geo_eval.enabled') || ! Schema::hasTable('geo_admin_alerts')) {
            return ['count' => 0, 'latest' => null, 'items' => []];
        }

        $items = GeoAdminAlert::query()
            ->orderByDesc('id')
            ->limit(5)
            ->get()
            ->map(static fn (GeoAdminAlert $row): array => [
                'type' => (string) $row->alert_type,
                'message' => (string) ($row->message ?? ''),
                'created_at' => optional($row->created_at)->format('Y-m-d H:i'),
            ])
            ->all();

        return [
            'count' => count($items),
            'latest' => $items[0]['message'] ?? null,
            'items' => $items,
        ];
    }
}
