import { zh } from "@/lib/i18n/zh";

export type NavKey = "dashboard" | "production_hub" | "operations_hub" | "strategy_hub" | "site_settings";

export const TOP_NAV: { key: NavKey; href: string; label: string; group?: string }[] = [
  { key: "dashboard", href: "/dashboard", label: zh.nav.dashboard },
  { key: "production_hub", href: "/production/overview", label: zh.nav.productionHub, group: zh.nav.groupProduction },
  { key: "operations_hub", href: "/operations/overview", label: zh.nav.operationsHub, group: zh.nav.groupOperations },
  { key: "strategy_hub", href: "/strategy/overview", label: zh.nav.strategyHub, group: zh.nav.groupStrategy },
  { key: "site_settings", href: "/settings/site", label: zh.nav.siteSettings },
];

export type HubTone = "emerald" | "blue" | "violet";

export type HubNavItem = { key: string; label: string; href: string };

export function resolveActiveNav(pathname: string): NavKey {
  if (pathname.startsWith("/production")) return "production_hub";
  if (pathname.startsWith("/operations")) return "operations_hub";
  if (pathname.startsWith("/strategy")) return "strategy_hub";
  if (pathname.startsWith("/settings")) return "site_settings";
  return "dashboard";
}

export const PRODUCTION_NAV: HubNavItem[] = [
  { key: "overview", label: zh.production.tabs.overview, href: "/production/overview" },
  { key: "ai_config", label: zh.production.tabs.ai_config, href: "/production/ai_config" },
  { key: "materials", label: zh.production.tabs.materials, href: "/production/materials" },
  { key: "knowledge", label: zh.production.tabs.knowledge, href: "/production/knowledge" },
  { key: "tech-assets", label: zh.nav.techAssets, href: "/production/tech-assets" },
];

export const OPERATIONS_NAV: HubNavItem[] = [
  { key: "overview", label: zh.operations.tabs.overview, href: "/operations/overview" },
  { key: "tasks", label: zh.operations.tabs.tasks, href: "/operations/tasks" },
  { key: "articles", label: zh.operations.tabs.articles, href: "/operations/articles" },
  { key: "distribution", label: zh.operations.tabs.distribution, href: "/operations/distribution" },
];

export const STRATEGY_NAV: HubNavItem[] = [
  { key: "overview", label: zh.strategy.tabs.overview, href: "/strategy/overview" },
  { key: "monitor", label: zh.strategy.tabs.monitor, href: "/strategy/monitor" },
  { key: "web-intel", label: zh.strategy.tabs["web-intel"], href: "/strategy/web-intel" },
  { key: "simulator", label: zh.strategy.tabs.simulator, href: "/strategy/simulator" },
  { key: "geo-eval", label: zh.strategy.tabs["geo-eval"], href: "/strategy/geo-eval" },
  { key: "analytics", label: zh.strategy.tabs.analytics, href: "/strategy/analytics" },
  { key: "insight-templates", label: "洞察模板", href: "/strategy/insight-templates" },
];

export const HUB_TONE_CLASS: Record<HubTone, { active: string; inactive: string }> = {
  emerald: { active: "bg-emerald-100 text-emerald-800", inactive: "text-gray-600 hover:bg-gray-50" },
  blue: { active: "bg-blue-100 text-blue-800", inactive: "text-gray-600 hover:bg-gray-50" },
  violet: { active: "bg-violet-100 text-violet-800", inactive: "text-gray-600 hover:bg-gray-50" },
};
