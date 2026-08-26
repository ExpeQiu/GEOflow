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
};

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
};
