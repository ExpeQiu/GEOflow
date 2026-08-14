export type TaskFormOption = {
  id: number;
  name: string;
  count?: number;
  vectorized_count?: number;
  rag_ready?: boolean;
};

export type TaskFormPromptOption = {
  id: number;
  name: string;
  type?: string;
};

export type TaskFormChannel = {
  id: number;
  name: string;
  domain: string;
  channel_type: string;
};

export type TaskFormTechIp = {
  id: number;
  ip_name: string;
  wiki_type: string;
  status: string;
};

export type TaskFormOptions = {
  has_categories: boolean;
  title_libraries: TaskFormOption[];
  prompts: TaskFormPromptOption[];
  ai_models: TaskFormOption[];
  image_libraries: TaskFormOption[];
  knowledge_bases: TaskFormOption[];
  authors: TaskFormOption[];
  categories: TaskFormOption[];
  distribution_channels: TaskFormChannel[];
  tech_ip_assets: TaskFormTechIp[];
  insight_templates: TaskFormOption[];
  wiki_page_types: string[];
};

export type TaskCreatePayload = {
  task_name: string;
  title_library_id: number;
  prompt_id: number;
  ai_model_id: number;
  author_id?: number | null;
  image_library_id?: number | null;
  image_count?: number;
  knowledge_base_id?: number | null;
  insight_template_id?: number | null;
  fixed_category_id?: number | null;
  status: "active" | "paused";
  article_limit: number;
  draft_limit: number;
  publish_interval: number;
  category_mode: "smart" | "fixed" | "random";
  model_selection_mode: "fixed" | "smart_failover";
  content_pipeline_mode: "legacy" | "pipeline" | "auto";
  content_format: "article" | "wiki_mdx";
  wiki_page_type: string;
  tech_ip_asset_id?: number | null;
  publish_scope: "local_and_distribution" | "distribution_only" | "local_only";
  distribution_channel_ids: number[];
  need_review: boolean;
  is_loop: boolean;
  auto_keywords: boolean;
  auto_description: boolean;
};

export const DEFAULT_TASK_FORM: TaskCreatePayload = {
  task_name: "",
  title_library_id: 0,
  prompt_id: 0,
  ai_model_id: 0,
  author_id: 0,
  image_library_id: null,
  image_count: 1,
  knowledge_base_id: null,
  insight_template_id: null,
  fixed_category_id: null,
  status: "active",
  article_limit: 10,
  draft_limit: 10,
  publish_interval: 60,
  category_mode: "smart",
  model_selection_mode: "fixed",
  content_pipeline_mode: "legacy",
  content_format: "article",
  wiki_page_type: "concept",
  tech_ip_asset_id: null,
  publish_scope: "local_only",
  distribution_channel_ids: [],
  need_review: false,
  is_loop: true,
  auto_keywords: true,
  auto_description: true,
};
