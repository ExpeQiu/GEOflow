"use client";

import { useState } from "react";
import { zh } from "@/lib/i18n/zh";
import type { AnalyticsSnapshot, MonitorInsight, MonitorSnapshot, TrendPoint } from "@/lib/strategy-types";
import { surfaceCardClass } from "./shared/AivisPrimitives";

type AnalyticsTab = "overview" | "insights" | "trends";

export function AnalyticsPanel({
  snapshot,
  publicationTrend,
  taskHealth,
  aiUsage,
  topArticles,
  insights = [],
  visibilityTrends = [],
  themes = [],
}: {
  snapshot: AnalyticsSnapshot;
  publicationTrend: TrendPoint[];
  taskHealth: { running: number; pending: number; failed: number };
  aiUsage: { used_today: number; total_used: number; active_models: number };
  topArticles: { id: number; title: string; view_count: number; status: string }[];
  insights?: MonitorInsight[];
  visibilityTrends?: MonitorSnapshot[];
  themes?: Array<{
    theme_id: number;
    title: string;
    status: string;
    article_count: number;
    gate_pass_rate_pct: number;
    distribution_success_rate_pct: number;
  }>;
}) {
  const [tab, setTab] = useState<AnalyticsTab>("overview");
  const maxTrend = Math.max(1, ...publicationTrend.map((p) => p.count));

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">{zh.strategy.analytics.heading}</h2>
        <p className="mt-1 text-sm text-gray-600">内容产量 · 任务健康 · 访问与可见性趋势</p>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-gray-100 pb-2">
        {([
          ["overview", "内容概览"],
          ["insights", "洞察"],
          ["trends", "趋势"],
        ] as const).map(([k, label]) => (
          <button
            key={k}
            type="button"
            onClick={() => setTab(k)}
            className={`rounded-md px-3 py-1.5 text-sm ${tab === k ? "bg-violet-600 text-white" : "bg-gray-100 text-gray-700"}`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Stat label={zh.strategy.analytics.totalArticles} value={snapshot.total_articles} />
            <Stat label={zh.strategy.analytics.published} value={snapshot.published_articles} />
            <Stat label={zh.strategy.analytics.totalViews} value={snapshot.total_views} />
            <Stat label={zh.strategy.analytics.activeTasks} value={snapshot.active_tasks} />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <section className={`${surfaceCardClass} p-5`}>
              <h3 className="text-sm font-semibold text-gray-900">{zh.strategy.analytics.publicationTrend}</h3>
              <div className="mt-4 flex h-32 items-end gap-2">
                {publicationTrend.length === 0 ? (
                  <p className="text-sm text-gray-400">暂无数据</p>
                ) : (
                  publicationTrend.map((p) => (
                    <div key={p.date} className="flex flex-1 flex-col items-center gap-1">
                      <div
                        className="w-full rounded-t bg-violet-500"
                        style={{ height: `${(p.count / maxTrend) * 100}%`, minHeight: p.count ? 4 : 0 }}
                      />
                      <span className="text-[10px] text-gray-400">{p.date.slice(5)}</span>
                    </div>
                  ))
                )}
              </div>
            </section>

            <section className={`${surfaceCardClass} p-5`}>
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

          <section className={`${surfaceCardClass} p-5`}>
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

          <section className={`${surfaceCardClass} p-5`}>
            <h3 className="text-sm font-semibold text-gray-900">Theme 产量与门禁</h3>
            <ul className="mt-4 divide-y divide-gray-100">
              {themes.length === 0 ? (
                <li className="py-4 text-sm text-gray-400">暂无主题包数据</li>
              ) : (
                themes.slice(0, 10).map((t) => (
                  <li key={t.theme_id} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
                    <span className="font-medium text-gray-900">{t.title}</span>
                    <span className="text-xs text-gray-500">
                      {t.status} · 文章 {t.article_count} · 门禁 {t.gate_pass_rate_pct}% · 分发 {t.distribution_success_rate_pct}%
                    </span>
                  </li>
                ))
              )}
            </ul>
          </section>
        </>
      )}

      {tab === "insights" && (
        <ul className="space-y-3">
          {insights.length === 0 ? (
            <li className={`${surfaceCardClass} p-6 text-sm text-gray-400`}>暂无洞察，执行全量扫描后自动生成</li>
          ) : (
            insights.map((i) => (
              <li key={i.id} className={`${surfaceCardClass} p-4`}>
                <p className="font-medium text-violet-900">{i.title}</p>
                <p className="mt-1 text-sm text-gray-600">{i.body}</p>
                {i.insight_type && <p className="mt-2 text-xs text-gray-400">{i.insight_type}</p>}
              </li>
            ))
          )}
        </ul>
      )}

      {tab === "trends" && (
        <div className={`overflow-x-auto ${surfaceCardClass} p-4`}>
          {visibilityTrends.length === 0 ? (
            <p className="text-sm text-gray-400">暂无可见性趋势，执行扫描后按日聚合</p>
          ) : (
            <table className="min-w-full text-sm">
              <thead>
                <tr>
                  {["日期", "可见性%", "加权排名", "好感度", "提及率"].map((h) => (
                    <th key={h} className="px-3 py-2 text-left text-xs text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibilityTrends.map((s) => (
                  <tr key={s.date} className="border-t border-gray-100">
                    <td className="px-3 py-2">{s.date}</td>
                    <td className="px-3 py-2">{s.visibility_pct}%</td>
                    <td className="px-3 py-2">{s.weighted_rank_score ?? "—"}</td>
                    <td className="px-3 py-2">{s.sentiment_score ?? "—"}</td>
                    <td className="px-3 py-2">{Math.round(s.mention_rate * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className={`${surfaceCardClass} p-4`}>
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
