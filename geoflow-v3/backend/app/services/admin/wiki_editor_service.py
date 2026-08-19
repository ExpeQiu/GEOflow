"""GEOweb Wiki 轻量编辑台 — Admin BFF（ADR-011 Wave 1）。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.article import Article
from app.models.material import Author, Category
from app.services.admin.wiki_editor_schema import (
    WikiPageBody,
    as_faq,
    as_str_list,
    build_wiki_meta,
    meta_get,
    validate_wiki_slug,
    validate_wiki_type,
)
from app.services.geoflow.geoweb_publisher import GeowebPublisher
from app.services.geoflow.wiki_types import GEOWEB_PAGE_TYPES, is_smoke_slug, wiki_preview_url

logger = get_logger("geoflow.admin.wiki")

WIKI_FORMAT = "wiki_mdx"
DOMAINS = ("adas", "battery", "edrive", "cockpit", "safety")
SCHEMA_TYPES = ("TechArticle", "FAQPage", "HowTo")


def _meta_dict(article: Article) -> dict[str, Any]:
    return article.wiki_meta if isinstance(article.wiki_meta, dict) else {}


def resolve_wiki_page_type(article: Article) -> str:
    meta = _meta_dict(article)
    raw = str(meta_get(meta, "wiki_page_type") or meta_get(meta, "type") or "concept").strip()
    return raw if raw in GEOWEB_PAGE_TYPES else "concept"


def _serialize_wiki_page(article: Article, geoweb_base_url: str) -> dict[str, Any]:
    meta = _meta_dict(article)
    page_type = resolve_wiki_page_type(article)
    slug = str(meta_get(meta, "slug") or article.slug)
    geoweb_url = str(meta_get(meta, "geoweb_url") or "") or None
    preview = geoweb_url or wiki_preview_url(geoweb_base_url, page_type, slug)
    theme_raw = meta_get(meta, "geo_theme_id")
    if theme_raw is None and article.theme_id:
        theme_raw = str(article.theme_id)
    return {
        "id": article.id,
        "title": article.title,
        "slug": slug,
        "status": article.status,
        "review_status": article.review_status,
        "content_format": article.content_format or WIKI_FORMAT,
        "wiki_page_type": page_type,
        "domain": str(meta_get(meta, "domain") or "") or None,
        "body": article.content or "",
        "quick_answer": str(meta_get(meta, "quick_answer") or article.excerpt or "") or None,
        "core_takeaway": str(meta_get(meta, "core_takeaway") or "") or None,
        "target_query": str(meta_get(meta, "target_query") or article.original_keyword or "") or None,
        "related": as_str_list(meta_get(meta, "related")),
        "faq": as_faq(meta_get(meta, "faq")),
        "schema_type": str(meta_get(meta, "schema_type") or "TechArticle"),
        "geo_theme_id": str(theme_raw) if theme_raw else None,
        "tags": as_str_list(meta_get(meta, "tags")),
        "geoweb_url": geoweb_url,
        "geo_content_hash": str(meta_get(meta, "geo_content_hash") or "") or None,
        "preview_url": preview,
        "synced": bool(meta_get(meta, "geo_content_hash") or geoweb_url),
        "task_id": article.task_id,
        "theme_id": article.theme_id,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "created_at": article.created_at.isoformat() if article.created_at else None,
        "updated_at": article.updated_at.isoformat() if article.updated_at else None,
    }


def _wiki_query():
    return select(Article).where(
        Article.deleted_at.is_(None),
        Article.content_format == WIKI_FORMAT,
    )


async def _require_wiki_article(db: AsyncSession, article_id: int) -> Article:
    article = await db.get(Article, article_id)
    if article is None or article.deleted_at:
        raise HTTPException(status_code=404, detail="wiki_page_not_found")
    if (article.content_format or "article") != WIKI_FORMAT:
        raise HTTPException(status_code=404, detail="wiki_page_not_found")
    return article


async def _ensure_unique_slug(db: AsyncSession, slug: str, article_id: int | None) -> str:
    query = select(Article.id).where(Article.slug == slug, Article.deleted_at.is_(None)).limit(1)
    if article_id:
        query = query.where(Article.id != article_id)
    existing = (await db.execute(query)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=422, detail="wiki_slug_taken")
    return slug


async def _default_category_author(db: AsyncSession) -> tuple[int, int]:
    category = (
        await db.execute(select(Category).order_by(Category.sort_order, Category.id).limit(1))
    ).scalar_one_or_none()
    author = (await db.execute(select(Author).order_by(Author.id).limit(1))).scalar_one_or_none()
    if category is None or author is None:
        raise HTTPException(status_code=422, detail="wiki_missing_category_or_author")
    return category.id, author.id


def _parse_theme_id(geo_theme_id: str | None) -> int | None:
    raw = (geo_theme_id or "").strip()
    if raw.isdigit():
        return int(raw)
    return None


async def build_wiki_panel(
    db: AsyncSession,
    page_type: str | None = None,
    q: str | None = None,
    include_smoke: bool = False,
) -> dict[str, Any]:
    settings = get_settings()
    geoweb_base_url = (settings.geoweb_base_url or "").rstrip("/")

    query = _wiki_query().order_by(Article.id.desc()).limit(200)
    if page_type:
        validate_wiki_type(page_type)
    articles = (await db.execute(query)).scalars().all()

    items: list[dict[str, Any]] = []
    type_counts: dict[str, int] = {t: 0 for t in sorted(GEOWEB_PAGE_TYPES)}
    smoke_hidden = 0
    needle = (q or "").strip().lower()

    for article in articles:
        resolved_type = resolve_wiki_page_type(article)
        type_counts[resolved_type] = type_counts.get(resolved_type, 0) + 1
        slug = str(meta_get(_meta_dict(article), "slug") or article.slug)
        if not include_smoke and is_smoke_slug(slug):
            smoke_hidden += 1
            continue
        if page_type and resolved_type != page_type:
            continue
        if needle and needle not in (article.title or "").lower() and needle not in slug.lower():
            continue
        items.append(_serialize_wiki_page(article, geoweb_base_url))

    total = int(
        await db.scalar(
            select(func.count()).select_from(Article).where(
                Article.deleted_at.is_(None),
                Article.content_format == WIKI_FORMAT,
            )
        )
        or 0
    )
    synced = sum(1 for item in items if item["synced"])
    return {
        "pages": items,
        "stats": {
            "total": total,
            "visible": len(items),
            "synced": synced,
            "smoke_hidden": smoke_hidden,
        },
        "type_counts": type_counts,
        "types": sorted(GEOWEB_PAGE_TYPES),
        "domains": list(DOMAINS),
        "schema_types": list(SCHEMA_TYPES),
        "geoweb_base_url": geoweb_base_url,
        "geoweb_sync_enabled": bool(settings.geoweb_sync_enabled),
    }


async def build_wiki_detail(db: AsyncSession, article_id: int) -> dict[str, Any]:
    article = await _require_wiki_article(db, article_id)
    await db.refresh(article)
    settings = get_settings()
    geoweb_base_url = (settings.geoweb_base_url or "").rstrip("/")
    return {
        "page": _serialize_wiki_page(article, geoweb_base_url),
        "types": sorted(GEOWEB_PAGE_TYPES),
        "domains": list(DOMAINS),
        "schema_types": list(SCHEMA_TYPES),
        "geoweb_base_url": geoweb_base_url,
        "geoweb_sync_enabled": bool(settings.geoweb_sync_enabled),
    }


async def create_wiki_page(db: AsyncSession, body: WikiPageBody) -> dict[str, Any]:
    page_type = validate_wiki_type(body.wiki_page_type)
    slug = await _ensure_unique_slug(db, validate_wiki_slug(body.slug), None)
    if is_smoke_slug(slug):
        raise HTTPException(status_code=422, detail="wiki_slug_reserved_smoke")
    category_id, author_id = await _default_category_author(db)
    excerpt = (body.quick_answer or body.core_takeaway or "").strip()
    article = Article(
        title=body.title.strip(),
        slug=slug,
        content=body.body,
        excerpt=excerpt,
        original_keyword=(body.target_query or "").strip(),
        keywords=",".join(t.strip() for t in body.tags if t.strip()),
        category_id=category_id,
        author_id=author_id,
        status="draft",
        review_status="pending",
        eval_status="skipped",
        content_format=WIKI_FORMAT,
        wiki_meta=build_wiki_meta(None, body, page_type, slug),
        theme_id=_parse_theme_id(body.geo_theme_id),
        is_ai_generated=0,
    )
    db.add(article)
    await db.flush()
    logger.info(
        "wiki_page_created article_id=%s slug=%s wiki_page_type=%s",
        article.id,
        slug,
        page_type,
    )
    return await build_wiki_detail(db, article.id)


async def update_wiki_page(db: AsyncSession, article_id: int, body: WikiPageBody) -> dict[str, Any]:
    article = await _require_wiki_article(db, article_id)
    page_type = validate_wiki_type(body.wiki_page_type)
    slug = await _ensure_unique_slug(db, validate_wiki_slug(body.slug), article.id)
    if is_smoke_slug(slug):
        raise HTTPException(status_code=422, detail="wiki_slug_reserved_smoke")

    article.title = body.title.strip()
    article.slug = slug
    article.content = body.body
    article.excerpt = (body.quick_answer or body.core_takeaway or "").strip()
    article.original_keyword = (body.target_query or "").strip()
    article.keywords = ",".join(t.strip() for t in body.tags if t.strip())
    article.content_format = WIKI_FORMAT
    article.theme_id = _parse_theme_id(body.geo_theme_id) or article.theme_id
    article.wiki_meta = build_wiki_meta(_meta_dict(article), body, page_type, slug)
    await db.flush()
    logger.info(
        "wiki_page_updated article_id=%s slug=%s wiki_page_type=%s",
        article.id,
        slug,
        page_type,
    )
    return await build_wiki_detail(db, article.id)


async def publish_wiki_page(db: AsyncSession, article_id: int) -> dict[str, Any]:
    article = await _require_wiki_article(db, article_id)
    slug = str(meta_get(_meta_dict(article), "slug") or article.slug)
    if is_smoke_slug(slug):
        raise HTTPException(status_code=422, detail="wiki_slug_reserved_smoke")
    if not (article.content or "").strip():
        raise HTTPException(status_code=422, detail="wiki_body_empty")

    publisher = GeowebPublisher()
    try:
        result = await publisher.publish(article)
    except RuntimeError as exc:
        logger.warning(
            "wiki_page_publish_failed article_id=%s slug=%s error=%s",
            article.id,
            slug,
            str(exc)[:200],
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if article.review_status not in ("approved", "auto_approved"):
        article.review_status = "auto_approved"
    article.status = "published"
    if article.published_at is None:
        article.published_at = datetime.now(UTC).replace(tzinfo=None)
    await db.flush()
    logger.info(
        "wiki_page_published article_id=%s slug=%s wiki_page_type=%s geoweb_url=%s dry_run=%s",
        article.id,
        slug,
        resolve_wiki_page_type(article),
        result.get("url"),
        bool(result.get("dry_run")),
    )
    payload = await build_wiki_detail(db, article.id)
    payload["publish"] = result
    return payload
