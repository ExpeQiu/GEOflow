"""采集平台 Open API 凭证解析：企业 Gateway 统一 / 供应商直连。"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

from app.ai.llm_gateway import (
    ENTERPRISE_KEY_SENTINEL,
    enterprise_ready,
    enterprise_text_base_url,
    lobster_base_for,
    lobster_ready,
)
from app.core.api_key_crypto import decrypt_api_key
from app.core.config import get_settings

from app.services.geoeval.probe_platform_registry import (
    BUILTIN_PLATFORM_META,
    merged_platform_meta,
    platform_order,
)

logger = logging.getLogger(__name__)

# 向后兼容测试/导入
PROBE_PLATFORM_META: dict[str, dict[str, Any]] = BUILTIN_PLATFORM_META


@dataclass(frozen=True)
class ProbeApiEndpoint:
    platform: str
    via: str
    base_url: str
    api_key: str
    model_id: str


def _env_fallback(platform: str, config: dict[str, Any] | None = None) -> tuple[str, str, str]:
    meta = merged_platform_meta(config).get(platform) or {}
    key = os.getenv(str(meta.get("env_key") or ""), "").strip()
    if platform == "doubao" and not key:
        key = os.getenv("ARK_API_KEY", "").strip()
    if platform == "kimi" and not key:
        key = os.getenv("MOONSHOT_API_KEY", "").strip()
    model = os.getenv(str(meta.get("env_model") or ""), "").strip() or str(meta.get("default_model") or "")
    base = (
        os.getenv(str(meta.get("env_base") or ""), "").strip()
        or str(meta.get("default_base") or "")
    ).rstrip("/")
    return base, key, model


def _effective_global_mode(config: dict[str, Any]) -> str:
    mode = str(config.get("global_mode") or "inherit").strip().lower()
    if mode in ("enterprise-gateway", "enterprise", "geely"):
        return "enterprise-gateway"
    if mode == "direct":
        return "direct"
    if mode == "lobster":
        return "lobster"
    if enterprise_ready():
        return "enterprise-gateway"
    if lobster_ready():
        return "lobster"
    return "direct"


def resolve_probe_api_endpoint(platform: str, config: dict[str, Any] | None = None) -> ProbeApiEndpoint | None:
    """解析单平台 Open API 端点；不可 API 的平台返回 None。"""
    cfg = config or {}
    meta_map = merged_platform_meta(cfg)
    meta = meta_map.get(platform)
    if not meta or not meta.get("api_capable"):
        return None

    platforms_cfg = cfg.get("platforms") if isinstance(cfg.get("platforms"), dict) else {}
    plat_cfg = platforms_cfg.get(platform) if isinstance(platforms_cfg.get(platform), dict) else {}

    kind = str(plat_cfg.get("connection_kind") or "inherit").strip().lower()
    if kind == "enterprise":
        kind = "enterprise-gateway"
    via = kind if kind in ("direct", "enterprise-gateway", "lobster") else _effective_global_mode(cfg)

    settings = get_settings()
    stored_model = str(plat_cfg.get("model_id") or "").strip()
    stored_url = str(plat_cfg.get("api_url") or "").strip()
    stored_key_raw = str(plat_cfg.get("api_key") or "").strip()
    stored_key = (
        decrypt_api_key(stored_key_raw)
        if stored_key_raw and stored_key_raw not in (ENTERPRISE_KEY_SENTINEL, "lobster-proxy")
        else stored_key_raw
    )

    vendor = str(meta.get("vendor") or "")

    if via == "enterprise-gateway" and enterprise_ready():
        model = stored_model or os.getenv(str(meta.get("env_model") or ""), "").strip() or str(
            meta.get("default_model") or settings.enterprise_ai_text_model or "gpt-4o"
        )
        ep = ProbeApiEndpoint(
            platform=platform,
            via="enterprise-gateway",
            base_url=enterprise_text_base_url(),
            api_key=settings.enterprise_ai_gateway_api_key.strip(),
            model_id=model,
        )
        logger.info("probe_api_resolve platform=%s via=enterprise-gateway model=%s", platform, model)
        return ep

    if via == "lobster" and lobster_ready() and vendor:
        model = stored_model or os.getenv(str(meta.get("env_model") or ""), "").strip() or str(meta.get("default_model") or "")
        ep = ProbeApiEndpoint(
            platform=platform,
            via="lobster",
            base_url=lobster_base_for(vendor),
            api_key=settings.lobster_proxy_token.strip(),
            model_id=model,
        )
        logger.info("probe_api_resolve platform=%s via=lobster model=%s", platform, model)
        return ep

    env_base, env_key, env_model = _env_fallback(platform, cfg)
    base = (stored_url or env_base).rstrip("/")
    key = stored_key if stored_key not in (ENTERPRISE_KEY_SENTINEL, "lobster-proxy", "") else env_key
    model = stored_model or env_model
    if not key or (platform == "doubao" and not model):
        logger.warning("probe_api_resolve_missing platform=%s has_key=%s has_model=%s", platform, bool(key), bool(model))
        return None

    logger.info("probe_api_resolve platform=%s via=direct model=%s", platform, model)
    return ProbeApiEndpoint(platform=platform, via="direct", base_url=base, api_key=key, model_id=model)


def parse_probe_api_config(raw: str | None) -> dict[str, Any]:
    default = {"global_mode": "inherit", "platforms": {}, "custom_platforms": []}
    if not raw or not str(raw).strip():
        return default
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            if "custom_platforms" not in data:
                data["custom_platforms"] = []
            return data
    except json.JSONDecodeError:
        logger.warning("probe_api_config_invalid_json")
    return default
