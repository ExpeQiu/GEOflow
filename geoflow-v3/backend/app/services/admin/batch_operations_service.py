"""运营批量操作 — Admin BFF。"""

import logging

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.task import Task
from app.services.geoflow.task_lifecycle import TaskLifecycleService

logger = logging.getLogger(__name__)


class BatchIdsBody(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=100)


async def batch_start_tasks(db: AsyncSession, body: BatchIdsBody) -> dict:
    svc = TaskLifecycleService(db)
    started = 0
    for tid in body.ids:
        task = await db.get(Task, tid)
        if task:
            await svc.start(task.id)
            started += 1
    logger.info("batch_start_tasks count=%s", started)
    return {"started": started}


async def batch_trash_articles(db: AsyncSession, body: BatchIdsBody) -> dict:
    from datetime import UTC, datetime

    trashed = 0
    for aid in body.ids:
        article = await db.get(Article, aid)
        if article and not article.deleted_at:
            article.deleted_at = datetime.now(UTC)
            article.status = "trashed"
            trashed += 1
    await db.flush()
    logger.info("batch_trash_articles count=%s", trashed)
    return {"trashed": trashed}


async def batch_publish_articles(db: AsyncSession, body: BatchIdsBody) -> dict:
    from app.services.geoflow.article_publish import ArticlePublishService

    svc = ArticlePublishService(db)
    published = 0
    for aid in body.ids:
        article = await db.get(Article, aid)
        if article and not article.deleted_at:
            try:
                await svc.publish(aid)
                published += 1
            except Exception as exc:
                logger.warning("batch_publish_failed article_id=%s err=%s", aid, exc)
    logger.info("batch_publish_articles count=%s", published)
    return {"published": published}
