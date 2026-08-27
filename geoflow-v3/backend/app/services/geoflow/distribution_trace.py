"""分发追踪链接 — GEOweb canonical URL + 渠道可追溯后缀。"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qsl

GEOWEB_CHANNEL_TYPE = "geoweb"
EXTERNAL_CHANNEL_TYPES = ("geoflow_agent", "wordpress_rest", "generic_http_api")

DEFAULT_LINK_TEMPLATE = (
    "?utm_source={channel_slug}&utm_medium=distribution"
    "&utm_campaign={theme_id}&geo_task={task_id}&geo_dist={dist_id}&geo_article={article_id}"
)


def is_geoweb_channel(channel_type: str) -> bool:
    return channel_type == GEOWEB_CHANNEL_TYPE


def is_external_channel(channel_type: str) -> bool:
    return channel_type in EXTERNAL_CHANNEL_TYPES


def _channel_cfg(channel: Any) -> dict:
    raw = getattr(channel, "config_json", None)
    return raw if isinstance(raw, dict) else {}


def channel_slug(channel: Any) -> str:
    cfg = _channel_cfg(channel)
    raw = str(cfg.get("channel_slug") or cfg.get("domain") or getattr(channel, "name", "") or f"ch{channel.id}")
    slug = re.sub(r"[^\w\-]", "-", raw.lower()).strip("-")
    return slug[:40] or f"ch{getattr(channel, 'id', 0)}"


def trace_enabled(config: dict[str, Any]) -> bool:
    mode = str(config.get("trace_mode") or "suffix").lower()
    return mode not in ("off", "none", "disabled")


def require_geoweb_first(config: dict[str, Any], channel_type: str) -> bool:
    if is_geoweb_channel(channel_type):
        return False
    if config.get("require_geoweb_first") is False:
        return False
    return True


def get_link_template(config: dict[str, Any]) -> str:
    template = str(config.get("link_template") or DEFAULT_LINK_TEMPLATE).strip()
    return template or DEFAULT_LINK_TEMPLATE


def build_trace_params(*, article: Any, channel: Any, dist_id: int) -> dict[str, str]:
    return {
        "channel_slug": channel_slug(channel),
        "task_id": str(getattr(article, "task_id", None) or getattr(article, "id", "")),
        "dist_id": str(dist_id),
        "article_id": str(getattr(article, "id", "")),
        "theme_id": str(getattr(article, "theme_id", None) or ""),
    }


def render_link_template(template: str, params: dict[str, str]) -> str:
    rendered = template
    for key, val in params.items():
        rendered = rendered.replace("{" + key + "}", val)
    return rendered


def build_tracked_url(canonical_url: str, suffix: str) -> str:
    base = (canonical_url or "").strip()
    if not base:
        return ""
    tail = (suffix or "").strip()
    if not tail:
        return base
    if tail.startswith("?"):
        clean_base = base.split("?", 1)[0]
        return f"{clean_base}{tail}"
    if tail.startswith("&"):
        return f"{base}{tail}"
    return f"{base}?{tail.lstrip('?')}"


def parse_trace_suffix(suffix: str) -> dict[str, str]:
    qs = (suffix or "").lstrip("?&")
    if not qs:
        return {}
    return dict(parse_qsl(qs, keep_blank_values=True))


def resolve_canonical_from_article(article: Any) -> str | None:
    meta = article.wiki_meta if isinstance(getattr(article, "wiki_meta", None), dict) else {}
    url = str(meta.get("geoweb_url") or meta.get("remote_url") or "").strip()
    return url or None


def build_external_tracked_url(
    *,
    article: Any,
    channel: Any,
    dist_id: int,
    canonical_url: str,
) -> tuple[str, dict[str, str]]:
    cfg = _channel_cfg(channel)
    params = build_trace_params(article=article, channel=channel, dist_id=dist_id)
    suffix = render_link_template(get_link_template(cfg), params)
    tracked = build_tracked_url(canonical_url, suffix)
    trace_snapshot = {**params, **parse_trace_suffix(suffix)}
    return tracked, trace_snapshot


def sort_channels_for_distribution(channels: list[Any]) -> list[Any]:
    """GEOweb 主站优先，外渠在后。"""

    def _key(ch: Any) -> tuple[int, int]:
        if is_geoweb_channel(getattr(ch, "channel_type", "")):
            return (0, int(getattr(ch, "id", 0)))
        return (1, int(getattr(ch, "id", 0)))

    return sorted(channels, key=_key)
