"""Wiki / GEOweb 页面类型与 slug 约定（无 ORM，可供单测直接导入）。"""

from __future__ import annotations

import hashlib
import re
from typing import Any

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

WIKI_CONTENT_FORMAT = "wiki_mdx"
ARTICLE_CONTENT_FORMAT = "article"

# Theme 包误写入「长文章」列表的 Wiki 页特征
_WIKI_NON_ARTICLE_SLUG_RE = re.compile(
    r"^ai-(concept|compare|guide|glossary|topic|thread|data|certification)-\d+",
    re.I,
)
_WIKI_NON_ARTICLE_TITLE_RE = re.compile(
    r" · (concept|compare|guide|glossary|topic|thread|data|certification)$",
    re.I,
)


THEME_PACK_TITLE_RE = re.compile(
    r"补齐 AI 决策链| · (concept|compare|guide|glossary|topic|thread|data|certification|article)$",
    re.I,
)

# 分发长文 / 探针误写入 Wiki 编辑台的 slug 特征
GEOFLOW_PIPELINE_WIKI_SLUG_RE = re.compile(
    r"^(?:article|l7|suv|noa|15-suv|ad-max|2024-noa|ai-dfe8196b00|ssot|geoflow-kb-fact|geoflow-geoweb|geoflow-interop)(?:-|$)",
    re.I,
)
GEOFLOW_HASH_SLUG_SUFFIX_RE = re.compile(r"-[a-f0-9]{8,}-\d+$", re.I)


def is_wiki_mdx_pollution(
    *,
    slug: str = "",
    title: str = "",
    wiki_meta: dict[str, Any] | None = None,
) -> bool:
    """误写入 Wiki 编辑台的分发长文、Theme 管线页或探针（非官方 Wiki seed）。"""
    meta = wiki_meta if isinstance(wiki_meta, dict) else {}
    page_type = str(meta.get("wiki_page_type") or meta.get("type") or "").strip().lower()
    if page_type == "article":
        return True
    lane = str(meta.get("geoflow_lane") or "").strip().lower()
    if lane == "distribution":
        return True
    resolved = str(meta.get("slug") or slug or "").strip()
    if not resolved:
        return True
    if GEOFLOW_PIPELINE_WIKI_SLUG_RE.match(resolved):
        return True
    if GEOFLOW_HASH_SLUG_SUFFIX_RE.search(resolved):
        return True
    source = str(meta.get("imported_from") or meta.get("source") or "").strip().lower()
    if source == "geoflow" and lane != "wiki":
        return True
    if is_theme_pack_wiki_record(slug=resolved, title=title, wiki_meta=meta):
        return True
    return False

def is_theme_pack_wiki_record(
    *,
    theme_id: int | None = None,
    slug: str = "",
    title: str = "",
    wiki_meta: dict[str, Any] | None = None,
) -> bool:
    """Theme 包产出（应走 /operations/articles，不进 Wiki 编辑台）。"""
    if theme_id:
        return True
    meta = wiki_meta if isinstance(wiki_meta, dict) else {}
    if str(meta.get("geo_theme_id") or meta.get("theme_id") or "").strip():
        return True
    if THEME_PACK_TITLE_RE.search(title or ""):
        return True
    if _WIKI_NON_ARTICLE_SLUG_RE.match(slug or ""):
        return True
    if _WIKI_NON_ARTICLE_TITLE_RE.search(title or ""):
        return True
    return False


def is_editable_wiki_panel_record(
    *,
    content_format: str | None,
    theme_id: int | None,
    slug: str,
    title: str,
    wiki_meta: dict[str, Any] | None,
    official_slugs: set[str],
    tech_brand_mode: bool,
) -> bool:
    """Wiki 编辑台列表可见性：Techstore 模式 = 新建 Wiki（无 Theme）；默认 = 官方 seed slug 对齐。"""
    if (content_format or ARTICLE_CONTENT_FORMAT) != WIKI_CONTENT_FORMAT:
        return False
    if is_theme_pack_wiki_record(theme_id=theme_id, slug=slug, title=title, wiki_meta=wiki_meta):
        return False
    if is_wiki_mdx_pollution(slug=slug, title=title, wiki_meta=wiki_meta):
        return False
    meta = wiki_meta if isinstance(wiki_meta, dict) else {}
    resolved_slug = str(meta.get("slug") or slug or "").strip()
    if tech_brand_mode:
        return bool(resolved_slug) and not is_smoke_slug(resolved_slug)
    if not resolved_slug or resolved_slug not in official_slugs:
        return False
    page_type = str(meta.get("wiki_page_type") or meta.get("type") or "").strip()
    if page_type == "article":
        return False
    return not is_smoke_slug(resolved_slug)


