"""探针被监测平台注册表：内置 6 平台 + Admin 自定义平台。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

PROBE_API_CONFIG_KEY = "probe_platform_api_config"
CUSTOM_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")
BUILTIN_PLATFORM_IDS: tuple[str, ...] = ("doubao", "deepseek", "tongyi", "yuanbao", "wenxin", "kimi")

BUILTIN_PLATFORM_META: dict[str, dict[str, Any]] = {
    "doubao": {
        "label": "豆包",
        "vendor": "volcengine",
        "api_capable": True,
        "custom": False,
        "default_model": "",
        "default_base": "https://ark.cn-beijing.volces.com/api/v3",
        "env_key": "DOUBAO_API_KEY",
        "env_model": "DOUBAO_MODEL",
        "env_base": "DOUBAO_API_BASE",
    },
    "deepseek": {
        "label": "DeepSeek",
        "vendor": "deepseek",
        "api_capable": True,
        "custom": False,
        "default_model": "deepseek-chat",
        "default_base": "https://api.deepseek.com",
        "env_key": "DEEPSEEK_API_KEY",
        "env_model": "DEEPSEEK_MODEL",
        "env_base": "DEEPSEEK_API_BASE",
    },
    "tongyi": {
        "label": "通义千问",
        "vendor": "qwen",
        "api_capable": True,
        "custom": False,
        "default_model": "qwen-plus",
        "default_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "env_key": "QWEN_API_KEY",
        "env_model": "QWEN_CHAT_MODEL",
        "env_base": "QWEN_API_BASE",
    },
    "kimi": {
        "label": "Kimi",
        "vendor": "moonshot",
        "api_capable": True,
        "custom": False,
        "default_model": "moonshot-v1-auto",
        "default_base": "https://api.moonshot.cn/v1",
        "env_key": "KIMI_API_KEY",
        "env_model": "KIMI_MODEL",
        "env_base": "KIMI_API_BASE",
    },
    "yuanbao": {
        "label": "元宝",
        "vendor": "",
        "api_capable": False,
        "custom": False,
        "default_model": "",
        "default_base": "",
        "note": "无 Open API，日扫走 C 端 Playwright",
    },
    "wenxin": {
        "label": "文心一言",
        "vendor": "",
        "api_capable": False,
        "custom": False,
        "default_model": "",
        "default_base": "",
        "note": "无 Open API，日扫走 C 端 Playwright",
    },
}


def normalize_custom_platform(raw: dict[str, Any]) -> dict[str, Any] | None:
    pid = str(raw.get("id") or "").strip().lower()
    if not pid or not CUSTOM_ID_RE.match(pid):
        return None
    if pid in BUILTIN_PLATFORM_IDS and raw.get("custom") is not True:
        return None
    label = str(raw.get("label") or pid).strip()
    if not label:
        return None
    return {
        "id": pid,
        "label": label[:50],
        "vendor": str(raw.get("vendor") or "").strip(),
        "api_capable": bool(raw.get("api_capable", True)),
        "custom": True,
        "default_model": str(raw.get("default_model") or "").strip(),
        "default_base": str(raw.get("default_base") or "").strip(),
        "note": str(raw.get("note") or "").strip(),
        "enabled": bool(raw.get("enabled", True)),
        "cend_url": str(raw.get("cend_url") or "").strip(),
    }


def parse_custom_platforms(config: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not config:
        return []
    raw = config.get("custom_platforms")
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        norm = normalize_custom_platform(item)
        if norm is None or norm["id"] in seen:
            continue
        seen.add(norm["id"])
        out.append(norm)
    return out


def merged_platform_meta(config: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    meta = {k: dict(v) for k, v in BUILTIN_PLATFORM_META.items()}
    for c in parse_custom_platforms(config):
        if not c.get("enabled", True):
            continue
        meta[c["id"]] = {
            "label": c["label"],
            "vendor": c.get("vendor") or "",
            "api_capable": c.get("api_capable", True),
            "custom": True,
            "default_model": c.get("default_model") or "",
            "default_base": c.get("default_base") or "",
            "note": c.get("note") or "",
            "cend_url": c.get("cend_url") or "",
        }
    return meta


def platform_order(config: dict[str, Any] | None = None) -> tuple[str, ...]:
    custom_ids = [c["id"] for c in parse_custom_platforms(config) if c.get("enabled", True)]
    return tuple(BUILTIN_PLATFORM_IDS) + tuple(pid for pid in custom_ids if pid not in BUILTIN_PLATFORM_IDS)


def platform_label(platform: str, config: dict[str, Any] | None = None) -> str:
    meta = merged_platform_meta(config).get(platform) or {}
    return str(meta.get("label") or platform)


def is_known_platform(platform: str, config: dict[str, Any] | None = None) -> bool:
    return platform in merged_platform_meta(config)


async def load_probe_api_config_raw(db: AsyncSession) -> dict[str, Any]:
    from app.services.admin.production_service import _table_exists

    if not await _table_exists(db, "site_settings"):
        return {"global_mode": "inherit", "platforms": {}, "custom_platforms": []}
    row = (
        await db.execute(
            text("SELECT setting_value FROM site_settings WHERE setting_key = :k LIMIT 1"),
            {"k": PROBE_API_CONFIG_KEY},
        )
    ).first()
    raw = (row[0] if row else "") or ""
    if not str(raw).strip():
        return {"global_mode": "inherit", "platforms": {}, "custom_platforms": []}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        logger.warning("probe_api_config_invalid_json")
    return {"global_mode": "inherit", "platforms": {}, "custom_platforms": []}


async def list_available_platforms(db: AsyncSession) -> list[dict[str, Any]]:
    cfg = await load_probe_api_config_raw(db)
    meta = merged_platform_meta(cfg)
    items: list[dict[str, Any]] = []
    for pid in platform_order(cfg):
        m = meta.get(pid) or {}
        items.append(
            {
                "id": pid,
                "label": m.get("label") or pid,
                "api_capable": bool(m.get("api_capable")),
                "custom": bool(m.get("custom")),
                "note": m.get("note") or "",
            }
        )
    return items
