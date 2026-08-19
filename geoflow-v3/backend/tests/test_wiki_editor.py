"""Wiki 轻量编辑台纯函数单测（不依赖 ORM / pgvector）。"""

from fastapi import HTTPException

from app.services.admin.wiki_editor_schema import (
    WikiFaqItem,
    WikiPageBody,
    build_wiki_meta,
    validate_wiki_slug,
    validate_wiki_type,
)
from app.services.geoflow.wiki_types import is_smoke_slug, route_prefix_for_type, wiki_preview_url


def test_smoke_slug_filters_probe_pages():
    assert is_smoke_slug("gads-smoke-check")
    assert is_smoke_slug("wiki-probe-1")
    assert is_smoke_slug("interop-roundtrip")
    assert not is_smoke_slug("g-ads")


def test_wiki_slug_validation():
    assert validate_wiki_slug("G-ADS") == "g-ads"
    try:
        validate_wiki_slug("雷神混动")
        assert False, "expected invalid slug"
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail == "wiki_slug_invalid"


def test_wiki_type_validation():
    assert validate_wiki_type("concept") == "concept"
    try:
        validate_wiki_type("map-node")
        assert False, "expected invalid type"
    except HTTPException as exc:
        assert exc.status_code == 422


def test_preview_url_uses_type_route():
    url = wiki_preview_url("http://127.0.0.1:3070", "concept", "g-ads")
    assert url == "http://127.0.0.1:3070/concepts/g-ads"
    assert route_prefix_for_type("guide") == "guides"


def test_build_wiki_meta_keeps_sync_fields():
    existing = {"geo_content_hash": "abc", "geoweb_url": "http://127.0.0.1:3070/concepts/g-ads"}
    body = WikiPageBody(
        title="G-ADS",
        slug="g-ads",
        wiki_page_type="concept",
        body="## 概述",
        domain="adas",
        quick_answer="吉利智能驾驶辅助系统",
        related=["concepts/npr", "guides/g-ads"],
        faq=[WikiFaqItem(q="是什么", a="智能驾驶辅助")],
    )
    meta = build_wiki_meta(existing, body, "concept", "g-ads")
    assert meta["wiki_page_type"] == "concept"
    assert meta["type"] == "concept"
    assert meta["slug"] == "g-ads"
    assert meta["geo_content_hash"] == "abc"
    assert meta["geoweb_url"].endswith("/concepts/g-ads")
    assert meta["faq"][0]["q"] == "是什么"
