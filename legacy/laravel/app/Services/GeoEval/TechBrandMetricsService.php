<?php

namespace App\Services\GeoEval;

use App\Models\Article;
use App\Models\ArticleDistribution;
use App\Models\TechIpAsset;
use Illuminate\Support\Facades\Schema;

/** 技术品牌 Strategy Hub / Dashboard 指标聚合。 */
final class TechBrandMetricsService
{
    /**
     * @return array<string, int|float|string|null>
     */
    public function summary(): array
    {
        if (! Schema::hasTable('tech_ip_assets')) {
            return $this->emptySummary();
        }

        $totalAssets = TechIpAsset::query()->count();
        $p0Total = TechIpAsset::query()->where('priority', 'P0')->count();
        $p0Ready = TechIpAsset::query()
            ->where('priority', 'P0')
            ->where('can_name', true)
            ->where('can_visualize', true)
            ->where('can_translate', true)
            ->count();
        $publishedAssets = TechIpAsset::query()->where('status', '已发布')->count();
        $needsUpdate = TechIpAsset::query()->where('status', '需更新')->count();

        $wikiArticles = 0;
        $wikiCompliant = 0;
        if (Schema::hasColumn('articles', 'content_format')) {
            $wikiArticles = Article::query()->where('content_format', 'wiki_mdx')->count();
            $wikiCompliant = Article::query()
                ->where('content_format', 'wiki_mdx')
                ->whereIn('eval_status', ['passed', 'skipped'])
                ->count();
        }

        $gwebSuccess = 0;
        $gwebTotal = 0;
        if (Schema::hasTable('article_distributions')) {
            $gwebQuery = ArticleDistribution::query()
                ->whereHas('channel', static fn ($q) => $q->where('channel_type', 'gweb_wiki'));
            $gwebTotal = (clone $gwebQuery)->count();
            $gwebSuccess = (clone $gwebQuery)->where('status', 'success')->count();
        }

        $complianceRate = $wikiArticles > 0 ? round($wikiCompliant / $wikiArticles * 100, 1) : 0.0;
        $p0Coverage = $p0Total > 0 ? round($p0Ready / $p0Total * 100, 1) : 0.0;
        $gwebSyncRate = $gwebTotal > 0 ? round($gwebSuccess / $gwebTotal * 100, 1) : 0.0;

        return [
            'total_assets' => $totalAssets,
            'p0_total' => $p0Total,
            'p0_ready' => $p0Ready,
            'p0_coverage_pct' => $p0Coverage,
            'published_assets' => $publishedAssets,
            'needs_update_assets' => $needsUpdate,
            'wiki_articles' => $wikiArticles,
            'wiki_compliance_pct' => $complianceRate,
            'gweb_sync_total' => $gwebTotal,
            'gweb_sync_success' => $gwebSuccess,
            'gweb_sync_rate_pct' => $gwebSyncRate,
            'gweb_analytics_url' => (string) config('geoflow.gweb.analytics_url', ''),
        ];
    }

    /**
     * @return array<string, int|float|string|null>
     */
    private function emptySummary(): array
    {
        return [
            'total_assets' => 0,
            'p0_total' => 0,
            'p0_ready' => 0,
            'p0_coverage_pct' => 0.0,
            'published_assets' => 0,
            'needs_update_assets' => 0,
            'wiki_articles' => 0,
            'wiki_compliance_pct' => 0.0,
            'gweb_sync_total' => 0,
            'gweb_sync_success' => 0,
            'gweb_sync_rate_pct' => 0.0,
            'gweb_analytics_url' => (string) config('geoflow.gweb.analytics_url', ''),
        ];
    }
}
