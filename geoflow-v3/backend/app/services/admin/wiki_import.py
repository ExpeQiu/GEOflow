"""从 GEOweb content/wiki 拉回 Wiki 页到编辑台（无 ORM 的解析部分可单测）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.services.geoflow.wiki_types import GEOWEB_PAGE_TYPES, WIKI_ROUTE_PREFIX, is_smoke_slug, route_prefix_for_type

_ROUTE_TO_TYPE = {prefix: page_type for page_type, prefix in WIKI_ROUTE_PREFIX.items()}


def default_geoweb_wiki_dir() -> Path:
    import os

    env = (os.environ.get("GEOWEB_WIKI_DIR") or "").strip()
    if env:
        return Path(env)
    # geoflow-v3/backend/app/services/admin → 03T/GEOweb/content/wiki
    return Path(__file__).resolve().parents[5].parent / "GEOweb" / "content" / "wiki"


def parse_wiki_markdown(raw: str, fallback_slug: str, route_prefix: str) -> dict[str, Any] | None:
    fm: dict[str, Any] = {}
    body = raw.strip()
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            loaded = yaml.safe_load(parts[1]) or {}
            if isinstance(loaded, dict):
                fm = loaded
            body = parts[2].strip()
    slug = str(fm.get("slug") or fallback_slug).strip()
    page_type = str(fm.get("type") or _ROUTE_TO_TYPE.get(route_prefix) or "").strip()
    if page_type not in GEOWEB_PAGE_TYPES:
        return None
    if not slug or not body:
        return None
    faq_raw = fm.get("faq") if isinstance(fm.get("faq"), list) else []
    faq: list[dict[str, str]] = []
    for item in faq_raw:
        if not isinstance(item, dict):
            continue
        q = str(item.get("q") or item.get("question") or "").strip()
        a = str(item.get("a") or item.get("answer") or "").strip()
        if q and a:
            faq.append({"q": q, "a": a})
    related = fm.get("related") if isinstance(fm.get("related"), list) else []
    tags = fm.get("tags") if isinstance(fm.get("tags"), list) else []
    return {
        "title": str(fm.get("title") or slug).strip(),
        "slug": slug,
        "wiki_page_type": page_type,
        "body": body,
        "domain": str(fm.get("domain") or "").strip(),
        "quick_answer": str(fm.get("quick_answer") or "").strip(),
        "core_takeaway": str(fm.get("core_takeaway") or "").strip(),
        "target_query": str(fm.get("target_query") or "").strip(),
        "related": [str(x).strip() for x in related if str(x).strip()],
        "faq": faq,
        "schema_type": str(fm.get("schema_type") or "TechArticle").strip() or "TechArticle",
        "geo_theme_id": str(fm.get("geo_theme_id") or "").strip() or None,
        "tags": [str(x).strip() for x in tags if str(x).strip()],
        "geo_content_hash": str(fm.get("geo_content_hash") or "").strip() or None,
        "source": str(fm.get("source") or "").strip() or None,
        "route_prefix": route_prefix_for_type(page_type),
    }


def scan_geoweb_wiki_dir(wiki_dir: Path, include_smoke: bool = False) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    if not wiki_dir.is_dir():
        return pages
    for prefix_dir in sorted(wiki_dir.iterdir()):
        if not prefix_dir.is_dir() or prefix_dir.name.startswith("."):
            continue
        route_prefix = prefix_dir.name
        files = [*sorted(prefix_dir.glob("*.md")), *sorted(prefix_dir.glob("*.mdx"))]
        for path in files:
            if path.name.startswith("._"):
                continue
            parsed = parse_wiki_markdown(path.read_text(encoding="utf-8"), path.stem, route_prefix)
            if parsed is None:
                continue
            parsed["smoke"] = is_smoke_slug(parsed["slug"])
            pages.append(parsed)
    return pages
