"""WordPress / Generic HTTP / GeoFlow Agent / GEOweb 分发发布器。"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.logging import get_logger
from app.models.article import Article
from app.models.distribution import DistributionChannel
from app.services.geoflow.distribution_trace import trace_enabled
from app.services.geoflow.geoweb_publisher import GeowebPublisher

logger = get_logger("geoflow.distribution.publishers")


def _cfg(channel: DistributionChannel) -> dict:
    return channel.config_json if isinstance(channel.config_json, dict) else {}


def _external_link_payload(
    article: Article,
    *,
    canonical_url: str | None,
    tracked_url: str | None,
) -> dict[str, Any]:
    link = (tracked_url or canonical_url or "").strip()
    summary = (article.content or "")[:280].strip()
    return {
        "title": article.title,
        "content": article.content or "",
        "slug": article.slug,
        "content_format": article.content_format or "article",
        "link": link,
        "canonical_url": canonical_url or "",
        "tracked_url": tracked_url or link,
        "summary": summary,
    }


def _wordpress_body(article: Article, *, link: str, trace_mode: bool) -> str:
    if not trace_mode or not link:
        return article.content or ""
    summary = (article.content or "")[:400].strip()
    return (
        f"<p>{summary}</p>\n"
        f'<p><a href="{link}" rel="noopener noreferrer">阅读原文</a></p>'
        if summary
        else f'<p><a href="{link}" rel="noopener noreferrer">阅读原文</a></p>'
    )


async def publish_geoweb(channel: DistributionChannel, article: Article) -> dict:
    """主路径：委托 GeowebPublisher → GEOweb /api/geoflow/sync。"""
    return await GeowebPublisher().publish(article, channel=channel)


async def publish_geoflow_agent(
    channel: DistributionChannel,
    article: Article,
    *,
    canonical_url: str | None = None,
    tracked_url: str | None = None,
    dist_id: int | None = None,
) -> dict:
    config = _cfg(channel)
    endpoint = config.get("endpoint_url") or config.get("publish_url")
    if not endpoint:
        raise RuntimeError("missing_agent_endpoint")
    use_trace = trace_enabled(config)
    payload = _external_link_payload(
        article,
        canonical_url=canonical_url,
        tracked_url=tracked_url if use_trace else canonical_url,
    )
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(endpoint, json=payload)
    if resp.status_code >= 400:
        raise RuntimeError(f"geoflow_agent_http_{resp.status_code}")
    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    out_url = payload["tracked_url"] or data.get("url") or endpoint
    logger.info(
        "geoflow_agent_published article_id=%s dist_id=%s trace=%s",
        article.id,
        dist_id,
        use_trace,
    )
    return {"url": out_url, "remote_id": str(data.get("id", article.slug))}


async def publish_wordpress(
    channel: DistributionChannel,
    article: Article,
    *,
    canonical_url: str | None = None,
    tracked_url: str | None = None,
    dist_id: int | None = None,
) -> dict:
    config = _cfg(channel)
    endpoint = config.get("api_url") or config.get("endpoint_url") or f"https://{config.get('domain', '')}/wp-json/wp/v2/posts"
    use_trace = trace_enabled(config)
    link = (tracked_url if use_trace else canonical_url) or ""
    payload = {
        "title": article.title,
        "content": _wordpress_body(article, link=link, trace_mode=use_trace and bool(link)),
        "status": config.get("wordpress_post_status", "draft"),
    }
    auth = None
    user = config.get("wordpress_username")
    pwd = config.get("wordpress_application_password")
    if user and pwd:
        auth = (user, pwd)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(endpoint, json=payload, auth=auth)
    if resp.status_code >= 400:
        raise RuntimeError(f"wordpress_http_{resp.status_code}")
    data = resp.json()
    remote_link = data.get("link") or link or canonical_url
    logger.info(
        "wordpress_published article_id=%s dist_id=%s trace=%s",
        article.id,
        dist_id,
        use_trace,
    )
    return {"url": remote_link, "remote_id": str(data.get("id", ""))}


async def publish_generic_http(
    channel: DistributionChannel,
    article: Article,
    *,
    canonical_url: str | None = None,
    tracked_url: str | None = None,
    dist_id: int | None = None,
) -> dict:
    config = _cfg(channel)
    base = config.get("endpoint_url") or config.get("publish_url") or ""
    path = config.get("generic_publish_path", "/articles")
    method = (config.get("generic_publish_method") or "POST").upper()
    endpoint = f"{base.rstrip('/')}{path}" if base else ""
    if not endpoint:
        raise RuntimeError("missing_publish_url")
    use_trace = trace_enabled(config)
    payload = _external_link_payload(
        article,
        canonical_url=canonical_url,
        tracked_url=tracked_url if use_trace else canonical_url,
    )
    headers: dict[str, str] = {}
    auth_type = config.get("generic_auth_type", "none")
    secret = config.get("generic_secret", "")
    if auth_type == "bearer" and secret:
        headers["Authorization"] = f"Bearer {secret}"
    async with httpx.AsyncClient(timeout=int(config.get("generic_timeout_seconds", 30))) as client:
        resp = await client.request(method, endpoint, json=payload, headers=headers)
    if resp.status_code >= 400:
        raise RuntimeError(f"generic_http_{resp.status_code}")
    out_url = payload["tracked_url"] or endpoint
    logger.info(
        "generic_http_published article_id=%s dist_id=%s trace=%s",
        article.id,
        dist_id,
        use_trace,
    )
    return {"url": out_url, "remote_id": article.slug}
