"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { zh } from "@/lib/i18n/zh";
import type {
  EvalFailureRow,
  FailureTopN,
  GateConfig,
  GeoAlert,
  GeoEvalSummary,
  ProbeStandardsConfig,
} from "@/lib/strategy-types";
import { surfaceCardClass } from "./shared/AivisPrimitives";

function scoreLabel(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(2);
}

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
  busyId,
  saving,
  extraActions,
}: {
  gate: GateConfig;
  probeStandards?: ProbeStandardsConfig | null;
  summary: GeoEvalSummary;
  failureTopN: FailureTopN[];
  recentFailures: EvalFailureRow[];
  recentAlerts?: GeoAlert[];
  onReevaluate: (articleId: number) => void;
  onBatchReevaluate?: (articleIds: number[]) => void;
  onSaveGate?: (next: {
    enabled: boolean;
    hard_gate: boolean;
    wiki_checks_enabled: boolean;
    simulation_pass_score: number;
    audit_pass_score: number;
  }) => Promise<void> | void;
  onSaveProbeStandards?: (next: {
    footnote_on_bias: boolean;
    do_not_overwrite_open_api_kpi: true;
    rank_report_weight: { list_order: number; first_mention: number; unknown: number };
    min_evidence_level: string;
    forbid_corpus_as_l1: boolean;
    fixture_min_list_acc: number;
    scan_platforms: string;
    priority_floor_daily: number;
  }) => Promise<void> | void;
  busyId: number | null;
  saving?: boolean;
  extraActions?: (row: EvalFailureRow) => ReactNode;
}) {
  const [enabled, setEnabled] = useState(gate.enabled);
  const [hardGate, setHardGate] = useState(Boolean(gate.hard_gate ?? gate.gate_enabled));
  const [wikiEnabled, setWikiEnabled] = useState(Boolean(gate.wiki_checks_enabled));
  const [simPass, setSimPass] = useState(gate.simulation_pass_score ?? 0.55);
  const [auditPass, setAuditPass] = useState(gate.audit_pass_score ?? 0.6);

  const [footnote, setFootnote] = useState(probeStandards?.footnote_on_bias ?? true);
  const [listOrderW, setListOrderW] = useState(probeStandards?.rank_report_weight.list_order ?? 1);
  const [firstMentionW, setFirstMentionW] = useState(probeStandards?.rank_report_weight.first_mention ?? 0.3);
  const [unknownW, setUnknownW] = useState(probeStandards?.rank_report_weight.unknown ?? 0);
  const [minEvidence, setMinEvidence] = useState(probeStandards?.min_evidence_level ?? "L1");
  const [forbidCorpus, setForbidCorpus] = useState(probeStandards?.forbid_corpus_as_l1 ?? true);
  const [listAcc, setListAcc] = useState(probeStandards?.fixture_min_list_acc ?? 0.8);
  const [platforms, setPlatforms] = useState(probeStandards?.scan_platforms ?? "doubao,deepseek");
  const [priorityFloor, setPriorityFloor] = useState(probeStandards?.priority_floor_daily ?? 80);

  useEffect(() => {
    setEnabled(gate.enabled);
    setHardGate(Boolean(gate.hard_gate ?? gate.gate_enabled));
    setWikiEnabled(Boolean(gate.wiki_checks_enabled));
    setSimPass(gate.simulation_pass_score ?? 0.55);
    setAuditPass(gate.audit_pass_score ?? 0.6);
  }, [gate]);

  useEffect(() => {
    if (!probeStandards) return;
    setFootnote(probeStandards.footnote_on_bias);
    setListOrderW(probeStandards.rank_report_weight.list_order);
    setFirstMentionW(probeStandards.rank_report_weight.first_mention);
    setUnknownW(probeStandards.rank_report_weight.unknown);
    setMinEvidence(probeStandards.min_evidence_level);
    setForbidCorpus(probeStandards.forbid_corpus_as_l1);
    setListAcc(probeStandards.fixture_min_list_acc);
    setPlatforms(probeStandards.scan_platforms);
    setPriorityFloor(probeStandards.priority_floor_daily);
  }, [probeStandards]);

  const failedIds = recentFailures.map((r) => r.article_id);

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <p className="font-semibold">{zh.strategy.geoEval.dualTrackTitle}</p>
            <p className="mt-1 text-emerald-800">{zh.strategy.geoEval.dualTrackHint}</p>
          </div>
          {onBatchReevaluate && failedIds.length > 0 && (
            <button
              type="button"
              disabled={busyId !== null}
              onClick={() => onBatchReevaluate(failedIds)}
              className="shrink-0 rounded-md bg-emerald-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-800 disabled:opacity-50"
            >
              {zh.strategy.geoEval.batchReevaluate}
            </button>
          )}
        </div>
        <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-emerald-200/80 pt-3 text-xs text-emerald-800">
          <li>
            {zh.strategy.geoEval.gateEnabled}: {gate.enabled ? "是" : "否"}
          </li>
          <li>
            {zh.strategy.geoEval.gatePublish}: {gate.gate_enabled ? "是" : "否"}
            {" · "}
            {gate.mode === "hard" ? zh.strategy.geoEval.gateModeHard : zh.strategy.geoEval.gateModeSoft}
          </li>
          {gate.wiki_checks_enabled !== undefined && (
            <li>
              {zh.strategy.geoEval.wikiChecks}: {gate.wiki_checks_enabled ? "是" : "否"}
            </li>
          )}
          {gate.simulation_pass_score !== undefined && (
            <li>
              {zh.strategy.geoEval.simPassScore}: {gate.simulation_pass_score}
            </li>
          )}
          {gate.audit_pass_score !== undefined && (
            <li>
              {zh.strategy.geoEval.auditPassScore}: {gate.audit_pass_score}
            </li>
          )}
        </ul>
      </div>

      {/* Track A — 内容门禁配置 */}
      <section className={`${surfaceCardClass} p-4`}>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-gray-900">{zh.strategy.geoEval.contentGateTitle}</h2>
          {onSaveGate && (
            <button
              type="button"
              disabled={saving}
              onClick={() =>
                onSaveGate({
                  enabled,
                  hard_gate: hardGate,
                  wiki_checks_enabled: wikiEnabled,
                  simulation_pass_score: simPass,
                  audit_pass_score: auditPass,
                })
              }
              className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              {zh.strategy.geoEval.saveGate}
            </button>
          )}
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3 text-sm">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} disabled={!onSaveGate} />
            {zh.strategy.geoEval.gateEnabled}
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={hardGate} onChange={(e) => setHardGate(e.target.checked)} disabled={!onSaveGate} />
            {zh.strategy.geoEval.gatePublish}
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={wikiEnabled} onChange={(e) => setWikiEnabled(e.target.checked)} disabled={!onSaveGate} />
            {zh.strategy.geoEval.wikiChecks}
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-gray-500">{zh.strategy.geoEval.simPassScore}</span>
            <input
              type="number"
              min={0}
              max={1}
              step={0.01}
              value={simPass}
              disabled={!onSaveGate}
              onChange={(e) => setSimPass(Number(e.target.value))}
              className="rounded-md border border-gray-300 px-2 py-1"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-gray-500">{zh.strategy.geoEval.auditPassScore}</span>
            <input
              type="number"
              min={0}
              max={1}
              step={0.01}
              value={auditPass}
              disabled={!onSaveGate}
              onChange={(e) => setAuditPass(Number(e.target.value))}
              className="rounded-md border border-gray-300 px-2 py-1"
            />
          </label>
        </div>
        <p className="mt-3 text-xs text-gray-500">
          {hardGate ? zh.strategy.geoEval.gateModeHard : zh.strategy.geoEval.gateModeSoft}
        </p>
      </section>

      {/* Track B — 探针标准 */}
      {probeStandards && (
        <section className={`${surfaceCardClass} p-4`}>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-gray-900">{zh.strategy.geoEval.probeStandardsTitle}</h2>
            {onSaveProbeStandards && (
              <button
                type="button"
                disabled={saving}
                onClick={() =>
                  onSaveProbeStandards({
                    footnote_on_bias: footnote,
                    do_not_overwrite_open_api_kpi: true,
                    rank_report_weight: {
                      list_order: listOrderW,
                      first_mention: firstMentionW,
                      unknown: unknownW,
                    },
                    min_evidence_level: minEvidence,
                    forbid_corpus_as_l1: forbidCorpus,
                    fixture_min_list_acc: listAcc,
                    scan_platforms: platforms,
                    priority_floor_daily: priorityFloor,
                  })
                }
                className="rounded-md bg-cyan-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-cyan-800 disabled:opacity-50"
              >
                {zh.strategy.geoEval.saveProbe}
              </button>
            )}
          </div>
          <p className="mb-3 text-xs text-gray-500">{probeStandards.effect_note || zh.strategy.geoEval.probeEffectNote}</p>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3 text-sm">
            <div className="text-xs text-gray-600">
              {zh.strategy.geoEval.metricPrimary}: <span className="font-medium">open_api</span>（固定）
            </div>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={footnote} onChange={(e) => setFootnote(e.target.checked)} disabled={!onSaveProbeStandards} />
              {zh.strategy.geoEval.footnoteOnBias}
            </label>
            <label className="flex items-center gap-2 opacity-80">
              <input type="checkbox" checked readOnly disabled />
              {zh.strategy.geoEval.doNotOverwriteKpi}
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs text-gray-500">{zh.strategy.geoEval.minEvidence}</span>
              <select
                value={minEvidence}
                disabled={!onSaveProbeStandards}
                onChange={(e) => setMinEvidence(e.target.value)}
                className="rounded-md border border-gray-300 px-2 py-1"
              >
                <option value="L0">L0</option>
                <option value="L1">L1</option>
              </select>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={forbidCorpus} onChange={(e) => setForbidCorpus(e.target.checked)} disabled={!onSaveProbeStandards} />
              {zh.strategy.geoEval.forbidCorpusL1}
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs text-gray-500">{zh.strategy.geoEval.fixtureMinListAcc}</span>
              <input
                type="number"
                min={0}
                max={1}
                step={0.05}
                value={listAcc}
                disabled={!onSaveProbeStandards}
                onChange={(e) => setListAcc(Number(e.target.value))}
                className="rounded-md border border-gray-300 px-2 py-1"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs text-gray-500">list_order 权重</span>
              <input type="number" min={0} max={1} step={0.1} value={listOrderW} disabled={!onSaveProbeStandards} onChange={(e) => setListOrderW(Number(e.target.value))} className="rounded-md border border-gray-300 px-2 py-1" />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs text-gray-500">first_mention 权重</span>
              <input type="number" min={0} max={1} step={0.1} value={firstMentionW} disabled={!onSaveProbeStandards} onChange={(e) => setFirstMentionW(Number(e.target.value))} className="rounded-md border border-gray-300 px-2 py-1" />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs text-gray-500">unknown 权重</span>
              <input type="number" min={0} max={1} step={0.1} value={unknownW} disabled={!onSaveProbeStandards} onChange={(e) => setUnknownW(Number(e.target.value))} className="rounded-md border border-gray-300 px-2 py-1" />
            </label>
            <label className="flex flex-col gap-1 md:col-span-2">
              <span className="text-xs text-gray-500">{zh.strategy.geoEval.scanPlatforms}</span>
              <input type="text" value={platforms} disabled={!onSaveProbeStandards} onChange={(e) => setPlatforms(e.target.value)} className="rounded-md border border-gray-300 px-2 py-1" />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs text-gray-500">{zh.strategy.geoEval.priorityFloor}</span>
              <input type="number" min={0} max={1000} value={priorityFloor} disabled={!onSaveProbeStandards} onChange={(e) => setPriorityFloor(Number(e.target.value))} className="rounded-md border border-gray-300 px-2 py-1" />
            </label>
          </div>
          {probeStandards.contract_fields && probeStandards.contract_fields.length > 0 && (
            <div className="mt-4 rounded-md bg-gray-50 p-3 text-xs text-gray-600">
              <p className="mb-1 font-medium text-gray-800">{zh.strategy.geoEval.contractTitle}</p>
              <ul className="list-inside list-disc space-y-0.5">
                {probeStandards.contract_fields.map((row) => (
                  <li key={row.field}>
                    <code>{row.field}</code>: {row.values}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        {(
          [
            ["pending_eval", zh.strategy.geoEval.pending],
            ["passed", zh.strategy.geoEval.passed],
            ["advisory", zh.strategy.geoEval.advisory],
            ["failed", zh.strategy.geoEval.failed],
            ["skipped", zh.strategy.geoEval.skipped],
          ] as const
        ).map(([key, label]) => (
          <div key={key} className={`${surfaceCardClass} p-4`}>
            <p className="text-xs text-gray-500">{label}</p>
            <p className="mt-1 text-xl font-semibold">{summary[key] ?? 0}</p>
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
                <li key={`${row.article_id}-${row.updated_at || ""}`} className="border-b border-gray-100 pb-2">
                  <div className="flex flex-wrap items-baseline gap-2">
                    <Link href={`/operations/articles/${row.article_id}`} className="font-medium text-emerald-700 hover:underline">
                      #{row.article_id}
                    </Link>
                    {row.status && <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">{row.status}</span>}
                    {row.gate_mode && <span className="text-xs text-gray-400">{row.gate_mode}</span>}
                  </div>
                  <p className="mt-1 text-gray-700">{row.failure_reason}</p>
                  <p className="mt-1 text-xs text-gray-500">
                    sim {scoreLabel(row.simulation_score)} · audit {scoreLabel(row.audit_score)}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-3">
                    <button
                      type="button"
                      disabled={busyId === row.article_id}
                      onClick={() => onReevaluate(row.article_id)}
                      className="text-xs text-blue-600 hover:underline disabled:opacity-50"
                    >
                      {zh.strategy.geoEval.reevaluate}
                    </button>
                    <Link href={`/operations/articles/${row.article_id}`} className="text-xs text-emerald-700 hover:underline">
                      {zh.strategy.geoEval.openArticle}
                    </Link>
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