def is_wiki_content_format(content_format: str | None) -> bool:
    return (content_format or ARTICLE_CONTENT_FORMAT) == WIKI_CONTENT_FORMAT


def is_article_content_format(content_format: str | None) -> bool:
    return not is_wiki_content_format(content_format)


def infer_wiki_page_type_from_article(*, slug: str, title: str, wiki_meta: dict[str, Any] | None = None) -> str | None:
    """从 slug / 标题 / meta 推断误写入长文章表的 Wiki 页型。"""
    meta = wiki_meta if isinstance(wiki_meta, dict) else {}
    page_type = str(meta.get("type") or meta.get("wiki_page_type") or "").strip().lower()
    if page_type in GEOWEB_PAGE_TYPES and page_type != "article":
        return page_type
    slug_match = _WIKI_NON_ARTICLE_SLUG_RE.match(slug or "")
    if slug_match:
        return slug_match.group(1).lower()
    title_match = _WIKI_NON_ARTICLE_TITLE_RE.search(title or "")
    if title_match:
        return title_match.group(1).lower()
    return None


def is_distribution_article(
    *,
    content_format: str | None,
    slug: str,
    title: str,
    wiki_meta: dict[str, Any] | None = None,
) -> bool:
    """生产-分发长文（/operations/articles ↔ GEOweb /articles），排除 Wiki 页型。"""
    if not is_article_content_format(content_format):
        return False
    meta = wiki_meta if isinstance(wiki_meta, dict) else {}
    page_type = str(meta.get("type") or meta.get("wiki_page_type") or "").strip().lower()
    if page_type and page_type != "article":
        return False
    lane = str(meta.get("geoflow_lane") or "").strip().lower()
    if lane == "wiki":
        return False
    if infer_wiki_page_type_from_article(slug=slug, title=title, wiki_meta=meta):
        return False
    return True


def route_prefix_for_type(page_type: str) -> str:
    return WIKI_ROUTE_PREFIX.get(page_type, "articles")


def is_smoke_slug(slug: str) -> bool:
    return bool(SMOKE_SLUG_RE.search(slug or ""))


def ascii_slug(text: str, *, fallback: str = "page") -> str:
    """只产出 GEOweb 可发布的 ASCII slug；中文标题落到 fallback-hash。

    有汉字且拉丁字母不足 4 个时（如「…-ai-16」），不得把短 latin 当正式 slug。
    """
    raw = (text or "").strip().lower()
    latin = re.sub(r"[^a-z0-9]+", "-", raw)
    latin = re.sub(r"-+", "-", latin).strip("-")[:80]
    has_cjk = bool(re.search(r"[\u4e00-\u9fff]", raw))
    latin_alpha = re.sub(r"[0-9-]+", "", latin)
    if latin and SLUG_RE.fullmatch(latin) and (not has_cjk or len(latin_alpha) >= 4):
        return latin
    digest = hashlib.sha1(raw.encode("utf-8") or b"page").hexdigest()[:10]
    if latin:
        candidate = re.sub(r"-+", "-", f"{latin[:40].strip('-')}-{digest}").strip("-")
        if SLUG_RE.fullmatch(candidate):
            return candidate[:80]
    out = f"{fallback}-{digest}"
    return out if SLUG_RE.fullmatch(out) else fallback


def related_path_for(page_type: str, slug: str) -> str:
    return f"{route_prefix_for_type(page_type)}/{slug}"


def fill_sibling_related(pages: list[dict]) -> list[dict]:
    """同包互链：related 为空时用兄弟页路径补齐。"""
    paths = [
        related_path_for(str(p.get("type") or "concept"), str(p.get("slug") or ""))
        for p in pages
        if p.get("slug")
    ]
    filled: list[dict] = []
    for page in pages:
        slug = str(page.get("slug") or "")
        page_type = str(page.get("type") or "concept")
        own = related_path_for(page_type, slug) if slug else ""
        related = [str(x).strip() for x in (page.get("related") or []) if str(x).strip()]
        for path in paths:
            if path and path != own and path not in related:
                related.append(path)
        next_page = dict(page)
        if related:
            next_page["related"] = related
        filled.append(next_page)
    return filled


def wiki_preview_url(base_url: str, page_type: str, slug: str) -> str:
    base = (base_url or "").rstrip("/")
    prefix = route_prefix_for_type(page_type)
    if not base:
        return f"/{prefix}/{slug}"
    return f"{base}/{prefix}/{slug}"
