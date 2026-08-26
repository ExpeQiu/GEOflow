"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { KnowledgeSubNav } from "@/components/production/KnowledgeSubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import { PRODUCTION_MORE_NAV, PRODUCTION_NAV } from "@/lib/nav-config";

type HistoryItem = { id: number; url: string; target: string; status: string };
type LibraryOption = { id: number; name: string };

export default function UrlImportPage() {
  const token = useAuthGuard();
  const [url, setUrl] = useState("");
  const [target, setTarget] = useState<"knowledge" | "title" | "keyword">("knowledge");
  const [libraryId, setLibraryId] = useState<number | "">("");
  const [titleLibs, setTitleLibs] = useState<LibraryOption[]>([]);
  const [keywordLibs, setKeywordLibs] = useState<LibraryOption[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const t = getToken();
    if (!t) return;
    apiGet<{ items: HistoryItem[] }>("/api/admin/production/url-import/history", t).then((d) => setHistory(d.items));
    apiGet<{ items: LibraryOption[] }>("/api/admin/materials/title-libraries", t).then((d) => setTitleLibs(d.items));
    apiGet<{ items: LibraryOption[] }>("/api/admin/materials/keyword-libraries", t).then((d) => setKeywordLibs(d.items));
  }, [token]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t || !url.trim()) return;
    setError("");
    if ((target === "title" || target === "keyword") && !libraryId) {
      setError("请选择目标素材库");
      return;
    }
    try {
      await apiPost("/api/admin/production/url-import", t, {
        url: url.trim(),
        target,
        library_id: target === "knowledge" ? null : Number(libraryId),
      });
      setUrl("");
      const data = await apiGet<{ items: HistoryItem[] }>("/api/admin/production/url-import/history", t);
      setHistory(data.items);
    } catch {
      setError("导入失败，请检查 URL 或目标库配置");
    }
  }

  const libs = target === "title" ? titleLibs : keywordLibs;

  if (!token) return null;

  return (
    <div>
      <HubHeader title="URL 导入" subtitle="从网页导入知识库、标题库或关键词库" />
      <HubNav items={PRODUCTION_NAV} moreItems={PRODUCTION_MORE_NAV} tone="emerald" />
      <KnowledgeSubNav />
      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      <form onSubmit={onSubmit} className="mb-6 space-y-3 rounded-lg bg-white p-4 shadow-sm ring-1 ring-gray-200">
        <input
          className="w-full rounded-md border px-3 py-2 text-sm"
          placeholder="https://..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <div className="grid gap-2 sm:grid-cols-2">
          <select
            className="rounded-md border px-3 py-2 text-sm"
            value={target}
            onChange={(e) => {
              setTarget(e.target.value as typeof target);
              setLibraryId("");
            }}
          >
            <option value="knowledge">导入为知识库</option>
            <option value="title">导入为标题</option>
            <option value="keyword">导入为关键词</option>
          </select>
          {target !== "knowledge" && (
            <select
              className="rounded-md border px-3 py-2 text-sm"
              value={libraryId}
              onChange={(e) => setLibraryId(Number(e.target.value))}
            >
              <option value="">选择目标库</option>
              {libs.map((lib) => (
                <option key={lib.id} value={lib.id}>{lib.name}</option>
              ))}
            </select>
          )}
        </div>
        <button type="submit" className="rounded-md bg-emerald-600 px-4 py-2 text-sm text-white">开始导入</button>
      </form>
      <ul className="divide-y divide-gray-100 rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
        {history.map((h) => (
          <li key={h.id} className="flex items-center justify-between px-4 py-3 text-sm">
            <span className="line-clamp-1 flex-1 pr-4">{h.url}</span>
            <span className="shrink-0 text-gray-500">{h.target} · {h.status}</span>
            <Link href={`/production/url-import/${h.id}`} className="ml-3 shrink-0 text-emerald-700">详情</Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
