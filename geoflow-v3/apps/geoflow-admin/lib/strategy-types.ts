export type GeoEvalSummary = {
  pending_eval: number;
  passed: number;
  failed: number;
  skipped: number;
  advisory?: number;
};

export type GateConfig = {
  enabled: boolean;
  gate_enabled: boolean;
  hard_gate?: boolean;
  wiki_checks_enabled?: boolean;
  mode?: "soft" | "hard" | string;
  rollout_percent: number;
  simulation_pass_score?: number;
  audit_pass_score?: number;
};

export type ProbeStandardsConfig = {
  metric_primary: string;
  footnote_on_bias: boolean;
  do_not_overwrite_open_api_kpi: boolean;
  rank_report_weight: {
    list_order: number;
    first_mention: number;
    unknown: number;
  };
  min_evidence_level: "L0" | "L1" | string;
  forbid_corpus_as_l1: boolean;
  fixture_min_list_acc: number;
  scan_platforms: string;
  priority_floor_daily: number;
  contract_fields?: Array<{ field: string; values: string }>;
  effect_note?: string;
};

export type TechBrandMetrics = {
  total_assets: number;
  p0_total: number;
  p0_ready: number;
  p0_coverage_pct: number;
  wiki_articles: number;
  wiki_compliance_pct: number;
  geoweb_sync_total: number;
  geoweb_sync_success: number;
  geoweb_sync_rate_pct: number;
  /** @deprecated 兼容旧字段 */
  gweb_sync_total?: number;
  gweb_sync_success?: number;
  gweb_sync_rate_pct?: number;
  needs_update_assets: number;
};

export type StrategyOverviewData = {
  geo_eval: GeoEvalSummary;
  tech_brand: TechBrandMetrics;
  monitor: MonitorKpis;
  analytics: AnalyticsSnapshot;
  geoweb_alignment?: GeowebAlignment | null;
  gweb_alignment?: GeowebAlignment | null;
  remediations?: GapRemediation[];
};

export type PlatformSummary = {
  platform: string;
  total: number;
  mentions: number;
  avg_rank: number | null;
  visibility_pct?: number;
  weighted_rank_score?: number | null;
  top3_pct?: number | null;
};

export type MonitorKpis = {
  question_count: number;
  probe_count: number;
  avg_brand_rank: number | null;
  mention_rate: number;
  mention_rate_pct?: number;
  visibility_pct?: number;
  visibility_open_api?: number | null;
  weighted_rank_score?: number | null;
  sentiment_score?: number | null;
  sentiment_negative_pct?: number | null;
  top1_pct?: number | null;
  top3_pct?: number | null;
  top5_pct?: number | null;
  valid_sample_n?: number;
  gap_vs_leader_top3_pp?: number | null;
  self_top3_pct?: number | null;
  leader_top3_pct?: number | null;
  kpi_track?: string;
  platform_summary: PlatformSummary[];
  platform_matrix?: PlatformSummary[];
  engine_mix?: Array<{ engine: string; label: string; count: number }>;
  api_probe_ratio_pct?: number;
  win_rate_pct?: number | null;
  win_rate_samples?: number;
  quality?: {
    param_consistency_pct?: number | null;
    attribution_accuracy_pct?: number | null;
    gate_pass?: boolean | null;
    status?: string;
    threshold?: number;
  };
  source?: {
    official_share_pct?: number | null;
    third_party_share_pct?: number | null;
    target_domain_hits?: number;
    citation_count?: number;
  };
};

export type GeowebAlignment = {
  status: string;
  alignment_pct: number;
  geoweb_page_count: number;
  matched_count: number;
  only_geoweb_count: number;
  only_local_count: number;
  source_url?: string;
  fetch_reason?: string;
  /** @deprecated */
  gweb_page_count?: number;
  only_gweb_count?: number;
};

/** @deprecated 使用 GeowebAlignment */
export type GwebAlignment = GeowebAlignment;

export type GapRemediation = {
  id: number;
  scene_id: number;
  task_id: number | null;
  theme_id?: number | null;
  theme_title?: string;
  status: string;
  gap_rate_at_create: number;
  baseline_visibility_pct: number | null;
  post_visibility_pct: number | null;
  delta_visibility_pct: number | null;
  baseline_top3_pct?: number | null;
  post_top3_pct?: number | null;
  delta_top3_pp?: number | null;
  published_at: string | null;
  rescan_after: string | null;
  created_at: string | null;
  scene_name: string;
};

