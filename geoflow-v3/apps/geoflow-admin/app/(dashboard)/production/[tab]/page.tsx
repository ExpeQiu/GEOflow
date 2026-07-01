"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiGet, getToken } from "@/lib/api-client";

export default function ProductionPage() {
  const { tab } = useParams<{ tab: string }>();
  const router = useRouter();
  const [assets, setAssets] = useState<{ id: number; name: string; ip_id: string; wiki_type: string }[]>([]);
  const [kbs, setKbs] = useState<{ id: number; name: string }[]>([]);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }
    if (tab === "tech-assets") {
      apiGet<{ items: typeof assets }>("/api/admin/tech-assets", token).then((d) => setAssets(d.items));
    }
    if (tab === "knowledge") {
      apiGet<{ items: typeof kbs }>("/api/admin/knowledge-bases", token).then((d) => setKbs(d.items));
    }
  }, [tab, router]);

  return (
    <div>
      <h1 className="text-lg font-bold mb-4">Production · {tab}</h1>
      {tab === "tech-assets" && (
        <ul className="bg-white border rounded-lg divide-y">
          {assets.map((a) => (
            <li key={a.id} className="p-3 text-sm">
              {a.name} <span className="text-[var(--muted)]">({a.ip_id} · {a.wiki_type})</span>
            </li>
          ))}
        </ul>
      )}
      {tab === "knowledge" && (
        <ul className="bg-white border rounded-lg divide-y">
          {kbs.map((k) => (
            <li key={k.id} className="p-3 text-sm">{k.name}</li>
          ))}
        </ul>
      )}
      {tab === "materials" && <p className="text-[var(--muted)]">素材库 — 对接 /api/v1/materials</p>}
      {tab === "ai_config" && <p className="text-[var(--muted)]">AI 配置 — 模型 / Prompt</p>}
    </div>
  );
}
