import Link from "next/link";
import { zh } from "@/lib/i18n/zh";
import type { AnalyticsSnapshot, GeoEvalSummary, MonitorKpis, TechBrandMetrics } from "@/lib/strategy-types";

export function StrategyOverview({
  geoEval,
  techBrand,
  monitor,
  analytics,
}: {
  geoEval: GeoEvalSummary;
  techBrand: TechBrandMetrics;
  monitor: MonitorKpis;
  analytics: AnalyticsSnapshot;
}) {
  const passRate =
    geoEval.passed + geoEval.failed > 0
      ? Math.round((geoEval.passed / (geoEval.passed + geoEval.failed)) * 100)
      : 0;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <MiniCard
          label="GEO 通过率"
          value={`${passRate}%`}
          meta={`通过 ${geoEval.passed} · 失败 ${geoEval.failed}`}
          href="/strategy/geo-eval"
          tone="cyan"
        />
        <MiniCard
          label={zh.strategy.monitor.kpiQuestions}
          value={String(monitor.question_count)}
          meta={`探针 ${monitor.probe_count}`}
          href="/strategy/monitor"
          tone="violet"
        />
        <MiniCard
          label={zh.strategy.analytics.totalViews}
          value={String(analytics.total_views)}
          meta={`文章 ${analytics.total_articles}`}
          href="/strategy/analytics"
          tone="green"
        />
      </div>

      <TechBrandPanel metrics={techBrand} />
    </div>
  );
}

function TechBrandPanel({ metrics }: { metrics: TechBrandMetrics }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold text-gray-900">{zh.strategy.techBrand.title}</h2>
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label={zh.strategy.techBrand.p0Coverage} value={`${metrics.p0_ready}/${metrics.p0_total}`} sub={`${metrics.p0_coverage_pct}%`} tone="violet" />
        <MetricCard label={zh.strategy.techBrand.wikiCompliance} value={`${metrics.wiki_compliance_pct}%`} sub={`${metrics.wiki_articles} Wiki 页`} tone="emerald" />
        <MetricCard label={zh.strategy.techBrand.gwebSync} value={`${metrics.gweb_sync_rate_pct}%`} sub={`${metrics.gweb_sync_success}/${metrics.gweb_sync_total}`} tone="blue" />
        <MetricCard label={zh.strategy.techBrand.assets} value={String(metrics.total_assets)} sub={metrics.needs_update_assets > 0 ? `${metrics.needs_update_assets} 需更新` : "—"} tone="amber" />
      </div>
      <div className="mt-4 flex flex-wrap gap-3 border-t border-slate-100 pt-4 text-sm">
        <Link href="/production/tech-assets" className="text-blue-600 hover:underline">
          技术 IP 资产
        </Link>
        <Link href="/operations/tasks" className="text-blue-600 hover:underline">
          创建 Wiki 任务
        </Link>
      </div>
    </section>
  );
}

function MiniCard({
  label,
  value,
  meta,
  href,
  tone,
}: {
  label: string;
  value: string;
  meta: string;
  href: string;
  tone: "cyan" | "violet" | "green";
}) {
  const border = { cyan: "border-cyan-200 bg-cyan-50/60", violet: "border-violet-200 bg-violet-50/60", green: "border-emerald-200 bg-emerald-50/60" }[tone];
  const link = { cyan: "text-cyan-800", violet: "text-violet-800", green: "text-emerald-800" }[tone];
  return (
    <div className={`rounded-lg border p-5 ${border}`}>
      <p className="text-xs font-semibold uppercase text-gray-600">{label}</p>
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
  }[tone];
  return (
    <div className={`rounded-md border p-4 ${bg}`}>
      <p className="text-xs font-medium">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
      <p className="text-xs opacity-80">{sub}</p>
    </div>
  );
}
