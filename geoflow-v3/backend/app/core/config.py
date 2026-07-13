"""应用配置 — 对齐 Laravel config/geoflow.php + geo_eval.php。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


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

    geoflow_tech_brand_mode: bool = False
    geoflow_public_site_enabled: bool = True
    geo_eval_enabled: bool = True
    geo_eval_wiki_gate_enabled: bool = True
    geo_eval_simulation_pass_score: float = 0.55
    geo_eval_audit_pass_score: float = 0.60
    ai_mock_mode: bool = True
    pdf_ocr_enabled: bool = False

    gweb_base_url: str = "http://localhost:3000"
    gweb_revalidate_secret: str = ""
    gweb_sync_enabled: bool = False

    upload_path: str = "./storage/uploads"
    embedding_batch_size: int = 1
    semantic_chunking_max_chars: int = 20000

    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
