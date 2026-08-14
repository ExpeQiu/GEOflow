"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import type { VisibilityReport } from "@/lib/strategy-types";

export default function MonitorReportsPage() {
  const [reports, setReports] = useState<VisibilityReport[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    const t = getToken();
    if (!t) return;
    const data = await apiGet<{ items: VisibilityReport[] }>("/api/admin/strategy/monitor/reports", t);
    setReports(data.items);
    setLoading(false);
  }

  useEffect(() => {
    load().catch(() => setLoading(false));
  }, []);

  async function generate() {
    const t = getToken();
    if (!t) return;
    await apiPost("/api/admin/strategy/monitor/reports/generate?period_days=7", t, {});
    await load();
  }

  return (
    <div className="p-6">
      <Link href="/strategy/probes" className="mb-4 inline-block text-sm text-violet-700">← 返回数据采集</Link>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">AI 可见性诊断报告</h1>
        <button type="button" onClick={generate} className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white">生成报告</button>
      </div>
      {loading ? <p className="text-sm text-gray-500">加载中…</p> : (
        <ul className="divide-y divide-gray-100 rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
          {reports.length === 0 ? <li className="px-4 py-8 text-center text-sm text-gray-500">暂无报告</li> : reports.map((r) => (
            <li key={r.id} className="px-4 py-4">
              <p className="font-medium">{r.title}</p>
              <p className="text-xs text-gray-500">{r.period_start} ~ {r.period_end} · {r.status}</p>
              {r.html_path && <p className="mt-1 text-xs text-gray-400">{r.html_path}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
