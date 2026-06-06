<?php

namespace App\Services\GeoEval\Monitor;

use App\Models\AiModel;
use App\Models\GeoMonitorPlatformConfig;
use Illuminate\Support\Collection;

final class MonitorPlatformConfigService
{
    /**
     * @param  list<int>  $aiModelIds
     */
    public function syncPlatforms(array $aiModelIds): int
    {
        $aiModelIds = array_values(array_unique(array_filter(array_map('intval', $aiModelIds))));
        $existing = GeoMonitorPlatformConfig::query()->pluck('ai_model_id')->map(fn ($id): int => (int) $id)->all();

        foreach (array_diff($existing, $aiModelIds) as $removeId) {
            GeoMonitorPlatformConfig::query()->where('ai_model_id', $removeId)->delete();
        }

        $count = 0;
        foreach ($aiModelIds as $index => $modelId) {
            $model = AiModel::query()->find($modelId);
            if (! $model) {
                continue;
            }
            GeoMonitorPlatformConfig::query()->updateOrCreate(
                ['ai_model_id' => $modelId],
                [
                    'label' => (string) $model->name,
                    'is_enabled' => true,
                    'sort_order' => 100 - $index,
                ]
            );
            $count++;
        }

        return $count;
    }

    /**
     * @return Collection<int, GeoMonitorPlatformConfig>
     */
    public function enabledPlatforms(): Collection
    {
        return GeoMonitorPlatformConfig::query()
            ->where('is_enabled', true)
            ->orderByDesc('sort_order')
            ->orderBy('id')
            ->get();
    }

    /**
     * @return list<array{id: int, name: string, configured: bool, enabled: bool}>
     */
    public function availableModels(): array
    {
        $configs = GeoMonitorPlatformConfig::query()->get()->keyBy('ai_model_id');
        $models = AiModel::query()
            ->where('status', 'active')
            ->orderBy('name')
            ->get(['id', 'name', 'model_id']);

        return $models->map(function (AiModel $model) use ($configs): array {
            $cfg = $configs->get((int) $model->id);

            return [
                'id' => (int) $model->id,
                'name' => (string) $model->name,
                'model_id' => (string) ($model->model_id ?? ''),
                'configured' => $cfg !== null,
                'enabled' => $cfg ? (bool) $cfg->is_enabled : false,
            ];
        })->all();
    }
}
