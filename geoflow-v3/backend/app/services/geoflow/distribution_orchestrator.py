"""分发编排 — 按 publish_scope 与任务渠道绑定过滤。"""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.article import Article
from app.models.distribution import ArticleDistribution, DistributionChannel
from app.models.task import Task
from app.services.admin.production_service import _table_exists
from app.services.geoflow.distribution_publishers import (
    publish_generic_http,
    publish_geoflow_agent,
    publish_wordpress,
)
from app.services.geoflow.geoweb_publisher import GeowebPublisher

logger = get_logger("geoflow.distribution")


class DistributionOrchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.geoweb = GeowebPublisher()

    async def _resolve_channels(self, article: Article) -> list[DistributionChannel]:
        if article.task_id:
            task = await self.db.get(Task, article.task_id)
            if task and task.publish_scope == "local_only":
                return []
            if task and await _table_exists(self.db, "task_distribution_channels"):
                rows = (
                    await self.db.execute(
                        text("SELECT channel_id FROM task_distribution_channels WHERE task_id = :tid"),
                        {"tid": task.id},
                    )
                ).all()
                if rows:
                    ids = [int(r[0]) for r in rows]
                    return list(
                        (
                            await self.db.execute(
                                select(DistributionChannel).where(
                                    DistributionChannel.id.in_(ids),
                                    DistributionChannel.status == "active",
                                )
                            )
                        ).scalars().all()
                    )

        return list(
            (await self.db.execute(select(DistributionChannel).where(DistributionChannel.status == "active"))).scalars().all()
        )

    async def _load_channels_by_ids(self, channel_ids: list[int]) -> list[DistributionChannel]:
        if not channel_ids:
            return []
        return list(
            (
                await self.db.execute(
                    select(DistributionChannel).where(
                        DistributionChannel.id.in_(channel_ids),
                        DistributionChannel.status == "active",
                    )
                )
            )
            .scalars()
            .all()
        )

    async def distribute_article(self, article_id: int, channel_ids: list[int] | None = None) -> None:
        article = await self.db.get(Article, article_id)
        if article is None:
            return

        # Theme 硬门禁：整包未过则跳过分发
        if article.theme_id:
            from app.models.theme import GeoTheme
            from app.services.geoeval.theme_service import (
                mark_theme_distributing,
                mark_theme_published,
                refresh_theme_gate_summary,
            )

            theme = await self.db.get(GeoTheme, article.theme_id)
            if theme and (theme.gate_mode or "soft") == "hard":
                summary = await refresh_theme_gate_summary(self.db, int(article.theme_id))
                if not (summary.get("gate_summary") or {}).get("pack_gate_ok"):
                    logger.info(
                        "distribution_skipped_theme_gate theme_id=%s article_id=%s",
                        article.theme_id,
                        article_id,
                    )
                    return
            await mark_theme_distributing(self.db, int(article.theme_id))

        channels = (
            await self._load_channels_by_ids(channel_ids)
            if channel_ids is not None
            else await self._resolve_channels(article)
        )
        if not channels:
            logger.info("distribution_skipped_no_channels article_id=%s", article_id)
            return

        published_any = False
        for channel in channels:
            existing = (
                await self.db.execute(
                    select(ArticleDistribution).where(
                        ArticleDistribution.article_id == article.id,
                        ArticleDistribution.channel_id == channel.id,
                    )
                )
            ).scalar_one_or_none()
            if existing and existing.status in ("published", "synced", "success"):
                logger.info(
                    "distribution_skip_already_ok article_id=%s channel_id=%s status=%s",
                    article_id,
                    channel.id,
                    existing.status,
                )
                continue
            if existing:
                dist = existing
                dist.status = "pending"
                dist.error_message = ""
            else:
                dist = ArticleDistribution(article_id=article.id, channel_id=channel.id, status="pending")
                self.db.add(dist)
            await self.db.flush()

            try:
                if channel.channel_type == "geoweb":
                    result = await self.geoweb.publish(article, channel=channel)
                    dist.status = "published"
                    dist.remote_url = result.get("url")
                    dist.remote_id = result.get("slug") or result.get("remote_id")
                    published_any = True
                elif channel.channel_type == "geoflow_agent":
                    result = await publish_geoflow_agent(channel, article)
                    dist.status = "published"
                    dist.remote_url = result.get("url")
                    dist.remote_id = result.get("remote_id")
                    published_any = True
                elif channel.channel_type == "wordpress_rest":
                    result = await publish_wordpress(channel, article)
                    dist.status = "published"
                    dist.remote_url = result.get("url")
                    dist.remote_id = result.get("remote_id")
                    published_any = True
                elif channel.channel_type == "generic_http_api":
                    result = await publish_generic_http(channel, article)
                    dist.status = "published"
                    dist.remote_url = result.get("url")
                    dist.remote_id = result.get("remote_id")
                    published_any = True
                else:
                    dist.status = "skipped"
                    dist.error_message = f"unsupported_channel:{channel.channel_type}"
                logger.info(
                    "distribution_ok article_id=%s theme_id=%s channel=%s",
                    article_id,
                    article.theme_id,
                    channel.channel_type,
                )
                if dist.status == "published" and article.task_id:
                    try:
                        from app.services.geoeval.remediation_service import mark_remediation_published

                        rem = await mark_remediation_published(
                            self.db, task_id=int(article.task_id), article_id=int(article.id)
                        )
                        logger.info(
                            "remediation_hook_after_distribution article_id=%s task_id=%s theme_id=%s result=%s",
                            article_id,
                            article.task_id,
                            article.theme_id,
                            rem.get("status"),
                        )
                    except Exception as rem_exc:  # noqa: BLE001
                        logger.warning(
                            "remediation_hook_failed article_id=%s error=%s",
                            article_id,
                            rem_exc,
                        )
            except Exception as exc:  # noqa: BLE001
                dist.status = "failed"
                dist.error_message = str(exc)[:500]
                dist.attempt_count += 1
                logger.exception("distribution_failed", article_id=article_id, error=str(exc))

        if published_any and article.theme_id:
            from app.services.geoeval.theme_service import mark_theme_published

            hub = None
            wiki_meta = article.wiki_meta if isinstance(article.wiki_meta, dict) else {}
            if wiki_meta.get("type") == "topic":
                hub = article.slug
            await mark_theme_published(self.db, int(article.theme_id), hub_slug=hub)