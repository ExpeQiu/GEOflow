"""Wiki 编辑台字段校验与 wiki_meta 组装（无 ORM）。"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.services.geoflow.wiki_types import GEOWEB_PAGE_TYPES, SLUG_RE


class WikiFaqItem(BaseModel):
    q: str = Field(min_length=1)
    a: str = Field(min_length=1)


class WikiPageBody(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    slug: str = Field(min_length=1, max_length=180)
    wiki_page_type: str = Field(min_length=1)
    body: str = Field(min_length=1)
    domain: str = ""
    quick_answer: str = ""
    core_takeaway: str = ""
    target_query: str = ""
    related: list[str] = Field(default_factory=list)
    faq: list[WikiFaqItem] = Field(default_factory=list)
    schema_type: str = "TechArticle"
    geo_theme_id: str | None = None
    tags: list[str] = Field(default_factory=list)


def validate_wiki_slug(slug: str) -> str:
    cleaned = (slug or "").strip().lower()
    if not SLUG_RE.fullmatch(cleaned):
        raise HTTPException(status_code=422, detail="wiki_slug_invalid")
    return cleaned


def validate_wiki_type(page_type: str) -> str:
    cleaned = (page_type or "").strip()
    if cleaned not in GEOWEB_PAGE_TYPES:
        raise HTTPException(status_code=422, detail="wiki_type_invalid")
    return cleaned


def meta_get(meta: dict[str, Any], key: str, default: Any = None) -> Any:
    frontmatter = meta.get("frontmatter") if isinstance(meta.get("frontmatter"), dict) else {}
    if key in frontmatter and frontmatter[key] not in (None, ""):
        return frontmatter[key]
    if key in meta and meta[key] not in (None, ""):
        return meta[key]
    return default


def as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        if isinstance(value, str) and value.strip():
            return [line.strip() for line in value.splitlines() if line.strip()]
        return []
    return [str(x).strip() for x in value if str(x).strip()]


def as_faq(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    out: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        q = str(item.get("q") or item.get("question") or "").strip()
        a = str(item.get("a") or item.get("answer") or "").strip()
        if q and a:
            out.append({"q": q, "a": a})
    return out


def build_wiki_meta(existing: dict[str, Any] | None, body: WikiPageBody, page_type: str, slug: str) -> dict[str, Any]:
    meta = dict(existing or {})
    tags = [t.strip() for t in body.tags if t.strip()]
    related = [r.strip() for r in body.related if r.strip()]
    faq = [{"q": item.q.strip(), "a": item.a.strip()} for item in body.faq if item.q.strip() and item.a.strip()]
    domain = (body.domain or "").strip()
    schema_type = (body.schema_type or "TechArticle").strip() or "TechArticle"
    geo_theme_id = (body.geo_theme_id or "").strip() or None

    meta.update(
        {
            "wiki_page_type": page_type,
            "type": page_type,
            "slug": slug,
            "domain": domain or None,
            "quick_answer": (body.quick_answer or "").strip() or None,
            "core_takeaway": (body.core_takeaway or "").strip() or None,
            "target_query": (body.target_query or "").strip() or None,
            "related": related,
            "faq": faq,
            "schema_type": schema_type,
            "geo_theme_id": geo_theme_id,
            "tags": tags,
        }
    )
    return meta
