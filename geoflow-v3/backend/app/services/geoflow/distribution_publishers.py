"""WordPress / Generic HTTP / GeoFlow Agent 分发发布器。"""

import httpx

from app.core.logging import get_logger
from app.models.article import Article
from app.models.distribution import DistributionChannel

logger = get_logger("geoflow.distribution.publishers")


def _cfg(channel: DistributionChannel) -> dict:
    return channel.config_json if isinstance(channel.config_json, dict) else {}


async def publish_geoflow_agent(channel: DistributionChannel, article: Article) -> dict:
    config = _cfg(channel)
    endpoint = config.get("endpoint_url") or config.get("publish_url")
    if not endpoint:
        raise RuntimeError("missing_agent_endpoint")
    payload = {
        "title": article.title,
        "content": article.content or "",
        "slug": article.slug,
        "content_format": article.content_format or "article",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(endpoint, json=payload)
    if resp.status_code >= 400:
        raise RuntimeError(f"geoflow_agent_http_{resp.status_code}")
    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    logger.info("geoflow_agent_published", article_id=article.id)
    return {"url": data.get("url") or endpoint, "remote_id": str(data.get("id", article.slug))}


async def publish_wordpress(channel: DistributionChannel, article: Article) -> dict:
    config = _cfg(channel)
    endpoint = config.get("api_url") or config.get("endpoint_url") or f"https://{config.get('domain', '')}/wp-json/wp/v2/posts"
    payload = {
        "title": article.title,
        "content": article.content or "",
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
    logger.info("wordpress_published", article_id=article.id, remote_id=data.get("id"))
    return {"url": data.get("link"), "remote_id": str(data.get("id", ""))}


async def publish_generic_http(channel: DistributionChannel, article: Article) -> dict:
    config = _cfg(channel)
    base = config.get("endpoint_url") or config.get("publish_url") or ""
    path = config.get("generic_publish_path", "/articles")
    method = (config.get("generic_publish_method") or "POST").upper()
    endpoint = f"{base.rstrip('/')}{path}" if base else ""
    if not endpoint:
        raise RuntimeError("missing_publish_url")
    payload = {"title": article.title, "content": article.content or "", "slug": article.slug}
    headers: dict[str, str] = {}
    auth_type = config.get("generic_auth_type", "none")
    secret = config.get("generic_secret", "")
    if auth_type == "bearer" and secret:
        headers["Authorization"] = f"Bearer {secret}"
    async with httpx.AsyncClient(timeout=int(config.get("generic_timeout_seconds", 30))) as client:
        resp = await client.request(method, endpoint, json=payload, headers=headers)
    if resp.status_code >= 400:
        raise RuntimeError(f"generic_http_{resp.status_code}")
    logger.info("generic_http_published", article_id=article.id)
    return {"url": endpoint, "remote_id": article.slug}
