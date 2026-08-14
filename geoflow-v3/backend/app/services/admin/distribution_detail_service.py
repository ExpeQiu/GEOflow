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
    theme_id: int | None = None,
    limit: int = 50,
) -> dict:
    from sqlalchemy import text

    from app.services.admin.production_service import _table_exists

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

    theme_meta: dict[int, tuple[str, str | None, bool | None]] = {}
    theme_ids = {a.theme_id for a in articles.values() if a.theme_id}
    if theme_ids and await _table_exists(db, "geo_themes"):
        rows = (
            await db.execute(
                text(
                    """
                    SELECT id, title, gate_mode,
                           COALESCE((gate_summary->>'pack_gate_ok')::text, '')
                    FROM geo_themes WHERE id = ANY(:ids)
                    """
                ),
                {"ids": list(theme_ids)},
            )
        ).all()
        for r in rows:
            pack_ok = True if r[3] == "true" else (False if r[3] == "false" else None)
            theme_meta[int(r[0])] = (str(r[1] or ""), str(r[2] or "soft"), pack_ok)

    items = []
    for j in jobs:
        art = articles.get(j.article_id)
        tid = art.theme_id if art else None
        if theme_id is not None and tid != theme_id:
            continue
        tmeta = theme_meta.get(tid) if tid else None
        gate_mode = tmeta[1] if tmeta else None
        pack_ok = tmeta[2] if tmeta else None
        gate_hint = "待门禁" if (gate_mode or "soft") == "hard" and pack_ok is not True else None
        items.append(
            {
                "id": j.id,
                "article_id": j.article_id,
                "article_title": art.title if art else "",
                "channel_id": j.channel_id,
                "channel_name": channels[j.channel_id].name if j.channel_id in channels else "",
                "status": j.status,
                "remote_id": j.remote_id,
                "remote_url": j.remote_url,
                "error_message": (j.error_message or "")[:200],
                "attempt_count": j.attempt_count,
                "updated_at": j.updated_at.isoformat() if j.updated_at else None,
                "theme_id": tid,
                "theme_title": tmeta[0] if tmeta else None,
                "theme_gate_mode": gate_mode,
                "theme_pack_gate_ok": pack_ok,
                "theme_gate_hint": gate_hint,
            }
        )

    return {"jobs": items}


class DistributionJobUpdateBody(BaseModel):
    status: str = Field(pattern="^(pending|cancelled|failed)$")


