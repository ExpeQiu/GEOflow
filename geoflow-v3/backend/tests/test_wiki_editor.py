"""Wiki 轻量编辑台纯函数单测（不依赖 ORM / pgvector）。"""

import re

from fastapi import HTTPException

from app.services.admin.wiki_draft import render_wiki_draft
from app.services.admin.wiki_editor_schema import (
    WikiFaqItem,
    WikiPageBody,
    build_wiki_meta,
    validate_wiki_slug,
    validate_wiki_type,
    wiki_publish_gate,
)
from app.services.admin.wiki_pack import sort_pack_pages
from app.services.admin.wiki_reconcile import (
    diff_wiki_inventories,
    is_geoflow_remote_page,
    is_public_geoweb_wiki_page,
)
from app.services.geoflow.wiki_types import (
    ascii_slug,
    fill_sibling_related,
    is_smoke_slug,
    related_path_for,
    route_prefix_for_type,
    wiki_preview_url,
)


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


def test_ascii_slug_strips_cjk():
    assert ascii_slug("G-ADS 选型") == "g-ads"
    hashed = ascii_slug("家用纯电选型", fallback="theme")
    assert hashed.startswith("theme-")
    assert hashed.replace("-", "").isalnum()
    assert "家" not in hashed
    mixed = ascii_slug("家用纯电选型补齐-ai-决策链内容-16", fallback="theme")
    assert mixed != "ai-16"
    assert "家" not in mixed
    assert re.search(r"[a-z0-9]{6,}", mixed)


def test_fill_sibling_related_completes_pack():
    pages = [
        {"slug": "hub", "type": "topic", "related": []},
        {"slug": "def", "type": "concept"},
        {"slug": "vs", "type": "compare", "related": ["glossary/odd"]},
        {"slug": "howto", "type": "guide"},
    ]
    filled = fill_sibling_related(pages)
    hub_related = filled[0]["related"]
    assert "concepts/def" in hub_related
    assert "compare/vs" in hub_related
    assert "guides/howto" in hub_related
    assert "topics/hub" not in hub_related
    assert "glossary/odd" in filled[2]["related"]


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


def test_related_path_uses_route_prefix():
    assert related_path_for("concept", "g-ads") == "concepts/g-ads"
    assert related_path_for("guide", "npr") == "guides/npr"


def test_publish_gate_skips_concept():
    gate = wiki_publish_gate("concept", [], [])
    assert gate["ok"] is True
    assert gate["required"] is False


def test_publish_gate_blocks_compare_until_related_and_faq():
    blocked = wiki_publish_gate("compare", ["concepts/a"], [{"q": "q1", "a": "a1"}])
    assert blocked["ok"] is False
    assert "related_min_3" in blocked["errors"]
    assert "faq_min_3" in blocked["errors"]

    related = ["concepts/a", "concepts/b", "guides/c"]
    faq = [{"q": "q1", "a": "a1"}, {"q": "q2", "a": "a2"}, {"q": "q3", "a": "a3"}]
    ok = wiki_publish_gate("guide", related, faq)
    assert ok["ok"] is True


def test_pack_sorts_topic_hub_last():
    pages = [
        {"id": 1, "wiki_page_type": "topic"},
        {"id": 2, "wiki_page_type": "guide"},
        {"id": 3, "wiki_page_type": "concept"},
        {"id": 4, "wiki_page_type": "compare"},
    ]
    ordered = sort_pack_pages(pages)
    assert [p["wiki_page_type"] for p in ordered] == ["concept", "compare", "guide", "topic"]


def test_mock_draft_fills_body():
    draft = render_wiki_draft(title="G-ADS", wiki_page_type="concept", hits=[], mock=True)
    assert "G-ADS" in draft["body"]
    assert draft["mock"] is True
    draft2 = render_wiki_draft(
        title="G-ADS",
        wiki_page_type="concept",
        hits=[{"content": "吉利智能驾驶辅助系统"}],
        mock=True,
    )
    assert "吉利智能驾驶辅助系统" in draft2["body"]
    assert draft2["hit_count"] == 1


def test_reconcile_uses_public_geoweb_wiki_pages():
    local = [
        {"slug": "g-ads", "title": "G-ADS", "wiki_page_type": "concept", "id": 1, "geo_content_hash": "aaa"},
        {"slug": "local-only", "title": "仅本地", "wiki_page_type": "concept", "id": 2},
        {"slug": "gads-smoke-check", "title": "探针", "wiki_page_type": "concept", "id": 3},
    ]
    remote = [
        {"slug": "g-ads", "title": "G-ADS", "type": "concept", "source": "seed", "geoContentHash": "aaa"},
        {"slug": "seed-page", "title": "种子", "type": "concept", "source": "seed"},
        {"slug": "remote-only", "title": "仅远端", "type": "concept", "source": "seed"},
        {"slug": "geoflow-junk", "title": "junk", "type": "concept", "source": "geoflow"},
        {"slug": "wiki-probe-1", "title": "探针", "type": "concept", "source": "geoflow"},
        {"slug": "long-article", "title": "长文", "type": "article", "source": "seed"},
    ]
    assert is_public_geoweb_wiki_page(remote[0]) is True
    assert is_public_geoweb_wiki_page(remote[3]) is False
    assert is_public_geoweb_wiki_page(remote[5]) is False
    assert is_geoflow_remote_page(remote[3]) is True
    diff = diff_wiki_inventories(local, remote)
    assert [r["slug"] for r in diff["matched"]] == ["g-ads"]
    assert [r["slug"] for r in diff["local_only"]] == ["local-only"]
    assert sorted(r["slug"] for r in diff["remote_only"]) == ["remote-only", "seed-page"]
    assert diff["stats"]["remote"] == 3
