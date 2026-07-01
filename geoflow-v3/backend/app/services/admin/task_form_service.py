"""任务创建表单 — 选项加载与校验。"""

import logging
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.distribution import DistributionChannel
from app.models.geoeval import InsightTemplate
from app.models.knowledge import KnowledgeBase
from app.models.material import AiModel, Author, Category, Prompt
from app.models.task import Task
from app.models.tech_ip import TechIpAsset
from app.services.admin.production_service import _table_exists
from app.services.geoflow.task_lifecycle import TaskLifecycleService

logger = logging.getLogger(__name__)

WIKI_PAGE_TYPES = ["concept", "compare", "guide", "glossary", "data", "thread", "topic"]


class AdminTaskCreateBody(BaseModel):
    task_name: str = Field(min_length=1, max_length=200)
    title_library_id: int = Field(ge=1)
    prompt_id: int = Field(ge=1)
    ai_model_id: int = Field(ge=1)
    author_id: int | None = Field(default=None, ge=0)
    image_library_id: int | None = Field(default=None, ge=1)
    image_count: int | None = Field(default=1, ge=0, le=5)
    knowledge_base_id: int | None = Field(default=None, ge=1)
    insight_template_id: int | None = Field(default=None, ge=1)
    fixed_category_id: int | None = Field(default=None, ge=1)
    status: str = Field(default="active", pattern="^(active|paused)$")
    article_limit: int | None = Field(default=10, ge=1, le=99999)
    draft_limit: int | None = Field(default=10, ge=1, le=9999)
    publish_interval: int | None = Field(default=60, ge=1)
    category_mode: str | None = Field(default="smart", pattern="^(smart|fixed|random)$")
    model_selection_mode: str | None = Field(default="fixed", pattern="^(fixed|smart_failover)$")
    content_pipeline_mode: str | None = Field(default="legacy", pattern="^(legacy|pipeline|auto)$")
    content_format: str | None = Field(default="article", pattern="^(article|wiki_mdx)$")
    wiki_page_type: str | None = Field(default="concept")
    tech_ip_asset_id: int | None = Field(default=None, ge=1)
    publish_scope: str | None = Field(default="local_and_distribution", pattern="^(local_and_distribution|distribution_only|local_only)$")
    distribution_channel_ids: list[int] = Field(default_factory=list)
    need_review: bool = False
    is_loop: bool = True
    auto_keywords: bool = True
    auto_description: bool = True


async def build_task_form_options(db: AsyncSession) -> dict[str, Any]:
    categories = (
        await db.execute(select(Category).order_by(Category.sort_order, Category.id))
    ).scalars().all()

    options: dict[str, Any] = {
        "has_categories": len(categories) > 0,
        "title_libraries": await _load_title_libraries(db),
        "prompts": await _load_prompts(db),
        "ai_models": await _load_ai_models(db),
        "image_libraries": await _load_image_libraries(db),
        "knowledge_bases": [
            {"id": kb.id, "name": kb.name}
            for kb in (await db.execute(select(KnowledgeBase).order_by(KnowledgeBase.name))).scalars().all()
        ],
        "authors": [
            {"id": a.id, "name": a.name}
            for a in (await db.execute(select(Author).order_by(Author.name))).scalars().all()
        ],
        "categories": [{"id": c.id, "name": c.name} for c in categories],
        "distribution_channels": await _load_distribution_channels(db),
        "tech_ip_assets": await _load_tech_ip_assets(db),
        "insight_templates": await _load_insight_templates(db),
        "wiki_page_types": WIKI_PAGE_TYPES,
    }
    logger.info(
        "task_form_options_loaded titles=%s prompts=%s models=%s categories=%s",
        len(options["title_libraries"]),
        len(options["prompts"]),
        len(options["ai_models"]),
        len(options["categories"]),
    )
    return options


async def create_admin_task(db: AsyncSession, body: AdminTaskCreateBody) -> dict:
    if not await db.scalar(select(func.count()).select_from(Category)):
        raise HTTPException(status_code=422, detail="no_categories_configured")
    payload, channel_ids = _validate_task_body(body)

    svc = TaskLifecycleService(db)
    task = await svc.create(payload)
    await _sync_task_channels(db, task.id, channel_ids)
    logger.info("admin_task_created task_id=%s name=%s scope=%s", task.id, task.name, payload["publish_scope"])

    return {
        "task": _task_dict(task),
        "distribution_channel_ids": channel_ids,
        "distribution_sync_pending": False,
    }


class AdminTaskUpdateBody(AdminTaskCreateBody):
    pass


