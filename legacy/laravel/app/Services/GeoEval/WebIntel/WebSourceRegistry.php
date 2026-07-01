<?php

namespace App\Services\GeoEval\WebIntel;

use App\Models\GeoWebSource;
use Illuminate\Support\Collection;

final class WebSourceRegistry
{
    public function __construct(
        private readonly WebPageAnalyzer $webPageAnalyzer,
        private readonly AdoptionSignalService $adoptionSignalService,
    ) {}

    /**
     * @param  array<string, mixed>  $data
     */
    public function register(array $data): GeoWebSource
    {
        $url = trim((string) ($data['url'] ?? ''));
        $domain = parse_url($url, PHP_URL_HOST) ?: '';

        return GeoWebSource::query()->create([
            'url' => $url,
            'domain' => $domain,
            'label' => (string) ($data['label'] ?? 'competitor'),
            'question_id' => isset($data['question_id']) ? (int) $data['question_id'] : null,
            'fetch_status' => 'pending',
        ]);
    }

    public function refresh(GeoWebSource $source): GeoWebSource
    {
        try {
            $analyzed = $this->webPageAnalyzer->analyze((string) $source->url);
            $signals = $this->adoptionSignalService->signalsForUrl((string) $source->url);

            $features = is_array($analyzed['features'] ?? null) ? $analyzed['features'] : [];
            $features['adoption_signals'] = $signals;

            $source->features_json = $features;
            $source->eeat_json = is_array($analyzed['eeat'] ?? null) ? $analyzed['eeat'] : [];
            $source->last_fetched_at = now();
            $source->fetch_status = 'ok';
            $source->save();
        } catch (\Throwable) {
            $source->fetch_status = 'failed';
            $source->save();
        }

        return $source->fresh() ?? $source;
    }

    /**
     * @return Collection<int, GeoWebSource>
     */
    public function staleSources(int $days = 0): Collection
    {
        $days = $days > 0 ? $days : (int) config('geo_eval.web_intel.refresh_days', 7);
        $cutoff = now()->subDays($days);

        return GeoWebSource::query()
            ->where(function ($q) use ($cutoff): void {
                $q->whereNull('last_fetched_at')
                    ->orWhere('last_fetched_at', '<', $cutoff)
                    ->orWhere('fetch_status', 'failed');
            })
            ->orderBy('id')
            ->limit(50)
            ->get();
    }

    public function delete(GeoWebSource $source): void
    {
        $source->delete();
    }
}
