"""GEOweb 内容同步 — POST /api/geoflow/sync，默认落到 /articles。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.article import Article
from app.models.distribution import DistributionChannel
from app.services.geoflow.wiki_types import GEOWEB_PAGE_TYPES, route_prefix_for_type

settings = get_settings()
logger = get_logger("geoflow.publishers.geoweb")


def _cfg(channel: DistributionChannel | None) -> dict[str, Any]:
    if channel is None:
        return {}
    return channel.config_json if isinstance(channel.config_json, dict) else {}


def _resolve_geo_task_id(article: Article) -> str:
    if article.task_id:
        return str(article.task_id)
    return str(article.id)


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(x).strip() for x in value if str(x).strip()]


def _as_faq(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    out: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        q = str(item.get("q") or item.get("question") or "").strip()
        a = str(item.get("a") or item.get("answer") or "").strip()
        if q and a:
            out.append({"q": q, "a": a})
    return out


def _resolve_page_type(article: Article, config: dict[str, Any]) -> str:
    """普通文章默认 article；Wiki MDX 按 wiki_page_type；渠道可强制覆盖。"""
    forced = str(config.get("default_page_type") or config.get("page_type") or "").strip()
    if forced in GEOWEB_PAGE_TYPES:
        return forced

    meta = article.wiki_meta if isinstance(article.wiki_meta, dict) else {}
    if (article.content_format or "article") == "wiki_mdx":
        wiki_type = str(
            meta.get("wiki_page_type") or meta.get("type") or "concept"
        ).strip()
        return wiki_type if wiki_type in GEOWEB_PAGE_TYPES else "concept"

    return "article"


class GeowebPublisher:
    """把 GEOFlow Article 推到 GEOweb `/api/geoflow/sync`。"""

    async def publish(
        self,
        article: Article,
        channel: DistributionChannel | None = None,
    ) -> dict:
        config = _cfg(channel)
        base_url = (
            config.get("geoweb_base_url")
            or config.get("endpoint_url")
            or settings.geoweb_base_url
        )
        secret = config.get("geoweb_sync_token") or settings.geoweb_sync_token
        timeout = int(config.get("geoweb_timeout_seconds") or 30)
        sync_enabled = settings.geoweb_sync_enabled or bool(
            config.get("geoweb_base_url") or config.get("endpoint_url")
        )

        if not sync_enabled or not base_url:
            logger.info(
                "geoweb_dry_run",
                article_id=article.id,
                reason="sync_disabled_or_missing_base_url",
            )
            return {"url": "", "slug": article.slug, "dry_run": True}

        if not secret:
            raise RuntimeError("geoweb_publisher_missing_config: geoweb_sync_token 未配置")

        meta = article.wiki_meta if isinstance(article.wiki_meta, dict) else {}
        frontmatter = meta.get("frontmatter") if isinstance(meta.get("frontmatter"), dict) else {}
        page_type = _resolve_page_type(article, config)
        slug = str(meta.get("slug") or article.slug).strip() or article.slug
        geo_task_id = _resolve_geo_task_id(article)

        body = (article.content or "").strip()
        if not body and isinstance(meta.get("mdx"), str):
            # Wiki 组装产物：去掉 frontmatter 后仍可作 body 兜底
            mdx = meta["mdx"]
            if mdx.startswith("---"):
                parts = mdx.split("---", 2)
                body = parts[2].strip() if len(parts) >= 3 else mdx
            else:
                body = mdx.strip()
        if not body:
            raise RuntimeError("geoweb_publisher_empty_body")

        quick_answer = (
            str(frontmatter.get("quick_answer") or meta.get("quick_answer") or "").strip()
            or (article.excerpt or "").strip()
            or None
        )
        core_takeaway = (
            str(frontmatter.get("core_takeaway") or meta.get("core_takeaway") or "").strip()
            or quick_answer
        )
        target_query = (
            str(frontmatter.get("target_query") or meta.get("target_query") or "").strip()
            or (article.original_keyword or "").strip()
            or None
        )
        domain = str(frontmatter.get("domain") or meta.get("domain") or "").strip() or None
        related = _as_str_list(frontmatter.get("related") or meta.get("related"))
        faq = _as_faq(frontmatter.get("faq") or meta.get("faq"))
        tags = _as_str_list(frontmatter.get("tags") or meta.get("tags"))
        if not tags and article.keywords:
            tags = [k.strip() for k in str(article.keywords).split(",") if k.strip()]

        last_updated = (
            str(frontmatter.get("last_updated") or meta.get("last_updated") or "").strip()
            or datetime.now(UTC).date().isoformat()
        )

        payload: dict[str, Any] = {
            "slug": slug,
            "type": page_type,
            "title": article.title,
            "body": body,
            "geo_publish": True,
            "geo_flow_task": geo_task_id,
            "last_updated": last_updated,
            "schema_type": str(
                frontmatter.get("schema_type") or meta.get("schema_type") or "TechArticle"
            ),
        }
        if article.theme_id:
            payload["geo_theme_id"] = str(article.theme_id)
        if domain:
            payload["domain"] = domain
        if quick_answer:
            payload["quick_answer"] = quick_answer
        if core_takeaway:
            payload["core_takeaway"] = core_takeaway
        if target_query:
            payload["target_query"] = target_query
        if related:
            payload["related"] = related
        if faq:
            payload["faq"] = faq
        if tags:
            payload["tags"] = tags

        endpoint = f"{base_url.rstrip('/')}/api/geoflow/sync"
        headers = {"Authorization": f"Bearer {secret}"}

        async with httpx.AsyncClient(timeout=float(timeout)) as client:
            resp = await client.post(endpoint, json=payload, headers=headers)
            if resp.status_code >= 400:
                raise RuntimeError(f"geoweb_http_{resp.status_code}: {resp.text[:200]}")
            data = resp.json() if resp.content else {}

        remote_url = data.get("url") or f"{base_url.rstrip('/')}/{_route_prefix(page_type)}/{slug}"
        geo_content_hash = data.get("geo_content_hash")

        # 回写 wiki_meta，便于溯源与幂等
        article.wiki_meta = {
            **meta,
            "wiki_page_type": page_type,
            "type": page_type,
            "slug": slug,
            "theme_id": article.theme_id,
            "geo_theme_id": str(article.theme_id) if article.theme_id else None,
            "geo_content_hash": geo_content_hash,
            "geo_task_id": geo_task_id,
            "geoweb_url": remote_url,
        }
        logger.info(
            "geoweb_published article_id=%s theme_id=%s type=%s slug=%s geo_flow_task=%s",
            article.id,
            article.theme_id,
            page_type,
            slug,
            geo_task_id,
        )
        return {
            "url": remote_url,
            "slug": slug,
            "remote_id": slug,
            "geo_task_id": geo_task_id,
            "geo_content_hash": geo_content_hash,
            "type": page_type,
        }


def _route_prefix(page_type: str) -> str:
    return route_prefix_for_type(page_type)
