export type FlowNodeAction = {
  href: string;
  label: string;
  primary?: boolean;
  warning?: boolean;
};

export type FlowNode = {
  key: string;
  title: string;
  desc: string;
  icon: string;
  tone: string;
  status: string;
  metrics: string[];
  actions: FlowNodeAction[];
};

export type Recommendation = {
  count: number;
  title: string;
  desc: string;
  icon: string;
  style: string;
  badge: string;
  href: string;
  button: string;
};

export type NavigationLaneRow = {
  title: string;
  desc: string;
  href: string;
  icon: string;
  count: number | string;
};

export type NavigationLane = {
  title_key: string;
  rows: NavigationLaneRow[];
};

export type DashboardAutomationPayload = {
  running_badge_count: number;
  attention_badge_count: number;
  flow_nodes: FlowNode[];
  recommendations: Recommendation[];
  lanes: NavigationLane[];
};

export type DashboardPayload = {
  version: string;
  site_name: string;
  stats: {
    total_articles: number;
    published_articles: number;
    draft_articles: number;
    pending_review: number;
    total_tasks: number;
    active_tasks: number;
    running_jobs: number;
    pending_jobs: number;
    failed_jobs: number;
    tech_ip_assets_count: number;
    knowledge_bases: number;
    knowledge_chunks: number;
    vectorized_chunks: number;
    chat_models: number;
    embedding_models: number;
    ai_used_today: number;
    total_prompts: number;
    body_prompts: number;
    special_prompts: number;
    channels_total: number;
    channels_active: number;
    distribution_pending: number;
    distribution_failed: number;
    eval_pending: number;
    eval_failed: number;
    eval_passed: number;
    today_articles: number;
    today_views: number;
  };
  automation: DashboardAutomationPayload;
};

export type SiteSettingsPayload = {
  app_name: string;
  version: string;
  geo_eval_enabled: boolean;
  geo_eval_wiki_gate_enabled: boolean;
  geo_eval_hard_gate?: boolean;
  tech_brand_mode: boolean;
  public_site_enabled: boolean;
  ai_mock_mode: boolean;
  gweb_sync_enabled?: boolean;
  geoweb_sync_enabled: boolean;
  geoweb_base_url?: string;
};
