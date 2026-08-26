"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import { PRODUCTION_MORE_NAV, PRODUCTION_NAV } from "@/lib/nav-config";

type JobDetail = {
  id: number;
  url: string;
  target: string;
  name: string;
  status: string;
  error_message?: string;
  result_summary?: string;
  result_json?: {
    titles?: string[];
    keywords?: string[];
    knowledge_markdown?: string;
    library_name?: string;
    analysis_source?: string;
  } | null;
  created_at?: string | null;
};

export default function UrlImportJobPage() {
  const token = useAuthGuard();
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<JobDetail | null>(null);
  const [flash, setFlash] = useState("");

  useEffect(() => {
    const t = getToken();
    if (!t) return;
    apiGet<{ job: JobDetail }>(`/api/admin/production/url-import/${jobId}`, t).then((d) => setJob(d.job));
  }, [jobId, token]);

  async function commit() {
    const t = getToken();
    if (!t) return;
    const res = await apiPost<{ sync_queued?: boolean; knowledge_base_id?: number }>(
      `/api/admin/production/url-import/${jobId}/commit`,
      t,
    );
    setFlash(
      res.sync_queued
        ? `已提交入库，知识库 #${res.knowledge_base_id} 切片同步已入队`
        : "已提交入库",
    );
    const d = await apiGet<{ job: JobDetail }>(`/api/admin/production/url-import/${jobId}`, t);
    setJob(d.job);
  }

  if (!token) return null;

  const result = job?.result_json;

  return (
    <div>
      <HubHeader title={`URL 导入 #${jobId}`} subtitle="任务详情与提交" />
      <HubNav items={PRODUCTION_NAV} moreItems={PRODUCTION_MORE_NAV} tone="emerald" />
      <Link href="/production/url-import" className="mb-4 inline-block text-sm text-emerald-700">← 返回列表</Link>
      {flash && <FlashAlert variant="success">{flash}</FlashAlert>}
      {job && (
        <div className="space-y-4 rounded-lg bg-white p-6 text-sm shadow-sm ring-1 ring-gray-200">
          <p><strong>URL:</strong> {job.url}</p>
          <p><strong>状态:</strong> {job.status}</p>
          <p><strong>目标:</strong> {job.target}</p>
          {result?.analysis_source && <p><strong>分析来源:</strong> {result.analysis_source}</p>}
          {job.result_summary && <p><strong>摘要:</strong> {job.result_summary}</p>}
          {result?.titles && result.titles.length > 0 && (
            <div>
              <strong>预览标题（{result.titles.length}）</strong>
              <ul className="mt-1 list-inside list-disc text-gray-700">
                {result.titles.slice(0, 8).map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
            </div>
          )}
          {result?.keywords && result.keywords.length > 0 && (
            <div>
              <strong>预览关键词（{result.keywords.length}）</strong>
              <p className="mt-1 text-gray-700">{result.keywords.slice(0, 12).join(" · ")}</p>
            </div>
          )}
          {result?.knowledge_markdown && job.target === "knowledge" && (
            <div>
              <strong>知识库预览</strong>
              <pre className="mt-1 max-h-48 overflow-auto rounded bg-gray-50 p-2 text-xs whitespace-pre-wrap">
                {result.knowledge_markdown.slice(0, 1200)}
              </pre>
            </div>
          )}
          {job.error_message && <p className="text-red-600">{job.error_message}</p>}
          {job.status === "completed" && (
            <button type="button" onClick={commit} className="rounded-md bg-emerald-600 px-4 py-2 text-white">
              提交入库
            </button>
          )}
        </div>
      )}
    </div>
  );
}
