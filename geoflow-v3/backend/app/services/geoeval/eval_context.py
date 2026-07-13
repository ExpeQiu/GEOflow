"""GEO 评估上下文 — 知识库与模型解析。"""

import logging

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.material import AiModel
from app.models.task import Task
from app.services.admin.production_service import _table_exists
from app.services.geoflow.llm_client import get_active_chat_model

logger = logging.getLogger(__name__)


async def load_default_kb_id(db: AsyncSession) -> int | None:
    if not await _table_exists(db, "site_settings"):
        return None
    row = (
        await db.execute(
            text("SELECT setting_value FROM site_settings WHERE setting_key = 'default_knowledge_base_id' LIMIT 1")
        )
    ).scalar_one_or_none()
    try:
        return int(row) if row else None
    except (TypeError, ValueError):
        return None


async def resolve_kb_id(db: AsyncSession, article: Article) -> int | None:
    if article.task_id:
        task = await db.get(Task, article.task_id)
        if task and task.knowledge_base_id:
            return int(task.knowledge_base_id)
    return await load_default_kb_id(db)


async def resolve_eval_model(db: AsyncSession, article: Article) -> AiModel | None:
    if article.task_id:
        task = await db.get(Task, article.task_id)
        if task and task.ai_model_id:
            model = await db.get(AiModel, task.ai_model_id)
            if model and model.status == "active":
                logger.info("geo_eval_model task_id=%s model_id=%s name=%s", task.id, model.id, model.name)
                return model
    model = await get_active_chat_model(db)
    if model:
        logger.info("geo_eval_model fallback model_id=%s name=%s", model.id, model.name)
    return model
