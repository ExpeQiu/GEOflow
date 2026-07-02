"use client";

import { FormEvent, useState } from "react";
import { GeoEvalPanel } from "@/components/strategy/GeoEvalPanel";
import type { EvalFailureRow, FailureTopN, GateConfig, GeoEvalSummary } from "@/lib/strategy-types";

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
  const [idsText, setIdsText] = useState("");

  async function handleBatch(e: FormEvent) {
    e.preventDefault();
    const ids = idsText
      .split(/[\s,]+/)
      .map((s) => parseInt(s.trim(), 10))
      .filter((n) => !Number.isNaN(n));
    if (ids.length === 0) return;
    await onBatchReevaluate(ids);
    setIdsText("");
  }

  return (
    <div className="space-y-6">
      <form onSubmit={handleBatch} className="rounded-lg border bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-900">批量重评</h3>
        <p className="mt-1 text-xs text-gray-500">输入文章 ID，逗号或空格分隔</p>
        <div className="mt-3 flex gap-2">
          <input className="flex-1 rounded-md border px-3 py-2 text-sm" placeholder="1, 2, 3" value={idsText} onChange={(e) => setIdsText(e.target.value)} />
          <button type="submit" className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white">批量入队</button>
        </div>
      </form>
      <GeoEvalPanel
        gate={gate}
        summary={summary}
        failureTopN={failureTopN}
        recentFailures={recentFailures}
        onReevaluate={onReevaluate}
        busyId={busyId}
        extraActions={(row) => (
          <button
            type="button"
            disabled={busyId === row.article_id}
            onClick={() => onApplyRecommendations(row.article_id)}
            className="text-xs text-emerald-700 hover:underline disabled:opacity-50"
          >
            应用建议
          </button>
        )}
      />
    </div>
  );
}
