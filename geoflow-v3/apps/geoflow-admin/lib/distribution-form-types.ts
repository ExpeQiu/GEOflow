export type DistributionChannelType =
  | "geoflow_agent"
  | "geoweb"
  | "wordpress_rest"
  | "generic_http_api";

export type DistributionFormOptions = {
  default_channel_type: DistributionChannelType;
  channel_types: DistributionChannelType[];
  advanced_channel_types?: DistributionChannelType[];
  tech_brand_mode: boolean;
  default_geoweb_base_url?: string;
};

export type DistributionCreatePayload = {
  name: string;
  domain: string;
  endpoint_url: string;
  channel_type: DistributionChannelType;
  front_mode: "static" | "rewrite";
  template_key: string;
  status: "active" | "paused";
  description: string;
  wordpress_username: string;
  wordpress_application_password: string;
  wordpress_post_status: "publish" | "draft" | "pending" | "private";
  wordpress_category_strategy: "match_or_create" | "match_only" | "fixed";
  wordpress_fixed_category: string;
  wordpress_tag_strategy: "keywords_to_tags" | "disabled";
  wordpress_image_strategy: "upload_to_media" | "keep_original";
  generic_auth_type: "none" | "bearer" | "basic" | "header_key" | "hmac";
  generic_basic_username: string;
  generic_secret: string;
  generic_header_name: string;
  generic_timeout_seconds: number;
  generic_success_statuses: string;
  generic_publish_method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  generic_publish_path: string;
  generic_remote_id_path: string;
  generic_remote_url_path: string;
  generic_payload_wrapper: "none" | "data";
  geoweb_sync_token: string;
  geoweb_timeout_seconds: number;
  geoweb_default_page_type: string;
  trace_mode: "suffix" | "off";
  link_template: string;
  require_geoweb_first: boolean;
  channel_slug: string;
};

export const DEFAULT_LINK_TEMPLATE =
  "?utm_source={channel_slug}&utm_medium=distribution&utm_campaign={theme_id}&geo_task={task_id}&geo_dist={dist_id}&geo_article={article_id}";

export const TRACE_PLACEHOLDERS = [
  "{channel_slug}",
  "{task_id}",
  "{dist_id}",
  "{article_id}",
  "{theme_id}",
] as const;

export const DEFAULT_DISTRIBUTION_FORM: DistributionCreatePayload = {
  name: "",
  domain: "",
  endpoint_url: "",
  channel_type: "geoweb",
  front_mode: "static",
  template_key: "",
  status: "active",
  description: "",
  wordpress_username: "",
  wordpress_application_password: "",
  wordpress_post_status: "draft",
  wordpress_category_strategy: "match_or_create",
  wordpress_fixed_category: "",
  wordpress_tag_strategy: "keywords_to_tags",
  wordpress_image_strategy: "upload_to_media",
  generic_auth_type: "bearer",
  generic_basic_username: "",
  generic_secret: "",
  generic_header_name: "X-API-Key",
  generic_timeout_seconds: 30,
  generic_success_statuses: "200,201,202,204",
  generic_publish_method: "POST",
  generic_publish_path: "/articles",
  generic_remote_id_path: "id",
  generic_remote_url_path: "url",
  generic_payload_wrapper: "none",
  geoweb_sync_token: "",
  geoweb_timeout_seconds: 30,
  geoweb_default_page_type: "article",
  trace_mode: "suffix",
  link_template: DEFAULT_LINK_TEMPLATE,
  require_geoweb_first: true,
  channel_slug: "",
};

export type DistributionChannelDetail = {
  id: number;
  name: string;
  channel_type: DistributionChannelType;
  status: "active" | "paused" | "deleted";
  domain: string;
  endpoint_url: string;
  description: string;
  front_mode?: "static" | "rewrite";
  template_key?: string;
  config?: Record<string, unknown>;
};

export function isExternalChannelType(type: DistributionChannelType): boolean {
  return type !== "geoweb";
}

export function channelDetailToForm(channel: DistributionChannelDetail): DistributionCreatePayload {
  const cfg = (channel.config ?? {}) as Record<string, string | number | boolean>;
  return {
    ...DEFAULT_DISTRIBUTION_FORM,
    name: channel.name,
    domain: channel.domain,
    endpoint_url: channel.endpoint_url,
    channel_type: channel.channel_type,
    front_mode: (channel.front_mode as "static" | "rewrite") || "static",
    template_key: channel.template_key || String(cfg.template_key || ""),
    status: channel.status === "paused" ? "paused" : "active",
    description: channel.description || String(cfg.description || ""),
    wordpress_username: String(cfg.wordpress_username || ""),
    wordpress_application_password: String(cfg.wordpress_application_password || ""),
    wordpress_post_status: (cfg.wordpress_post_status as DistributionCreatePayload["wordpress_post_status"]) || "draft",
    wordpress_category_strategy:
      (cfg.wordpress_category_strategy as DistributionCreatePayload["wordpress_category_strategy"]) || "match_or_create",
    wordpress_fixed_category: String(cfg.wordpress_fixed_category || ""),
    wordpress_tag_strategy:
      (cfg.wordpress_tag_strategy as DistributionCreatePayload["wordpress_tag_strategy"]) || "keywords_to_tags",
    wordpress_image_strategy:
      (cfg.wordpress_image_strategy as DistributionCreatePayload["wordpress_image_strategy"]) || "upload_to_media",
    generic_auth_type: (cfg.generic_auth_type as DistributionCreatePayload["generic_auth_type"]) || "bearer",
    generic_basic_username: String(cfg.generic_basic_username || ""),
    generic_secret: String(cfg.generic_secret || ""),
    generic_header_name: String(cfg.generic_header_name || "X-API-Key"),
    generic_timeout_seconds: Number(cfg.generic_timeout_seconds || 30),
    generic_success_statuses: String(cfg.generic_success_statuses || "200,201,202,204"),
    generic_publish_method: (cfg.generic_publish_method as DistributionCreatePayload["generic_publish_method"]) || "POST",
    generic_publish_path: String(cfg.generic_publish_path || "/articles"),
    generic_remote_id_path: String(cfg.generic_remote_id_path || "id"),
    generic_remote_url_path: String(cfg.generic_remote_url_path || "url"),
    generic_payload_wrapper: (cfg.generic_payload_wrapper as DistributionCreatePayload["generic_payload_wrapper"]) || "none",
    geoweb_sync_token: String(cfg.geoweb_sync_token || ""),
    geoweb_timeout_seconds: Number(cfg.geoweb_timeout_seconds || 30),
    geoweb_default_page_type: String(cfg.default_page_type || cfg.geoweb_default_page_type || "article"),
    trace_mode: cfg.trace_mode === "off" ? "off" : "suffix",
    link_template: String(cfg.link_template || DEFAULT_LINK_TEMPLATE),
    require_geoweb_first: cfg.require_geoweb_first !== false,
    channel_slug: String(cfg.channel_slug || ""),
  };
}
