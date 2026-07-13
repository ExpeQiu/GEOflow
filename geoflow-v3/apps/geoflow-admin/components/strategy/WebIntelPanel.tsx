"use client";

import { FormEvent, useState } from "react";
import { zh } from "@/lib/i18n/zh";
import type { WebSource } from "@/lib/strategy-types";
import { surfaceCardClass, surfaceInputClass } from "./shared/AivisPrimitives";

export function WebIntelPanel({
  sources,
  reports,
  onCreate,
  onDelete,
  onRefresh,
}: {
  sources: WebSource[];
  reports: { id: number; title: string; status: string; created_at: string | null }[];
  onCreate: (body: { url: string; label: string }) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
  onRefresh: (id: number) => Promise<void>;
}) {
  const [url, setUrl] = useState("");
  const [label, setLabel] = useState("");

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    await onCreate({ url: url.trim(), label: label.trim() });
    setUrl("");
    setLabel("");
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <section className={`${surfaceCardClass} p-5`}>
        <h2 className="text-lg font-semibold text-gray-900">{zh.strategy.webIntel.sourcesTitle}</h2>
        <form onSubmit={handleAdd} className="mt-4 flex flex-wrap gap-2">
          <input className={`min-w-[180px] flex-1 ${surfaceInputClass}`} placeholder="https://..." value={url} onChange={(e) => setUrl(e.target.value)} />
          <input className={surfaceInputClass} placeholder="标签" value={label} onChange={(e) => setLabel(e.target.value)} />
          <button type="submit" className="rounded-md bg-violet-600 px-3 py-2 text-sm text-white">添加</button>
        </form>
        {sources.length === 0 ? (
          <p className="mt-4 text-sm text-gray-500">{zh.strategy.webIntel.emptySources}</p>
        ) : (
          <ul className="mt-4 divide-y divide-gray-100">
            {sources.map((s) => (
              <li key={s.id} className="flex items-start justify-between gap-2 py-3 text-sm">
                <div>
                  <p className="font-medium text-gray-900 break-all">{s.url}</p>
                  <p className="mt-1 text-xs text-gray-500">{s.label} · {s.fetch_status}</p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button type="button" className="text-violet-600" onClick={() => onRefresh(s.id)}>刷新</button>
                  <button type="button" className="text-red-600" onClick={() => onDelete(s.id)}>删除</button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section className={`${surfaceCardClass} p-5`}>
        <h2 className="text-lg font-semibold text-gray-900">{zh.strategy.webIntel.reportsTitle}</h2>
        {reports.length === 0 ? (
          <p className="mt-4 text-sm text-gray-500">{zh.strategy.webIntel.emptyReports}</p>
        ) : (
          <ul className="mt-4 divide-y divide-gray-100">
            {reports.map((r) => (
              <li key={r.id} className="py-3 text-sm">
                <p className="font-medium text-gray-900">{r.title || `#${r.id}`}</p>
                <p className="mt-1 text-xs text-gray-500">{r.status}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
