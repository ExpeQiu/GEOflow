"use client";

import type { ReactNode } from "react";
import { zh } from "@/lib/i18n/zh";
import type { EvalFailureRow, FailureTopN, GateConfig, GeoAlert, GeoEvalSummary } from "@/lib/strategy-types";
import { surfaceCardClass } from "./shared/AivisPrimitives";

export function GeoEvalPanel({
  gate,
  summary,
  failureTopN,
  recentFailures,
  recentAlerts = [],
  onReevaluate,
  busyId,
  extraActions,
}: {
  gate: GateConfig;
  summary: GeoEvalSummary;
  failureTopN: FailureTopN[];
  recentFailures: EvalFailureRow[];
  recentAlerts?: GeoAlert[];
  onReevaluate: (articleId: number) => void;
  busyId: number | null;
  extraActions?: (row: EvalFailureRow) => ReactNode;
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
          <div key={key} className={`${surfaceCardClass} p-4`}>
            <p className="text-xs text-gray-500">{label}</p>
            <p className="mt-1 text-xl font-semibold">{summary[key]}</p>
          </div>
        ))}
      </div>

      {recentAlerts.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
          <h2 className="mb-3 text-sm font-semibold text-amber-900">最近告警</h2>
          <ul className="space-y-2 text-sm text-amber-800">
            {recentAlerts.map((alert) => (
              <li key={alert.id} className="flex flex-wrap gap-2 border-b border-amber-100 pb-2 last:border-0">
                <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium">{alert.alert_type}</span>
                <span>{alert.message}</span>
                {alert.created_at && <span className="text-xs text-amber-600">{new Date(alert.created_at).toLocaleString()}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className={`${surfaceCardClass} p-4`}>
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
        <div className={`${surfaceCardClass} p-4`}>
          <h2 className="mb-3 text-sm font-semibold text-gray-900">{zh.strategy.geoEval.recentFailures}</h2>
          <ul className="space-y-3 text-sm text-gray-700">
            {recentFailures.length === 0 ? (
              <li className="text-gray-400">{zh.strategy.geoEval.noFailures}</li>
            ) : (
              recentFailures.map((row) => (
                <li key={row.article_id} className="border-b border-gray-100 pb-2">
                  <span className="font-medium">#{row.article_id}</span> — {row.failure_reason}
                  <div className="mt-2 flex gap-3">
                    <button
                      type="button"
                      disabled={busyId === row.article_id}
                      onClick={() => onReevaluate(row.article_id)}
                      className="text-xs text-blue-600 hover:underline disabled:opacity-50"
                    >
                      {zh.strategy.geoEval.reevaluate}
                    </button>
                    {extraActions?.(row)}
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
