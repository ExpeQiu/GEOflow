"use client";

import { useState } from "react";
import { cn } from "@/lib/cn";
import { zh } from "@/lib/i18n/zh";
import type {
  EvalFailureRow,
  FailureTopN,
  GateConfig,
  GeoAlert,
  GeoEvalSummary,
  ProbeStandardsConfig,
  SimulateResult,
} from "@/lib/strategy-types";
import {
  GeoStandardsConfigPanel,
  type GateSavePayload,
  type ProbeSavePayload,
} from "./GeoStandardsConfigPanel";
import { GeoSimulatorPanel } from "./GeoSimulatorPanel";

type Block = "standards" | "simulator";

export function GeoEvalPanel({
  gate,
  probeStandards,
  summary,
  failureTopN,
  recentFailures,
  recentAlerts = [],
  onReevaluate,
  onBatchReevaluate,
  onSaveGate,
  onSaveProbeStandards,
  onSimulate,
  onApplyRecommendations,
  busyId,
  saving,
  simulating,
}: {
  gate: GateConfig;
  probeStandards?: ProbeStandardsConfig | null;
  summary: GeoEvalSummary;
  failureTopN: FailureTopN[];
  recentFailures: EvalFailureRow[];
  recentAlerts?: GeoAlert[];
  onReevaluate: (articleId: number) => void;
  onBatchReevaluate?: (articleIds: number[]) => void;
  onSaveGate?: (next: GateSavePayload) => Promise<void> | void;
  onSaveProbeStandards?: (next: ProbeSavePayload) => Promise<void> | void;
  onSimulate: (payload: {
    title: string;
    content: string;
    query?: string;
    keyword?: string;
    article_id?: number;
  }) => Promise<SimulateResult>;
  onApplyRecommendations?: (articleId: number) => Promise<void>;
  busyId: number | null;
  saving?: boolean;
  simulating?: boolean;
}) {
  const [block, setBlock] = useState<Block>("standards");

  const tabs: Array<{ key: Block; label: string }> = [
    { key: "standards", label: zh.strategy.geoEval.standardsBlockTitle },
    { key: "simulator", label: zh.strategy.geoEval.simulatorBlockTitle },
  ];

  return (
    <div>
      <nav className="mb-6 flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setBlock(tab.key)}
            className={cn(
              "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
              block === tab.key ? "bg-emerald-100 text-emerald-800" : "text-gray-600 hover:bg-gray-50",
            )}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {block === "standards" && (
        <GeoStandardsConfigPanel
          gate={gate}
          probeStandards={probeStandards}
          onSaveGate={onSaveGate}
          onSaveProbeStandards={onSaveProbeStandards}
          saving={saving}
        />
      )}

      {block === "simulator" && (
        <GeoSimulatorPanel
          gate={gate}
          summary={summary}
          failureTopN={failureTopN}
          recentFailures={recentFailures}
          recentAlerts={recentAlerts}
          onReevaluate={onReevaluate}
          onBatchReevaluate={onBatchReevaluate}
          onSimulate={onSimulate}
          onApplyRecommendations={onApplyRecommendations}
          busyId={busyId}
          simulating={simulating}
        />
      )}
    </div>
  );
}
