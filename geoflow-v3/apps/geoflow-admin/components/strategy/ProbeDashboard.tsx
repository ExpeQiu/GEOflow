"use client";

import Link from "next/link";
import { zh } from "@/lib/i18n/zh";
import type { MonitorKpis } from "@/lib/strategy-types";
import { platformLabel } from "./shared/AivisPrimitives";

export function ProbeDashboard({
  dashboard,
  onScan,
  scanning,
}: {
  dashboard: MonitorKpis;
  onScan?: () => void;
  scanning?: boolean;
}) {
  const visibility = dashboard.visibility_pct ?? Math.round(dashboard.mention_rate * 1000) / 10;

  return (
    <section className="rounded-lg border border-violet-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">探针概览</h2>
          <p className="text-sm text-gray-500">AIVIS 可见性 · 排名 · 好感度 · 平台探针</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {onScan && (
            <button
              type="button"
              disabled={scanning}
              onClick={onScan}
              className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              {scanning ? "扫描中…" : zh.strategy.monitor.scanAll}
            </button>
          )}
          <Link href="/strategy/collection" className="rounded-md border border-violet-300 px-4 py-2 text-sm text-violet-700">
            探针设置
          </Link>
          <Link href="/strategy/reports" className="rounded-md border border-violet-300 px-4 py-2 text-sm text-violet-700">
            诊断报告
          </Link>
          <Link href="/strategy/question-bank" className="rounded-md border border-violet-300 px-4 py-2 text-sm text-violet-700">
            问题库
          </Link>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        <Kpi label="可见性" value={`${visibility}%`} tone="violet" />
        <Kpi label="加权排名" value={dashboard.weighted_rank_score ?? dashboard.avg_brand_rank ?? "—"} />
        <Kpi label="好感度" value={dashboard.sentiment_score != null ? `${dashboard.sentiment_score}%` : "—"} />
        <Kpi label={zh.strategy.monitor.kpiQuestions} value={dashboard.question_count} />
        <Kpi label={zh.strategy.monitor.kpiProbes} value={dashboard.probe_count} />
      </div>
      {dashboard.platform_summary.length > 0 && (
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-xs text-gray-600">
            <thead>
              <tr>
                {["平台", "可见性%", "加权排名", "提及"].map((h) => (
                  <th key={h} className="px-2 py-1 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dashboard.platform_summary.map((p) => (
                <tr key={p.platform}>
                  <td className="px-2 py-1">{platformLabel(p.platform)}</td>
                  <td className="px-2 py-1">{p.visibility_pct ?? Math.round((p.mentions / Math.max(p.total, 1)) * 100)}%</td>
                  <td className="px-2 py-1">{p.weighted_rank_score ?? p.avg_rank ?? "—"}</td>
                  <td className="px-2 py-1">{p.mentions}/{p.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function Kpi({ label, value, tone }: { label: string; value: string | number; tone?: "violet" }) {
  return (
    <div className={`rounded-md p-4 ${tone === "violet" ? "bg-violet-50" : "bg-gray-50"}`}>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}
