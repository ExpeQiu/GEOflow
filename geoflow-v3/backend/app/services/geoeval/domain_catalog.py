"""官方 / 竞品 / 百科域名目录，供 B 轨归属判定。

GEOweb 技术站计入 official（match_type=domain_official），
第三方百科才是 domain_wiki。二者不要混。
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

DEFAULT_WIKI_DOMAINS = (
    "wikipedia.org",
    "baike.baidu.com",
    "wikiwand.com",
)

THIRD_PARTY_HINTS = (
    "dongchedi",
    "autohome",
    "pcauto",
    "yiche",
    "36kr",
    "ithome",
    "zhihu",
    "bilibili",
    "weixin",
    "cirs",
    "中保研",
)

OWNER_OURS = "ours"
OWNER_COMPETITOR = "competitor"
OWNER_THIRD = "third_party"
OWNER_UNKNOWN = "unknown"

# 渠道表列名是 config_json，不是 config / endpoint_url
CHANNEL_HOST_SQL = """
SELECT COALESCE(
    config_json->>'geoweb_base_url',
    config_json->>'endpoint_url',
    config_json->>'domain',
    ''
)
FROM distribution_channels
WHERE channel_type = 'geoweb' AND status = 'active'
LIMIT 10
"""


def host_of(url_or_host: str) -> str:
    raw = (url_or_host or "").strip().lower()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw if "://" in raw else f"https://{raw}")
        host = (parsed.hostname or parsed.netloc or raw).lower()
    except Exception:
        host = raw
    host = host.split(":")[0].removeprefix("www.")
    return host


def split_domains(raw: str | None) -> list[str]:
    if not raw:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for part in str(raw).replace("\n", ",").split(","):
        h = host_of(part.strip())
        if h and h not in seen:
            seen.add(h)
            out.append(h)
    return out


def host_matches(host: str, domains: list[str] | tuple[str, ...]) -> bool:
    h = host_of(host)
    if not h:
        return False
    for d in domains:
        dd = host_of(d)
        if not dd:
            continue
        if h == dd or h.endswith("." + dd):
            return True
    return False


def classify_owner(
    url_or_host: str,
    *,
    official: list[str] | None = None,
    competitors: list[str] | None = None,
    wiki: list[str] | None = None,
) -> str:
    host = host_of(url_or_host)
    if not host:
        return OWNER_UNKNOWN
    if host_matches(host, official or []):
        return OWNER_OURS
    if host_matches(host, competitors or []):
        return OWNER_COMPETITOR
    wiki_domains = list(wiki) if wiki else list(DEFAULT_WIKI_DOMAINS)
    if host_matches(host, wiki_domains):
        return OWNER_THIRD
    if any(h in host or h in (url_or_host or "").lower() for h in THIRD_PARTY_HINTS):
        return OWNER_THIRD
    return OWNER_UNKNOWN


def annotate_urls(
    urls: list[str],
    *,
    official: list[str] | None = None,
    competitors: list[str] | None = None,
    wiki: list[str] | None = None,
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for u in urls:
        url = str(u or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        domain = host_of(url)
        out.append(
            {
                "title": domain,
                "url": url,
                "domain": domain,
                "owner": classify_owner(
                    url, official=official, competitors=competitors, wiki=wiki
                ),
            }
        )
    return out


def _alias_loopback(hosts: list[str]) -> list[str]:
    """开发态 GEOweb（127.0.0.1 / localhost）互认。"""
    extra: list[str] = []
    if any(h in ("127.0.0.1", "localhost", "::1") for h in hosts):
        extra.extend(["127.0.0.1", "localhost"])
    return list(dict.fromkeys([*hosts, *extra]))


async def load_domain_catalog(db: AsyncSession) -> dict[str, Any]:
    """合并 site_settings + GEOWEB_BASE_URL + geoweb 分发渠道。"""
    from app.core.config import get_settings
    from app.services.admin.production_service import _table_exists

    official: list[str] = []
    competitors: list[str] = []
    wiki: list[str] = list(DEFAULT_WIKI_DOMAINS)

    if await _table_exists(db, "site_settings"):
        rows = (
            await db.execute(
                text(
                    """
                    SELECT setting_key, setting_value FROM site_settings
                    WHERE setting_key IN (
                        'official_domains', 'competitor_domains', 'wiki_domains'
                    )
                    """
                )
            )
        ).all()
        for key, value in rows:
            if key == "official_domains":
                official.extend(split_domains(str(value or "")))
            elif key == "competitor_domains":
                competitors.extend(split_domains(str(value or "")))
            elif key == "wiki_domains" and value:
                parsed = split_domains(str(value))
                if parsed:
                    wiki = parsed

    try:
        geoweb = host_of(get_settings().geoweb_base_url or "")
        if geoweb:
            official.append(geoweb)
    except Exception:
        logger.debug("domain_catalog_geoweb_settings_skip", exc_info=True)

    if await _table_exists(db, "distribution_channels"):
        try:
            async with db.begin_nested():
                rows = (await db.execute(text(CHANNEL_HOST_SQL))).all()
            for r in rows:
                h = host_of(str(r[0] or ""))
                if h:
                    official.append(h)
        except Exception:
            logger.debug("domain_catalog_channels_skip", exc_info=True)

    official = _alias_loopback(list(dict.fromkeys(official)))
    competitors = list(dict.fromkeys(competitors))
    wiki = list(dict.fromkeys(wiki))
    logger.info(
        "domain_catalog_loaded official=%s competitors=%s wiki=%s",
        official,
        competitors,
        wiki,
    )
    return {"official": official, "competitor": competitors, "wiki": wiki}
