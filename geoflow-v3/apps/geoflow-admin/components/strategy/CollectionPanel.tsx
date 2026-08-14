"use client";

import Link from "next/link";
import { useState } from "react";
import { apiPost, getToken } from "@/lib/api-client";
import type { CollectionPanel as CollectionPanelData, MonitorRun } from "@/lib/strategy-types";
import { ProbeSettingsForm } from "./ProbeSettingsForm";
import { AivisKpiCard, LayerSection, PlatformBadge } from "./shared/AivisPrimitives";

const PROBE_MODE_LABEL: Record<string, string> = {
  corpus: "语料",
  llm: "LLM 模拟",
  api: "真实 API",
};

function RunStatusBadge({ status }: { status: string }) {
  const cls =
    status === "completed"
      ? "bg-emerald-50 text-emerald-700"
      : status === "running"
        ? "bg-amber-50 text-amber-700"
        : "bg-gray-100 text-gray-600";
  const label = status === "completed" ? "已完成" : status === "running" ? "进行中" : status;
  return <span className={`rounded px-1.5 py-0.5 text-xs ${cls}`}>{label}</span>;
}

export function CollectionPanel({
  data,
  onScan,
  onCendScan,
  onRefresh,
  scanning,
  scanStatus,
  cendScanning,
}: {
  data: CollectionPanelData;
  onScan: (scanType: "daily" | "market") => void;
  onCendScan?: () => void;
  onRefresh?: () => void;
  scanning: boolean;
  scanStatus?: string;
  cendScanning?: boolean;
}) {
  const [seeding, setSeeding] = useState(false);
  const [seedMsg, setSeedMsg] = useState("");

  const window =
    data.collection_window.period_start && data.collection_window.period_end
      ? `${data.collection_window.period_start} ~ ${data.collection_window.period_end}`
      : "—";

  const nextScan = data.next_scan;
  const probeMode = data.probe_settings?.probe_mode ?? nextScan?.probe_mode ?? "corpus";
  const brandZero = data.question_stats.brand_questions === 0;

  async function seedBrandQuestions() {
    const t = getToken();
    if (!t) return;
    setSeeding(true);
    setSeedMsg("");
    try {
      const res = await apiPost<{ created: number; skipped: number }>(
        "/api/admin/strategy/monitor/questions/seed-brand",
        t,
      );
      setSeedMsg(`已补 ${res.created} 条品牌题${res.skipped ? `，跳过 ${res.skipped} 条重复` : ""}`);
      onRefresh?.();
    } catch {
      setSeedMsg("补题失败，请检查探针设置中的品牌名");
    } finally {
      setSeeding(false);
    }
  }

  return (
    <div className="space-y-6">
      {brandZero && (
        <div className="rounded-lg border border-amber-200 bg-amber-50/60 px-4 py-3 text-sm text-amber-900">
          当前无品牌类探针，品牌可见性分析将无数据。
          <button
            type="button"
            disabled={seeding}
            onClick={seedBrandQuestions}
            className="ml-2 text-violet-700 underline disabled:opacity-50"
          >
            {seeding ? "生成中…" : "一键补品牌题"}
          </button>
          {seedMsg && <span className="ml-2 text-xs">{seedMsg}</span>}
        </div>
      )}

      <LayerSection
        title="采集概况"
        subtitle={`时间窗口：${window} · 模式：${PROBE_MODE_LABEL[probeMode] ?? probeMode}${data.probe_settings?.ai_mock_mode ? " · Mock" : ""}`}
      >
        <div className="mb-3">
          <p className="mb-2 text-xs font-medium text-gray-500">下次扫描预估（每平台 × 有效问题数）</p>
          <div className="flex flex-wrap gap-2">
            {(data.platforms_next ?? nextScan?.platforms ?? []).map((p) => (
              <span
                key={p.platform}
                className="inline-flex items-center gap-1 rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1 text-xs text-cyan-900"
              >
                {p.label}
                <span className="text-cyan-600">({p.estimate})</span>
              </span>
            ))}
            {nextScan && (
              <span className="self-center text-xs text-gray-500">
                共 {nextScan.effective_questions}/{nextScan.active_questions} 题（上限 {nextScan.scan_limit}）→{" "}
                {nextScan.total_probes_estimated} 探针
              </span>
            )}
          </div>
        </div>

        <div className="mb-4">
          <p className="mb-2 text-xs font-medium text-gray-500">历史累计探针（全库）</p>
          <div className="flex flex-wrap gap-2">
            {data.platforms.map((p) => (
              <PlatformBadge key={p.platform} platform={p.platform} count={p.probe_count} />
            ))}
          </div>
        </div>

        {data.engine_distribution && data.engine_distribution.length > 0 && (
          <p className="mb-4 text-xs text-gray-500">
            最近扫描引擎：
            {data.engine_distribution.map((e) => `${e.label} ${e.count}`).join(" · ")}
          </p>
        )}

        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          <AivisKpiCard
            label="品牌问题"
            value={String(data.question_stats.brand_questions)}
            sub={`预估 ${data.question_stats.brand_probes_estimated} 次`}
          />
          <AivisKpiCard
            label="产品问题"
            value={String(data.question_stats.product_questions)}
            sub={`预估 ${data.question_stats.product_probes_estimated} 次`}
            tone="cyan"
          />
          <AivisKpiCard
            label="竞品问题"
            value={String(data.question_stats.competitor_questions)}
            sub={`预估 ${data.question_stats.competitor_probes_estimated ?? 0} 次`}
          />
          <AivisKpiCard
            label="下次探针"
            value={String(data.question_stats.total_probes_estimated ?? nextScan?.total_probes_estimated ?? 0)}
            tone="amber"
          />
          <AivisKpiCard label="历史探针" value={String(data.probe_count)} sub={`${data.platform_count} 平台`} />
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={scanning}
            onClick={() => onScan("daily")}
            className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            {scanning ? scanStatus || "扫描中…" : "全量扫描 (daily)"}
          </button>
          <button
            type="button"
            disabled={scanning}
            onClick={() => onScan("market")}
            className="rounded-md border border-violet-400 px-4 py-2 text-sm text-violet-700 disabled:opacity-50"
          >
            竞品扫描 (market)
          </button>
          <button
            type="button"
            disabled={scanning || cendScanning || !onCendScan}
            onClick={() => onCendScan?.()}
            className="rounded-md border border-amber-400 bg-amber-50 px-4 py-2 text-sm text-amber-900 disabled:opacity-50"
            title="辅轨 cend_sample：思考链路 / 资料链 / 结构化排名；不覆盖 open_api KPI"
          >
            {cendScanning ? "C端金标扫描中…" : "C端金标扫描"}
          </button>
          <Link href="/strategy/probes?view=questions" className="rounded-md border border-violet-300 px-4 py-2 text-sm text-violet-700">
            问题库
          </Link>
          <Link href="/strategy/visibility?view=brand" className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700">
            品牌分析
          </Link>
          <Link href="/strategy/visibility?view=product" className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700">
            产品分析
          </Link>
        </div>

        {data.latest_run && (
          <p className="mt-3 text-xs text-gray-500">
            最近任务 #{data.latest_run.id}{" "}
            <RunStatusBadge status={scanning && data.latest_run.status === "running" ? "running" : data.latest_run.status} />
            {data.latest_run.probe_count != null && ` · ${data.latest_run.probe_count} 探针`}
          </p>
        )}
      </LayerSection>

      {data.recent_alerts && data.recent_alerts.length > 0 && (
        <LayerSection title="监控告警" subtitle="最近 5 条">
          <ul className="space-y-2 text-sm">
            {data.recent_alerts.map((a) => (
              <li key={a.id} className="rounded-md bg-red-50/50 px-3 py-2 text-red-900">
                <span className="text-xs text-red-600">{a.alert_type}</span>
                <p>{a.message}</p>
              </li>
            ))}
          </ul>
        </LayerSection>
      )}

      <ProbeSettingsForm onSaved={onRefresh} />

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
                  <td className="max-w-[8rem] truncate px-3 py-2 text-xs">{run.platform}</td>
                  <td className="px-3 py-2">{run.question_count}</td>
                  <td className="px-3 py-2">{run.probe_count ?? "—"}</td>
                  <td className="px-3 py-2">
                    <RunStatusBadge status={run.status} />
                  </td>
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
