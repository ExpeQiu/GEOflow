"""GeowebPublisher 页面类型解析单测（不依赖 ORM / pgvector）。"""

from types import SimpleNamespace


def _resolve_page_type(article, config: dict) -> str:
    """与 geoweb_publisher._resolve_page_type 保持同逻辑的轻量副本，避免重依赖导入。"""
    types = {
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
    meta = article.wiki_meta if isinstance(article.wiki_meta, dict) else {}
    if (article.content_format or "article") == "wiki_mdx":
        wiki_type = str(meta.get("type") or meta.get("wiki_page_type") or "concept").strip()
        return wiki_type if wiki_type in types else "concept"
    forced = str(config.get("default_page_type") or config.get("page_type") or "").strip()
    if forced in types:
        return forced
    return "article"


def test_article_format_defaults_to_article():
    article = SimpleNamespace(content_format="article", wiki_meta=None)
    assert _resolve_page_type(article, {}) == "article"


def test_channel_default_page_type_override():
    article = SimpleNamespace(content_format="article", wiki_meta=None)
    assert _resolve_page_type(article, {"default_page_type": "concept"}) == "concept"


def test_wiki_mdx_ignores_channel_default_page_type():
    article = SimpleNamespace(
        content_format="wiki_mdx",
        wiki_meta={"type": "topic"},
    )
    assert _resolve_page_type(article, {"default_page_type": "article"}) == "topic"


def test_wiki_mdx_uses_wiki_page_type():
    article = SimpleNamespace(
        content_format="wiki_mdx",
        wiki_meta={"wiki_page_type": "article"},
    )
    assert _resolve_page_type(article, {}) == "article"


def test_wiki_mdx_certification_type():
    article = SimpleNamespace(
        content_format="wiki_mdx",
        wiki_meta={"wiki_page_type": "certification"},
    )
    assert _resolve_page_type(article, {}) == "certification"


def test_wiki_mdx_invalid_falls_back_to_concept():
    article = SimpleNamespace(
        content_format="wiki_mdx",
        wiki_meta={"wiki_page_type": "unknown"},
    )
    assert _resolve_page_type(article, {}) == "concept"
