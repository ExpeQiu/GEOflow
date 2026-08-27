"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { AiConfigSubNav } from "@/components/production/AiConfigSubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiDelete, apiGet, apiPatch, apiPost, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import { PRODUCTION_MORE_NAV, PRODUCTION_NAV } from "@/lib/nav-config";
import { cn } from "@/lib/cn";

type VendorSpec = {
  id: string;
  label: string;
  lobster?: boolean;
  enterprise?: boolean;
  direct_base: string;
  default_chat: string;
  default_embed?: string;
};

type ResourceOption = {
  id: string;
  label: string;
  mode: string;
  desc: string;
};

type ModelRow = {
  id: number;
  name: string;
  model_id: string;
  model_type: string;
  api_url: string;
  status: string;
  vendor: string;
  connection_kind: string;
  resolved_via: string;
  resolved_base_url: string;
  has_api_key: boolean;
};

type ModelsPayload = {
  items: ModelRow[];
  resource?: string;
  resource_label?: string;
  resource_options?: ResourceOption[];
  mode?: string;
  configured_mode?: string;
  enterprise_text_base?: string;
  enterprise_key_configured?: boolean;
  enterprise_ready?: boolean;
  lobster_base?: string;
  token_configured?: boolean;
  ready?: boolean;
  vendors?: VendorSpec[];
  note?: string;
};

const EMPTY_FORM = {
  name: "",
  model_id: "",
  api_key: "",
  api_url: "https://api.openai.com/v1",
  model_type: "chat",
  vendor: "zhipu",
  connection_kind: "inherit",
};

const DEFAULT_RESOURCES: ResourceOption[] = [
  {
    id: "vendor",
    label: "供应商资源",
    mode: "direct",
    desc: "直连通义 / DeepSeek / 智谱等公网 API，需填写厂商 Key",
  },
  {
    id: "geely",
    label: "企业 AI Gateway",
    mode: "enterprise-gateway",
    desc: "经公司 AI Gateway，使用 ENTERPRISE_AI_GATEWAY_API_KEY",
  },
];

