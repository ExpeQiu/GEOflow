"""分发渠道详情、编辑与 jobs — Admin BFF。"""

import logging
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.distribution import ArticleDistribution, DistributionChannel
from app.services.admin.distribution_form_service import (
    AdminDistributionCreateBody,
    _build_type_config,
    _is_valid_http_endpoint,
    _normalize_domain,
    _normalize_endpoint_url,
    _validate_type_specific,
)

logger = logging.getLogger(__name__)


class AdminDistributionUpdateBody(AdminDistributionCreateBody):
    pass


async def build_channel_detail(db: AsyncSession, channel_id: int) -> dict:
    channel = await db.get(DistributionChannel, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="channel_not_found")
    cfg = channel.config_json if isinstance(channel.config_json, dict) else {}
    job_counts = dict(
        (await db.execute(
            select(ArticleDistribution.status, func.count())
            .where(ArticleDistribution.channel_id == channel_id)
            .group_by(ArticleDistribution.status)
        )).all()
    )
    return {
        "channel": {
            "id": channel.id,
            "name": channel.name,
            "channel_type": channel.channel_type,
            "status": channel.status,
            "domain": cfg.get("domain", ""),
            "endpoint_url": cfg.get("endpoint_url", ""),
            "description": cfg.get("description", ""),
            "front_mode": cfg.get("front_mode", "static"),
            "template_key": cfg.get("template_key") or "",
            "config": cfg,
            "created_at": channel.created_at.isoformat() if channel.created_at else None,
            "updated_at": channel.updated_at.isoformat() if channel.updated_at else None,
        },
        "stats": {
            "pending": job_counts.get("pending", 0) + job_counts.get("sending", 0) + job_counts.get("queued", 0),
            "failed": job_counts.get("failed", 0),
            "synced": job_counts.get("synced", 0) + job_counts.get("published", 0),
            "total": sum(int(v) for v in job_counts.values()),
        },
    }


async def update_admin_distribution_channel(
    db: AsyncSession, channel_id: int, body: AdminDistributionUpdateBody
) -> dict:
    channel = await db.get(DistributionChannel, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="channel_not_found")

    endpoint_url = _normalize_endpoint_url(body.endpoint_url)
    if not _is_valid_http_endpoint(endpoint_url):
        raise HTTPException(status_code=422, detail="invalid_endpoint_url")
    domain = _normalize_domain(body.domain)
    _validate_type_specific(body)

    cfg: dict[str, Any] = {
        "domain": domain,
        "endpoint_url": endpoint_url,
        "description": body.description.strip(),
        "front_mode": body.front_mode,
        "template_key": body.template_key.strip() or None,
    }
    cfg.update(_build_type_config(body, endpoint_url))

    channel.name = body.name.strip()
    channel.channel_type = body.channel_type
    channel.status = body.status
    channel.config_json = cfg
    await db.flush()
    logger.info("admin_distribution_channel_updated id=%s status=%s", channel.id, channel.status)
    return (await build_channel_detail(db, channel.id))["channel"]


async def toggle_channel_status(db: AsyncSession, channel_id: int, action: str) -> dict:
    channel = await db.get(DistributionChannel, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="channel_not_found")
    if action == "pause":
        channel.status = "paused"
    elif action == "activate":
        channel.status = "active"
    else:
        raise HTTPException(status_code=422, detail="invalid_action")
    await db.flush()
    logger.info("admin_distribution_channel_toggled id=%s status=%s", channel.id, channel.status)
    return {"id": channel.id, "status": channel.status}


async def build_distribution_jobs(
    db: AsyncSession,
    *,
    channel_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
) -> dict:
    query = select(ArticleDistribution).order_by(ArticleDistribution.id.desc()).limit(limit)
    if channel_id:
        query = query.where(ArticleDistribution.channel_id == channel_id)
    if status:
        query = query.where(ArticleDistribution.status == status)
    jobs = (await db.execute(query)).scalars().all()

    article_ids = {j.article_id for j in jobs}
    channel_ids = {j.channel_id for j in jobs}
    articles: dict[int, Article] = {}
    channels: dict[int, DistributionChannel] = {}
    if article_ids:
        for a in (await db.execute(select(Article).where(Article.id.in_(article_ids)))).scalars().all():
            articles[a.id] = a
    if channel_ids:
        for c in (await db.execute(select(DistributionChannel).where(DistributionChannel.id.in_(channel_ids)))).scalars().all():
            channels[c.id] = c

    return {
        "jobs": [
            {
                "id": j.id,
                "article_id": j.article_id,
                "article_title": articles[j.article_id].title if j.article_id in articles else "",
                "channel_id": j.channel_id,
                "channel_name": channels[j.channel_id].name if j.channel_id in channels else "",
                "status": j.status,
                "remote_id": j.remote_id,
                "remote_url": j.remote_url,
                "error_message": (j.error_message or "")[:200],
                "attempt_count": j.attempt_count,
                "updated_at": j.updated_at.isoformat() if j.updated_at else None,
            }
            for j in jobs
        ]
    }


async def retry_distribution_job(db: AsyncSession, job_id: int) -> dict:
    job = await db.get(ArticleDistribution, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job_not_found")
    job.status = "pending"
    job.error_message = ""
    await db.flush()
    logger.info("admin_distribution_job_retry id=%s article_id=%s", job.id, job.article_id)
    try:
        from app.workers.celery_app import celery_app

        celery_app.send_task("app.workers.tasks.distribute_article", args=[job.id])
    except Exception:
        logger.exception("distribution_retry_queue_failed job_id=%s", job.id)
    return {"job": {"id": job.id, "status": job.status}}
