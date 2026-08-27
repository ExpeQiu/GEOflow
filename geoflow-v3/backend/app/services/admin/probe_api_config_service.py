"""采集平台 API 配置 — Admin CRUD（企业 Gateway / 供应商直连）。"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_gateway import (
    ENTERPRISE_KEY_SENTINEL,
    effective_gateway_mode,
    enterprise_ready,
    gateway_status_payload,
    lobster_ready,
)
from app.core.api_key_crypto import encrypt_api_key
from app.core.config import get_settings
from app.services.admin.production_service import _table_exists
from app.services.admin.settings_crud_service import SiteSettingBody, upsert_site_setting
from app.services.geoeval.probe_platform_registry import (
    is_known_platform,
    merged_platform_meta,
    normalize_custom_platform,
    parse_custom_platforms,
    platform_order,
)
from app.services.geoeval.probe_api_resolver import (
    parse_probe_api_config,
    resolve_probe_api_endpoint,
)

logger = logging.getLogger(__name__)

SETTING_KEY = "probe_platform_api_config"


class ProbePlatformApiBody(BaseModel):
    connection_kind: str = Field(default="inherit", pattern="^(inherit|direct|enterprise-gateway|enterprise|lobster)$")
    model_id: str = ""
    api_url: str = ""
    api_key: str = ""


class ProbeApiConfigBody(BaseModel):
    global_mode: str = Field(default="inherit", pattern="^(inherit|direct|enterprise-gateway|enterprise|geely|lobster)$")
    platforms: dict[str, ProbePlatformApiBody] = Field(default_factory=dict)
    custom_platforms: list[dict[str, Any]] | None = None


class CustomPlatformBody(BaseModel):
    id: str
    label: str = ""
    vendor: str = ""
    api_capable: bool = True
    default_model: str = ""
    default_base: str = ""
    note: str = ""
    enabled: bool = True
    cend_url: str = ""


async def _load_raw_config(db: AsyncSession) -> dict[str, Any]:
    if not await _table_exists(db, "site_settings"):
        return parse_probe_api_config(None)
    row = (
        await db.execute(
            text("SELECT setting_value FROM site_settings WHERE setting_key = :k LIMIT 1"),
            {"k": SETTING_KEY},
        )
    ).first()
    return parse_probe_api_config(row[0] if row else None)


async def _load_raw_with_keys(db: AsyncSession) -> dict[str, Any]:
    return await _load_raw_config(db)


def _public_platform_view(platform: str, cfg: dict[str, Any], stored: dict[str, Any]) -> dict[str, Any]:
    meta = merged_platform_meta(cfg).get(platform, {})
    plat = stored.get(platform) if isinstance(stored.get(platform), dict) else {}
    key_raw = str(plat.get("api_key") or "")
    has_key = bool(key_raw) and key_raw not in ("", ENTERPRISE_KEY_SENTINEL, "lobster-proxy")
    ep = resolve_probe_api_endpoint(platform, cfg) if meta.get("api_capable") else None
    if ep and ep.via in ("enterprise-gateway", "lobster"):
        has_key = enterprise_ready() if ep.via == "enterprise-gateway" else lobster_ready()
    return {
        "platform": platform,
        "label": meta.get("label") or platform,
        "api_capable": bool(meta.get("api_capable")),
        "custom": bool(meta.get("custom")),
        "note": meta.get("note"),
        "vendor": meta.get("vendor") or "",
        "default_model": meta.get("default_model") or "",
        "default_base": meta.get("default_base") or "",
        "connection_kind": str(plat.get("connection_kind") or "inherit"),
        "model_id": str(plat.get("model_id") or meta.get("default_model") or ""),
        "api_url": str(plat.get("api_url") or meta.get("default_base") or ""),
        "has_api_key": has_key,
        "resolved_via": ep.via if ep else None,
        "resolved_base_url": ep.base_url if ep else None,
        "resolved_model_id": ep.model_id if ep else None,
        "ready": ep is not None,
    }


async def get_probe_api_config(db: AsyncSession) -> dict[str, Any]:
    cfg = await _load_raw_config(db)
    stored_platforms = cfg.get("platforms") if isinstance(cfg.get("platforms"), dict) else {}
    gw = gateway_status_payload()
    order = platform_order(cfg)
    platforms = [_public_platform_view(p, cfg, stored_platforms) for p in order]
    custom = parse_custom_platforms(cfg)
    return {
        "global_mode": str(cfg.get("global_mode") or "inherit"),
        "global_mode_options": [
            {"id": "inherit", "label": "跟随 AI 模型页", "desc": f"当前生效：{effective_gateway_mode()}"},
            {"id": "enterprise-gateway", "label": "企业 AI Gateway", "desc": "统一 Bearer + 文本端点"},
            {"id": "direct", "label": "供应商直连", "desc": "各平台独立 Key / Base URL"},
            {"id": "lobster", "label": "Lobster（遗留）", "desc": "Eva 本地 :56045"},
        ],
        "enterprise_ready": enterprise_ready(),
        "lobster_ready": lobster_ready(),
        "ai_mock_mode": get_settings().ai_mock_mode,
        "platforms": platforms,
        "custom_platforms": custom,
        "llm_gateway": {
            "mode": gw.get("mode"),
            "enterprise_text_base": gw.get("enterprise_text_base"),
            "enterprise_text_model": get_settings().enterprise_ai_text_model,
            "enterprise_key_configured": gw.get("enterprise_key_configured"),
        },
    }


def _merge_platform_save(
    existing: dict[str, Any],
    body: ProbePlatformApiBody,
) -> dict[str, Any]:
    prev = existing if isinstance(existing, dict) else {}
    kind = body.connection_kind
    if kind == "enterprise":
        kind = "enterprise-gateway"
    out: dict[str, Any] = {
        "connection_kind": kind,
        "model_id": body.model_id.strip(),
        "api_url": body.api_url.strip(),
    }
    key = (body.api_key or "").strip()
    if not key:
        prev_key = str(prev.get("api_key") or "")
        if prev_key:
            out["api_key"] = prev_key
        elif kind == "enterprise-gateway":
            out["api_key"] = ENTERPRISE_KEY_SENTINEL
        elif kind == "lobster":
            out["api_key"] = "lobster-proxy"
    elif key in (ENTERPRISE_KEY_SENTINEL, "lobster-proxy"):
        out["api_key"] = key
    else:
        out["api_key"] = encrypt_api_key(key)
    return out


async def save_probe_api_config(db: AsyncSession, body: ProbeApiConfigBody) -> dict[str, Any]:
    existing = await _load_raw_with_keys(db)
    stored = existing.get("platforms") if isinstance(existing.get("platforms"), dict) else {}
    merged_platforms = dict(stored)
    known = set(platform_order(existing))
    for platform, plat_body in body.platforms.items():
        if platform not in known:
            continue
        merged_platforms[platform] = _merge_platform_save(stored.get(platform) or {}, plat_body)

    global_mode = body.global_mode.strip().lower()
    if global_mode == "enterprise":
        global_mode = "enterprise-gateway"
    if global_mode == "geely":
        global_mode = "enterprise-gateway"

    if body.custom_platforms is not None:
        custom: list[dict[str, Any]] = []
        for raw in body.custom_platforms:
            if not isinstance(raw, dict):
                continue
            norm = normalize_custom_platform(raw)
            if norm:
                custom.append(norm)
    else:
        custom = parse_custom_platforms(existing)

    payload = {"global_mode": global_mode, "platforms": merged_platforms, "custom_platforms": custom}
    await upsert_site_setting(
        db,
        SiteSettingBody(
            setting_key=SETTING_KEY,
            setting_value=json.dumps(payload, ensure_ascii=False),
            value_type="json",
            group_name="monitor",
        ),
    )
    logger.info("probe_api_config_saved global_mode=%s platforms=%s", global_mode, list(body.platforms.keys()))
    return await get_probe_api_config(db)


async def test_probe_platform_api(db: AsyncSession, platform: str) -> dict[str, Any]:
    cfg = await _load_raw_config(db)
    if not is_known_platform(platform, cfg):
        return {"ok": False, "message": "unknown_platform"}
    meta = merged_platform_meta(cfg).get(platform) or {}
    if not meta.get("api_capable"):
        return {"ok": False, "message": "platform_cend_only", "note": meta.get("note")}

    settings = get_settings()
    if settings.ai_mock_mode:
        return {"ok": True, "mock": True, "message": "mock_mode_ok"}

    ep = resolve_probe_api_endpoint(platform, cfg)
    if ep is None:
        return {"ok": False, "mock": False, "message": "credentials_missing — 请配置企业 Key 或供应商 Key"}

    url = f"{ep.base_url.rstrip('/')}/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {ep.api_key}", "Content-Type": "application/json"},
                json={
                    "model": ep.model_id,
                    "messages": [{"role": "user", "content": "只回复 OK"}],
                    "max_tokens": 8,
                    "temperature": 0,
                },
            )
        if resp.status_code >= 400:
            detail = (resp.text or "")[:160]
            logger.warning("probe_api_test_http platform=%s status=%s", platform, resp.status_code)
            return {"ok": False, "mock": False, "message": f"http_{resp.status_code}:{detail}", "via": ep.via}
        logger.info("probe_api_test_ok platform=%s via=%s model=%s", platform, ep.via, ep.model_id)
        return {"ok": True, "mock": False, "message": f"ok via={ep.via}", "via": ep.via, "model_id": ep.model_id}
    except Exception as exc:
        logger.warning("probe_api_test_failed platform=%s err=%s", platform, exc)
        return {"ok": False, "mock": False, "message": str(exc)[:200]}
