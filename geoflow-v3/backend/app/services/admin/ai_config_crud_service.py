"""AI 模型与提示词 CRUD — Admin BFF。"""

import logging

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.material import AiModel, Prompt

logger = logging.getLogger(__name__)


class AiModelBody(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    model_id: str = Field(min_length=1, max_length=100)
    api_key: str = Field(default="", max_length=500)
    api_url: str = "https://api.openai.com/v1"
    model_type: str = "chat"
    failover_priority: int = 100
    status: str = Field(default="active", pattern="^(active|inactive)$")


class PromptBody(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1)
    variables: str = ""


async def list_ai_models(db: AsyncSession) -> dict:
    rows = (await db.execute(select(AiModel).order_by(AiModel.failover_priority, AiModel.id.desc()))).scalars().all()
    return {
        "items": [
            {
                "id": m.id,
                "name": m.name,
                "model_id": m.model_id,
                "model_type": m.model_type,
                "api_url": m.api_url,
                "failover_priority": m.failover_priority,
                "status": m.status,
                "has_api_key": bool(m.api_key),
            }
            for m in rows
        ]
    }


async def create_ai_model(db: AsyncSession, body: AiModelBody) -> dict:
    if not body.api_key.strip():
        raise HTTPException(status_code=422, detail="api_key_required")
    row = AiModel(**body.model_dump())
    db.add(row)
    await db.flush()
    logger.info("ai_model_created id=%s", row.id)
    return {"item": {"id": row.id, "name": row.name}}


async def update_ai_model(db: AsyncSession, model_id: int, body: AiModelBody) -> dict:
    row = await db.get(AiModel, model_id)
    if row is None:
        raise HTTPException(status_code=404, detail="model_not_found")
    data = body.model_dump()
    if not data.get("api_key"):
        data.pop("api_key", None)
    for k, v in data.items():
        setattr(row, k, v)
    await db.flush()
    return {"item": {"id": row.id, "name": row.name}}


async def delete_ai_model(db: AsyncSession, model_id: int) -> dict:
    row = await db.get(AiModel, model_id)
    if row is None:
        raise HTTPException(status_code=404, detail="model_not_found")
    await db.delete(row)
    return {"deleted": True}


async def test_ai_model(db: AsyncSession, model_id: int) -> dict:
    row = await db.get(AiModel, model_id)
    if row is None:
        raise HTTPException(status_code=404, detail="model_not_found")
    from app.core.config import get_settings

    if get_settings().ai_mock_mode:
        return {"ok": True, "mock": True, "message": "mock_mode_ok"}

    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{row.api_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {row.api_key}"},
            )
        if resp.status_code >= 400:
            return {"ok": False, "mock": False, "message": f"http_{resp.status_code}"}
        return {"ok": True, "mock": False, "message": "connectivity_ok"}
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
