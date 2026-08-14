"use client";

import { useEffect, useState } from "react";
import { zh } from "@/lib/i18n/zh";
import type { GateConfig, ProbeStandardsConfig } from "@/lib/strategy-types";
import { surfaceCardClass } from "./shared/AivisPrimitives";

export type GateSavePayload = {
  enabled: boolean;
  hard_gate: boolean;
  wiki_checks_enabled: boolean;
  simulation_pass_score: number;
  audit_pass_score: number;
};

export type ProbeSavePayload = {
  footnote_on_bias: boolean;
  do_not_overwrite_open_api_kpi: true;
  rank_report_weight: { list_order: number; first_mention: number; unknown: number };
  min_evidence_level: string;
  forbid_corpus_as_l1: boolean;
  fixture_min_list_acc: number;
  scan_platforms: string;
  priority_floor_daily: number;
};

export function GeoStandardsConfigPanel({
  gate,
  probeStandards,
  onSaveGate,
  onSaveProbeStandards,
  saving,
}: {
  gate: GateConfig;
  probeStandards?: ProbeStandardsConfig | null;
  onSaveGate?: (next: GateSavePayload) => Promise<void> | void;
  onSaveProbeStandards?: (next: ProbeSavePayload) => Promise<void> | void;
  saving?: boolean;
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

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
        <p className="font-semibold">{zh.strategy.geoEval.standardsBlockTitle}</p>
        <p className="mt-1 text-emerald-800">{zh.strategy.geoEval.standardsBlockHint}</p>
        <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-emerald-200/80 pt-3 text-xs text-emerald-800">
          <li>
            {zh.strategy.geoEval.gateEnabled}: {gate.enabled ? "是" : "否"}
          </li>
          <li>
            {zh.strategy.geoEval.gatePublish}: {gate.gate_enabled ? "是" : "否"}
            {" · "}
            {gate.mode === "hard" ? zh.strategy.geoEval.gateModeHard : zh.strategy.geoEval.gateModeSoft}
          </li>
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
        <div className="grid grid-cols-1 gap-3 text-sm md:grid-cols-2 lg:grid-cols-3">
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
        <p className="mt-3 text-xs text-gray-500">{hardGate ? zh.strategy.geoEval.gateModeHard : zh.strategy.geoEval.gateModeSoft}</p>
      </section>

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
          <div className="grid grid-cols-1 gap-3 text-sm md:grid-cols-2 lg:grid-cols-3">
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
    </div>
  );
}
