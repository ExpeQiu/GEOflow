"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import { OPERATIONS_NAV } from "@/lib/nav-config";

type JobRow = {
  id: number;
  article_id: number;
  article_title: string;
  channel_id: number;
  channel_name: string;
  status: string;
  error_message: string;
};

export default function DistributionJobsPage() {
  const token = useAuthGuard();
  const [jobs, setJobs] = useState<JobRow[]>([]);

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    const data = await apiGet<{ jobs: JobRow[] }>("/api/admin/distribution/jobs", t);
    setJobs(data.jobs);
  }, []);

  useEffect(() => {
    if (token) load().catch(() => undefined);
  }, [token, load]);

  async function retry(id: number) {
    const t = getToken();
    if (!t) return;
    await apiPost(`/api/admin/distribution/jobs/${id}/retry`, t);
    await load();
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title={zh.distribution.jobsTitle} subtitle="" />
      <HubNav items={OPERATIONS_NAV} tone="blue" />
      <Link href="/operations/distribution" className="mb-4 inline-block text-sm text-blue-600">← 返回分发概览</Link>
      <div className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {["Job", "文章", "渠道", "状态", "错误", "操作"].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {jobs.map((j) => (
              <tr key={j.id}>
                <td className="px-4 py-3 text-sm">#{j.id}</td>
                <td className="px-4 py-3 text-sm">{j.article_title || `#${j.article_id}`}</td>
                <td className="px-4 py-3 text-sm">{j.channel_name || `#${j.channel_id}`}</td>
                <td className="px-4 py-3 text-sm">{j.status}</td>
                <td className="max-w-xs truncate px-4 py-3 text-sm text-gray-500">{j.error_message || "—"}</td>
                <td className="px-4 py-3 text-sm">
                  {j.status === "failed" && (
                    <button type="button" onClick={() => retry(j.id)} className="text-blue-600 hover:text-blue-700">重试</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
