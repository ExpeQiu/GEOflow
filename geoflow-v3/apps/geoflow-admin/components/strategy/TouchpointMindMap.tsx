"use client";

import { useMemo, useState } from "react";
import { Briefcase, ChevronDown, MessageCircleWarning, RotateCcw, Sparkles, User, ZoomIn, ZoomOut } from "lucide-react";
import type { SceneFunnel, SceneFunnelIntent } from "@/lib/strategy-types";

const CARD_W = 300;
const PERSONA_H = 84;
const SCENE_H = 80;
const INTENT_H = 80;
const GAP = 16;
const COL = { persona: 0, scene: 360, intent: 720, detail: 1040 };
const CANVAS_W = COL.detail + 280;
const SCALE_MIN = 0.5;
const SCALE_MAX = 1.5;
const SCALE_STEP = 0.1;

type LayoutNode = {
  id: string;
  type: "persona" | "scene" | "intent";
  x: number;
  y: number;
  w: number;
  h: number;
  personaName?: string;
  sceneName?: string;
  intent?: SceneFunnelIntent;
  title: string;
  subtitle: string;
  weightPct?: number;
};

type LayoutEdge = { from: string; to: string };

function needsOptimization(intent: SceneFunnelIntent) {
  return intent.gap_priority === "high" || intent.gap_priority === "medium" || intent.visibility_pct < 40;
}

function sceneIntents(scene: { intents?: SceneFunnelIntent[] }) {
  return scene.intents ?? [];
}

function normalizeFunnel(funnel: SceneFunnel): SceneFunnel {
  return {
    ...funnel,
    personas: (funnel.personas ?? []).map((persona) => ({
      ...persona,
      scenes: (persona.scenes ?? []).map((scene) => ({
        ...scene,
        intents: sceneIntents(scene).map((intent) => ({
          ...intent,
          queries: intent.queries ?? [],
        })),
      })),
    })),
    stats: funnel.stats ?? { persona_count: 0, scene_count: 0, intent_count: 0, query_count: 0 },
  };
}

function buildLayout(funnel: SceneFunnel): { nodes: LayoutNode[]; edges: LayoutEdge[]; height: number } {
  const nodes: LayoutNode[] = [];
  const edges: LayoutEdge[] = [];
  let y = 32;

  for (const persona of funnel.personas) {
    const personaId = `p:${persona.name}`;
    const personaStartY = y;

    let scenesHeight = 0;
    for (const scene of persona.scenes ?? []) {
      const intents = sceneIntents(scene);
      const intentBlock = intents.length * (INTENT_H + GAP) - (intents.length ? GAP : 0);
      scenesHeight += Math.max(SCENE_H, intentBlock || SCENE_H) + GAP;
    }
    if (scenesHeight > 0) scenesHeight -= GAP;
    const blockHeight = Math.max(PERSONA_H, scenesHeight);

    nodes.push({
      id: personaId,
      type: "persona",
      x: COL.persona,
      y: personaStartY + blockHeight / 2 - PERSONA_H / 2,
      w: CARD_W,
      h: PERSONA_H,
      title: persona.name,
      subtitle: "营销图谱",
      weightPct: persona.weight_pct,
    });

    let sceneY = personaStartY;
    for (const scene of persona.scenes ?? []) {
      const sceneId = `s:${persona.name}:${scene.name}`;
      const intents = sceneIntents(scene);
      const intentBlock = intents.length * (INTENT_H + GAP) - (intents.length ? GAP : 0);
      const sceneBlockH = Math.max(SCENE_H, intentBlock || SCENE_H);

      nodes.push({
        id: sceneId,
        type: "scene",
        x: COL.scene,
        y: sceneY + sceneBlockH / 2 - SCENE_H / 2,
        w: CARD_W,
        h: SCENE_H,
        personaName: persona.name,
        sceneName: scene.name,
        title: scene.name,
        subtitle: "使用场景",
        weightPct: scene.weight_pct,
      });
      edges.push({ from: personaId, to: sceneId });

      let intentY = sceneY;
      for (const intent of intents) {
        const intentId = `i:${intent.id}`;
        nodes.push({
          id: intentId,
          type: "intent",
          x: COL.intent,
          y: intentY,
          w: CARD_W,
          h: INTENT_H,
          personaName: persona.name,
          sceneName: scene.name,
          intent,
          title: intent.name,
          subtitle: "用户意图",
        });
        edges.push({ from: sceneId, to: intentId });
        intentY += INTENT_H + GAP;
      }
      sceneY += sceneBlockH + GAP;
    }
    y += blockHeight + 40;
  }

  return { nodes, edges, height: y + 32 };
}

function nodeCenter(node: LayoutNode, side: "left" | "right") {
  const x = side === "right" ? node.x + node.w : node.x;
  return { x, y: node.y + node.h / 2 };
}

