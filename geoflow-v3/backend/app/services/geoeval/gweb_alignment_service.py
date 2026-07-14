"""Gweb pages.json 回流 — 目录对齐率（Step 5 信源覆盖）。"""

from __future__ import annotations

import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.article import Article
from app.models.tech_ip import TechIpAsset

logger = logging.getLogger(__name__)


def _normalize_slug(slug: str) -> str:
    s = (slug or "").strip().strip("/")
    if "/" in s:
        s = s.rsplit("/", 1)[-1]
    return s.lower()


async def fetch_gweb_pages(db: AsyncSession | None = None) -> dict:
    settings = get_settings()
    base = (settings.gweb_base_url or "").rstrip("/")
    if not base:
        return {"status": "skipped", "reason": "gweb_base_url_missing", "pages": []}

    url = f"{base}/api/pages.json"
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url)
        if resp.status_code >= 400:
            logger.warning("gweb_pages_fetch_failed status=%s url=%s", resp.status_code, url)
            return {"status": "error", "reason": f"http_{resp.status_code}", "pages": [], "url": url}
        data = resp.json()
        pages = data.get("pages") if isinstance(data, dict) else []
        if not isinstance(pages, list):
            pages = []
        logger.info("gweb_pages_fetched count=%s url=%s", len(pages), url)
        return {
            "status": "ok",
            "url": url,
            "generated_at": data.get("generatedAt") if isinstance(data, dict) else None,
            "count": len(pages),
            "pages": pages,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("gweb_pages_fetch_exception url=%s error=%s", url, exc)
        return {"status": "error", "reason": str(exc)[:200], "pages": [], "url": url}


async def compute_gweb_alignment(db: AsyncSession) -> dict:
    fetched = await fetch_gweb_pages(db)
    gweb_slugs: set[str] = set()
    page_items: list[dict] = []
    for p in fetched.get("pages") or []:
        if not isinstance(p, dict):
            continue
        slug = _normalize_slug(str(p.get("slug") or ""))
        if not slug:
            continue
        gweb_slugs.add(slug)
        page_items.append(
            {
                "slug": slug,
                "title": p.get("title"),
                "type": p.get("type"),
                "url": p.get("url"),
                "last_updated": p.get("lastUpdated"),
            }
        )

    asset_slugs: set[str] = set()
    try:
        rows = (
            await db.execute(
                select(TechIpAsset.wiki_slug).where(
                    TechIpAsset.wiki_slug.is_not(None),
                    TechIpAsset.status == "active",
                )
            )
        ).all()
        for (slug,) in rows:
            ns = _normalize_slug(str(slug))
            if ns:
                asset_slugs.add(ns)
    except Exception:
        logger.debug("tech_ip_slug_load_skipped")

    wiki_article_slugs: set[str] = set()
    try:
        rows = (
            await db.execute(
                select(Article.slug).where(
                    Article.content_format == "wiki_mdx",
                    Article.deleted_at.is_(None),
                    Article.status == "published",
                    Article.slug.is_not(None),
                )
            )
        ).all()
        for (slug,) in rows:
            ns = _normalize_slug(str(slug))
            if ns:
                wiki_article_slugs.add(ns)
    except Exception:
        logger.debug("wiki_article_slug_load_skipped")

    local_slugs = asset_slugs | wiki_article_slugs
    matched = sorted(gweb_slugs & local_slugs)
    only_gweb = sorted(gweb_slugs - local_slugs)
    only_local = sorted(local_slugs - gweb_slugs)
    denom = len(gweb_slugs) or 1
    alignment_pct = round(len(matched) / denom * 100, 1) if gweb_slugs else 0.0

    result = {
        "status": fetched.get("status", "ok"),
        "source_url": fetched.get("url"),
        "generated_at": fetched.get("generated_at"),
        "gweb_page_count": len(gweb_slugs),
        "asset_slug_count": len(asset_slugs),
        "published_wiki_slug_count": len(wiki_article_slugs),
        "matched_count": len(matched),
        "only_gweb_count": len(only_gweb),
        "only_local_count": len(only_local),
        "alignment_pct": alignment_pct,
        "matched_sample": matched[:20],
        "only_gweb_sample": only_gweb[:20],
        "only_local_sample": only_local[:20],
        "fetch_reason": fetched.get("reason"),
    }
    logger.info(
        "gweb_alignment_computed alignment_pct=%s gweb=%s matched=%s status=%s",
        alignment_pct,
        len(gweb_slugs),
        len(matched),
        result["status"],
    )
    return result
