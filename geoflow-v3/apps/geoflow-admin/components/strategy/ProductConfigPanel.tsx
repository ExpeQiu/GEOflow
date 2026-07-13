"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import type { CompetitorBrand } from "@/lib/strategy-types";
import { LayerSection, surfaceCardClass, surfaceInputClass } from "./shared/AivisPrimitives";

const AUTO_COLLAPSE_THRESHOLD = 3;

export function ProductConfigPanel({ onChanged }: { onChanged?: () => void }) {
  const [products, setProducts] = useState<CompetitorBrand[]>([]);
  const [form, setForm] = useState({ brand_name: "", is_self: false });
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    try {
      const data = await apiGet<{ items: CompetitorBrand[] }>("/api/admin/strategy/monitor/products", t);
      setProducts(data.items);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (loading) return;
    if (products.length === 0) {
      setOpen(true);
    } else if (products.length > AUTO_COLLAPSE_THRESHOLD) {
      setOpen(false);
    }
  }, [loading, products.length]);

  async function createProduct(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t || !form.brand_name.trim()) return;
    await apiPost("/api/admin/strategy/monitor/products", t, { ...form, aliases: [] });
    setForm({ brand_name: "", is_self: false });
    await load();
    onChanged?.();
  }

  return (
    <LayerSection
      title="产品配置"
      subtitle="维护对标智驾产品/系统，用于产品可见性分析"
      collapsible
      open={open}
      onOpenChange={setOpen}
      badge={products.length > 0 ? `${products.length} 个产品` : undefined}
    >
      <form onSubmit={createProduct} className="mb-4 flex flex-wrap gap-2">
        <input
          className={`min-w-[200px] flex-1 ${surfaceInputClass}`}
          placeholder="产品/系统名，如华为 ADS、千里浩瀚G-ASD"
          value={form.brand_name}
          onChange={(e) => setForm({ ...form, brand_name: e.target.value })}
        />
        <label className="flex items-center gap-1 text-sm">
          <input type="checkbox" checked={form.is_self} onChange={(e) => setForm({ ...form, is_self: e.target.checked })} />
          自有产品
        </label>
        <button type="submit" className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white">
          添加
        </button>
      </form>
      {loading ? (
        <p className="text-sm text-gray-400">加载中…</p>
      ) : products.length === 0 ? (
        <p className="text-sm text-gray-400">尚未配置产品，请添加自有智驾产品与对标系统（如小鹏 XNGP、理想 AD Max）</p>
      ) : (
        <ul className={`divide-y divide-gray-100 ${surfaceCardClass}`}>
          {products.map((p) => (
            <li key={p.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
              <span className={p.is_self ? "font-medium text-violet-800" : ""}>
                {p.brand_name}
                {p.is_self ? "（自有）" : ""}
              </span>
              <span className="text-xs text-gray-400">{p.status}</span>
            </li>
          ))}
        </ul>
      )}
    </LayerSection>
  );
}
