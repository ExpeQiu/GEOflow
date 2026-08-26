"use client";

import Link from "next/link";
import { type ReactNode, useState } from "react";
import { apiPost, getToken } from "@/lib/api-client";
import type { CollectionPanel as CollectionPanelData, MonitorRun, SchemeCard } from "@/lib/strategy-types";
import { AivisKpiCard, LayerSection, PlatformBadge, SchemeBadge } from "./shared/AivisPrimitives";

const PROBE_MODE_LABEL: Record<string, string> = {
  corpus: "语料",
  llm: "LLM 模拟",
  api: "真实 API",
};

const FALLBACK_CARDS: SchemeCard[] = [
  {
    scheme: "open_api",
    tracks: ["C"],
    label: "日常 C 轨",
    kpi_note: "计入 visibility_open_api",
    covers_kpi: true,
    probe_count: 0,
    questions_estimated: 0,
  },
  {
    scheme: "framework_api",
    tracks: ["A", "C"],
    label: "A 框架轨",
    kpi_note: "明文 CoT，不覆盖北极星",
    covers_kpi: false,
    probe_count: 0,
    questions_estimated: 0,
  },
  {
    scheme: "citation_grounded",
    tracks: ["B", "C"],
    label: "B 引用轨",
    kpi_note: "答文 URL L1，不覆盖北极星",
    covers_kpi: false,
    probe_count: 0,
    questions_estimated: 0,
  },
  {
    scheme: "cend_sample",
    tracks: ["B", "C"],
    label: "C 端金标",
    kpi_note: "资料链 L2，不覆盖北极星",
    covers_kpi: false,
    probe_count: 0,
    questions_estimated: 0,
  },
];

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

