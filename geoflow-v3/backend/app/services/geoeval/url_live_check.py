"""B 轨答文 URL 存活核验（HEAD，失败再 GET）。不替代原生搜索。"""

from __future__ import annotations

import asyncio
import logging
import os

import httpx

logger = logging.getLogger(__name__)

LIVE = "live"
DEAD = "dead"
SKIPPED = "skipped"

_DEFAULT_TIMEOUT = 4.0
_DEFAULT_LIMIT = 8


def _live_check_enabled() -> bool:
    raw = os.getenv("CITATION_LIVE_CHECK", "true").lower()
    return raw not in ("0", "false", "no", "off")


async def _one(client: httpx.AsyncClient, url: str) -> str:
    try:
        resp = await client.head(url)
        if resp.status_code in (405, 501) or resp.status_code >= 400:
            resp = await client.get(url)
        code = resp.status_code
        if 200 <= code < 400 or code in (401, 403, 429):
            return LIVE
        return DEAD
    except Exception as exc:
        logger.info("url_live_check_fail url=%s error=%s", url[:120], type(exc).__name__)
        return DEAD


async def classify_url_liveness(
    urls: list[str],
    *,
    timeout: float = _DEFAULT_TIMEOUT,
    limit: int = _DEFAULT_LIMIT,
) -> dict[str, str]:
    """url → live | dead | skipped。"""
    out: dict[str, str] = {}
    uniq: list[str] = []
    seen: set[str] = set()
    for raw in urls:
        u = str(raw or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        uniq.append(u)
    if not uniq:
        return out
    if not _live_check_enabled():
        return {u: SKIPPED for u in uniq[:limit]}

    capped = uniq[: max(1, limit)]
    timeout_cfg = httpx.Timeout(timeout, connect=min(2.0, timeout))
    async with httpx.AsyncClient(timeout=timeout_cfg, follow_redirects=True, headers={"User-Agent": "GEOFlow-citation-check/1"}) as client:
        results = await asyncio.gather(*[_one(client, u) for u in capped], return_exceptions=True)
    for url, res in zip(capped, results, strict=True):
        out[url] = DEAD if isinstance(res, Exception) else str(res)
    for extra in uniq[len(capped) :]:
        out[extra] = SKIPPED
    live_n = sum(1 for v in out.values() if v == LIVE)
    logger.info("url_live_check_done total=%s live=%s dead=%s", len(out), live_n, sum(1 for v in out.values() if v == DEAD))
    return out
