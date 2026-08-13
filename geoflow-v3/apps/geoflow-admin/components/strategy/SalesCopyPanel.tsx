"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import { LayerSection, surfaceCardClass, surfaceInputClass } from "./shared/AivisPrimitives";

export type SalesCopyItem = {
  id: number;
  title: string;
  copy_type: string;
  body: string;
  scene_id: number | null;
  version: number;
  status: string;
  updated_at: string | null;
};

const COPY_TYPES = [
  { value: "talking_point", label: "话术要点" },
  { value: "compare_sell", label: "对比卖点" },
  { value: "scene_answer", label: "场景答法" },
  { value: "faq", label: "FAQ" },
];

export function SalesCopyPanel() {
  const [items, setItems] = useState<SalesCopyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");
  const [form, setForm] = useState({ title: "", body: "", copy_type: "talking_point", scene_id: "" });

  async function load() {
    const t = getToken();
    if (!t) return;
    setLoading(true);
    setError("");
    try {
      const data = await apiGet<{ items: SalesCopyItem[]; status?: string }>("/api/admin/strategy/sales-copy", t);
      setItems(data.items ?? []);
      if (data.status === "table_missing") setError("销售口径表未迁移（geo_sales_copy_assets）");
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t || !form.title.trim() || !form.body.trim()) return;
    setFlash("");
    try {
      await apiPost("/api/admin/strategy/sales-copy", t, {
        title: form.title.trim(),
        body: form.body.trim(),
        copy_type: form.copy_type,
        scene_id: form.scene_id ? Number(form.scene_id) : null,
      });
      setForm({ title: "", body: "", copy_type: "talking_point", scene_id: "" });
      setFlash("已保存销售口径");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    }
  }

  return (
    <div className="space-y-6">
      {error && <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
      {flash && <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{flash}</p>}

      <LayerSection title="销售口径 SSOT" subtitle="话术 / 对比卖点 / 场景答法，供诊断与 GeoEval 引用">
        <form onSubmit={handleSubmit} className="grid gap-3 md:grid-cols-2">
          <input
            className={surfaceInputClass}
            placeholder="标题"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            required
          />
          <select
            className={surfaceInputClass}
            value={form.copy_type}
            onChange={(e) => setForm({ ...form, copy_type: e.target.value })}
          >
            {COPY_TYPES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
          <input
            className={surfaceInputClass}
            placeholder="场景 ID（可选）"
            value={form.scene_id}
            onChange={(e) => setForm({ ...form, scene_id: e.target.value })}
          />
          <textarea
            className={`md:col-span-2 min-h-[100px] ${surfaceInputClass}`}
            placeholder="正文口径"
            value={form.body}
            onChange={(e) => setForm({ ...form, body: e.target.value })}
            required
          />
          <button type="submit" className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white md:col-span-2 md:w-fit">
            新增/更新口径
          </button>
        </form>
      </LayerSection>

      <LayerSection title="已有口径">
        {loading ? (
          <p className="text-sm text-gray-400">加载中…</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-gray-400">暂无销售口径</p>
        ) : (
          <ul className={`divide-y divide-gray-100 ${surfaceCardClass}`}>
            {items.map((item) => (
              <li key={item.id} className="px-4 py-3 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-gray-900">{item.title}</span>
                  <span className="rounded bg-violet-50 px-1.5 py-0.5 text-xs text-violet-700">{item.copy_type}</span>
                  <span className="text-xs text-gray-400">v{item.version}</span>
                </div>
                <p className="mt-1 whitespace-pre-wrap text-gray-600">{item.body}</p>
              </li>
            ))}
          </ul>
        )}
      </LayerSection>
    </div>
  );
}