async def build_task_detail(db: AsyncSession, task_id: int) -> dict:
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task_not_found")
    channel_ids = await _load_task_channel_ids(db, task_id)
    return {
        "task": {
            **_task_dict(task),
            "task_name": task.name,
            "title_library_id": task.title_library_id,
            "prompt_id": task.prompt_id,
            "ai_model_id": task.ai_model_id,
            "author_id": task.author_id,
            "image_library_id": task.image_library_id,
            "image_count": task.image_count,
            "knowledge_base_id": task.knowledge_base_id,
            "insight_template_id": task.insight_template_id,
            "fixed_category_id": task.fixed_category_id,
            "status": task.status,
            "article_limit": task.article_limit,
            "draft_limit": task.draft_limit,
            "publish_interval": max(1, task.publish_interval // 60),
            "category_mode": task.category_mode,
            "model_selection_mode": task.model_selection_mode,
            "content_pipeline_mode": task.content_pipeline_mode or "legacy",
            "content_format": task.content_format or "article",
            "wiki_page_type": task.wiki_page_type or "concept",
            "tech_ip_asset_id": task.tech_ip_asset_id,
            "publish_scope": task.publish_scope or "local_and_distribution",
            "distribution_channel_ids": channel_ids,
            "need_review": bool(task.need_review),
            "is_loop": bool(task.is_loop),
            "auto_keywords": bool(task.auto_keywords),
            "auto_description": bool(task.auto_description),
        }
    }


async def update_admin_task(db: AsyncSession, task_id: int, body: AdminTaskUpdateBody) -> dict:
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task_not_found")
    payload, channel_ids = _validate_task_body(body)
    svc = TaskLifecycleService(db)
    task = await svc.update(task_id, payload)
    await _sync_task_channels(db, task_id, channel_ids)
    logger.info("admin_task_updated task_id=%s", task_id)
    return {"task": _task_dict(task), "distribution_channel_ids": channel_ids}


async def delete_admin_task(db: AsyncSession, task_id: int) -> dict:
    svc = TaskLifecycleService(db)
    try:
        await svc.delete(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    logger.info("admin_task_deleted task_id=%s", task_id)
    return {"deleted": True}


def _validate_task_body(body: AdminTaskCreateBody) -> tuple[dict, list[int]]:
    if body.draft_limit and body.article_limit and body.draft_limit > body.article_limit:
        raise HTTPException(status_code=422, detail="draft_limit_too_large")

    publish_scope = body.publish_scope or "local_and_distribution"
    channel_ids = [cid for cid in body.distribution_channel_ids if cid > 0]
    if publish_scope == "distribution_only" and not channel_ids:
        raise HTTPException(status_code=422, detail="distribution_only_requires_channel")

    if body.content_format == "wiki_mdx" and publish_scope != "distribution_only":
        publish_scope = "distribution_only"

    category_mode = body.category_mode or "smart"
    if category_mode == "random":
        category_mode = "smart"
    if category_mode == "fixed" and not body.fixed_category_id:
        raise HTTPException(status_code=422, detail="fixed_category_required")

    author_id = body.author_id if body.author_id and body.author_id > 0 else None
    image_library_id = body.image_library_id
    image_count = body.image_count if image_library_id else 0

    payload = {
        "name": body.task_name.strip(),
        "title_library_id": body.title_library_id,
        "prompt_id": body.prompt_id,
        "ai_model_id": body.ai_model_id,
        "author_id": author_id,
        "image_library_id": image_library_id,
        "image_count": image_count or 0,
        "knowledge_base_id": body.knowledge_base_id,
        "insight_template_id": body.insight_template_id,
        "fixed_category_id": body.fixed_category_id if category_mode == "fixed" else None,
        "status": body.status,
        "publish_scope": publish_scope,
        "article_limit": body.article_limit or 10,
        "draft_limit": body.draft_limit or 10,
        "publish_interval": max(1, body.publish_interval or 60) * 60,
        "need_review": 1 if body.need_review else 0,
        "is_loop": 1 if body.is_loop else 0,
        "category_mode": category_mode,
        "model_selection_mode": body.model_selection_mode or "fixed",
        "content_pipeline_mode": body.content_pipeline_mode or "legacy",
        "content_format": body.content_format or "article",
        "wiki_page_type": body.wiki_page_type if body.content_format == "wiki_mdx" else None,
        "tech_ip_asset_id": body.tech_ip_asset_id,
        "auto_keywords": 0 if body.content_format == "wiki_mdx" else (1 if body.auto_keywords else 0),
        "auto_description": 0 if body.content_format == "wiki_mdx" else (1 if body.auto_description else 0),
    }
    return payload, channel_ids


def _task_dict(task: Task) -> dict:
    return {
        "id": task.id,
        "name": task.name,
        "status": task.status,
        "publish_scope": task.publish_scope,
        "content_format": task.content_format,
    }


async def _load_task_channel_ids(db: AsyncSession, task_id: int) -> list[int]:
    if not await _table_exists(db, "task_distribution_channels"):
        return []
    try:
        rows = (
            await db.execute(
                text("SELECT channel_id FROM task_distribution_channels WHERE task_id = :tid ORDER BY channel_id"),
                {"tid": task_id},
            )
        ).all()
        return [int(r[0]) for r in rows]
    except Exception:
        logger.exception("load_task_channel_ids_failed task_id=%s", task_id)
        return []


async def _sync_task_channels(db: AsyncSession, task_id: int, channel_ids: list[int]) -> None:
    if not await _table_exists(db, "task_distribution_channels"):
        return
    try:
        await db.execute(text("DELETE FROM task_distribution_channels WHERE task_id = :tid"), {"tid": task_id})
        for cid in channel_ids:
            await db.execute(
                text(
                    "INSERT INTO task_distribution_channels (task_id, channel_id) VALUES (:tid, :cid) ON CONFLICT DO NOTHING"
                ),
                {"tid": task_id, "cid": cid},
            )
        await db.flush()
    except Exception:
        logger.exception("sync_task_channels_failed task_id=%s", task_id)


async def _load_title_libraries(db: AsyncSession) -> list[dict]:
    if not await _table_exists(db, "title_libraries"):
        return []
    try:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT tl.id, tl.name,
                           (SELECT COUNT(*) FROM titles t WHERE t.library_id = tl.id) AS title_count
                    FROM title_libraries tl
                    ORDER BY tl.id DESC
                    """
                )
            )
        ).all()
        return [{"id": int(r[0]), "name": str(r[1]), "count": int(r[2] or 0)} for r in rows]
    except Exception:
        logger.exception("load_title_libraries_failed")
        return []


async def _load_image_libraries(db: AsyncSession) -> list[dict]:
    if not await _table_exists(db, "image_libraries"):
        return []
    try:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT il.id, il.name,
                           (SELECT COUNT(*) FROM images i WHERE i.library_id = il.id) AS image_count
                    FROM image_libraries il
                    ORDER BY il.name
                    """
                )
            )
        ).all()
        return [{"id": int(r[0]), "name": str(r[1]), "count": int(r[2] or 0)} for r in rows]
    except Exception:
        logger.exception("load_image_libraries_failed")
        return []


