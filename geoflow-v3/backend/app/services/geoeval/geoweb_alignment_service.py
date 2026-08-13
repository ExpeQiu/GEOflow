"""GEOweb pages.json 回流 — 目录对齐率（信源覆盖）。"""

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


async def fetch_geoweb_pages(db: AsyncSession | None = None) -> dict:
    settings = get_settings()
    base = (settings.geoweb_base_url or "").rstrip("/")
    if not base:
        return {"status": "skipped", "reason": "geoweb_base_url_missing", "pages": []}

    url = f"{base}/api/pages.json"
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url)
        if resp.status_code >= 400:
            logger.warning("geoweb_pages_fetch_failed status=%s url=%s", resp.status_code, url)
            return {"status": "error", "reason": f"http_{resp.status_code}", "pages": [], "url": url}
        data = resp.json()
        if isinstance(data, list):
            pages = data
            generated_at = None
        elif isinstance(data, dict):
            pages = data.get("pages") if isinstance(data.get("pages"), list) else []
            generated_at = data.get("generatedAt") or data.get("generated_at")
        else:
            pages = []
            generated_at = None
        logger.info("geoweb_pages_fetched count=%s url=%s", len(pages), url)
        return {
            "status": "ok",
            "url": url,
            "generated_at": generated_at,
            "count": len(pages),
            "pages": pages,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("geoweb_pages_fetch_exception url=%s error=%s", url, exc)
        return {"status": "error", "reason": str(exc)[:200], "pages": [], "url": url}


async def compute_geoweb_alignment(db: AsyncSession) -> dict:
    """计算 GEOFlow 本地已发布内容与 GEOweb 目录对齐率。"""
    fetched = await fetch_geoweb_pages(db)
    remote_slugs: set[str] = set()
    for p in fetched.get("pages") or []:
        if not isinstance(p, dict):
            continue
        slug = _normalize_slug(str(p.get("slug") or ""))
        if slug:
            remote_slugs.add(slug)

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

    published_slugs: set[str] = set()
    try:
        rows = (
            await db.execute(
                select(Article.slug).where(
                    Article.deleted_at.is_(None),
                    Article.status == "published",
                    Article.slug.is_not(None),
                )
            )
        ).all()
        for (slug,) in rows:
            ns = _normalize_slug(str(slug))
            if ns:
                published_slugs.add(ns)
    except Exception:
        logger.debug("published_slug_load_skipped")

    local_slugs = asset_slugs | published_slugs
    matched = sorted(remote_slugs & local_slugs)
    only_remote = sorted(remote_slugs - local_slugs)
    only_local = sorted(local_slugs - remote_slugs)
    alignment_pct = round(len(matched) / (len(remote_slugs) or 1) * 100, 1) if remote_slugs else 0.0

    result = {
        "status": fetched.get("status", "ok"),
        "source_url": fetched.get("url"),
        "generated_at": fetched.get("generated_at"),
        "geoweb_page_count": len(remote_slugs),
        "asset_slug_count": len(asset_slugs),
        "published_slug_count": len(published_slugs),
        "matched_count": len(matched),
        "only_geoweb_count": len(only_remote),
        "only_local_count": len(only_local),
        "alignment_pct": alignment_pct,
        "matched_sample": matched[:20],
        "only_geoweb_sample": only_remote[:20],
        "only_local_sample": only_local[:20],
        "fetch_reason": fetched.get("reason"),
        "target": "geoweb",
    }
    logger.info(
        "geoweb_alignment_computed alignment_pct=%s remote=%s matched=%s status=%s",
        alignment_pct,
        len(remote_slugs),
        len(matched),
        result["status"],
    )
    return result


# 兼容旧函数名（报告/路由迁移期）
async def compute_gweb_alignment(db: AsyncSession) -> dict:
    return await compute_geoweb_alignment(db)


async def fetch_gweb_pages(db: AsyncSession | None = None) -> dict:
    return await fetch_geoweb_pages(db)
