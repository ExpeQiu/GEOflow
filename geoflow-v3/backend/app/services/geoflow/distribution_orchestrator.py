"""分发编排 — 按 publish_scope 与任务渠道绑定过滤；GEOweb 优先 + 外渠追踪链接。"""

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
from app.services.geoflow.distribution_trace import (
    build_external_tracked_url,
    is_external_channel,
    is_geoweb_channel,
    require_geoweb_first,
    resolve_canonical_from_article,
    sort_channels_for_distribution,
    trace_enabled,
)
from app.services.geoflow.geoweb_publisher import GeowebPublisher

logger = get_logger("geoflow.distribution")

_SUCCESS_STATUSES = ("published", "synced", "success")


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

    async def _find_geoweb_success_url(self, article_id: int) -> str | None:
        row = (
            await self.db.execute(
                select(ArticleDistribution, DistributionChannel)
                .join(DistributionChannel, DistributionChannel.id == ArticleDistribution.channel_id)
                .where(
                    ArticleDistribution.article_id == article_id,
                    DistributionChannel.channel_type == "geoweb",
                    ArticleDistribution.status.in_(_SUCCESS_STATUSES),
                )
                .order_by(ArticleDistribution.updated_at.desc(), ArticleDistribution.id.desc())
                .limit(1)
            )
        ).first()
        if not row:
            return None
        dist, _channel = row
        return (dist.canonical_url or dist.remote_url or "").strip() or None

    async def _resolve_canonical_url(self, article: Article, session_canonical: str | None) -> str | None:
        if session_canonical:
            return session_canonical
        from_article = resolve_canonical_from_article(article)
        if from_article:
            return from_article
        return await self._find_geoweb_success_url(int(article.id))

    async def _publish_geoweb_channel(
        self,
        article: Article,
        channel: DistributionChannel,
        dist: ArticleDistribution,
    ) -> str | None:
        result = await self.geoweb.publish(article, channel=channel)
        url = (result.get("url") or "").strip() or None
        dist.status = "published"
        dist.remote_url = url
        dist.canonical_url = url
        dist.tracked_url = None
        dist.trace_params_json = None
        dist.remote_id = result.get("slug") or result.get("remote_id")
        return url

    async def _publish_external_channel(
        self,
        article: Article,
        channel: DistributionChannel,
        dist: ArticleDistribution,
        *,
        canonical_url: str | None,
    ) -> None:
        cfg = channel.config_json if isinstance(channel.config_json, dict) else {}
        if require_geoweb_first(cfg, channel.channel_type) and not canonical_url:
            raise RuntimeError("geoweb_canonical_required")

        tracked_url: str | None = None
        trace_snapshot: dict | None = None
        if trace_enabled(cfg) and canonical_url:
            tracked_url, trace_snapshot = build_external_tracked_url(
                article=article,
                channel=channel,
                dist_id=int(dist.id),
                canonical_url=canonical_url,
            )

        publish_kwargs = {
            "canonical_url": canonical_url,
            "tracked_url": tracked_url,
            "dist_id": int(dist.id),
        }
        if channel.channel_type == "geoflow_agent":
            result = await publish_geoflow_agent(channel, article, **publish_kwargs)
        elif channel.channel_type == "wordpress_rest":
            result = await publish_wordpress(channel, article, **publish_kwargs)
        elif channel.channel_type == "generic_http_api":
            result = await publish_generic_http(channel, article, **publish_kwargs)
        else:
            dist.status = "skipped"
            dist.error_message = f"unsupported_channel:{channel.channel_type}"
            return

        dist.status = "published"
        dist.canonical_url = canonical_url
        dist.tracked_url = tracked_url or canonical_url
        dist.trace_params_json = trace_snapshot
        dist.remote_url = tracked_url or result.get("url") or canonical_url
        dist.remote_id = result.get("remote_id")

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
        channels = sort_channels_for_distribution(channels)
        if not channels:
            logger.info("distribution_skipped_no_channels article_id=%s", article_id)
            return

        session_canonical: str | None = await self._resolve_canonical_url(article, None)
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
            if existing and existing.status in _SUCCESS_STATUSES:
                if is_geoweb_channel(channel.channel_type):
                    session_canonical = session_canonical or (existing.canonical_url or existing.remote_url)
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
                if is_geoweb_channel(channel.channel_type):
                    url = await self._publish_geoweb_channel(article, channel, dist)
                    if url:
                        session_canonical = url
                    published_any = True
                elif is_external_channel(channel.channel_type):
                    canonical = await self._resolve_canonical_url(article, session_canonical)
                    await self._publish_external_channel(article, channel, dist, canonical_url=canonical)
                    published_any = True
                else:
                    dist.status = "skipped"
                    dist.error_message = f"unsupported_channel:{channel.channel_type}"

                logger.info(
                    "distribution_ok article_id=%s theme_id=%s channel=%s canonical=%s tracked=%s",
                    article_id,
                    article.theme_id,
                    channel.channel_type,
                    dist.canonical_url,
                    dist.tracked_url,
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
                logger.exception(
                    "distribution_failed article_id=%s channel=%s error=%s",
                    article_id,
                    channel.channel_type,
                    str(exc),
                )

        if published_any and article.theme_id:
            from app.services.geoeval.theme_service import mark_theme_published

            hub = None
            wiki_meta = article.wiki_meta if isinstance(article.wiki_meta, dict) else {}
            if wiki_meta.get("type") == "topic":
                hub = article.slug
            await mark_theme_published(self.db, int(article.theme_id), hub_slug=hub)
