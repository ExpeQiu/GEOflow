"""应用配置 — 对齐 Laravel config/geoflow.php + geo_eval.php。"""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[3]

_INSECURE_JWT_SECRETS = frozenset(
    {
        "change-me-in-production",
        "change-me-in-production-v3",
        "secret",
        "jwt-secret",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_PROJECT_ROOT / ".env", _PROJECT_ROOT / ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "GEOFlow"
    app_version: str = "3.0.0"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://geo_user:geo_password@localhost:5432/geo_flow"
    database_url_sync: str = "postgresql://geo_user:geo_password@localhost:5432/geo_flow"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    api_token_default_ttl_days: int = 30
    # 逗号分隔；空则本地默认 Admin 源
    cors_allowed_origins: str = "http://127.0.0.1:13001,http://localhost:13001"
    # Content Agent 回调 HMAC；生产必须非默认
    content_agent_callback_secret: str = "dev-callback-secret"
    # AI Key 加密材料；空则回退 jwt_secret
    api_key_encryption_key: str = ""
    login_max_failures: int = 5
    login_lockout_seconds: int = 900
    # DEBUG=true 时允许弱 JWT_SECRET；生产务必 false
    allow_insecure_jwt: bool = False

    geoflow_tech_brand_mode: bool = False
    geoflow_public_site_enabled: bool = True
    geo_eval_enabled: bool = True
    geo_eval_wiki_gate_enabled: bool = True
    # False=只打分/建议不拦发布；True=未过阈值时 eval_status=failed 并拦截 publish
    geo_eval_hard_gate: bool = False
    geo_eval_simulation_pass_score: float = 0.55
    geo_eval_audit_pass_score: float = 0.60
    ai_mock_mode: bool = True
    pdf_ocr_enabled: bool = False

    # 企业 LLM 网关。enterprise-gateway=公司 AI Gateway；lobster=Eva 本地代理（遗留）
    llm_gateway_mode: str = "auto"
    # 企业 AI Gateway（文本 / Embedding，OpenAI 兼容）
    enterprise_ai_gateway_api_key: str = ""
    enterprise_ai_text_base_url: str = "https://ai-gateway-office.zeekrlife.com/v1"
    enterprise_ai_text_model: str = "gpt-4o"
    enterprise_ai_anthropic_base_url: str = "https://ai-gateway-office.zeekrlife.com/anthropic"
    # AIGC 主机（文生图 / 视频 / 视觉，暂未用于 GEOFlow 正文链路）
    enterprise_ai_gateway_base_url: str = "https://ai-gateway.zeekrlife-test.com"
    enterprise_ai_image_model: str = "doubao-seedream-5-0-pro-260628"
    enterprise_ai_video_model: str = "doubao-seedance-1-0-pro-250528"
    enterprise_ai_vision_model: str = "qwen3-vl-plus"
    enterprise_ai_chat_base_url: str = ""
    # Lobster 本地代理（Eva 同学 :56045，遗留/dev）
    lobster_proxy_base: str = "http://127.0.0.1:56045"
    lobster_proxy_token: str = ""
    lobster_api_root: str = "v1"

    # GEOweb（官方技术发布站）— POST /api/geoflow/sync
    geoweb_base_url: str = "http://127.0.0.1:3070"
    geoweb_sync_token: str = ""
    geoweb_sync_enabled: bool = False

    upload_path: str = "./storage/uploads"
    embedding_batch_size: int = 1
    semantic_chunking_max_chars: int = 20000

    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Techstore 只读 Postgres（吉利知识地图/FAQ/文档）。空则导入走 fixture
    techstore_database_url: str = ""

    @field_validator("jwt_secret")
    @classmethod
    def _jwt_secret_not_blank(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("JWT_SECRET must not be empty")
        return v.strip()

    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    def encryption_key_material(self) -> str:
        return (self.api_key_encryption_key or self.jwt_secret).strip()

    def assert_secure_startup(self) -> None:
        """生产失败安全：弱密钥 / 默认回调密钥拒绝启动。"""
        if self.debug or self.allow_insecure_jwt:
            return
        secret = (self.jwt_secret or "").strip()
        if secret in _INSECURE_JWT_SECRETS or len(secret) < 24:
            raise RuntimeError(
                "insecure_jwt_secret: set a strong JWT_SECRET (≥24 chars) or ALLOW_INSECURE_JWT=true for local only"
            )
        cb = (self.content_agent_callback_secret or "").strip()
        if cb in ("", "dev-callback-secret"):
            raise RuntimeError(
                "insecure_callback_secret: set CONTENT_AGENT_CALLBACK_SECRET (not the default) when DEBUG=false"
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
