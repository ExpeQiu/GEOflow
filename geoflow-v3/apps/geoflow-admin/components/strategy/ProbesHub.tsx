"use client";

import { useEffect, useMemo, useState } from "react";
import { CollectionPanel } from "./CollectionPanel";
import { QuestionBankPanel } from "./QuestionBankPanel";
import type {
  CollectionPanel as CollectionPanelData,
  CompetitorBrand,
  MonitorRun,
  MonitorScene,
  QueryTemplate,
} from "@/lib/strategy-types";

type ProbeView = "scan" | "questions";

export function ProbesHub({
  collection,
  onScan,
  onCendScan,
  onRefreshCollection,
  scanning,
  scanStatus,
  cendScanning,
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
  onRefreshCollection: () => Promise<void>;
  scanning: boolean;
  scanStatus: string;
  cendScanning: boolean;
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
    const v = new URLSearchParams(window.location.search).get("view");
    if (v === "questions") setView("questions");
  }, []);

  const tabs = useMemo(
    () =>
      [
        { key: "scan" as const, label: "数据采集" },
        { key: "questions" as const, label: "监控问题库" },
      ] as const,
    [],
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 border-b border-gray-100 pb-3">
        {tabs.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setView(t.key)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${
              view === t.key ? "bg-violet-100 text-violet-800" : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {view === "scan" && collection && (
        <CollectionPanel
          data={collection}
          onScan={onScan}
          onCendScan={onCendScan}
          onRefresh={onRefreshCollection}
          scanning={scanning}
          scanStatus={scanStatus}
          cendScanning={cendScanning}
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
    </div>
  );
}
