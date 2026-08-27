"""长文章与 GEOweb pages.json 对账（纯函数）。"""

from __future__ import annotations

from typing import Any

from app.services.geoflow.wiki_types import is_smoke_slug


def is_public_geoweb_article_page(page: dict[str, Any]) -> bool:
    """GEOweb 公开 /articles 页（pages.json）。"""
    slug = str(page.get("slug") or "")
    if is_smoke_slug(slug):
        return False
    page_type = str(page.get("type") or page.get("wiki_page_type") or "").strip()
    if page_type != "article":
        return False
    source = str(page.get("source") or "").strip().lower()
    if source == "geoflow":
        lane = str(page.get("geoflow_lane") or page.get("geoflowLane") or "").strip().lower()
        return lane == "distribution"
    return True


def _remote_hash(page: dict[str, Any]) -> str:
    return str(page.get("geoContentHash") or page.get("geo_content_hash") or "").strip()


def _local_hash(article_meta: dict[str, Any]) -> str:
    return str(article_meta.get("geo_content_hash") or "").strip()


def diff_article_inventories(
    local: list[dict[str, Any]],
    remote: list[dict[str, Any]],
) -> dict[str, Any]:
    local_map = {
        str(p["slug"]): p
        for p in local
        if p.get("slug") and not is_smoke_slug(str(p.get("slug") or ""))
    }
    remote_map = {
        str(p["slug"]): p
        for p in remote
        if p.get("slug") and is_public_geoweb_article_page(p)
    }

    matched: list[dict[str, Any]] = []
    hash_mismatch: list[dict[str, Any]] = []
    for slug, loc in local_map.items():
        rem = remote_map.get(slug)
        if rem is None:
            continue
        local_hash = _local_hash(loc.get("wiki_meta") if isinstance(loc.get("wiki_meta"), dict) else {})
        remote_hash = _remote_hash(rem)
        row = {
            "slug": slug,
            "title": loc.get("title") or rem.get("title"),
            "local_hash": local_hash or None,
            "remote_hash": remote_hash or None,
            "url": rem.get("url"),
            "id": loc.get("id"),
        }
        if local_hash and remote_hash and local_hash != remote_hash:
            hash_mismatch.append(row)
        else:
            matched.append(row)

    local_only = [
        {
            "slug": slug,
            "title": page.get("title"),
            "id": page.get("id"),
            "status": page.get("status"),
        }
        for slug, page in local_map.items()
        if slug not in remote_map
    ]
    remote_only = [
        {
            "slug": slug,
            "title": page.get("title"),
            "url": page.get("url"),
            "source": page.get("source"),
        }
        for slug, page in remote_map.items()
        if slug not in local_map
    ]

    return {
        "matched": matched,
        "hash_mismatch": hash_mismatch,
        "local_only": local_only,
        "remote_only": remote_only,
        "stats": {
            "local": len(local_map),
            "remote": len(remote_map),
            "matched": len(matched),
            "hash_mismatch": len(hash_mismatch),
            "local_only": len(local_only),
            "remote_only": len(remote_only),
        },
    }
