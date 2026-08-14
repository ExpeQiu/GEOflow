import type { SceneFunnel, SceneFunnelIntent } from "@/lib/strategy-types";
import { TouchpointMindMap } from "./TouchpointMindMap";

export function SceneFunnelView({
  funnel,
  onIntentSelect,
}: {
  funnel: SceneFunnel;
  onIntentSelect?: (intent: SceneFunnelIntent) => void;
}) {
  return <TouchpointMindMap funnel={funnel} onIntentSelect={onIntentSelect} />;
}