function formatRunTime(iso: string | null | undefined) {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export function CollectionPanel({
  data,
  onScan,
  onCendScan,
  onFrameworkScan,
  onCitationScan,
  onRefresh,
  scanning,
  scanStatus,
  cendScanning,
  frameworkScanning,
  citationScanning,
}: {
  data: CollectionPanelData;
  onScan: (scanType: "daily" | "market") => void;
  onCendScan?: () => void;
  onFrameworkScan?: () => void;
  onCitationScan?: () => void;
  onRefresh?: () => void;
  scanning: boolean;
  scanStatus?: string;
  cendScanning?: boolean;
  frameworkScanning?: boolean;
  citationScanning?: boolean;
}) {
  const [seeding, setSeeding] = useState(false);
  const [seedMsg, setSeedMsg] = useState("");

  const window =
    data.collection_window.period_start && data.collection_window.period_end
      ? `${data.collection_window.period_start} ~ ${data.collection_window.period_end}`
      : "—";

  const nextScan = data.next_scan;
  const probeMode = data.probe_settings?.probe_mode ?? nextScan?.probe_mode ?? "corpus";
  const scanPlatforms =
    (data.probe_settings?.platforms ?? []).filter(Boolean).length > 0
      ? (data.probe_settings?.platforms ?? []).filter(Boolean)
      : (nextScan?.platforms ?? []).map((p) => p.platform).filter(Boolean);
  const scanPlatformHint = scanPlatforms.length ? `平台 ${scanPlatforms.join("/")}` : "未配置平台";
  const brandZero = data.question_stats.brand_questions === 0;
  const busy = scanning || Boolean(cendScanning) || Boolean(frameworkScanning) || Boolean(citationScanning);
  const cards = data.scheme_cards?.length ? data.scheme_cards : FALLBACK_CARDS;

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

  function cardByScheme(scheme: string) {
    return cards.find((c) => c.scheme === scheme) ?? FALLBACK_CARDS.find((c) => c.scheme === scheme)!;
  }

  const daily = cardByScheme("open_api");
  const framework = cardByScheme("framework_api");
  const citation = cardByScheme("citation_grounded");
  const cend = cardByScheme("cend_sample");

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
        title="open_api 日扫"
        subtitle={`时间窗口：${window} · 模式：${PROBE_MODE_LABEL[probeMode] ?? probeMode}${data.probe_settings?.ai_mock_mode ? " · Mock" : ""} · 计入北极星 Top3`}
      >
        <SchemeScanCard
          card={daily}
          hint="日扫 priority≥80；竞品扫描为 market 批次"
          busy={busy}
          scanning={scanning}
          scanLabel={scanning ? scanStatus || "扫描中…" : undefined}
          actions={
            <>
              <button
                type="button"
                disabled={busy}
                onClick={() => onScan("daily")}
                className="rounded-md bg-violet-600 px-3 py-1.5 text-sm text-white disabled:opacity-50"
              >
                {scanning ? scanStatus || "扫描中…" : "日扫 (daily)"}
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => onScan("market")}
                className="rounded-md border border-violet-400 px-3 py-1.5 text-sm text-violet-700 disabled:opacity-50"
              >
                竞品 (market)
              </button>
            </>
          }
        />
      </LayerSection>

      <details className="rounded-lg border border-gray-200 bg-white p-4">
        <summary className="cursor-pointer text-sm font-medium text-gray-700">
          实验室扫描（框架 / 引用 / C 端，不覆盖北极星）
        </summary>
        <p className="mt-2 mb-3 text-xs text-gray-500">{scanPlatformHint} · 辅轨结果只进挖掘与金标，不改 visibility_open_api</p>
        <div className="grid gap-3 md:grid-cols-3">
          <SchemeScanCard
            card={framework}
            hint="种子题 ≤12，明文思维链 A+C"
            busy={busy}
            scanning={Boolean(frameworkScanning)}
            actions={
              <button
                type="button"
                disabled={busy || !onFrameworkScan || !scanPlatforms.length}
                onClick={() => onFrameworkScan?.()}
                className="rounded-md border border-cyan-400 bg-cyan-50 px-3 py-1.5 text-sm text-cyan-900 disabled:opacity-50"
              >
                {frameworkScanning ? "框架轨扫描中…" : "框架轨扫描"}
              </button>
            }
          />
          <SchemeScanCard
            card={citation}
            hint="答文抽 URL；原生搜索仅 Kimi+CITATION_WEB_SEARCH"
            busy={busy}
            scanning={Boolean(citationScanning)}
            actions={
              <button
                type="button"
                disabled={busy || !onCitationScan || !scanPlatforms.length}
                onClick={() => onCitationScan?.()}
                className="rounded-md border border-emerald-400 bg-emerald-50 px-3 py-1.5 text-sm text-emerald-900 disabled:opacity-50"
              >
                {citationScanning ? "引用轨扫描中…" : "引用轨扫描（B-L1）"}
              </button>
            }
          />
          <SchemeScanCard
            card={cend}
            hint="默认 ≤5 题，硬顶 20；需持久 Profile"
            busy={busy}
            scanning={Boolean(cendScanning)}
            actions={
              <button
                type="button"
                disabled={busy || !onCendScan}
                onClick={() => onCendScan?.()}
                className="rounded-md border border-amber-400 bg-amber-50 px-3 py-1.5 text-sm text-amber-900 disabled:opacity-50"
              >
                {cendScanning ? "C端金标扫描中…" : "C端金标扫描"}
              </button>
            }
          />
        </div>
      </details>

      <LayerSection
        title="采集概况"
        subtitle={nextScan ? `下次日扫 ${nextScan.effective_questions}/${nextScan.active_questions} 题（上限 ${nextScan.scan_limit}）` : undefined}
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
              <span className="self-center text-xs text-gray-500">→ {nextScan.total_probes_estimated} 探针</span>
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

      <LayerSection title="最近扫描任务">
        {data.recent_runs.length === 0 ? (
          <p className="text-sm text-gray-400">暂无扫描记录</p>
        ) : (
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500">
                {["ID", "方案", "平台", "问题数", "探针数", "状态", "完成时间"].map((h) => (
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
                  <td className="px-3 py-2">
                    <SchemeBadge scheme={run.scheme || "open_api"} />
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

function SchemeScanCard({
  card,
  hint,
  busy,
  scanning,
  scanLabel,
  actions,
}: {
  card: SchemeCard;
  hint: string;
  busy: boolean;
  scanning: boolean;
  scanLabel?: string;
  actions: ReactNode;
}) {
  const run = card.latest_run;
  return (
    <div className={`rounded-lg border p-4 ${card.covers_kpi ? "border-violet-200 bg-violet-50/40" : "border-gray-200 bg-white"}`}>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <h4 className="text-sm font-semibold text-gray-900">{card.label}</h4>
        <SchemeBadge scheme={card.scheme} />
        <span className="text-[11px] text-gray-500">tracks {card.tracks.join("+")}</span>
      </div>
      <p className="mb-3 text-xs text-gray-600">
        {card.kpi_note}
        {hint ? ` · ${hint}` : ""}
      </p>
      <div className="mb-3 grid grid-cols-2 gap-2 text-xs text-gray-600">
        <div>
          <p className="text-gray-400">预估题量</p>
          <p className="text-sm font-medium text-gray-900">{card.questions_estimated}</p>
        </div>
        <div>
          <p className="text-gray-400">历史探针</p>
          <p className="text-sm font-medium text-gray-900">{card.probe_count}</p>
        </div>
        <div className="col-span-2">
          <p className="text-gray-400">上次运行</p>
          {run ? (
            <p className="text-sm text-gray-800">
              <Link href={`/strategy/monitor/runs/${run.id}`} className="text-violet-700 hover:underline">
                #{run.id}
              </Link>{" "}
              <RunStatusBadge status={scanning && run.status === "running" ? "running" : run.status} />
              {run.probe_count != null ? ` · ${run.probe_count} 探针` : ""}
              <span className="ml-1 text-gray-500">{formatRunTime(run.completed_at)}</span>
            </p>
          ) : (
            <p className="text-sm text-gray-400">尚未运行</p>
          )}
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {actions}
        {scanLabel && busy && scanning ? <span className="self-center text-xs text-gray-500">{scanLabel}</span> : null}
      </div>
    </div>
  );
}
