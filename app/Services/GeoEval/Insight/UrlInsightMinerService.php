<?php

namespace App\Services\GeoEval\Insight;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;

/**
 * URL 抓取 + 规则 StyleGuide（参考 GEO strategy_miner）。
 */
final class UrlInsightMinerService
{
    /**
     * @return array{url: string, features: array<string, mixed>, eeat: array<string, mixed>, style_guide: array<string, mixed>}
     */
    public function mine(string $url): array
    {
        $url = trim($url);
        if ($url === '' || ! filter_var($url, FILTER_VALIDATE_URL)) {
            throw new \InvalidArgumentException('invalid_url');
        }

        $html = $this->fetchHtml($url);
        $text = $this->extractText($html);
        $title = $this->extractTitle($html);

        $wordCount = str_word_count($text);
        $headings = preg_match_all('/<h[1-3][^>]*>/i', $html, $m) ? count($m[0]) : 0;
        $lists = preg_match_all('/<ul|<ol/i', $html) ? 1 : 0;

        $eeatOverall = min(1.0, 0.45 + min(0.35, $wordCount / 2000) + ($headings > 2 ? 0.15 : 0.05));

        return [
            'url' => $url,
            'features' => [
                'title' => $title,
                'word_count' => $wordCount,
                'headings' => $headings,
                'has_lists' => (bool) $lists,
                'tone' => $wordCount > 800 ? 'long_form' : 'concise',
            ],
            'eeat' => [
                'overall' => round($eeatOverall, 2),
                'experience' => round(min(1.0, $eeatOverall * 0.9), 2),
                'expertise' => round(min(1.0, $eeatOverall * 0.95), 2),
            ],
            'style_guide' => [
                'voice' => '专业、可验证、结构清晰',
                'title_pattern' => $title !== '' ? $title : '参考原文标题结构',
                'must_include' => array_values(array_filter([
                    $headings >= 2 ? '多级标题' : null,
                    $lists ? '要点列表' : null,
                    '核心事实与数据锚点',
                ])),
                'avoid' => ['空洞口号', '无来源的夸张表述'],
                'summary' => Str::limit($text, 280),
            ],
        ];
    }

    private function fetchHtml(string $url): string
    {
        $timeout = max(3, (int) config('geo_eval.insight.fetch_timeout', 12));
        $response = Http::timeout($timeout)
            ->withHeaders(['User-Agent' => (string) config('geo_eval.insight.user_agent', 'GEOworkflow-Insight/1.0')])
            ->get($url);

        if (! $response->successful()) {
            throw new \RuntimeException('fetch_failed:'.$response->status());
        }

        return (string) $response->body();
    }

    private function extractTitle(string $html): string
    {
        if (preg_match('/<title[^>]*>(.*?)<\/title>/is', $html, $m)) {
            return trim(html_entity_decode(strip_tags($m[1]), ENT_QUOTES | ENT_HTML5, 'UTF-8'));
        }

        return '';
    }

    private function extractText(string $html): string
    {
        $stripped = preg_replace('/<script\b[^>]*>.*?<\/script>/is', '', $html) ?? $html;
        $stripped = preg_replace('/<style\b[^>]*>.*?<\/style>/is', '', $stripped) ?? $stripped;

        return trim(preg_replace('/\s+/u', ' ', strip_tags($stripped)) ?? '');
    }
}
