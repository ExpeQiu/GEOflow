import { zh } from "@/lib/i18n/zh";

export type NavKey = "dashboard" | "production_hub" | "operations_hub" | "strategy_hub" | "site_settings";

export const TOP_NAV: { key: NavKey; href: string; label: string; group?: string }[] = [
  { key: "dashboard", href: "/dashboard", label: zh.nav.dashboard },
  { key: "strategy_hub", href: "/strategy/diagnosis", label: zh.nav.strategyHub, group: zh.nav.groupStrategy },
  { key: "production_hub", href: "/production/overview", label: zh.nav.productionHub, group: zh.nav.groupProduction },
  { key: "operations_hub", href: "/operations/overview", label: zh.nav.operationsHub, group: zh.nav.groupOperations },
];

export type HubTone = "emerald" | "blue" | "violet";

export type HubNavItem = { key: string; label: string; href: string; matchPrefixes?: string[] };

export function resolveActiveNav(pathname: string): NavKey {
  if (pathname.startsWith("/production")) return "production_hub";
  if (pathname.startsWith("/operations")) return "operations_hub";
  if (pathname.startsWith("/strategy")) return "strategy_hub";
  if (pathname.startsWith("/settings")) return "site_settings";
  return "dashboard";
}

export const KNOWLEDGE_HUB_PREFIXES = [
  "/production/knowledge",
  "/production/rag-sandbox",
  "/production/knowledge-settings",
  "/production/tech-assets",
  "/production/url-import",
] as const;

export const KNOWLEDGE_SUB_NAV: HubNavItem[] = [
  { key: "bases", label: zh.production.knowledgeSub.bases, href: "/production/knowledge" },
  { key: "rag-sandbox", label: zh.production.knowledgeSub.ragSandbox, href: "/production/rag-sandbox" },
  { key: "settings", label: zh.production.knowledgeSub.settings, href: "/production/knowledge-settings" },
  { key: "tech-assets", label: zh.production.knowledgeSub.techAssets, href: "/production/tech-assets" },
];

export const AI_CONFIG_HUB_PREFIXES = [
  "/production/ai_config",
  "/production/ai-models",
  "/production/ai-prompts",
  "/production/ai-agents",
] as const;

export const AI_CONFIG_SUB_NAV: HubNavItem[] = [
  { key: "orchestration", label: zh.production.aiConfigSub.orchestration, href: "/production/ai_config" },
  { key: "models", label: zh.production.aiConfigSub.models, href: "/production/ai-models" },
  { key: "prompts", label: zh.production.aiConfigSub.prompts, href: "/production/ai-prompts" },
  { key: "agents", label: zh.production.aiConfigSub.agents, href: "/production/ai-agents" },
];

export const PRODUCTION_NAV: HubNavItem[] = [
  { key: "overview", label: zh.production.tabs.overview, href: "/production/overview" },
  {
    key: "ai_config",
    label: zh.production.tabs.ai_config,
    href: "/production/ai_config",
    matchPrefixes: [...AI_CONFIG_HUB_PREFIXES],
  },
  { key: "materials", label: zh.production.tabs.materials, href: "/production/materials" },
  {
    key: "knowledge",
    label: zh.production.tabs.knowledge,
    href: "/production/knowledge",
    matchPrefixes: [...KNOWLEDGE_HUB_PREFIXES],
  },
  { key: "geo-eval", label: zh.production.tabs["geo-eval"], href: "/production/geo-eval" },
];

export const OPERATIONS_NAV: HubNavItem[] = [
  { key: "overview", label: zh.operations.tabs.overview, href: "/operations/overview" },
  { key: "tasks", label: zh.operations.tabs.tasks, href: "/operations/tasks" },
  { key: "articles", label: zh.operations.tabs.articles, href: "/operations/articles" },
  { key: "distribution", label: zh.operations.tabs.distribution, href: "/operations/distribution" },
  { key: "distribution-citations", label: zh.operations.tabs.distributionCitations, href: "/operations/distribution-citations" },
];

export const STRATEGY_NAV: HubNavItem[] = [
  { key: "diagnosis", label: zh.strategy.tabs.diagnosis, href: "/strategy/diagnosis" },
  { key: "collection", label: zh.strategy.tabs.collection, href: "/strategy/collection" },
  { key: "question-bank", label: zh.strategy.tabs.questionBank, href: "/strategy/question-bank" },
  { key: "brand", label: zh.strategy.tabs.brand, href: "/strategy/brand" },
  { key: "product", label: zh.strategy.tabs.product, href: "/strategy/product" },
  { key: "scene-graph", label: zh.strategy.tabs.sceneGraph, href: "/strategy/scene-graph" },
  { key: "optimization", label: zh.strategy.tabs.optimization, href: "/strategy/optimization" },
  { key: "difficulty", label: zh.strategy.tabs.difficulty, href: "/strategy/difficulty" },
  { key: "reports", label: zh.strategy.tabs.reports, href: "/strategy/reports" },
  { key: "gold-labels", label: zh.strategy.tabs.goldLabels, href: "/strategy/gold-labels" },
  { key: "sales-copy", label: zh.strategy.tabs.salesCopy, href: "/strategy/sales-copy" },
  { key: "web-intel", label: zh.strategy.tabs["web-intel"], href: "/strategy/web-intel" },
  { key: "simulator", label: zh.strategy.tabs.simulator, href: "/strategy/simulator" },
];

export const HUB_TONE_CLASS: Record<HubTone, { active: string; inactive: string }> = {
  emerald: { active: "bg-emerald-100 text-emerald-800", inactive: "text-gray-600 hover:bg-gray-50" },
  blue: { active: "bg-blue-100 text-blue-800", inactive: "text-gray-600 hover:bg-gray-50" },
  violet: { active: "bg-violet-100 text-violet-800", inactive: "text-gray-600 hover:bg-gray-50" },
};
