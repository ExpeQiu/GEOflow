"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { apiPost, apiPut, getToken } from "@/lib/api-client";
import type { DifficultyPanel, OptimizationPanel } from "@/lib/strategy-types";
import { AivisKpiCard, GapPriorityBadge, LayerSection, surfaceCardClass, surfaceInputClass } from "./shared/AivisPrimitives";

function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return `${Number(v).toFixed(digits)}%`;
}

function fmtPp(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  const n = Number(v);
  return `${n > 0 ? "+" : ""}${n.toFixed(1)}pp`;
}

export function OptimizationPanelView({
  data,
  onMarketSaved,
}: {
  data: OptimizationPanel;
  onMarketSaved?: () => void;
}) {
  const readiness = data.readiness;
  const north = data.north_star;
  const actions = data.actions ?? [];
  const ready = Boolean(readiness?.ready);

  const [monthlySearch, setMonthlySearch] = useState(String(data.market_opportunity.monthly_search_volume || 50000));
  const [mau, setMau] = useState(String(data.market_opportunity.ai_platform_mau || 820000000));
  const [regulatory, setRegulatory] = useState("3");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [busySceneId, setBusySceneId] = useState<number | null>(null);

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
      setMsg("市场/监管参数已保存");
      onMarketSaved?.();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function createGapTask(sceneId: number) {
    const t = getToken();
    if (!t) return;
    setBusySceneId(sceneId);
    try {
      const res = await apiPost<{ theme_id?: number; theme?: { id: number } }>(
        `/api/admin/strategy/monitor/scenes/${sceneId}/create-task`,
        t,
        {},
      );
      const themeId = res.theme_id || res.theme?.id;
      setMsg(
        themeId
          ? `场景 #${sceneId} 主题草稿 #${themeId} 已创建（含挖掘摘要），请到内容生产→主题包确认`
          : `场景 #${sceneId} 主题草稿已创建，请到内容生产→主题包确认`,
      );
      onMarketSaved?.();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "创建主题草稿失败");
    } finally {
      setBusySceneId(null);
    }
  }

  return (
    <div className="space-y-6">
      <section className={`${surfaceCardClass} border-violet-200 bg-violet-50/40 p-5`}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">优化策略决策台</h2>
            <p className="mt-1 text-sm text-gray-600">{readiness?.summary || "基于探针与场景缺口的投入优先级"}</p>
          </div>
          <span
            className={`rounded-full px-3 py-1 text-xs font-semibold ${
              ready ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"
            }`}
          >
            {ready ? "可决策" : "待就绪"}
          </span>
        </div>
        {readiness && (
          <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
            <MiniStat label="监控问题" value={String(readiness.question_count)} />
            <MiniStat label="场景" value={String(readiness.scene_count)} />
            <MiniStat label="探针样本" value={String(readiness.probe_count)} />
            <MiniStat label="竞品" value={String(readiness.competitor_count)} />
          </div>
        )}
        {!!readiness?.blockers?.length && (
          <ul className="mt-3 space-y-1 text-sm text-amber-900">
            {readiness.blockers.map((b) => (
              <li key={b}>· {b}</li>
            ))}
          </ul>
        )}
        {msg && <p className="mt-3 text-sm text-violet-800">{msg}</p>}
      </section>

      <LayerSection title="挖主题" subtitle="正式入口：策略 → 挖掘主题">
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/strategy/theme-mining"
            className="rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700"
          >
            打开挖掘主题 →
          </Link>
          <Link href="/production/themes" className="text-sm text-violet-700 hover:underline">
            主题包确认 →
          </Link>
          {data.priority_scenes[0]?.scene_id ? (
            <button
              type="button"
              disabled={busySceneId === data.priority_scenes[0].scene_id}
              onClick={() => createGapTask(data.priority_scenes[0].scene_id!)}
              className="rounded-md border border-violet-300 px-3 py-2 text-sm text-violet-700 disabled:opacity-50"
            >
              {busySceneId === data.priority_scenes[0].scene_id
                ? "挖掘中…"
                : `快捷：${data.priority_scenes[0].scene_name}`}
            </button>
          ) : null}
        </div>
        {msg && <p className="mt-3 text-sm text-violet-800">{msg}</p>}
      </LayerSection>

      {actions.length > 0 && (
        <LayerSection title="本周优先动作" subtitle="按阻塞与缺口自动排序，可直接跳转执行">
          <div className="grid gap-3 md:grid-cols-2">
            {actions.map((a) => (
              <div key={a.id} className={`${surfaceCardClass} flex flex-col p-4`}>
                <div className="flex items-center gap-2">
                  <PriorityPill priority={a.priority} />
                  <p className="font-medium text-gray-900">{a.title}</p>
                </div>
                <p className="mt-2 flex-1 text-sm text-gray-600">{a.body}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Link href={a.href} className="rounded-md bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-700">
                    {a.cta}
                  </Link>
                  {a.scene_id ? (
                    <button
                      type="button"
                      disabled={busySceneId === a.scene_id}
                      onClick={() => createGapTask(a.scene_id!)}
                      className="rounded-md border border-violet-300 px-3 py-1.5 text-xs text-violet-700 disabled:opacity-50"
                    >
                      {busySceneId === a.scene_id ? "挖掘中…" : "生成主题草稿"}
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </LayerSection>
      )}

      {(north?.probe_count || 0) > 0 && (
        <LayerSection title="北极星现状" subtitle={`口径 ${north?.kpi_track || "open_api"} · 有效样本 ${north?.valid_sample_n ?? "—"}`}>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <AivisKpiCard label="Top3" value={fmtPct(north?.top3_pct)} />
            <AivisKpiCard label="相对竞品" value={fmtPp(north?.gap_vs_leader_top3_pp)} tone="cyan" />
            <AivisKpiCard label="提及率" value={fmtPct(north?.mention_rate_pct, 0)} tone="amber" />
            <AivisKpiCard label="探针" value={String(north?.probe_count ?? 0)} />
          </div>
        </LayerSection>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <LayerSection title="竞品差距" subtitle="决定「追平标杆」所需 lift">
          <div className="grid grid-cols-2 gap-3">
            <AivisKpiCard label="自有可见性" value={fmtPct(data.competitor_gap?.self_visibility_pct)} />
            <AivisKpiCard label="差距" value={fmtPp(data.competitor_gap?.gap_vs_leader)} tone="cyan" />
          </div>
          <p className="mt-3 text-sm text-gray-600">
            竞品：{(data.competitor_gap?.competitors || []).slice(0, 6).join("、") || "未配置"}
            {data.competitor_gap?.lift_needed_pct != null ? ` · 预估 lift ${data.competitor_gap.lift_needed_pct}%` : ""}
          </p>
          <Link href="/strategy/brand" className="mt-2 inline-block text-sm text-violet-700 hover:underline">
            品牌竞品矩阵 →
          </Link>
        </LayerSection>

        <LayerSection title="难度快照" subtitle={data.difficulty?.overall_label || "—"}>
          <div className="grid grid-cols-2 gap-3">
            <AivisKpiCard label="综合难度" value={`${data.difficulty?.overall_score ?? "—"}/5`} tone="amber" />
            <AivisKpiCard
              label="市场竞争"
              value={`${data.difficulty?.market_competition?.score ?? "—"}/5`}
              sub={data.difficulty?.market_competition?.description}
            />
            <AivisKpiCard
              label="实体基础"
              value={`${data.difficulty?.entity_foundation?.score ?? "—"}/5`}
              sub={data.difficulty?.entity_foundation?.description}
              tone="cyan"
            />
            <AivisKpiCard
              label="预估 lift"
              value={data.difficulty?.lift_needed_pct != null ? `${data.difficulty.lift_needed_pct}%` : "—"}
            />
          </div>
          <Link href="/strategy/difficulty" className="mt-3 inline-block text-sm text-violet-700 hover:underline">
            难度详情 →
          </Link>
        </LayerSection>
      </div>

      <LayerSection
        title="平台投入建议"
        subtitle={
          data.platform_recommendations.length
            ? "可见性 40% + 排名 30% + 好感度 30%（仅统计有样本平台）"
            : "需先完成探针扫描后才有可信排序"
        }
      >
        {data.platform_recommendations.length === 0 ? (
          <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-gray-600">
            暂无平台评分。请先在问题库配置对比/决策题，再到数据采集执行全量扫描。
            <div className="mt-2 flex gap-3">
              <Link href="/strategy/question-bank" className="text-violet-700 hover:underline">
                问题库 →
              </Link>
              <Link href="/strategy/collection" className="text-violet-700 hover:underline">
                数据采集 →
              </Link>
            </div>
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-3">
            {data.platform_recommendations.map((p, idx) => (
              <div
                key={p.platform}
                className={`rounded-lg border p-4 ${idx === 0 ? "border-violet-300 bg-violet-50" : "border-slate-200"}`}
              >
                <p className="text-xs text-gray-500">{idx === 0 ? "优先投入" : `#${idx + 1}`}</p>
                <p className="text-lg font-semibold">{p.label}</p>
                <p className="text-2xl font-bold text-violet-700">{p.score} 分</p>
                <p className="mt-1 text-xs text-gray-600">{p.reason || `可见性 ${p.visibility_pct}%`}</p>
                {p.sample_n != null && <p className="mt-1 text-[11px] text-gray-400">样本 {p.sample_n}</p>}
              </div>
            ))}
          </div>
        )}
      </LayerSection>

      {data.insights.length > 0 && (
        <LayerSection title="策略洞察">
          <ul className="space-y-3">
            {data.insights.map((i) => (
              <li key={String(i.id)} className={`${surfaceCardClass} px-4 py-3 text-sm`}>
                <span className="font-medium text-gray-900">{i.title}</span>
                <span className="text-gray-600"> — {i.body}</span>
              </li>
            ))}
          </ul>
        </LayerSection>
      )}

      <details className={`${surfaceCardClass} p-5`}>
        <summary className="cursor-pointer text-sm font-semibold text-gray-900">高级：市场机会参数（人工标定）</summary>
        <p className="mt-2 text-xs text-gray-500">
          月搜索量 / AI 月活为外部标定输入，不替代探针 KPI；用于报告叙述与难度参考。
        </p>
        <p className="mt-2 text-sm text-violet-900">{data.market_opportunity.summary}</p>
        <form onSubmit={saveMarket} className="mt-4 grid gap-2 md:grid-cols-4">
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
        </form>
      </details>

      {msg && <p className="text-sm text-gray-600">{msg}</p>}
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-violet-100 bg-white/80 px-3 py-2">
      <p className="text-[11px] text-gray-500">{label}</p>
      <p className="text-lg font-semibold text-gray-900">{value}</p>
    </div>
  );
}

function PriorityPill({ priority }: { priority: string }) {
  const tone =
    priority === "high"
      ? "bg-rose-100 text-rose-800"
      : priority === "medium"
        ? "bg-amber-100 text-amber-900"
        : "bg-slate-100 text-slate-700";
  const label = priority === "high" ? "高优" : priority === "medium" ? "中优" : "低优";
  return <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${tone}`}>{label}</span>;
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
