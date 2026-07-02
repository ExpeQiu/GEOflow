"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import { PRODUCTION_NAV } from "@/lib/nav-config";

type JobDetail = {
  id: number;
  url: string;
  target: string;
  name: string;
  status: string;
  error_message?: string;
  result_summary?: string;
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
    await apiPost(`/api/admin/production/url-import/${jobId}/commit`, t);
    setFlash("已提交入库");
    const d = await apiGet<{ job: JobDetail }>(`/api/admin/production/url-import/${jobId}`, t);
    setJob(d.job);
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title={`URL 导入 #${jobId}`} subtitle="任务详情与提交" />
      <HubNav items={PRODUCTION_NAV} tone="emerald" />
      <Link href="/production/url-import" className="mb-4 inline-block text-sm text-emerald-700">← 返回列表</Link>
      {flash && <FlashAlert variant="success">{flash}</FlashAlert>}
      {job && (
        <div className="space-y-3 rounded-lg bg-white p-6 text-sm shadow-sm ring-1 ring-gray-200">
          <p><strong>URL:</strong> {job.url}</p>
          <p><strong>状态:</strong> {job.status}</p>
          <p><strong>目标:</strong> {job.target}</p>
          {job.result_summary && <p><strong>结果:</strong> {job.result_summary}</p>}
          {job.error_message && <p className="text-red-600">{job.error_message}</p>}
          {job.status === "completed" && (
            <button type="button" onClick={commit} className="rounded-md bg-emerald-600 px-4 py-2 text-white">提交入库</button>
          )}
        </div>
      )}
    </div>
  );
}
