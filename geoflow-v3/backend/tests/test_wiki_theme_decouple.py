"""Wiki / Theme 解耦：Theme 包 → 长文章；Wiki 编辑台排除 Theme 产出。"""

from app.services.geoflow.wiki_types import (
    is_editable_wiki_panel_record,
    is_theme_pack_wiki_record,
    is_wiki_mdx_pollution,
)


def test_theme_pack_wiki_by_theme_id():
    assert is_theme_pack_wiki_record(theme_id=19, slug="g-ads", title="G-ADS") is True


def test_theme_pack_wiki_by_title_suffix():
    assert is_theme_pack_wiki_record(
        theme_id=None,
        slug="ai-concept-13",
        title="家用纯电选型：补齐 AI 决策链内容 · concept",
    )


def test_manual_wiki_not_theme_pack():
    assert is_theme_pack_wiki_record(theme_id=None, slug="g-ads", title="G-ADS 千里浩瀚") is False


def test_editable_wiki_tech_brand_mode_excludes_theme():
    assert (
        is_editable_wiki_panel_record(
            content_format="wiki_mdx",
            theme_id=19,
            slug="g-ads",
            title="G-ADS",
            wiki_meta={"type": "concept"},
            official_slugs={"g-ads"},
            tech_brand_mode=True,
        )
        is False
    )


def test_editable_wiki_tech_brand_mode_includes_manual():
    assert (
        is_editable_wiki_panel_record(
            content_format="wiki_mdx",
            theme_id=None,
            slug="my-new-concept",
            title="新建概念页",
            wiki_meta={"type": "concept"},
            official_slugs=set(),
            tech_brand_mode=True,
        )
        is True
    )


def test_editable_wiki_legacy_requires_official_slug():
    assert (
        is_editable_wiki_panel_record(
            content_format="wiki_mdx",
            theme_id=None,
            slug="my-new-concept",
            title="新建概念页",
            wiki_meta={"type": "concept", "slug": "my-new-concept"},
            official_slugs={"g-ads"},
            tech_brand_mode=False,
        )
        is False
    )
    assert (
        is_editable_wiki_panel_record(
            content_format="wiki_mdx",
            theme_id=None,
            slug="g-ads",
            title="G-ADS",
            wiki_meta={"type": "concept", "slug": "g-ads"},
            official_slugs={"g-ads"},
            tech_brand_mode=False,
        )
        is True
    )


def test_wiki_mdx_pollution_distribution_slug():
    assert is_wiki_mdx_pollution(slug="l7-8ab53fa87e-555", title="L7 续航", wiki_meta={"type": "concept"}) is True
    assert is_wiki_mdx_pollution(slug="article-504e3a4231-542", title="对比决策", wiki_meta={"type": "concept"}) is True
    assert is_wiki_mdx_pollution(slug="g-ads", title="G-ADS", wiki_meta={"type": "concept", "geoflow_lane": "wiki"}) is False


def test_editable_wiki_tech_brand_excludes_distribution_pollution():
    assert (
        is_editable_wiki_panel_record(
            content_format="wiki_mdx",
            theme_id=None,
            slug="l7-8ab53fa87e-555",
            title="在家用纯电选型场景，关于「吉利银河 L7 续航和空间适合家庭吗」",
            wiki_meta={"type": "concept", "wiki_page_type": "concept"},
            official_slugs=set(),
            tech_brand_mode=True,
        )
        is False
    )
    assert (
        is_editable_wiki_panel_record(
            content_format="wiki_mdx",
            theme_id=None,
            slug="perception-stack",
            title="感知栈",
            wiki_meta={"type": "concept", "geoflow_lane": "wiki"},
            official_slugs={"perception-stack"},
            tech_brand_mode=True,
        )
        is True
    )
