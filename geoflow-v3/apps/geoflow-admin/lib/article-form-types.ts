export type ArticleFormOption = { id: number; name: string };

export type ArticleFormOptions = {
  categories: ArticleFormOption[];
  authors: ArticleFormOption[];
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
  geo_eval_enabled: boolean;
  geo_eval_gate_enabled: boolean;
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
