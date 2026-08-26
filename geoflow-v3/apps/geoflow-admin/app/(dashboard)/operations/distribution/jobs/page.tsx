"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { DistributionSubNav } from "@/components/operations/DistributionSubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiDelete, apiGet, apiPatch, apiPost, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import { OPERATIONS_MORE_NAV, OPERATIONS_NAV } from "@/lib/nav-config";

type JobRow = {
  id: number;
  article_id: number;
  article_title: string;
  channel_id: number;
  channel_name: string;
  status: string;
  error_message: string;
};

const STATUS_OPTIONS = ["", "pending", "running", "success", "failed"];

export default function DistributionJobsPage() {
  const token = useAuthGuard();
  const [jobs, setJobs] = useState<JobRow[]>([]);
  const [channels, setChannels] = useState<{ id: number; name: string }[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [channelFilter, setChannelFilter] = useState("");

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    const params = new URLSearchParams();
    if (statusFilter) params.set("status", statusFilter);
    if (channelFilter) params.set("channel_id", channelFilter);
    const qs = params.toString() ? `?${params}` : "";
    const [jobsData, distData] = await Promise.all([
      apiGet<{ jobs: JobRow[] }>(`/api/admin/distribution/jobs${qs}`, t),
      apiGet<{ channels: { id: number; name: string }[] }>("/api/admin/distribution", t),
    ]);
    setJobs(jobsData.jobs);
    setChannels(distData.channels.map((c) => ({ id: c.id, name: c.name })));
  }, [statusFilter, channelFilter]);

  useEffect(() => {
    if (token) load().catch(() => undefined);
  }, [token, load]);

  async function retry(id: number) {
    const t = getToken();
    if (!t) return;
    await apiPost(`/api/admin/distribution/jobs/${id}/retry`, t);
    await load();
  }

  async function cancelJob(id: number) {
    const t = getToken();
    if (!t) return;
    await apiPatch(`/api/admin/distribution/jobs/${id}`, t, { status: "cancelled" });
    await load();
  }

  async function removeJob(id: number) {
    const t = getToken();
    if (!t || !confirm("确认删除此 Job？")) return;
    await apiDelete(`/api/admin/distribution/jobs/${id}`, t);
    await load();
  }

  const channelIds = channels.length > 0 ? channels : [...new Set(jobs.map((j) => ({ id: j.channel_id, name: j.channel_name })))];

  if (!token) return null;

  return (
    <div>
      <HubHeader title={zh.distribution.jobsTitle} subtitle="" />
      <HubNav items={OPERATIONS_NAV} moreItems={OPERATIONS_MORE_NAV} tone="blue" />
      <DistributionSubNav />
      <Link href="/operations/distribution" className="mb-4 inline-block text-sm text-blue-600">← 返回分发概览</Link>

      <div className="mb-4 flex flex-wrap gap-3">
        <select
          className="rounded-md border px-3 py-2 text-sm"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">全部状态</option>
          {STATUS_OPTIONS.filter(Boolean).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          className="rounded-md border px-3 py-2 text-sm"
          value={channelFilter}
          onChange={(e) => setChannelFilter(e.target.value)}
        >
          <option value="">全部渠道</option>
          {channelIds.map((c) => (
            <option key={c.id} value={String(c.id)}>{c.name || `渠道 #${c.id}`}</option>
          ))}
        </select>
      </div>

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
            {jobs.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500">暂无匹配的分发任务</td>
              </tr>
            ) : (
              jobs.map((j) => (
                <tr key={j.id}>
                  <td className="px-4 py-3 text-sm">#{j.id}</td>
                  <td className="px-4 py-3 text-sm">{j.article_title || `#${j.article_id}`}</td>
                  <td className="px-4 py-3 text-sm">{j.channel_name || `#${j.channel_id}`}</td>
                  <td className="px-4 py-3 text-sm">{j.status}</td>
                  <td className="max-w-xs truncate px-4 py-3 text-sm text-gray-500">{j.error_message || "—"}</td>
                  <td className="px-4 py-3 text-sm space-x-2">
                    {j.status === "failed" && (
                      <button type="button" onClick={() => retry(j.id)} className="text-blue-600 hover:text-blue-700">重试</button>
                    )}
                    {j.status !== "cancelled" && (
                      <button type="button" onClick={() => cancelJob(j.id)} className="text-amber-600">取消</button>
                    )}
                    <button type="button" onClick={() => removeJob(j.id)} className="text-red-600">删除</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
