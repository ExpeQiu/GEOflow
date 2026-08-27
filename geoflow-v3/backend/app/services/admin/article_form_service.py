"""文章编辑 — Admin BFF。"""

import logging
import re
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.geoeval import ArticleEvaluation
from app.models.material import Author, Category
from app.models.task import Task
from app.core.config import get_settings
from app.core.sensitive_filter import assert_text_clean
from app.services.admin.geo_eval_settings_service import get_geo_eval_gate_config
from app.services.admin.article_import import (
    default_geoweb_articles_dir,
    is_official_geoweb_article_page,
    scan_geoweb_articles_dir,
)
from app.services.admin.article_reconcile import diff_article_inventories
from app.services.admin.operations_service import build_articles_panel
from app.services.admin.wiki_editor_service import _default_category_author, _parse_theme_id
from app.services.geoflow.wiki_types import is_article_content_format, is_distribution_article, is_wiki_content_format

logger = logging.getLogger(__name__)


class AdminArticleUpdateBody(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    excerpt: str = ""
    content: str = Field(min_length=1)
    keywords: str = ""
    meta_description: str = ""
    status: str = Field(pattern="^(draft|published|private)$")
    review_status: str = Field(pattern="^(pending|approved|rejected|auto_approved)$")
    category_id: int = Field(ge=1)
    author_id: int = Field(ge=1)


class AdminArticleCreateBody(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    excerpt: str = ""
    content: str = Field(min_length=1)
    keywords: str = ""
    meta_description: str = ""
    status: str = Field(default="draft", pattern="^(draft|published|private)$")
    review_status: str = Field(default="pending", pattern="^(pending|approved|rejected|auto_approved)$")
    category_id: int = Field(ge=1)
    author_id: int = Field(ge=1)


async def build_article_form_options(db: AsyncSession) -> dict[str, Any]:
    categories = (await db.execute(select(Category).order_by(Category.sort_order, Category.id))).scalars().all()
    authors = (await db.execute(select(Author).order_by(Author.name))).scalars().all()
    return {
        "categories": [{"id": c.id, "name": c.name} for c in categories],
        "authors": [{"id": a.id, "name": a.name} for a in authors],
    }


async def build_article_detail(db: AsyncSession, article_id: int) -> dict[str, Any]:
    article = await db.get(Article, article_id)
    if article is None or article.deleted_at:
        raise HTTPException(status_code=404, detail="article_not_found")
    if is_wiki_content_format(article.content_format):
        raise HTTPException(status_code=404, detail="article_not_found")

    task_name = ""
    publish_scope = "local_and_distribution"
    if article.task_id:
        task = await db.get(Task, article.task_id)
        if task:
            task_name = task.name
            publish_scope = task.publish_scope or publish_scope

    eval_meta = article.eval_meta if isinstance(article.eval_meta, dict) else {}
    latest_eval = (
        await db.execute(
            select(ArticleEvaluation)
            .where(ArticleEvaluation.article_id == article_id)
            .order_by(ArticleEvaluation.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest_eval and isinstance(latest_eval.metrics, dict):
        # 以最新评估 metrics 为准，覆盖可能过期的 article.eval_meta
        eval_meta = {**eval_meta, **latest_eval.metrics}

    sim = eval_meta.get("simulation") if isinstance(eval_meta.get("simulation"), dict) else {}
    audit = eval_meta.get("audit") if isinstance(eval_meta.get("audit"), dict) else {}
    eval_failure_reason = ""
    if latest_eval and latest_eval.failure_reason:
        eval_failure_reason = str(latest_eval.failure_reason)
    elif article.eval_status in ("failed", "advisory"):
        eval_failure_reason = "; ".join(eval_meta.get("advisory_issues") or [])[:500]

    gate = await get_geo_eval_gate_config(db)
    hard_gate = bool(gate["hard_gate"])
    geo_eval_enabled = bool(gate["enabled"])
    sim_score = eval_meta.get("simulation_score")
    if sim_score is None and sim:
        sim_score = sim.get("simulation_score")
    audit_score = eval_meta.get("audit_score")
    if audit_score is None and audit:
        audit_score = audit.get("audit_score")

    return {
        "article": {
            "id": article.id,
            "title": article.title,
            "slug": article.slug,
            "excerpt": article.excerpt or "",
            "content": article.content,
            "keywords": article.keywords or "",
            "meta_description": article.meta_description or "",
            "status": article.status,
            "review_status": article.review_status,
            "eval_status": article.eval_status,
            "content_format": article.content_format or "article",
            "category_id": article.category_id,
            "author_id": article.author_id,
            "task_id": article.task_id,
            "task_name": task_name,
            "publish_scope": publish_scope,
            "view_count": article.view_count,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "created_at": article.created_at.isoformat() if article.created_at else None,
            "updated_at": article.updated_at.isoformat() if article.updated_at else None,
            "eval_failure_reason": eval_failure_reason,
            "eval_simulation_score": sim_score,
            "eval_audit_score": audit_score,
            "eval_audit_passed": eval_meta.get("audit_passed", audit.get("audit_passed")),
            "eval_retrieval_score": sim.get("retrieval_score"),
            "eval_query": sim.get("query") or "",
            "eval_simulated_answer": (sim.get("simulated_answer") or "")[:280],
            "eval_recommendations": eval_meta.get("recommendations") or [],
            "eval_advisory_issues": eval_meta.get("advisory_issues") or [],
            "eval_meets_thresholds": eval_meta.get("meets_thresholds"),
            "eval_gate_mode": eval_meta.get("gate_mode") or ("hard" if hard_gate else "soft"),
            "geo_eval_enabled": geo_eval_enabled,
            # 展示用：硬门禁才真正拦发布；软门禁仅评分建议
            "geo_eval_gate_enabled": geo_eval_enabled and hard_gate,
            "geo_eval_hard_gate": hard_gate,
        }
    }


async def update_admin_article(db: AsyncSession, article_id: int, body: AdminArticleUpdateBody) -> dict:
    await assert_text_clean(db, body.title, body.content, body.excerpt, body.keywords, context="article_update")
    article = await db.get(Article, article_id)
    if article is None or article.deleted_at:
        raise HTTPException(status_code=404, detail="article_not_found")

    category = await db.get(Category, body.category_id)
    author = await db.get(Author, body.author_id)
    if category is None:
        raise HTTPException(status_code=422, detail="category_not_found")
    if author is None:
        raise HTTPException(status_code=422, detail="author_not_found")

    title_changed = body.title.strip() != article.title
    article.title = body.title.strip()
    if title_changed:
        article.slug = await _unique_slug(db, body.title.strip(), article.id)

    article.content = body.content
    article.excerpt = body.excerpt.strip() or _auto_excerpt(body.content)
    article.keywords = body.keywords.strip()
    article.meta_description = body.meta_description.strip()
    article.category_id = body.category_id
    article.author_id = body.author_id
    article.status = body.status
    article.review_status = body.review_status

    if body.status == "published" and body.review_status in ("approved", "auto_approved") and article.published_at is None:
        article.published_at = datetime.now(UTC)
    if body.status == "draft" and article.published_at and body.review_status == "pending":
        article.published_at = None

    await db.flush()
    logger.info("admin_article_updated article_id=%s status=%s review=%s", article.id, article.status, article.review_status)

    return {"article": (await build_article_detail(db, article.id))["article"]}


async def create_admin_article(db: AsyncSession, body: AdminArticleCreateBody) -> dict:
    await assert_text_clean(db, body.title, body.content, getattr(body, "excerpt", ""), getattr(body, "keywords", ""), context="article_create")
    category = await db.get(Category, body.category_id)
    author = await db.get(Author, body.author_id)
    if category is None:
        raise HTTPException(status_code=422, detail="category_not_found")
    if author is None:
        raise HTTPException(status_code=422, detail="author_not_found")

    slug = await _unique_slug(db, body.title.strip(), 0)
    article = Article(
        title=body.title.strip(),
        slug=slug,
        content=body.content,
        excerpt=body.excerpt.strip() or _auto_excerpt(body.content),
        keywords=body.keywords.strip(),
        meta_description=body.meta_description.strip(),
        category_id=body.category_id,
        author_id=body.author_id,
        status=body.status,
        review_status=body.review_status,
        content_format="article",
    )
    if body.status == "published" and body.review_status in ("approved", "auto_approved"):
        article.published_at = datetime.now(UTC)
    db.add(article)
    await db.flush()
    logger.info("admin_article_created article_id=%s", article.id)
    return {"article": (await build_article_detail(db, article.id))["article"]}


async def build_trashed_articles(db: AsyncSession) -> dict:
    articles = (
        await db.execute(
            select(Article).where(Article.deleted_at.isnot(None)).order_by(Article.deleted_at.desc()).limit(100)
        )
    ).scalars().all()
    articles = [a for a in articles if is_article_content_format(a.content_format)]
    return {
        "articles": [
            {
                "id": a.id,
                "title": a.title,
                "status": a.status,
                "deleted_at": a.deleted_at.isoformat() if a.deleted_at else None,
            }
            for a in articles
        ],
        "total": len(articles),
    }


async def restore_admin_article(db: AsyncSession, article_id: int) -> dict:
    article = await db.get(Article, article_id)
    if article is None or article.deleted_at is None:
        raise HTTPException(status_code=404, detail="article_not_found")
    article.deleted_at = None
    article.status = "draft" if article.status == "trashed" else article.status
    await db.flush()
    logger.info("admin_article_restored article_id=%s", article_id)
    return {"article": _article_brief(article)}


async def purge_admin_article(db: AsyncSession, article_id: int) -> dict:
    article = await db.get(Article, article_id)
    if article is None or article.deleted_at is None:
        raise HTTPException(status_code=404, detail="article_not_found")
    await db.delete(article)
    await db.flush()
    logger.info("admin_article_purged article_id=%s", article_id)
    return {"deleted": True}


def _article_brief(article: Article) -> dict:
    return {"id": article.id, "title": article.title, "status": article.status, "review_status": article.review_status}


def _auto_excerpt(content: str, limit: int = 200) -> str:
    plain = re.sub(r"[#*`>\[\]()]", "", content)
    plain = re.sub(r"\s+", " ", plain).strip()
    return plain[:limit]


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_-]+", "-", slug).strip("-")[:80] or "article"


async def _unique_slug(db: AsyncSession, title: str, article_id: int) -> str:
    base = _slugify(title)
    slug = base
    suffix = 1
    while True:
        query = select(Article.id).where(Article.slug == slug).limit(1)
        if article_id:
            query = query.where(Article.id != article_id)
        existing = (await db.execute(query)).scalar_one_or_none()
        if existing is None:
            return slug
        suffix += 1
        slug = f"{base}-{suffix}"


def _article_geoweb_url(base: str, slug: str) -> str:
    return f"{base.rstrip('/')}/articles/{slug}"


def _build_article_import_meta(parsed: dict[str, Any], *, geoweb_url: str) -> dict[str, Any]:
    source = str(parsed.get("source") or "seed").strip() or "seed"
    meta: dict[str, Any] = {
        "type": "article",
        "slug": parsed["slug"],
        "domain": parsed.get("domain") or "",
        "quick_answer": parsed.get("quick_answer") or "",
        "core_takeaway": parsed.get("core_takeaway") or "",
        "target_query": parsed.get("target_query") or "",
        "related": parsed.get("related") or [],
        "faq": parsed.get("faq") or [],
        "schema_type": parsed.get("schema_type") or "TechArticle",
        "tags": parsed.get("tags") or [],
        "imported_from": source,
        "geoflow_lane": "distribution",
        "geoweb_url": geoweb_url,
    }
    if parsed.get("geo_content_hash"):
        meta["geo_content_hash"] = parsed["geo_content_hash"]
    if parsed.get("geo_theme_id"):
        meta["geo_theme_id"] = parsed["geo_theme_id"]
    return meta


async def import_geoweb_articles(
    db: AsyncSession,
    wiki_dir: str | None = None,
    include_smoke: bool = False,
    *,
    official_only: bool = True,
) -> dict[str, Any]:
    """把 GEOweb content/wiki/articles 官方长文拉进编辑台。"""
    from pathlib import Path

    settings = get_settings()
    root = Path(wiki_dir) if wiki_dir else default_geoweb_articles_dir()
    if not root.is_dir():
        raise HTTPException(status_code=422, detail=f"wiki_dir_not_found:{root}")

    scanned_all = scan_geoweb_articles_dir(root, include_smoke=True, official_only=False)
    scanned = scan_geoweb_articles_dir(root, include_smoke=include_smoke, official_only=official_only)
    geoflow_skipped = sum(1 for p in scanned_all if not is_official_geoweb_article_page(p))
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
        existing = (
            await db.execute(
                select(Article).where(Article.slug == slug, Article.deleted_at.is_(None)).limit(1)
            )
        ).scalar_one_or_none()
        if existing is not None and is_wiki_content_format(existing.content_format):
            skipped_conflict += 1
            logger.warning("article_import_slug_conflict slug=%s article_id=%s", slug, existing.id)
            continue

        excerpt = (parsed.get("quick_answer") or parsed.get("core_takeaway") or "").strip()
        tags = parsed.get("tags") or []
        preview = _article_geoweb_url(geoweb_base_url, slug) if geoweb_base_url else ""
        if existing is None:
            article = Article(
                title=parsed["title"],
                slug=slug,
                content=parsed["body"],
                excerpt=excerpt,
                original_keyword=parsed.get("target_query") or "",
                keywords=",".join(tags),
                category_id=category_id,
                author_id=author_id,
                status="published",
                review_status="auto_approved",
                eval_status="skipped",
                content_format="article",
                wiki_meta={},
                theme_id=_parse_theme_id(parsed.get("geo_theme_id")),
                published_at=datetime.now(UTC).replace(tzinfo=None),
                is_ai_generated=0,
            )
            db.add(article)
            await db.flush()
            created += 1
        else:
            article = existing
            article.title = parsed["title"]
            article.content = parsed["body"]
            article.excerpt = excerpt
            article.original_keyword = parsed.get("target_query") or ""
            article.keywords = ",".join(tags)
            article.content_format = "article"
            article.status = "published"
            if article.review_status not in ("approved", "auto_approved"):
                article.review_status = "auto_approved"
            if article.published_at is None:
                article.published_at = datetime.now(UTC).replace(tzinfo=None)
            if parsed.get("geo_theme_id"):
                article.theme_id = _parse_theme_id(parsed.get("geo_theme_id"))
            updated += 1

        article.wiki_meta = _build_article_import_meta(parsed, geoweb_url=preview)

    await db.flush()
    logger.info(
        "articles_imported created=%s updated=%s smoke_skipped=%s geoflow_skipped=%s conflict=%s dir=%s official_only=%s",
        created,
        updated,
        smoke_skipped,
        geoflow_skipped,
        skipped_conflict,
        str(root),
        official_only,
    )
    panel = await build_articles_panel(db)
    panel["import"] = {
        "created": created,
        "updated": updated,
        "smoke_skipped": smoke_skipped,
        "geoflow_skipped": geoflow_skipped,
        "conflict": skipped_conflict,
        "wiki_dir": str(root),
        "official_only": official_only,
        "official_count": len(scanned),
    }
    return panel


async def reconcile_articles_with_geoweb(db: AsyncSession) -> dict[str, Any]:
    import httpx

    settings = get_settings()
    geoweb_base_url = (settings.geoweb_base_url or "").rstrip("/")
    if not geoweb_base_url:
        raise HTTPException(status_code=422, detail="geoweb_base_url_missing")

    articles = (
        await db.execute(
            select(Article).where(Article.deleted_at.is_(None)).order_by(Article.id.desc())
        )
    ).scalars().all()
    local = [
        {
            "id": a.id,
            "slug": a.slug,
            "title": a.title,
            "status": a.status,
            "wiki_meta": a.wiki_meta if isinstance(a.wiki_meta, dict) else {},
        }
        for a in articles
        if is_distribution_article(
            content_format=a.content_format,
            slug=a.slug or "",
            title=a.title or "",
            wiki_meta=a.wiki_meta if isinstance(a.wiki_meta, dict) else {},
        )
    ]

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
        logger.warning("articles_reconcile_fetch_failed url=%s error=%s", url, str(exc)[:200])
        raise HTTPException(status_code=502, detail="geoweb_pages_unreachable") from exc

    if not isinstance(remote, list):
        raise HTTPException(status_code=502, detail="geoweb_pages_invalid")

    diff = diff_article_inventories(local, remote)
    logger.info(
        "articles_reconciled local=%s remote=%s matched=%s local_only=%s remote_only=%s hash_mismatch=%s",
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
