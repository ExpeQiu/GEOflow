"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { KnowledgeSubNav } from "@/components/production/KnowledgeSubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPatch, getToken } from "@/lib/api-client";
import { PRODUCTION_MORE_NAV, PRODUCTION_NAV } from "@/lib/nav-config";
import { useRouteParams } from "@/lib/use-route-params";

export default function TechAssetEditPage({ params }: { params: Promise<{ id: string }> }) {
  const token = useAuthGuard();
  const { id } = useRouteParams(params);
  const router = useRouter();
  const [form, setForm] = useState({ ip_id: "", name: "", mind_tag: "", wiki_type: "concept", wiki_slug: "", priority: 100, status: "active" });

  useEffect(() => {
    if (!token) return;
    apiGet<{ items: { id: number; ip_id: string; name: string; mind_tag: string; wiki_type: string; wiki_slug: string; priority: number; status: string }[] }>(
      "/api/admin/tech-assets",
      token,
    ).then((d) => {
      const row = d.items.find((a) => String(a.id) === id);
      if (row) setForm({ ip_id: row.ip_id, name: row.name, mind_tag: row.mind_tag, wiki_type: row.wiki_type, wiki_slug: row.wiki_slug || "", priority: row.priority, status: row.status });
    });
  }, [id, token]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    await apiPatch(`/api/admin/tech-assets/${id}`, t, form);
    router.push("/production/tech-assets");
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title="编辑技术 IP" subtitle="" />
      <HubNav items={PRODUCTION_NAV} moreItems={PRODUCTION_MORE_NAV} tone="emerald" />
      <KnowledgeSubNav />
      <Link href="/production/tech-assets" className="mb-4 inline-block text-sm text-emerald-700">← 返回</Link>
      <form onSubmit={onSubmit} className="grid max-w-lg gap-3 rounded-lg bg-white p-6 shadow-sm ring-1 ring-gray-200">
        {(["ip_id", "name", "mind_tag", "wiki_type", "wiki_slug", "status"] as const).map((k) => (
          <input key={k} className="rounded-md border px-3 py-2 text-sm" placeholder={k} value={String(form[k])} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
        ))}
        <input type="number" className="rounded-md border px-3 py-2 text-sm" placeholder="priority" value={form.priority} onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })} />
        <button type="submit" className="rounded-md bg-emerald-600 px-4 py-2 text-sm text-white">保存</button>
      </form>
    </div>
  );
}
