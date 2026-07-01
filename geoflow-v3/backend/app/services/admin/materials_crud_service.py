"""L2 素材库 CRUD — 分类与作者。"""

import logging
import re

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.material import Author, Category

logger = logging.getLogger(__name__)


class CategoryBody(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str | None = Field(default=None, max_length=100)
    description: str = ""
    sort_order: int = 0


class AuthorBody(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    bio: str = ""
    email: str = ""


async def list_categories(db: AsyncSession) -> dict:
    rows = (await db.execute(select(Category).order_by(Category.sort_order, Category.id))).scalars().all()
    return {
        "items": [
            {
                "id": c.id,
                "name": c.name,
                "slug": c.slug,
                "description": c.description or "",
                "sort_order": c.sort_order,
            }
            for c in rows
        ]
    }


async def create_category(db: AsyncSession, body: CategoryBody) -> dict:
    slug = _slugify(body.slug or body.name)
    if await _category_slug_exists(db, slug):
        raise HTTPException(status_code=422, detail="slug_exists")
    row = Category(name=body.name.strip(), slug=slug, description=body.description.strip(), sort_order=body.sort_order)
    db.add(row)
    await db.flush()
    logger.info("admin_category_created id=%s slug=%s", row.id, row.slug)
    return {"item": _category_dict(row)}


async def update_category(db: AsyncSession, category_id: int, body: CategoryBody) -> dict:
    row = await db.get(Category, category_id)
    if row is None:
        raise HTTPException(status_code=404, detail="category_not_found")
    slug = _slugify(body.slug or body.name)
    if slug != row.slug and await _category_slug_exists(db, slug, exclude_id=category_id):
        raise HTTPException(status_code=422, detail="slug_exists")
    row.name = body.name.strip()
    row.slug = slug
    row.description = body.description.strip()
    row.sort_order = body.sort_order
    await db.flush()
    logger.info("admin_category_updated id=%s", row.id)
    return {"item": _category_dict(row)}


async def delete_category(db: AsyncSession, category_id: int) -> dict:
    row = await db.get(Category, category_id)
    if row is None:
        raise HTTPException(status_code=404, detail="category_not_found")
    in_use = int(
        await db.scalar(select(func.count()).select_from(Article).where(Article.category_id == category_id)) or 0
    )
    if in_use > 0:
        raise HTTPException(status_code=422, detail="category_in_use")
    await db.delete(row)
    logger.info("admin_category_deleted id=%s", category_id)
    return {"deleted": True}


async def list_authors(db: AsyncSession) -> dict:
    rows = (await db.execute(select(Author).order_by(Author.name))).scalars().all()
    return {
        "items": [
            {"id": a.id, "name": a.name, "bio": a.bio or "", "email": a.email or ""}
            for a in rows
        ]
    }


async def create_author(db: AsyncSession, body: AuthorBody) -> dict:
    row = Author(name=body.name.strip(), bio=body.bio.strip(), email=body.email.strip())
    db.add(row)
    await db.flush()
    logger.info("admin_author_created id=%s", row.id)
    return {"item": _author_dict(row)}


async def update_author(db: AsyncSession, author_id: int, body: AuthorBody) -> dict:
    row = await db.get(Author, author_id)
    if row is None:
        raise HTTPException(status_code=404, detail="author_not_found")
    row.name = body.name.strip()
    row.bio = body.bio.strip()
    row.email = body.email.strip()
    await db.flush()
    logger.info("admin_author_updated id=%s", row.id)
    return {"item": _author_dict(row)}


async def delete_author(db: AsyncSession, author_id: int) -> dict:
    row = await db.get(Author, author_id)
    if row is None:
        raise HTTPException(status_code=404, detail="author_not_found")
    in_use = int(
        await db.scalar(select(func.count()).select_from(Article).where(Article.author_id == author_id)) or 0
    )
    if in_use > 0:
        raise HTTPException(status_code=422, detail="author_in_use")
    await db.delete(row)
    logger.info("admin_author_deleted id=%s", author_id)
    return {"deleted": True}


def _category_dict(row: Category) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "slug": row.slug,
        "description": row.description or "",
        "sort_order": row.sort_order,
    }


def _author_dict(row: Author) -> dict:
    return {"id": row.id, "name": row.name, "bio": row.bio or "", "email": row.email or ""}


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug[:100] or "category"


async def _category_slug_exists(db: AsyncSession, slug: str, exclude_id: int | None = None) -> bool:
    query = select(Category.id).where(Category.slug == slug).limit(1)
    if exclude_id:
        query = query.where(Category.id != exclude_id)
    return (await db.execute(query)).scalar_one_or_none() is not None
