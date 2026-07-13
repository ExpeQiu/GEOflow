"use client";

import { FormEvent, useState } from "react";
import { apiPost, getToken } from "@/lib/api-client";
import type { MonitorScene, SceneFunnel, SceneFunnelIntent } from "@/lib/strategy-types";
import { QueryCitationExplorer } from "./QueryCitationExplorer";
import { SceneFunnelView } from "./SceneFunnelView";
import { GapPriorityBadge, LayerSection, surfaceCardClass, surfaceInputClass } from "./shared/AivisPrimitives";

export function SceneGraphPanel({
  scenes,
  funnel,
  onRefresh,
}: {
  scenes: MonitorScene[];
  funnel: SceneFunnel;
  onRefresh?: () => void;
}) {
  const [sceneForm, setSceneForm] = useState({ persona: "", scene_name: "", intent: "", weight_pct: 10 });
  const [selectedIntent, setSelectedIntent] = useState<SceneFunnelIntent | null>(null);

  async function createScene(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t || !sceneForm.scene_name.trim()) return;
    await apiPost("/api/admin/strategy/monitor/scenes", t, sceneForm);
    setSceneForm({ persona: "", scene_name: "", intent: "", weight_pct: 10 });
    onRefresh?.();
  }

  async function createGapTask(sceneId: number) {
    const t = getToken();
    if (!t) return;
    await apiPost(`/api/admin/strategy/monitor/scenes/${sceneId}/create-task`, t, {});
    alert("补缺 Task 已创建");
  }

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-violet-200 bg-violet-50/40 p-5">
        <h2 className="text-lg font-semibold text-gray-900">场景图谱</h2>
        <p className="mt-1 text-sm text-gray-500">用户画像 → 场景 → 意图 → Query → 引用</p>
        <div className="mt-4 flex flex-wrap gap-4 text-sm">
          <span>画像 <strong>{funnel.stats.persona_count}</strong></span>
          <span>场景 <strong>{funnel.stats.scene_count}</strong></span>
          <span>意图 <strong>{funnel.stats.intent_count}</strong></span>
          <span>Query <strong>{funnel.stats.query_count}</strong></span>
        </div>
      </section>

      <LayerSection title="场景图谱分析" subtitle="人群画像 → 使用场景 → 用户意图 → 场景问题">
        <SceneFunnelView funnel={funnel} onIntentSelect={setSelectedIntent} />
      </LayerSection>

      <QueryCitationExplorer sceneId={selectedIntent?.id ?? null} intentLabel={selectedIntent?.name} />

      <LayerSection title="场景管理" subtitle="维护画像、场景、意图与缺口优先级">
        <form onSubmit={createScene} className="mb-4 grid gap-2 md:grid-cols-4">
          <input className={surfaceInputClass} placeholder="用户画像" value={sceneForm.persona} onChange={(e) => setSceneForm({ ...sceneForm, persona: e.target.value })} />
          <input className={surfaceInputClass} placeholder="场景名称" value={sceneForm.scene_name} onChange={(e) => setSceneForm({ ...sceneForm, scene_name: e.target.value })} />
          <input className={surfaceInputClass} placeholder="用户意图" value={sceneForm.intent} onChange={(e) => setSceneForm({ ...sceneForm, intent: e.target.value })} />
          <button type="submit" className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white">添加场景</button>
        </form>
        {scenes.length === 0 ? (
          <p className="text-sm text-gray-400">暂无场景记录</p>
        ) : (
          <table className={`min-w-full divide-y divide-gray-100 ${surfaceCardClass} text-sm`}>
            <thead className="bg-gray-50">
              <tr>
                {["画像", "场景", "意图", "权重%", "缺口率", "优先级", "操作"].map((h) => (
                  <th key={h} className="px-3 py-2 text-left text-xs">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {scenes.map((s) => (
                <tr key={s.id} className="border-t border-gray-100">
                  <td className="px-3 py-2">{s.persona}</td>
                  <td className="px-3 py-2">{s.scene_name}</td>
                  <td className="px-3 py-2">{s.intent}</td>
                  <td className="px-3 py-2">{s.weight_pct}</td>
                  <td className="px-3 py-2">{(s.gap_rate * 100).toFixed(1)}%</td>
                  <td className="px-3 py-2"><GapPriorityBadge priority={s.gap_priority} /></td>
                  <td className="px-3 py-2">
                    <button type="button" className="text-violet-600" onClick={() => createGapTask(s.id)}>创建补缺 Task</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </LayerSection>
    </div>
  );
}
