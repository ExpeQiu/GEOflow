"use client";

import { FormEvent, useState } from "react";
import { apiPut, getToken } from "@/lib/api-client";
import type { DifficultyPanel, OptimizationPanel } from "@/lib/strategy-types";
import { AivisKpiCard, GapPriorityBadge, LayerSection, surfaceCardClass, surfaceInputClass } from "./shared/AivisPrimitives";

export function OptimizationPanelView({
  data,
  onMarketSaved,
}: {
  data: OptimizationPanel;
  onMarketSaved?: () => void;
}) {
  const [monthlySearch, setMonthlySearch] = useState(String(data.market_opportunity.monthly_search_volume || 50000));
  const [mau, setMau] = useState(String(data.market_opportunity.ai_platform_mau || 820000000));
  const [regulatory, setRegulatory] = useState("3");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  async function saveMarket(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    setSaving(true);
    setMsg("");
    try {
      await apiPut("/api/admin/settings/site", t, {
        setting_key: "aivis_monthly_search_volume",
        setting_value: String(Number(monthlySearch) || 50000),
        group_name: "aivis",
        value_type: "int",
      });
      await apiPut("/api/admin/settings/site", t, {
        setting_key: "aivis_ai_platform_mau",
        setting_value: String(Number(mau) || 820000000),
        group_name: "aivis",
        value_type: "int",
      });
      await apiPut("/api/admin/settings/site", t, {
        setting_key: "aivis_regulatory_score",
        setting_value: String(Math.max(1, Math.min(5, Number(regulatory) || 3))),
        group_name: "aivis",
        value_type: "int",
      });
      setMsg("市场/监管参数已保存，刷新后生效");
      onMarketSaved?.();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <LayerSection title="市场机会分析">
        <p className="text-lg font-medium text-violet-900">{data.market_opportunity.summary}</p>
        <div className="mt-3 grid grid-cols-2 gap-4 md:grid-cols-3">
          <AivisKpiCard label="月搜索量" value={`${(data.market_opportunity.monthly_search_volume / 10000).toFixed(0)}万+`} />
          <AivisKpiCard label="AI 平台月活" value={`${(data.market_opportunity.ai_platform_mau / 1e8).toFixed(1)} 亿`} tone="cyan" />
        </div>
        <form onSubmit={saveMarket} className={`mt-4 grid gap-2 md:grid-cols-4 ${surfaceCardClass} p-4`}>
          <div>
            <label className="text-xs text-gray-500">月搜索量</label>
            <input className={surfaceInputClass} value={monthlySearch} onChange={(e) => setMonthlySearch(e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-gray-500">AI 平台月活</label>
            <input className={surfaceInputClass} value={mau} onChange={(e) => setMau(e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-gray-500">监管难度 1–5</label>
            <input className={surfaceInputClass} value={regulatory} onChange={(e) => setRegulatory(e.target.value)} />
          </div>
          <div className="flex items-end">
            <button type="submit" disabled={saving} className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white disabled:opacity-50">
              {saving ? "保存中…" : "保存参数"}
            </button>
          </div>
          {msg && <p className="md:col-span-4 text-xs text-gray-600">{msg}</p>}
        </form>
      </LayerSection>

      <LayerSection title="平台选择建议">
        {data.platform_recommendations.length === 0 ? (
          <p className="text-sm text-gray-400">暂无平台评分，请先执行扫描</p>
        ) : (
          <div className="grid gap-3 md:grid-cols-3">
            {data.platform_recommendations.map((p, idx) => (
              <div key={p.platform} className={`rounded-lg border p-4 ${idx === 0 ? "border-violet-300 bg-violet-50" : "border-slate-200"}`}>
                <p className="text-xs text-gray-500">{idx === 0 ? "优先推荐" : `#${idx + 1}`}</p>
                <p className="text-lg font-semibold">{p.label}</p>
                <p className="text-2xl font-bold text-violet-700">{p.score} 分</p>
                <p className="text-xs text-gray-500">可见性 {p.visibility_pct}%</p>
              </div>
            ))}
          </div>
        )}
      </LayerSection>

      <LayerSection title="场景优化优先级 TOP3">
        <ul className="space-y-2">
          {data.priority_scenes.length === 0 ? (
            <li className="text-sm text-gray-400">暂无场景</li>
          ) : (
            data.priority_scenes.map((s) => (
              <li key={s.scene_name} className={`flex items-center justify-between ${surfaceCardClass} px-4 py-3 text-sm`}>
                <span>{s.scene_name}</span>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">缺口 {(s.gap_rate * 100).toFixed(1)}%</span>
                  <GapPriorityBadge priority={s.gap_priority} />
                </div>
              </li>
            ))
          )}
        </ul>
      </LayerSection>

      {data.insights.length > 0 && (
        <LayerSection title="优化建议">
          <ul className="space-y-3">
            {data.insights.map((i) => (
              <li key={i.id} className="text-sm">
                <span className="font-medium">{i.title}</span>
                <span className="text-gray-600"> — {i.body}</span>
              </li>
            ))}
          </ul>
        </LayerSection>
      )}
    </div>
  );
}

export function DifficultyPanelView({ data }: { data: DifficultyPanel }) {
  const dims = [
    { key: "regulatory_compliance", title: "监管合规" },
    { key: "market_competition", title: "市场竞争" },
    { key: "entity_foundation", title: "实体基础" },
  ] as const;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {dims.map(({ key, title }) => {
          const d = data[key];
          return <AivisKpiCard key={key} label={title} value={`${d.score}/5`} sub={d.label} />;
        })}
        <AivisKpiCard label="综合难度" value={`${data.overall_score}/5`} sub={data.overall_label} tone="amber" />
      </div>

      <LayerSection title="维度说明">
        <ul className="space-y-3">
          {dims.map(({ key, title }) => {
            const d = data[key];
            return (
              <li key={key} className={`${surfaceCardClass} px-4 py-3 text-sm`}>
                <div className="flex items-center justify-between">
                  <span className="font-medium">{title}</span>
                  <span className="text-violet-700">
                    {d.score}/5 · {d.label}
                  </span>
                </div>
                <p className="mt-1 text-gray-500">{d.description}</p>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-gray-100">
                  <div className="h-full rounded-full bg-violet-500" style={{ width: `${(d.score / 5) * 100}%` }} />
                </div>
              </li>
            );
          })}
        </ul>
        {data.lift_needed_pct != null && (
          <p className="mt-4 text-sm text-gray-600">达到标杆需提升约 {data.lift_needed_pct}%</p>
        )}
      </LayerSection>
    </div>
  );
}
