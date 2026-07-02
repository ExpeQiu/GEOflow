"""OpenAI 兼容 Chat Completions 轻量封装。"""

import json
import logging
import re

import httpx
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.material import AiModel

logger = logging.getLogger(__name__)


async def get_active_chat_model(db: AsyncSession) -> AiModel | None:
    row = (
        await db.execute(
            select(AiModel)
            .where(
                AiModel.status == "active",
                or_(AiModel.model_type.is_(None), AiModel.model_type == "", AiModel.model_type == "chat"),
            )
            .order_by(AiModel.failover_priority, AiModel.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return row


def _parse_json_text(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


async def chat_json(
    model: AiModel,
    *,
    system: str,
    user: str,
    timeout: float = 45.0,
) -> dict:
    url = f"{model.api_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model.model_id,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {model.api_key}", "Content-Type": "application/json"},
            json=payload,
        )
    if resp.status_code >= 400:
        logger.warning("llm_chat_failed status=%s body=%s", resp.status_code, resp.text[:200])
        raise RuntimeError(f"llm_http_{resp.status_code}")
    data = resp.json()
    content = ""
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("llm_empty_response") from None
    return _parse_json_text(content)


async def chat_json_or_mock(db: AsyncSession, *, system: str, user: str) -> dict | None:
    if get_settings().ai_mock_mode:
        return None
    model = await get_active_chat_model(db)
    if model is None:
        return None
    try:
        return await chat_json(model, system=system, user=user)
    except Exception as exc:
        logger.warning("llm_chat_json_failed err=%s", exc)
        return None
