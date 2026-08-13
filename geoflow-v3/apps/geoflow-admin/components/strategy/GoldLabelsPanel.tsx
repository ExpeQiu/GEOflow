"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import { LayerSection, surfaceCardClass, surfaceInputClass } from "./shared/AivisPrimitives";

type GoldItem = {
  id: number;
  question_id: number | null;
  platform: string;
  source: string;
  mentioned: boolean;
  brand_rank: number | null;
  snippet: string;
  notes: string;
  captured_at: string | null;
};

type BiasResult = {
  sample_n: number;
  mention_agreement: number | null;
  mean_rank_delta: number | null;
  footnote: string;
  status: string;
};

export function GoldLabelsPanel() {
  const [items, setItems] = useState<GoldItem[]>([]);
  const [bias, setBias] = useState<BiasResult | null>(null);
  const [jsonl, setJsonl] = useState("");
  const [form, setForm] = useState({
    question_id: "",
    platform: "doubao",
    mentioned: true,
    brand_rank: "",
    snippet: "",
    notes: "",
  });
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const t = getToken();
    if (!t) return;
    setError("");
    try {
      const [list, b] = await Promise.all([
        apiGet<{ items: GoldItem[]; status?: string }>("/api/admin/strategy/gold-labels", t),
        apiGet<BiasResult>("/api/admin/strategy/gold-labels/bias?days=30", t),
      ]);
      setItems(list.items ?? []);
      setBias(b);
      if (list.status === "table_missing") setError("金标表未迁移，请执行 alembic upgrade head（015）");
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function createOne(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    try {
      await apiPost("/api/admin/strategy/gold-labels", t, {
        question_id: form.question_id ? Number(form.question_id) : null,
        platform: form.platform,
        mentioned: form.mentioned,
        brand_rank: form.brand_rank ? Number(form.brand_rank) : null,
        snippet: form.snippet,
        notes: form.notes,
        source: "manual",
      });
      setMsg("金标已保存");
      setForm({ ...form, question_id: "", brand_rank: "", snippet: "", notes: "" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    }
  }

  async function importJsonl(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t || !jsonl.trim()) return;
    try {
      const res = await apiPost<{ created: number; errors?: string[] }>(
        "/api/admin/strategy/gold-labels/import-jsonl",
        t,
        { content: jsonl },
      );
      setMsg(`已导入 ${res.created} 条${res.errors?.length ? `，错误 ${res.errors.length}` : ""}`);
      setJsonl("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "导入失败");
    }
  }

  return (
    <div className="space-y-6">
      {error && <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
      {msg && <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{msg}</p>}

      <LayerSection title="金标辅轨偏移" subtitle="Open-API vs 人工/抽检对照；不覆盖 visibility_open_api">
        {!bias ? (
          <p className="text-sm text-gray-400">加载中…</p>
        ) : (
          <div className={`grid gap-3 md:grid-cols-3 ${surfaceCardClass} p-4 text-sm`}>
            <div>
              <p className="text-xs text-gray-500">样本 n</p>
              <p className="text-xl font-semibold">{bias.sample_n}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">提及一致率</p>
              <p className="text-xl font-semibold">
                {bias.mention_agreement == null ? "—" : `${(bias.mention_agreement * 100).toFixed(0)}%`}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">平均 rank 偏移</p>
              <p className="text-xl font-semibold">
                {bias.mean_rank_delta == null ? "—" : `${bias.mean_rank_delta > 0 ? "+" : ""}${bias.mean_rank_delta}`}
              </p>
            </div>
            <p className="md:col-span-3 text-xs text-gray-600">{bias.footnote}</p>
          </div>
        )}
      </LayerSection>

      <LayerSection title="录入金标">
        <form onSubmit={createOne} className="grid gap-2 md:grid-cols-3">
          <input
            className={surfaceInputClass}
            placeholder="question_id"
            value={form.question_id}
            onChange={(e) => setForm({ ...form, question_id: e.target.value })}
          />
          <input
            className={surfaceInputClass}
            placeholder="platform"
            value={form.platform}
            onChange={(e) => setForm({ ...form, platform: e.target.value })}
          />
          <input
            className={surfaceInputClass}
            placeholder="brand_rank"
            value={form.brand_rank}
            onChange={(e) => setForm({ ...form, brand_rank: e.target.value })}
          />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.mentioned}
              onChange={(e) => setForm({ ...form, mentioned: e.target.checked })}
            />
            提及品牌
          </label>
          <input
            className={`md:col-span-2 ${surfaceInputClass}`}
            placeholder="snippet / notes"
            value={form.snippet}
            onChange={(e) => setForm({ ...form, snippet: e.target.value })}
          />
          <button type="submit" className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white md:w-fit">
            保存金标
          </button>
        </form>
      </LayerSection>

      <LayerSection title="JSONL 批量导入" subtitle='每行：{"question_id":1,"platform":"doubao","mentioned":true,"brand_rank":2}'>
        <form onSubmit={importJsonl} className="space-y-2">
          <textarea
            className={`min-h-[120px] w-full ${surfaceInputClass}`}
            value={jsonl}
            onChange={(e) => setJsonl(e.target.value)}
            placeholder='{"question_id":1,"platform":"doubao","mentioned":true,"brand_rank":2}'
          />
          <button type="submit" className="rounded-md border border-violet-300 bg-violet-50 px-4 py-2 text-sm text-violet-800">
            导入
          </button>
        </form>
      </LayerSection>

      <LayerSection title="已有金标">
        {items.length === 0 ? (
          <p className="text-sm text-gray-400">暂无金标</p>
        ) : (
          <ul className={`divide-y divide-gray-100 ${surfaceCardClass}`}>
            {items.map((g) => (
              <li key={g.id} className="px-4 py-3 text-sm">
                <span className="font-medium">
                  Q{g.question_id ?? "—"} · {g.platform}
                </span>
                <span className="ml-2 text-xs text-gray-500">
                  {g.mentioned ? "提及" : "未提及"}
                  {g.brand_rank != null ? ` · rank ${g.brand_rank}` : ""} · {g.source}
                </span>
                {g.snippet && <p className="mt-1 text-gray-600">{g.snippet}</p>}
              </li>
            ))}
          </ul>
        )}
      </LayerSection>
    </div>
  );
}