function bezierPath(from: LayoutNode, to: LayoutNode) {
  const s = nodeCenter(from, "right");
  const e = nodeCenter(to, "left");
  const mx = (s.x + e.x) / 2;
  return `M ${s.x} ${s.y} C ${mx} ${s.y}, ${mx} ${e.y}, ${e.x} ${e.y}`;
}

function MindMapCard({
  node,
  active,
  onClick,
}: {
  node: LayoutNode;
  active: boolean;
  onClick?: () => void;
}) {
  const icon =
    node.type === "persona" ? (
      <User className="h-4 w-4" />
    ) : node.type === "scene" ? (
      <Briefcase className="h-4 w-4" />
    ) : (
      <MessageCircleWarning className="h-4 w-4" />
    );
  const iconStyle =
    node.type === "persona"
      ? "bg-purple-500/10 text-purple-500"
      : node.type === "scene"
        ? "bg-sky-500/10 text-sky-500"
        : "bg-orange-500/10 text-orange-500";

  return (
    <button
      type="button"
      onClick={onClick}
      className={`absolute z-10 cursor-pointer text-left transition-all duration-300 ${
        active ? "ring-2 ring-violet-300 scale-[1.02]" : "hover:shadow-lg"
      }`}
      style={{ left: node.x, top: node.y, width: node.w, transformOrigin: "left top" }}
    >
      <div
        className={`rounded-[20px] border border-slate-200 bg-white px-5 py-4 ${node.type === "persona" ? "rounded-[22px] px-7 py-6" : ""}`}
        style={{ boxShadow: "0 14px 34px rgba(15,23,42,0.08)", minHeight: node.h }}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${iconStyle}`}>{icon}</div>
            <div className="min-w-0">
              <div className="truncate text-lg font-semibold leading-7 text-slate-900">{node.title}</div>
              <div className="mt-0.5 truncate text-sm text-slate-500">{node.subtitle}</div>
            </div>
          </div>
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-slate-200 text-slate-400">
            <ChevronDown className="h-4 w-4" />
          </div>
        </div>
      </div>
    </button>
  );
}

function IntentDetailPanel({
  intent,
  y,
  onSelectQuery,
}: {
  intent: SceneFunnelIntent;
  y: number;
  onSelectQuery?: (intent: SceneFunnelIntent) => void;
}) {
  const optimize = needsOptimization(intent);
  return (
    <div
      className="absolute z-10 w-[260px]"
      style={{ left: COL.detail, top: Math.max(0, y - 8), transformOrigin: "left top" }}
    >
      <div
        className="relative rounded-[18px] border bg-white px-5 py-4 transition-all hover:border-pink-300 hover:shadow-lg"
        style={{
          borderColor: optimize ? "rgb(244, 163, 184)" : "rgb(226, 232, 240)",
          boxShadow: optimize ? "0 12px 30px rgba(244,114,182,0.12)" : "0 14px 34px rgba(15,23,42,0.08)",
          minHeight: 112,
        }}
      >
        {optimize && (
          <div className="absolute -top-3 left-4 flex items-center gap-1 rounded-full bg-pink-300 px-3 py-1 text-[11px] font-semibold text-pink-950">
            <Sparkles className="h-3 w-3" /> 待优化
          </div>
        )}
        <div className="grid grid-cols-3 gap-3 pt-3 text-center">
          <div>
            <div className="text-2xl font-bold text-slate-900">{intent.visibility_pct}%</div>
            <div className="mt-1 text-sm text-slate-500">可见性</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900">{intent.query_count}</div>
            <div className="mt-1 text-sm text-slate-500">场景问题</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900">{intent.citation_count ?? 0}</div>
            <div className="mt-1 text-sm text-slate-500">引用数</div>
          </div>
        </div>
        {intent.queries?.length ? (
          <ul className="mt-3 space-y-1 border-t border-slate-100 pt-3">
            {intent.queries.slice(0, 3).map((q) => (
              <li key={q.id}>
                <button
                  type="button"
                  onClick={() => onSelectQuery?.(intent)}
                  className="w-full truncate text-left text-xs text-violet-700 hover:underline"
                >
                  💬 {q.text}
                  {(q.citation_count ?? 0) > 0 ? ` (${q.citation_count}引用)` : ""}
                </button>
              </li>
            ))}
          </ul>
        ) : null}
        {intent.node_metadata?.intent_description_kvs ? (
          <div className="mt-2 space-y-1 border-t border-slate-100 pt-2 text-[11px] text-slate-500">
            {Object.entries(intent.node_metadata.intent_description_kvs).slice(0, 2).map(([k, v]) => (
              <p key={k} className="truncate">
                {k}：{v}
              </p>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function clampScale(value: number) {
  return Math.min(SCALE_MAX, Math.max(SCALE_MIN, Math.round(value * 10) / 10));
}

export function TouchpointMindMap({
  funnel,
  onIntentSelect,
}: {
  funnel: SceneFunnel;
  onIntentSelect?: (intent: SceneFunnelIntent) => void;
}) {
  const safeFunnel = useMemo(() => normalizeFunnel(funnel), [funnel]);
  const layout = useMemo(() => buildLayout(safeFunnel), [safeFunnel]);
  const nodeMap = useMemo(() => Object.fromEntries(layout.nodes.map((n) => [n.id, n])), [layout.nodes]);
  const [selectedIntentId, setSelectedIntentId] = useState<string | null>(
    layout.nodes.find((n) => n.type === "intent")?.id ?? null,
  );
  const [scale, setScale] = useState(1);

  const selectedIntent = selectedIntentId ? layout.nodes.find((n) => n.id === selectedIntentId) : null;
  const scaledWidth = CANVAS_W * scale;
  const scaledHeight = layout.height * scale;

  if (safeFunnel.personas.length === 0) {
    return <p className="text-sm text-gray-400">暂无场景图谱，请在下方的场景管理中新增</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-3 text-xs text-gray-500">
          <span>画像 {safeFunnel.stats.persona_count}</span>
          <span>场景 {safeFunnel.stats.scene_count}</span>
          <span>意图 {safeFunnel.stats.intent_count}</span>
          <span>Query {safeFunnel.stats.query_count}</span>
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-gray-50 px-2 py-1.5">
          <button
            type="button"
            aria-label="缩小"
            disabled={scale <= SCALE_MIN}
            onClick={() => setScale((s) => clampScale(s - SCALE_STEP))}
            className="flex h-7 w-7 items-center justify-center rounded-md text-gray-600 hover:bg-white disabled:cursor-not-allowed disabled:opacity-40"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <input
            type="range"
            min={SCALE_MIN * 100}
            max={SCALE_MAX * 100}
            step={SCALE_STEP * 100}
            value={Math.round(scale * 100)}
            onChange={(e) => setScale(clampScale(Number(e.target.value) / 100))}
            className="h-1.5 w-24 cursor-pointer accent-violet-600"
            aria-label="显示比例"
          />
          <span className="min-w-[3rem] text-center text-xs font-medium text-gray-600">{Math.round(scale * 100)}%</span>
          <button
            type="button"
            aria-label="放大"
            disabled={scale >= SCALE_MAX}
            onClick={() => setScale((s) => clampScale(s + SCALE_STEP))}
            className="flex h-7 w-7 items-center justify-center rounded-md text-gray-600 hover:bg-white disabled:cursor-not-allowed disabled:opacity-40"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
          <button
            type="button"
            aria-label="重置显示比例"
            onClick={() => setScale(1)}
            className="flex h-7 w-7 items-center justify-center rounded-md text-gray-600 hover:bg-white"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      <div className="overflow-auto rounded-xl border border-slate-200/60 bg-white p-4">
        <div style={{ width: scaledWidth, height: scaledHeight, minWidth: 900 * scale }}>
          <div
            className="relative"
            style={{
              width: CANVAS_W,
              height: layout.height,
              transform: `scale(${scale})`,
              transformOrigin: "top left",
            }}
          >
          <svg className="pointer-events-none absolute inset-0 h-full w-full overflow-visible" aria-hidden="true">
            {layout.edges.map((edge) => {
              const from = nodeMap[edge.from];
              const to = nodeMap[edge.to];
              if (!from || !to) return null;
              const active =
                selectedIntentId &&
                (edge.to === selectedIntentId ||
                  edge.from === selectedIntentId ||
                  (selectedIntent?.personaName &&
                    (from.id === `p:${selectedIntent.personaName}` ||
                      to.id === `s:${selectedIntent.personaName}:${selectedIntent.sceneName}`)));
              return (
                <path
                  key={`${edge.from}-${edge.to}`}
                  d={bezierPath(from, to)}
                  fill="none"
                  stroke={active ? "rgba(167,139,250,0.85)" : "rgba(199,210,254,0.65)"}
                  strokeWidth={active ? 20 : 14}
                  strokeLinecap="round"
                  className="transition-all duration-300"
                />
              );
            })}
          </svg>

          {layout.nodes.map((node) => (
            <MindMapCard
              key={node.id}
              node={node}
              active={selectedIntentId === node.id}
              onClick={
                node.type === "intent"
                  ? () => {
                      setSelectedIntentId(node.id);
                      if (node.intent) onIntentSelect?.(node.intent);
                    }
                  : undefined
              }
            />
          ))}

          {selectedIntent?.intent && (
            <IntentDetailPanel
              intent={selectedIntent.intent}
              y={selectedIntent.y}
              onSelectQuery={onIntentSelect}
            />
          )}
          </div>
        </div>
      </div>
    </div>
  );
}
