"""文章发布 — 移植 ArticlePublishService。"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article


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
        if article.review_status not in ("approved", "auto_approved"):
            article.review_status = "auto_approved"
        article.status = "published"
        article.published_at = datetime.now(UTC).replace(tzinfo=None)

        from app.workers.celery_app import celery_app

        celery_app.send_task("app.workers.tasks.process_article_distribution", args=[article.id])
        return article
