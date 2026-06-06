<?php

namespace App\Services\GeoEval\WebIntel;

use App\Services\GeoEval\Insight\UrlInsightMinerService;
use Illuminate\Support\Facades\Http;

/**
 * 扩展 URL 挖掘：多维度页面特征分析。
 */
final class WebPageAnalyzer
{
    public function __construct(
        private readonly UrlInsightMinerService $urlInsightMinerService,
    ) {}

    /**
     * @return array{url: string, features: array<string, mixed>, eeat: array<string, mixed>, style_guide: array<string, mixed>}
     */
    public function analyze(string $url): array
    {
        $mined = $this->urlInsightMinerService->mine($url);
        $html = $this->fetchHtml($url);

        $externalLinks = preg_match_all('/<a\s[^>]*href=["\']https?:\/\//i', $html) ?: 0;
        $tables = preg_match_all('/<table\b/i', $html) ?: 0;
        $dataDensity = preg_match_all('/\d{2,}/', strip_tags($html)) ?: 0;
        $author = $this->extractMeta($html, 'author');

        $features = array_merge(is_array($mined['features'] ?? null) ? $mined['features'] : [], [
            'external_links' => $externalLinks,
            'tables' => $tables,
            'data_anchor_count' => $dataDensity,
            'author_meta' => $author,
        ]);

        $eeat = is_array($mined['eeat'] ?? null) ? $mined['eeat'] : [];
        if ($author !== '') {
            $eeat['author_present'] = true;
            $eeat['overall'] = min(1.0, ((float) ($eeat['overall'] ?? 0.5)) + 0.05);
        }

        return [
            'url' => (string) ($mined['url'] ?? $url),
            'features' => $features,
            'eeat' => $eeat,
            'style_guide' => is_array($mined['style_guide'] ?? null) ? $mined['style_guide'] : [],
        ];
    }

    private function fetchHtml(string $url): string
    {
        try {
            $timeout = max(3, (int) config('geo_eval.insight.fetch_timeout', 12));
            $response = Http::timeout($timeout)
                ->withHeaders(['User-Agent' => (string) config('geo_eval.insight.user_agent', 'GEOworkflow-Insight/1.0')])
                ->get($url);

            return $response->successful() ? (string) $response->body() : '';
        } catch (\Throwable) {
            return '';
        }
    }

    private function extractMeta(string $html, string $name): string
    {
        if (preg_match('/<meta[^>]+name=["\']'.preg_quote($name, '/').'["\'][^>]+content=["\']([^"\']+)/i', $html, $m)) {
            return trim(html_entity_decode($m[1], ENT_QUOTES | ENT_HTML5, 'UTF-8'));
        }

        return '';
    }
}
