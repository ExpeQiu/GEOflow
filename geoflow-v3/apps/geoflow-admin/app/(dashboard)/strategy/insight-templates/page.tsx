"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiDelete, apiGet, apiPost, getToken } from "@/lib/api-client";
import { STRATEGY_NAV } from "@/lib/nav-config";

export default function InsightTemplatesPage() {
  const token = useAuthGuard();
  const [items, setItems] = useState<{ id: number; name: string; source_url: string }[]>([]);
  const [form, setForm] = useState({ name: "", source_url: "" });

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    const data = await apiGet<{ items: typeof items }>("/api/admin/strategy/insight-templates/manage", t);
    setItems(data.items);
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    await apiPost("/api/admin/strategy/insight-templates", t, form);
    setForm({ name: "", source_url: "" });
    await load();
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title="Insight Templates" subtitle="洞察模板 CRUD 与 re-mine" />
      <HubNav items={[...STRATEGY_NAV, { key: "insight-templates", label: "洞察模板", href: "/strategy/insight-templates" }]} tone="violet" />
      <form onSubmit={onSubmit} className="mb-6 grid gap-2 rounded-lg bg-white p-4 shadow-sm ring-1 ring-gray-200 md:grid-cols-3">
        <input className="rounded-md border px-3 py-2 text-sm" placeholder="名称" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input className="rounded-md border px-3 py-2 text-sm" placeholder="来源 URL" value={form.source_url} onChange={(e) => setForm({ ...form, source_url: e.target.value })} />
        <button type="submit" className="rounded-md bg-violet-600 px-3 py-2 text-sm text-white">创建</button>
      </form>
      <ul className="divide-y divide-gray-100 rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
        {items.map((t) => (
          <li key={t.id} className="flex items-center justify-between px-4 py-3 text-sm">
            <span>{t.name}</span>
            <span className="space-x-2">
              <button type="button" onClick={() => apiPost(`/api/admin/strategy/insight-templates/${t.id}/re-mine`, getToken()!)} className="text-violet-600">re-mine</button>
              <button type="button" onClick={() => apiDelete(`/api/admin/strategy/insight-templates/${t.id}`, getToken()!).then(load)} className="text-red-600">删除</button>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
