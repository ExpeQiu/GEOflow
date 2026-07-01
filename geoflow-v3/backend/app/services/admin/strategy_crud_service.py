"""策略写操作 — Insight Templates / Monitor / WebIntel / Simulator。"""

import logging

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.geoeval import InsightTemplate
from app.services.admin.production_service import _table_exists

logger = logging.getLogger(__name__)


class InsightTemplateBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    source_url: str = ""


class MonitorQuestionBody(BaseModel):
    question_text: str = Field(min_length=1)
    priority: int = Field(default=50, ge=0, le=100)
    status: str = Field(default="active", pattern="^(active|paused)$")


class WebSourceBody(BaseModel):
    url: str = Field(min_length=8, max_length=500)
    label: str = ""


class BatchReevalBody(BaseModel):
    article_ids: list[int] = Field(min_length=1, max_length=50)


async def list_insight_templates_crud(db: AsyncSession) -> dict:
    rows = (await db.execute(select(InsightTemplate).order_by(InsightTemplate.id.desc()))).scalars().all()
    return {
        "items": [
            {"id": t.id, "name": t.name, "source_url": t.source_url or "", "eeat_score": float(t.eeat_score or 0)}
            for t in rows
        ]
    }


async def create_insight_template(db: AsyncSession, body: InsightTemplateBody) -> dict:
    row = InsightTemplate(name=body.name.strip(), source_url=body.source_url.strip() or None)
    db.add(row)
    await db.flush()
    return {"item": {"id": row.id, "name": row.name}}


async def update_insight_template(db: AsyncSession, template_id: int, body: InsightTemplateBody) -> dict:
    row = await db.get(InsightTemplate, template_id)
    if row is None:
        raise HTTPException(status_code=404, detail="template_not_found")
    row.name = body.name.strip()
    row.source_url = body.source_url.strip() or None
    await db.flush()
    return {"item": {"id": row.id, "name": row.name}}


async def delete_insight_template(db: AsyncSession, template_id: int) -> dict:
    row = await db.get(InsightTemplate, template_id)
    if row is None:
        raise HTTPException(status_code=404, detail="template_not_found")
    await db.delete(row)
    return {"deleted": True}


async def remine_insight_template(db: AsyncSession, template_id: int) -> dict:
    row = await db.get(InsightTemplate, template_id)
    if row is None:
        raise HTTPException(status_code=404, detail="template_not_found")
    from app.workers.celery_app import celery_app

    celery_app.send_task("app.workers.tasks.remine_insight_template", args=[template_id])
    logger.info("insight_template_remine_queued id=%s", template_id)
    return {"queued": True, "template_id": template_id}


async def create_monitor_question(db: AsyncSession, body: MonitorQuestionBody) -> dict:
    if not await _table_exists(db, "geo_monitor_questions"):
        raise HTTPException(status_code=503, detail="monitor_not_migrated")
    row = (
        await db.execute(
            text(
                "INSERT INTO geo_monitor_questions (question_text, priority, status) VALUES (:q, :p, :s) RETURNING id"
            ),
            {"q": body.question_text.strip(), "p": body.priority, "s": body.status},
        )
    ).first()
    await db.flush()
    return {"item": {"id": int(row[0]), "question_text": body.question_text.strip()}}


async def update_monitor_question(db: AsyncSession, question_id: int, body: MonitorQuestionBody) -> dict:
    if not await _table_exists(db, "geo_monitor_questions"):
        raise HTTPException(status_code=503, detail="monitor_not_migrated")
    result = await db.execute(
        text(
            "UPDATE geo_monitor_questions SET question_text=:q, priority=:p, status=:s, updated_at=CURRENT_TIMESTAMP WHERE id=:id"
        ),
        {"q": body.question_text.strip(), "p": body.priority, "s": body.status, "id": question_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="question_not_found")
    return {"item": {"id": question_id}}


async def delete_monitor_question(db: AsyncSession, question_id: int) -> dict:
    if not await _table_exists(db, "geo_monitor_questions"):
        raise HTTPException(status_code=503, detail="monitor_not_migrated")
    await db.execute(text("DELETE FROM geo_monitor_questions WHERE id=:id"), {"id": question_id})
    return {"deleted": True}


async def create_web_source(db: AsyncSession, body: WebSourceBody) -> dict:
    if not await _table_exists(db, "geo_web_sources"):
        raise HTTPException(status_code=503, detail="web_intel_not_migrated")
    row = (
        await db.execute(
            text("INSERT INTO geo_web_sources (url, label) VALUES (:u, :l) RETURNING id"),
            {"u": body.url.strip(), "l": body.label.strip()},
        )
    ).first()
    await db.flush()
    return {"item": {"id": int(row[0]), "url": body.url.strip()}}


async def delete_web_source(db: AsyncSession, source_id: int) -> dict:
    if not await _table_exists(db, "geo_web_sources"):
        raise HTTPException(status_code=503, detail="web_intel_not_migrated")
    await db.execute(text("DELETE FROM geo_web_sources WHERE id=:id"), {"id": source_id})
    return {"deleted": True}


async def refresh_web_source(db: AsyncSession, source_id: int) -> dict:
    if not await _table_exists(db, "geo_web_sources"):
        raise HTTPException(status_code=503, detail="web_intel_not_migrated")
    from app.workers.celery_app import celery_app

    celery_app.send_task("app.workers.tasks.fetch_web_source", args=[source_id])
    return {"queued": True, "source_id": source_id}


async def batch_reevaluate(db: AsyncSession, body: BatchReevalBody) -> dict:
    from app.workers.celery_app import celery_app

    queued = 0
    for aid in body.article_ids:
        article = await db.get(Article, aid)
        if article and not article.deleted_at:
            celery_app.send_task("app.workers.tasks.evaluate_article", args=[aid])
            queued += 1
    logger.info("batch_reevaluate_queued count=%s", queued)
    return {"queued": queued}


async def apply_recommendations(db: AsyncSession, article_id: int) -> dict:
    article = await db.get(Article, article_id)
    if article is None or article.deleted_at:
        raise HTTPException(status_code=404, detail="article_not_found")
    logger.info("apply_recommendations article_id=%s (placeholder)", article_id)
    return {"applied": True, "article_id": article_id, "note": "recommendations_applied_placeholder"}
