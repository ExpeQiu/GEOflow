<?php

namespace App\Services\GeoEval\Monitor;

use App\Models\GeoMonitorQuestion;
use App\Models\SiteSetting;
use Illuminate\Support\Facades\Schema;

final class MonitorSettingsService
{
    private const TECH_KEYWORDS_KEY = 'geo_monitor_tech_keywords';

    /**
     * @return list<string>
     */
    public function techKeywords(): array
    {
        if (! Schema::hasTable('site_settings')) {
            return config('geo_eval.brand_keywords', []);
        }

        $raw = (string) (SiteSetting::query()->where('setting_key', self::TECH_KEYWORDS_KEY)->value('setting_value') ?? '');
        if ($raw === '') {
            return config('geo_eval.brand_keywords', []);
        }

        $decoded = json_decode($raw, true);

        return is_array($decoded)
            ? array_values(array_filter(array_map('strval', $decoded), static fn (string $v): bool => trim($v) !== ''))
            : array_values(array_filter(array_map('trim', preg_split('/[\r\n,，、]+/u', $raw) ?: [])));
    }

    /**
     * @param  list<string>|string  $keywords
     */
    public function saveTechKeywords(array|string $keywords): void
    {
        if (! Schema::hasTable('site_settings')) {
            return;
        }

        $list = is_array($keywords)
            ? $keywords
            : array_values(array_filter(array_map('trim', preg_split('/[\r\n,，、]+/u', (string) $keywords) ?: [])));

        SiteSetting::query()->updateOrCreate(
            ['setting_key' => self::TECH_KEYWORDS_KEY],
            ['setting_value' => json_encode($list, JSON_UNESCAPED_UNICODE)]
        );
    }

    /**
     * @return list<string>
     */
    public function allBrandTargets(?GeoMonitorQuestion $question = null): array
    {
        $merged = array_merge(
            $this->techKeywords(),
            config('geo_eval.brand_keywords', [])
        );
        if ($question && is_array($question->tech_keywords)) {
            $merged = array_merge($merged, $question->tech_keywords);
        }

        return array_values(array_unique(array_filter(array_map('trim', $merged), static fn (string $v): bool => $v !== '')));
    }
}
