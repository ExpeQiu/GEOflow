"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import type { VisibilityReport, VisibilityReportDetail } from "@/lib/strategy-types";
import { LayerSection, surfaceCardClass } from "./shared/AivisPrimitives";

export function ReportsPanel() {
  const [reports, setReports] = useState<VisibilityReport[]>([]);
  const [selected, setSelected] = useState<VisibilityReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

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
    setGenerating(true);
    try {
      await apiPost("/api/admin/strategy/monitor/reports/generate?period_days=7", t, {});
      await load();
    } finally {
      setGenerating(false);
    }
  }

  async function viewReport(id: number) {
    const t = getToken();
    if (!t) return;
    const detail = await apiGet<VisibilityReportDetail>(`/api/admin/strategy/reports/${id}`, t);
    setSelected(detail);
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <LayerSection title="诊断报告列表">
        <button
          type="button"
          disabled={generating}
          onClick={generate}
          className="mb-4 rounded-md bg-violet-600 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {generating ? "生成中…" : "生成 7 日诊断报告"}
        </button>
        {loading ? (
          <p className="text-sm text-gray-400">加载中…</p>
        ) : reports.length === 0 ? (
          <p className="text-sm text-gray-400">暂无报告</p>
        ) : (
          <ul className={`divide-y divide-gray-100 ${surfaceCardClass}`}>
            {reports.map((r) => (
              <li key={r.id}>
                <button
                  type="button"
                  onClick={() => viewReport(r.id)}
                  className="w-full px-4 py-3 text-left text-sm hover:bg-violet-50"
                >
                  <p className="font-medium">{r.title}</p>
                  <p className="text-xs text-gray-500">
                    {r.period_start} ~ {r.period_end} · {r.status}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        )}
        <Link href="/strategy/monitor/reports" className="mt-3 inline-block text-xs text-violet-600 hover:underline">
          旧版报告页
        </Link>
      </LayerSection>

      <LayerSection title="报告预览">
        {!selected ? (
          <p className="text-sm text-gray-400">选择左侧报告查看</p>
        ) : selected.html_content ? (
          <iframe
            title={selected.title}
            srcDoc={selected.html_content}
            className={`h-[600px] w-full ${surfaceCardClass}`}
            sandbox=""
          />
        ) : (
          <div className="space-y-2 text-sm">
            <p className="font-medium">{selected.title}</p>
            <p className="text-gray-500">{selected.html_path || "HTML 文件不可用"}</p>
          </div>
        )}
      </LayerSection>
    </div>
  );
}
