"use client";

import Link from "next/link";
import { zh } from "@/lib/i18n/zh";
import type { MonitorKpis } from "@/lib/strategy-types";
import { platformLabel } from "./shared/AivisPrimitives";

function fmtPct(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return `${Number(v).toFixed(1)}%`;
}

function fmtPp(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  const n = Number(v);
  return `${n > 0 ? "+" : ""}${n.toFixed(1)}pp`;
}

export function ProbeDashboard({
  dashboard,
  onScan,
  scanning,
}: {
  dashboard: MonitorKpis;
  onScan?: () => void;
  scanning?: boolean;
}) {
  const top3 = dashboard.top3_pct ?? dashboard.self_top3_pct;
  const mention = dashboard.mention_rate_pct ?? Math.round((dashboard.mention_rate || 0) * 1000) / 10;
  const quality = dashboard.quality;
  const gatePass = quality?.gate_pass;

  return (
    <section className="rounded-lg border border-violet-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">北极星 KPI</h2>
          <p className="text-sm text-gray-500">
            口径={dashboard.kpi_track || "open_api"} · 对比+决策 · 有效样本 {dashboard.valid_sample_n ?? "—"} · API{" "}
            {dashboard.api_probe_ratio_pct ?? 0}%
            {gatePass === false ? " · 参数硬门槛未过" : ""}
          </p>
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
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Kpi label="Top3 概率" value={fmtPct(top3)} tone="violet" hint={gatePass === false ? "否决参考" : `Top5 ${fmtPct(dashboard.top5_pct)}`} />
        <Kpi label="相对竞品 pp" value={fmtPp(dashboard.gap_vs_leader_top3_pp)} hint={`领先者 ${fmtPct(dashboard.leader_top3_pct)}`} />
        <Kpi
          label="参数一致率"
          value={quality?.param_consistency_pct == null ? "—" : fmtPct(quality.param_consistency_pct)}
          tone={gatePass === false ? "rose" : gatePass === true ? "emerald" : "amber"}
          hint={gatePass === true ? "达标 ≥95%" : gatePass === false ? "未达标" : "待标定"}
        />
        <Kpi label="提及率" value={fmtPct(mention)} hint={`负向 ${fmtPct(dashboard.sentiment_negative_pct)}`} />
      </div>
      {(dashboard.source?.citation_count || 0) > 0 && (
        <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
          <div className="rounded-md bg-slate-50 p-3">
            <p className="text-xs text-gray-500">官方信源</p>
            <p className="font-semibold">{fmtPct(dashboard.source?.official_share_pct)}</p>
          </div>
          <div className="rounded-md bg-slate-50 p-3">
            <p className="text-xs text-gray-500">第三方</p>
            <p className="font-semibold">{fmtPct(dashboard.source?.third_party_share_pct)}</p>
          </div>
          <div className="rounded-md bg-slate-50 p-3">
            <p className="text-xs text-gray-500">目标域名命中</p>
            <p className="font-semibold">{dashboard.source?.target_domain_hits ?? 0}</p>
          </div>
        </div>
      )}
      {dashboard.platform_summary.length > 0 && (
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-xs text-gray-600">
            <thead>
              <tr>
                {["平台", "Top3%", "可见性%", "提及"].map((h) => (
                  <th key={h} className="px-2 py-1 text-left">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dashboard.platform_summary.map((p) => (
                <tr key={p.platform}>
                  <td className="px-2 py-1">{platformLabel(p.platform)}</td>
                  <td className="px-2 py-1">{p.top3_pct != null ? `${p.top3_pct}%` : "—"}</td>
                  <td className="px-2 py-1">
                    {p.visibility_pct ?? Math.round((p.mentions / Math.max(p.total, 1)) * 100)}%
                  </td>
                  <td className="px-2 py-1">
                    {p.mentions}/{p.total}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-3 text-xs text-gray-400">
        问题 {dashboard.question_count} · 探针 {dashboard.probe_count} · 旧「可见性/好感度」已降级为工程参考
      </p>
    </section>
  );
}

function Kpi({
  label,
  value,
  tone = "slate",
  hint,
}: {
  label: string;
  value: string | number;
  tone?: "violet" | "slate" | "rose" | "emerald" | "amber";
  hint?: string;
}) {
  const bg = {
    violet: "bg-violet-50 border-violet-100",
    slate: "bg-slate-50 border-slate-100",
    rose: "bg-rose-50 border-rose-100",
    emerald: "bg-emerald-50 border-emerald-100",
    amber: "bg-amber-50 border-amber-100",
  }[tone];
  return (
    <div className={`rounded-md border p-3 ${bg}`}>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-gray-900">{value}</p>
      {hint ? <p className="mt-0.5 text-[11px] text-gray-500">{hint}</p> : null}
    </div>
  );
}
