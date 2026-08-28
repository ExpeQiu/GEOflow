"""从 GEOweb content/wiki/articles 拉回长文章到编辑台（解析层可单测）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.admin.article_reconcile import is_public_geoweb_article_page
from app.services.admin.wiki_import import default_geoweb_wiki_dir, parse_wiki_markdown
from app.services.geoflow.wiki_types import is_smoke_slug


def is_official_geoweb_article_page(parsed: dict[str, Any]) -> bool:
    """GEOweb /articles 官方 seed：type=article 且非 GEOFlow 同步页。"""
    if str(parsed.get("wiki_page_type") or "").strip() != "article":
        return False
    if str(parsed.get("source") or "").strip().lower() == "geoflow":
        return False
    return True


def is_public_geoweb_article_from_disk(parsed: dict[str, Any]) -> bool:
    """与 GEOweb catalog.isPublicArticlePage / pages.json 一致。"""
    if parsed.get("geo_publish") is False:
        return False
    return is_public_geoweb_article_page(
        {
            "slug": parsed.get("slug"),
            "type": parsed.get("wiki_page_type"),
            "wiki_page_type": parsed.get("wiki_page_type"),
            "source": parsed.get("source"),
            "geoflow_lane": parsed.get("geoflow_lane"),
            "geoflowLane": parsed.get("geoflow_lane"),
        }
    )


def scan_geoweb_articles_dir(
    wiki_dir: Path,
    include_smoke: bool = False,
    *,
    official_only: bool = False,
    public_only: bool = False,
) -> list[dict[str, Any]]:
    articles_dir = wiki_dir / "articles"
    pages: list[dict[str, Any]] = []
    if not articles_dir.is_dir():
        return pages
    for path in [*sorted(articles_dir.glob("*.md")), *sorted(articles_dir.glob("*.mdx"))]:
        if path.name.startswith("._"):
            continue
        parsed = parse_wiki_markdown(path.read_text(encoding="utf-8"), path.stem, "articles")
        if parsed is None:
            continue
        if official_only and not is_official_geoweb_article_page(parsed):
            continue
        if public_only and not is_public_geoweb_article_from_disk(parsed):
            continue
        parsed["smoke"] = is_smoke_slug(parsed["slug"])
        if parsed.get("smoke") and not include_smoke:
            continue
        pages.append(parsed)
    return pages


def default_geoweb_articles_dir() -> Path:
    return default_geoweb_wiki_dir()
