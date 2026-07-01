"use client";

import { zh } from "@/lib/i18n/zh";
import type { MonitorKpis, MonitorQuestion } from "@/lib/strategy-types";

export function MonitorPanel({
  dashboard,
  questions,
  onScan,
  scanning,
}: {
  dashboard: MonitorKpis;
  questions: MonitorQuestion[];
  onScan: () => void;
  scanning: boolean;
}) {
  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-violet-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{zh.strategy.monitor.dashboardTitle}</h2>
            <p className="text-sm text-gray-500">{zh.strategy.monitor.dashboardSubtitle}</p>
          </div>
          <button
            type="button"
            disabled={scanning}
            onClick={onScan}
            className="rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50"
          >
            {zh.strategy.monitor.scanAll}
          </button>
        </div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Kpi label={zh.strategy.monitor.kpiQuestions} value={dashboard.question_count} tone="violet" />
          <Kpi label={zh.strategy.monitor.kpiProbes} value={dashboard.probe_count} />
          <Kpi label="平均排名" value={dashboard.avg_brand_rank ?? "—"} />
          <Kpi label="提及率" value={`${Math.round(dashboard.mention_rate * 100)}%`} />
        </div>
      </section>

      <section className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        <div className="border-b px-4 py-3 text-sm font-semibold text-gray-900">{zh.strategy.monitor.questionsTitle}</div>
        {questions.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-gray-500">{zh.strategy.monitor.emptyQuestions}</div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["问题", "优先级", "状态"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {questions.map((q) => (
                <tr key={q.id}>
                  <td className="px-4 py-3">{q.question_text}</td>
                  <td className="px-4 py-3">{q.priority}</td>
                  <td className="px-4 py-3">{q.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

function Kpi({ label, value, tone }: { label: string; value: string | number; tone?: "violet" }) {
  const cls = tone === "violet" ? "bg-violet-50" : "bg-gray-50";
  return (
    <div className={`rounded-md p-4 ${cls}`}>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
    </div>
  );
}
