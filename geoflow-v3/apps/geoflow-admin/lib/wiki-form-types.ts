export const WIKI_PAGE_TYPES = [
  "concept",
  "compare",
  "guide",
  "glossary",
  "data",
  "thread",
  "topic",
  "article",
  "certification",
] as const;

export type WikiPageType = (typeof WIKI_PAGE_TYPES)[number];

export const WIKI_DOMAINS = ["adas", "battery", "edrive", "cockpit", "safety"] as const;

export type WikiFaqItem = { q: string; a: string };

export type WikiPublishGate = {
  ok: boolean;
  errors: string[];
  required: boolean;
  related_count?: number;
  faq_count?: number;
};

export type WikiRelatedOption = {
  id: number;
  path: string;
  title: string;
  type: string;
  slug: string;
};

export type WikiKbItem = { id: number; name: string };

export function wikiPublishGate(pageType: string, related: string[], faq: WikiFaqItem[]): WikiPublishGate {
  const required = pageType === "compare" || pageType === "guide";
  if (!required) return { ok: true, errors: [], required: false };
  const errors: string[] = [];
  if (related.filter((item) => item.trim()).length < 3) errors.push("related_min_3");
  if (faq.filter((item) => item.q.trim() && item.a.trim()).length < 3) errors.push("faq_min_3");
  return { ok: errors.length === 0, errors, required };
}

export type WikiPage = {
  id: number;
  title: string;
  slug: string;
  status: string;
  review_status: string;
  content_format: string;
  wiki_page_type: WikiPageType | string;
  domain: string | null;
  body: string;
  quick_answer: string | null;
  core_takeaway: string | null;
  target_query: string | null;
  related: string[];
  faq: WikiFaqItem[];
  publish_gate?: WikiPublishGate;
  schema_type: string;
  geo_theme_id: string | null;
  tags: string[];
  geoweb_url: string | null;
  geo_content_hash: string | null;
  preview_url: string;
  synced: boolean;
  task_id: number | null;
  theme_id: number | null;
  published_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type WikiStats = {
  total: number;
  visible: number;
  synced: number;
  smoke_hidden: number;
};

export type WikiPanelPayload = {
  pages: WikiPage[];
  stats: WikiStats;
  type_counts: Record<string, number>;
  types: string[];
  domains: string[];
  schema_types: string[];
  geoweb_base_url: string;
  geoweb_sync_enabled: boolean;
};

export type WikiDetailPayload = {
  page: WikiPage;
  types: string[];
  domains: string[];
  schema_types: string[];
  geoweb_base_url: string;
  geoweb_sync_enabled: boolean;
  publish?: {
    url?: string;
    slug?: string;
    dry_run?: boolean;
    type?: string;
    geo_content_hash?: string;
  };
};

export type WikiPagePayload = {
  title: string;
  slug: string;
  wiki_page_type: string;
  body: string;
  domain: string;
  quick_answer: string;
  core_takeaway: string;
  target_query: string;
  related: string[];
  faq: WikiFaqItem[];
  schema_type: string;
  geo_theme_id: string;
  tags: string[];
};

export function emptyWikiPayload(): WikiPagePayload {
  return {
    title: "",
    slug: "",
    wiki_page_type: "concept",
    body: "",
    domain: "",
    quick_answer: "",
    core_takeaway: "",
    target_query: "",
    related: [],
    faq: [],
    schema_type: "TechArticle",
    geo_theme_id: "",
    tags: [],
  };
}

export function wikiPayloadFromPage(page: WikiPage): WikiPagePayload {
  return {
    title: page.title,
    slug: page.slug,
    wiki_page_type: page.wiki_page_type,
    body: page.body,
    domain: page.domain || "",
    quick_answer: page.quick_answer || "",
    core_takeaway: page.core_takeaway || "",
    target_query: page.target_query || "",
    related: page.related || [],
    faq: page.faq?.length ? page.faq : [],
    schema_type: page.schema_type || "TechArticle",
    geo_theme_id: page.geo_theme_id || "",
    tags: page.tags || [],
  };
}

export function suggestWikiSlug(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}
