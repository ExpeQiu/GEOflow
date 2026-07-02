"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiDelete, apiGet, apiPatch, apiPost, apiUpload, getToken } from "@/lib/api-client";
import { PRODUCTION_NAV } from "@/lib/nav-config";

export default function KnowledgeEditPage() {
  const token = useAuthGuard();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const isNew = id === "new";
  const [form, setForm] = useState({ name: "", description: "", content: "" });
  const [uploadMsg, setUploadMsg] = useState("");

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

  async function onDelete() {
    const t = getToken();
    if (!t || isNew || !confirm("确认删除知识库？")) return;
    await apiDelete(`/api/admin/knowledge-bases/${id}`, t);
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
        {!isNew && (
          <div className="rounded-md border border-dashed border-emerald-200 bg-emerald-50/40 p-3">
            <label className="text-sm font-medium text-emerald-800">上传文件 (.txt / .md / .pdf)</label>
            <input
              type="file"
              accept=".txt,.md,.markdown,.csv,.pdf"
              className="mt-2 block w-full text-sm"
              onChange={async (e) => {
                const file = e.target.files?.[0];
                const t = getToken();
                if (!file || !t) return;
                const res = await apiUpload<{ item: { character_count: number } }>(`/api/admin/knowledge-bases/${id}/upload-file`, t, file);
                setUploadMsg(`已追加导入，当前 ${res.item.character_count} 字`);
                const d = await apiGet<{ item: typeof form }>(`/api/admin/knowledge-bases/${id}/detail`, t);
                setForm({ name: d.item.name, description: d.item.description, content: d.item.content });
              }}
            />
            {uploadMsg && <p className="mt-2 text-xs text-emerald-700">{uploadMsg}</p>}
          </div>
        )}
        <div className="flex gap-3">
          <button type="submit" className="rounded-md bg-emerald-600 px-4 py-2 text-sm text-white">保存</button>
          {!isNew && (
            <button type="button" onClick={onDelete} className="rounded-md border border-red-200 px-4 py-2 text-sm text-red-600">删除</button>
          )}
        </div>
      </form>
    </div>
  );
}
