"""Wiki 与 GEOweb pages.json 对账（纯函数）。"""

from __future__ import annotations

from typing import Any

from app.services.geoflow.wiki_types import is_smoke_slug


def is_geoflow_remote_page(page: dict[str, Any]) -> bool:
    """@deprecated 使用 is_public_geoweb_wiki_page。"""
    slug = str(page.get("slug") or "")
    if is_smoke_slug(slug):
        return False
    source = str(page.get("source") or "").strip().lower()
    if source == "geoflow":
        return True
    if source:
        return False
    return bool(
        page.get("geoContentHash")
        or page.get("geo_content_hash")
        or page.get("geoFlowTask")
        or page.get("geo_flow_task")
    )


def is_public_geoweb_wiki_page(page: dict[str, Any]) -> bool:
    """GEOweb 公开 Wiki 板块页（pages.json），不含 /articles 与 GEOFlow 管线页。"""
    slug = str(page.get("slug") or "")
    if is_smoke_slug(slug):
        return False
    page_type = str(page.get("type") or page.get("wiki_page_type") or "").strip()
    if page_type == "article":
        return False
    source = str(page.get("source") or "").strip().lower()
    if source == "geoflow":
        lane = str(page.get("geoflow_lane") or page.get("geoflowLane") or "").strip().lower()
        return lane == "wiki"
    return True


def _remote_hash(page: dict[str, Any]) -> str:
    return str(page.get("geoContentHash") or page.get("geo_content_hash") or "").strip()


def diff_wiki_inventories(
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
        if p.get("slug") and is_public_geoweb_wiki_page(p)
    }

    matched: list[dict[str, Any]] = []
    hash_mismatch: list[dict[str, Any]] = []
    for slug, loc in local_map.items():
        rem = remote_map.get(slug)
        if rem is None:
            continue
        local_hash = str(loc.get("geo_content_hash") or "").strip()
        remote_hash = _remote_hash(rem)
        row = {
            "slug": slug,
            "title": loc.get("title") or rem.get("title"),
            "wiki_page_type": loc.get("wiki_page_type") or rem.get("type"),
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
            "wiki_page_type": page.get("wiki_page_type"),
            "id": page.get("id"),
            "synced": bool(page.get("synced")),
        }
        for slug, page in local_map.items()
        if slug not in remote_map
    ]
    remote_only = [
        {
            "slug": slug,
            "title": page.get("title"),
            "wiki_page_type": page.get("type"),
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
