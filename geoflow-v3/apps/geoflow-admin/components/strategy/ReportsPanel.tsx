"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import type { VisibilityReport, VisibilityReportDetail } from "@/lib/strategy-types";
import { LayerSection, surfaceCardClass, surfaceInputClass } from "./shared/AivisPrimitives";

export function ReportsPanel() {
  const [reports, setReports] = useState<VisibilityReport[]>([]);
  const [selected, setSelected] = useState<VisibilityReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [importing, setImporting] = useState(false);
  const [flash, setFlash] = useState("");
  const [error, setError] = useState("");
  const [tjgUrl, setTjgUrl] = useState("");
  const [tjgToken, setTjgToken] = useState("");

  async function load() {
    const t = getToken();
    if (!t) return;
    const data = await apiGet<{ items: VisibilityReport[] }>("/api/admin/strategy/monitor/reports", t);
    setReports(data.items);
    setLoading(false);
  }

  useEffect(() => {
    load().catch((e) => {
      setLoading(false);
      setError(e instanceof Error ? e.message : "加载报告失败");
    });
  }, []);

  async function generate() {
    const t = getToken();
    if (!t) return;
    setGenerating(true);
    setError("");
    try {
      await apiPost("/api/admin/strategy/monitor/reports/generate?period_days=7", t, {});
      setFlash("已生成 7 日诊断报告");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成失败");
    } finally {
      setGenerating(false);
    }
  }

  async function importTjg(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    if (!tjgUrl.trim() && !tjgToken.trim()) {
      setError("请填写 TJG share_url 或 token");
      return;
    }
    setImporting(true);
    setError("");
    setFlash("");
    try {
      const qs = new URLSearchParams();
      if (tjgUrl.trim()) qs.set("share_url", tjgUrl.trim());
      if (tjgToken.trim()) qs.set("token", tjgToken.trim());
      await apiPost(`/api/admin/strategy/monitor/reports/import/tjg?${qs.toString()}`, t, {});
      setFlash("TJG 报告已导入");
      setTjgUrl("");
      setTjgToken("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "TJG 导入失败");
    } finally {
      setImporting(false);
    }
  }

  async function viewReport(id: number) {
    const t = getToken();
    if (!t) return;
    const detail = await apiGet<VisibilityReportDetail>(`/api/admin/strategy/reports/${id}`, t);
    setSelected(detail);
  }

  return (
    <div className="space-y-4">
      {error && <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
      {flash && <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{flash}</p>}

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

      <LayerSection title="导入 TJG 报告" subtitle="用 share_url 或 token 灌入外部诊断包">
        <form onSubmit={importTjg} className="flex flex-wrap gap-2">
          <input
            className={`min-w-[220px] flex-1 ${surfaceInputClass}`}
            placeholder="share_url"
            value={tjgUrl}
            onChange={(e) => setTjgUrl(e.target.value)}
          />
          <input
            className={`min-w-[160px] ${surfaceInputClass}`}
            placeholder="token（可选）"
            value={tjgToken}
            onChange={(e) => setTjgToken(e.target.value)}
          />
          <button
            type="submit"
            disabled={importing}
            className="rounded-md border border-violet-300 bg-violet-50 px-4 py-2 text-sm text-violet-800 disabled:opacity-50"
          >
            {importing ? "导入中…" : "导入"}
          </button>
        </form>
      </LayerSection>
    </div>
  );
}
