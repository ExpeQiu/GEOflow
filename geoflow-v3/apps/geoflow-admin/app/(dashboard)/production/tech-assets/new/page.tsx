"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { KnowledgeSubNav } from "@/components/production/KnowledgeSubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiPost, getToken } from "@/lib/api-client";
import { PRODUCTION_NAV } from "@/lib/nav-config";

export default function TechAssetNewPage() {
  const token = useAuthGuard();
  const router = useRouter();
  const [form, setForm] = useState({ ip_id: "", name: "", mind_tag: "", wiki_type: "concept", priority: 100 });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    await apiPost("/api/admin/tech-assets", t, form);
    router.push("/production/tech-assets");
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title="新建技术 IP" subtitle="" />
      <HubNav items={PRODUCTION_NAV} tone="emerald" />
      <KnowledgeSubNav />
      <Link href="/production/tech-assets" className="mb-4 inline-block text-sm text-emerald-700">← 返回</Link>
      <form onSubmit={onSubmit} className="grid max-w-lg gap-3 rounded-lg bg-white p-6 shadow-sm ring-1 ring-gray-200">
        {(["ip_id", "name", "mind_tag", "wiki_type"] as const).map((k) => (
          <input key={k} className="rounded-md border px-3 py-2 text-sm" placeholder={k} value={String(form[k])} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
        ))}
        <button type="submit" className="rounded-md bg-emerald-600 px-4 py-2 text-sm text-white">创建</button>
      </form>
    </div>
  );
}
