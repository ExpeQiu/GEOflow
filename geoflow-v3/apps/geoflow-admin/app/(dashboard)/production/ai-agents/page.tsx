"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { AiConfigSubNav } from "@/components/production/AiConfigSubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPatch, getToken } from "@/lib/api-client";
import { cn } from "@/lib/cn";
import { zh } from "@/lib/i18n/zh";
import { PRODUCTION_NAV } from "@/lib/nav-config";

type AgentUsage = { workflow: string; node_id: string };

type AgentRow = {
  id: string;
  name: string;
  system_prompt: string;
  system_prompt_preview: string;
  temperature: number;
  output_format: string;
  used_by: AgentUsage[];
};

type FormState = {
  name: string;
  system_prompt: string;
  temperature: number;
  output_format: string;
};

export default function AiAgentsPage() {
  const token = useAuthGuard();
  const [items, setItems] = useState<AgentRow[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const applySelection = useCallback((row: AgentRow) => {
    setSelectedId(row.id);
    setForm({
      name: row.name,
      system_prompt: row.system_prompt,
      temperature: row.temperature,
      output_format: row.output_format,
    });
  }, []);

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    setLoading(true);
    setErr("");
    try {
      const data = await apiGet<{ items: AgentRow[]; config_path: string }>("/api/admin/agents", t);
      const next = data.items ?? [];
      setItems(next);
      if (next.length === 0) {
        setSelectedId(null);
        setForm(null);
        setErr("未读到 Agent 节点（请检查 agents.yml 与 API 路由 /api/admin/agents）");
        return;
      }
      setSelectedId((prev) => {
        const keep = prev ? next.find((a) => a.id === prev) : undefined;
        const pick = keep ?? next[0];
        setForm({
          name: pick.name,
          system_prompt: pick.system_prompt,
          temperature: pick.temperature,
          output_format: pick.output_format,
        });
        return pick.id;
      });
    } catch (ex) {
      setItems([]);
      setSelectedId(null);
      setForm(null);
      setErr(ex instanceof Error ? ex.message : "加载 Agent 配置失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) void load();
  }, [token, load]);

  function onSelect(id: string) {
    const row = items.find((a) => a.id === id);
    if (!row) return;
    applySelection(row);
    setMsg("");
    setErr("");
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t || !selectedId || !form) return;
    setSaving(true);
    setMsg("");
    setErr("");
    try {
      await apiPatch(`/api/admin/agents/${selectedId}`, t, form);
      setMsg("已保存，运行时配置已热刷新");
      await load();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  if (!token) return null;

  const selected = items.find((a) => a.id === selectedId);

  return (
    <div>
      <HubHeader title={zh.production.tabs.ai_config} subtitle={zh.production.aiConfigSub.agents} />
      <HubNav items={PRODUCTION_NAV} tone="emerald" />
      <AiConfigSubNav />

      {msg && <FlashAlert variant="success">{msg}</FlashAlert>}
      {err && <FlashAlert variant="error">{err}</FlashAlert>}

      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-gray-600">
          配置 Content Agent 各节点的人设（system_prompt）。对应编排图里括号中的 agent id；规则节点无 prompt，不在此列表。
        </p>
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-60"
        >
          {loading ? "刷新中…" : "刷新"}
        </button>
      </div>

      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        <ul className="max-h-[70vh] overflow-y-auto divide-y divide-gray-100 rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
          {loading && items.length === 0 && (
            <li className="px-4 py-6 text-sm text-gray-500">加载中…</li>
          )}
          {!loading && items.length === 0 && (
            <li className="px-4 py-6 text-sm text-gray-500">暂无 Agent 节点</li>
          )}
          {items.map((a) => (
            <li key={a.id}>
              <button
                type="button"
                onClick={() => onSelect(a.id)}
                className={cn(
                  "w-full px-4 py-3 text-left text-sm transition-colors",
                  selectedId === a.id ? "bg-emerald-50 text-emerald-900" : "hover:bg-gray-50",
                )}
              >
                <span className="font-medium">{a.name}</span>
                <span className="mt-0.5 block font-mono text-[11px] text-gray-500">{a.id}</span>
                {a.used_by.length > 0 && (
                  <span className="mt-1 block text-[11px] text-gray-400">
                    {a.used_by.map((u) => `${u.workflow}.${u.node_id}`).join(" · ")}
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>

        {form && selected && (
          <form onSubmit={onSubmit} className="space-y-3 rounded-lg bg-white p-5 shadow-sm ring-1 ring-gray-200">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-gray-900">
                {selected.name}{" "}
                <span className="font-mono text-xs font-normal text-gray-500">({selected.id})</span>
              </h3>
              {selected.used_by.length > 0 && (
                <p className="text-xs text-gray-500">
                  引用：{selected.used_by.map((u) => `${u.workflow}/${u.node_id}`).join("、")}
                </p>
              )}
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              <label className="block text-xs text-gray-500">
                显示名
                <input
                  className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                />
              </label>
              <label className="block text-xs text-gray-500">
                Temperature
                <input
                  type="number"
                  min={0}
                  max={2}
                  step={0.1}
                  className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                  value={form.temperature}
                  onChange={(e) => setForm({ ...form, temperature: Number(e.target.value) })}
                  required
                />
              </label>
              <label className="block text-xs text-gray-500 md:col-span-2">
                输出格式
                <select
                  className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                  value={form.output_format}
                  onChange={(e) => setForm({ ...form, output_format: e.target.value })}
                >
                  <option value="markdown">markdown</option>
                  <option value="json">json</option>
                </select>
              </label>
            </div>
            <label className="block text-xs text-gray-500">
              System Prompt
              <textarea
                className="mt-1 min-h-[280px] w-full rounded-md border px-3 py-2 font-mono text-sm leading-relaxed"
                value={form.system_prompt}
                onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
                required
              />
            </label>
            <button
              type="submit"
              disabled={saving}
              className="rounded-md bg-emerald-600 px-4 py-2 text-sm text-white disabled:opacity-60"
            >
              {saving ? "保存中…" : "保存"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
