"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import { PRODUCTION_NAV } from "@/lib/nav-config";

export default function UrlImportPage() {
  const token = useAuthGuard();
  const [url, setUrl] = useState("");
  const [history, setHistory] = useState<{ id: number; url: string; status: string }[]>([]);

  useEffect(() => {
    const t = getToken();
    if (!t) return;
    apiGet<{ items: typeof history }>("/api/admin/production/url-import/history", t).then((d) => setHistory(d.items));
  }, [token]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t || !url.trim()) return;
    await apiPost("/api/admin/production/url-import", t, { url: url.trim(), target: "knowledge" });
    setUrl("");
    const data = await apiGet<{ items: typeof history }>("/api/admin/production/url-import/history", t);
    setHistory(data.items);
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title="URL 导入" subtitle="从网页导入知识或素材" />
      <HubNav items={PRODUCTION_NAV} tone="emerald" />
      <Link href="/production/materials" className="mb-4 inline-block text-sm text-emerald-700">← 素材 Hub</Link>
      <form onSubmit={onSubmit} className="mb-6 flex gap-2 rounded-lg bg-white p-4 shadow-sm ring-1 ring-gray-200">
        <input className="flex-1 rounded-md border px-3 py-2 text-sm" placeholder="https://..." value={url} onChange={(e) => setUrl(e.target.value)} />
        <button type="submit" className="rounded-md bg-emerald-600 px-4 py-2 text-sm text-white">导入</button>
      </form>
      <ul className="divide-y divide-gray-100 rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
        {history.map((h) => (
          <li key={h.id} className="flex items-center justify-between px-4 py-3 text-sm">
            <span>{h.url} · {h.status}</span>
            <Link href={`/production/url-import/${h.id}`} className="text-emerald-700">详情</Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
