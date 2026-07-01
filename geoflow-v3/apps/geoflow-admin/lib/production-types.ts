export type MaterialStats = {
  keyword_libraries: number;
  total_keywords: number;
  title_libraries: number;
  total_titles: number;
  image_libraries: number;
  total_images: number;
  knowledge_bases: number;
  knowledge_chunks: number;
  vectorized_chunks: number;
  unvectorized_chunks: number;
  knowledge_usage_count: number;
  active_embedding_models: number;
  authors: number;
  body_prompts: number;
  special_prompts: number;
};

export type AiStats = {
  model_count: number;
  chat_models: number;
  embedding_models: number;
  prompt_count: number;
  total_usage: number;
  today_usage: number;
};

export type OrchestrationStats = {
  backend: string;
  sidecar_healthy: boolean;
  driver_hint: string;
  totals_24h: Record<string, number>;
  by_workflow: Record<string, { completed: number; failed: number; pending: number }>;
  recent_failures: { request_id: string; workflow_type: string; error_message: string }[];
  knowledge_pending: number;
};

export type WorkflowStep = { id: string; label: string; type: string; agent?: string };
export type WorkflowDef = { description: string; visual_layout: string; visual_steps: WorkflowStep[] };
export type WorkflowCatalog = { default_workflow: string; workflows: Record<string, WorkflowDef> };

export type KnowledgeItem = {
  id: number;
  name: string;
  description: string;
  word_count: number;
  usage_count: number;
  used_task_count: number;
  chunk_count: number;
  vectorized_count: number;
  updated_at: string | null;
};

export type AiModelRow = {
  id: number;
  name: string;
  model_id: string;
  model_type: string;
  status: string;
  used_today: number;
  total_used: number;
  daily_limit: number;
};

export type PromptRow = { id: number; name: string; type: string; preview: string };

export type TechAsset = {
  id: number;
  name: string;
  ip_id: string;
  wiki_type: string;
  status: string;
};
