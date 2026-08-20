"use client";

import { useCallback, useEffect, useState } from "react";
import { ExternalLink, Link2, MessageSquareQuote } from "lucide-react";
import { apiGet, getToken } from "@/lib/api-client";
import type { CitationChain, CitationChainQuery, QueryProbe } from "@/lib/strategy-types";
import { LayerSection, OwnerBadge, platformLabel, SchemeBadge } from "./shared/AivisPrimitives";

function ProbeCard({ probe }: { probe: QueryProbe }) {
  const [open, setOpen] = useState(probe.mentioned || probe.citation_count > 0);
  return (
    <div className="rounded-lg border border-slate-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
      >
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-slate-900">{probe.label || platformLabel(probe.platform)}</span>
          <span
            className={`rounded-full px-2 py-0.5 text-[11px] ${
              probe.mentioned ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"
            }`}
          >
            {probe.mentioned ? "已提及" : "未提及"}
          </span>
          {probe.brand_rank != null && <span className="text-xs text-slate-500">排名 {probe.brand_rank}</span>}
          <SchemeBadge scheme={probe.scheme} />
        </div>
        <span className="text-xs text-violet-700">{probe.citation_count} 引用</span>
      </button>
      {open && (
        <div className="border-t border-slate-100 px-4 py-3">
          {probe.snippet_preview ? (
            <p className="mb-3 whitespace-pre-wrap text-xs leading-relaxed text-slate-600">{probe.snippet_preview}</p>
          ) : (
            <p className="mb-3 text-xs text-slate-400">暂无回答摘要</p>
          )}
          {probe.citations.length > 0 ? (
            <ul className="space-y-2">
              {probe.citations.map((c) => (
                <li key={c.id} className="rounded-md bg-slate-50 px-3 py-2 text-xs">
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-start gap-2 font-medium text-violet-700 hover:underline"
                  >
                    <ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    <span className="line-clamp-2">{c.title || c.url}</span>
                  </a>
                  <p className="mt-1 flex flex-wrap items-center gap-1 truncate text-slate-500">
                    <OwnerBadge owner={c.owner} />
                    <span>{c.domain || c.url}</span>
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-slate-400">该平台无引用来源</p>
          )}
        </div>
      )}
    </div>
  );
}

function QueryDetail({ query }: { query: CitationChainQuery }) {
  return (
    <div className="space-y-3">
      <div className="rounded-lg bg-violet-50/60 px-4 py-3">
        <p className="text-sm font-medium text-violet-950">💬 {query.text}</p>
        <p className="mt-1 text-xs text-violet-700">
          {query.stats.probe_count ?? 0} 探针 · {query.stats.citation_count ?? 0} 引用
          {(query.stats.unique_domains ?? 0) > 0 ? ` · ${query.stats.unique_domains} 域名` : ""}
        </p>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {query.probes.map((probe) => (
          <ProbeCard key={probe.probe_id} probe={probe} />
        ))}
      </div>
    </div>
  );
}

export function QueryCitationExplorer({
  sceneId,
  intentLabel,
}: {
  sceneId: number | null;
  intentLabel?: string;
}) {
  const [chain, setChain] = useState<CitationChain | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedQueryId, setSelectedQueryId] = useState<number | null>(null);

  const load = useCallback(async () => {
    if (!sceneId) {
      setChain(null);
      return;
    }
    const token = getToken();
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<CitationChain>(`/api/admin/strategy/monitor/scenes/${sceneId}/citation-chain`, token);
      if (data.status !== "ok") {
        setError(data.status === "not_found" ? "未找到该意图场景数据" : "加载引用链路失败");
        setChain(null);
        return;
      }
      setChain(data);
      setSelectedQueryId(data.queries[0]?.id ?? null);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "";
      if (msg.includes("404")) {
        setError("引用链路接口未就绪，请重启后端 API（./scripts/run-api.sh）后刷新页面");
      } else if (msg.includes("401") || msg.includes("403")) {
        setError("登录已过期，请重新登录");
      } else {
        setError("加载引用链路失败");
      }
      setChain(null);
    } finally {
      setLoading(false);
    }
  }, [sceneId]);

  useEffect(() => {
    load();
  }, [load]);

  if (!sceneId) {
    return (
      <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50/50 px-4 py-8 text-center text-sm text-slate-500">
        点击场景图谱中的「用户意图」节点，查看 Query → 探针 → 引用 第五层链路
      </div>
    );
  }

  const selectedQuery = chain?.queries.find((q) => q.id === selectedQueryId) ?? null;

  return (
    <LayerSection
      title="Query → Citation 引用链路"
      subtitle={intentLabel ? `意图：${intentLabel}` : "第五层：场景问题 → 6 平台探针 → AI 引用来源"}
    >
      {loading ? (
        <p className="text-sm text-slate-500">加载引用数据…</p>
      ) : error ? (
        <p className="text-sm text-red-600">{error}</p>
      ) : !chain ? (
        <p className="text-sm text-slate-400">暂无数据</p>
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-4 text-xs text-slate-600">
            <span className="inline-flex items-center gap-1">
              <MessageSquareQuote className="h-3.5 w-3.5" />
              Query {chain.stats.query_count}
            </span>
            <span>探针 {chain.stats.probe_count}</span>
            <span className="inline-flex items-center gap-1">
              <Link2 className="h-3.5 w-3.5" />
              引用 {chain.stats.citation_count}
            </span>
            <span>
              场景：{chain.scene.persona} / {chain.scene.scene_name}
            </span>
          </div>

          {chain.queries.length === 0 ? (
            <p className="text-sm text-slate-400">该意图下暂无关联 Query</p>
          ) : (
            <div className="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)]">
              <div className="space-y-2">
                <p className="text-xs font-medium text-slate-500">场景问题</p>
                {chain.queries.map((q) => (
                  <button
                    key={q.id}
                    type="button"
                    onClick={() => setSelectedQueryId(q.id)}
                    className={`w-full rounded-lg border px-3 py-2 text-left text-xs transition-colors ${
                      selectedQueryId === q.id
                        ? "border-violet-300 bg-violet-50 text-violet-900"
                        : "border-slate-200 bg-white text-slate-700 hover:border-violet-200"
                    }`}
                  >
                    <p className="line-clamp-2 font-medium">{q.text}</p>
                    <p className="mt-1 text-slate-500">{(q.stats.citation_count ?? 0)} 引用</p>
                  </button>
                ))}
              </div>
              <div>{selectedQuery ? <QueryDetail query={selectedQuery} /> : null}</div>
            </div>
          )}
        </div>
      )}
    </LayerSection>
  );
}
