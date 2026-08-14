"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { zh } from "@/lib/i18n/zh";
import type {
  EvalFailureRow,
  FailureTopN,
  GateConfig,
  GeoAlert,
  GeoEvalSummary,
  SimulateResult,
} from "@/lib/strategy-types";
import { surfaceCardClass, surfaceInputClass } from "./shared/AivisPrimitives";

function scoreLabel(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(2);
}

function pctLabel(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function ProbBar({ label, value, hint }: { label: string; value: number; hint?: string }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between gap-2 text-xs">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium tabular-nums text-gray-900">{pct.toFixed(1)}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-gray-100">
        <div
          className="h-full rounded-full bg-violet-500 transition-[width] duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      {hint && <p className="mt-1 text-[11px] text-gray-400">{hint}</p>}
    </div>
  );
}

export function GeoSimulatorPanel({
  gate,
  summary,
  failureTopN,
  recentFailures,
  recentAlerts = [],
  onReevaluate,
  onBatchReevaluate,
  onSimulate,
  onApplyRecommendations,
  busyId,
  simulating,
}: {
  gate: GateConfig;
  summary: GeoEvalSummary;
  failureTopN: FailureTopN[];
  recentFailures: EvalFailureRow[];
  recentAlerts?: GeoAlert[];
  onReevaluate: (articleId: number) => void;
  onBatchReevaluate?: (articleIds: number[]) => void;
  onSimulate: (payload: {
    title: string;
    content: string;
    query?: string;
    keyword?: string;
    article_id?: number;
  }) => Promise<SimulateResult>;
  onApplyRecommendations?: (articleId: number) => Promise<void>;
  busyId: number | null;
  simulating?: boolean;
}) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [query, setQuery] = useState("");
  const [keyword, setKeyword] = useState("");
  const [articleIdText, setArticleIdText] = useState("");
  const [batchIds, setBatchIds] = useState("");
  const [result, setResult] = useState<SimulateResult | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  const failedIds = recentFailures.map((r) => r.article_id);
  const passScore = gate.simulation_pass_score ?? 0.55;

  async function runDraftSimulate(e: FormEvent) {
    e.preventDefault();
    setLocalError(null);
    if (!title.trim() || !content.trim()) {
      setLocalError("请填写标题与正文");
      return;
    }
    try {
      const data = await onSimulate({
        title: title.trim(),
        content: content.trim(),
        query: query.trim() || undefined,
        keyword: keyword.trim() || undefined,
      });
      setResult(data);
    } catch {
      setLocalError("仿真失败，请稍后重试");
    }
  }

  async function runArticleSimulate(e: FormEvent) {
    e.preventDefault();
    setLocalError(null);
    const id = parseInt(articleIdText.trim(), 10);
    if (Number.isNaN(id)) {
      setLocalError("请输入有效文章 ID");
      return;
    }
    try {
      const data = await onSimulate({
        title: "",
        content: "",
        article_id: id,
        query: query.trim() || undefined,
      });
      setResult(data);
    } catch {
      setLocalError("按文章仿真失败");
    }
  }

  async function handleBatch(e: FormEvent) {
    e.preventDefault();
    if (!onBatchReevaluate) return;
    const ids = batchIds
      .split(/[\s,]+/)
      .map((s) => parseInt(s.trim(), 10))
      .filter((n) => !Number.isNaN(n));
    if (ids.length === 0) return;
    await onBatchReevaluate(ids);
    setBatchIds("");
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-violet-200 bg-violet-50 p-4 text-sm text-violet-950">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <p className="font-semibold">{zh.strategy.geoEval.simulatorBlockTitle}</p>
            <p className="mt-1 text-violet-800">{zh.strategy.geoEval.simulatorBlockHint}</p>
          </div>
          {onBatchReevaluate && failedIds.length > 0 && (
            <button
              type="button"
              disabled={busyId !== null}
              onClick={() => onBatchReevaluate(failedIds)}
              className="shrink-0 rounded-md bg-violet-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-800 disabled:opacity-50"
            >
              {zh.strategy.geoEval.batchReevaluate}
            </button>
          )}
        </div>
        <p className="mt-3 border-t border-violet-200/80 pt-3 text-xs text-violet-800">
          {zh.strategy.geoEval.simPassScore}: {passScore} · 低于阈值记为未通过门禁
        </p>
      </div>

      <form onSubmit={runDraftSimulate} className={`${surfaceCardClass} space-y-3 p-4`}>
        <h2 className="text-sm font-semibold text-gray-900">{zh.strategy.geoEval.draftSimulateTitle}</h2>
        <p className="text-xs text-gray-500">{zh.strategy.geoEval.draftSimulateHint}</p>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm md:col-span-2">
            <span className="text-xs text-gray-500">标题</span>
            <input className={surfaceInputClass} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="内容标题" />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-xs text-gray-500">关键词（可选）</span>
            <input className={surfaceInputClass} value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="神盾电池安全" />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-xs text-gray-500">用户问题 / Query（可选）</span>
            <input className={surfaceInputClass} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="默认用标题+关键词" />
          </label>
          <label className="flex flex-col gap-1 text-sm md:col-span-2">
            <span className="text-xs text-gray-500">正文</span>
            <textarea
              className={`${surfaceInputClass} min-h-[140px] font-mono text-xs`}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="粘贴待验证的生成内容…"
            />
          </label>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="submit"
            disabled={simulating}
            className="rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50"
          >
            {simulating ? zh.strategy.geoEval.simulating : zh.strategy.geoEval.runSimulate}
          </button>
        </div>
        {localError && <p className="text-xs text-red-600">{localError}</p>}
      </form>

      <form onSubmit={runArticleSimulate} className={`${surfaceCardClass} p-4`}>
        <h3 className="text-sm font-semibold text-gray-900">{zh.strategy.geoEval.articleSimulateTitle}</h3>
        <p className="mt-1 text-xs text-gray-500">{zh.strategy.geoEval.articleSimulateHint}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <input
            className={`w-40 ${surfaceInputClass}`}
            placeholder="文章 ID"
            value={articleIdText}
            onChange={(e) => setArticleIdText(e.target.value)}
          />
          <button
            type="submit"
            disabled={simulating}
            className="rounded-md bg-violet-600 px-3 py-2 text-sm text-white hover:bg-violet-700 disabled:opacity-50"
          >
            {zh.strategy.geoEval.runArticleSimulate}
          </button>
        </div>
      </form>

      {result && (
        <section className={`${surfaceCardClass} p-4`}>
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-gray-900">{zh.strategy.geoEval.probabilityTitle}</h2>
              <p className="mt-1 text-xs text-gray-500">
                Query: <span className="font-mono text-gray-700">{result.query}</span>
                {result.engine && <span className="ml-2 text-gray-400">· {result.engine}</span>}
              </p>
            </div>
            <div className="text-right">
              <p className="text-3xl font-semibold tabular-nums text-violet-700">
                {result.probability_pct ?? Number(((result.adoption_probability ?? result.simulation_score) * 100).toFixed(1))}
                <span className="text-lg">%</span>
              </p>
              <p className="text-xs text-gray-500">{zh.strategy.geoEval.adoptionProb}</p>
              <p
                className={`mt-1 text-xs font-medium ${
                  result.passes_threshold ? "text-emerald-700" : "text-amber-700"
                }`}
              >
                {result.passes_threshold ? zh.strategy.geoEval.passThreshold : zh.strategy.geoEval.failThreshold}
                （≥ {result.pass_threshold ?? passScore}）
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <ProbBar
              label={zh.strategy.geoEval.retrievalProb}
              value={result.breakdown?.retrieval ?? result.retrieval_probability ?? result.retrieval_score ?? 0}
              hint="语料检索命中强度"
            />
            <ProbBar
              label={zh.strategy.geoEval.inContextProb}
              value={result.breakdown?.in_context ?? result.in_context_probability ?? 0}
              hint="内容是否进入检索上下文"
            />
            <ProbBar
              label={zh.strategy.geoEval.overlapScore}
              value={result.breakdown?.overlap ?? result.overlap_score ?? 0}
              hint="Query 与正文词元重叠"
            />
            <ProbBar
              label={zh.strategy.geoEval.answerConfidence}
              value={result.breakdown?.confidence ?? result.confidence ?? 0}
              hint="模拟答文置信度"
            />
          </div>

          {result.simulated_answer && (
            <div className="mt-4 rounded-md bg-gray-50 p-3 text-xs text-gray-700">
              <p className="mb-1 font-medium text-gray-800">{zh.strategy.geoEval.simulatedAnswer}</p>
              <p className="whitespace-pre-wrap leading-relaxed">{result.simulated_answer}</p>
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

      {onBatchReevaluate && (
        <form onSubmit={handleBatch} className={`${surfaceCardClass} p-4`}>
          <h3 className="text-sm font-semibold text-gray-900">批量重评</h3>
          <p className="mt-1 text-xs text-gray-500">输入文章 ID，逗号或空格分隔</p>
          <div className="mt-3 flex gap-2">
            <input className={`flex-1 ${surfaceInputClass}`} placeholder="1, 2, 3" value={batchIds} onChange={(e) => setBatchIds(e.target.value)} />
            <button type="submit" className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white">
              批量入队
            </button>
          </div>
        </form>
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
                    {zh.strategy.geoEval.adoptionProb} {pctLabel(row.simulation_score)} · audit {scoreLabel(row.audit_score)}
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
                    {onApplyRecommendations && (
                      <button
                        type="button"
                        disabled={busyId === row.article_id}
                        onClick={() => onApplyRecommendations(row.article_id)}
                        className="text-xs text-emerald-700 hover:underline disabled:opacity-50"
                      >
                        应用建议
                      </button>
                    )}
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
