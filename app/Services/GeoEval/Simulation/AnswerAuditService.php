<?php

namespace App\Services\GeoEval\Simulation;

/**
 * 规则审计：基于正文摘录与品牌词，不依赖 LLM 生成答案。
 */
final class AnswerAuditService
{
    /**
     * @param  list<string>  $brandKeywords
     * @return array{status: string, tech_accuracy: float, brand_consistency: float, brand_hits: int, keyword_hit: bool}
     */
    public function audit(string $question, string $excerpt, array $brandKeywords = []): array
    {
        $excerptLower = mb_strtolower($excerpt, 'UTF-8');
        $questionLower = mb_strtolower($question, 'UTF-8');

        $brandHits = 0;
        $keywords = $brandKeywords !== [] ? $brandKeywords : config('geo_eval.brand_keywords', []);
        foreach ($keywords as $keyword) {
            $kw = mb_strtolower(trim((string) $keyword), 'UTF-8');
            if ($kw !== '' && str_contains($excerptLower, $kw)) {
                $brandHits++;
            }
        }

        $minBrandHits = max(0, (int) config('geo_eval.audit.min_brand_hits', 0));
        $brandOk = $keywords === [] || $brandHits >= $minBrandHits;

        $keywordHit = true;
        preg_match_all('/[\p{L}\p{N}]{2,}/u', $questionLower, $qMatches);
        foreach ($qMatches[0] ?? [] as $term) {
            if (mb_strlen($term, 'UTF-8') >= 4 && ! str_contains($excerptLower, $term)) {
                continue;
            }
        }
        if (preg_match('/[\p{L}\p{N}]{4,}/u', $questionLower, $main)) {
            $keywordHit = str_contains($excerptLower, mb_strtolower($main[0], 'UTF-8'));
        }

        $hasDigits = preg_match('/\d/', $excerpt) === 1;
        $techAccuracy = ($keywordHit ? 0.5 : 0.2) + ($hasDigits ? 0.3 : 0.1);
        $brandConsistency = $keywords === [] ? 1.0 : min(1.0, $brandHits / max(1, count($keywords)));

        $status = ($brandOk && $keywordHit && mb_strlen($excerpt, 'UTF-8') >= 80) ? 'pass' : 'fail';

        return [
            'status' => $status,
            'tech_accuracy' => round($techAccuracy, 2),
            'brand_consistency' => round($brandConsistency, 2),
            'brand_hits' => $brandHits,
            'keyword_hit' => $keywordHit,
        ];
    }
}
