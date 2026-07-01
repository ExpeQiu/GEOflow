"use client";

import { zh } from "@/lib/i18n/zh";
import type { EvalFailureRow, FailureTopN, GateConfig, GeoEvalSummary } from "@/lib/strategy-types";

export function GeoEvalPanel({
  gate,
  summary,
  failureTopN,
  recentFailures,
  onReevaluate,
  busyId,
}: {
  gate: GateConfig;
  summary: GeoEvalSummary;
  failureTopN: FailureTopN[];
  recentFailures: EvalFailureRow[];
  onReevaluate: (articleId: number) => void;
  busyId: number | null;
}) {
  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-cyan-200 bg-cyan-50 p-4 text-sm text-cyan-900">
        <p className="font-semibold">{zh.strategy.geoEval.gateTitle}</p>
        <ul className="mt-2 list-inside list-disc space-y-1">
          <li>
            {zh.strategy.geoEval.gateEnabled}: {gate.enabled ? "是" : "否"}
          </li>
          <li>
            {zh.strategy.geoEval.gatePublish}: {gate.gate_enabled ? "是" : "否"}
          </li>
        </ul>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {(
          [
            ["pending_eval", zh.strategy.geoEval.pending],
            ["passed", zh.strategy.geoEval.passed],
            ["failed", zh.strategy.geoEval.failed],
            ["skipped", zh.strategy.geoEval.skipped],
          ] as const
        ).map(([key, label]) => (
          <div key={key} className="rounded-lg border border-gray-200 bg-white p-4">
            <p className="text-xs text-gray-500">{label}</p>
            <p className="mt-1 text-xl font-semibold">{summary[key]}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold text-gray-900">{zh.strategy.geoEval.failureTopN}</h2>
          <ul className="space-y-2 text-sm text-gray-700">
            {failureTopN.length === 0 ? (
              <li className="text-gray-400">{zh.strategy.geoEval.noFailures}</li>
            ) : (
              failureTopN.map((row) => (
                <li key={row.failure_reason}>
                  {row.failure_reason} ({row.total})
                </li>
              ))
            )}
          </ul>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold text-gray-900">{zh.strategy.geoEval.recentFailures}</h2>
          <ul className="space-y-3 text-sm text-gray-700">
            {recentFailures.length === 0 ? (
              <li className="text-gray-400">{zh.strategy.geoEval.noFailures}</li>
            ) : (
              recentFailures.map((row) => (
                <li key={row.article_id} className="border-b border-gray-100 pb-2">
                  <span className="font-medium">#{row.article_id}</span> — {row.failure_reason}
                  <div className="mt-2">
                    <button
                      type="button"
                      disabled={busyId === row.article_id}
                      onClick={() => onReevaluate(row.article_id)}
                      className="text-xs text-blue-600 hover:underline disabled:opacity-50"
                    >
                      {zh.strategy.geoEval.reevaluate}
                    </button>
                  </div>
                </li>
              ))
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}
