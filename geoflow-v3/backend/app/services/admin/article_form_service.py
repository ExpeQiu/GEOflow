"""文章编辑 — Admin BFF。"""

import logging
import re
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.article import Article
from app.models.geoeval import ArticleEvaluation
from app.models.material import Author, Category
from app.models.task import Task

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

    task_name = ""
    publish_scope = "local_and_distribution"
    if article.task_id:
        task = await db.get(Task, article.task_id)
        if task:
            task_name = task.name
            publish_scope = task.publish_scope or publish_scope

    eval_failure_reason = ""
    if article.eval_status == "failed":
        row = (
            await db.execute(
                select(ArticleEvaluation.failure_reason)
                .where(ArticleEvaluation.article_id == article_id, ArticleEvaluation.status == "failed")
                .order_by(ArticleEvaluation.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        eval_failure_reason = str(row or "")

    settings = get_settings()
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
            "geo_eval_enabled": settings.geo_eval_enabled,
            "geo_eval_gate_enabled": settings.geo_eval_enabled and settings.geo_eval_wiki_gate_enabled,
        }
    }


async def update_admin_article(db: AsyncSession, article_id: int, body: AdminArticleUpdateBody) -> dict:
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
