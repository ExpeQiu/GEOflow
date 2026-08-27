"""企业 LLM 网关：优先公司 AI Gateway，遗留 Lobster 本地代理。

路由约定（企业 AI Gateway · 文本）：
  推理  POST {ENTERPRISE_AI_TEXT_BASE_URL}/chat/completions  Bearer ENTERPRISE_AI_GATEWAY_API_KEY

遗留 Lobster（Eva :56045，本地 dev）：
  列模型  GET  {base}/v1/geely/{vendor}/models
  推理    POST {base}/v1/geely/{vendor}/v1/chat/completions  LOBSTER_PROXY_TOKEN

API 资源开关（Admin 可切换，优先于 .env）：
  vendor  → 供应商直连
  geely   → 企业 AI Gateway（公司级）
  auto    → 跟随 .env LLM_GATEWAY_MODE
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_key_crypto import decrypt_api_key
from app.core.config import get_settings

logger = logging.getLogger(__name__)

LOBSTER_KEY_SENTINEL = "lobster-proxy"
ENTERPRISE_KEY_SENTINEL = "enterprise-gateway"
SITE_SETTING_KEY = "llm_api_resource"

_runtime_resource: str | None = None

API_RESOURCE_OPTIONS: list[dict[str, Any]] = [
    {
        "id": "vendor",
        "label": "供应商资源",
        "mode": "direct",
        "desc": "直连通义 / DeepSeek / 智谱等公网 API，需在模型里填写厂商 Key",
    },
    {
        "id": "geely",
        "label": "企业 AI Gateway",
        "mode": "enterprise-gateway",
        "desc": "经公司 AI Gateway（ai-gateway-office / ai-gateway），使用 ENTERPRISE_AI_GATEWAY_API_KEY",
    },
]

VENDORS: dict[str, dict[str, Any]] = {
    "enterprise": {
        "label": "企业 AI Gateway",
        "lobster": False,
        "enterprise": True,
        "direct_base": "https://ai-gateway-office.zeekrlife.com/v1",
        "default_chat": "gpt-4o",
        "default_embed": "text-embedding-v3",
    },
    "qwen": {
        "label": "通义千问",
        "lobster": True,
        "enterprise": True,
        "direct_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_chat": "qwen-plus",
        "default_embed": "text-embedding-v3",
    },
    "deepseek": {
        "label": "DeepSeek",
        "lobster": True,
        "enterprise": True,
        "direct_base": "https://api.deepseek.com",
        "default_chat": "deepseek-chat",
        "default_embed": "",
    },
    "zhipu": {
        "label": "智谱",
        "lobster": True,
        "enterprise": True,
        "direct_base": "https://open.bigmodel.cn/api/paas/v4",
        "default_chat": "glm-4-flash",
        "default_embed": "embedding-3",
    },
    "moonshot": {
        "label": "Kimi / 月之暗面",
        "lobster": True,
        "enterprise": True,
        "direct_base": "https://api.moonshot.cn/v1",
        "default_chat": "kimi-k2.6",
        "default_embed": "",
    },
    "minimax": {
        "label": "MiniMax",
        "lobster": True,
        "enterprise": True,
        "direct_base": "https://api.minimax.chat/v1",
        "default_chat": "MiniMax-M3",
        "default_embed": "",
    },
    "volcengine": {
        "label": "火山引擎 / 豆包",
        "lobster": True,
        "enterprise": True,
        "direct_base": "https://ark.cn-beijing.volces.com/api/v3",
        "default_chat": "doubao-seed-2-0-pro",
        "default_embed": "",
    },
    "openai": {
        "label": "OpenAI",
        "lobster": False,
        "enterprise": True,
        "direct_base": "https://api.openai.com/v1",
        "default_chat": "gpt-4o-mini",
        "default_embed": "text-embedding-3-small",
    },
}


@dataclass(frozen=True)
class LlmEndpoint:
    via: str
    vendor: str
    base_url: str
    api_key: str
    model_id: str


def vendor_catalog() -> list[dict[str, Any]]:
    return [{"id": k, **v} for k, v in VENDORS.items()]


def infer_vendor(model_id: str = "", api_url: str = "", name: str = "") -> str:
    blob = f"{model_id} {api_url} {name}".lower()
    if "ai-gateway" in blob or "enterprise" in blob or "zeekrlife" in blob:
        return "enterprise"
    rules = (
        ("zhipu", ("glm", "zhipu", "bigmodel")),
        ("qwen", ("qwen", "dashscope", "tongyi")),
        ("deepseek", ("deepseek",)),
        ("moonshot", ("kimi", "moonshot")),
        ("minimax", ("minimax",)),
        ("volcengine", ("doubao", "volc", "ark.", "seed-")),
        ("openai", ("openai", "gpt-", "text-embedding-3")),
    )
    for vendor, needles in rules:
        if any(n in blob for n in needles):
            return vendor
    return "openai"


def enterprise_text_base_url() -> str:
    settings = get_settings()
    return (settings.enterprise_ai_text_base_url or "https://ai-gateway-office.zeekrlife.com/v1").rstrip("/")


def enterprise_ready() -> bool:
    settings = get_settings()
    return bool((settings.enterprise_ai_gateway_api_key or "").strip() and enterprise_text_base_url())


def lobster_ready() -> bool:
    settings = get_settings()
    return bool((settings.lobster_proxy_token or "").strip() and (settings.lobster_proxy_base or "").strip())


def _normalize_resource(value: str | None) -> str:
    raw = (value or "").strip().lower()
    if raw in ("vendor", "direct", "supplier"):
        return "vendor"
    if raw in ("geely", "enterprise", "enterprise-gateway", "intranet"):
        return "geely"
    if raw in ("lobster",):
        return "geely"
    if raw in ("auto", ""):
        return "auto"
    return "auto"


def set_runtime_api_resource(resource: str | None) -> None:
    global _runtime_resource
    _runtime_resource = _normalize_resource(resource) if resource is not None else None


def env_api_resource() -> str:
    mode = (get_settings().llm_gateway_mode or "auto").strip().lower()
    if mode in ("enterprise-gateway", "enterprise", "geely"):
        return "geely"
    if mode == "lobster":
        return "geely"
    if mode == "direct":
        return "vendor"
    return "auto"


def configured_api_resource() -> str:
    if _runtime_resource in ("vendor", "geely", "auto"):
        return _runtime_resource
    return env_api_resource()


def effective_gateway_mode() -> str:
    """解析为调用路径：direct | enterprise-gateway | lobster。"""
    resource = configured_api_resource()
    if resource == "geely":
        if enterprise_ready():
            return "enterprise-gateway"
        if lobster_ready():
            return "lobster"
        return "direct"
    if resource == "vendor":
        return "direct"
    if enterprise_ready():
        return "enterprise-gateway"
    token = (get_settings().lobster_proxy_token or "").strip()
    return "lobster" if token else "direct"


def lobster_base_for(vendor: str) -> str:
    settings = get_settings()
    root = settings.lobster_proxy_base.rstrip("/")
    extra = (settings.lobster_api_root or "v1").strip().strip("/")
    path = f"{root}/v1/geely/{vendor}"
    return f"{path}/{extra}" if extra else path


def lobster_models_url(vendor: str) -> str:
    settings = get_settings()
    root = settings.lobster_proxy_base.rstrip("/")
    return f"{root}/v1/geely/{vendor}/models"


async def refresh_api_resource_from_db(db: AsyncSession) -> str:
    from app.services.admin.production_service import _table_exists

    if not await _table_exists(db, "site_settings"):
        set_runtime_api_resource(None)
        return configured_api_resource()
    row = (
        await db.execute(
            text("SELECT setting_value FROM site_settings WHERE setting_key = :k LIMIT 1"),
            {"k": SITE_SETTING_KEY},
        )
    ).first()
    value = (row[0] if row else "") or ""
    if value.strip():
        set_runtime_api_resource(value)
    else:
        set_runtime_api_resource("auto")
    resource = configured_api_resource()
    logger.info("llm_api_resource_loaded resource=%s", resource)
    return resource


async def save_api_resource(db: AsyncSession, resource: str, actor_id: int = 0) -> dict[str, Any]:
    from fastapi import HTTPException

    from app.services.admin.settings_crud_service import SiteSettingBody, upsert_site_setting, write_activity_log

    normalized = _normalize_resource(resource)
    if normalized not in ("vendor", "geely", "auto"):
        raise HTTPException(status_code=422, detail="invalid_api_resource")
    await upsert_site_setting(
        db,
        SiteSettingBody(
            setting_key=SITE_SETTING_KEY,
            setting_value=normalized,
            value_type="string",
            group_name="ai",
        ),
    )
    set_runtime_api_resource(normalized)
    await write_activity_log(db, actor_id, "ai.api_resource", "site_settings", SITE_SETTING_KEY, normalized)
    logger.info("llm_api_resource_saved resource=%s actor_id=%s", normalized, actor_id)
    return gateway_status_payload()


def _resolve_via(connection_kind: str) -> str:
    kind = (connection_kind or "inherit").strip().lower()
    if kind == "direct":
        return "direct"
    if kind == "lobster":
        return "lobster"
    if kind in ("enterprise-gateway", "enterprise"):
        return "enterprise-gateway"
    return effective_gateway_mode()


def resolve_llm_endpoint(model: Any) -> LlmEndpoint:
    """把 AiModel 行解析成实际调用的 base_url + key。"""
    settings = get_settings()
    model_id = str(getattr(model, "model_id", "") or "")
    stored_url = str(getattr(model, "api_url", "") or "")
    stored_key_raw = str(getattr(model, "api_key", "") or "")
    stored_key = (
        decrypt_api_key(stored_key_raw)
        if stored_key_raw not in ("", "mock", LOBSTER_KEY_SENTINEL, ENTERPRISE_KEY_SENTINEL)
        else stored_key_raw
    )
    name = str(getattr(model, "name", "") or "")
    vendor = (getattr(model, "vendor", None) or "").strip() or infer_vendor(model_id, stored_url, name)
    kind = getattr(model, "connection_kind", None) or "inherit"
    spec = VENDORS.get(vendor) or VENDORS["openai"]

    via = _resolve_via(kind)
    if via == "enterprise-gateway" and not enterprise_ready():
        via = "lobster" if lobster_ready() else "direct"
        logger.warning("llm_gateway_fallback via=%s reason=enterprise_key_missing", via)
    if via == "lobster" and not spec.get("lobster"):
        via = "enterprise-gateway" if enterprise_ready() else "direct"
        logger.info("llm_gateway_fallback vendor=%s reason=not_on_lobster via=%s", vendor, via)
    if via == "lobster" and not lobster_ready():
        via = "enterprise-gateway" if enterprise_ready() else "direct"
        logger.warning("llm_gateway_fallback vendor=%s reason=lobster_token_missing via=%s", vendor, via)

    if via == "enterprise-gateway":
        token = settings.enterprise_ai_gateway_api_key.strip()
        base = enterprise_text_base_url()
        resolved_model = model_id or settings.enterprise_ai_text_model or "gpt-4o"
        logger.info(
            "llm_gateway_resolve via=enterprise-gateway resource=%s vendor=%s model_id=%s",
            configured_api_resource(),
            vendor,
            resolved_model,
        )
        return LlmEndpoint(
            via="enterprise-gateway",
            vendor=vendor,
            base_url=base,
            api_key=token,
            model_id=resolved_model,
        )

    if via == "lobster":
        token = settings.lobster_proxy_token.strip()
        base = lobster_base_for(vendor)
        logger.info(
            "llm_gateway_resolve via=lobster resource=%s vendor=%s model_id=%s",
            configured_api_resource(),
            vendor,
            model_id,
        )
        return LlmEndpoint(via="lobster", vendor=vendor, base_url=base, api_key=token, model_id=model_id)

    base = stored_url.rstrip("/") or str(spec.get("direct_base") or "")
    logger.info(
        "llm_gateway_resolve via=direct resource=%s vendor=%s model_id=%s",
        configured_api_resource(),
        vendor,
        model_id,
    )
    return LlmEndpoint(via="direct", vendor=vendor, base_url=base, api_key=stored_key, model_id=model_id)


def public_model_view(model: Any) -> dict[str, Any]:
    ep = resolve_llm_endpoint(model)
    stored_key = str(getattr(model, "api_key", "") or "")
    has_key = bool(stored_key) and stored_key not in ("mock", LOBSTER_KEY_SENTINEL, ENTERPRISE_KEY_SENTINEL)
    if ep.via == "enterprise-gateway":
        has_key = enterprise_ready()
    elif ep.via == "lobster":
        has_key = lobster_ready()
    return {
        "id": getattr(model, "id", None),
        "name": getattr(model, "name", ""),
        "model_id": getattr(model, "model_id", ""),
        "model_type": getattr(model, "model_type", "chat") or "chat",
        "api_url": getattr(model, "api_url", ""),
        "failover_priority": getattr(model, "failover_priority", 100),
        "status": getattr(model, "status", "active"),
        "vendor": ep.vendor,
        "connection_kind": getattr(model, "connection_kind", None) or "inherit",
        "resolved_via": ep.via,
        "resolved_base_url": ep.base_url,
        "has_api_key": has_key,
    }


def gateway_status_payload() -> dict[str, Any]:
    settings = get_settings()
    resource = configured_api_resource()
    mode = effective_gateway_mode()
    active = next((o for o in API_RESOURCE_OPTIONS if o["id"] == resource), None)
    ent_ready = enterprise_ready()
    lob_ready = lobster_ready()
    return {
        "resource": resource,
        "resource_label": (active or {}).get("label")
        or ("跟随环境变量" if resource == "auto" else resource),
        "resource_options": API_RESOURCE_OPTIONS
        + [
            {
                "id": "auto",
                "label": "跟随环境变量",
                "mode": "auto",
                "desc": f"使用 .env LLM_GATEWAY_MODE={settings.llm_gateway_mode}",
            }
        ],
        "mode": mode,
        "configured_mode": settings.llm_gateway_mode,
        "enterprise_text_base": enterprise_text_base_url(),
        "enterprise_key_configured": bool((settings.enterprise_ai_gateway_api_key or "").strip()),
        "enterprise_ready": ent_ready,
        "lobster_base": settings.lobster_proxy_base,
        "token_configured": lob_ready,
        "ready": ent_ready if mode == "enterprise-gateway" else (lob_ready if mode == "lobster" else True),
        "vendors": vendor_catalog(),
        "note": "生成/RAG 跟随上方 API 资源开关；AIVIS 探针仍问 C 端平台，不经企业 Gateway。",
    }


async def probe_lobster_gateway(db: AsyncSession | None = None) -> dict[str, Any]:
    """探测企业 AI Gateway（优先）或 Lobster 遗留代理。"""
    if db is not None:
        await refresh_api_resource_from_db(db)
    payload = gateway_status_payload()
    mode = payload.get("mode") or "direct"

    if mode == "enterprise-gateway" and enterprise_ready():
        url = f"{enterprise_text_base_url()}/chat/completions"
        payload["probe_url"] = url
        payload["probe_target"] = "enterprise-gateway"
        try:
            import httpx

            settings = get_settings()
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {settings.enterprise_ai_gateway_api_key.strip()}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.enterprise_ai_text_model or "gpt-4o",
                        "messages": [{"role": "user", "content": "OK"}],
                        "max_tokens": 4,
                    },
                )
            ok = resp.status_code < 500
            payload["probe"] = {"ok": ok, "status": resp.status_code}
            logger.info("enterprise_gateway_probe status=%s url=%s", resp.status_code, url)
        except Exception as exc:
            payload["probe"] = {"ok": False, "error": str(exc)[:200]}
            logger.warning("enterprise_gateway_probe_failed err=%s url=%s", exc, url)
        return payload

    url = lobster_models_url("qwen")
    payload["probe_url"] = url
    payload["probe_target"] = "lobster"
    try:
        import httpx

        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(url)
        payload["probe"] = {"ok": resp.status_code < 500, "status": resp.status_code}
        logger.info("lobster_probe status=%s url=%s", resp.status_code, url)
    except Exception as exc:
        payload["probe"] = {"ok": False, "error": str(exc)[:200]}
        logger.warning("lobster_probe_failed err=%s url=%s", exc, url)
    return payload
