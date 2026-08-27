"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiGet, apiPatch, apiPost, getToken } from "@/lib/api-client";
import { surfaceCardClass, surfaceInputClass } from "./shared/AivisPrimitives";

type PlatformApiRow = {
  platform: string;
  label: string;
  api_capable: boolean;
  custom?: boolean;
  note?: string;
  connection_kind: string;
  model_id: string;
  api_url: string;
  has_api_key: boolean;
  resolved_via?: string | null;
  resolved_base_url?: string | null;
  resolved_model_id?: string | null;
  ready?: boolean;
  default_model?: string;
  default_base?: string;
};

type CustomPlatform = {
  id: string;
  label: string;
  vendor?: string;
  api_capable: boolean;
  default_model?: string;
  default_base?: string;
  note?: string;
  enabled?: boolean;
};

type ProbeApiConfigPayload = {
  global_mode: string;
  global_mode_options: Array<{ id: string; label: string; desc: string }>;
  enterprise_ready: boolean;
  lobster_ready: boolean;
  ai_mock_mode: boolean;
  platforms: PlatformApiRow[];
  custom_platforms?: CustomPlatform[];
  llm_gateway?: {
    mode?: string;
    enterprise_text_base?: string;
    enterprise_text_model?: string;
    enterprise_key_configured?: boolean;
  };
};

type PlatformForm = {
  connection_kind: string;
  model_id: string;
  api_url: string;
  api_key: string;
};

const EMPTY_CUSTOM = {
  id: "",
  label: "",
  default_model: "",
  default_base: "",
  api_capable: true,
};

function effectiveVia(connectionKind: string, globalMode: string, fallbackMode?: string): string {
  const kind = connectionKind || "inherit";
  if (kind === "enterprise-gateway" || kind === "enterprise") return "enterprise-gateway";
  if (kind === "direct") return "direct";
  if (kind === "lobster") return "lobster";
  if (globalMode === "enterprise-gateway" || globalMode === "geely") return "enterprise-gateway";
  if (globalMode === "lobster") return "lobster";
  if (globalMode === "direct") return "direct";
  if (fallbackMode === "enterprise-gateway" || fallbackMode === "geely") return "enterprise-gateway";
  if (fallbackMode === "lobster") return "lobster";
  return fallbackMode || "direct";
}

function applyGlobalModePreview(
  mode: string,
  forms: Record<string, PlatformForm>,
  rows: PlatformApiRow[],
  payload: ProbeApiConfigPayload,
): Record<string, PlatformForm> {
  const enterpriseBase =
    payload.llm_gateway?.enterprise_text_base || "https://ai-gateway-office.zeekrlife.com/v1";
  const enterpriseModel = payload.llm_gateway?.enterprise_text_model || "gpt-4o";
  const next = { ...forms };

  for (const row of rows) {
    if (!row.api_capable) continue;
    const prev = next[row.platform] ?? {
      connection_kind: "inherit",
      model_id: "",
      api_url: "",
      api_key: "",
    };

    if (mode === "enterprise-gateway" || mode === "geely") {
      const keepOverride = prev.connection_kind === "direct" || prev.connection_kind === "lobster";
      next[row.platform] = {
        ...prev,
        connection_kind: keepOverride ? prev.connection_kind : "inherit",
        api_url: enterpriseBase,
        model_id: prev.model_id || row.default_model || enterpriseModel,
        api_key: "",
      };
    } else if (mode === "direct") {
      next[row.platform] = {
        ...prev,
        connection_kind: prev.connection_kind === "enterprise-gateway" ? "inherit" : prev.connection_kind,
        api_url: row.api_url || row.default_base || "",
        model_id: row.model_id || row.default_model || "",
        api_key: "",
      };
    } else if (mode === "lobster") {
      next[row.platform] = {
        ...prev,
        connection_kind: prev.connection_kind === "direct" ? prev.connection_kind : "inherit",
        api_url: row.resolved_base_url || row.default_base || "",
        model_id: row.model_id || row.default_model || "",
        api_key: "",
      };
    }
  }
  return next;
}