export type MonitorQuestion = {
  id: number;
  question_text: string;
  priority: number;
  status: string;
  last_scan_at: string | null;
  scene_id?: number | null;
  template_id?: number | null;
  query_type?: string;
  competitor_brands?: string[];
};

export type MonitorQuestionListPage = {
  items: MonitorQuestion[];
  total: number;
  page: number;
  page_size: number;
  stats: {
    total: number;
    brand: number;
    product: number;
    competitor: number;
    active: number;
  };
};

export type QuestionCitationDetail = {
  status: string;
  question?: {
    id: number;
    text: string;
    scene_id: number | null;
    query_type: string;
    priority: number;
    persona: string;
    scene_name: string;
    intent: string;
    visibility_pct: number;
  };
  probes: QueryProbe[];
  stats: {
    probe_count: number;
    citation_count: number;
    unique_domains: number;
    domains: string[];
  };
};

export type MonitorQuestionBulkResult = {
  created: number;
  skipped: number;
  errors: Array<{ index: number; question_text: string; detail: string }>;
  total_input: number;
};

export type MonitorScene = {
  id: number;
  persona: string;
  scene_name: string;
  intent: string;
  weight_pct: number;
  industry: string;
  gap_rate: number;
  gap_priority: string;
  insight_template_id: number | null;
  status: string;
  last_gap_at: string | null;
};

export type QueryTemplate = {
  id: number;
  template_type: string;
  category: string;
  pattern: string;
  scene_id: number | null;
  default_priority: number;
  status: string;
};

export type CompetitorBrand = {
  id: number;
  brand_name: string;
  aliases: string[];
  is_self: boolean;
  status: string;
};

export type MonitorInsight = {
  id: number;
  insight_type: string;
  title: string;
  body: string;
  payload: Record<string, unknown>;
  created_at: string | null;
};

export type MonitorSnapshot = {
  date: string;
  visibility_pct: number;
  weighted_rank_score: number | null;
  sentiment_score: number | null;
  mention_rate: number;
};

export type VisibilityReport = {
  id: number;
  title: string;
  period_start: string | null;
  period_end: string | null;
  status: string;
  html_path: string;
  created_at: string | null;
};

export type CompetitorMatrix = {
  matrix: Array<{ platform: string; brands: Array<{ name: string; is_self: boolean; visibility_pct: number; weighted_rank_score: number | null }> }>;
  self_visibility_pct: number;
  gap_vs_leader: number;
  competitors: string[];
  source?: string;
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
  scheme?: string | null;
  metric_kind?: string | null;
  match_type?: string | null;
};

export type MonitorSettings = {
  brand_name: string;
  brand_aliases: string;
  probe_mode: "corpus" | "llm" | "api";
  monitor_platforms?: string;
  monitor_scan_limit?: number;
  default_knowledge_base_id?: number | null;
  platforms: string[];
  ai_mock_mode: boolean;
  strict_api?: boolean;
  remediation_delay_hours?: number;
  gap_rag_score_threshold?: number;
  official_domains?: string;
  competitor_domains?: string;
  wiki_domains?: string;
  geoweb_base_url?: string;
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
  status?: string;
  simulation_score?: number | null;
  audit_score?: number | null;
  gate_mode?: string | null;
  rank?: number;
  found?: boolean;
  updated_at: string | null;
};

export type FailureTopN = { failure_reason: string; total: number };

/** 虚拟 GEO 仿真：采纳/检索概率结果 */
export type SimulateResult = {
  query: string;
  kb_id?: number | null;
  retrieved_count?: number;
  retrieval_score?: number;
  overlap_score?: number;
  article_in_retrieval?: boolean;
  simulated_answer?: string;
  confidence?: number;
  simulation_score: number;
  adoption_probability?: number;
  retrieval_probability?: number;
  in_context_probability?: number;
  engine?: string;
  pass_threshold?: number;
  passes_threshold?: boolean;
  probability_pct?: number;
  breakdown?: {
    retrieval: number;
    overlap: number;
    confidence: number;
    in_context: number;
    adoption: number;
  };
};

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

