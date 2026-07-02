export type GeoEvalSummary = {
  pending_eval: number;
  passed: number;
  failed: number;
  skipped: number;
};

export type GateConfig = {
  enabled: boolean;
  gate_enabled: boolean;
  rollout_percent: number;
};

export type TechBrandMetrics = {
  total_assets: number;
  p0_total: number;
  p0_ready: number;
  p0_coverage_pct: number;
  wiki_articles: number;
  wiki_compliance_pct: number;
  gweb_sync_total: number;
  gweb_sync_success: number;
  gweb_sync_rate_pct: number;
  needs_update_assets: number;
};

export type PlatformSummary = {
  platform: string;
  total: number;
  mentions: number;
  avg_rank: number | null;
};

export type MonitorKpis = {
  question_count: number;
  probe_count: number;
  avg_brand_rank: number | null;
  mention_rate: number;
  platform_summary: PlatformSummary[];
};

export type MonitorQuestion = {
  id: number;
  question_text: string;
  priority: number;
  status: string;
  last_scan_at: string | null;
};

export type MonitorRun = {
  id: number;
  status: string;
  platform: string;
  question_count: number;
  probe_count?: number;
  completed_at: string | null;
};

export type MonitorProbe = {
  id: number;
  platform: string;
  brand_rank: number | null;
  mentioned: boolean;
  snippet: string;
  question_text: string;
  engine?: string;
};

export type MonitorSettings = {
  brand_name: string;
  brand_aliases: string;
  probe_mode: "corpus" | "llm";
  platforms: string[];
  ai_mock_mode: boolean;
};

export type MonitorRunDetail = {
  run: MonitorRun & { started_at: string | null; mention_rate: number };
  probes: MonitorProbe[];
  platform_stats: PlatformSummary[];
};

export type GeoAlert = {
  id: number;
  alert_type: string;
  message: string;
  created_at: string | null;
};

export type EvalFailureRow = {
  article_id: number;
  failure_reason: string;
  rank: number;
  found: boolean;
  updated_at: string | null;
};

export type FailureTopN = { failure_reason: string; total: number };

export type AnalyticsSnapshot = {
  total_articles: number;
  published_articles: number;
  total_views: number;
  active_tasks: number;
  eval_passed: number;
  eval_failed: number;
};

export type TrendPoint = { date: string; count: number };

export type WebSource = {
  id: number;
  url: string;
  label: string;
  fetch_status: string;
  last_fetched_at: string | null;
};

export type InsightTemplate = {
  id: number;
  name: string;
  source_url: string | null;
  eeat_score: number | null;
  created_at: string | null;
};
