"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiDelete, apiGet, apiPost, getToken } from "@/lib/api-client";
import { PRODUCTION_NAV } from "@/lib/nav-config";

export default function AiModelsPage() {
  const token = useAuthGuard();
  const [items, setItems] = useState<{ id: number; name: string; model_id: string; status: string }[]>([]);
  const [form, setForm] = useState({ name: "", model_id: "", api_key: "" });

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    const data = await apiGet<{ items: typeof items }>("/api/admin/ai-models", t);
    setItems(data.items);
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    await apiPost("/api/admin/ai-models", t, form);
    setForm({ name: "", model_id: "", api_key: "" });
    await load();
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title="AI 模型" subtitle="聊天与 embedding 模型配置" />
      <HubNav items={PRODUCTION_NAV} tone="emerald" />
      <Link href="/production/ai_config" className="mb-4 inline-block text-sm text-emerald-700">← AI 配置 Hub</Link>
      <form onSubmit={onSubmit} className="mb-6 grid gap-2 rounded-lg bg-white p-4 shadow-sm ring-1 ring-gray-200 md:grid-cols-4">
        <input className="rounded-md border px-3 py-2 text-sm" placeholder="显示名" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input className="rounded-md border px-3 py-2 text-sm" placeholder="model_id" value={form.model_id} onChange={(e) => setForm({ ...form, model_id: e.target.value })} />
        <input className="rounded-md border px-3 py-2 text-sm" placeholder="api_key" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} />
        <button type="submit" className="rounded-md bg-emerald-600 px-3 py-2 text-sm text-white">添加</button>
      </form>
      <ul className="divide-y divide-gray-100 rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
        {items.map((m) => (
          <li key={m.id} className="flex items-center justify-between px-4 py-3 text-sm">
            <span>{m.name} · {m.model_id} · {m.status}</span>
            <button type="button" onClick={() => apiPost(`/api/admin/ai-models/${m.id}/test`, getToken()!)} className="text-blue-600">测试</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
