"""文章发布 — 移植 ArticlePublishService。"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.article import Article

logger = get_logger("geoflow.publish")


class ArticlePublishService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def publish(self, article_id: int) -> Article:
        article = await self.db.get(Article, article_id)
        if article is None:
            raise ValueError("article_not_found")
        # soft 模式 advisory 仅供参考，不拦发布；hard 模式 failed 才拦截
        if article.eval_status not in ("passed", "skipped", "advisory"):
            raise ValueError(f"eval_gate_blocked:{article.eval_status}")

        # Theme 包级门禁：hard 下整包未过则拦截分发入口
        if article.theme_id:
            from app.models.theme import GeoTheme
            from app.services.geoeval.theme_service import refresh_theme_gate_summary

            theme = await self.db.get(GeoTheme, article.theme_id)
            if theme and (theme.gate_mode or "soft") == "hard":
                summary = await refresh_theme_gate_summary(self.db, int(article.theme_id))
                gs = summary.get("gate_summary") or {}
                if not gs.get("pack_gate_ok"):
                    # 单篇仍可落库为 published，但硬门禁下阻断分发（由 orchestrator 二次校验）
                    # 这里对硬门禁：若本篇不是 passed 则拦；整包未齐时允许本篇 published 但不触发分发
                    if article.eval_status != "passed":
                        raise ValueError(f"theme_gate_blocked:{article.eval_status}")
                    logger.info(
                        "theme_hard_gate_defer_distribution theme_id=%s article_id=%s pack_gate_ok=false",
                        article.theme_id,
                        article.id,
                    )
                    if article.review_status not in ("approved", "auto_approved"):
                        article.review_status = "auto_approved"
                    article.status = "published"
                    article.published_at = datetime.now(UTC).replace(tzinfo=None)
                    return article

        if article.review_status not in ("approved", "auto_approved"):
            article.review_status = "auto_approved"
        article.status = "published"
        article.published_at = datetime.now(UTC).replace(tzinfo=None)

        from app.workers.celery_app import celery_app

        celery_app.send_task("app.workers.tasks.process_article_distribution", args=[article.id])
        logger.info(
            "article_publish_queued article_id=%s theme_id=%s eval_status=%s",
            article.id,
            article.theme_id,
            article.eval_status,
        )
        return article
