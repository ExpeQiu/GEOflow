"use client";

import { FormEvent, useState } from "react";
import { apiPost, getToken } from "@/lib/api-client";
import type { SceneFunnel, SceneFunnelIntent } from "@/lib/strategy-types";
import { QueryCitationExplorer } from "./QueryCitationExplorer";
import { SceneFunnelView } from "./SceneFunnelView";
import { LayerSection, surfaceInputClass } from "./shared/AivisPrimitives";

export function SceneGraphPanel({
  funnel,
  onRefresh,
}: {
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

  return (
    <div className="space-y-6">
      <LayerSection title="场景管理" subtitle="维护画像、场景、意图与缺口优先级">
        <form onSubmit={createScene} className="mb-4 grid gap-2 md:grid-cols-4">
          <input
            className={surfaceInputClass}
            placeholder="用户画像"
            value={sceneForm.persona}
            onChange={(e) => setSceneForm({ ...sceneForm, persona: e.target.value })}
          />
          <input
            className={surfaceInputClass}
            placeholder="场景名称"
            value={sceneForm.scene_name}
            onChange={(e) => setSceneForm({ ...sceneForm, scene_name: e.target.value })}
          />
          <input
            className={surfaceInputClass}
            placeholder="用户意图"
            value={sceneForm.intent}
            onChange={(e) => setSceneForm({ ...sceneForm, intent: e.target.value })}
          />
          <button type="submit" className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white">
            添加场景
          </button>
        </form>
      </LayerSection>

      <LayerSection title="场景图谱分析" subtitle="人群画像 → 使用场景 → 用户意图 → 场景问题；点选意图后可跳转挖掘主题">
        <SceneFunnelView funnel={funnel} onIntentSelect={setSelectedIntent} />
      </LayerSection>

      <QueryCitationExplorer sceneId={selectedIntent?.id ?? null} intentLabel={selectedIntent?.name} />
    </div>
  );
}
