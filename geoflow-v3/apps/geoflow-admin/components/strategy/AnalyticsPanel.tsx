import { zh } from "@/lib/i18n/zh";
import type { AnalyticsSnapshot, TrendPoint } from "@/lib/strategy-types";

export function AnalyticsPanel({
  snapshot,
  publicationTrend,
  taskHealth,
  aiUsage,
  topArticles,
}: {
  snapshot: AnalyticsSnapshot;
  publicationTrend: TrendPoint[];
  taskHealth: { running: number; pending: number; failed: number };
  aiUsage: { used_today: number; total_used: number; active_models: number };
  topArticles: { id: number; title: string; view_count: number; status: string }[];
}) {
  const maxTrend = Math.max(1, ...publicationTrend.map((p) => p.count));

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">{zh.strategy.analytics.heading}</h2>
        <p className="mt-1 text-sm text-gray-600">{zh.strategy.analytics.subtitle}</p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label={zh.strategy.analytics.totalArticles} value={snapshot.total_articles} />
        <Stat label={zh.strategy.analytics.published} value={snapshot.published_articles} />
        <Stat label={zh.strategy.analytics.totalViews} value={snapshot.total_views} />
        <Stat label={zh.strategy.analytics.activeTasks} value={snapshot.active_tasks} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-900">{zh.strategy.analytics.publicationTrend}</h3>
          <div className="mt-4 flex h-32 items-end gap-2">
            {publicationTrend.length === 0 ? (
              <p className="text-sm text-gray-400">暂无数据</p>
            ) : (
              publicationTrend.map((p) => (
                <div key={p.date} className="flex flex-1 flex-col items-center gap-1">
                  <div className="w-full rounded-t bg-violet-500" style={{ height: `${(p.count / maxTrend) * 100}%`, minHeight: p.count ? 4 : 0 }} />
                  <span className="text-[10px] text-gray-400">{p.date.slice(5)}</span>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-900">{zh.strategy.analytics.aiUsage}</h3>
          <dl className="mt-4 space-y-3 text-sm">
            <Row label="今日" value={aiUsage.used_today} />
            <Row label="累计" value={aiUsage.total_used} />
            <Row label="活跃模型" value={aiUsage.active_models} />
            <Row label="队列运行" value={taskHealth.running} />
            <Row label="队列失败" value={taskHealth.failed} tone="red" />
          </dl>
        </section>
      </div>

      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-900">{zh.strategy.analytics.topContent}</h3>
        <ul className="mt-4 divide-y divide-gray-100">
          {topArticles.length === 0 ? (
            <li className="py-4 text-sm text-gray-400">暂无数据</li>
          ) : (
            topArticles.map((a) => (
              <li key={a.id} className="flex items-center justify-between py-3 text-sm">
                <span className="line-clamp-1 font-medium text-gray-900">{a.title}</span>
                <span className="shrink-0 text-gray-500">{a.view_count} 次</span>
              </li>
            ))
          )}
        </ul>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
    </div>
  );
}

function Row({ label, value, tone }: { label: string; value: number; tone?: "red" }) {
  return (
    <div className="flex justify-between">
      <dt className="text-gray-500">{label}</dt>
      <dd className={tone === "red" ? "font-semibold text-red-600" : "font-semibold text-gray-900"}>{value}</dd>
    </div>
  );
}
