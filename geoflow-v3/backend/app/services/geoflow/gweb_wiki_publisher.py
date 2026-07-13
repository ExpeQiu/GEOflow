"""Gweb Wiki 同步 — 契约对齐 GwebWikiPublisher。"""

import httpx

from app.core.config import get_settings
from app.models.article import Article

settings = get_settings()

WIKI_TYPE_PREFIX = {
    "concept": "concepts",
    "compare": "compare",
    "guide": "guides",
    "glossary": "glossary",
    "data": "data",
    "thread": "threads",
    "topic": "topics",
}


class GwebWikiPublisher:
    async def publish(self, article: Article) -> dict:
        if not settings.gweb_sync_enabled or not settings.gweb_base_url:
            return {"url": "", "slug": article.slug, "dry_run": True}

        meta = article.wiki_meta or {}
        wiki_type = meta.get("type") or "concept"
        route_prefix = WIKI_TYPE_PREFIX.get(wiki_type, "concepts")
        slug = meta.get("slug") or article.slug

        body = {
            "action": "upsert",
            "slug": slug,
            "type": wiki_type,
            "route_prefix": route_prefix,
            "frontmatter": {**meta, "slug": slug, "type": wiki_type},
            "body": article.content,
        }

        headers = {"Authorization": f"Bearer {settings.gweb_revalidate_secret}"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{settings.gweb_base_url.rstrip('/')}/api/wiki/sync", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            paths = data.get("revalidate_paths") or [f"/{route_prefix}/{slug}", "/wiki"]
            await client.post(
                f"{settings.gweb_base_url.rstrip('/')}/api/revalidate",
                json={"paths": paths},
                headers=headers,
            )

        return {"url": data.get("url", ""), "slug": slug}
