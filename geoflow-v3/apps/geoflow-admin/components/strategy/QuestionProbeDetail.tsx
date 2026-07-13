"use client";

import { useEffect, useState } from "react";
import { ExternalLink, X } from "lucide-react";
import { apiGet, getToken } from "@/lib/api-client";
import type { QuestionCitationDetail, QueryProbe } from "@/lib/strategy-types";
import { platformLabel, surfaceCardClass } from "./shared/AivisPrimitives";

function ProbeRow({ probe }: { probe: QueryProbe }) {
  const [open, setOpen] = useState(probe.mentioned);
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
        </div>
        <span className="text-xs text-violet-600">{probe.citation_count} 引用</span>
      </button>
      {open && (
        <div className="border-t border-gray-100 px-3 py-2">
          {probe.snippet_preview ? (
            <p className="mb-2 whitespace-pre-wrap text-xs leading-relaxed text-gray-600">{probe.snippet_preview}</p>
          ) : (
            <p className="mb-2 text-xs text-gray-400">暂无回答摘要</p>
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
                </li>
              ))}
            </ul>
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
          {!loading && !error && data && (
            <>
              <p className="text-xs text-gray-500">
                {data.stats.probe_count} 探针 · {data.stats.citation_count} 引用
                {data.stats.unique_domains > 0 ? ` · ${data.stats.unique_domains} 域名` : ""}
              </p>
              {data.probes.length === 0 ? (
                <p className="text-sm text-gray-500">暂无探针记录，请先执行全量扫描</p>
              ) : (
                <div className="grid gap-2 sm:grid-cols-2">
                  {data.probes.map((probe) => (
                    <ProbeRow key={probe.probe_id} probe={probe} />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
