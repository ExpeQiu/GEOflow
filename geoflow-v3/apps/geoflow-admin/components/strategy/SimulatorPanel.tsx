"use client";

import { GeoEvalPanel } from "@/components/strategy/GeoEvalPanel";
import type {
  EvalFailureRow,
  FailureTopN,
  GateConfig,
  GeoEvalSummary,
  SimulateResult,
} from "@/lib/strategy-types";
import { apiPost, getToken } from "@/lib/api-client";

/** @deprecated 仿真能力已并入 /production/geo-eval 的「GEO 仿真模型器」 */
export function SimulatorPanel({
  gate,
  summary,
  failureTopN,
  recentFailures,
  onReevaluate,
  onBatchReevaluate,
  onApplyRecommendations,
  busyId,
}: {
  gate: GateConfig;
  summary: GeoEvalSummary;
  failureTopN: FailureTopN[];
  recentFailures: EvalFailureRow[];
  onReevaluate: (articleId: number) => void;
  onBatchReevaluate: (articleIds: number[]) => Promise<void>;
  onApplyRecommendations: (articleId: number) => Promise<void>;
  busyId: number | null;
}) {
  async function onSimulate(payload: {
    title: string;
    content: string;
    query?: string;
    keyword?: string;
    article_id?: number;
  }): Promise<SimulateResult> {
    const t = getToken();
    if (!t) throw new Error("unauthorized");
    return apiPost<SimulateResult>("/api/admin/strategy/geo-eval/simulate", t, payload);
  }

  return (
    <GeoEvalPanel
      gate={gate}
      summary={summary}
      failureTopN={failureTopN}
      recentFailures={recentFailures}
      onReevaluate={onReevaluate}
      onBatchReevaluate={onBatchReevaluate}
      onSimulate={onSimulate}
      onApplyRecommendations={onApplyRecommendations}
      busyId={busyId}
    />
  );
}
