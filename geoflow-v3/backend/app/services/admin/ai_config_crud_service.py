"""AI 模型与提示词 CRUD — Admin BFF。"""

import logging

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.material import AiModel, Prompt
from app.ai.llm_gateway import (
    ENTERPRISE_KEY_SENTINEL,
    LOBSTER_KEY_SENTINEL,
    effective_gateway_mode,
    enterprise_ready,
    gateway_status_payload,
    infer_vendor,
    public_model_view,
    refresh_api_resource_from_db,
    resolve_llm_endpoint,
)
from app.core.api_key_crypto import encrypt_api_key
from app.services.admin.settings_crud_service import write_activity_log

logger = logging.getLogger(__name__)


class AiModelBody(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    model_id: str = Field(min_length=1, max_length=100)
    api_key: str = Field(default="", max_length=500)
    api_url: str = "https://api.openai.com/v1"
    model_type: str = "chat"
    vendor: str = ""
    connection_kind: str = Field(
        default="inherit",
        pattern="^(inherit|direct|lobster|enterprise-gateway|enterprise)$",
    )
    failover_priority: int = 100
    status: str = Field(default="active", pattern="^(active|inactive)$")


class PromptBody(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1)
    variables: str = ""


def _prepare_model_data(body: AiModelBody, *, existing_key: str | None = None) -> dict:
    data = body.model_dump()
    vendor = (data.get("vendor") or "").strip() or infer_vendor(body.model_id, body.api_url, body.name)
    data["vendor"] = vendor
    kind = data.get("connection_kind") or "inherit"
    via = kind if kind in ("direct", "lobster", "enterprise-gateway", "enterprise") else effective_gateway_mode()
    if via == "enterprise":
        via = "enterprise-gateway"
    key = (data.get("api_key") or "").strip()
    if not key and existing_key is not None:
        data.pop("api_key", None)
        return data
    if via == "enterprise-gateway" and not key:
        data["api_key"] = ENTERPRISE_KEY_SENTINEL
    elif via == "lobster" and not key:
        data["api_key"] = LOBSTER_KEY_SENTINEL
    elif not key:
        raise HTTPException(status_code=422, detail="api_key_required")
    elif key not in ("mock", LOBSTER_KEY_SENTINEL, ENTERPRISE_KEY_SENTINEL):
        data["api_key"] = encrypt_api_key(key)
    return data


async def list_ai_models(db: AsyncSession) -> dict:
    await refresh_api_resource_from_db(db)
    rows = (await db.execute(select(AiModel).order_by(AiModel.failover_priority, AiModel.id.desc()))).scalars().all()
    return {
        **gateway_status_payload(),
        "items": [public_model_view(m) for m in rows],
    }


async def create_ai_model(db: AsyncSession, body: AiModelBody, actor_id: int = 0) -> dict:
    data = _prepare_model_data(body)
    row = AiModel(**data)
    db.add(row)
    await db.flush()
    await write_activity_log(db, actor_id, "ai_model.create", "ai_model", str(row.id), row.name)
    logger.info("ai_model_created id=%s vendor=%s kind=%s", row.id, row.vendor, row.connection_kind)
    return {"item": public_model_view(row)}


async def update_ai_model(db: AsyncSession, model_id: int, body: AiModelBody, actor_id: int = 0) -> dict:
    row = await db.get(AiModel, model_id)
    if row is None:
        raise HTTPException(status_code=404, detail="model_not_found")
    data = _prepare_model_data(body, existing_key=row.api_key)
    for k, v in data.items():
        setattr(row, k, v)
    await db.flush()
    await write_activity_log(db, actor_id, "ai_model.update", "ai_model", str(model_id), row.name)
    logger.info("ai_model_updated id=%s vendor=%s kind=%s", row.id, row.vendor, row.connection_kind)
    return {"item": public_model_view(row)}


async def delete_ai_model(db: AsyncSession, model_id: int, actor_id: int = 0) -> dict:
    row = await db.get(AiModel, model_id)
    if row is None:
        raise HTTPException(status_code=404, detail="model_not_found")
    await write_activity_log(db, actor_id, "ai_model.delete", "ai_model", str(model_id), row.name)
    await db.delete(row)
    return {"deleted": True}


async def test_ai_model(db: AsyncSession, model_id: int) -> dict:
    row = await db.get(AiModel, model_id)
    if row is None:
        raise HTTPException(status_code=404, detail="model_not_found")
    from app.core.config import get_settings

    if get_settings().ai_mock_mode:
        return {"ok": True, "mock": True, "message": "mock_mode_ok — 请设 AI_MOCK_MODE=false 后重测"}

    import httpx

    ep = resolve_llm_endpoint(row)
    base = ep.base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {ep.api_key}", "Content-Type": "application/json"}
    model_type = (row.model_type or "chat").strip().lower()

    if ep.via == "enterprise-gateway" and not ep.api_key:
        return {"ok": False, "mock": False, "message": "enterprise_key_missing — 请配置 ENTERPRISE_AI_GATEWAY_API_KEY"}
    if ep.via == "lobster" and not ep.api_key:
        return {"ok": False, "mock": False, "message": "lobster_token_missing — 请配置 LOBSTER_PROXY_TOKEN"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if model_type == "embedding":
                resp = await client.post(
                    f"{base}/embeddings",
                    headers=headers,
                    json={"model": ep.model_id, "input": "geoflow embedding connectivity probe"},
                )
            else:
                resp = await client.post(
                    f"{base}/chat/completions",
                    headers=headers,
                    json={
                        "model": ep.model_id,
                        "messages": [{"role": "user", "content": "只回复 OK"}],
                        "max_tokens": 8,
                        "temperature": 0,
                    },
                )
        if resp.status_code >= 400:
            detail = (resp.text or "")[:160]
            logger.warning("ai_model_test_http id=%s status=%s body=%s", model_id, resp.status_code, detail)
            return {"ok": False, "mock": False, "message": f"http_{resp.status_code}:{detail}"}
        logger.info("ai_model_test_ok id=%s type=%s model=%s via=%s", model_id, model_type, ep.model_id, ep.via)
        return {"ok": True, "mock": False, "message": f"{model_type}_ok via={ep.via}", "via": ep.via}
    except Exception as exc:
        logger.warning("ai_model_test_failed id=%s err=%s", model_id, exc)
        return {"ok": False, "mock": False, "message": str(exc)[:200]}


async def list_prompts(db: AsyncSession) -> dict:
    rows = (await db.execute(select(Prompt).order_by(Prompt.id.desc()))).scalars().all()
    return {
        "items": [
            {"id": p.id, "name": p.name, "type": p.type, "content_preview": (p.content or "")[:80]}
            for p in rows
        ]
    }


async def create_prompt(db: AsyncSession, body: PromptBody) -> dict:
    row = Prompt(**body.model_dump())
    db.add(row)
    await db.flush()
    return {"item": {"id": row.id, "name": row.name}}


async def update_prompt(db: AsyncSession, prompt_id: int, body: PromptBody) -> dict:
    row = await db.get(Prompt, prompt_id)
    if row is None:
        raise HTTPException(status_code=404, detail="prompt_not_found")
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    await db.flush()
    return {"item": {"id": row.id, "name": row.name}}


async def delete_prompt(db: AsyncSession, prompt_id: int) -> dict:
    row = await db.get(Prompt, prompt_id)
    if row is None:
        raise HTTPException(status_code=404, detail="prompt_not_found")
    await db.delete(row)
    return {"deleted": True}
