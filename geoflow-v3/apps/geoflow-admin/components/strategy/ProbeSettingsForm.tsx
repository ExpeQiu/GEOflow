"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiGet, apiPatch, getToken } from "@/lib/api-client";
import type { MonitorSettings } from "@/lib/strategy-types";
import { platformLabel, surfaceCardClass, surfaceInputClass } from "./shared/AivisPrimitives";

const ALL_PLATFORMS = ["doubao", "deepseek", "tongyi", "yuanbao", "wenxin", "kimi"] as const;

export function ProbeSettingsForm({ onSaved }: { onSaved?: () => void }) {
  const [settings, setSettings] = useState<MonitorSettings | null>(null);
  const [knowledgeBases, setKnowledgeBases] = useState<Array<{ id: number; name: string }>>([]);
  const [form, setForm] = useState({
    brand_name: "",
    brand_aliases: "",
    probe_mode: "corpus" as MonitorSettings["probe_mode"],
    monitor_platforms: "",
    monitor_scan_limit: 50,
    default_knowledge_base_id: null as number | null,
    selectedPlatforms: [] as string[],
  });
  const [msg, setMsg] = useState("");

  useEffect(() => {
    const t = getToken();
    if (!t) return;
    apiGet<MonitorSettings>("/api/admin/strategy/monitor/settings", t)
      .then((s) => {
        setSettings(s);
        const plats = s.platforms?.length ? s.platforms : ALL_PLATFORMS.slice();
        setForm({
          brand_name: s.brand_name,
          brand_aliases: s.brand_aliases,
          probe_mode: s.probe_mode,
          monitor_platforms: s.monitor_platforms || plats.join(","),
          monitor_scan_limit: s.monitor_scan_limit || 50,
          default_knowledge_base_id: s.default_knowledge_base_id ?? null,
          selectedPlatforms: plats,
        });
      })
      .catch(() => {});

    apiGet<{ items: Array<{ id: number; name: string }> }>("/api/admin/production/knowledge", t)
      .then((res) => setKnowledgeBases(res.items ?? []))
      .catch(() => {});
  }, []);

  function togglePlatform(p: string) {
    setForm((prev) => {
      const exists = prev.selectedPlatforms.includes(p);
      const next = exists ? prev.selectedPlatforms.filter((x) => x !== p) : [...prev.selectedPlatforms, p];
      return { ...prev, selectedPlatforms: next, monitor_platforms: next.join(",") };
    });
  }

  async function save(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    if (form.selectedPlatforms.length === 0) {
      setMsg("请至少选择一个平台");
      return;
    }
    try {
      const payload = {
        brand_name: form.brand_name,
        brand_aliases: form.brand_aliases,
        probe_mode: form.probe_mode,
        monitor_platforms: form.selectedPlatforms.join(","),
        monitor_scan_limit: form.monitor_scan_limit,
        default_knowledge_base_id: form.default_knowledge_base_id,
      };
      const saved = await apiPatch<MonitorSettings>("/api/admin/strategy/monitor/settings", t, payload);
      setSettings(saved);
      setMsg("探针设置已保存");
      onSaved?.();
    } catch {
      setMsg("保存失败");
    }
  }

  if (!settings) return null;

  return (
    <form onSubmit={save} className={`${surfaceCardClass} space-y-3 p-4`}>
      <h3 className="text-sm font-semibold">探针设置（国内 6 平台）</h3>
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
          type="number"
          min={1}
          max={500}
          className={surfaceInputClass}
          placeholder="扫描上限"
          value={form.monitor_scan_limit}
          onChange={(e) => setForm({ ...form, monitor_scan_limit: Number(e.target.value) })}
        />
        <select
          className={surfaceInputClass}
          value={form.default_knowledge_base_id ?? ""}
          onChange={(e) =>
            setForm({
              ...form,
              default_knowledge_base_id: e.target.value ? Number(e.target.value) : null,
            })
          }
        >
          <option value="">默认知识库（缺口分析）</option>
          {knowledgeBases.map((kb) => (
            <option key={kb.id} value={kb.id}>
              {kb.name}
            </option>
          ))}
        </select>
        <button type="submit" className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white">
          保存
        </button>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-gray-500">采集平台：</span>
        {ALL_PLATFORMS.map((p) => (
          <label key={p} className="inline-flex cursor-pointer items-center gap-1 rounded-md bg-gray-50 px-2 py-1">
            <input type="checkbox" checked={form.selectedPlatforms.includes(p)} onChange={() => togglePlatform(p)} />
            {platformLabel(p)}
          </label>
        ))}
      </div>
      {msg && <p className="text-xs text-violet-700">{msg}</p>}
    </form>
  );
}
