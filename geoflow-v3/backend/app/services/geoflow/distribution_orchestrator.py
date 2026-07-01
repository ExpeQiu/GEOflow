"""分发编排 — 移植 DistributionOrchestrator。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.article import Article
from app.models.distribution import ArticleDistribution, DistributionChannel
from app.services.geoflow.gweb_wiki_publisher import GwebWikiPublisher

logger = get_logger("geoflow.distribution")


class DistributionOrchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.gweb = GwebWikiPublisher()

    async def distribute_article(self, article_id: int) -> None:
        article = await self.db.get(Article, article_id)
        if article is None:
            return

        channels = (await self.db.execute(select(DistributionChannel).where(DistributionChannel.status == "active"))).scalars().all()

        for channel in channels:
            dist = ArticleDistribution(article_id=article.id, channel_id=channel.id, status="pending")
            self.db.add(dist)
            await self.db.flush()

            try:
                if channel.channel_type == "gweb_wiki" and article.content_format == "wiki_mdx":
                    result = await self.gweb.publish(article)
                    dist.status = "published"
                    dist.remote_url = result.get("url")
                    dist.remote_id = result.get("slug")
                else:
                    dist.status = "skipped"
                    dist.error_message = f"unsupported_channel:{channel.channel_type}"
                logger.info("distribution_ok", article_id=article_id, channel=channel.channel_type)
            except Exception as exc:  # noqa: BLE001
                dist.status = "failed"
                dist.error_message = str(exc)[:500]
                dist.attempt_count += 1
                logger.exception("distribution_failed", article_id=article_id, error=str(exc))
