"use client";

import type { CSSProperties } from "react";
import type { CompetitorMatrix } from "@/lib/strategy-types";
import { isProductName } from "@/lib/entity-classifier";
import { platformLabel } from "./shared/AivisPrimitives";

const PLATFORM_ORDER = ["doubao", "deepseek", "tongyi", "yuanbao", "wenxin", "kimi"];

type ProductRow = {
  name: string;
  is_self: boolean;
  avgVisibility: number;
  platforms: Record<string, { visibility_pct: number; weighted_rank_score: number | null }>;
};

function buildProductRows(matrix: CompetitorMatrix): { rows: ProductRow[]; platforms: string[] } {
  const platformSet = new Set<string>();
  const productMap = new Map<string, ProductRow>();

  for (const row of matrix.matrix) {
    platformSet.add(row.platform);
    for (const brand of row.brands) {
      if (!isProductName(brand.name)) continue;
      let entry = productMap.get(brand.name);
      if (!entry) {
        entry = { name: brand.name, is_self: brand.is_self, avgVisibility: 0, platforms: {} };
        productMap.set(brand.name, entry);
      }
      entry.platforms[row.platform] = {
        visibility_pct: brand.visibility_pct,
        weighted_rank_score: brand.weighted_rank_score,
      };
      if (brand.is_self) entry.is_self = true;
    }
  }

  const platforms = PLATFORM_ORDER.filter((p) => platformSet.has(p));
  for (const p of platformSet) {
    if (!platforms.includes(p)) platforms.push(p);
  }

  const rows = Array.from(productMap.values()).map((row) => {
    const values = platforms.map((p) => row.platforms[p]?.visibility_pct ?? 0);
    const avg = values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
    return { ...row, avgVisibility: avg };
  });
  rows.sort((a, b) => b.avgVisibility - a.avgVisibility);

  return { rows, platforms };
}

function heatStyle(value: number, min: number, max: number): CSSProperties {
  if (max <= min) return {};
  const t = (value - min) / (max - min);
  return { backgroundColor: `rgba(124, 58, 237, ${0.08 + t * 0.42})` };
}

export function ProductVisibilityMatrixTable({ matrix }: { matrix: CompetitorMatrix }) {
  const { rows, platforms } = buildProductRows(matrix);
  if (rows.length === 0) {
    return <p className="text-sm text-gray-400">暂无产品可见性数据，请先配置产品或导入诊断报告</p>;
  }

  const allValues = rows.flatMap((r) => platforms.map((p) => r.platforms[p]?.visibility_pct ?? 0));
  const minVis = Math.min(...allValues);
  const maxVis = Math.max(...allValues);

  return (
    <div>
      <div className="mb-3 flex items-center justify-between text-xs text-gray-500">
        <span>相对可见性</span>
        <div className="flex items-center gap-2">
          <span>最低</span>
          <div
            className="h-2 w-24 rounded"
            style={{ background: "linear-gradient(to right, rgba(124,58,237,0.08), rgba(124,58,237,0.5))" }}
          />
          <span>最高</span>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-xs">
          <thead>
            <tr className="bg-violet-50">
              <th className="w-10 px-2 py-2 text-center">#</th>
              <th className="min-w-[140px] px-2 py-2 text-left">产品</th>
              {platforms.map((p) => (
                <th key={p} className="px-2 py-2 text-center whitespace-nowrap">
                  {platformLabel(p)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={row.name} className={`border-t border-gray-100 ${row.is_self ? "bg-violet-50/40" : ""}`}>
                <td className="px-2 py-2 text-center text-gray-400">{idx + 1}</td>
                <td className={`px-2 py-2 ${row.is_self ? "font-semibold text-violet-800" : "font-medium text-gray-800"}`}>
                  {row.name}
                  {row.is_self && <span className="ml-1 text-[10px] text-violet-600">（自有）</span>}
                </td>
                {platforms.map((p) => {
                  const cell = row.platforms[p];
                  const vis = cell?.visibility_pct ?? 0;
                  return (
                    <td key={p} className="px-2 py-2 text-center" style={heatStyle(vis, minVis, maxVis)}>
                      {vis > 0 ? `${vis}%` : "—"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-gray-500">
        与领先者差距 {matrix.gap_vs_leader}pp · 自有可见性 {matrix.self_visibility_pct}%
        {matrix.source === "tjg_import" && <span className="ml-2 text-violet-600">· 来源：诊断报告导入</span>}
      </p>
    </div>
  );
}
