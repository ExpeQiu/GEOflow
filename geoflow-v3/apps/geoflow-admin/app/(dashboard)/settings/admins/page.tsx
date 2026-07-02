"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiDelete, apiGet, apiPatch, apiPost, getToken } from "@/lib/api-client";

type AdminRow = { id: number; username: string; role: string; status: string; display_name: string };

export default function AdminsSettingsPage() {
  const token = useAuthGuard();
  const [admins, setAdmins] = useState<AdminRow[]>([]);
  const [logs, setLogs] = useState<{ id: number; action: string; created_at: string }[]>([]);
  const [form, setForm] = useState({ username: "", password: "", display_name: "" });
  const [editId, setEditId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState({ display_name: "", password: "" });

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    const [a, l] = await Promise.all([
      apiGet<{ items: AdminRow[] }>("/api/admin/settings/admins", t),
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

  async function toggleAdmin(id: number) {
    const t = getToken();
    if (!t) return;
    await apiPost(`/api/admin/settings/admins/${id}/toggle-status`, t);
    await load();
  }

  async function removeAdmin(id: number) {
    const t = getToken();
    if (!t || !confirm("确认删除管理员？")) return;
    await apiDelete(`/api/admin/settings/admins/${id}`, t);
    await load();
  }

  async function saveAdminEdit() {
    const t = getToken();
    if (!t || editId === null) return;
    await apiPatch(`/api/admin/settings/admins/${editId}`, t, editForm);
    setEditId(null);
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
        <ul className="divide-y rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
          {admins.map((a) => (
            <li key={a.id} className="px-4 py-3 text-sm">
              {editId === a.id ? (
                <div className="flex flex-wrap items-center gap-2">
                  <input className="rounded border px-2 py-1" value={editForm.display_name} onChange={(e) => setEditForm({ ...editForm, display_name: e.target.value })} placeholder="显示名" />
                  <input className="rounded border px-2 py-1" type="password" value={editForm.password} onChange={(e) => setEditForm({ ...editForm, password: e.target.value })} placeholder="新密码（可选）" />
                  <button type="button" onClick={saveAdminEdit} className="text-blue-600">保存</button>
                  <button type="button" onClick={() => setEditId(null)} className="text-gray-500">取消</button>
                </div>
              ) : (
                <div className="flex items-center justify-between">
                  <span>{a.username} · {a.display_name || "—"} · {a.role} · {a.status}</span>
                  <span className="flex gap-2">
                    <button type="button" onClick={() => { setEditId(a.id); setEditForm({ display_name: a.display_name || "", password: "" }); }} className="text-violet-600">编辑</button>
                    <button type="button" onClick={() => toggleAdmin(a.id)} className="text-blue-600">切换状态</button>
                    <button type="button" onClick={() => removeAdmin(a.id)} className="text-red-600">删除</button>
                  </span>
                </div>
              )}
            </li>
          ))}
        </ul>
        <ul className="max-h-80 divide-y overflow-y-auto rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
          {logs.map((l) => (
            <li key={l.id} className="px-4 py-2 text-xs text-gray-600">{l.action} · {l.created_at}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
