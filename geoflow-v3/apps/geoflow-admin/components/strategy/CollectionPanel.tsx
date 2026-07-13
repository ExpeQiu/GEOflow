"use client";

import Link from "next/link";
import type { CollectionPanel as CollectionPanelData, MonitorRun } from "@/lib/strategy-types";
import { ProbeSettingsForm } from "./ProbeSettingsForm";
import { AivisKpiCard, LayerSection, PlatformBadge } from "./shared/AivisPrimitives";

export function CollectionPanel({
  data,
  onScan,
  scanning,
}: {
  data: CollectionPanelData;
  onScan: () => void;
  scanning: boolean;
}) {
  const window =
    data.collection_window.period_start && data.collection_window.period_end
      ? `${data.collection_window.period_start} ~ ${data.collection_window.period_end}`
      : "—";

  return (
    <div className="space-y-6">
      <LayerSection title="采集概况" subtitle={`时间窗口：${window}`}>
        <div className="mb-4 flex flex-wrap gap-2">
          {data.platforms.map((p) => (
            <PlatformBadge key={p.platform} platform={p.platform} count={p.probe_count} />
          ))}
        </div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <AivisKpiCard label="品牌问题" value={String(data.question_stats.brand_questions)} sub={`预估 ${data.question_stats.brand_probes_estimated} 次`} />
          <AivisKpiCard label="产品问题" value={String(data.question_stats.product_questions)} sub={`预估 ${data.question_stats.product_probes_estimated} 次`} tone="cyan" />
          <AivisKpiCard label="探针总数" value={String(data.probe_count)} tone="amber" />
          <AivisKpiCard label="平台数" value={String(data.platform_count)} />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={scanning}
            onClick={onScan}
            className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            {scanning ? "扫描中…" : "启动全量扫描"}
          </button>
          <Link href="/strategy/question-bank" className="rounded-md border border-violet-300 px-4 py-2 text-sm text-violet-700">
            问题库
          </Link>
        </div>
      </LayerSection>

      <ProbeSettingsForm />

      <LayerSection title="最近扫描任务">
        {data.recent_runs.length === 0 ? (
          <p className="text-sm text-gray-400">暂无扫描记录</p>
        ) : (
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500">
                {["ID", "平台", "问题数", "探针数", "状态", "完成时间"].map((h) => (
                  <th key={h} className="px-3 py-2">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.recent_runs.map((run: MonitorRun) => (
                <tr key={run.id} className="border-t border-gray-100">
                  <td className="px-3 py-2">
                    <Link href={`/strategy/monitor/runs/${run.id}`} className="text-violet-600 hover:underline">
                      #{run.id}
                    </Link>
                  </td>
                  <td className="px-3 py-2">{run.platform}</td>
                  <td className="px-3 py-2">{run.question_count}</td>
                  <td className="px-3 py-2">{run.probe_count ?? "—"}</td>
                  <td className="px-3 py-2">{run.status}</td>
                  <td className="px-3 py-2 text-xs text-gray-500">{run.completed_at ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </LayerSection>
    </div>
  );
}
