"""L3 运营 Hub — Admin BFF 聚合。"""

import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.distribution import ArticleDistribution, DistributionChannel
from app.models.knowledge import KnowledgeBase
from app.models.material import AiModel
from app.models.task import Task, TaskRun
from app.services.admin.distribution_citation_service import build_distribution_citation_summary
from app.services.admin.production_service import _table_exists
from app.services.geoflow.wiki_types import is_distribution_article

logger = logging.getLogger(__name__)


async def build_operations_overview(db: AsyncSession) -> dict:
    stats = await _base_ops_stats(db)
    return {"stats": stats}


def _parse_pack_gate_ok(raw: str | None) -> bool | None:
    if raw == "true":
        return True
    if raw == "false":
        return False
    return None


def _theme_gate_hint(gate_mode: str | None, pack_gate_ok: bool | None) -> str | None:
    if (gate_mode or "soft") == "hard" and pack_gate_ok is not True:
        return "待门禁"
    return None


async def build_tasks_panel(db: AsyncSession, theme_id: int | None = None) -> dict:
    from sqlalchemy import text

    tasks = (await db.execute(select(Task).order_by(Task.id.desc()).limit(100))).scalars().all()
    theme_by_task: dict[int, tuple[int, str, str | None, bool | None]] = {}
    if await _table_exists(db, "geo_themes"):
        rows = (
            await db.execute(
                text(
                    """
                    SELECT task_id, id, title, gate_mode,
                           COALESCE((gate_summary->>'pack_gate_ok')::text, '') AS pack_ok
                    FROM geo_themes
                    WHERE task_id IS NOT NULL
                    """
                )
            )
        ).all()
        for r in rows:
            tid = int(r[0]) if r[0] else None
            if tid:
                theme_by_task[tid] = (
                    int(r[1]),
                    str(r[2] or ""),
                    str(r[3] or "soft"),
                    _parse_pack_gate_ok(str(r[4]) if r[4] is not None else None),
                )

    if theme_id is not None:
        tasks = [t for t in tasks if theme_by_task.get(t.id, (None,))[0] == theme_id]

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
    kb_ids = {t.knowledge_base_id for t in tasks if t.knowledge_base_id}
    models: dict[int, AiModel] = {}
    knowledge_names: dict[int, str] = {}
    title_lib_names: dict[int, str] = {}
    if model_ids:
        model_rows = (await db.execute(select(AiModel).where(AiModel.id.in_(model_ids)))).scalars().all()
        models = {m.id: m for m in model_rows}
    if kb_ids:
        kb_rows = (await db.execute(select(KnowledgeBase).where(KnowledgeBase.id.in_(kb_ids)))).scalars().all()
        knowledge_names = {k.id: k.name for k in kb_rows}
    if await _table_exists(db, "title_libraries"):
        tl_ids = {t.title_library_id for t in tasks}
        if tl_ids:
            rows = (
                await db.execute(
                    text("SELECT id, name FROM title_libraries WHERE id = ANY(:ids)"),
                    {"ids": list(tl_ids)},
                )
            ).all()
            title_lib_names = {int(r[0]): str(r[1]) for r in rows}

    items = []
    for task in tasks:
        run = latest_runs.get(task.id)
        model = models.get(task.ai_model_id)
        th = theme_by_task.get(task.id)
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
                "title_library_name": title_lib_names.get(task.title_library_id, ""),
                "knowledge_base_name": knowledge_names.get(task.knowledge_base_id or 0, ""),
                "knowledge_base_id": task.knowledge_base_id,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "last_run_at": task.last_run_at.isoformat() if task.last_run_at else None,
                "batch_status": run.status if run else None,
                "batch_error_message": run.error_message if run else "",
                "theme_id": th[0] if th else None,
                "theme_title": th[1] if th else None,
                "theme_gate_mode": th[2] if th else None,
                "theme_pack_gate_ok": th[3] if th else None,
                "theme_gate_hint": _theme_gate_hint(th[2], th[3]) if th else None,
            }
        )

    return {"tasks": items, "stats": await _base_ops_stats(db)}


