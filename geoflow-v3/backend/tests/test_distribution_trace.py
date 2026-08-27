"""分发追踪链接单元测试。"""

from types import SimpleNamespace

from app.services.geoflow.distribution_trace import (
    build_external_tracked_url,
    build_tracked_url,
    channel_slug,
    render_link_template,
    sort_channels_for_distribution,
)


def test_build_tracked_url_appends_suffix():
    url = build_tracked_url(
        "http://127.0.0.1:3070/articles/demo-slug",
        "?utm_source=weibo&geo_task=42",
    )
    assert url == "http://127.0.0.1:3070/articles/demo-slug?utm_source=weibo&geo_task=42"


def test_render_link_template_replaces_placeholders():
    rendered = render_link_template(
        "?utm_source={channel_slug}&geo_dist={dist_id}",
        {"channel_slug": "weibo", "dist_id": "99"},
    )
    assert rendered == "?utm_source=weibo&geo_dist=99"


def test_build_external_tracked_url():
    article = SimpleNamespace(id=7, task_id=3, theme_id=11)
    channel = SimpleNamespace(
        id=2,
        name="Weibo Matrix",
        config_json={"channel_slug": "weibo", "link_template": "?utm_source={channel_slug}&geo_dist={dist_id}"},
    )
    tracked, params = build_external_tracked_url(
        article=article,
        channel=channel,
        dist_id=99,
        canonical_url="http://127.0.0.1:3070/articles/demo",
    )
    assert tracked.startswith("http://127.0.0.1:3070/articles/demo?")
    assert params["channel_slug"] == "weibo"
    assert params["dist_id"] == "99"


def test_sort_channels_geoweb_first():
    geoweb = SimpleNamespace(id=2, channel_type="geoweb")
    external = SimpleNamespace(id=1, channel_type="wordpress_rest")
    ordered = sort_channels_for_distribution([external, geoweb])
    assert [c.id for c in ordered] == [2, 1]


def test_channel_slug_sanitizes_name():
    channel = SimpleNamespace(id=5, name="Weibo Matrix", config_json={})
    assert channel_slug(channel) == "weibo-matrix"
