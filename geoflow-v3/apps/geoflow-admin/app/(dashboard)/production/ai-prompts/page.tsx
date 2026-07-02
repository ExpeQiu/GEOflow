"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiDelete, apiGet, apiPatch, apiPost, getToken } from "@/lib/api-client";
import { PRODUCTION_NAV } from "@/lib/nav-config";

type PromptRow = { id: number; name: string; type: string; content_preview: string };

export default function AiPromptsPage() {
  const token = useAuthGuard();
  const [items, setItems] = useState<PromptRow[]>([]);
  const [form, setForm] = useState({ name: "", type: "content", content: "" });
  const [editId, setEditId] = useState<number | null>(null);

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    const data = await apiGet<{ items: PromptRow[] }>("/api/admin/prompts", t);
    setItems(data.items);
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    if (editId) {
      await apiPatch(`/api/admin/prompts/${editId}`, t, form);
      setEditId(null);
    } else {
      await apiPost("/api/admin/prompts", t, form);
    }
    setForm({ name: "", type: "content", content: "" });
    await load();
  }

  async function onDelete(id: number) {
    const t = getToken();
    if (!t || !confirm("确认删除？")) return;
    await apiDelete(`/api/admin/prompts/${id}`, t);
    await load();
  }

  async function onEdit(id: number) {
    const t = getToken();
    if (!t) return;
    const data = await apiGet<{ items: { id: number; name: string; type: string; content_preview: string }[] }>("/api/admin/prompts", t);
    const row = data.items.find((p) => p.id === id);
    if (!row) return;
    setEditId(id);
    setForm({ name: row.name, type: row.type, content: row.content_preview });
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title="AI 提示词" subtitle="内容生成与编排提示词" />
      <HubNav items={PRODUCTION_NAV} tone="emerald" />
      <Link href="/production/ai_config" className="mb-4 inline-block text-sm text-emerald-700">← AI 配置 Hub</Link>
      <form onSubmit={onSubmit} className="mb-6 space-y-2 rounded-lg bg-white p-4 shadow-sm ring-1 ring-gray-200">
        <div className="grid gap-2 md:grid-cols-2">
          <input className="rounded-md border px-3 py-2 text-sm" placeholder="名称" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input className="rounded-md border px-3 py-2 text-sm" placeholder="类型" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} />
        </div>
        <textarea className="min-h-[120px] w-full rounded-md border px-3 py-2 text-sm" placeholder="内容" value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} />
        <button type="submit" className="rounded-md bg-emerald-600 px-4 py-2 text-sm text-white">{editId ? "更新" : "创建"}</button>
      </form>
      <ul className="divide-y divide-gray-100 rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
        {items.map((p) => (
          <li key={p.id} className="flex items-center justify-between px-4 py-3 text-sm">
            <span>{p.name} · {p.type} · {p.content_preview}</span>
            <span className="flex gap-3">
              <button type="button" onClick={() => onEdit(p.id)} className="text-emerald-700">编辑</button>
              <button type="button" onClick={() => onDelete(p.id)} className="text-red-600">删除</button>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
