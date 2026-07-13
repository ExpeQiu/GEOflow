"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import type { CompetitorBrand } from "@/lib/strategy-types";
import { LayerSection, surfaceCardClass, surfaceInputClass } from "./shared/AivisPrimitives";

const AUTO_COLLAPSE_THRESHOLD = 3;

export function CompetitorConfigPanel({ onChanged }: { onChanged?: () => void }) {
  const [competitors, setCompetitors] = useState<CompetitorBrand[]>([]);
  const [form, setForm] = useState({ brand_name: "", is_self: false });
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    try {
      const data = await apiGet<{ items: CompetitorBrand[] }>("/api/admin/strategy/monitor/competitors", t);
      setCompetitors(data.items);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (loading) return;
    if (competitors.length === 0) {
      setOpen(true);
    } else if (competitors.length > AUTO_COLLAPSE_THRESHOLD) {
      setOpen(false);
    }
  }, [loading, competitors.length]);

  async function createCompetitor(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t || !form.brand_name.trim()) return;
    await apiPost("/api/admin/strategy/monitor/competitors", t, { ...form, aliases: [] });
    setForm({ brand_name: "", is_self: false });
    await load();
    onChanged?.();
  }

  return (
    <LayerSection
      title="竞品配置"
      subtitle="维护对标品牌（车企品牌），用于品牌竞品矩阵"
      collapsible
      open={open}
      onOpenChange={setOpen}
      badge={competitors.length > 0 ? `${competitors.length} 个品牌` : undefined}
    >
      <form onSubmit={createCompetitor} className="mb-4 flex flex-wrap gap-2">
        <input
          className={`min-w-[200px] flex-1 ${surfaceInputClass}`}
          placeholder="品牌名，如吉利汽车、理想汽车"
          value={form.brand_name}
          onChange={(e) => setForm({ ...form, brand_name: e.target.value })}
        />
        <label className="flex items-center gap-1 text-sm">
          <input type="checkbox" checked={form.is_self} onChange={(e) => setForm({ ...form, is_self: e.target.checked })} />
          自有品牌
        </label>
        <button type="submit" className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white">
          添加
        </button>
      </form>
      {loading ? (
        <p className="text-sm text-gray-400">加载中…</p>
      ) : competitors.length === 0 ? (
        <p className="text-sm text-gray-400">尚未配置竞品，请添加自有品牌与对标竞品</p>
      ) : (
        <ul className={`divide-y divide-gray-100 ${surfaceCardClass}`}>
          {competitors.map((c) => (
            <li key={c.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
              <span className={c.is_self ? "font-medium text-violet-800" : ""}>
                {c.brand_name}
                {c.is_self ? "（自有）" : ""}
              </span>
              <span className="text-xs text-gray-400">{c.status}</span>
            </li>
          ))}
        </ul>
      )}
    </LayerSection>
  );
}
