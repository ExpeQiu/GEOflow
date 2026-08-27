"""GEOweb Wiki markdown 解析单测。"""

from app.services.admin.wiki_import import (
    is_geoweb_aligned_wiki_record,
    is_official_geoweb_wiki_page,
    load_official_geoweb_wiki_slugs,
    parse_wiki_markdown,
    scan_geoweb_wiki_dir,
    default_geoweb_wiki_dir,
)
from app.services.geoflow.wiki_types import is_smoke_slug


SAMPLE = """---
title: "G-ADS 千里浩瀚"
slug: "g-ads"
type: concept
domain: adas
related:
  - "concepts/smart-cockpit"
faq:
  - q: "G-ADS 是 L2 还是 L3？"
    a: "以车型公开标定为准。"
---

## 定义

正文
"""


def test_parse_wiki_markdown_frontmatter():
    page = parse_wiki_markdown(SAMPLE, "g-ads", "concepts")
    assert page is not None
    assert page["slug"] == "g-ads"
    assert page["wiki_page_type"] == "concept"
    assert page["domain"] == "adas"
    assert page["related"] == ["concepts/smart-cockpit"]
    assert page["faq"][0]["q"].startswith("G-ADS")
    assert page["body"].startswith("## 定义")


def test_official_geoweb_wiki_page_filter():
    assert is_official_geoweb_wiki_page({"source": "seed", "wiki_page_type": "concept"}) is True
    assert is_official_geoweb_wiki_page({"source": "geoflow", "wiki_page_type": "concept"}) is False
    assert is_official_geoweb_wiki_page({"source": "seed", "wiki_page_type": "article"}) is False


def test_scan_official_only_excludes_geoflow(tmp_path):
    wiki = tmp_path / "wiki"
    (wiki / "concepts").mkdir(parents=True)
    (wiki / "concepts" / "g-ads.md").write_text(SAMPLE, encoding="utf-8")
    geoflow_sample = SAMPLE.replace('slug: "g-ads"', 'slug: "ai-concept-1"').replace(
        'type: concept', 'type: concept\nsource: geoflow'
    )
    (wiki / "concepts" / "ai-concept-1.md").write_text(geoflow_sample, encoding="utf-8")
    all_pages = scan_geoweb_wiki_dir(wiki, include_smoke=True, official_only=False)
    official = scan_geoweb_wiki_dir(wiki, include_smoke=True, official_only=True)
    assert {p["slug"] for p in all_pages} == {"g-ads", "ai-concept-1"}
    assert {p["slug"] for p in official} == {"g-ads"}


def test_geoweb_aligned_wiki_record():
    official = {"g-ads", "odd"}
    assert is_geoweb_aligned_wiki_record(
        content_format="wiki_mdx",
        slug="g-ads",
        wiki_meta={"type": "concept", "slug": "g-ads"},
        official_slugs=official,
    )
    assert not is_geoweb_aligned_wiki_record(
        content_format="wiki_mdx",
        slug="ai-concept-74",
        wiki_meta={"type": "concept"},
        official_slugs=official,
    )
    assert not is_geoweb_aligned_wiki_record(
        content_format="wiki_mdx",
        slug="g-ads",
        wiki_meta={"type": "article", "slug": "g-ads"},
        official_slugs=official,
    )


def test_load_official_geoweb_wiki_slugs_if_present():
    slugs = load_official_geoweb_wiki_slugs()
    if not slugs:
        return
    assert "g-ads" in slugs
    assert len(slugs) >= 40


def test_scan_default_geoweb_dir_if_present():
    root = default_geoweb_wiki_dir()
    if not root.is_dir():
        return
    pages = scan_geoweb_wiki_dir(root, include_smoke=True, official_only=True)
    slugs = {p["slug"] for p in pages}
    assert "g-ads" in slugs
    assert len(slugs) >= 40
    visible = [p for p in pages if not p["smoke"]]
    assert "g-ads" in {p["slug"] for p in visible}
