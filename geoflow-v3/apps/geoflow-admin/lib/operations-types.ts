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
