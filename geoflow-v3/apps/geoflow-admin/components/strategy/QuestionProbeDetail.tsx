"use client";

import { useEffect, useState } from "react";
import { ExternalLink, X } from "lucide-react";
import { apiGet, getToken } from "@/lib/api-client";
import type { QuestionCitationDetail, QueryProbe } from "@/lib/strategy-types";
import { platformLabel, surfaceCardClass } from "./shared/AivisPrimitives";

function ProbeRow({ probe }: { probe: QueryProbe }) {
  const [open, setOpen] = useState(probe.mentioned || probe.engine === "cend_browser");
  const isCend = probe.engine === "cend_browser" || probe.metric_kind === "cend_sample";
  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm"
      >
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium">{probe.label || platformLabel(probe.platform)}</span>
          <span
            className={`rounded px-1.5 py-0.5 text-[11px] ${
              probe.mentioned ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-600"
            }`}
          >
            {probe.mentioned ? "已提及" : "未提及"}
          </span>
          {probe.brand_rank != null && <span className="text-xs text-gray-500">排名 {probe.brand_rank}</span>}
          {isCend && (
            <span className="rounded bg-amber-50 px-1.5 py-0.5 text-[11px] text-amber-800">C端 · L2</span>
          )}
          {probe.engine && !isCend && (
            <span className="rounded bg-slate-50 px-1.5 py-0.5 text-[11px] text-slate-600">{probe.engine}</span>
          )}
          {probe.evidence_level && (
            <span className="text-[11px] text-gray-400">{probe.evidence_level}</span>
          )}
        </div>
        <span className="text-xs text-violet-600">{probe.citation_count} 引用</span>
      </button>
      {open && (
        <div className="space-y-3 border-t border-gray-100 px-3 py-2">
          {probe.thinking_text && (
            <div>
              <p className="mb-1 text-[11px] font-medium text-gray-500">
                思考链路{probe.thinking_ms != null ? ` · ${Math.round(probe.thinking_ms / 1000)}s` : ""}
              </p>
              <p className="max-h-28 overflow-y-auto whitespace-pre-wrap text-xs leading-relaxed text-gray-600">
                {probe.thinking_text}
              </p>
            </div>
          )}
          {probe.keywords && probe.keywords.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {probe.keywords.map((kw) => (
                <span key={kw} className="rounded bg-cyan-50 px-1.5 py-0.5 text-[11px] text-cyan-800">
                  {kw}
                </span>
              ))}
            </div>
          )}
          {probe.rank_blocks && probe.rank_blocks.length > 0 && (
            <div>
              <p className="mb-1 text-[11px] font-medium text-gray-500">排名结构</p>
              <ul className="space-y-1 text-xs text-gray-700">
                {probe.rank_blocks.map((b, i) => (
                  <li key={i} className="rounded bg-gray-50 px-2 py-1">
                    {String((b as { camp?: string }).camp || `块 ${i + 1}`)}
                    {(b as { brand_rank?: number }).brand_rank != null && (
                      <span className="ml-2 text-gray-500">rank={(b as { brand_rank?: number }).brand_rank}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {probe.snippet_preview ? (
            <p className="whitespace-pre-wrap text-xs leading-relaxed text-gray-600">{probe.snippet_preview}</p>
          ) : (
            <p className="text-xs text-gray-400">暂无回答摘要</p>
          )}
          {probe.citations.length > 0 && (
            <ul className="space-y-1">
              {probe.citations.map((c) => (
                <li key={c.id} className="rounded bg-gray-50 px-2 py-1.5 text-xs">
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-start gap-1 text-violet-700 hover:underline"
                  >
                    <ExternalLink className="mt-0.5 h-3 w-3 shrink-0" />
                    <span className="line-clamp-2">{c.title || c.url}</span>
                  </a>
                  {(c.evidence_level || c.source) && (
                    <span className="mt-0.5 block text-[10px] text-gray-400">
                      {[c.evidence_level, c.source].filter(Boolean).join(" · ")}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
          {probe.source_hosts && probe.source_hosts.length > 0 && (
            <p className="text-[11px] text-gray-400">源：{probe.source_hosts.join(" · ")}</p>
          )}
        </div>
      )}
    </div>
  );
}

export function QuestionProbeDetail({
  questionId,
  questionText,
  onClose,
}: {
  questionId: number;
  questionText: string;
  onClose: () => void;
}) {
  const [data, setData] = useState<QuestionCitationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const t = getToken();
    if (!t) return;
    setLoading(true);
    setError("");
    apiGet<QuestionCitationDetail>(`/api/admin/strategy/monitor/questions/${questionId}/citations`, t)
      .then(setData)
      .catch(() => setError("加载探针结果失败"))
      .finally(() => setLoading(false));
  }, [questionId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className={`max-h-[85vh] w-full max-w-2xl overflow-y-auto ${surfaceCardClass}`}>
        <div className="sticky top-0 flex items-start justify-between gap-3 border-b border-gray-100 bg-white px-4 py-3">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">各平台探针结果</h3>
            <p className="mt-1 text-xs text-gray-500 line-clamp-2">{questionText}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded p-1 text-gray-500 hover:bg-gray-100">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-3 p-4">
          {loading && <p className="text-sm text-gray-500">加载中…</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}
          {data && !loading && (
            <>
              <p className="text-xs text-gray-500">
                探针 {data.probes?.length ?? 0} · 引用合计{" "}
                {data.probes?.reduce((s, p) => s + (p.citation_count || 0), 0) ?? 0}
              </p>
              <div className="space-y-2">
                {(data.probes || []).map((p) => (
                  <ProbeRow key={p.probe_id} probe={p} />
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