async def update_distribution_job(db: AsyncSession, job_id: int, body: DistributionJobUpdateBody) -> dict:
    job = await db.get(ArticleDistribution, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job_not_found")
    job.status = body.status
    await db.flush()
    logger.info("admin_distribution_job_updated id=%s status=%s", job.id, body.status)
    return {"job": {"id": job.id, "status": job.status}}


async def delete_distribution_job(db: AsyncSession, job_id: int) -> dict:
    job = await db.get(ArticleDistribution, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job_not_found")
    await db.delete(job)
    await db.flush()
    logger.info("admin_distribution_job_deleted id=%s", job_id)
    return {"deleted": True, "id": job_id}


async def delete_admin_distribution_channel(db: AsyncSession, channel_id: int) -> dict:
    channel = await db.get(DistributionChannel, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="channel_not_found")
    active_jobs = int(
        await db.scalar(
            select(func.count())
            .select_from(ArticleDistribution)
            .where(ArticleDistribution.channel_id == channel_id, ArticleDistribution.status.in_(("pending", "sending", "queued")))
        )
        or 0
    )
    if active_jobs > 0:
        raise HTTPException(status_code=422, detail="channel_has_active_jobs")
    channel.status = "deleted"
    await db.flush()
    logger.info("admin_distribution_channel_deleted id=%s", channel_id)
    return {"deleted": True, "id": channel_id, "status": "deleted"}


async def check_channel_health(db: AsyncSession, channel_id: int) -> dict:
    channel = await db.get(DistributionChannel, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="channel_not_found")
    cfg = channel.config_json if isinstance(channel.config_json, dict) else {}
    endpoint = str(cfg.get("endpoint_url") or cfg.get("domain") or "").strip()
    healthy = False
    http_status = None
    message = "no_endpoint"
    if endpoint:
        import httpx

        url = endpoint if endpoint.startswith("http") else f"https://{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                resp = await client.get(url)
            http_status = resp.status_code
            healthy = resp.status_code < 500
            message = "ok" if healthy else f"http_{resp.status_code}"
        except Exception as exc:
            message = str(exc)[:120]
    logger.info("channel_health_check id=%s healthy=%s", channel_id, healthy)
    return {
        "channel_id": channel_id,
        "healthy": healthy,
        "endpoint": endpoint,
        "http_status": http_status,
        "message": message,
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

        celery_app.send_task(
            "app.workers.tasks.process_article_distribution",
            args=[job.article_id, [job.channel_id]],
        )
    except Exception:
        logger.exception("distribution_retry_queue_failed job_id=%s", job.id)
    return {"job": {"id": job.id, "status": job.status}}


class AdminDistributionBatchBody(BaseModel):
    article_ids: list[int] = Field(min_length=1)
    channel_ids: list[int] = Field(min_length=1)
    interval_seconds: int = Field(default=0, ge=0, le=86400)


async def create_distribution_batch(db: AsyncSession, body: AdminDistributionBatchBody) -> dict:
    article_ids = sorted({int(i) for i in body.article_ids if int(i) > 0})
    channel_ids = sorted({int(i) for i in body.channel_ids if int(i) > 0})
    if not article_ids or not channel_ids:
        raise HTTPException(status_code=422, detail="article_ids_and_channel_ids_required")

    articles = list(
        (
            await db.execute(
                select(Article).where(
                    Article.id.in_(article_ids),
                    Article.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    found_article_ids = {int(a.id) for a in articles}
    missing_articles = [aid for aid in article_ids if aid not in found_article_ids]
    if missing_articles:
        raise HTTPException(status_code=404, detail=f"articles_not_found:{missing_articles[:5]}")

    channels = list(
        (
            await db.execute(
                select(DistributionChannel).where(
                    DistributionChannel.id.in_(channel_ids),
                    DistributionChannel.status == "active",
                )
            )
        )
        .scalars()
        .all()
    )
    found_channel_ids = {int(c.id) for c in channels}
    missing_channels = [cid for cid in channel_ids if cid not in found_channel_ids]
    if missing_channels:
        raise HTTPException(status_code=422, detail=f"active_channels_not_found:{missing_channels[:5]}")

    created = 0
    skipped = 0
    queued_articles: list[int] = []
    for article in articles:
        for channel in channels:
            existing = (
                await db.execute(
                    select(ArticleDistribution).where(
                        ArticleDistribution.article_id == article.id,
                        ArticleDistribution.channel_id == channel.id,
                    )
                )
            ).scalar_one_or_none()
            if existing and existing.status in ("published", "synced", "success"):
                skipped += 1
                continue
            if existing:
                existing.status = "pending"
                existing.error_message = ""
            else:
                db.add(
                    ArticleDistribution(
                        article_id=article.id,
                        channel_id=channel.id,
                        status="pending",
                    )
                )
                created += 1
        queued_articles.append(int(article.id))

    await db.flush()

    interval = int(body.interval_seconds or 0)
    queued = 0
    try:
        from app.workers.celery_app import celery_app

        for idx, article_id in enumerate(queued_articles):
            countdown = idx * interval if interval > 0 else 0
            celery_app.send_task(
                "app.workers.tasks.process_article_distribution",
                args=[article_id, channel_ids],
                countdown=countdown,
            )
            queued += 1
    except Exception:
        logger.exception(
            "admin_distribution_batch_queue_failed article_count=%s channel_count=%s",
            len(article_ids),
            len(channel_ids),
        )

    logger.info(
        "admin_distribution_batch article_count=%s channel_count=%s created=%s skipped=%s queued=%s interval=%s",
        len(article_ids),
        len(channel_ids),
        created,
        skipped,
        queued,
        interval,
    )
    return {
        "article_count": len(article_ids),
        "channel_count": len(channel_ids),
        "jobs_created": created,
        "jobs_skipped": skipped,
        "queued": queued,
        "interval_seconds": interval,
    }
