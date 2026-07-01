<?php

namespace App\Services\GeoEval;

use App\Models\Article;
use App\Models\TechIpAsset;
use App\Support\GeoFlow\WikiTaskPolicy;

/** Wiki 页 GEO 规范检查（路线图附录 B）。 */
final class WikiGeoComplianceChecker
{
    /**
     * @return array{passed:bool,checks:list<array{key:string,label:string,passed:bool,detail:string}>}
     */
    public function check(Article $article): array
    {
        if (! WikiTaskPolicy::isWikiFormat((string) ($article->content_format ?? 'article'))) {
            return ['passed' => true, 'checks' => []];
        }

        $meta = is_array($article->wiki_meta) ? $article->wiki_meta : [];
        $content = (string) $article->content;
        $checks = [];

        $quickAnswer = trim((string) ($meta['quick_answer'] ?? ''));
        $checks[] = $this->row('quick_answer', '快速结论', $quickAnswer !== '' && mb_strlen($quickAnswer) <= 200, $quickAnswer === '' ? '缺少 quick_answer' : '');

        $hasTable = (bool) preg_match('/^\|.+\|/m', $content);
        $checks[] = $this->row('table', '表格呈现', $hasTable, $hasTable ? '' : '正文需含 Markdown 表格');

        $relatedCount = is_array($meta['related'] ?? null) ? count($meta['related']) : 0;
        $inlineLinks = preg_match_all('/\]\(\/(?:concepts|compare|guides|data|glossary|threads|topics)\//', $content, $_m);
        $linkOk = $relatedCount >= 3 || $inlineLinks >= 3;
        $checks[] = $this->row('links', '内链 ≥3', $linkOk, 'related 或正文内链不足 3 条');

        $faqCount = is_array($meta['faq'] ?? null) ? count($meta['faq']) : 0;
        if ($faqCount < 2) {
            $faqCount = preg_match_all('/###\s+.+/u', $content, $_f);
        }
        $checks[] = $this->row('faq', 'FAQ ≥2', $faqCount >= 2, 'FAQ 不足 2 条');

        $lastUpdated = trim((string) ($meta['last_updated'] ?? ''));
        $checks[] = $this->row('last_updated', '更新日期', $lastUpdated !== '', '缺少 last_updated');

        $type = (string) ($meta['type'] ?? 'concept');
        $schemaType = (string) ($meta['schema_type'] ?? '');
        $expected = match ($type) {
            'compare' => 'FAQPage',
            'guide' => 'HowTo',
            'data' => 'Dataset',
            default => 'TechArticle',
        };
        $schemaOk = $schemaType === '' || strcasecmp($schemaType, $expected) === 0;
        $checks[] = $this->row('schema_type', 'Schema 类型', $schemaOk, "期望 {$expected}，当前 {$schemaType}");

        $sources = is_array($meta['sources'] ?? null) ? $meta['sources'] : [];
        $hasEvidence = $sources !== [];
        if (! $hasEvidence && (int) ($article->tech_ip_asset_id ?? 0) > 0) {
            $asset = TechIpAsset::query()->find((int) $article->tech_ip_asset_id);
            $hasEvidence = $asset && is_array($asset->evidence) && $asset->evidence !== [];
        }
        $checks[] = $this->row('evidence', '证据链', $hasEvidence, '缺少 sources 或资产 evidence');

        $passed = collect($checks)->every(static fn (array $c): bool => (bool) $c['passed']);

        return ['passed' => $passed, 'checks' => $checks];
    }

    /**
     * @return array{key:string,label:string,passed:bool,detail:string}
     */
    private function row(string $key, string $label, bool $passed, string $detail): array
    {
        return compact('key', 'label', 'passed', 'detail');
    }
}
