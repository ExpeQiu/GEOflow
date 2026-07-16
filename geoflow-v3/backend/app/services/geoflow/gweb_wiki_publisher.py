"""Gweb Wiki 同步 — 契约对齐 GwebWikiPublisher，注入溯源字段。"""

from __future__ import annotations

import hashlib
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.article import Article
from app.models.distribution import DistributionChannel
from app.services.geoflow.wiki_mdx_assembler import WikiMdxAssembler

settings = get_settings()
logger = get_logger("geoflow.publishers.gweb")

WIKI_TYPE_PREFIX = {
    "concept": "concepts",
    "compare": "compare",
    "guide": "guides",
    "glossary": "glossary",
    "data": "data",
    "thread": "threads",
    "topic": "topics",
}


def _cfg(channel: DistributionChannel | None) -> dict[str, Any]:
    if channel is None:
        return {}
    return channel.config_json if isinstance(channel.config_json, dict) else {}


def _content_hash(content: str) -> str:
    """计算内容指纹，便于 GWEB 侧判断是否真正变化。"""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _resolve_geo_task_id(article: Article) -> str:
    """优先溯源到 Task；无绑定任务时回退 Article.id。"""
    if article.task_id:
        return str(article.task_id)
    return str(article.id)


class GwebWikiPublisher:
    async def publish(
        self,
        article: Article,
        channel: DistributionChannel | None = None,
    ) -> dict:
        config = _cfg(channel)
        base_url = (
            config.get("gweb_base_url")
            or config.get("endpoint_url")
            or settings.gweb_base_url
        )
        secret = config.get("gweb_sync_secret") or settings.gweb_revalidate_secret
        timeout = int(config.get("gweb_timeout_seconds") or 30)
        sync_enabled = settings.gweb_sync_enabled or bool(config.get("gweb_base_url"))

        if not sync_enabled or not base_url:
            logger.info(
                "gweb_wiki_dry_run",
                article_id=article.id,
                reason="sync_disabled_or_missing_base_url",
            )
            return {"url": "", "slug": article.slug, "dry_run": True}

        if not secret:
            raise RuntimeError("gweb_publisher_missing_config: gweb_sync_secret 未配置")

        meta = article.wiki_meta or {}
        wiki_type = (
            meta.get("wiki_page_type")
            or meta.get("type")
            or "concept"
        )
        route_prefix = (
            config.get("route_prefix")
            or meta.get("route_prefix")
            or WIKI_TYPE_PREFIX.get(str(wiki_type), "concepts")
        )
        slug = meta.get("slug") or article.slug

        frontmatter = meta.get("frontmatter") if isinstance(meta.get("frontmatter"), dict) else {}
        # 扁平 wiki_meta 也作为 frontmatter 来源（排除内部组装字段）
        skip_keys = {"mdx", "frontmatter", "content_hash", "route_prefix"}
        flat_meta = {k: v for k, v in meta.items() if k not in skip_keys}
        merged_frontmatter = {**flat_meta, **frontmatter, "slug": slug, "type": wiki_type}

        mdx_content = meta.get("mdx") if isinstance(meta.get("mdx"), str) else ""
        if not mdx_content.strip():
            mdx_content = WikiMdxAssembler.assemble(article)

        content_for_hash = mdx_content or article.content or ""
        content_hash = meta.get("content_hash") or _content_hash(content_for_hash)
        if isinstance(content_hash, str) and content_hash.startswith("sha256:"):
            content_hash = content_hash.removeprefix("sha256:")[:16]
        geo_task_id = _resolve_geo_task_id(article)

        # 回写 wiki_meta，便于后续分发跳过未变内容
        updated_meta = {
            **meta,
            "content_hash": content_hash,
            "geo_task_id": geo_task_id,
            "route_prefix": route_prefix,
            "wiki_page_type": wiki_type,
        }
        article.wiki_meta = updated_meta

        payload = {
            "action": "upsert",
            "slug": slug,
            "type": wiki_type,
            "route_prefix": route_prefix,
            "geo_task_id": geo_task_id,
            "geo_content_hash": content_hash,
            "frontmatter": merged_frontmatter,
            "body": article.content or "",
            "mdx": mdx_content,
        }

        endpoint = f"{base_url.rstrip('/')}/api/wiki/sync"
        headers = {"Authorization": f"Bearer {secret}"}

        async with httpx.AsyncClient(timeout=float(timeout)) as client:
            resp = await client.post(endpoint, json=payload, headers=headers)
            if resp.status_code >= 400:
                raise RuntimeError(f"gweb_wiki_http_{resp.status_code}: {resp.text[:200]}")
            data = resp.json()

            paths = data.get("revalidate_paths") or [f"/{route_prefix}/{slug}", "/wiki"]
            try:
                await client.post(
                    f"{base_url.rstrip('/')}/api/revalidate",
                    json={"paths": paths},
                    headers=headers,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "gweb_revalidate_failed",
                    article_id=article.id,
                    error=str(exc),
                )

            remote_url = data.get("url") or f"{base_url.rstrip('/')}/{route_prefix}/{slug}"
            if remote_url.startswith("/"):
                remote_url = f"{base_url.rstrip('/')}{remote_url}"

            await self._maybe_ai_submit(client, base_url, secret, [remote_url])

        logger.info(
            "gweb_wiki_published",
            article_id=article.id,
            slug=slug,
            geo_task_id=geo_task_id,
            geo_content_hash=content_hash,
            remote_url=remote_url,
        )

        return {
            "url": remote_url,
            "slug": slug,
            "remote_id": slug,
            "geo_task_id": geo_task_id,
            "geo_content_hash": content_hash,
        }

    async def _maybe_ai_submit(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        secret: str,
        urls: list[str],
    ) -> None:
        """发布成功后可选推送到 GWEB /api/ai-submit（密钥由 GWEB 环境变量持有）。"""
        if not urls:
            return
        try:
            resp = await client.post(
                f"{base_url.rstrip('/')}/api/ai-submit",
                json={"urls": urls},
                headers={"Authorization": f"Bearer {secret}"},
                timeout=30.0,
            )
            if resp.status_code >= 400:
                logger.warning(
                    "gweb_ai_submit_http_error",
                    status=resp.status_code,
                    body=resp.text[:200],
                )
                return
            logger.info("gweb_ai_submit_ok", urls=urls, response=resp.json())
        except Exception as exc:  # noqa: BLE001
            logger.warning("gweb_ai_submit_failed", error=str(exc), urls=urls)
