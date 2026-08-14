"use client";

import Link from "next/link";
import { useState } from "react";
import { apiPost, getToken } from "@/lib/api-client";
import type { MonitorScene } from "@/lib/strategy-types";
import { GapPriorityBadge, LayerSection, surfaceCardClass } from "./shared/AivisPrimitives";

type DraftTheme = {
  id: number;
  title: string;
  status: string;
  scene_id?: number | null;
  meta?: { mining?: { longtail_queries?: string[]; thinking_digest?: string } };
};

export function ThemeMiningPanel({
  scenes,
  draftThemes,
  onRefresh,
}: {
  scenes: MonitorScene[];
  draftThemes: DraftTheme[];
  onRefresh?: () => void;
}) {
  const [busySceneId, setBusySceneId] = useState<number | null>(null);
  const [msg, setMsg] = useState("");

  const ranked = [...scenes].sort((a, b) => {
    const pa = a.gap_priority === "high" ? 3 : a.gap_priority === "medium" ? 2 : 1;
    const pb = b.gap_priority === "high" ? 3 : b.gap_priority === "medium" ? 2 : 1;
    if (pb !== pa) return pb - pa;
    return Number(b.gap_rate || 0) - Number(a.gap_rate || 0);
  });

  async function createGapTask(sceneId: number) {
    const t = getToken();
    if (!t) return;
    setBusySceneId(sceneId);
    setMsg("");
    try {
      const res = await apiPost<{ theme_id?: number; theme?: { id: number } }>(
        `/api/admin/strategy/monitor/scenes/${sceneId}/create-task`,
        t,
        {},
      );
      const themeId = res.theme_id || res.theme?.id;
      setMsg(
        themeId
          ? `已生成主题草稿 #${themeId}。请到「内容生产 → 主题包」确认挖掘摘要后启生产。`
          : "已生成主题草稿。请到内容生产→主题包确认。",
      );
      onRefresh?.();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "创建主题草稿失败");
    } finally {
      setBusySceneId(null);
    }
  }

  async function computeGap(sceneId: number) {
    const t = getToken();
    if (!t) return;
    setBusySceneId(sceneId);
    try {
      await apiPost(`/api/admin/strategy/monitor/scenes/${sceneId}/compute-gap`, t, {});
      onRefresh?.();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "计算缺口失败");
    } finally {
      setBusySceneId(null);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-violet-200 bg-violet-50/40 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">挖掘主题</h2>
            <p className="mt-1 text-sm text-gray-600">
              差距场景 → 思考链 / 信源 / 长尾 Query → 主题草稿。监控题只作证据，不作生产标题。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href="/strategy/scene-graph"
              className="rounded-md border border-violet-200 bg-white px-3 py-1.5 text-xs text-violet-700 hover:bg-violet-50"
            >
              场景图谱 →
            </Link>
            <Link
              href="/production/themes"
              className="rounded-md bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-700"
            >
              主题包确认 →
            </Link>
          </div>
        </div>
        {msg && <p className="mt-3 text-sm text-violet-800">{msg}</p>}
      </section>

      <LayerSection title="按缺口挖主题" subtitle="优先高/中缺口场景；生成后到主题包查看挖掘摘要并确认">
        {ranked.length === 0 ? (
          <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-gray-600">
            暂无场景。请先建立场景图谱或导入 TJG 报告。
            <Link href="/strategy/scene-graph" className="mt-2 block text-violet-700 hover:underline">
              去场景图谱 →
            </Link>
          </div>
        ) : (
          <ul className="space-y-2">
            {ranked.map((s) => (
              <li key={s.id} className={`${surfaceCardClass} px-4 py-3`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{s.scene_name}</p>
                    <p className="text-xs text-gray-500">
                      {[s.persona, s.intent].filter(Boolean).join(" · ") || "—"}
                      {` · 权重 ${s.weight_pct ?? 0}% · 缺口 ${(Number(s.gap_rate || 0) * 100).toFixed(0)}%`}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <GapPriorityBadge priority={s.gap_priority} />
                    <button
                      type="button"
                      disabled={busySceneId === s.id}
                      onClick={() => computeGap(s.id)}
                      className="rounded-md border border-gray-200 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-50"
                    >
                      算缺口
                    </button>
                    <button
                      type="button"
                      disabled={busySceneId === s.id}
                      onClick={() => createGapTask(s.id)}
                      className="rounded-md bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-700 disabled:opacity-50"
                    >
                      {busySceneId === s.id ? "挖掘中…" : "生成主题草稿"}
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </LayerSection>

      <LayerSection title="近期主题草稿" subtitle="确认规格与启生产在「内容生产 → 主题包」">
        {draftThemes.length === 0 ? (
          <p className="text-sm text-gray-400">尚无草稿。从上方场景生成后会出现在此。</p>
        ) : (
          <ul className="space-y-2">
            {draftThemes.map((th) => (
              <li key={th.id} className={`${surfaceCardClass} flex flex-wrap items-center justify-between gap-2 px-4 py-3`}>
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    #{th.id} {th.title}
                  </p>
                  <p className="text-xs text-gray-500">
                    状态 {th.status}
                    {th.scene_id ? ` · 场景 #${th.scene_id}` : ""}
                    {th.meta?.mining?.longtail_queries?.length
                      ? ` · 长尾 ${th.meta.mining.longtail_queries.length} 条`
                      : ""}
                  </p>
                </div>
                <Link
                  href="/production/themes"
                  className="rounded-md border border-violet-300 px-3 py-1.5 text-xs text-violet-700 hover:bg-violet-50"
                >
                  去确认 →
                </Link>
              </li>
            ))}
          </ul>
        )}
      </LayerSection>
    </div>
  );
}
