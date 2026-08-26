"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { KnowledgeSubNav } from "@/components/production/KnowledgeSubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPatch, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import { PRODUCTION_MORE_NAV, PRODUCTION_NAV } from "@/lib/nav-config";

export default function KnowledgeSettingsPage() {
  const token = useAuthGuard();
  const [form, setForm] = useState({ chunk_size: 1200, chunk_overlap: 200, retrieval_limit: 8, hybrid_enabled: true });
  const [flash, setFlash] = useState("");

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    const data = await apiGet<typeof form>("/api/admin/knowledge-settings", t);
    setForm({
      chunk_size: data.chunk_size,
      chunk_overlap: data.chunk_overlap,
      retrieval_limit: data.retrieval_limit,
      hybrid_enabled: data.hybrid_enabled,
    });
  }, []);

  useEffect(() => {
    if (token) load().catch(() => undefined);
  }, [token, load]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    await apiPatch("/api/admin/knowledge-settings", t, form);
    setFlash("设置已保存");
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title={zh.production.tabs.knowledge} subtitle="切片与检索参数" />
      <HubNav items={PRODUCTION_NAV} moreItems={PRODUCTION_MORE_NAV} tone="emerald" />
      <KnowledgeSubNav />
      {flash && <FlashAlert variant="success">{flash}</FlashAlert>}
      <form onSubmit={onSubmit} className="max-w-lg space-y-4 rounded-lg bg-white p-6 shadow-sm ring-1 ring-gray-200">
        <label className="block text-sm">
          切片大小
          <input type="number" className="mt-1 w-full rounded-md border px-3 py-2" value={form.chunk_size} onChange={(e) => setForm({ ...form, chunk_size: Number(e.target.value) })} />
        </label>
        <label className="block text-sm">
          重叠长度
          <input type="number" className="mt-1 w-full rounded-md border px-3 py-2" value={form.chunk_overlap} onChange={(e) => setForm({ ...form, chunk_overlap: Number(e.target.value) })} />
        </label>
        <label className="block text-sm">
          检索条数
          <input type="number" className="mt-1 w-full rounded-md border px-3 py-2" value={form.retrieval_limit} onChange={(e) => setForm({ ...form, retrieval_limit: Number(e.target.value) })} />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.hybrid_enabled} onChange={(e) => setForm({ ...form, hybrid_enabled: e.target.checked })} />
          启用混合检索
        </label>
        <button type="submit" className="rounded-md bg-emerald-600 px-4 py-2 text-sm text-white">保存</button>
      </form>
    </div>
  );
}
