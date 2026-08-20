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
    strict_api: false,
    remediation_delay_hours: 72,
    gap_rag_score_threshold: 0.3,
    official_domains: "",
    competitor_domains: "",
    wiki_domains: "",
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
          strict_api: Boolean(s.strict_api),
          remediation_delay_hours: s.remediation_delay_hours ?? 72,
          gap_rag_score_threshold: s.gap_rag_score_threshold ?? 0.3,
          official_domains: s.official_domains || "",
          competitor_domains: s.competitor_domains || "",
          wiki_domains: s.wiki_domains || "",
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
        strict_api: form.strict_api,
        remediation_delay_hours: form.remediation_delay_hours,
        gap_rag_score_threshold: form.gap_rag_score_threshold,
        official_domains: form.official_domains,
        competitor_domains: form.competitor_domains,
        wiki_domains: form.wiki_domains,
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
      {settings.ai_mock_mode && (
        <p className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">
          当前 AI_MOCK_MODE=true：RAG/LLM 走 Mock。非 mock E2E：`.env` 设 AI_MOCK_MODE=false，探针模式选「真实
          API」，打开 strict_api，并配置 DEEPSEEK_API_KEY / DOUBAO_API_KEY。
        </p>
      )}
      {!settings.ai_mock_mode && form.probe_mode === "api" && (
        <p className="rounded-md bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
          非 Mock + API 模式：超限写 engine=skipped（认 ai_models.daily_limit）；daily 扫描仅 priority≥探针标准
          floor（默认 80）。金标对照见「金标对照」Tab。
        </p>
      )}
      <div className="rounded-md border border-emerald-100 bg-emerald-50/50 px-3 py-2 text-xs text-emerald-900">
        <p className="font-medium">四套 scheme 不要混进日扫</p>
        <ul className="mt-1 list-disc pl-4 space-y-0.5">
          <li>日扫 = open_api（C 轨 KPI）</li>
          <li>框架轨 / 引用轨 / C 端金标均为独立扫描，metric 隔离</li>
          <li>GEOweb 域名自动记入 official（当前 {settings.geoweb_base_url || "未配置"}），第三方百科才是 wiki</li>
        </ul>
      </div>
      <div className="rounded-md border border-violet-100 bg-violet-50/40 px-3 py-2 text-xs text-violet-900">
        <p className="font-medium">非 mock 验收清单</p>
        <ul className="mt-1 list-disc pl-4 space-y-0.5">
          <li>AI_MOCK_MODE=false（当前 {settings.ai_mock_mode ? "未关闭" : "已关闭"}）</li>
          <li>探针模式=api + strict_api（防 corpus 填洞）</li>
          <li>平台建议 doubao,deepseek；题量受 monitor_scan_limit 与 priority floor 双重约束</li>
          <li>在「AI 模型」为平台配置 daily_limit，打满后 KPI 可见 skipped</li>
        </ul>
      </div>
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
        <label className="inline-flex items-center gap-2 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={form.strict_api}
            onChange={(e) => setForm({ ...form, strict_api: e.target.checked })}
          />
          严格 API（禁止降级污染）
        </label>
        <input
          type="number"
          min={0}
          max={720}
          className={surfaceInputClass}
          placeholder="补缺再扫延迟(小时)"
          value={form.remediation_delay_hours}
          onChange={(e) => setForm({ ...form, remediation_delay_hours: Number(e.target.value) })}
          title="发布后延迟多少小时再扫同场景"
        />
        <input
          type="number"
          min={0.05}
          max={0.95}
          step={0.05}
          className={surfaceInputClass}
          placeholder="RAG 缺口阈值"
          value={form.gap_rag_score_threshold}
          onChange={(e) => setForm({ ...form, gap_rag_score_threshold: Number(e.target.value) })}
        />
        <button type="submit" className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white">
          保存
        </button>
      </div>
      <input
        className={surfaceInputClass}
        placeholder="官方域名（逗号分隔，GEOweb 会自动并入）"
        value={form.official_domains}
        onChange={(e) => setForm({ ...form, official_domains: e.target.value })}
      />
      <div className="grid gap-3 md:grid-cols-2">
        <input
          className={surfaceInputClass}
          placeholder="竞品域名（逗号分隔）"
          value={form.competitor_domains}
          onChange={(e) => setForm({ ...form, competitor_domains: e.target.value })}
        />
        <input
          className={surfaceInputClass}
          placeholder="百科域名（默认 wikipedia.org, baike.baidu.com）"
          value={form.wiki_domains}
          onChange={(e) => setForm({ ...form, wiki_domains: e.target.value })}
        />
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
      <p className="text-xs text-gray-500">
        真实闭环建议：probe_mode=api + 勾选严格 API + 平台选豆包/DeepSeek；补缺再扫默认 72 小时（联调可设 0）。
      </p>
      {msg && <p className="text-xs text-violet-700">{msg}</p>}
    </form>
  );
}
