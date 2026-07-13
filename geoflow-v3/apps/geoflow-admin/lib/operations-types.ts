export type OpsStats = {
  total_tasks: number;
  active_tasks: number;
  running_jobs: number;
  pending_jobs: number;
  failed_jobs: number;
  total_articles: number;
  published_articles: number;
  pending_review: number;
  channels_total: number;
  channels_active: number;
  distribution_pending: number;
  distribution_failed: number;
};

export type AdminTask = {
  id: number;
  name: string;
  status: string;
  publish_scope: string;
  content_format: string;
  created_count: number;
  published_count: number;
  loop_count: number;
  article_limit: number;
  publish_interval: number;
  model_selection_mode: string;
  ai_model_name: string;
  created_at: string | null;
  last_run_at: string | null;
  batch_status: string | null;
  batch_error_message: string;
};

export type AdminArticle = {
  id: number;
  title: string;
  status: string;
  review_status: string;
  eval_status: string;
  content_format: string;
  task_id: number | null;
  view_count: number;
  published_at: string | null;
  created_at: string | null;
};

export type ArticleStats = {
  total: number;
  published: number;
  draft: number;
  pending_review: number;
};

export type DistributionChannelRow = {
  id: number;
  name: string;
  channel_type: string;
  status: string;
  pending: number;
  failed: number;
  synced: number;
};

export type DistributionJobRow = {
  id: number;
  article_id: number;
  channel_id: number;
  status: string;
  remote_url: string | null;
  error_message: string;
  updated_at: string | null;
};

export type DistributionStats = {
  total: number;
  active: number;
  pending: number;
  failed: number;
  synced: number;
  jobs_total: number;
};

export type DistributionPanelPayload = {
  stats: DistributionStats;
  channels: DistributionChannelRow[];
  recent_jobs: DistributionJobRow[];
  citation_summary?: DistributionCitationSummary;
};

export type DistributionCitationKpis = {
  monitored_questions: number;
  visibility_pct: number;
  citation_source_count: number;
  article_cited_count: number;
  distributed_article_count: number;
  not_indexed_count: number;
  positive_rate_pct: number | null;
  negative_rate_pct: number | null;
};

export type DistributionCitationKpiDelta = {
  monitored_questions?: number | null;
  visibility_pct?: number | null;
  citation_source_count?: number | null;
  article_cited_count?: number | null;
  positive_rate_pct?: number | null;
  negative_rate_pct?: number | null;
};

export type DistributionCitationAlert = {
  type: string;
  severity: string;
  message: string;
  count?: number;
};

export type DistributionCitationSummary = {
  distributed_count: number;
  indexed_count: number;
  not_indexed_count: number;
  last_refreshed_at: string | null;
};

export type DistributionCitationOverview = {
  period_days: number;
  has_probe_data: boolean;
  cache_ready: boolean;
  last_refreshed_at: string | null;
  kpis: DistributionCitationKpis;
  kpis_delta: DistributionCitationKpiDelta;
  alerts: DistributionCitationAlert[];
  contribution: {
    cited_articles: number;
    citation_sources: number;
    platform_coverage: number;
  };
  domain_chart: { domain: string; count: number }[];
  articles_preview: DistributedArticleCitation[];
};

export type DistributedArticleCitation = {
  article_id: number;
  title: string;
  primary_url: string | null;
  index_status: "indexed" | "not_indexed" | "pending_scan" | "not_distributed";
  citation_count: number;
  scene_question_count: number;
  platforms: string[];
  platform_labels: string[];
  match_types: string[];
  distributions: {
    distribution_id: number;
    channel_id: number;
    channel_name: string;
    channel_type: string;
    remote_url: string | null;
    synced_at: string | null;
  }[];
  citations?: {
    id: number;
    title: string;
    url: string;
    domain: string;
    platform: string;
    platform_label: string;
    question_id: number | null;
    question_text: string;
    match_type: string;
  }[];
};

export type ArticleCitationDetail = DistributedArticleCitation & {
  status: string;
  article: { id: number; title: string; slug: string };
  stats: {
    citation_count: number;
    scene_question_count: number;
    platform_count: number;
  };
};
