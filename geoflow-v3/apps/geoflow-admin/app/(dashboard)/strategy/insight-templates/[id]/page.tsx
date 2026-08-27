"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, getToken } from "@/lib/api-client";
import { STRATEGY_MORE_NAV, STRATEGY_NAV } from "@/lib/nav-config";
import { useRouteParams } from "@/lib/use-route-params";

export default function InsightTemplateDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const token = useAuthGuard();
  const { id } = useRouteParams(params);
  const [item, setItem] = useState<{ id: number; name: string; source_url: string; eeat_score: number | null } | null>(null);

  useEffect(() => {
    const t = getToken();
    if (!t) return;
    apiGet<{ items: { id: number; name: string; source_url: string; eeat_score: number | null }[] }>("/api/admin/strategy/insight-templates/manage", t).then((d) => {
      const row = d.items.find((x) => String(x.id) === id);
      if (row) setItem(row);
    });
  }, [id, token]);

  return (
    <div>
      <HubHeader title={item?.name ?? "洞察模板"} subtitle="模板详情" />
      <HubNav items={STRATEGY_NAV} moreItems={STRATEGY_MORE_NAV} tone="violet" />
      <Link href="/strategy/insight-templates" className="mb-4 inline-block text-sm text-violet-700">← 返回列表</Link>
      {item && (
        <dl className="space-y-2 rounded-lg bg-white p-6 text-sm shadow-sm ring-1 ring-gray-200">
          <div><dt className="text-gray-500">ID</dt><dd>{item.id}</dd></div>
          <div><dt className="text-gray-500">名称</dt><dd>{item.name}</dd></div>
          <div><dt className="text-gray-500">来源</dt><dd className="break-all">{item.source_url || "—"}</dd></div>
          <div><dt className="text-gray-500">EEAT</dt><dd>{item.eeat_score ?? "—"}</dd></div>
        </dl>
      )}
    </div>
  );
}
