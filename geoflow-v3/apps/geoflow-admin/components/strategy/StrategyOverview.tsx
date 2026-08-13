import Link from "next/link";
import { zh } from "@/lib/i18n/zh";
import type { AnalyticsSnapshot, GapRemediation, GeoEvalSummary, GeowebAlignment, MonitorKpis, TechBrandMetrics } from "@/lib/strategy-types";
import { surfaceCardClass } from "./shared/AivisPrimitives";

function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${Number(v).toFixed(digits)}%`;
}

function fmtPp(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const n = Number(v);
  return `${n > 0 ? "+" : ""}${n.toFixed(1)}pp`;
}

export function StrategyOverview({
  geoEval,
  techBrand,
  monitor,
  analytics,
  geowebAlignment,
  gwebAlignment,
  remediations = [],
  onProcessDue,
  processBusy,
}: {
  geoEval: GeoEvalSummary;
  techBrand: TechBrandMetrics;
  monitor: MonitorKpis;
  analytics: AnalyticsSnapshot;
  geowebAlignment?: GeowebAlignment | null;
  /** @deprecated */
  gwebAlignment?: GeowebAlignment | null;
  remediations?: GapRemediation[];
  onProcessDue?: () => void;
  processBusy?: boolean;
}) {
  const alignment = geowebAlignment ?? gwebAlignment;
  const pageCount = alignment?.geoweb_page_count ?? alignment?.gweb_page_count ?? 0;
  const passRate =
    geoEval.passed + geoEval.failed > 0
      ? Math.round((geoEval.passed / (geoEval.passed + geoEval.failed)) * 100)
      : 0;

  const completed = remediations.filter((r) => r.status === "completed");
  const latestLift = completed[0];
  const quality = monitor.quality;
  const source = monitor.source;
  const gatePass = quality?.gate_pass;
  const top3 = monitor.top3_pct ?? monitor.self_top3_pct;
  const gap = monitor.gap_vs_leader_top3_pp;
  const mention = monitor.mention_rate_pct ?? Math.round((monitor.mention_rate || 0) * 100);
  const paramPct = quality?.param_consistency_pct;
  const paramLabel =
    gatePass === true ? "达标" : gatePass === false ? "未达标" : "待标定";
  const paramTone = gatePass === true ? "green" : gatePass === false ? "rose" : "amber";

  return (
    <div className="space-y-6">
      <p className="text-xs text-gray-500">
        口径={monitor.kpi_track || "open_api"} · 子集=对比+决策 · 有效样本=
        {monitor.valid_sample_n ?? "—"} · API占比={monitor.api_probe_ratio_pct ?? 0}%
        {gatePass === false ? " · 参数硬门槛未过，结果层视为未达标" : ""}
      </p>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <MiniCard
          label="Top3 概率"
          value={fmtPct(top3)}
          meta={`Top5 ${fmtPct(monitor.top5_pct)} · 加权 ${monitor.weighted_rank_score ?? monitor.avg_brand_rank ?? "—"}`}
          href="/strategy/brand"
          tone="violet"
          badge={gatePass === false ? "否决参考" : undefined}
        />
        <MiniCard
          label="相对竞品 pp"
          value={fmtPp(gap)}
          meta={`领先者 Top3 ${fmtPct(monitor.leader_top3_pct)}`}
          href="/strategy/brand"
          tone="cyan"
        />
        <MiniCard
          label="参数一致率"
          value={paramPct == null ? "—" : fmtPct(paramPct)}
          meta={`${paramLabel} · 门槛 ≥${quality?.threshold ?? 95}%`}
          href="/production/tech-assets"
          tone={paramTone}
        />
        <MiniCard
          label="提及率"
          value={fmtPct(mention, 0)}
          meta={`负向率 ${fmtPct(monitor.sentiment_negative_pct)} · 操作化 ≥40%`}
          href="/strategy/question-bank"
          tone="cyan"
        />
      </div>

      {(source?.official_share_pct != null || (source?.citation_count ?? 0) > 0) && (
        <section className={`${surfaceCardClass} p-5`}>
          <h2 className="text-base font-semibold text-gray-900">信源成因</h2>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3 text-sm">
            <div>
              <p className="text-xs text-gray-500">官方信源占比</p>
              <p className="font-semibold">{fmtPct(source?.official_share_pct)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">第三方占比</p>
              <p className="font-semibold">{fmtPct(source?.third_party_share_pct)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">目标域名命中</p>
              <p className="font-semibold">{source?.target_domain_hits ?? 0}</p>
            </div>
          </div>
        </section>
      )}

      {(latestLift || remediations.length > 0 || onProcessDue) && (
        <section className={`${surfaceCardClass} p-5`}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-base font-semibold text-gray-900">补缺 Lift 闭环</h2>
            {onProcessDue && (
              <button
                type="button"
                disabled={processBusy}
                onClick={onProcessDue}
                className="rounded-md bg-violet-600 px-3 py-1.5 text-xs text-white disabled:opacity-50"
              >
                {processBusy ? "处理中…" : "处理到期实验"}
              </button>
            )}
          </div>
          <p className="mt-1 text-sm text-gray-500">
            实验 {remediations.length} 条
            {latestLift
              ? latestLift.delta_top3_pp != null
                ? ` · 最近 ΔTop3 ${latestLift.delta_top3_pp}pp（${latestLift.scene_name || latestLift.scene_id}）`
                : ` · 最近 Δ可见性 ${latestLift.delta_visibility_pct ?? "—"}pp（过渡）`
              : " · 等待发布后再扫"}
          </p>
          <ul className="mt-3 space-y-1 text-sm text-gray-700">
            {remediations.slice(0, 5).map((r) => (
              <li key={r.id}>
                [{r.status}] {r.scene_name || r.scene_id}
                {r.delta_top3_pp != null
                  ? ` · Top3 ${r.baseline_top3_pct ?? "—"}% → Δ ${r.delta_top3_pp}pp`
                  : ` · 基线 ${r.baseline_visibility_pct ?? "—"}%${
                      r.delta_visibility_pct != null ? ` → Δ ${r.delta_visibility_pct}pp` : ""
                    }`}
              </li>
            ))}
          </ul>
        </section>
      )}

      <details className={`${surfaceCardClass} p-5`}>
        <summary className="cursor-pointer text-base font-semibold text-gray-900">基建健康（折叠）</summary>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="GEO 仿真通过率" value={`${passRate}%`} sub={`通过 ${geoEval.passed} · 失败 ${geoEval.failed}`} tone="cyan" />
          <MetricCard
            label="GEOweb 对齐"
            value={alignment ? `${alignment.alignment_pct}%` : "—"}
            sub={alignment ? `${alignment.matched_count}/${pageCount} 页` : "未拉取"}
            tone="emerald"
          />
          <MetricCard label={zh.strategy.techBrand.p0Coverage} value={`${techBrand.p0_ready}/${techBrand.p0_total}`} sub={`${techBrand.p0_coverage_pct}%`} tone="violet" />
          <MetricCard label={zh.strategy.techBrand.assets} value={String(techBrand.total_assets)} sub={techBrand.needs_update_assets > 0 ? `${techBrand.needs_update_assets} 需更新` : "—"} tone="amber" />
        </div>
        <div className="mt-4 flex flex-wrap gap-3 border-t border-slate-100 pt-4 text-sm">
          <Link href="/production/geo-eval" className="text-blue-600 hover:underline">
            GEO 门禁
          </Link>
          <Link href="/production/tech-assets" className="text-blue-600 hover:underline">
            技术 IP 资产
          </Link>
          <Link href="/operations/tasks" className="text-blue-600 hover:underline">
            创建 Wiki 任务
          </Link>
          <span className="text-xs text-gray-400">分析文章 {analytics.total_articles}</span>
        </div>
      </details>
    </div>
  );
}

function MiniCard({
  label,
  value,
  meta,
  href,
  tone,
  badge,
}: {
  label: string;
  value: string;
  meta: string;
  href: string;
  tone: "cyan" | "violet" | "green" | "amber" | "rose";
  badge?: string;
}) {
  const border = {
    cyan: "border-cyan-200 bg-cyan-50/60",
    violet: "border-violet-200 bg-violet-50/60",
    green: "border-emerald-200 bg-emerald-50/60",
    amber: "border-amber-200 bg-amber-50/60",
    rose: "border-rose-200 bg-rose-50/60",
  }[tone];
  const link = {
    cyan: "text-cyan-800",
    violet: "text-violet-800",
    green: "text-emerald-800",
    amber: "text-amber-800",
    rose: "text-rose-800",
  }[tone];
  return (
    <div className={`rounded-lg border p-5 ${border}`}>
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase text-gray-600">{label}</p>
        {badge ? <span className="rounded bg-rose-100 px-1.5 py-0.5 text-[10px] font-semibold text-rose-700">{badge}</span> : null}
      </div>
      <p className="mt-2 text-2xl font-semibold text-gray-900">{value}</p>
      <p className="mt-1 text-xs text-gray-500">{meta}</p>
      <Link href={href} className={`mt-3 inline-block text-sm hover:underline ${link}`}>
        {zh.strategy.viewDetail}
      </Link>
    </div>
  );
}

function MetricCard({ label, value, sub, tone }: { label: string; value: string; sub: string; tone: string }) {
  const bg = {
    violet: "border-violet-100 bg-violet-50/50 text-violet-700",
    emerald: "border-emerald-100 bg-emerald-50/50 text-emerald-700",
    blue: "border-blue-100 bg-blue-50/50 text-blue-700",
    amber: "border-amber-100 bg-amber-50/50 text-amber-700",
    cyan: "border-cyan-100 bg-cyan-50/50 text-cyan-700",
  }[tone];
  return (
    <div className={`rounded-md border p-4 ${bg}`}>
      <p className="text-xs font-medium">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
      <p className="text-xs opacity-80">{sub}</p>
    </div>
  );
}
