"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import { PRODUCTION_NAV } from "@/lib/nav-config";

type KbOption = { id: number; name: string };
type Hit = {
  chunk_id: number;
  chunk_index?: number;
  content: string;
  score: number;
  source?: string;
};

export default function RagSandboxPage() {
  const token = useAuthGuard();
  const [kbs, setKbs] = useState<KbOption[]>([]);
  const [kbId, setKbId] = useState<number | "">("");
  const [kbName, setKbName] = useState("");
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [hitCount, setHitCount] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    const t = getToken();
    if (!t) return;
    apiGet<{ items: KbOption[] }>("/api/admin/knowledge-bases", t).then((d) => {
      setKbs(d.items);
      if (d.items[0]) {
        setKbId(d.items[0].id);
        setKbName(d.items[0].name);
      }
    });
  }, [token]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t || !kbId) return;
    setError("");
    try {
      const res = await apiPost<{
        hits: Hit[];
        hit_count: number;
        knowledge_base_name: string;
      }>("/api/admin/knowledge-bases/rag-sandbox", t, {
        knowledge_base_id: kbId,
        query,
        limit: 8,
      });
      setHits(res.hits);
      setHitCount(res.hit_count);
      setKbName(res.knowledge_base_name);
    } catch {
      setError("检索失败，请确认知识库已向量化");
    }
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title="RAG 沙箱" subtitle="测试知识库召回质量" />
      <HubNav items={PRODUCTION_NAV} tone="emerald" />
      <Link href="/production/knowledge" className="mb-4 inline-block text-sm text-emerald-700">← 知识库</Link>
      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      <form onSubmit={onSubmit} className="mb-6 space-y-3 rounded-lg bg-white p-4 shadow-sm ring-1 ring-gray-200">
        <select
          className="w-full rounded-md border px-3 py-2 text-sm"
          value={kbId}
          onChange={(e) => {
            const id = Number(e.target.value);
            setKbId(id);
            const found = kbs.find((kb) => kb.id === id);
            if (found) setKbName(found.name);
          }}
        >
          {kbs.map((kb) => (
            <option key={kb.id} value={kb.id}>{kb.name}</option>
          ))}
        </select>
        <input
          className="w-full rounded-md border px-3 py-2 text-sm"
          placeholder="输入检索问题"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="submit" className="rounded-md bg-emerald-600 px-4 py-2 text-sm text-white">检索</button>
      </form>

      {hitCount > 0 && (
        <p className="mb-3 text-sm text-gray-600">
          知识库「{kbName}」召回 {hitCount} 条
        </p>
      )}

      <ul className="space-y-3">
        {hits.map((h) => (
          <li key={h.chunk_id} className="rounded-lg bg-white p-4 text-sm shadow-sm ring-1 ring-gray-200">
            <div className="mb-1 flex flex-wrap gap-2 text-xs text-gray-500">
              <span>chunk #{h.chunk_id}</span>
              {h.chunk_index !== undefined && <span>index {h.chunk_index}</span>}
              <span>score {h.score.toFixed(2)}</span>
              {h.source && <span className="rounded bg-slate-100 px-1.5 py-0.5">{h.source}</span>}
            </div>
            <p className="whitespace-pre-wrap text-gray-800">{h.content}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
