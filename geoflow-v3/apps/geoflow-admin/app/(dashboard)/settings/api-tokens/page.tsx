"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { SecurityRuntimePanel, type SecurityRuntime } from "@/components/admin/SecurityRuntimePanel";
import { SettingsSubNav } from "@/components/admin/SettingsSubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";

type TokenRow = {
  id: number;
  name: string;
  token_prefix: string;
  scopes: string[];
  expires_at: string | null;
  revoked_at: string | null;
  last_used_at: string | null;
};

const SCOPE_LABELS: Record<string, string> = {
  "catalog:read": "目录读取",
  "tasks:read": "任务读取",
  "tasks:write": "任务写入",
  "jobs:read": "作业读取",
  "materials:read": "素材读取",
  "materials:write": "素材写入",
  "articles:read": "文章读取",
  "articles:write": "文章写入",
  "articles:publish": "文章发布",
};

const DEFAULT_SCOPES = Object.keys(SCOPE_LABELS);

function formatDt(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString("zh-CN");
}

export default function ApiTokensPage() {
  const token = useAuthGuard();
  const [items, setItems] = useState<TokenRow[]>([]);
  const [availableScopes, setAvailableScopes] = useState<string[]>(DEFAULT_SCOPES);
  const [runtime, setRuntime] = useState<SecurityRuntime | null>(null);
  const [name, setName] = useState("cli");
  const [scopes, setScopes] = useState<string[]>(DEFAULT_SCOPES);
  const [expiresDays, setExpiresDays] = useState(30);
  const [createdToken, setCreatedToken] = useState("");
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    const data = await apiGet<{
      items: TokenRow[];
      available_scopes?: string[];
      default_ttl_days?: number;
      security_runtime?: SecurityRuntime;
    }>("/api/admin/settings/api-tokens", t);
    setItems(data.items);
    if (data.security_runtime) setRuntime(data.security_runtime);
    if (typeof data.default_ttl_days === "number") {
      setExpiresDays(data.default_ttl_days);
    }
    if (data.available_scopes?.length) {
      setAvailableScopes(data.available_scopes);
      setScopes((prev) => (prev.length ? prev : data.available_scopes!));
    }
  }, []);

  useEffect(() => {
    if (!token) return;
    load().catch(() => setError("无法加载 Token 列表（需超级管理员）"));
  }, [token, load]);

  function toggleScope(scope: string) {
    setScopes((prev) => (prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope]));
  }

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    if (scopes.length === 0) {
      setError("请至少选择一个权限范围");
      return;
    }
    setError("");
    setSaving(true);
    try {
      const res = await apiPost<{ item: { token: string } }>("/api/admin/settings/api-tokens", t, {
        name: name.trim() || "default",
        scopes,
        expires_days: expiresDays,
      });
      setCreatedToken(res.item.token);
      setCopied(false);
      setName("cli");
      await load();
    } catch {
      setError("创建 Token 失败");
    } finally {
      setSaving(false);
    }
  }

  async function onRevoke(id: number) {
    const t = getToken();
    if (!t || !confirm("确认吊销此 Token？吊销后立即失效。")) return;
    try {
      await apiPost(`/api/admin/settings/api-tokens/${id}/revoke`, t);
      await load();
    } catch {
      setError("吊销失败");
    }
  }

  async function copyCreated() {
    if (!createdToken) return;
    try {
      await navigator.clipboard.writeText(createdToken);
      setCopied(true);
    } catch {
      setError("复制失败");
    }
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title={zh.settings.tokens.title} subtitle={zh.settings.tokens.subtitle} />
      <SettingsSubNav />
      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      <div className="mb-6">
        <SecurityRuntimePanel runtime={runtime} variant="tokens" />
      </div>
      <p className="mb-4 text-xs text-gray-500">{zh.settings.tokens.superAdminOnly}</p>
      {createdToken && (
        <FlashAlert variant="success">
          <div className="flex flex-wrap items-center gap-2">
            <span>{zh.settings.tokens.createdOnce}：</span>
            <code className="break-all rounded bg-white/70 px-1.5 py-0.5 text-xs">{createdToken}</code>
            <button type="button" onClick={copyCreated} className="rounded bg-emerald-700 px-2 py-0.5 text-xs text-white">
              {copied ? zh.settings.tokens.copied : zh.settings.tokens.copy}
            </button>
          </div>
        </FlashAlert>
      )}
      <form onSubmit={onCreate} className="mb-6 space-y-4 rounded-lg bg-white p-4 shadow-sm ring-1 ring-gray-200">
        <div className="flex flex-wrap gap-3">
          <label className="text-sm text-gray-600">
            {zh.settings.tokens.name}
            <input
              className="ml-2 rounded-md border px-3 py-2 text-sm"
              placeholder="cli / geoweb"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label className="text-sm text-gray-600">
            {zh.settings.tokens.expires}
            <select
              className="ml-2 rounded-md border px-3 py-2 text-sm"
              value={expiresDays}
              onChange={(e) => setExpiresDays(Number(e.target.value))}
            >
              <option value={7}>{zh.settings.tokens.days7}</option>
              <option value={30}>{zh.settings.tokens.days30}</option>
              <option value={90}>{zh.settings.tokens.days90}</option>
              <option value={365}>{zh.settings.tokens.days365}</option>
            </select>
          </label>
          <button type="submit" disabled={saving} className="rounded-md bg-gray-900 px-4 py-2 text-sm text-white disabled:opacity-50">
            {zh.settings.tokens.create}
          </button>
        </div>
        <div>
          <div className="mb-2 flex items-center gap-3 text-sm text-gray-600">
            <span>{zh.settings.tokens.scopes}</span>
            <button
              type="button"
              className="text-xs text-blue-600 hover:underline"
              onClick={() => setScopes(scopes.length === availableScopes.length ? [] : [...availableScopes])}
            >
              {zh.settings.tokens.selectAll}
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {availableScopes.map((scope) => (
              <label key={scope} className="inline-flex items-center gap-1.5 rounded-md border border-gray-200 bg-gray-50 px-2 py-1 text-xs">
                <input type="checkbox" checked={scopes.includes(scope)} onChange={() => toggleScope(scope)} />
                <span>{SCOPE_LABELS[scope] || scope}</span>
              </label>
            ))}
          </div>
        </div>
      </form>
      {items.length === 0 ? (
        <p className="rounded-lg bg-white px-4 py-8 text-center text-sm text-gray-500 shadow-sm ring-1 ring-gray-200">
          {zh.settings.tokens.empty}
        </p>
      ) : (
        <ul className="divide-y divide-gray-100 rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
          {items.map((row) => (
            <li key={row.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 text-sm">
              <div>
                <div className="font-medium text-gray-900">
                  {row.name}{" "}
                  <span className="font-mono text-xs font-normal text-gray-400">
                    {zh.settings.tokens.prefix} {row.token_prefix}…
                  </span>
                  {row.revoked_at && <span className="ml-2 text-red-600">{zh.settings.tokens.revoked}</span>}
                </div>
                <div className="mt-1 text-xs text-gray-500">
                  {(row.scopes || []).map((s) => SCOPE_LABELS[s] || s).join(" · ") || "—"}
                </div>
                <div className="mt-1 text-xs text-gray-400">
                  {zh.settings.tokens.expires} {formatDt(row.expires_at)} · {zh.settings.tokens.lastUsed}{" "}
                  {row.last_used_at ? formatDt(row.last_used_at) : zh.settings.tokens.neverUsed}
                </div>
              </div>
              {!row.revoked_at && (
                <button type="button" onClick={() => onRevoke(row.id)} className="text-red-600 hover:underline">
                  {zh.settings.tokens.revoke}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