export type AivisMetrics = {
  visibility_pct: number;
  visibility_open_api?: number | null;
  weighted_rank_score: number | null;
  sentiment_score: number | null;
  sentiment_negative_pct?: number | null;
  top3_pct?: number | null;
  top5_pct?: number | null;
  mention_rate_pct?: number | null;
  gap_vs_leader_top3_pp?: number | null;
  kpi_track?: string;
  probe_count: number;
};

export type DiagnosisPanel = {
  collection: {
    platform_count: number;
    question_stats: {
      brand_questions: number;
      product_questions: number;
      brand_probes_estimated: number;
      product_probes_estimated: number;
    };
    collection_window: { period_start: string | null; period_end: string | null };
  };
  brand: AivisMetrics;
  product: AivisMetrics;
  optimization: {
    top_platform: { label: string; score: number } | null;
    priority_scenes: Array<{ scene_name: string; gap_rate: number; gap_priority: string }>;
    insights: MonitorInsight[];
    market_summary: string;
  };
  difficulty: {
    regulatory_compliance: number;
    market_competition: number;
    entity_foundation: number;
    overall_score: number;
  };
  latest_report: VisibilityReport | null;
  monitor: MonitorKpis;
};

export type CollectionPanel = {
  platforms: Array<{ platform: string; label: string; probe_count: number }>;
  platforms_next?: Array<{ platform: string; label: string; estimate: number }>;
  platform_count: number;
  question_stats: {
    brand_questions: number;
    product_questions: number;
    competitor_questions: number;
    total_questions: number;
    brand_probes_estimated: number;
    product_probes_estimated: number;
    competitor_probes_estimated?: number;
    total_probes_estimated?: number;
  };
  next_scan?: {
    active_questions: number;
    effective_questions: number;
    scan_limit: number;
    platform_count: number;
    total_probes_estimated: number;
    probe_mode: string;
    platforms: Array<{ platform: string; label: string; estimate: number }>;
  };
  probe_settings?: {
    brand_name: string;
    probe_mode: string;
    monitor_scan_limit: number;
    platforms: string[];
    ai_mock_mode: boolean;
  };
  engine_distribution?: Array<{ engine: string; label: string; count: number }>;
  latest_run?: {
    id: number;
    status: string;
    question_count: number;
    probe_count: number | null;
    started_at: string | null;
    completed_at: string | null;
  } | null;
  recent_alerts?: Array<{ id: number; alert_type: string; message: string; created_at: string | null }>;
  collection_window: { period_start: string | null; period_end: string | null };
  probe_count: number;
  recent_runs: MonitorRun[];
};

export type PlatformBreakdownRow = {
  platform: string;
  label: string;
  visibility_pct: number;
  rank_label: string;
  leader_visibility_pct: number;
  leader_brand: string;
};

export type BrandPanel = {
  metrics: AivisMetrics;
  competitor_matrix: CompetitorMatrix;
  platform_summary: PlatformSummary[];
  platform_breakdown?: PlatformBreakdownRow[];
  sentiment_topics: Array<{ category: string; polarity: string; count: number; label: string }>;
  insights: MonitorInsight[];
};

export type SceneFunnelQuery = {
  id: number;
  text: string;
  citation_count?: number;
};

export type ProbeCitation = {
  id: number;
  title: string;
  url: string;
  position: number;
  domain?: string;
  evidence_level?: string;
  source?: string;
  owner?: string;
};

export type QueryProbe = {
  probe_id: number;
  platform: string;
  label: string;
  mentioned: boolean;
  brand_rank: number | null;
  ranking_score: number | null;
  snippet: string;
  snippet_preview: string;
  citations: ProbeCitation[];
  citation_count: number;
  engine?: string | null;
  thinking_text?: string | null;
  thinking_ms?: number | null;
  keywords?: string[];
  rank_blocks?: Array<Record<string, unknown>>;
  decision_table?: Array<Record<string, unknown>>;
  source_hosts?: string[];
  evidence_level?: string | null;
  metric_kind?: string | null;
  capture_artifact?: string | null;
  scheme?: string | null;
  tracks?: string[];
  reasoning_grade?: string | null;
};

