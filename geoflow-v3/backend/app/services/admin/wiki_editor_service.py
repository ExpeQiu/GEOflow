"""GEOweb Wiki 轻量编辑台 — Admin BFF（ADR-011 Wave 1）。"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.article import Article
from app.models.material import Author, Category
from app.services.admin.wiki_draft import render_wiki_draft
from app.services.admin.wiki_editor_schema import (
    WikiGenerateDraftBody,
    WikiPageBody,
    as_faq,
    as_str_list,
    build_wiki_meta,
    meta_get,
    validate_wiki_slug,
    validate_wiki_type,
    wiki_publish_gate,
)
from app.services.admin.wiki_pack import sort_pack_pages
from app.services.admin.wiki_reconcile import diff_wiki_inventories
from app.services.geoflow.geoweb_publisher import GeowebPublisher
from app.services.geoflow.wiki_types import (
    GEOWEB_PAGE_TYPES,
    is_smoke_slug,
    related_path_for,
    wiki_preview_url,
)

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
    related = as_str_list(meta_get(meta, "related"))
    faq = as_faq(meta_get(meta, "faq"))
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
        "related": related,
        "faq": faq,
        "publish_gate": wiki_publish_gate(page_type, related, faq),
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
    meta = _meta_dict(article)
    slug = str(meta_get(meta, "slug") or article.slug)
    page_type = resolve_wiki_page_type(article)
    if is_smoke_slug(slug):
        raise HTTPException(status_code=422, detail="wiki_slug_reserved_smoke")
    if not (article.content or "").strip():
        raise HTTPException(status_code=422, detail="wiki_body_empty")
    gate = wiki_publish_gate(page_type, as_str_list(meta_get(meta, "related")), as_faq(meta_get(meta, "faq")))
    if not gate["ok"]:
        logger.info(
            "wiki_publish_gate_blocked article_id=%s slug=%s wiki_page_type=%s errors=%s",
            article.id,
            slug,
            page_type,
            gate["errors"],
        )
        raise HTTPException(status_code=422, detail={"code": "wiki_publish_gate", **gate})

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


async def import_geoweb_wiki_pages(
    db: AsyncSession,
    wiki_dir: str | None = None,
    include_smoke: bool = False,
) -> dict[str, Any]:
    """把 GEOweb content/wiki 拉进编辑台，不回写前台文件。"""
    from app.services.admin.wiki_import import default_geoweb_wiki_dir, scan_geoweb_wiki_dir

    settings = get_settings()
    root = Path(wiki_dir) if wiki_dir else default_geoweb_wiki_dir()
    if not root.is_dir():
        raise HTTPException(status_code=422, detail=f"wiki_dir_not_found:{root}")

    scanned = scan_geoweb_wiki_dir(root, include_smoke=True)
    category_id, author_id = await _default_category_author(db)
    geoweb_base_url = (settings.geoweb_base_url or "").rstrip("/")
    created = 0
    updated = 0
    skipped_conflict = 0
    smoke_skipped = 0

    for parsed in scanned:
        slug = parsed["slug"]
        if parsed.get("smoke") and not include_smoke:
            smoke_skipped += 1
            continue
        page_type = parsed["wiki_page_type"]
        existing = (
            await db.execute(
                select(Article).where(Article.slug == slug, Article.deleted_at.is_(None)).limit(1)
            )
        ).scalar_one_or_none()
        if existing is not None and (existing.content_format or "article") != WIKI_FORMAT:
            skipped_conflict += 1
            logger.warning("wiki_import_slug_conflict slug=%s article_id=%s", slug, existing.id)
            continue

        body = WikiPageBody(
            title=parsed["title"],
            slug=slug,
            wiki_page_type=page_type,
            body=parsed["body"],
            domain=parsed.get("domain") or "",
            quick_answer=parsed.get("quick_answer") or "",
            core_takeaway=parsed.get("core_takeaway") or "",
            target_query=parsed.get("target_query") or "",
            related=parsed.get("related") or [],
            faq=parsed.get("faq") or [],
            schema_type=parsed.get("schema_type") or "TechArticle",
            geo_theme_id=parsed.get("geo_theme_id"),
            tags=parsed.get("tags") or [],
        )
        preview = wiki_preview_url(geoweb_base_url, page_type, slug)
        if existing is None:
            article = Article(
                title=body.title,
                slug=slug,
                content=body.body,
                excerpt=(body.quick_answer or body.core_takeaway or "").strip(),
                original_keyword=body.target_query,
                keywords=",".join(body.tags),
                category_id=category_id,
                author_id=author_id,
                status="published",
                review_status="auto_approved",
                eval_status="skipped",
                content_format=WIKI_FORMAT,
                wiki_meta={},
                theme_id=_parse_theme_id(body.geo_theme_id),
                published_at=datetime.now(UTC).replace(tzinfo=None),
                is_ai_generated=0,
            )
            db.add(article)
            await db.flush()
            created += 1
        else:
            article = existing
            article.title = body.title
            article.content = body.body
            article.excerpt = (body.quick_answer or body.core_takeaway or "").strip()
            article.original_keyword = body.target_query
            article.keywords = ",".join(body.tags)
            article.content_format = WIKI_FORMAT
            article.status = "published"
            if article.review_status not in ("approved", "auto_approved"):
                article.review_status = "auto_approved"
            if article.published_at is None:
                article.published_at = datetime.now(UTC).replace(tzinfo=None)
            updated += 1

        meta = build_wiki_meta(_meta_dict(article), body, page_type, slug)
        meta["geoweb_url"] = preview
        if parsed.get("geo_content_hash"):
            meta["geo_content_hash"] = parsed["geo_content_hash"]
        source = parsed.get("source") or "seed"
        meta["imported_from"] = source
        article.wiki_meta = meta

    await db.flush()
    logger.info(
        "wiki_imported created=%s updated=%s smoke_skipped=%s conflict=%s dir=%s",
        created,
        updated,
        smoke_skipped,
        skipped_conflict,
        str(root),
    )
    panel = await build_wiki_panel(db)
    panel["import"] = {
        "created": created,
        "updated": updated,
        "smoke_skipped": smoke_skipped,
        "conflict": skipped_conflict,
        "wiki_dir": str(root),
    }
    return panel


def _theme_id_of(article: Article) -> int | None:
    if article.theme_id:
        return int(article.theme_id)
    raw = meta_get(_meta_dict(article), "geo_theme_id")
    if raw is not None and str(raw).strip().isdigit():
        return int(str(raw).strip())
    return None


async def list_wiki_related_options(db: AsyncSession, exclude_id: int | None = None) -> dict[str, Any]:
    settings = get_settings()
    articles = (await db.execute(_wiki_query().order_by(Article.id.desc()).limit(400))).scalars().all()
    items: list[dict[str, Any]] = []
    for article in articles:
        if exclude_id and article.id == exclude_id:
            continue
        slug = str(meta_get(_meta_dict(article), "slug") or article.slug)
        if is_smoke_slug(slug):
            continue
        published = article.status == "published" or bool(
            meta_get(_meta_dict(article), "geo_content_hash") or meta_get(_meta_dict(article), "geoweb_url")
        )
        if not published:
            continue
        page_type = resolve_wiki_page_type(article)
        items.append(
            {
                "id": article.id,
                "path": related_path_for(page_type, slug),
                "title": article.title,
                "type": page_type,
                "slug": slug,
            }
        )
    logger.info("wiki_related_options count=%s exclude_id=%s", len(items), exclude_id)
    return {"items": items, "geoweb_base_url": (settings.geoweb_base_url or "").rstrip("/")}


async def generate_wiki_draft(db: AsyncSession, body: WikiGenerateDraftBody) -> dict[str, Any]:
    from app.models.knowledge import KnowledgeBase
    from app.services.geoflow.rag.retrieval import KnowledgeRetrievalService

    page_type = validate_wiki_type(body.wiki_page_type)
    kb = await db.get(KnowledgeBase, body.knowledge_base_id)
    if kb is None:
        raise HTTPException(status_code=404, detail="knowledge_base_not_found")

    settings = get_settings()
    query = (body.target_query or body.title).strip()
    hits: list[dict[str, Any]] = []
    try:
        hits = await KnowledgeRetrievalService(db).retrieve(body.knowledge_base_id, query, limit=4)
    except Exception:
        logger.exception(
            "wiki_draft_rag_failed knowledge_base_id=%s title=%s wiki_page_type=%s",
            body.knowledge_base_id,
            body.title,
            page_type,
        )
        hits = []

    draft = render_wiki_draft(
        title=body.title.strip(),
        wiki_page_type=page_type,
        hits=hits,
        target_query=query,
        domain=(body.domain or "").strip(),
        mock=bool(settings.ai_mock_mode) or not hits,
    )
    logger.info(
        "wiki_draft_generated knowledge_base_id=%s wiki_page_type=%s mock=%s hits=%s title=%s",
        body.knowledge_base_id,
        page_type,
        draft["mock"],
        draft["hit_count"],
        body.title,
    )
    return {
        **draft,
        "knowledge_base_id": body.knowledge_base_id,
        "knowledge_base_name": kb.name,
    }


async def build_wiki_packs(db: AsyncSession) -> dict[str, Any]:
    from app.models.theme import GeoTheme
    from app.services.admin.production_service import _table_exists
    from app.services.geoeval.theme_service import _theme_dict

    settings = get_settings()
    geoweb_base_url = (settings.geoweb_base_url or "").rstrip("/")
    articles = (await db.execute(_wiki_query().order_by(Article.id.asc()))).scalars().all()

    by_theme: dict[int, list[Article]] = {}
    unassigned: list[dict[str, Any]] = []
    for article in articles:
        slug = str(meta_get(_meta_dict(article), "slug") or article.slug)
        if is_smoke_slug(slug):
            continue
        theme_id = _theme_id_of(article)
        if theme_id is None:
            unassigned.append(_serialize_wiki_page(article, geoweb_base_url))
            continue
        by_theme.setdefault(theme_id, []).append(article)

    if not await _table_exists(db, "geo_themes"):
        return {
            "packs": [],
            "unassigned": unassigned,
            "table_missing": True,
            "geoweb_base_url": geoweb_base_url,
            "geoweb_sync_enabled": bool(settings.geoweb_sync_enabled),
        }

    themes = (await db.execute(select(GeoTheme).order_by(GeoTheme.id.desc()).limit(200))).scalars().all()

    packs: list[dict[str, Any]] = []
    for theme in themes:
        pages = [_serialize_wiki_page(article, geoweb_base_url) for article in by_theme.get(theme.id, [])]
        ordered = sort_pack_pages(pages)
        blocked = [
            {
                "id": page["id"],
                "slug": page["slug"],
                "wiki_page_type": page["wiki_page_type"],
                "errors": page["publish_gate"]["errors"],
            }
            for page in ordered
            if not page["publish_gate"]["ok"]
        ]
        empty = [page["slug"] for page in ordered if not (page.get("body") or "").strip()]
        can_sync = bool(ordered) and not blocked and not empty
        packs.append(
            {
                **_theme_dict(theme),
                "pages": ordered,
                "page_count": len(ordered),
                "blocked": blocked,
                "empty_body": empty,
                "can_sync": can_sync,
                "hub_last": True,
            }
        )

    logger.info("wiki_packs_built themes=%s packs_with_pages=%s", len(packs), sum(1 for p in packs if p["page_count"]))
    return {
        "packs": packs,
        "unassigned": unassigned,
        "geoweb_base_url": geoweb_base_url,
        "geoweb_sync_enabled": bool(settings.geoweb_sync_enabled),
    }


async def sync_wiki_pack(db: AsyncSession, theme_id: int) -> dict[str, Any]:
    from app.models.theme import GeoTheme

    theme = await db.get(GeoTheme, theme_id)
    if theme is None:
        raise HTTPException(status_code=404, detail="theme_not_found")

    articles = (await db.execute(_wiki_query().order_by(Article.id.asc()))).scalars().all()
    members: list[Article] = []
    blocked: list[dict[str, Any]] = []
    for article in articles:
        if _theme_id_of(article) != theme.id:
            continue
        slug = str(meta_get(_meta_dict(article), "slug") or article.slug)
        if is_smoke_slug(slug):
            continue
        page_type = resolve_wiki_page_type(article)
        meta = _meta_dict(article)
        gate = wiki_publish_gate(
            page_type,
            as_str_list(meta_get(meta, "related")),
            as_faq(meta_get(meta, "faq")),
        )
        if not (article.content or "").strip():
            blocked.append({"id": article.id, "slug": slug, "wiki_page_type": page_type, "errors": ["wiki_body_empty"]})
            continue
        if not gate["ok"]:
            blocked.append({"id": article.id, "slug": slug, "wiki_page_type": page_type, "errors": gate["errors"]})
            continue
        members.append(article)

    if blocked:
        logger.info("wiki_pack_gate_blocked theme_id=%s blocked=%s", theme.id, blocked)
        raise HTTPException(status_code=422, detail={"code": "wiki_pack_gate", "theme_id": theme.id, "blocked": blocked})
    if not members:
        raise HTTPException(status_code=422, detail="wiki_pack_empty")

    serialized = [
        {"id": a.id, "wiki_page_type": resolve_wiki_page_type(a), "type": resolve_wiki_page_type(a)}
        for a in members
    ]
    order_ids = [row["id"] for row in sort_pack_pages(serialized)]
    by_id = {a.id: a for a in members}
    ordered_articles = [by_id[i] for i in order_ids if i in by_id]

    publisher = GeowebPublisher()
    try:
        result = await publisher.publish_pack(str(theme.id), ordered_articles, geo_flow_task=str(theme.task_id or theme.id))
    except RuntimeError as exc:
        logger.warning("wiki_pack_sync_failed theme_id=%s error=%s", theme.id, str(exc)[:200])
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if result.get("fail_count"):
        raise HTTPException(status_code=502, detail={"code": "wiki_pack_partial", **result})

    now = datetime.now(UTC).replace(tzinfo=None)
    for article in ordered_articles:
        if article.review_status not in ("approved", "auto_approved"):
            article.review_status = "auto_approved"
        article.status = "published"
        if article.published_at is None:
            article.published_at = now
        article.theme_id = theme.id
    await db.flush()
    logger.info(
        "wiki_pack_synced theme_id=%s pages=%s dry_run=%s",
        theme.id,
        len(ordered_articles),
        bool(result.get("dry_run")),
    )
    board = await build_wiki_packs(db)
    board["sync"] = result
    return board


async def reconcile_wiki_with_geoweb(db: AsyncSession) -> dict[str, Any]:
    import httpx

    settings = get_settings()
    geoweb_base_url = (settings.geoweb_base_url or "").rstrip("/")
    if not geoweb_base_url:
        raise HTTPException(status_code=422, detail="geoweb_base_url_missing")

    articles = (await db.execute(_wiki_query().order_by(Article.id.desc()))).scalars().all()
    local = []
    for article in articles:
        page = _serialize_wiki_page(article, geoweb_base_url)
        if is_smoke_slug(page["slug"]):
            continue
        local.append(page)

    url = f"{geoweb_base_url}/api/pages.json"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"geoweb_pages_http_{resp.status_code}")
            remote = resp.json()
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("wiki_reconcile_fetch_failed url=%s error=%s", url, str(exc)[:200])
        raise HTTPException(status_code=502, detail="geoweb_pages_unreachable") from exc

    if not isinstance(remote, list):
        raise HTTPException(status_code=502, detail="geoweb_pages_invalid")

    diff = diff_wiki_inventories(local, remote)
    logger.info(
        "wiki_reconciled local=%s remote=%s matched=%s local_only=%s remote_only=%s hash_mismatch=%s",
        diff["stats"]["local"],
        diff["stats"]["remote"],
        diff["stats"]["matched"],
        diff["stats"]["local_only"],
        diff["stats"]["remote_only"],
        diff["stats"]["hash_mismatch"],
    )
    return {
        **diff,
        "geoweb_base_url": geoweb_base_url,
        "pages_json": url,
    }