export default function AiModelsPage() {
  const token = useAuthGuard();
  const [payload, setPayload] = useState<ModelsPayload | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editId, setEditId] = useState<number | null>(null);
  const [testMsg, setTestMsg] = useState("");
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");
  const [probe, setProbe] = useState("");
  const [switching, setSwitching] = useState(false);

  const vendors = payload?.vendors ?? [];
  const items = payload?.items ?? [];
  const resource = payload?.resource || "auto";
  const resourceOptions = (payload?.resource_options || DEFAULT_RESOURCES).filter((o) =>
    ["vendor", "geely"].includes(o.id),
  );
  const enterpriseMode = payload?.mode === "enterprise-gateway";
  const usesEnterprise =
    form.connection_kind === "enterprise-gateway" ||
    form.connection_kind === "enterprise" ||
    (form.connection_kind === "inherit" && enterpriseMode);
  const usesLobster = form.connection_kind === "lobster";
  const usesGateway = usesEnterprise || usesLobster;

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    const data = await apiGet<ModelsPayload>("/api/admin/ai-models", t);
    setPayload(data);
  }, []);

  useEffect(() => {
    if (token) load().catch(() => setError("无法加载模型列表"));
  }, [token, load]);

  const selectedVendor = useMemo(() => vendors.find((v) => v.id === form.vendor), [vendors, form.vendor]);

  function applyVendor(vendorId: string, modelType = form.model_type) {
    const spec = vendors.find((v) => v.id === vendorId);
    if (!spec) {
      setForm((prev) => ({ ...prev, vendor: vendorId }));
      return;
    }
    const modelId = modelType === "embedding" ? spec.default_embed || spec.default_chat : spec.default_chat;
    setForm((prev) => ({
      ...prev,
      vendor: vendorId,
      name: prev.name || spec.label,
      model_id: modelId,
      api_url: spec.direct_base,
    }));
  }

  async function switchResource(next: string) {
    const t = getToken();
    if (!t || next === resource) return;
    setSwitching(true);
    setError("");
    try {
      const data = await apiPatch<ModelsPayload>("/api/admin/ai-gateway", t, { resource: next });
      setPayload((prev) => ({ ...(prev || { items: [] }), ...data, items: prev?.items ?? [] }));
      setFlash(next === "geely" ? "已切换：企业 AI Gateway" : "已切换：供应商资源（直连）");
      await load();
    } catch {
      setError("切换 API 资源失败（企业 Gateway 需先配 ENTERPRISE_AI_GATEWAY_API_KEY）");
    } finally {
      setSwitching(false);
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    setError("");
    const payloadBody = { ...form };
    try {
      if (editId) {
        if (!payloadBody.api_key) {
          const { api_key: _removed, ...rest } = payloadBody;
          await apiPatch(`/api/admin/ai-models/${editId}`, t, rest);
        } else {
          await apiPatch(`/api/admin/ai-models/${editId}`, t, payloadBody);
        }
        setEditId(null);
      } else {
        await apiPost("/api/admin/ai-models", t, payloadBody);
      }
      setForm(EMPTY_FORM);
      await load();
    } catch {
      setError("保存失败（企业 Gateway 可不填厂商 Key；供应商直连必须填 Key）");
    }
  }

  async function onDelete(id: number) {
    const t = getToken();
    if (!t || !confirm("确认删除？")) return;
    await apiDelete(`/api/admin/ai-models/${id}`, t);
    await load();
  }

  async function onTest(id: number) {
    const t = getToken();
    if (!t) return;
    const res = await apiPost<{ ok: boolean; message: string; mock?: boolean; via?: string }>(
      `/api/admin/ai-models/${id}/test`,
      t,
    );
    setTestMsg(res.mock ? "Mock 模式：连接 OK" : `${res.message}${res.via ? ` · ${res.via}` : ""}`);
  }

  async function onProbeGateway() {
    const t = getToken();
    if (!t) return;
    const res = await apiGet<{
      probe?: { ok?: boolean; status?: number; error?: string };
      probe_url?: string;
      probe_target?: string;
      resource?: string;
    }>("/api/admin/ai-gateway", t);
    const target = res.probe_target === "enterprise-gateway" ? "企业 Gateway" : "Lobster";
    if (res.probe?.ok) setProbe(`${target} 可达 ${res.probe_url} · HTTP ${res.probe.status}`);
    else
      setProbe(
        `${target} 未就绪：${res.probe?.error || `HTTP ${res.probe?.status ?? "—"}`}（请检查 .env 企业 Key 或 Eva :56045）`,
      );
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title={zh.production.tabs.ai_config} subtitle="API 资源开关：供应商直连 或 企业 AI Gateway" />
      <HubNav items={PRODUCTION_NAV} moreItems={PRODUCTION_MORE_NAV} tone="emerald" />
      <AiConfigSubNav />
      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      {flash && <FlashAlert variant="success">{flash}</FlashAlert>}
      {testMsg && <FlashAlert variant="success">{testMsg}</FlashAlert>}
      {probe && <FlashAlert variant={probe.includes("未就绪") ? "error" : "info"}>{probe}</FlashAlert>}

      <section className="mb-6 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold text-gray-900">API 资源开关</h2>
            <p className="mt-0.5 text-xs text-gray-500">{payload?.note}</p>
          </div>
          <button
            type="button"
            onClick={onProbeGateway}
            className="rounded-md border px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
          >
            探测 Gateway
          </button>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {resourceOptions.map((opt) => {
            const active = resource === opt.id || (resource === "auto" && payload?.mode === opt.mode);
            return (
              <button
                key={opt.id}
                type="button"
                disabled={switching}
                onClick={() => switchResource(opt.id)}
                className={cn(
                  "rounded-lg border p-4 text-left transition-colors disabled:opacity-50",
                  active
                    ? "border-slate-900 bg-slate-900 text-white"
                    : "border-gray-200 bg-gray-50 text-gray-800 hover:border-gray-300",
                )}
              >
                <div className="text-sm font-semibold">{opt.label}</div>
                <div className={cn("mt-1 text-xs", active ? "text-slate-200" : "text-gray-500")}>{opt.desc}</div>
                {active && <div className="mt-2 text-[11px] font-medium opacity-80">当前启用</div>}
              </button>
            );
          })}
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-gray-500">
          <span>
            生效：{payload?.resource_label || resource} · 路径 {payload?.mode || "—"}
          </span>
          {payload?.enterprise_key_configured ? (
            <span className="text-emerald-700">已配置 ENTERPRISE_AI_GATEWAY_API_KEY</span>
          ) : (
            <span className="text-amber-700">未配置企业 Key（选企业 Gateway 前请先配）</span>
          )}
          <span className="font-mono text-[11px]">{payload?.enterprise_text_base}</span>
          <button
            type="button"
            disabled={switching}
            onClick={() => switchResource("auto")}
            className="ml-auto text-blue-600 hover:underline disabled:opacity-50"
          >
            恢复跟随 .env
          </button>
        </div>
      </section>

      <form onSubmit={onSubmit} className="mb-6 space-y-3 rounded-lg bg-white p-4 shadow-sm ring-1 ring-gray-200">
        <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
          <select
            className="rounded-md border px-3 py-2 text-sm"
            value={form.vendor}
            onChange={(e) => applyVendor(e.target.value)}
          >
            {(vendors.length ? vendors : [{ id: form.vendor, label: form.vendor }]).map((v) => (
              <option key={v.id} value={v.id}>
                {v.label || v.id}
              </option>
            ))}
          </select>
          <select
            className="rounded-md border px-3 py-2 text-sm"
            value={form.connection_kind}
            onChange={(e) => setForm({ ...form, connection_kind: e.target.value })}
          >
            <option value="inherit">跟随全局开关（推荐）</option>
            <option value="enterprise-gateway">强制企业 AI Gateway</option>
            <option value="lobster">强制 Lobster（遗留/dev）</option>
            <option value="direct">强制供应商直连</option>
          </select>
          <select
            className="rounded-md border px-3 py-2 text-sm"
            value={form.model_type}
            onChange={(e) => {
              const next = e.target.value;
              setForm({ ...form, model_type: next });
              applyVendor(form.vendor, next);
            }}
          >
            <option value="chat">Chat（正文生成）</option>
            <option value="embedding">Embedding（知识库 RAG）</option>
          </select>
          <input
            className="rounded-md border px-3 py-2 text-sm"
            placeholder="显示名"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <input
            className="rounded-md border px-3 py-2 text-sm"
            placeholder="model_id"
            value={form.model_id}
            onChange={(e) => setForm({ ...form, model_id: e.target.value })}
          />
          <input
            className="rounded-md border px-3 py-2 text-sm"
            placeholder="直连 API URL"
            value={form.api_url}
            onChange={(e) => setForm({ ...form, api_url: e.target.value })}
            disabled={usesGateway}
          />
          <input
            className="rounded-md border px-3 py-2 text-sm lg:col-span-3"
            placeholder={
              usesGateway ? "厂商 Key 由企业 Gateway 统一下发，此处不必填" : editId ? "api_key（留空不修改）" : "api_key"
            }
            value={form.api_key}
            onChange={(e) => setForm({ ...form, api_key: e.target.value })}
            disabled={usesGateway && !editId}
          />
        </div>
        {selectedVendor && !selectedVendor.lobster && usesLobster && (
          <p className="text-xs text-amber-700">该厂商不在 Lobster 目录，实际会回退企业 Gateway 或直连。</p>
        )}
        <button type="submit" className="rounded-md bg-emerald-600 px-3 py-2 text-sm text-white">
          {editId ? "更新" : "添加"}
        </button>
      </form>
      <ul className="divide-y divide-gray-100 rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
        {items.map((m) => (
          <li key={m.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm">
            <span>
              {m.name} · {m.model_id} · <span className="text-gray-500">{m.model_type}</span>
              <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600">{m.vendor || "—"}</span>
              <span className="ml-1 rounded bg-blue-50 px-1.5 py-0.5 text-[10px] text-blue-700">
                {m.resolved_via === "enterprise-gateway"
                  ? "企业 Gateway"
                  : m.resolved_via === "lobster"
                    ? "Lobster"
                    : "供应商"}
              </span>
              <span className="ml-2 text-xs text-gray-400">{m.status}</span>
              {m.has_api_key ? "" : " · 无凭证"}
              <div className="mt-1 font-mono text-[11px] text-gray-400">{m.resolved_base_url}</div>
            </span>
            <span className="flex gap-3">
              <button
                type="button"
                onClick={() => {
                  setEditId(m.id);
                  setForm({
                    name: m.name,
                    model_id: m.model_id,
                    api_key: "",
                    api_url: m.api_url,
                    model_type: m.model_type,
                    vendor: m.vendor || "zhipu",
                    connection_kind: m.connection_kind || "inherit",
                  });
                }}
                className="text-emerald-700"
              >
                编辑
              </button>
              <button type="button" onClick={() => onTest(m.id)} className="text-blue-600">
                测试
              </button>
              <button type="button" onClick={() => onDelete(m.id)} className="text-red-600">
                删除
              </button>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
