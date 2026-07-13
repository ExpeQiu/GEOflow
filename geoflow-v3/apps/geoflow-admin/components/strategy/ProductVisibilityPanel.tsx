import Link from "next/link";
import type { ProductPanel } from "@/lib/strategy-types";
import { PlatformBreakdownTable } from "./PlatformBreakdownTable";
import { ProductConfigPanel } from "./ProductConfigPanel";
import { AivisKpiCard, LayerSection } from "./shared/AivisPrimitives";
import { ProductVisibilityMatrixTable } from "./ProductVisibilityMatrixTable";

export function ProductVisibilityPanel({ data, onRefresh }: { data: ProductPanel; onRefresh?: () => void }) {
  const { metrics } = data;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <AivisKpiCard label="可见性" value={`${metrics.visibility_pct}%`} sub={`${metrics.probe_count} 探针`} />
        <AivisKpiCard label="加权排名" value={String(metrics.weighted_rank_score ?? "—")} tone="cyan" />
        <AivisKpiCard label="好感度" value={metrics.sentiment_score != null ? `${metrics.sentiment_score}%` : "—"} tone="amber" />
        <AivisKpiCard label="场景数" value={String(data.scene_funnel.stats.scene_count)} tone="amber" />
      </div>

      <ProductConfigPanel onChanged={onRefresh} />

      <LayerSection title="产品可见性分析" subtitle="6 平台 × 产品 · 按平均可见性排序">
        <ProductVisibilityMatrixTable matrix={data.competitor_matrix} />
      </LayerSection>

      {(data.platform_breakdown?.length ?? 0) > 0 && (
        <LayerSection title="分平台表现" subtitle="当前可见性 vs 平台领先者">
          <PlatformBreakdownTable rows={data.platform_breakdown ?? []} />
        </LayerSection>
      )}

      <LayerSection title="场景图谱" subtitle="用户画像 → 场景 → 意图 → Query">
        <p className="text-sm text-gray-600">
          场景漏斗与缺口管理已独立至
          <Link href="/strategy/scene-graph" className="mx-1 text-violet-700 hover:underline">场景图谱</Link>
          页，当前共 {data.scene_funnel.stats.scene_count} 个场景、{data.scene_funnel.stats.query_count} 条 Query。
        </p>
      </LayerSection>
    </div>
  );
}
