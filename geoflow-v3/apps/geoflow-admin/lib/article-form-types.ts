export type ArticleFormOption = { id: number; name: string };

export type ArticleFormOptions = {
  categories: ArticleFormOption[];
  authors: ArticleFormOption[];
};

export type EvalRecommendation = {
  code: string;
  detail: string;
  suggestion: string;
  simulation_score?: number;
  audit_score?: number;
  pass_score?: number;
};

export type ArticleDetail = {
  id: number;
  title: string;
  slug: string;
  excerpt: string;
  content: string;
  keywords: string;
  meta_description: string;
  status: string;
  review_status: string;
  eval_status: string;
  content_format: string;
  category_id: number;
  author_id: number;
  task_id: number | null;
  task_name: string;
  publish_scope: string;
  view_count: number;
  published_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  eval_failure_reason: string;
  eval_simulation_score?: number | null;
  eval_audit_score?: number | null;
  eval_audit_passed?: boolean | null;
  eval_retrieval_score?: number | null;
  eval_query?: string;
  eval_simulated_answer?: string;
  eval_recommendations?: EvalRecommendation[];
  eval_advisory_issues?: string[];
  eval_meets_thresholds?: boolean | null;
  eval_gate_mode?: string;
  geo_eval_enabled: boolean;
  geo_eval_gate_enabled: boolean;
  geo_eval_hard_gate?: boolean;
};

export type ArticleUpdatePayload = {
  title: string;
  excerpt: string;
  content: string;
  keywords: string;
  meta_description: string;
  status: "draft" | "published" | "private";
  review_status: "pending" | "approved" | "rejected" | "auto_approved";
  category_id: number;
  author_id: number;
};
