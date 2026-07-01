<?php

namespace App\Services\GeoEval\WebIntel;

use App\Models\GeoWebInsightReport;
use App\Models\GeoWebSource;
use App\Models\InsightTemplate;
use Illuminate\Support\Collection;

final class StrategyInsightComposer
{
    /**
     * @param  Collection<int, GeoWebSource>  $competitors
     * @return array{gap_analysis: list<array<string, mixed>>, recommendations: list<array<string, mixed>>, style_guide: array<string, mixed>}
     */
    public function compose(?GeoWebSource $self, Collection $competitors): array
    {
        $selfFeatures = is_array($self?->features_json) ? $self->features_json : [];
        $gaps = [];
        $recommendations = [];

        $compHeadings = $this->avgInt($competitors, 'headings');
        $selfHeadings = (int) ($selfFeatures['headings'] ?? 0);
        if ($compHeadings >= 2 && $selfHeadings < 2) {
            $gaps[] = ['key' => 'headings', 'competitor_avg' => $compHeadings, 'self' => $selfHeadings];
            $recommendations[] = [
                'type' => 'structure',
                'priority' => 'high',
                'message' => '竞品普遍使用多级标题（H2/H3），建议补充章节结构。',
            ];
        }

        $compData = $this->avgInt($competitors, 'data_anchor_count');
        $selfData = (int) ($selfFeatures['data_anchor_count'] ?? 0);
        if ($compData >= 3 && $selfData < $compData) {
            $gaps[] = ['key' => 'data_anchors', 'competitor_avg' => $compData, 'self' => $selfData];
            $recommendations[] = [
                'type' => 'structure',
                'priority' => 'high',
                'message' => '竞品数据锚点密度更高，建议补充具体参数、年份与来源引用。',
            ];
        }

        $compLists = $this->countTruthy($competitors, 'has_lists');
        if ($compLists >= max(1, (int) ceil($competitors->count() / 2)) && ! ($selfFeatures['has_lists'] ?? false)) {
            $recommendations[] = [
                'type' => 'structure',
                'priority' => 'medium',
                'message' => '竞品多使用要点列表，建议将核心信息提炼为条目列表。',
            ];
        }

        $mustInclude = [];
        foreach ($recommendations as $rec) {
            if (str_contains((string) $rec['message'], '标题')) {
                $mustInclude[] = '多级标题';
            }
            if (str_contains((string) $rec['message'], '数据')) {
                $mustInclude[] = '具体参数与年份';
            }
            if (str_contains((string) $rec['message'], '列表')) {
                $mustInclude[] = '要点列表';
            }
        }

        $styleGuide = [
            'voice' => '专业、可验证、结构清晰',
            'must_include' => array_values(array_unique($mustInclude)),
            'avoid' => ['空洞口号', '无来源的夸张表述'],
            'summary' => '基于外部信源对比生成的策略约束',
        ];

        return [
            'gap_analysis' => $gaps,
            'recommendations' => $recommendations,
            'style_guide' => $styleGuide,
        ];
    }

    /**
     * @param  Collection<int, GeoWebSource>  $competitors
     */
    public function createReport(
        ?int $questionId,
        ?GeoWebSource $self,
        Collection $competitors,
        ?string $templateName = null
    ): GeoWebInsightReport {
        $composed = $this->compose($self, $competitors);

        $report = GeoWebInsightReport::query()->create([
            'question_id' => $questionId,
            'self_source_id' => $self ? (int) $self->id : null,
            'competitor_source_ids' => $competitors->pluck('id')->map(fn ($id): int => (int) $id)->all(),
            'gap_analysis_json' => $composed['gap_analysis'],
            'recommendations_json' => $composed['recommendations'],
        ]);

        if ($templateName !== null && $templateName !== '') {
            $template = InsightTemplate::query()->create([
                'name' => $templateName,
                'source_url' => $self ? (string) $self->url : null,
                'style_guide' => $composed['style_guide'],
                'features' => $self && is_array($self->features_json) ? $self->features_json : [],
                'eeat_score' => $self && is_array($self->eeat_json)
                    ? (float) ($self->eeat_json['overall'] ?? null)
                    : null,
            ]);
            $report->insight_template_id = (int) $template->id;
            $report->save();
        }

        return $report->fresh() ?? $report;
    }

    /**
     * @param  Collection<int, GeoWebSource>  $sources
     */
    private function avgInt(Collection $sources, string $key): float
    {
        if ($sources->isEmpty()) {
            return 0.0;
        }
        $sum = 0;
        foreach ($sources as $source) {
            $features = is_array($source->features_json) ? $source->features_json : [];
            $sum += (int) ($features[$key] ?? 0);
        }

        return $sum / $sources->count();
    }

    /**
     * @param  Collection<int, GeoWebSource>  $sources
     */
    private function countTruthy(Collection $sources, string $key): int
    {
        $count = 0;
        foreach ($sources as $source) {
            $features = is_array($source->features_json) ? $source->features_json : [];
            if (! empty($features[$key])) {
                $count++;
            }
        }

        return $count;
    }
}
