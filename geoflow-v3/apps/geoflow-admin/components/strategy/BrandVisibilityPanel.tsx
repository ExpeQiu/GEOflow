"use client";

import type { BrandPanel, CompetitorMatrix } from "@/lib/strategy-types";
import { CompetitorConfigPanel } from "./CompetitorConfigPanel";
import { PlatformBreakdownTable } from "./PlatformBreakdownTable";
import { AivisKpiCard, LayerSection, platformLabel } from "./shared/AivisPrimitives";

function CompetitorMatrixTable({ matrix }: { matrix: CompetitorMatrix }) {
  const brands: string[] = [];
  for (const row of matrix.matrix) {
    for (const b of row.brands) {
      if (!brands.includes(b.name)) brands.push(b.name);
    }
  }
  if (brands.length === 0) return <p className="text-sm text-gray-400">暂无竞品矩阵数据，请先配置竞品并执行扫描</p>;

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-xs">
        <thead>
          <tr className="bg-violet-50">
            <th className="px-2 py-2 text-left">平台</th>
            {brands.map((b) => (
              <th key={b} className={`px-2 py-2 text-left ${matrix.matrix.some((r) => r.brands.find((x) => x.name === b && x.is_self)) ? "font-bold text-violet-800" : ""}`}>
                {b}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.matrix.map((row) => (
            <tr key={row.platform} className="border-t border-gray-100">
              <td className="px-2 py-2 font-medium">{platformLabel(row.platform)}</td>
              {brands.map((bname) => {
                const cell = row.brands.find((x) => x.name === bname);
                const vis = cell?.visibility_pct ?? 0;
                const bg = vis >= 50 ? "bg-violet-100" : vis >= 20 ? "bg-violet-50" : "";
                return (
                  <td key={bname} className={`px-2 py-2 ${bg}`}>
                    {vis}%
                    {cell?.weighted_rank_score != null && <span className="ml-1 text-gray-400">/{cell.weighted_rank_score}</span>}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-gray-500">
        与领先者差距 {matrix.gap_vs_leader}pp · 自有可见性 {matrix.self_visibility_pct}%
      </p>
    </div>
  );
}

export function BrandVisibilityPanel({ data, onRefresh }: { data: BrandPanel; onRefresh?: () => void }) {
  const { metrics } = data;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <AivisKpiCard label="可见性" value={`${metrics.visibility_pct}%`} sub={`${metrics.probe_count} 探针`} />
        <AivisKpiCard label="加权排名" value={String(metrics.weighted_rank_score ?? "—")} tone="cyan" />
        <AivisKpiCard label="好感度" value={metrics.sentiment_score != null ? `${metrics.sentiment_score}%` : "—"} tone="amber" />
        <AivisKpiCard label="竞品数" value={String(data.competitor_matrix.competitors.length)} />
      </div>

      <CompetitorConfigPanel onChanged={onRefresh} />

      <LayerSection title="竞品对标矩阵" subtitle="6 平台 × 品牌">
        <CompetitorMatrixTable matrix={data.competitor_matrix} />
      </LayerSection>

      {(data.platform_breakdown?.length ?? 0) > 0 && (
        <LayerSection title="分平台表现" subtitle="当前可见性 vs 平台领先者">
          <PlatformBreakdownTable rows={data.platform_breakdown ?? []} />
        </LayerSection>
      )}

      {data.sentiment_topics.length > 0 && (
        <LayerSection title="正负向评价标签">
          <div className="flex flex-wrap gap-2">
            {data.sentiment_topics.map((t) => (
              <span
                key={`${t.category}-${t.polarity}`}
                className={`rounded-full px-3 py-1 text-xs ${t.polarity === "positive" ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"}`}
              >
                {t.label} ({t.count})
              </span>
            ))}
          </div>
        </LayerSection>
      )}

      {data.insights.length > 0 && (
        <LayerSection title="洞察摘要">
          <ul className="space-y-3">
            {data.insights.map((i) => (
              <li key={i.id} className="rounded-md border border-violet-100 bg-violet-50/40 p-3 text-sm">
                <p className="font-medium text-violet-900">{i.title}</p>
                <p className="mt-1 text-gray-600">{i.body}</p>
              </li>
            ))}
          </ul>
        </LayerSection>
      )}
    </div>
  );
}

export { CompetitorMatrixTable };
