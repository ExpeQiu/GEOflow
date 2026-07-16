"""分发渠道创建 — Admin BFF。"""

import logging
import re
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.distribution import DistributionChannel

logger = logging.getLogger(__name__)

CHANNEL_TYPES = ("geoflow_agent", "gweb_wiki", "wordpress_rest", "generic_http_api")


class AdminDistributionCreateBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    domain: str = Field(min_length=1, max_length=255)
    endpoint_url: str = Field(min_length=1, max_length=500)
    channel_type: str = Field(default="geoflow_agent")
    front_mode: str = Field(default="static", pattern="^(static|rewrite)$")
    template_key: str = ""
    status: str = Field(default="active", pattern="^(active|paused)$")
    description: str = ""
    wordpress_username: str = ""
    wordpress_application_password: str = ""
    wordpress_post_status: str = Field(default="draft", pattern="^(publish|draft|pending|private)$")
    wordpress_category_strategy: str = Field(default="match_or_create", pattern="^(match_or_create|match_only|fixed)$")
    wordpress_fixed_category: str = ""
    wordpress_tag_strategy: str = Field(default="keywords_to_tags", pattern="^(keywords_to_tags|disabled)$")
    wordpress_image_strategy: str = Field(default="upload_to_media", pattern="^(upload_to_media|keep_original)$")
    generic_auth_type: str = Field(default="bearer", pattern="^(none|bearer|basic|header_key|hmac)$")
    generic_basic_username: str = ""
    generic_secret: str = ""
    generic_header_name: str = "X-API-Key"
    generic_timeout_seconds: int = Field(default=30, ge=5, le=120)
    generic_success_statuses: str = "200,201,202,204"
    generic_publish_method: str = Field(default="POST", pattern="^(GET|POST|PUT|PATCH|DELETE)$")
    generic_publish_path: str = "/articles"
    generic_remote_id_path: str = "id"
    generic_remote_url_path: str = "url"
    generic_payload_wrapper: str = Field(default="none", pattern="^(none|data)$")
    gweb_sync_secret: str = ""
    gweb_timeout_seconds: int = Field(default=30, ge=5, le=120)
    gweb_route_prefix: str = ""


def build_distribution_form_options() -> dict[str, Any]:
    settings = get_settings()
    default_type = "gweb_wiki" if settings.geoflow_tech_brand_mode else "geoflow_agent"
    return {
        "default_channel_type": default_type,
        "channel_types": list(CHANNEL_TYPES),
        "tech_brand_mode": settings.geoflow_tech_brand_mode,
    }


async def create_admin_distribution_channel(db: AsyncSession, body: AdminDistributionCreateBody) -> dict:
    if body.channel_type not in CHANNEL_TYPES:
        raise HTTPException(status_code=422, detail="invalid_channel_type")

    endpoint_url = _normalize_endpoint_url(body.endpoint_url)
    if not _is_valid_http_endpoint(endpoint_url):
        raise HTTPException(status_code=422, detail="invalid_endpoint_url")

    domain = _normalize_domain(body.domain)
    _validate_type_specific(body)

    config_json: dict[str, Any] = {
        "domain": domain,
        "endpoint_url": endpoint_url,
        "description": body.description.strip(),
        "front_mode": body.front_mode,
        "template_key": body.template_key.strip() or None,
    }
    config_json.update(_build_type_config(body, endpoint_url))

    channel = DistributionChannel(
        name=body.name.strip(),
        channel_type=body.channel_type,
        status=body.status,
        config_json=config_json,
    )
    db.add(channel)
    await db.flush()

    logger.info(
        "admin_distribution_channel_created id=%s type=%s domain=%s",
        channel.id,
        channel.channel_type,
        domain,
    )

    return {
        "channel": {
            "id": channel.id,
            "name": channel.name,
            "channel_type": channel.channel_type,
            "status": channel.status,
            "domain": domain,
            "endpoint_url": endpoint_url,
        }
    }


def _validate_type_specific(body: AdminDistributionCreateBody) -> None:
    if body.channel_type == "wordpress_rest":
        if not body.wordpress_username.strip():
            raise HTTPException(status_code=422, detail="wordpress_username_required")
        if not body.wordpress_application_password.strip():
            raise HTTPException(status_code=422, detail="wordpress_password_required")
    if body.channel_type == "gweb_wiki" and not body.gweb_sync_secret.strip():
        raise HTTPException(status_code=422, detail="gweb_sync_secret_required")
    if body.channel_type == "generic_http_api":
        if body.generic_auth_type == "basic" and not body.generic_basic_username.strip():
            raise HTTPException(status_code=422, detail="generic_basic_username_required")
        if body.generic_auth_type != "none" and not body.generic_secret.strip():
            raise HTTPException(status_code=422, detail="generic_secret_required")
        if not body.generic_publish_path.strip():
            raise HTTPException(status_code=422, detail="generic_publish_path_required")


def _build_type_config(body: AdminDistributionCreateBody, endpoint_url: str) -> dict[str, Any]:
    if body.channel_type == "gweb_wiki":
        cfg: dict[str, Any] = {
            "gweb_base_url": endpoint_url.rstrip("/"),
            "gweb_sync_secret": body.gweb_sync_secret.strip(),
            "gweb_timeout_seconds": body.gweb_timeout_seconds,
        }
        prefix = body.gweb_route_prefix.strip()
        if prefix:
            cfg["route_prefix"] = prefix
        return cfg
    if body.channel_type == "wordpress_rest":
        return {
            "wordpress_username": body.wordpress_username.strip(),
            "wordpress_application_password": body.wordpress_application_password.strip(),
            "wordpress_post_status": body.wordpress_post_status,
            "wordpress_category_strategy": body.wordpress_category_strategy,
            "wordpress_fixed_category": body.wordpress_fixed_category.strip(),
            "wordpress_tag_strategy": body.wordpress_tag_strategy,
            "wordpress_image_strategy": body.wordpress_image_strategy,
            "wordpress_content_format": "html",
        }
    if body.channel_type == "generic_http_api":
        return {
            "generic_auth_type": body.generic_auth_type,
            "generic_basic_username": body.generic_basic_username.strip(),
            "generic_secret": body.generic_secret.strip(),
            "generic_header_name": body.generic_header_name.strip() or "X-API-Key",
            "generic_timeout_seconds": body.generic_timeout_seconds,
            "generic_success_statuses": body.generic_success_statuses.strip(),
            "generic_publish_method": body.generic_publish_method.upper(),
            "generic_publish_path": body.generic_publish_path.strip(),
            "generic_remote_id_path": body.generic_remote_id_path.strip() or "id",
            "generic_remote_url_path": body.generic_remote_url_path.strip() or "url",
            "generic_payload_wrapper": body.generic_payload_wrapper,
        }
    return {}


def _normalize_domain(domain: str) -> str:
    value = domain.strip()
    if not value:
        return ""
    if "://" not in value:
        value = f"https://{value}"
    parsed = urlparse(value)
    return parsed.hostname or domain.strip()


def _normalize_endpoint_url(endpoint_url: str) -> str:
    value = endpoint_url.strip()
    if not value:
        return ""
    if "://" not in value:
        value = f"https://{value}"
    return value.rstrip("/")


def _is_valid_http_endpoint(endpoint_url: str) -> bool:
    if not endpoint_url or re.search(r"\s", endpoint_url):
        return False
    parsed = urlparse(endpoint_url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)
