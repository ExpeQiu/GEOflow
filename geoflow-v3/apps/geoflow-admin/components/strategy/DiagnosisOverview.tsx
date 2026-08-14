"use client";

import Link from "next/link";
import type {
  DiagnosisPanel,
  GapRemediation,
  GeoEvalSummary,
  GeowebAlignment,
  MonitorKpis,
  TechBrandMetrics,
} from "@/lib/strategy-types";
import { zh } from "@/lib/i18n/zh";
import { ProbeDashboard } from "./ProbeDashboard";
import { AivisKpiCard, GapPriorityBadge, LayerSection, surfaceCardClass } from "./shared/AivisPrimitives";

/**
 * 诊断总览唯一入口：北极星 KPI + AIVIS 五层摘要 + 补缺闭环 + 基建健康。
 * 运营数据（文章/浏览/任务）已迁至 /operations/analytics。
 */
export function DiagnosisOverview({
  data,
  monitor,
  remediations = [],
  geoEval,
  techBrand,
  geowebAlignment,
  onScan,
  scanning,
  onProcessDue,
  processBusy,
}: {
  data: DiagnosisPanel;
  monitor: MonitorKpis;
  remediations?: GapRemediation[];
  geoEval?: GeoEvalSummary | null;
  techBrand?: TechBrandMetrics | null;
  geowebAlignment?: GeowebAlignment | null;
  onScan?: () => void;
  scanning?: boolean;
  onProcessDue?: () => void;
  processBusy?: boolean;
}) {
  const { collection, brand, product, optimization, difficulty } = data;
  const window =
    collection.collection_window.period_start && collection.collection_window.period_end
      ? `${collection.collection_window.period_start} ~ ${collection.collection_window.period_end}`
      : "暂无采集记录";

  const completed = remediations.filter((r) => r.status === "completed");
  const latestLift = completed[0];
  const alignment = geowebAlignment;
  const pageCount = alignment?.geoweb_page_count ?? alignment?.gweb_page_count ?? 0;
  const passRate =
    geoEval && geoEval.passed + geoEval.failed > 0
      ? Math.round((geoEval.passed / (geoEval.passed + geoEval.failed)) * 100)
      : null;

  return (
    <div className="space-y-6">
      <ProbeDashboard dashboard={monitor} onScan={onScan} scanning={scanning} />

      <LayerSection title="① 数据采集层" subtitle={`${collection.platform_count} 个 AI 平台 · ${window}`}>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <AivisKpiCard
            label="品牌场景"
            value={`${collection.question_stats.brand_questions} 题`}
            sub={`约 ${collection.question_stats.brand_probes_estimated} 次探针`}
          />
          <AivisKpiCard
            label="产品场景"
            value={`${collection.question_stats.product_questions} 题`}
            sub={`约 ${collection.question_stats.product_probes_estimated} 次探针`}
            tone="cyan"
          />
          <AivisKpiCard label="平台数" value={String(collection.platform_count)} tone="amber" />
          <div className="flex flex-col justify-center gap-1 text-sm">
            <Link href="/strategy/probes?view=scan" className="text-violet-700 hover:underline">
              采集详情 →
            </Link>
            <Link href="/strategy/probes?view=questions" className="text-violet-700 hover:underline">
              问题库 →
            </Link>
          </div>
        </div>
      </LayerSection>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <LayerSection title="② 品牌可见性">
          <div className="grid grid-cols-3 gap-3">
            <AivisKpiCard
              label="Top3"
              value={brand.top3_pct != null ? `${brand.top3_pct}%` : `${brand.visibility_pct}%`}
            />
            <AivisKpiCard
              label="提及率"
              value={brand.mention_rate_pct != null ? `${brand.mention_rate_pct}%` : `${brand.visibility_pct}%`}
              tone="cyan"
            />
            <AivisKpiCard
              label="负向率"
              value={
                brand.sentiment_negative_pct != null
                  ? `${brand.sentiment_negative_pct}%`
                  : brand.sentiment_score != null
                    ? `${brand.sentiment_score}%`
                    : "—"
              }
              tone="amber"
            />
          </div>
          <Link href="/strategy/visibility?view=brand" className="mt-3 inline-block text-sm text-violet-700 hover:underline">
            品牌竞品矩阵 →
          </Link>
        </LayerSection>

        <LayerSection title="③ 产品可见性">
          <div className="grid grid-cols-3 gap-3">
            <AivisKpiCard
              label="Top3"
              value={product.top3_pct != null ? `${product.top3_pct}%` : `${product.visibility_pct}%`}
            />
            <AivisKpiCard
              label="提及率"
              value={
                product.mention_rate_pct != null ? `${product.mention_rate_pct}%` : `${product.visibility_pct}%`
              }
              tone="cyan"
            />
            <AivisKpiCard
              label="负向率"
              value={
                product.sentiment_negative_pct != null
                  ? `${product.sentiment_negative_pct}%`
                  : product.sentiment_score != null
                    ? `${product.sentiment_score}%`
                    : "—"
              }
              tone="amber"
            />
          </div>
          <div className="mt-3 flex flex-wrap gap-3 text-sm">
            <Link href="/strategy/visibility?view=product" className="text-violet-700 hover:underline">
              产品详情 →
            </Link>
            <Link href="/strategy/scene-graph" className="text-violet-700 hover:underline">
              场景图谱 →
            </Link>
          </div>
        </LayerSection>
      </div>

      <LayerSection title="④ 优化策略" subtitle={optimization.market_summary}>
        <div className="grid gap-4 md:grid-cols-3">
          {optimization.top_platform && (
            <div className="rounded-md bg-violet-50 p-4">
              <p className="text-xs text-gray-500">平台优先</p>
              <p className="text-lg font-semibold">{optimization.top_platform.label}</p>
              <p className="text-sm text-violet-700">推荐分 {optimization.top_platform.score}</p>
            </div>
          )}
          <div className="md:col-span-2">
            <p className="mb-2 text-xs font-medium text-gray-500">TOP 高优先级场景</p>
            <ul className="space-y-2">
              {optimization.priority_scenes.length === 0 ? (
                <li className="text-sm text-gray-400">暂无场景数据</li>
              ) : (
                optimization.priority_scenes.map((s) => (
                  <li key={s.scene_name} className="flex items-center justify-between text-sm">
                    <span>{s.scene_name}</span>
                    <GapPriorityBadge priority={s.gap_priority} />
                  </li>
                ))
              )}
            </ul>
          </div>
        </div>
        {optimization.insights[0] && (
          <p className="mt-3 text-sm text-gray-600">
            {optimization.insights[0].title}：{optimization.insights[0].body}
          </p>
        )}
        <div className="mt-3 flex flex-wrap gap-3 text-sm">
          <Link href="/strategy/optimization" className="text-violet-700 hover:underline">
            优化策略 →
          </Link>
          <Link href="/strategy/difficulty" className="text-violet-700 hover:underline">
            难度评估 →
          </Link>
          <Link href="/strategy/reports" className="text-violet-700 hover:underline">
            诊断报告 →
          </Link>
        </div>
      </LayerSection>

      <LayerSection title="⑤ 难度评估">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <AivisKpiCard label="监管合规" value={`${difficulty.regulatory_compliance}/5`} />
          <AivisKpiCard label="市场竞争" value={`${difficulty.market_competition}/5`} tone="cyan" />
          <AivisKpiCard label="实体基础" value={`${difficulty.entity_foundation}/5`} tone="amber" />
          <AivisKpiCard label="综合难度" value={`${difficulty.overall_score}/5`} />
        </div>
      </LayerSection>

      {(latestLift || remediations.length > 0 || onProcessDue) && (
        <section className={`${surfaceCardClass} p-5`}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-base font-semibold text-gray-900">Theme 补缺 Lift 闭环</h2>
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
                [{r.status}] {r.theme_title || r.scene_name || r.scene_id}
                {r.theme_id ? ` · Theme #${r.theme_id}` : ""}
                {r.delta_top3_pp != null
                  ? ` · Top3 ${r.baseline_top3_pct ?? "—"}% → Δ ${r.delta_top3_pp}pp`
                  : ` · 基线 ${r.baseline_visibility_pct ?? "—"}%${
                      r.delta_visibility_pct != null ? ` → Δ ${r.delta_visibility_pct}pp` : ""
                    }`}
              </li>
            ))}
          </ul>
          <Link href="/production/themes" className="mt-3 inline-block text-sm text-blue-600 hover:underline">
            去主题包确认 / 启生产 →
          </Link>
        </section>
      )}

      {(geoEval || techBrand || alignment) && (
        <details className={`${surfaceCardClass} p-5`}>
          <summary className="cursor-pointer text-base font-semibold text-gray-900">基建健康（折叠）</summary>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <InfraCard
              label="GEO 仿真通过率"
              value={passRate == null ? "—" : `${passRate}%`}
              sub={geoEval ? `通过 ${geoEval.passed} · 失败 ${geoEval.failed}` : "未拉取"}
            />
            <InfraCard
              label="GEOweb 对齐"
              value={alignment ? `${alignment.alignment_pct}%` : "—"}
              sub={alignment ? `${alignment.matched_count}/${pageCount} 页` : "未拉取"}
            />
            <InfraCard
              label={zh.strategy.techBrand.p0Coverage}
              value={techBrand ? `${techBrand.p0_ready}/${techBrand.p0_total}` : "—"}
              sub={techBrand ? `${techBrand.p0_coverage_pct}%` : "—"}
            />
            <InfraCard
              label={zh.strategy.techBrand.assets}
              value={techBrand ? String(techBrand.total_assets) : "—"}
              sub={
                techBrand && techBrand.needs_update_assets > 0
                  ? `${techBrand.needs_update_assets} 需更新`
                  : "—"
              }
            />
          </div>
          <div className="mt-4 flex flex-wrap gap-3 border-t border-slate-100 pt-4 text-sm">
            <Link href="/production/geo-eval" className="text-blue-600 hover:underline">
              GEO 门禁（内容生产）
            </Link>
            <Link href="/production/tech-assets" className="text-blue-600 hover:underline">
              技术 IP 资产
            </Link>
            <Link href="/operations/analytics" className="text-blue-600 hover:underline">
              运营数据
            </Link>
          </div>
        </details>
      )}

      {data.latest_report && (
        <LayerSection title="最新诊断报告">
          <p className="text-sm font-medium">{data.latest_report.title}</p>
          <Link href="/strategy/reports" className="mt-2 inline-block text-sm text-violet-700 hover:underline">
            查看全部报告 →
          </Link>
        </LayerSection>
      )}
    </div>
  );
}

function InfraCard({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="rounded-md border border-slate-100 bg-slate-50/60 p-4">
      <p className="text-xs font-medium text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
      <p className="text-xs text-gray-500">{sub}</p>
    </div>
  );
}
