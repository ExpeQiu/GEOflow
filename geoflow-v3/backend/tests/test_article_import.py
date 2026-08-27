"""GEOweb 长文章 markdown 解析与过滤单测。"""

from app.services.admin.article_import import (
    is_official_geoweb_article_page,
    scan_geoweb_articles_dir,
    default_geoweb_articles_dir,
)
from app.services.admin.article_reconcile import diff_article_inventories, is_public_geoweb_article_page
from app.services.admin.wiki_import import default_geoweb_wiki_dir


ARTICLE_SAMPLE = """---
title: "为什么必须看 ODD"
slug: "why-odd-matters-for-adas-buyers"
type: article
domain: adas
source: seed
quick_answer: "买智驾先看 ODD"
core_takeaway: "ODD 决定能不能用"
target_query: "买车怎么判断智驾"
tags: [article, adas]
related:
  - "concepts/g-ads"
faq:
  - q: "和概念页区别？"
    a: "长文展开决策语境。"
---

## 开篇

正文
"""


def test_official_geoweb_article_page_filter():
    assert is_official_geoweb_article_page({"wiki_page_type": "article", "source": "seed"}) is True
    assert is_official_geoweb_article_page({"wiki_page_type": "article", "source": "geoflow"}) is False
    assert is_official_geoweb_article_page({"wiki_page_type": "concept", "source": "seed"}) is False


def test_scan_official_only_excludes_geoflow_articles(tmp_path):
    wiki = tmp_path / "wiki"
    articles = wiki / "articles"
    articles.mkdir(parents=True)
    (articles / "why-odd.md").write_text(ARTICLE_SAMPLE, encoding="utf-8")
    geoflow = ARTICLE_SAMPLE.replace('source: seed', 'source: geoflow').replace(
        'slug: "why-odd-matters-for-adas-buyers"', 'slug: "ai-article-36"'
    )
    (articles / "ai-article-36.md").write_text(geoflow, encoding="utf-8")
    all_pages = scan_geoweb_articles_dir(wiki, include_smoke=True, official_only=False)
    official = scan_geoweb_articles_dir(wiki, include_smoke=True, official_only=True)
    assert {p["slug"] for p in all_pages} == {"why-odd-matters-for-adas-buyers", "ai-article-36"}
    assert {p["slug"] for p in official} == {"why-odd-matters-for-adas-buyers"}


def test_reconcile_public_geoweb_articles():
    local = [
        {"id": 1, "slug": "why-odd", "title": "ODD", "wiki_meta": {"geo_content_hash": "aaa"}},
        {"id": 2, "slug": "local-only", "title": "仅本地", "wiki_meta": {}},
    ]
    remote = [
        {"slug": "why-odd", "title": "ODD", "type": "article", "source": "seed", "geoContentHash": "aaa"},
        {"slug": "remote-only", "title": "仅远端", "type": "article", "source": "seed"},
        {"slug": "wiki-page", "title": "概念", "type": "concept", "source": "seed"},
        {"slug": "geoflow-hidden", "title": "隐藏", "type": "article", "source": "geoflow"},
    ]
    assert is_public_geoweb_article_page(remote[0]) is True
    assert is_public_geoweb_article_page(remote[2]) is False
    assert is_public_geoweb_article_page(remote[3]) is False
    diff = diff_article_inventories(local, remote)
    assert [r["slug"] for r in diff["matched"]] == ["why-odd"]
    assert [r["slug"] for r in diff["local_only"]] == ["local-only"]
    assert [r["slug"] for r in diff["remote_only"]] == ["remote-only"]
    assert diff["stats"]["remote"] == 2


def test_scan_default_geoweb_articles_dir_if_present():
    root = default_geoweb_articles_dir()
    assert root == default_geoweb_wiki_dir()
    if not (root / "articles").is_dir():
        return
    pages = scan_geoweb_articles_dir(root, official_only=True)
    slugs = {p["slug"] for p in pages}
    assert "why-odd-matters-for-adas-buyers" in slugs
