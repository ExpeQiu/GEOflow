"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { SettingsSubNav } from "@/components/admin/SettingsSubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiDelete, apiGet, apiPatch, apiPost, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";

type AdminRow = {
  id: number;
  username: string;
  role: string;
  status: string;
  display_name: string;
  email: string;
  last_login: string | null;
  is_self?: boolean;
};

type LogRow = {
  id: number;
  action: string;
  created_at: string | null;
  username?: string;
  resource_type?: string;
  resource_id?: string;
  detail?: string;
};

const ACTION_LABEL: Record<string, string> = {
  "admin.create": "创建管理员",
  "admin.update": "更新管理员",
  "admin.toggle": "切换状态",
  "admin.delete": "删除管理员",
  "api_token.create": "创建 Token",
  "api_token.revoke": "吊销 Token",
  "security.password_change": "修改密码",
  "security.sensitive_words": "保存敏感词",
};

function formatDt(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString("zh-CN");
}

function errorMessage(err: unknown, fallback: string): string {
  const raw = err instanceof Error ? err.message : "";
  if (raw.includes("cannot_delete_self")) return zh.settings.admins.cannotDeleteSelf;
  if (raw.includes("cannot_delete_last_admin") || raw.includes("cannot_disable_last_admin")) {
    return zh.settings.admins.cannotDeleteLast;
  }
  if (raw.includes("username_exists")) return "用户名已存在";
  return fallback;
}

