"""信源层指标：官方/第三方占比与目标域名命中。"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

OFFICIAL_HINTS = (
    "geely",
    "lynk",
    "zeekr",
    "gweb",
    "wiki",
    "faq",
    "ai-facts",
    "datahub",
    "whitepaper",
    "白皮书",
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
    "中保研",
    "cirs",
)


def classify_domain(url_or_domain: str, target_domains: list[str] | None = None) -> str:
    raw = (url_or_domain or "").strip().lower()
    try:
        host = urlparse(raw if "://" in raw else f"https://{raw}").netloc or raw
    except Exception:
        host = raw
    host = host.removeprefix("www.")
    targets = [t.lower().removeprefix("www.") for t in (target_domains or []) if t]
    if any(t and t in host for t in targets):
        return "official"
    if any(h in host or h in raw for h in OFFICIAL_HINTS):
        return "official"
    if any(h in host or h in raw for h in THIRD_PARTY_HINTS):
        return "third_party"
    return "other"


async def _load_target_domains(db: AsyncSession) -> list[str]:
    from app.services.geoeval.domain_catalog import load_domain_catalog

    catalog = await load_domain_catalog(db)
    return list(catalog.get("official") or [])


async def compute_source_shares(db: AsyncSession, *, min_evidence_level: str = "L1") -> dict:
    """从探针 citations / 分发 citation cache 聚合信源结构。"""
    from app.services.admin.production_service import _table_exists

    targets = await _load_target_domains(db)
    urls: list[str] = []
    evidence_ok = 0
    evidence_total = 0

    if await _table_exists(db, "geo_monitor_probe_citations"):
        try:
            rows = (
                await db.execute(
                    text(
                        """
                        SELECT url, COALESCE(evidence_level, 'L0')
                        FROM geo_monitor_probe_citations
                        ORDER BY id DESC
                        LIMIT 500
                        """
                    )
                )
            ).all()
            for url, level in rows:
                evidence_total += 1
                if str(level) >= min_evidence_level or str(level) in ("L1", "L2", "L3"):
                    if min_evidence_level == "L0" or str(level) != "L0":
                        evidence_ok += 1
                        if url:
                            urls.append(str(url))
                elif min_evidence_level == "L0" and url:
                    urls.append(str(url))
        except Exception:
            logger.debug("probe_citations_query_failed", exc_info=True)

    if not urls and await _table_exists(db, "distribution_citation_index"):
        try:
            rows = (
                await db.execute(
                    text(
                        """
                        SELECT primary_url, citations_json
                        FROM distribution_citation_index
                        ORDER BY id DESC LIMIT 100
                        """
                    )
                )
            ).all()
            for primary, citations in rows:
                if primary:
                    urls.append(str(primary))
                if isinstance(citations, list):
                    for c in citations:
                        if isinstance(c, dict) and c.get("url"):
                            urls.append(str(c["url"]))
                        elif isinstance(c, str):
                            urls.append(c)
        except Exception:
            logger.debug("distribution_citations_query_failed", exc_info=True)

    counts = {"official": 0, "third_party": 0, "other": 0}
    target_hits = 0
    for u in urls:
        kind = classify_domain(u, targets)
        counts[kind] = counts.get(kind, 0) + 1
        if kind == "official":
            target_hits += 1

    total = sum(counts.values()) or 0
    official_share = round(counts["official"] / total * 100, 1) if total else None
    third_share = round(counts["third_party"] / total * 100, 1) if total else None
    result = {
        "official_share_pct": official_share,
        "third_party_share_pct": third_share,
        "target_domain_hits": target_hits,
        "citation_count": total,
        "evidence_filtered": evidence_ok,
        "evidence_total": evidence_total,
        "target_domains": targets,
        "kpi_track": "open_api",
    }
    logger.info(
        "source_shares_computed official=%s third=%s hits=%s n=%s",
        official_share,
        third_share,
        target_hits,
        total,
    )
    return result
