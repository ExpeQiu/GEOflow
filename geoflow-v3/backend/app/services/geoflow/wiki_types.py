"""Wiki / GEOweb 页面类型与 slug 约定（无 ORM，可供单测直接导入）。"""

from __future__ import annotations

import re

GEOWEB_PAGE_TYPES = frozenset(
    {
        "concept",
        "compare",
        "guide",
        "glossary",
        "data",
        "thread",
        "topic",
        "article",
        "certification",
    }
)

WIKI_ROUTE_PREFIX: dict[str, str] = {
    "concept": "concepts",
    "compare": "compare",
    "guide": "guides",
    "glossary": "glossary",
    "data": "data",
    "thread": "threads",
    "topic": "topics",
    "article": "articles",
    "certification": "certifications",
}

SMOKE_SLUG_RE = re.compile(r"(smoke|probe|interop)", re.I)
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def route_prefix_for_type(page_type: str) -> str:
    return WIKI_ROUTE_PREFIX.get(page_type, "articles")


def is_smoke_slug(slug: str) -> bool:
    return bool(SMOKE_SLUG_RE.search(slug or ""))


def related_path_for(page_type: str, slug: str) -> str:
    return f"{route_prefix_for_type(page_type)}/{slug}"


def wiki_preview_url(base_url: str, page_type: str, slug: str) -> str:
    base = (base_url or "").rstrip("/")
    prefix = route_prefix_for_type(page_type)
    if not base:
        return f"/{prefix}/{slug}"
    return f"{base}/{prefix}/{slug}"
