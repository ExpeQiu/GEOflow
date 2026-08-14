"use client";

import { useEffect, useMemo, useState } from "react";
import { BrandVisibilityPanel } from "./BrandVisibilityPanel";
import { ProductVisibilityPanel } from "./ProductVisibilityPanel";
import type { BrandPanel, ProductPanel } from "@/lib/strategy-types";

type VisView = "brand" | "product";

export function VisibilityHub({
  brand,
  product,
  onRefresh,
}: {
  brand: BrandPanel | null;
  product: ProductPanel | null;
  onRefresh?: () => void;
}) {
  const [view, setView] = useState<VisView>("brand");

  useEffect(() => {
    const v = new URLSearchParams(window.location.search).get("view");
    if (v === "product") setView("product");
  }, []);

  const tabs = useMemo(
    () =>
      [
        { key: "brand" as const, label: "品牌可见性" },
        { key: "product" as const, label: "产品可见性" },
      ] as const,
    [],
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 border-b border-gray-100 pb-3">
        {tabs.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setView(t.key)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${
              view === t.key ? "bg-violet-100 text-violet-800" : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {view === "brand" && brand && <BrandVisibilityPanel data={brand} onRefresh={onRefresh} />}
      {view === "brand" && !brand && <p className="text-sm text-gray-400">加载品牌可见性…</p>}

      {view === "product" && product && <ProductVisibilityPanel data={product} onRefresh={onRefresh} />}
      {view === "product" && !product && <p className="text-sm text-gray-400">加载产品可见性…</p>}
    </div>
  );
}
