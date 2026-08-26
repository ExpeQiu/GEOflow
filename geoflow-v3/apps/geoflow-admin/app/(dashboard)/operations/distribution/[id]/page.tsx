"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiDelete, apiGet, apiPatch, apiPost, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import { OPERATIONS_MORE_NAV, OPERATIONS_NAV } from "@/lib/nav-config";

type ChannelDetail = {
  id: number;
  name: string;
  channel_type: string;
  status: string;
  domain: string;
  endpoint_url: string;
  description: string;
};

export default function DistributionChannelPage() {
  const token = useAuthGuard();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [channel, setChannel] = useState<ChannelDetail | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [health, setHealth] = useState<{ healthy: boolean; message: string } | null>(null);

  useEffect(() => {
    const t = getToken();
    if (!t) return;
    apiGet<{ channel: ChannelDetail }>(`/api/admin/distribution/channels/${id}`, t)
      .then((d) => setChannel(d.channel))
      .catch(() => setError("加载失败"));
  }, [id]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!channel) return;
    const t = getToken();
    if (!t) return;
    setBusy(true);
    try {
      await apiPatch(`/api/admin/distribution/channels/${id}`, t, {
        name: channel.name,
        domain: channel.domain,
        endpoint_url: channel.endpoint_url,
        channel_type: channel.channel_type,
        description: channel.description,
        status: channel.status,
      });
      router.push("/operations/distribution");
    } catch {
      setError("保存失败");
    } finally {
      setBusy(false);
    }
  }

  async function toggle(action: "pause" | "activate") {
    const t = getToken();
    if (!t) return;
    await apiPost(`/api/admin/distribution/channels/${id}/${action}`, t);
    setChannel((c) => (c ? { ...c, status: action === "pause" ? "paused" : "active" } : c));
  }

  async function rotateSecret() {
    const t = getToken();
    if (!t) return;
    const res = await apiPost<{ secret: string }>(`/api/admin/distribution/channels/${id}/rotate-secret`, t);
    alert(`新密钥（请妥善保存）：${res.secret}`);
  }

  async function checkHealth() {
    const t = getToken();
    if (!t) return;
    const res = await apiGet<{ healthy: boolean; message: string }>(`/api/admin/distribution/channels/${id}/health`, t);
    setHealth(res);
  }

  async function removeChannel() {
    const t = getToken();
    if (!t || !confirm("确认删除此渠道？")) return;
    await apiDelete(`/api/admin/distribution/channels/${id}`, t);
    router.push("/operations/distribution");
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title="渠道详情" subtitle="" />
      <HubNav items={OPERATIONS_NAV} moreItems={OPERATIONS_MORE_NAV} tone="blue" />
      <Link href="/operations/distribution" className="mb-4 inline-flex items-center text-sm text-gray-500 hover:text-gray-700">
        <ArrowLeft className="mr-1 h-4 w-4" /> 返回分发列表
      </Link>
      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      {!channel ? (
        <FlashAlert variant="info">{zh.common.loading}</FlashAlert>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4 rounded-lg bg-white p-6 shadow-sm ring-1 ring-gray-200">
          <div>
            <label className="text-sm font-medium text-gray-700">名称</label>
            <input className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" value={channel.name} onChange={(e) => setChannel({ ...channel, name: e.target.value })} />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">域名</label>
            <input className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" value={channel.domain} onChange={(e) => setChannel({ ...channel, domain: e.target.value })} />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Endpoint</label>
            <input className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" value={channel.endpoint_url} onChange={(e) => setChannel({ ...channel, endpoint_url: e.target.value })} />
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="submit" disabled={busy} className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50">保存</button>
            {channel.status === "active" ? (
              <button type="button" onClick={() => toggle("pause")} className="rounded-md border border-gray-300 px-4 py-2 text-sm">暂停</button>
            ) : (
              <button type="button" onClick={() => toggle("activate")} className="rounded-md border border-green-300 px-4 py-2 text-sm text-green-700">激活</button>
            )}
            <button type="button" onClick={rotateSecret} className="rounded-md border border-violet-300 px-4 py-2 text-sm text-violet-700">轮换密钥</button>
            <button type="button" onClick={checkHealth} className="rounded-md border border-cyan-300 px-4 py-2 text-sm text-cyan-700">健康检查</button>
            <button type="button" onClick={removeChannel} className="rounded-md border border-red-200 px-4 py-2 text-sm text-red-600">删除渠道</button>
            <Link href="/operations/distribution/jobs" className="rounded-md border border-gray-300 px-4 py-2 text-sm">查看 Jobs</Link>
          </div>
          {health && (
            <p className={`text-sm ${health.healthy ? "text-green-700" : "text-red-600"}`}>
              健康状态：{health.healthy ? "正常" : "异常"} — {health.message}
            </p>
          )}
        </form>
      )}
    </div>
  );
}
