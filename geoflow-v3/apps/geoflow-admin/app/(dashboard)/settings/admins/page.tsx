"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPost, getToken } from "@/lib/api-client";

export default function AdminsSettingsPage() {
  const token = useAuthGuard();
  const [admins, setAdmins] = useState<{ id: number; username: string; role: string }[]>([]);
  const [logs, setLogs] = useState<{ id: number; action: string; created_at: string }[]>([]);
  const [form, setForm] = useState({ username: "", password: "", display_name: "" });

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    const [a, l] = await Promise.all([
      apiGet<{ items: typeof admins }>("/api/admin/settings/admins", t),
      apiGet<{ items: typeof logs }>("/api/admin/settings/activity-logs", t),
    ]);
    setAdmins(a.items);
    setLogs(l.items);
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    await apiPost("/api/admin/settings/admins", t, form);
    setForm({ username: "", password: "", display_name: "" });
    await load();
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title="超管" subtitle="管理员与活动日志" />
      <Link href="/settings/site" className="mb-4 inline-block text-sm text-gray-600">← 站点设置</Link>
      <form onSubmit={onSubmit} className="mb-6 grid gap-2 rounded-lg bg-white p-4 shadow-sm ring-1 ring-gray-200 md:grid-cols-4">
        <input className="rounded-md border px-3 py-2 text-sm" placeholder="用户名" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
        <input className="rounded-md border px-3 py-2 text-sm" placeholder="密码" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        <input className="rounded-md border px-3 py-2 text-sm" placeholder="显示名" value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
        <button type="submit" className="rounded-md bg-gray-900 px-3 py-2 text-sm text-white">添加管理员</button>
      </form>
      <div className="grid gap-6 lg:grid-cols-2">
        <ul className="rounded-lg bg-white shadow-sm ring-1 ring-gray-200 divide-y">
          {admins.map((a) => (
            <li key={a.id} className="px-4 py-3 text-sm">{a.username} · {a.role}</li>
          ))}
        </ul>
        <ul className="rounded-lg bg-white shadow-sm ring-1 ring-gray-200 divide-y max-h-80 overflow-y-auto">
          {logs.map((l) => (
            <li key={l.id} className="px-4 py-2 text-xs text-gray-600">{l.action} · {l.created_at}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