export type CitationChainQuery = {
  id: number;
  text: string;
  priority: number;
  stats: { probe_count?: number; citation_count?: number; unique_domains?: number; domains?: string[] };
  probes: QueryProbe[];
};

export type CitationChain = {
  status: string;
  scene: {
    id: number;
    persona: string;
    scene_name: string;
    intent: string;
    weight_pct: number;
    visibility_pct: number;
    gap_priority: string;
    article_count: number;
  };
  queries: CitationChainQuery[];
  stats: { query_count: number; probe_count: number; citation_count: number };
};

export type SceneFunnelIntent = {
  id: number;
  name: string;
  visibility_pct: number;
  gap_rate: number;
  gap_priority: string;
  queries: SceneFunnelQuery[];
  query_count: number;
  citation_count?: number;
  article_count: number;
  external_id?: string;
  node_metadata?: {
    persona_description?: string;
    persona_description_kvs?: Record<string, string>;
    scene_description_kvs?: Record<string, string>;
    intent_description_kvs?: Record<string, string>;
  };
};

export type SceneFunnelScene = {
  name: string;
  weight_pct: number;
  intents: SceneFunnelIntent[];
};

export type SceneFunnel = {
  personas: Array<{
    name: string;
    weight_pct: number;
    scenes: SceneFunnelScene[];
  }>;
  stats: { persona_count: number; scene_count: number; intent_count: number; query_count: number };
  touchpoint_tree?: { highlight_node_id?: string; stats?: Record<string, unknown>; tree?: unknown[] } | null;
  highlight_node_id?: string;
};

export type ProductPanel = {
  metrics: AivisMetrics;
  competitor_matrix: CompetitorMatrix;
  platform_summary: PlatformSummary[];
  platform_breakdown?: PlatformBreakdownRow[];
  scene_funnel: SceneFunnel;
};

export type OptimizationPanel = {
  market_opportunity: { monthly_search_volume: number; ai_platform_mau: number; summary: string };
  platform_recommendations: Array<{
    platform: string;
    label: string;
    score: number;
    visibility_pct: number;
    top3_pct?: number | null;
    sample_n?: number;
    weighted_rank_score?: number | null;
    sentiment_score?: number | null;
    reason?: string;
  }>;
  priority_scenes: Array<{
    scene_id?: number | null;
    scene_name: string;
    persona?: string | null;
    intent?: string | null;
    gap_rate: number;
    gap_priority: string;
    weight_pct?: number;
    question_count?: number | null;
    supported_count?: number | null;
    unsupported_sample?: Array<{ id: number; question_text: string }>;
  }>;
  insights: MonitorInsight[];
  north_star?: {
    top3_pct?: number | null;
    gap_vs_leader_top3_pp?: number | null;
    mention_rate_pct?: number | null;
    valid_sample_n?: number | null;
    probe_count?: number;
    kpi_track?: string;
  };
  readiness?: {
    question_count: number;
    scene_count: number;
    probe_count: number;
    competitor_count: number;
    high_gap_count?: number;
    has_scan: boolean;
    ready: boolean;
    blockers: string[];
    summary: string;
  };
  actions?: Array<{
    id: string;
    priority: "high" | "medium" | "low" | string;
    title: string;
    body: string;
    href: string;
    cta: string;
    scene_id?: number | null;
  }>;
  difficulty?: {
    overall_score?: number;
    overall_label?: string;
    market_competition?: { score: number; label: string; description: string };
    entity_foundation?: { score: number; label: string; description: string };
    lift_needed_pct?: number | null;
  };
  competitor_gap?: {
    gap_vs_leader?: number | null;
    self_visibility_pct?: number | null;
    competitors?: string[];
    lift_needed_pct?: number | null;
  };
};

export type DifficultyPanel = {
  regulatory_compliance: { score: number; label: string; description: string };
  market_competition: { score: number; label: string; description: string };
  entity_foundation: { score: number; label: string; description: string };
  overall_score: number;
  overall_label: string;
  lift_needed_pct?: number;
  difficulty_score?: number;
};

export type VisibilityReportDetail = VisibilityReport & {
  sections?: Record<string, unknown>;
  html_content?: string;
};
