"""长文章 vs Wiki 误分类过滤单测。"""

from app.services.geoflow.wiki_types import (
    infer_wiki_page_type_from_article,
    is_distribution_article,
)


def test_infer_wiki_type_from_slug_and_title():
    assert infer_wiki_page_type_from_article(slug="ai-concept-74", title="x") == "concept"
    assert infer_wiki_page_type_from_article(slug="x", title="主题 · guide") == "guide"
    assert infer_wiki_page_type_from_article(slug="article-1", title="正常长文") is None


def test_distribution_article_excludes_wiki_pages():
    assert is_distribution_article(
        content_format="article",
        slug="why-odd-matters",
        title="ODD 长文",
        wiki_meta={"type": "article", "geoflow_lane": "distribution"},
    )
    assert not is_distribution_article(
        content_format="article",
        slug="ai-concept-74",
        title="家用纯电 · concept",
        wiki_meta={},
    )
    assert not is_distribution_article(
        content_format="wiki_mdx",
        slug="g-ads",
        title="G-ADS",
        wiki_meta={"type": "concept"},
    )
    assert not is_distribution_article(
        content_format="article",
        slug="long-read",
        title="长文",
        wiki_meta={"geoflow_lane": "wiki"},
    )
