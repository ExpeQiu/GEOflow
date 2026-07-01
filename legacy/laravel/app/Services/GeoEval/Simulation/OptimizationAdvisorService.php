<?php

namespace App\Services\GeoEval\Simulation;

/**
 * 规则化 GEO 优化建议引擎。
 */
final class OptimizationAdvisorService
{
    /**
     * @param  array<string, mixed>  $metrics
     * @param  array<string, mixed>  $auditData
     * @param  list<array<string, mixed>>  $gapAnalysis
     * @return list<array{type: string, priority: string, message: string}>
     */
    public function advise(
        string $question,
        array $metrics,
        array $auditData,
        array $gapAnalysis = []
    ): array {
        $items = [];
        $rank = (int) ($metrics['rank'] ?? 99);
        $topK = (int) ($metrics['top_k'] ?? config('geo_eval.simulation.top_k', 5));
        $minRank = (int) config('geo_eval.simulation.min_rank', 1);
        $found = (bool) ($metrics['found'] ?? false);

        if (! $found || $rank > $minRank) {
            $items[] = [
                'type' => 'rank',
                'priority' => $rank > $topK ? 'high' : 'medium',
                'message' => "目标片段排名第 {$rank}（Top{$topK} 外或未命中），建议增加与问题关键词共现的段落，并强化首段摘要密度。",
            ];
        }

        $techAccuracy = (float) ($auditData['tech_accuracy'] ?? 0);
        $accuracyFloor = (float) config('geo_eval.monitor.accuracy_floor', 0.5);
        if ($techAccuracy < $accuracyFloor) {
            $items[] = [
                'type' => 'accuracy',
                'priority' => 'high',
                'message' => '技术准确性偏低，建议补充具体参数、年份或数据来源等数据锚点。',
            ];
        } elseif (! ($auditData['keyword_hit'] ?? true)) {
            $items[] = [
                'type' => 'accuracy',
                'priority' => 'medium',
                'message' => '正文未充分覆盖问题核心词，建议在标题或首段明确回应问题关键词。',
            ];
        }

        $brandHits = (int) ($auditData['brand_hits'] ?? 0);
        $brandKeywords = config('geo_eval.brand_keywords', []);
        if ($brandKeywords !== [] && $brandHits < count($brandKeywords)) {
            $items[] = [
                'type' => 'brand',
                'priority' => 'medium',
                'message' => '品牌词覆盖不足，建议在首段或结论段自然植入品牌关键词。',
            ];
        }

        $auditStatus = (string) ($auditData['status'] ?? '');
        if (in_array($auditStatus, ['fail', 'failed', 'reject'], true)) {
            $items[] = [
                'type' => 'audit',
                'priority' => 'high',
                'message' => '内容审计未通过，请检查正文长度（建议 ≥80 字）与事实表述完整性。',
            ];
        }

        foreach ($gapAnalysis as $gap) {
            $message = (string) ($gap['message'] ?? '');
            if ($message !== '') {
                $items[] = [
                    'type' => 'structure',
                    'priority' => (string) ($gap['priority'] ?? 'medium'),
                    'message' => $message,
                ];
            }
        }

        if ($items === [] && $question !== '') {
            $items[] = [
                'type' => 'info',
                'priority' => 'low',
                'message' => '当前仿真指标良好，可继续监控排名趋势变化。',
            ];
        }

        return $items;
    }
}
