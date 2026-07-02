"use client";

import Link from "next/link";
import { Brain, Database, Plus, RefreshCw } from "lucide-react";
import { cn } from "@/lib/cn";
import { zh } from "@/lib/i18n/zh";
import type { KnowledgeItem, MaterialStats } from "@/lib/production-types";

export function KnowledgePanel({
  stats,
  items,
  onSync,
  busyId,
}: {
  stats: MaterialStats;
  items: KnowledgeItem[];
  onSync: (id: number) => void;
  busyId: number | null;
}) {
  const progress = stats.knowledge_chunks > 0 ? Math.round((stats.vectorized_chunks / stats.knowledge_chunks) * 100) : 0;
  const health =
    stats.knowledge_bases <= 0
      ? "empty"
      : stats.active_embedding_models <= 0
        ? "no_embed"
        : stats.unvectorized_chunks > 0
          ? "pending"
          : "ready";

  const healthLabel = {
    ready: zh.production.knowledge.healthReady,
    pending: zh.production.knowledge.healthPending,
    no_embed: zh.production.knowledge.healthNoEmbed,
    empty: zh.production.knowledge.healthEmpty,
  }[health];

  const healthClass = {
    ready: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    pending: "bg-amber-50 text-amber-700 ring-amber-200",
    no_embed: "bg-red-50 text-red-700 ring-red-200",
    empty: "bg-slate-100 text-slate-700 ring-slate-200",
  }[health];

  return (
    <section className="overflow-hidden rounded-lg border border-orange-100 bg-white shadow-sm">
      <div className="border-b border-orange-100 bg-orange-50/50 px-6 py-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <span className="inline-flex items-center rounded-full bg-white px-3 py-1 text-sm font-semibold text-orange-700 ring-1 ring-orange-200">
              <Brain className="mr-2 h-4 w-4" />
              {zh.production.tabs.knowledge}
            </span>
            <h2 className="mt-3 text-2xl font-bold text-gray-900">{zh.production.knowledge.hubTitle}</h2>
            <p className="mt-2 text-sm text-gray-600">{zh.production.knowledge.hubDesc}</p>
          </div>
          <span className={cn("inline-flex w-fit rounded-full px-3 py-1 text-xs font-semibold ring-1", healthClass)}>
            {healthLabel}
          </span>
          <div className="flex flex-wrap gap-2">
            <Link href="/production/knowledge/new" className="inline-flex items-center rounded-md bg-orange-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-orange-700">
              <Plus className="mr-1 h-3 w-3" />
              新建知识库
            </Link>
            <Link href="/production/url-import" className="inline-flex items-center rounded-md border border-orange-200 px-3 py-1.5 text-xs font-medium text-orange-700 hover:bg-orange-50">
              URL 导入
            </Link>
            <Link href="/production/rag-sandbox" className="inline-flex items-center rounded-md border border-orange-200 px-3 py-1.5 text-xs font-medium text-orange-700 hover:bg-orange-50">
              RAG 沙箱
            </Link>
            <Link href="/production/knowledge-settings" className="inline-flex items-center rounded-md border border-orange-200 px-3 py-1.5 text-xs font-medium text-orange-700 hover:bg-orange-50">
              知识设置
            </Link>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6 px-6 py-6 lg:grid-cols-4">
        <Metric label="知识库" value={stats.knowledge_bases} />
        <Metric label="切片总数" value={stats.knowledge_chunks} />
        <Metric label="已向量化" value={stats.vectorized_chunks} valueClass="text-emerald-700" />
        <Metric label="任务引用" value={stats.knowledge_usage_count} />
      </div>

      <div className="px-6 pb-4">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">向量化进度</span>
          <span className="font-medium text-gray-900">{progress}%</span>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-gray-200">
          <div className="h-full rounded-full bg-orange-500" style={{ width: `${progress}%` }} />
        </div>
      </div>

      <div className="overflow-hidden border-t border-gray-200">
        {items.length === 0 ? (
          <div className="px-6 py-10 text-center text-sm text-gray-500">暂无知识库</div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {["名称", "字数", "切片", "向量化", "任务引用", "操作"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {items.map((kb) => (
                <tr key={kb.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 text-sm font-medium text-gray-900">
                      <Database className="h-4 w-4 text-orange-500" />
                      {kb.name}
                    </div>
                    {kb.description && <p className="mt-1 line-clamp-1 text-xs text-gray-500">{kb.description}</p>}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">{kb.word_count}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{kb.chunk_count}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {zh.production.knowledge.chunks(kb.vectorized_count, kb.chunk_count)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">{kb.used_task_count}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <Link href={`/production/knowledge/${kb.id}`} className="text-xs text-orange-700 hover:underline">编辑</Link>
                      <button
                        type="button"
                        disabled={busyId === kb.id}
                        onClick={() => onSync(kb.id)}
                        className="inline-flex items-center rounded-md border border-orange-200 bg-white px-2 py-1 text-xs font-medium text-orange-700 hover:bg-orange-50 disabled:opacity-50"
                      >
                        <RefreshCw className="mr-1 h-3 w-3" />
                        {zh.production.knowledge.syncChunks}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

function Metric({ label, value, valueClass }: { label: string; value: number; valueClass?: string }) {
  return (
    <div>
      <div className="text-sm font-medium text-gray-500">{label}</div>
      <div className={cn("mt-2 text-3xl font-bold text-gray-900", valueClass)}>{value}</div>
    </div>
  );
}
