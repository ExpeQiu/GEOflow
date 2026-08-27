"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CollectionPanel } from "./CollectionPanel";
import { CrossTrackPanel } from "./CrossTrackPanel";
import { GoldLabelsPanel } from "./GoldLabelsPanel";
import { ProbeApiConfigPanel } from "./ProbeApiConfigPanel";
import { ProbeSettingsForm } from "./ProbeSettingsForm";
import { QuestionBankPanel } from "./QuestionBankPanel";
import type {
  CollectionPanel as CollectionPanelData,
  CompetitorBrand,
  MonitorRun,
  MonitorScene,
  QueryTemplate,
} from "@/lib/strategy-types";

type ProbeView = "scan" | "questions" | "cross" | "gold" | "settings" | "api-config";

const VALID_VIEWS: ProbeView[] = ["scan", "questions", "cross", "gold", "settings", "api-config"];

function readViewFromUrl(): ProbeView {
  if (typeof window === "undefined") return "scan";
  const v = new URLSearchParams(window.location.search).get("view");
  return VALID_VIEWS.includes(v as ProbeView) ? (v as ProbeView) : "scan";
}

function writeViewToUrl(next: ProbeView) {
  const url = new URL(window.location.href);
  if (next === "scan") url.searchParams.delete("view");
  else url.searchParams.set("view", next);
  window.history.replaceState(null, "", `${url.pathname}${url.search}`);
}

export function ProbesHub({
  collection,
  onScan,
  onCendScan,
  onFrameworkScan,
  onCitationScan,
  onRefreshCollection,
  scanning,
  scanStatus,
  cendScanning,
  frameworkScanning,
  citationScanning,
  scenes,
  competitors,
  brandName,
  templates,
  recentRuns,
  onCreateQuestion,
  onUpdateQuestion,
  onDeleteQuestion,
  onRefreshQuestions,
}: {
  collection: CollectionPanelData | null;
  onScan: (scanType?: "daily" | "market") => void;
  onCendScan: () => void;
  onFrameworkScan: () => void;
  onCitationScan: () => void;
  onRefreshCollection: () => Promise<void>;
  scanning: boolean;
  scanStatus: string;
  cendScanning: boolean;
  frameworkScanning: boolean;
  citationScanning: boolean;
  scenes: MonitorScene[];
  competitors: CompetitorBrand[];
  brandName: string;
  templates: QueryTemplate[];
  recentRuns: MonitorRun[];
  onCreateQuestion: (body: Record<string, unknown>) => Promise<void>;
  onUpdateQuestion: (id: number, body: Record<string, unknown>) => Promise<void>;
  onDeleteQuestion: (id: number) => Promise<void>;
  onRefreshQuestions: () => void;
}) {
  const [view, setView] = useState<ProbeView>("scan");

  useEffect(() => {
    setView(readViewFromUrl());
    const onPop = () => setView(readViewFromUrl());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const selectView = useCallback((next: ProbeView) => {
    setView(next);
    writeViewToUrl(next);
  }, []);

  const primaryTabs = useMemo(
    () =>
      [
        { key: "scan" as const, label: "采集工作台" },
        { key: "questions" as const, label: "监控问题库" },
      ] as const,
    [],
  );
  const labTabs = useMemo(
    () =>
      [
        { key: "cross" as const, label: "交叉判定" },
        { key: "gold" as const, label: "金标对照" },
        { key: "settings" as const, label: "探针设置" },
        { key: "api-config" as const, label: "API 配置" },
      ] as const,
    [],
  );
  const labOpen = view === "cross" || view === "gold" || view === "settings" || view === "api-config";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 border-b border-gray-100 pb-3">
        {primaryTabs.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => selectView(t.key)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${
              view === t.key ? "bg-violet-100 text-violet-800" : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            {t.label}
          </button>
        ))}
        <span className="mx-1 hidden h-4 w-px bg-gray-200 sm:inline" aria-hidden="true" />
        <span className="text-[11px] font-medium uppercase tracking-wide text-gray-400">实验室</span>
        {labTabs.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => selectView(t.key)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${
              view === t.key ? "bg-violet-100 text-violet-800" : "text-gray-500 hover:bg-gray-50"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {labOpen && (
        <p className="text-xs text-gray-500">实验室入口不影响北极星 KPI；日常请用采集工作台的 open_api 日扫。</p>
      )}

      {view === "scan" && collection && (
        <CollectionPanel
          data={collection}
          onScan={onScan}
          onCendScan={onCendScan}
          onFrameworkScan={onFrameworkScan}
          onCitationScan={onCitationScan}
          onRefresh={onRefreshCollection}
          scanning={scanning}
          scanStatus={scanStatus}
          cendScanning={cendScanning}
          frameworkScanning={frameworkScanning}
          citationScanning={citationScanning}
        />
      )}
      {view === "scan" && !collection && <p className="text-sm text-gray-400">加载采集数据…</p>}

      {view === "questions" && (
        <QuestionBankPanel
          scenes={scenes}
          competitors={competitors}
          brandName={brandName}
          templates={templates}
          recentRuns={recentRuns}
          onCreate={onCreateQuestion}
          onUpdate={onUpdateQuestion}
          onDelete={onDeleteQuestion}
          onRefresh={onRefreshQuestions}
        />
      )}

      {view === "cross" && <CrossTrackPanel />}

      {view === "gold" && <GoldLabelsPanel />}

      {view === "settings" && <ProbeSettingsForm onSaved={onRefreshCollection} />}

      {view === "api-config" && <ProbeApiConfigPanel />}
    </div>
  );
}
