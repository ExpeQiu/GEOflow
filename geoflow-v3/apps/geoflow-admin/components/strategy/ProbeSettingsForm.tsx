"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiGet, apiPatch, getToken } from "@/lib/api-client";
import type { MonitorSettings } from "@/lib/strategy-types";
import { surfaceCardClass, surfaceInputClass } from "./shared/AivisPrimitives";

export function ProbeSettingsForm() {
  const [settings, setSettings] = useState<MonitorSettings | null>(null);
  const [form, setForm] = useState({
    brand_name: "",
    brand_aliases: "",
    probe_mode: "corpus" as MonitorSettings["probe_mode"],
    monitor_platforms: "",
    monitor_scan_limit: 50,
  });
  const [msg, setMsg] = useState("");

  useEffect(() => {
    const t = getToken();
    if (!t) return;
    apiGet<MonitorSettings>("/api/admin/strategy/monitor/settings", t)
      .then((s) => {
        setSettings(s);
        setForm({
          brand_name: s.brand_name,
          brand_aliases: s.brand_aliases,
          probe_mode: s.probe_mode,
          monitor_platforms: s.monitor_platforms || s.platforms.join(","),
          monitor_scan_limit: s.monitor_scan_limit || 50,
        });
      })
      .catch(() => {});
  }, []);

  async function save(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    try {
      const saved = await apiPatch<MonitorSettings>("/api/admin/strategy/monitor/settings", t, form);
      setSettings(saved);
      setMsg("探针设置已保存");
    } catch {
      setMsg("保存失败");
    }
  }

  if (!settings) return null;

  return (
    <form onSubmit={save} className={`${surfaceCardClass} p-4`}>
      <h3 className="mb-3 text-sm font-semibold">探针设置（国内 6 平台）</h3>
      <div className="grid gap-3 md:grid-cols-4">
        <input
          className={surfaceInputClass}
          placeholder="品牌名称"
          value={form.brand_name}
          onChange={(e) => setForm({ ...form, brand_name: e.target.value })}
        />
        <input
          className={`${surfaceInputClass} md:col-span-2`}
          placeholder="别名（逗号分隔）"
          value={form.brand_aliases}
          onChange={(e) => setForm({ ...form, brand_aliases: e.target.value })}
        />
        <select
          className={surfaceInputClass}
          value={form.probe_mode}
          onChange={(e) => setForm({ ...form, probe_mode: e.target.value as MonitorSettings["probe_mode"] })}
        >
          <option value="corpus">语料</option>
          <option value="llm">LLM 模拟</option>
          <option value="api">真实 API</option>
        </select>
        <input
          className={`${surfaceInputClass} md:col-span-2`}
          placeholder="平台列表（逗号分隔）"
          value={form.monitor_platforms}
          onChange={(e) => setForm({ ...form, monitor_platforms: e.target.value })}
        />
        <input
          type="number"
          className={surfaceInputClass}
          placeholder="扫描上限"
          value={form.monitor_scan_limit}
          onChange={(e) => setForm({ ...form, monitor_scan_limit: Number(e.target.value) })}
        />
        <button type="submit" className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white">
          保存
        </button>
      </div>
      {msg && <p className="mt-2 text-xs text-violet-700">{msg}</p>}
    </form>
  );
}