function previewPlatform(
  row: PlatformApiRow,
  form: PlatformForm,
  globalMode: string,
  payload: ProbeApiConfigPayload,
) {
  const via = effectiveVia(form.connection_kind, globalMode, payload.llm_gateway?.mode);
  const enterpriseBase =
    payload.llm_gateway?.enterprise_text_base || "https://ai-gateway-office.zeekrlife.com/v1";
  const enterpriseModel = payload.llm_gateway?.enterprise_text_model || "gpt-4o";

  if (via === "enterprise-gateway") {
    return {
      via,
      gateway: true,
      model_id: form.model_id || row.default_model || enterpriseModel,
      api_url: enterpriseBase,
      has_key: payload.enterprise_ready,
    };
  }
  if (via === "lobster") {
    return {
      via,
      gateway: true,
      model_id: form.model_id || row.default_model || "",
      api_url: row.resolved_base_url || row.default_base || "",
      has_key: payload.lobster_ready,
    };
  }
  return {
    via: "direct",
    gateway: false,
    model_id: form.model_id || row.default_model || "",
    api_url: form.api_url || row.default_base || "",
    has_key: row.has_api_key,
  };
}

export function ProbeApiConfigPanel() {
  const [payload, setPayload] = useState<ProbeApiConfigPayload | null>(null);
  const [globalMode, setGlobalMode] = useState("inherit");
  const [platformForms, setPlatformForms] = useState<Record<string, PlatformForm>>({});
  const [customPlatforms, setCustomPlatforms] = useState<CustomPlatform[]>([]);
  const [newCustom, setNewCustom] = useState(EMPTY_CUSTOM);
  const [msg, setMsg] = useState("");
  const [testMsg, setTestMsg] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    const data = await apiGet<ProbeApiConfigPayload>("/api/admin/strategy/monitor/probe-api-config", t);
    setPayload(data);
    setGlobalMode(data.global_mode || "inherit");
    setCustomPlatforms(data.custom_platforms ?? []);
    const forms: Record<string, PlatformForm> = {};
    for (const row of data.platforms ?? []) {
      forms[row.platform] = {
        connection_kind: row.connection_kind || "inherit",
        model_id: row.model_id || row.default_model || "",
        api_url: row.api_url || row.default_base || "",
        api_key: "",
      };
    }
    const mode = data.global_mode || "inherit";
    setPlatformForms(applyGlobalModePreview(mode, forms, data.platforms ?? [], data));
  }, []);

  useEffect(() => {
    load().catch(() => setMsg("加载 API 配置失败"));
  }, [load]);

  function selectGlobalMode(mode: string) {
    setGlobalMode(mode);
    if (!payload) return;
    setPlatformForms((prev) => applyGlobalModePreview(mode, prev, payload.platforms, payload));
    setTestMsg({});
  }

  function updatePlatform(platform: string, patch: Partial<PlatformForm>) {
    setPlatformForms((prev) => {
      const row = payload?.platforms.find((r) => r.platform === platform);
      const merged = { ...(prev[platform] ?? { connection_kind: "inherit", model_id: "", api_url: "", api_key: "" }), ...patch };
      if (!row || !payload) return { ...prev, [platform]: merged };
      const preview = previewPlatform(row, merged, globalMode, payload);
      return {
        ...prev,
        [platform]: {
          ...merged,
          api_url: preview.gateway ? preview.api_url : merged.api_url,
          model_id: preview.model_id,
        },
      };
    });
  }

  async function save(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    setMsg("");
    try {
      const platforms: Record<string, PlatformForm> = {};
      for (const row of payload?.platforms ?? []) {
        const f = platformForms[row.platform];
        if (!f || !payload) continue;
        const preview = previewPlatform(row, f, globalMode, payload);
        platforms[row.platform] = {
          ...f,
          api_url: preview.gateway ? preview.api_url : f.api_url,
          model_id: preview.model_id,
        };
      }
      const saved = await apiPatch<ProbeApiConfigPayload>(
        "/api/admin/strategy/monitor/probe-api-config",
        t,
        { global_mode: globalMode, platforms, custom_platforms: customPlatforms },
      );
      setPayload(saved);
      setMsg("采集平台 API 配置已保存");
      await load();
    } catch {
      setMsg("保存失败");
    }
  }

  async function testPlatform(platform: string) {
    const t = getToken();
    if (!t) return;
    const res = await apiPost<{ ok: boolean; message: string; mock?: boolean; via?: string }>(
      `/api/admin/strategy/monitor/probe-api-config/${platform}/test`,
      t,
    );
    setTestMsg((prev) => ({
      ...prev,
      [platform]: res.mock ? "Mock OK" : `${res.message}${res.via ? ` · ${res.via}` : ""}`,
    }));
  }

  function addCustomPlatform() {
    const id = newCustom.id.trim().toLowerCase();
    const label = newCustom.label.trim();
    if (!id || !label) {
      setMsg("自定义平台需填写 id 与显示名称");
      return;
    }
    if (!/^[a-z][a-z0-9_-]{1,31}$/.test(id)) {
      setMsg("id 须为小写字母开头，2–32 位字母数字/_/-");
      return;
    }
    if (customPlatforms.some((c) => c.id === id)) {
      setMsg("该平台 id 已存在");
      return;
    }
    setCustomPlatforms((prev) => [
      ...prev,
      {
        id,
        label,
        api_capable: newCustom.api_capable,
        default_model: newCustom.default_model.trim(),
        default_base: newCustom.default_base.trim(),
        enabled: true,
      },
    ]);
    setNewCustom(EMPTY_CUSTOM);
    setMsg("");
  }

  function removeCustomPlatform(id: string) {
    setCustomPlatforms((prev) => prev.filter((c) => c.id !== id));
  }

  if (!payload) return null;

  const modeOptions = payload.global_mode_options ?? [];

  return (
    <form onSubmit={save} className={`${surfaceCardClass} space-y-4 p-4`}>
      <div>
        <h3 className="text-sm font-semibold">采集平台 API 配置</h3>
        <p className="mt-1 text-xs text-gray-500">
          支持企业 AI Gateway 统一鉴权，或各平台供应商直连。元宝 / 文心无 Open API，日扫走 C 端。
        </p>
      </div>

      {payload.ai_mock_mode && (
        <p className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">
          AI_MOCK_MODE=true：探针测试返回 Mock。生产请关闭 Mock 并配置凭证。
        </p>
      )}

      <div className="rounded-md border border-violet-100 bg-violet-50/40 px-3 py-2 text-xs text-violet-900">
        <p className="font-medium">全局路由</p>
        <p className="mt-1">
          企业 Gateway：{payload.enterprise_ready ? "已就绪" : "未配置 Key"} · LLM 页生效模式：
          {payload.llm_gateway?.mode ?? "—"}
        </p>
      </div>

      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {modeOptions.map((opt) => (
          <button
            key={opt.id}
            type="button"
            onClick={() => selectGlobalMode(opt.id)}
            className={`rounded-lg border p-3 text-left text-xs transition-colors ${
              globalMode === opt.id
                ? "border-violet-600 bg-violet-50 text-violet-900"
                : "border-gray-200 bg-gray-50 text-gray-700 hover:border-gray-300"
            }`}
          >
            <div className="font-semibold">{opt.label}</div>
            <div className="mt-1 text-gray-500">{opt.desc}</div>
          </button>
        ))}
      </div>

      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2 text-sm text-gray-500">
          <span>采集平台：</span>
          {payload.platforms.map((row) => (
            <span key={row.platform} className="rounded-md bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
              {row.label}
              {row.custom ? " · 自定义" : ""}
            </span>
          ))}
        </div>

        {payload.platforms.map((row) => {
          const form = platformForms[row.platform] ?? {
            connection_kind: "inherit",
            model_id: "",
            api_url: "",
            api_key: "",
          };
          const preview = previewPlatform(row, form, globalMode, payload);
          const gateway = preview.gateway;
          const displayModel = preview.model_id;
          const displayUrl = preview.api_url;
          return (
            <div
              key={row.platform}
              className="rounded-lg border border-gray-100 bg-gray-50/80 p-3 space-y-2"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900">{row.label}</span>
                  {row.custom && (
                    <span className="rounded bg-violet-100 px-1.5 py-0.5 text-[10px] text-violet-800">
                      自定义
                    </span>
                  )}
                  {!row.api_capable && (
                    <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] text-amber-800">
                      C 端 only
                    </span>
                  )}
                  {preview.via && (
                    <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] text-blue-700">
                      {preview.via === "enterprise-gateway"
                        ? "企业 Gateway"
                        : preview.via === "lobster"
                          ? "Lobster"
                          : "直连"}
                    </span>
                  )}
                </div>
                {row.api_capable && (
                  <button
                    type="button"
                    onClick={() => testPlatform(row.platform)}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    测试连接
                  </button>
                )}
              </div>
              {!row.api_capable && row.note && (
                <p className="text-xs text-gray-500">{row.note}</p>
              )}
              {row.api_capable && (
                <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-4">
                  <select
                    className={surfaceInputClass}
                    value={form.connection_kind}
                    onChange={(e) => updatePlatform(row.platform, { connection_kind: e.target.value })}
                  >
                    <option value="inherit">跟随全局</option>
                    <option value="enterprise-gateway">企业 Gateway</option>
                    <option value="direct">供应商直连</option>
                    <option value="lobster">Lobster（遗留）</option>
                  </select>
                  <input
                    className={surfaceInputClass}
                    placeholder="model_id"
                    value={displayModel}
                    onChange={(e) => updatePlatform(row.platform, { model_id: e.target.value })}
                  />
                  <input
                    className={surfaceInputClass}
                    placeholder="API Base URL"
                    value={displayUrl}
                    disabled={gateway}
                    onChange={(e) => updatePlatform(row.platform, { api_url: e.target.value })}
                  />
                  <input
                    className={surfaceInputClass}
                    placeholder={gateway ? "Key 由 Gateway 统一下发" : "api_key（留空不修改）"}
                    value={form.api_key}
                    disabled={gateway}
                    onChange={(e) => updatePlatform(row.platform, { api_key: e.target.value })}
                  />
                </div>
              )}
              {row.api_capable && displayUrl && (
                <p className="font-mono text-[11px] text-gray-400">
                  解析 → {displayUrl} · {displayModel || "—"}
                  {preview.has_key ? "" : " · 无凭证"}
                </p>
              )}
              {testMsg[row.platform] && (
                <p className="text-xs text-violet-700">{testMsg[row.platform]}</p>
              )}
            </div>
          );
        })}
      </div>

      <div className="rounded-lg border border-dashed border-violet-200 bg-violet-50/30 p-3 space-y-3">
        <div>
          <h4 className="text-sm font-medium text-gray-900">添加自定义被监测平台</h4>
          <p className="mt-1 text-xs text-gray-500">
            id 唯一标识（如 zhipu），保存后可在探针设置中勾选；OpenAI 兼容 API 填 default_base + model。
          </p>
        </div>
        {customPlatforms.length > 0 && (
          <ul className="space-y-1 text-xs text-gray-600">
            {customPlatforms.map((c) => (
              <li key={c.id} className="flex items-center justify-between gap-2 rounded bg-white px-2 py-1">
                <span>
                  <code className="text-violet-700">{c.id}</code> · {c.label}
                  {c.api_capable ? "" : " · C 端 only"}
                </span>
                <button
                  type="button"
                  className="text-red-600 hover:underline"
                  onClick={() => removeCustomPlatform(c.id)}
                >
                  移除
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-5">
          <input
            className={surfaceInputClass}
            placeholder="id（如 zhipu）"
            value={newCustom.id}
            onChange={(e) => setNewCustom({ ...newCustom, id: e.target.value })}
          />
          <input
            className={surfaceInputClass}
            placeholder="显示名称"
            value={newCustom.label}
            onChange={(e) => setNewCustom({ ...newCustom, label: e.target.value })}
          />
          <input
            className={surfaceInputClass}
            placeholder="default_model"
            value={newCustom.default_model}
            onChange={(e) => setNewCustom({ ...newCustom, default_model: e.target.value })}
          />
          <input
            className={surfaceInputClass}
            placeholder="default_base URL"
            value={newCustom.default_base}
            onChange={(e) => setNewCustom({ ...newCustom, default_base: e.target.value })}
          />
          <label className="inline-flex items-center gap-2 text-xs text-gray-600">
            <input
              type="checkbox"
              checked={newCustom.api_capable}
              onChange={(e) => setNewCustom({ ...newCustom, api_capable: e.target.checked })}
            />
            支持 Open API
          </label>
        </div>
        <button
          type="button"
          onClick={addCustomPlatform}
          className="rounded-md border border-violet-300 bg-white px-3 py-1.5 text-xs text-violet-700 hover:bg-violet-50"
        >
          加入列表（保存后生效）
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button type="submit" className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white">
          保存 API 配置
        </button>
        {msg && <p className="text-xs text-violet-700">{msg}</p>}
      </div>
    </form>
  );
}
