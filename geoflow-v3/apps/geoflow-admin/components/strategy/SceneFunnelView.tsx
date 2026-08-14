import type { SceneFunnel, SceneFunnelIntent } from "@/lib/strategy-types";
import { TouchpointMindMap } from "./TouchpointMindMap";

export function SceneFunnelView({
  funnel,
  onIntentSelect,
  onGenerateTheme,
  themeBusySceneId,
}: {
  funnel: SceneFunnel;
  onIntentSelect?: (intent: SceneFunnelIntent) => void;
  onGenerateTheme?: (sceneId: number) => void;
  themeBusySceneId?: number | null;
}) {
  return (
    <TouchpointMindMap
      funnel={funnel}
      onIntentSelect={onIntentSelect}
      onGenerateTheme={onGenerateTheme}
      themeBusySceneId={themeBusySceneId}
    />
  );
}
