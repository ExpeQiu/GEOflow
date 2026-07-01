"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPatch, apiPost, getToken } from "@/lib/api-client";
import { PRODUCTION_NAV } from "@/lib/nav-config";

export default function KnowledgeEditPage() {
  const token = useAuthGuard();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const isNew = id === "new";
  const [form, setForm] = useState({ name: "", description: "", content: "" });

  useEffect(() => {
    if (isNew || !token) return;
    apiGet<{ item: typeof form }>(`/api/admin/knowledge-bases/${id}/detail`, token).then((d) => setForm({ name: d.item.name, description: d.item.description, content: d.item.content }));
  }, [id, isNew, token]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    if (isNew) {
      await apiPost("/api/admin/knowledge-bases/create", t, form);
    } else {
      await apiPatch(`/api/admin/knowledge-bases/${id}`, t, form);
    }
    router.push("/production/knowledge");
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title={isNew ? "新建知识库" : "编辑知识库"} subtitle="" />
      <HubNav items={PRODUCTION_NAV} tone="emerald" />
      <Link href="/production/knowledge" className="mb-4 inline-block text-sm text-emerald-700">← 返回</Link>
      <form onSubmit={onSubmit} className="space-y-4 rounded-lg bg-white p-6 shadow-sm ring-1 ring-gray-200">
        <input className="w-full rounded-md border px-3 py-2 text-sm" placeholder="名称" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input className="w-full rounded-md border px-3 py-2 text-sm" placeholder="描述" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <textarea className="min-h-[280px] w-full rounded-md border px-3 py-2 text-sm" placeholder="内容" value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} />
        <button type="submit" className="rounded-md bg-emerald-600 px-4 py-2 text-sm text-white">保存</button>
      </form>
    </div>
  );
}
