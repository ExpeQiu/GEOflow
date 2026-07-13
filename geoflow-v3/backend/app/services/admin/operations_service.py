"""L3 运营 Hub — Admin BFF 聚合。"""

import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.distribution import ArticleDistribution, DistributionChannel
from app.models.material import AiModel
from app.models.task import Task, TaskRun
from app.services.admin.distribution_citation_service import build_distribution_citation_summary

logger = logging.getLogger(__name__)


async def build_operations_overview(db: AsyncSession) -> dict:
    stats = await _base_ops_stats(db)
    return {"stats": stats}


async def build_tasks_panel(db: AsyncSession) -> dict:
    tasks = (await db.execute(select(Task).order_by(Task.id.desc()).limit(100))).scalars().all()
    task_ids = [t.id for t in tasks]
    latest_runs: dict[int, TaskRun] = {}
    if task_ids:
        runs = (
            await db.execute(
                select(TaskRun).where(TaskRun.task_id.in_(task_ids)).order_by(TaskRun.id.desc())
            )
        ).scalars().all()
        for run in runs:
            if run.task_id not in latest_runs:
                latest_runs[run.task_id] = run

    model_ids = {t.ai_model_id for t in tasks}
    models: dict[int, AiModel] = {}
    if model_ids:
        model_rows = (await db.execute(select(AiModel).where(AiModel.id.in_(model_ids)))).scalars().all()
        models = {m.id: m for m in model_rows}

    items = []
    for task in tasks:
        run = latest_runs.get(task.id)
        model = models.get(task.ai_model_id)
        items.append(
            {
                "id": task.id,
                "name": task.name,
                "status": task.status,
                "publish_scope": task.publish_scope or "local_and_distribution",
                "content_format": task.content_format or "article",
                "created_count": task.created_count,
                "published_count": task.published_count,
                "loop_count": task.loop_count,
                "article_limit": task.article_limit,
                "publish_interval": task.publish_interval,
                "model_selection_mode": task.model_selection_mode,
                "ai_model_name": model.name if model else "",
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "last_run_at": task.last_run_at.isoformat() if task.last_run_at else None,
                "batch_status": run.status if run else None,
                "batch_error_message": run.error_message if run else "",
            }
        )

    return {"tasks": items, "stats": await _base_ops_stats(db)}


