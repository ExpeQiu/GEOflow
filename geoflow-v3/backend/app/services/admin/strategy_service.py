"""L1 策略 Hub — Admin BFF 聚合。"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.article import Article
from app.models.distribution import ArticleDistribution, DistributionChannel
from app.models.geoeval import ArticleEvaluation, InsightTemplate
from app.models.material import AiModel
from app.models.task import Task, TaskRun
from app.models.tech_ip import TechIpAsset

logger = logging.getLogger(__name__)
settings = get_settings()


async def build_strategy_overview(db: AsyncSession) -> dict:
    return {
        "geo_eval": await _geo_eval_summary(db),
        "tech_brand": await _tech_brand_metrics(db),
        "monitor": await _monitor_kpis(db),
        "analytics": await _analytics_snapshot(db),
    }


async def build_monitor_panel(db: AsyncSession) -> dict:
    return {
        "dashboard": await _monitor_kpis(db),
        "questions": await _fetch_rows(
            db,
            """
            SELECT id, question_text, priority, status, last_scan_at
            FROM geo_monitor_questions
            ORDER BY priority DESC, id DESC
            LIMIT 50
            """,
            ("id", "question_text", "priority", "status", "last_scan_at"),
        ),
        "recent_runs": await _fetch_rows(
            db,
            """
            SELECT id, status, platform, question_count, probe_count, completed_at
            FROM geo_monitor_runs
            ORDER BY id DESC
            LIMIT 8
            """,
            ("id", "status", "platform", "question_count", "probe_count", "completed_at"),
        ),
        "recent_probes": await _fetch_rows(
            db,
            """
            SELECT pr.id, pr.platform, pr.brand_rank, pr.mentioned, pr.snippet, mq.question_text
            FROM geo_monitor_probe_results pr
            JOIN geo_monitor_questions mq ON mq.id = pr.question_id
            ORDER BY pr.id DESC
            LIMIT 24
            """,
            ("id", "platform", "brand_rank", "mentioned", "snippet", "question_text"),
        ),
    }


async def build_geo_eval_panel(db: AsyncSession) -> dict:
    return {
        "gate": _gate_config(),
        "summary": await _geo_eval_summary(db),
        "failure_top_n": await _failure_top_n(db),
        "recent_failures": await _recent_eval_failures(db),
        "recent_alerts": await _recent_alerts(db),
    }


async def build_analytics_panel(db: AsyncSession) -> dict:
    snapshot = await _analytics_snapshot(db)
    trend = await _publication_trend(db, days=7)
    return {
        "snapshot": snapshot,
        "publication_trend": trend,
        "task_health": await _task_health(db),
        "ai_usage": await _ai_usage(db),
        "top_articles": await _top_articles(db),
    }


async def build_web_intel_panel(db: AsyncSession) -> dict:
    return {
        "sources": await _fetch_rows(
            db,
            """
            SELECT id, url, label, fetch_status, last_fetched_at
            FROM geo_web_sources
            ORDER BY id DESC
            LIMIT 30
            """,
            ("id", "url", "label", "fetch_status", "last_fetched_at"),
        ),
        "reports": await _fetch_rows(
            db,
            """
            SELECT id, title, status, created_at
            FROM geo_web_insight_reports
            ORDER BY id DESC
            LIMIT 10
            """,
            ("id", "title", "status", "created_at"),
        ),
    }


async def build_insight_templates(db: AsyncSession) -> dict:
    rows = (await db.execute(select(InsightTemplate).order_by(InsightTemplate.id.desc()).limit(30))).scalars().all()
    return {
        "items": [
            {
                "id": t.id,
                "name": t.name,
                "source_url": t.source_url,
                "eeat_score": float(t.eeat_score) if t.eeat_score is not None else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in rows
        ]
    }


async def _geo_eval_summary(db: AsyncSession) -> dict:
    defaults = {"pending_eval": 0, "passed": 0, "failed": 0, "skipped": 0}
    try:
        rows = (
            await db.execute(
                select(Article.eval_status, func.count())
                .where(Article.deleted_at.is_(None))
                .group_by(Article.eval_status)
            )
        ).all()
        for status, count in rows:
            key = str(status)
            if key in defaults:
                defaults[key] = int(count)
            elif key == "pending":
                defaults["pending_eval"] += int(count)
    except Exception:
        logger.exception("geo_eval_summary_failed")
    return defaults


async def _failure_top_n(db: AsyncSession, limit: int = 8) -> list[dict]:
    try:
        rows = (
            await db.execute(
                select(ArticleEvaluation.failure_reason, func.count())
                .where(ArticleEvaluation.status == "failed", ArticleEvaluation.failure_reason.is_not(None))
                .group_by(ArticleEvaluation.failure_reason)
                .order_by(func.count().desc())
                .limit(limit)
            )
        ).all()
        return [{"failure_reason": str(r[0]), "total": int(r[1])} for r in rows if r[0]]
    except Exception:
        logger.exception("failure_top_n_failed")
        return []


async def _recent_eval_failures(db: AsyncSession, limit: int = 10) -> list[dict]:
    try:
        rows = (
            await db.execute(
                select(ArticleEvaluation)
                .where(ArticleEvaluation.status == "failed")
                .order_by(ArticleEvaluation.id.desc())
                .limit(limit)
            )
        ).scalars().all()
        items = []
        for ev in rows:
            metrics = ev.metrics if isinstance(ev.metrics, dict) else {}
            items.append(
                {
                    "article_id": ev.article_id,
                    "failure_reason": ev.failure_reason or "unknown",
                    "rank": int(metrics.get("rank", 0) or 0),
                    "found": bool(metrics.get("found", False)),
                    "updated_at": ev.updated_at.isoformat() if ev.updated_at else None,
                }
            )
        return items
    except Exception:
        logger.exception("recent_eval_failures_failed")
        return []


async def _recent_alerts(db: AsyncSession, limit: int = 5) -> list[dict]:
    return await _fetch_rows(
        db,
        """
        SELECT id, alert_type, message, created_at
        FROM geo_admin_alerts
        ORDER BY id DESC
        LIMIT :limit
        """,
        ("id", "alert_type", "message", "created_at"),
        {"limit": limit},
    )


async def _tech_brand_metrics(db: AsyncSession) -> dict:
    empty = {
        "total_assets": 0,
        "p0_total": 0,
        "p0_ready": 0,
        "p0_coverage_pct": 0.0,
        "wiki_articles": 0,
        "wiki_compliance_pct": 0.0,
        "gweb_sync_total": 0,
        "gweb_sync_success": 0,
        "gweb_sync_rate_pct": 0.0,
        "needs_update_assets": 0,
    }
    try:
        total_assets = int(await db.scalar(select(func.count()).select_from(TechIpAsset)) or 0)
        p0_total = int(
            await db.scalar(select(func.count()).select_from(TechIpAsset).where(TechIpAsset.priority <= 30)) or 0
        )
        p0_ready = int(
            await db.scalar(
                select(func.count())
                .select_from(TechIpAsset)
                .where(TechIpAsset.priority <= 30, TechIpAsset.wiki_slug.is_not(None), TechIpAsset.status == "active")
            )
            or 0
        )
        needs_update = int(
            await db.scalar(select(func.count()).select_from(TechIpAsset).where(TechIpAsset.status.in_(["需更新", "needs_update"])))
            or 0
        )
        wiki_articles = int(
            await db.scalar(
                select(func.count())
                .select_from(Article)
                .where(Article.content_format == "wiki_mdx", Article.deleted_at.is_(None))
            )
            or 0
        )
        wiki_compliant = int(
            await db.scalar(
                select(func.count())
                .select_from(Article)
                .where(
                    Article.content_format == "wiki_mdx",
                    Article.deleted_at.is_(None),
                    Article.eval_status.in_(["passed", "skipped"]),
                )
            )
            or 0
        )

        gweb_total = 0
        gweb_success = 0
        try:
            gweb_total = int(
                await db.scalar(
                    select(func.count())
                    .select_from(ArticleDistribution)
                    .join(DistributionChannel, ArticleDistribution.channel_id == DistributionChannel.id)
                    .where(DistributionChannel.channel_type == "gweb_wiki")
                )
                or 0
            )
            gweb_success = int(
                await db.scalar(
                    select(func.count())
                    .select_from(ArticleDistribution)
                    .join(DistributionChannel, ArticleDistribution.channel_id == DistributionChannel.id)
                    .where(
                        DistributionChannel.channel_type == "gweb_wiki",
                        ArticleDistribution.status.in_(["synced", "published", "success"]),
                    )
                )
                or 0
            )
        except Exception:
            pass

        empty.update(
            {
                "total_assets": total_assets,
                "p0_total": p0_total,
                "p0_ready": p0_ready,
                "p0_coverage_pct": round(p0_ready / p0_total * 100, 1) if p0_total else 0.0,
                "wiki_articles": wiki_articles,
                "wiki_compliance_pct": round(wiki_compliant / wiki_articles * 100, 1) if wiki_articles else 0.0,
                "gweb_sync_total": gweb_total,
                "gweb_sync_success": gweb_success,
                "gweb_sync_rate_pct": round(gweb_success / gweb_total * 100, 1) if gweb_total else 0.0,
                "needs_update_assets": needs_update,
            }
        )
    except Exception:
        logger.exception("tech_brand_metrics_failed")
    return empty


async def _monitor_kpis(db: AsyncSession) -> dict:
    from app.services.geoeval.monitor_probe import aggregate_probe_kpis

    kpis = await aggregate_probe_kpis(db)
    kpis["question_count"] = await _safe_count(db, "geo_monitor_questions")
    if kpis["probe_count"] == 0:
        kpis["probe_count"] = await _safe_count(db, "geo_monitor_runs")
    return kpis


async def _analytics_snapshot(db: AsyncSession) -> dict:
    try:
        total_views = int(
            await db.scalar(select(func.coalesce(func.sum(Article.view_count), 0)).where(Article.deleted_at.is_(None))) or 0
        )
        return {
            "total_articles": int(
                await db.scalar(select(func.count()).select_from(Article).where(Article.deleted_at.is_(None))) or 0
            ),
            "published_articles": int(
                await db.scalar(
                    select(func.count())
                    .select_from(Article)
                    .where(Article.status == "published", Article.deleted_at.is_(None))
                )
                or 0
            ),
            "total_views": total_views,
            "active_tasks": int(
                await db.scalar(select(func.count()).select_from(Task).where(Task.status == "active")) or 0
            ),
            "eval_passed": (await _geo_eval_summary(db))["passed"],
            "eval_failed": (await _geo_eval_summary(db))["failed"],
        }
    except Exception:
        logger.exception("analytics_snapshot_failed")
        return {
            "total_articles": 0,
            "published_articles": 0,
            "total_views": 0,
            "active_tasks": 0,
            "eval_passed": 0,
            "eval_failed": 0,
        }


async def _publication_trend(db: AsyncSession, days: int = 7) -> list[dict]:
    start = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        rows = (
            await db.execute(
                select(func.date(Article.created_at), func.count())
                .where(Article.created_at >= start, Article.deleted_at.is_(None))
                .group_by(func.date(Article.created_at))
                .order_by(func.date(Article.created_at))
            )
        ).all()
        return [{"date": str(d), "count": int(c)} for d, c in rows]
    except Exception:
        return []


async def _task_health(db: AsyncSession) -> dict:
    rows = (await db.execute(select(TaskRun.status, func.count()).group_by(TaskRun.status))).all()
    counts = {str(s): int(c) for s, c in rows}
    return {
        "running": counts.get("running", 0),
        "pending": counts.get("pending", 0) + counts.get("queued", 0),
        "failed": counts.get("failed", 0),
    }


async def _ai_usage(db: AsyncSession) -> dict:
    return {
        "used_today": int(await db.scalar(select(func.coalesce(func.sum(AiModel.used_today), 0))) or 0),
        "total_used": int(await db.scalar(select(func.coalesce(func.sum(AiModel.total_used), 0))) or 0),
        "active_models": int(
            await db.scalar(select(func.count()).select_from(AiModel).where(AiModel.status == "active")) or 0
        ),
    }


async def _top_articles(db: AsyncSession, limit: int = 5) -> list[dict]:
    rows = (
        await db.execute(
            select(Article.id, Article.title, Article.view_count, Article.status)
            .where(Article.deleted_at.is_(None))
            .order_by(Article.view_count.desc())
            .limit(limit)
        )
    ).all()
    return [{"id": r[0], "title": r[1], "view_count": r[2], "status": r[3]} for r in rows]


def _gate_config() -> dict:
    return {
        "enabled": settings.geo_eval_enabled,
        "gate_enabled": settings.geo_eval_wiki_gate_enabled,
        "rollout_percent": 100,
    }


async def _fetch_rows(
    db: AsyncSession,
    sql: str,
    columns: tuple[str, ...],
    params: dict | None = None,
) -> list[dict]:
    try:
        result = await db.execute(text(sql), params or {})
        return [dict(zip(columns, row)) for row in result.all()]
    except Exception:
        return []


async def _safe_count(db: AsyncSession, table: str) -> int:
    try:
        return int(await db.scalar(text(f"SELECT COUNT(*) FROM {table}")) or 0)
    except Exception:
        return 0