async def build_articles_panel(
    db: AsyncSession,
    review_status: str | None = None,
    theme_id: int | None = None,
) -> dict:
    from sqlalchemy import text

    query = (
        select(Article)
        .where(Article.deleted_at.is_(None))
        .order_by(Article.id.desc())
        .limit(100)
    )
    if review_status:
        query = query.where(Article.review_status == review_status)
    if theme_id is not None:
        query = query.where(Article.theme_id == theme_id)

    articles = [
        a
        for a in (await db.execute(query)).scalars().all()
        if is_distribution_article(
            content_format=a.content_format,
            slug=a.slug or "",
            title=a.title or "",
            wiki_meta=a.wiki_meta if isinstance(a.wiki_meta, dict) else {},
        )
    ]
    theme_titles: dict[int, str] = {}
    theme_gate: dict[int, tuple[str, bool | None]] = {}
    theme_ids = {a.theme_id for a in articles if a.theme_id}
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
            tid = int(r[0])
            theme_titles[tid] = str(r[1] or "")
            theme_gate[tid] = (str(r[2] or "soft"), _parse_pack_gate_ok(str(r[3]) if r[3] is not None else None))

    all_active = (
        await db.execute(select(Article).where(Article.deleted_at.is_(None)))
    ).scalars().all()
    distribution_articles = [
        a
        for a in all_active
        if is_distribution_article(
            content_format=a.content_format,
            slug=a.slug or "",
            title=a.title or "",
            wiki_meta=a.wiki_meta if isinstance(a.wiki_meta, dict) else {},
        )
    ]

    stats = {
        "total": len(distribution_articles),
        "published": sum(1 for a in distribution_articles if a.status == "published"),
        "draft": sum(1 for a in distribution_articles if a.status == "draft"),
        "pending_review": sum(1 for a in distribution_articles if a.review_status == "pending"),
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
                "theme_id": a.theme_id,
                "theme_title": theme_titles.get(a.theme_id) if a.theme_id else None,
                "theme_gate_mode": theme_gate.get(a.theme_id, (None, None))[0] if a.theme_id else None,
                "theme_pack_gate_ok": theme_gate.get(a.theme_id, (None, None))[1] if a.theme_id else None,
                "theme_gate_hint": (
                    _theme_gate_hint(
                        theme_gate.get(a.theme_id, (None, None))[0],
                        theme_gate.get(a.theme_id, (None, None))[1],
                    )
                    if a.theme_id
                    else None
                ),
                "view_count": a.view_count,
                "published_at": a.published_at.isoformat() if a.published_at else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in articles
        ],
    }


async def build_distribution_panel(db: AsyncSession, theme_id: int | None = None) -> dict:
    from sqlalchemy import text

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

    article_ids = {j.article_id for j in recent_jobs if j.article_id}
    article_theme: dict[int, tuple[int | None, str | None, str | None, bool | None]] = {}
    if article_ids:
        articles = (
            await db.execute(select(Article).where(Article.id.in_(list(article_ids))))
        ).scalars().all()
        theme_ids = {a.theme_id for a in articles if a.theme_id}
        theme_meta: dict[int, tuple[str, str | None, bool | None]] = {}
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
                theme_meta[int(r[0])] = (
                    str(r[1] or ""),
                    str(r[2] or "soft"),
                    _parse_pack_gate_ok(str(r[3]) if r[3] is not None else None),
                )
        for a in articles:
            if a.theme_id and a.theme_id in theme_meta:
                title, mode, ok = theme_meta[a.theme_id]
                article_theme[a.id] = (a.theme_id, title, mode, ok)
            else:
                article_theme[a.id] = (a.theme_id, None, None, None)

    job_rows = []
    for j in recent_jobs:
        th = article_theme.get(j.article_id, (None, None, None, None))
        if theme_id is not None and th[0] != theme_id:
            continue
        job_rows.append(
            {
                "id": j.id,
                "article_id": j.article_id,
                "channel_id": j.channel_id,
                "status": j.status,
                "remote_url": j.remote_url,
                "canonical_url": getattr(j, "canonical_url", None),
                "tracked_url": getattr(j, "tracked_url", None),
                "error_message": j.error_message[:120] if j.error_message else "",
                "updated_at": j.updated_at.isoformat() if j.updated_at else None,
                "theme_id": th[0],
                "theme_title": th[1],
                "theme_gate_mode": th[2],
                "theme_pack_gate_ok": th[3],
                "theme_gate_hint": _theme_gate_hint(th[2], th[3]),
            }
        )

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
        "recent_jobs": job_rows,
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