async def build_articles_panel(db: AsyncSession, review_status: str | None = None) -> dict:
    query = select(Article).where(Article.deleted_at.is_(None)).order_by(Article.id.desc()).limit(100)
    if review_status:
        query = query.where(Article.review_status == review_status)

    articles = (await db.execute(query)).scalars().all()
    stats = {
        "total": int(
            await db.scalar(select(func.count()).select_from(Article).where(Article.deleted_at.is_(None))) or 0
        ),
        "published": int(
            await db.scalar(
                select(func.count())
                .select_from(Article)
                .where(Article.status == "published", Article.deleted_at.is_(None))
            )
            or 0
        ),
        "draft": int(
            await db.scalar(
                select(func.count())
                .select_from(Article)
                .where(Article.status == "draft", Article.deleted_at.is_(None))
            )
            or 0
        ),
        "pending_review": int(
            await db.scalar(
                select(func.count())
                .select_from(Article)
                .where(Article.review_status == "pending", Article.deleted_at.is_(None))
            )
            or 0
        ),
    }

    return {
        "stats": stats,
        "articles": [
            {
                "id": a.id,
                "title": a.title,
                "status": a.status,
                "review_status": a.review_status,
                "eval_status": a.eval_status,
                "content_format": a.content_format or "article",
                "task_id": a.task_id,
                "view_count": a.view_count,
                "published_at": a.published_at.isoformat() if a.published_at else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in articles
        ],
    }


async def build_distribution_panel(db: AsyncSession) -> dict:
    channels = (await db.execute(select(DistributionChannel).order_by(DistributionChannel.id.desc()))).scalars().all()
    dist_rows = (
        await db.execute(select(ArticleDistribution.status, func.count()).group_by(ArticleDistribution.status))
    ).all()
    dist_counts = {str(status): int(count) for status, count in dist_rows}

    pending = dist_counts.get("pending", 0) + dist_counts.get("sending", 0) + dist_counts.get("queued", 0)
    failed = dist_counts.get("failed", 0)
    synced = dist_counts.get("synced", 0) + dist_counts.get("published", 0)
    total_jobs = sum(dist_counts.values())

    channel_stats = []
    for ch in channels:
        ch_rows = (
            await db.execute(
                select(ArticleDistribution.status, func.count())
                .where(ArticleDistribution.channel_id == ch.id)
                .group_by(ArticleDistribution.status)
            )
        ).all()
        ch_counts = {str(s): int(c) for s, c in ch_rows}
        channel_stats.append(
            {
                "id": ch.id,
                "name": ch.name,
                "channel_type": ch.channel_type,
                "status": ch.status,
                "pending": ch_counts.get("pending", 0) + ch_counts.get("sending", 0),
                "failed": ch_counts.get("failed", 0),
                "synced": ch_counts.get("synced", 0),
            }
        )

    recent_jobs = (
        await db.execute(select(ArticleDistribution).order_by(ArticleDistribution.id.desc()).limit(30))
    ).scalars().all()

    citation_summary = await build_distribution_citation_summary(db)

    return {
        "stats": {
            "total": len(channels),
            "active": sum(1 for c in channels if c.status == "active"),
            "pending": pending,
            "failed": failed,
            "synced": synced,
            "jobs_total": total_jobs,
        },
        "channels": channel_stats,
        "recent_jobs": [
            {
                "id": j.id,
                "article_id": j.article_id,
                "channel_id": j.channel_id,
                "status": j.status,
                "remote_url": j.remote_url,
                "error_message": j.error_message[:120] if j.error_message else "",
                "updated_at": j.updated_at.isoformat() if j.updated_at else None,
            }
            for j in recent_jobs
        ],
        "citation_summary": citation_summary,
    }


async def _base_ops_stats(db: AsyncSession) -> dict:
    defaults = {
        "total_tasks": 0,
        "active_tasks": 0,
        "running_jobs": 0,
        "pending_jobs": 0,
        "failed_jobs": 0,
        "total_articles": 0,
        "published_articles": 0,
        "pending_review": 0,
        "channels_total": 0,
        "channels_active": 0,
        "distribution_pending": 0,
        "distribution_failed": 0,
    }
    try:
        job_rows = (await db.execute(select(TaskRun.status, func.count()).group_by(TaskRun.status))).all()
        job_counts = {str(s): int(c) for s, c in job_rows}
        defaults["running_jobs"] = job_counts.get("running", 0)
        defaults["pending_jobs"] = job_counts.get("pending", 0) + job_counts.get("queued", 0)
        defaults["failed_jobs"] = job_counts.get("failed", 0)

        defaults["total_tasks"] = int(await db.scalar(select(func.count()).select_from(Task)) or 0)
        defaults["active_tasks"] = int(
            await db.scalar(select(func.count()).select_from(Task).where(Task.status == "active")) or 0
        )
        defaults["total_articles"] = int(
            await db.scalar(select(func.count()).select_from(Article).where(Article.deleted_at.is_(None))) or 0
        )
        defaults["published_articles"] = int(
            await db.scalar(
                select(func.count())
                .select_from(Article)
                .where(Article.status == "published", Article.deleted_at.is_(None))
            )
            or 0
        )
        defaults["pending_review"] = int(
            await db.scalar(
                select(func.count())
                .select_from(Article)
                .where(Article.review_status == "pending", Article.deleted_at.is_(None))
            )
            or 0
        )
        defaults["channels_total"] = int(await db.scalar(select(func.count()).select_from(DistributionChannel)) or 0)
        defaults["channels_active"] = int(
            await db.scalar(
                select(func.count()).select_from(DistributionChannel).where(DistributionChannel.status == "active")
            )
            or 0
        )

        dist_rows = (
            await db.execute(select(ArticleDistribution.status, func.count()).group_by(ArticleDistribution.status))
        ).all()
        dist_counts = {str(s): int(c) for s, c in dist_rows}
        defaults["distribution_pending"] = (
            dist_counts.get("pending", 0) + dist_counts.get("sending", 0) + dist_counts.get("queued", 0)
        )
        defaults["distribution_failed"] = dist_counts.get("failed", 0)
    except Exception:
        logger.exception("operations_stats_query_failed")

    return defaults