async def _load_prompts(db: AsyncSession) -> list[dict]:
    rows = (
        await db.execute(
            select(Prompt)
            .where(or_(Prompt.type == "content", Prompt.type == "body"))
            .order_by(Prompt.id.desc())
        )
    ).scalars().all()
    return [{"id": p.id, "name": p.name} for p in rows]


async def _load_ai_models(db: AsyncSession) -> list[dict]:
    rows = (
        await db.execute(
            select(AiModel)
            .where(
                AiModel.status == "active",
                or_(AiModel.model_type.is_(None), AiModel.model_type == "", AiModel.model_type == "chat"),
            )
            .order_by(AiModel.failover_priority, AiModel.id.desc())
        )
    ).scalars().all()
    return [{"id": m.id, "name": m.name} for m in rows]


async def _load_distribution_channels(db: AsyncSession) -> list[dict]:
    rows = (
        await db.execute(
            select(DistributionChannel)
            .where(DistributionChannel.status == "active")
            .order_by(DistributionChannel.name)
        )
    ).scalars().all()
    items = []
    for ch in rows:
        domain = ""
        if isinstance(ch.config_json, dict):
            domain = str(ch.config_json.get("domain") or ch.config_json.get("base_url") or "")
        items.append({"id": ch.id, "name": ch.name, "domain": domain, "channel_type": ch.channel_type})
    return items


async def _load_tech_ip_assets(db: AsyncSession) -> list[dict]:
    if not await _table_exists(db, "tech_ip_assets"):
        return []
    rows = (
        await db.execute(select(TechIpAsset).order_by(TechIpAsset.priority.desc(), TechIpAsset.name))
    ).scalars().all()
    return [
        {
            "id": a.id,
            "ip_name": a.name,
            "wiki_type": a.wiki_type,
            "status": a.status,
        }
        for a in rows
    ]


async def _load_insight_templates(db: AsyncSession) -> list[dict]:
    if not await _table_exists(db, "insight_templates"):
        return []
    rows = (await db.execute(select(InsightTemplate).order_by(InsightTemplate.id.desc()))).scalars().all()
    return [{"id": t.id, "name": t.name} for t in rows]
