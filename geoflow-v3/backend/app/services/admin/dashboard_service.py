"""Admin Dashboard 聚合数据 — 对齐 legacy DashboardController。"""

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.distribution import ArticleDistribution, DistributionChannel
from app.models.geoeval import ArticleEvaluation
from app.models.knowledge import KnowledgeBase, KnowledgeChunk
from app.models.material import AiModel, Prompt
from app.models.task import Task, TaskRun
from app.models.tech_ip import TechIpAsset
from app.services.admin.dashboard_automation import build_automation

logger = logging.getLogger(__name__)


async def build_dashboard_payload(db: AsyncSession) -> dict:
    defaults = {
        "total_articles": 0,
        "published_articles": 0,
        "draft_articles": 0,
        "pending_review": 0,
        "total_tasks": 0,
        "active_tasks": 0,
        "running_jobs": 0,
        "pending_jobs": 0,
        "failed_jobs": 0,
        "tech_ip_assets_count": 0,
        "knowledge_bases": 0,
        "knowledge_chunks": 0,
        "vectorized_chunks": 0,
        "chat_models": 0,
        "embedding_models": 0,
        "ai_used_today": 0,
        "total_prompts": 0,
        "channels_total": 0,
        "channels_active": 0,
        "distribution_pending": 0,
        "distribution_failed": 0,
        "eval_pending": 0,
        "eval_failed": 0,
        "eval_passed": 0,
        "today_articles": 0,
        "today_views": 0,
        "body_prompts": 0,
        "special_prompts": 0,
    }

    try:
        job_rows = (
            await db.execute(select(TaskRun.status, func.count()).group_by(TaskRun.status))
        ).all()
        job_counts = {str(status): int(count) for status, count in job_rows}
        defaults["running_jobs"] = job_counts.get("running", 0)
        defaults["pending_jobs"] = job_counts.get("pending", 0)
        defaults["failed_jobs"] = job_counts.get("failed", 0)

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
        defaults["draft_articles"] = int(
            await db.scalar(
                select(func.count()).select_from(Article).where(Article.status == "draft", Article.deleted_at.is_(None))
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

        defaults["total_tasks"] = int(await db.scalar(select(func.count()).select_from(Task)) or 0)
        defaults["active_tasks"] = int(
            await db.scalar(select(func.count()).select_from(Task).where(Task.status == "active")) or 0
        )
        defaults["tech_ip_assets_count"] = int(await db.scalar(select(func.count()).select_from(TechIpAsset)) or 0)
        defaults["knowledge_bases"] = int(await db.scalar(select(func.count()).select_from(KnowledgeBase)) or 0)
        defaults["knowledge_chunks"] = int(await db.scalar(select(func.count()).select_from(KnowledgeChunk)) or 0)
        defaults["vectorized_chunks"] = int(
            await db.scalar(
                select(func.count()).select_from(KnowledgeChunk).where(KnowledgeChunk.embedding_vector.is_not(None))
            )
            or 0
        )

        defaults["chat_models"] = int(
            await db.scalar(
                select(func.count()).select_from(AiModel).where(AiModel.status == "active", AiModel.model_type == "chat")
            )
            or 0
        )
        defaults["embedding_models"] = int(
            await db.scalar(
                select(func.count())
                .select_from(AiModel)
                .where(AiModel.status == "active", AiModel.model_type == "embedding")
            )
            or 0
        )
        defaults["ai_used_today"] = int(
            await db.scalar(select(func.coalesce(func.sum(AiModel.used_today), 0)).select_from(AiModel)) or 0
        )
        defaults["total_prompts"] = int(await db.scalar(select(func.count()).select_from(Prompt)) or 0)
        defaults["body_prompts"] = int(
            await db.scalar(select(func.count()).select_from(Prompt).where(Prompt.type == "body")) or 0
        )
        defaults["special_prompts"] = int(
            await db.scalar(select(func.count()).select_from(Prompt).where(Prompt.type == "special")) or 0
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
        dist_counts = {str(status): int(count) for status, count in dist_rows}
        defaults["distribution_pending"] = dist_counts.get("pending", 0) + dist_counts.get("sending", 0)
        defaults["distribution_failed"] = dist_counts.get("failed", 0)

        eval_rows = (
            await db.execute(select(ArticleEvaluation.status, func.count()).group_by(ArticleEvaluation.status))
        ).all()
        eval_counts = {str(status): int(count) for status, count in eval_rows}
        defaults["eval_pending"] = eval_counts.get("pending_eval", 0)
        defaults["eval_failed"] = eval_counts.get("failed", 0)
        defaults["eval_passed"] = eval_counts.get("passed", 0)

        # Article.created_at 为 naive UTC，避免 asyncpg 时区混用报错
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=None
        )
        defaults["today_articles"] = int(
            await db.scalar(
                select(func.count()).select_from(Article).where(Article.created_at >= today_start, Article.deleted_at.is_(None))
            )
            or 0
        )
        defaults["today_views"] = int(
            await db.scalar(select(func.coalesce(func.sum(Article.view_count), 0)).select_from(Article).where(Article.deleted_at.is_(None)))
            or 0
        )
    except Exception:
        logger.exception("dashboard_stats_query_failed")

    theme_funnel = {"by_status": {}, "total": 0, "blockers": [], "draft": 0, "producing": 0, "published": 0, "measuring": 0}
    try:
        from app.services.geoeval.theme_service import theme_funnel_stats

        theme_funnel = await theme_funnel_stats(db)
    except Exception:
        logger.exception("dashboard_theme_funnel_failed")

    return {
        "version": "3.0.0",
        "site_name": "GEOFlow",
        "stats": defaults,
        "automation": build_automation(defaults),
        "theme_funnel": theme_funnel,
    }
