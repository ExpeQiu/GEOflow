"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { SchemeBadge } from "@/components/strategy/shared/AivisPrimitives";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, getToken } from "@/lib/api-client";
import { STRATEGY_MORE_NAV, STRATEGY_NAV } from "@/lib/nav-config";
import type { MonitorRunDetail } from "@/lib/strategy-types";
import { useRouteParams } from "@/lib/use-route-params";

export default function MonitorRunDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const token = useAuthGuard();
  const { id } = useRouteParams(params);
  const [data, setData] = useState<MonitorRunDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token || !id) return;
    apiGet<MonitorRunDetail>(`/api/admin/strategy/monitor/runs/${id}`, token)
      .then(setData)
      .catch(() => setError("无法加载扫描详情"));
  }, [token, id]);

  if (!token) return null;

  return (
    <div>
      <HubHeader title={`Monitor 扫描 #${id}`} subtitle="探针明细与平台汇总；scheme 仅展示，不计入北极星" />
      <HubNav items={STRATEGY_NAV} moreItems={STRATEGY_MORE_NAV} tone="violet" />
      <Link href="/strategy/probes?view=scan" className="mb-4 inline-block text-sm text-violet-700">
        ← 返回采集工作台
      </Link>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {!data && !error && <p className="text-sm text-gray-500">加载中…</p>}

      {data && (
        <div className="space-y-6">
          <section className="rounded-lg bg-white p-5 shadow-sm ring-1 ring-gray-200">
            <div className="grid grid-cols-2 gap-4 md:grid-cols-5 text-sm">
              <Stat label="状态" value={data.run.status} />
              <Stat label="问题数" value={String(data.run.question_count)} />
              <Stat label="探针数" value={String(data.run.probe_count ?? 0)} />
              <Stat label="提及率" value={`${Math.round(data.run.mention_rate * 100)}%`} />
              <Stat label="完成时间" value={data.run.completed_at ? new Date(data.run.completed_at).toLocaleString() : "—"} />
            </div>
          </section>

          {data.platform_stats.length > 0 && (
            <section className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
              <div className="border-b border-gray-100 px-4 py-3 text-sm font-semibold">平台汇总</div>
              <table className="min-w-full divide-y text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {["平台", "探针", "提及", "均排名"].map((h) => (
                      <th key={h} className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data.platform_stats.map((p) => (
                    <tr key={p.platform}>
                      <td className="px-4 py-2">{p.platform}</td>
                      <td className="px-4 py-2">{p.total}</td>
                      <td className="px-4 py-2">{p.mentions}</td>
                      <td className="px-4 py-2">{p.avg_rank ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          <section className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
            <div className="border-b border-gray-100 px-4 py-3 text-sm font-semibold">探针明细 ({data.probes.length})</div>
            <div className="max-h-[520px] overflow-y-auto">
              <table className="min-w-full divide-y text-sm">
                <thead className="sticky top-0 bg-gray-50">
                  <tr>
                    {["问题", "平台", "方案", "引擎", "提及", "排名", "摘录"].map((h) => (
                      <th key={h} className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data.probes.map((p) => (
                    <tr key={p.id}>
                      <td className="max-w-xs px-3 py-2 text-gray-800">{p.question_text}</td>
                      <td className="px-3 py-2 text-violet-700">{p.platform}</td>
                      <td className="px-3 py-2">
                        <SchemeBadge scheme={p.scheme || "open_api"} />
                      </td>
                      <td className="px-3 py-2 text-xs text-gray-500">{p.engine ?? "corpus"}</td>
                      <td className="px-3 py-2">{p.mentioned ? "是" : "否"}</td>
                      <td className="px-3 py-2">{p.brand_rank ?? "—"}</td>
                      <td className="max-w-sm px-3 py-2 text-xs text-gray-600 line-clamp-3">{p.snippet || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-violet-50 p-3">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 font-semibold text-gray-900">{value}</p>
    </div>
  );
}