export default function AdminsSettingsPage() {
  const token = useAuthGuard();
  const [admins, setAdmins] = useState<AdminRow[]>([]);
  const [logs, setLogs] = useState<LogRow[]>([]);
  const [form, setForm] = useState({ username: "", password: "", display_name: "", email: "" });
  const [editId, setEditId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState({ display_name: "", password: "", email: "" });
  const [flash, setFlash] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    const [a, l] = await Promise.all([
      apiGet<{ items: AdminRow[] }>("/api/admin/settings/admins", t),
      apiGet<{ items: LogRow[] }>("/api/admin/settings/activity-logs", t),
    ]);
    setAdmins(a.items);
    setLogs(l.items);
  }, []);

  useEffect(() => {
    if (!token) return;
    load().catch(() => setError("无法加载管理员列表"));
  }, [token, load]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    setError("");
    setSaving(true);
    try {
      await apiPost("/api/admin/settings/admins", t, form);
      setForm({ username: "", password: "", display_name: "", email: "" });
      setFlash("已添加管理员");
      await load();
    } catch (err) {
      setError(errorMessage(err, "添加失败"));
    } finally {
      setSaving(false);
    }
  }

  async function toggleAdmin(id: number) {
    const t = getToken();
    if (!t) return;
    setError("");
    try {
      await apiPost(`/api/admin/settings/admins/${id}/toggle-status`, t);
      await load();
    } catch (err) {
      setError(errorMessage(err, "切换状态失败"));
    }
  }

  async function removeAdmin(row: AdminRow) {
    const t = getToken();
    if (!t) return;
    if (row.is_self) {
      setError(zh.settings.admins.cannotDeleteSelf);
      return;
    }
    if (!confirm(`确认删除管理员 ${row.username}？`)) return;
    setError("");
    try {
      await apiDelete(`/api/admin/settings/admins/${row.id}`, t);
      setFlash("已删除");
      await load();
    } catch (err) {
      setError(errorMessage(err, "删除失败"));
    }
  }

  async function saveAdminEdit() {
    const t = getToken();
    if (!t || editId === null) return;
    setError("");
    try {
      await apiPatch(`/api/admin/settings/admins/${editId}`, t, editForm);
      setEditId(null);
      setFlash("已更新");
      await load();
    } catch (err) {
      setError(errorMessage(err, "保存失败"));
    }
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title={zh.settings.admins.title} subtitle={zh.settings.admins.subtitle} />
      <SettingsSubNav />
      {flash && <FlashAlert variant="success">{flash}</FlashAlert>}
      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      <form onSubmit={onSubmit} className="mb-6 grid gap-2 rounded-lg bg-white p-4 shadow-sm ring-1 ring-gray-200 md:grid-cols-5">
        <input
          className="rounded-md border px-3 py-2 text-sm"
          placeholder={zh.settings.admins.username}
          value={form.username}
          onChange={(e) => setForm({ ...form, username: e.target.value })}
          minLength={3}
          required
        />
        <input
          className="rounded-md border px-3 py-2 text-sm"
          placeholder={zh.settings.admins.password}
          type="password"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          minLength={6}
          required
        />
        <input
          className="rounded-md border px-3 py-2 text-sm"
          placeholder={zh.settings.admins.displayName}
          value={form.display_name}
          onChange={(e) => setForm({ ...form, display_name: e.target.value })}
        />
        <input
          className="rounded-md border px-3 py-2 text-sm"
          placeholder={zh.settings.admins.email}
          type="email"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
        />
        <button type="submit" disabled={saving} className="rounded-md bg-gray-900 px-3 py-2 text-sm text-white disabled:opacity-50">
          {zh.settings.admins.add}
        </button>
      </form>
      <div className="grid gap-6 lg:grid-cols-2">
        {admins.length === 0 ? (
          <p className="rounded-lg bg-white px-4 py-8 text-center text-sm text-gray-500 shadow-sm ring-1 ring-gray-200">
            {zh.settings.admins.empty}
          </p>
        ) : (
          <ul className="divide-y rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
            {admins.map((a) => (
              <li key={a.id} className="px-4 py-3 text-sm">
                {editId === a.id ? (
                  <div className="flex flex-wrap items-center gap-2">
                    <input
                      className="rounded border px-2 py-1"
                      value={editForm.display_name}
                      onChange={(e) => setEditForm({ ...editForm, display_name: e.target.value })}
                      placeholder={zh.settings.admins.displayName}
                    />
                    <input
                      className="rounded border px-2 py-1"
                      type="email"
                      value={editForm.email}
                      onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                      placeholder={zh.settings.admins.email}
                    />
                    <input
                      className="rounded border px-2 py-1"
                      type="password"
                      value={editForm.password}
                      onChange={(e) => setEditForm({ ...editForm, password: e.target.value })}
                      placeholder="新密码（可选）"
                    />
                    <button type="button" onClick={saveAdminEdit} className="text-blue-600">
                      {zh.common.save}
                    </button>
                    <button type="button" onClick={() => setEditId(null)} className="text-gray-500">
                      {zh.common.cancel}
                    </button>
                  </div>
                ) : (
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-medium text-gray-900">
                        {a.username}
                        {a.is_self && (
                          <span className="ml-2 rounded-full bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-blue-700">
                            {zh.settings.admins.me}
                          </span>
                        )}
                        <span
                          className={
                            a.status === "active"
                              ? "ml-2 rounded-full bg-emerald-50 px-1.5 py-0.5 text-[10px] text-emerald-700"
                              : "ml-2 rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500"
                          }
                        >
                          {a.status === "active" ? "启用" : "停用"}
                        </span>
                      </div>
                      <div className="mt-1 text-xs text-gray-500">
                        {a.display_name || "—"} · {a.role} · {a.email || "无邮箱"}
                      </div>
                      <div className="mt-1 text-xs text-gray-400">
                        {zh.settings.admins.lastLogin} {a.last_login ? formatDt(a.last_login) : zh.settings.admins.neverLogin}
                      </div>
                    </div>
                    <span className="flex shrink-0 gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setEditId(a.id);
                          setEditForm({ display_name: a.display_name || "", password: "", email: a.email || "" });
                        }}
                        className="text-violet-600"
                      >
                        编辑
                      </button>
                      <button type="button" onClick={() => toggleAdmin(a.id)} className="text-blue-600">
                        {zh.settings.admins.toggle}
                      </button>
                      <button type="button" onClick={() => removeAdmin(a)} className="text-red-600">
                        {zh.common.delete}
                      </button>
                    </span>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
        <div className="rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
          <h2 className="border-b px-4 py-3 text-sm font-semibold text-gray-900">{zh.settings.admins.logsTitle}</h2>
          {logs.length === 0 ? (
            <p className="px-4 py-8 text-center text-sm text-gray-500">{zh.settings.admins.logsEmpty}</p>
          ) : (
            <ul className="max-h-80 divide-y overflow-y-auto">
              {logs.map((l) => (
                <li key={l.id} className="px-4 py-2 text-xs text-gray-600">
                  <span className="font-medium text-gray-800">{ACTION_LABEL[l.action] || l.action}</span>
                  {l.username ? <span className="text-gray-400"> · {l.username}</span> : null}
                  {l.detail ? <span> · {l.detail}</span> : null}
                  <div className="text-gray-400">{formatDt(l.created_at)}</div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
