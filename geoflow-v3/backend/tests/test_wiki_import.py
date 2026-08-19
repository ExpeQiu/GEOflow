"""GEOweb Wiki markdown 解析单测。"""

from app.services.admin.wiki_import import parse_wiki_markdown, scan_geoweb_wiki_dir, default_geoweb_wiki_dir
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


def test_scan_default_geoweb_dir_if_present():
    root = default_geoweb_wiki_dir()
    if not root.is_dir():
        return
    pages = scan_geoweb_wiki_dir(root, include_smoke=True)
    slugs = {p["slug"] for p in pages}
    assert "g-ads" in slugs
    smoke = [p for p in pages if is_smoke_slug(p["slug"])]
    assert len(smoke) >= 1
    visible = [p for p in pages if not p["smoke"]]
    assert "g-ads" in {p["slug"] for p in visible}
    assert "sync-smoke" not in {p["slug"] for p in visible}
