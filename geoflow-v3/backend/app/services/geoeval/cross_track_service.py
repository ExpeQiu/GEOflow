"""A∩C / B∩C 交叉判定：信源缺口、内容形态缺口、金标。"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists
from app.services.geoeval.domain_catalog import (
    OWNER_OURS,
    annotate_urls,
    classify_owner,
    load_domain_catalog,
)

logger = logging.getLogger(__name__)

FLAG_MENTION_NO_OURS = "mention_no_ours"
FLAG_FRAMEWORK_GAP = "framework_not_in_answer"
FLAG_OURS_CITED = "ours_cited"
FLAG_GOLD = "gold"

DIM_WORDS = ("安全", "寿命", "成本", "续航", "补能", "低温", "循环", "冬测", "保费")


def unused_framework_dims(compare_dims: list[str], snippet: str) -> list[str]:
    body = snippet or ""
    unused: list[str] = []
    for dim in compare_dims or []:
        keys = [w for w in DIM_WORDS if w in dim]
        if not keys:
            keys = [dim[:8]] if dim else []
        if keys and not any(k and k in body for k in keys):
            unused.append(dim)
    return unused


def diagnose_tracks(
    *,
    mentioned: bool,
    urls: list[str],
    official: list[str],
    competitors: list[str] | None = None,
    wiki: list[str] | None = None,
    compare_dims: list[str] | None = None,
    snippet: str = "",
    has_a: bool = False,
    has_b: bool = False,
    has_c: bool = False,
) -> dict[str, Any]:
    ours = any(
        classify_owner(u, official=official, competitors=competitors, wiki=wiki) == OWNER_OURS
        for u in urls
        if u
    )
    unused = unused_framework_dims(list(compare_dims or []), snippet)
    flags: list[str] = []
    if mentioned and not ours:
        flags.append(FLAG_MENTION_NO_OURS)
    if unused:
        flags.append(FLAG_FRAMEWORK_GAP)
    if mentioned and ours:
        flags.append(FLAG_OURS_CITED)
    if has_a and has_b and has_c and mentioned and ours:
        flags.append(FLAG_GOLD)
    return {
        "flags": flags,
        "unused_dims": unused,
        "ours_cited": ours,
        "mentioned": mentioned,
        "tracks_present": [t for t, ok in (("A", has_a), ("B", has_b), ("C", has_c)) if ok],
    }


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def _as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


async def build_cross_track(
    db: AsyncSession,
    *,
    scene_id: int | None = None,
    question_id: int | None = None,
    limit: int = 40,
) -> dict[str, Any]:
    catalog = await load_domain_catalog(db)
    official = list(catalog.get("official") or [])
    competitors = list(catalog.get("competitor") or [])
    wiki = list(catalog.get("wiki") or [])

    empty = {
        "items": [],
        "summary": {"mention_no_ours": 0, "framework_not_in_answer": 0, "ours_cited": 0, "gold": 0},
        "catalog": catalog,
    }
    if not await _table_exists(db, "geo_monitor_probe_results"):
        return empty

    params: dict[str, Any] = {"lim": max(1, min(120, int(limit)))}
    extra = ""
    if question_id is not None:
        extra += " AND pr.question_id = :qid"
        params["qid"] = question_id
    if scene_id is not None:
        extra += " AND q.scene_id = :sid"
        params["sid"] = scene_id

    try:
        rows = (
            await db.execute(
                text(
                    f"""
                    SELECT pr.id, pr.question_id, q.question_text, pr.scheme, pr.tracks,
                           pr.mentioned, pr.snippet, pr.match_type, pr.source_hosts,
                           pr.framework, pr.engine, q.scene_id
                    FROM geo_monitor_probe_results pr
                    JOIN geo_monitor_questions q ON q.id = pr.question_id
                    WHERE 1=1 {extra}
                    ORDER BY pr.id DESC
                    LIMIT :lim
                    """
                ),
                params,
            )
        ).all()
    except Exception:
        logger.info("cross_track_query_fallback", exc_info=True)
        return empty

    grouped: dict[int, dict[str, Any]] = {}
    for r in rows:
        qid = int(r[1])
        bucket = grouped.setdefault(
            qid,
            {
                "question_id": qid,
                "question_text": str(r[2] or ""),
                "scene_id": int(r[11]) if r[11] is not None else None,
                "a": None,
                "b": None,
                "c": None,
                "urls": [],
            },
        )
        scheme = str(r[3] or "")
        tracks = [str(t).upper() for t in _as_list(r[4])]
        fw = _as_dict(r[9])
        hosts = _as_list(r[8])
        snippet = str(r[6] or "")
        mentioned = bool(r[5])
        rec = {
            "probe_id": int(r[0]),
            "scheme": scheme,
            "tracks": tracks,
            "mentioned": mentioned,
            "snippet": snippet,
            "match_type": str(r[7] or "none"),
            "framework": fw,
            "engine": str(r[10] or ""),
            "hosts": [str(h) for h in hosts if h],
        }
        if scheme == "framework_api" and bucket["a"] is None:
            bucket["a"] = rec
        if scheme in ("citation_grounded", "cend_sample") and bucket["b"] is None:
            bucket["b"] = rec
        elif "B" in tracks and bucket["b"] is None:
            bucket["b"] = rec
        if scheme == "open_api" and bucket["c"] is None:
            bucket["c"] = rec
        elif "C" in tracks and bucket["c"] is None:
            bucket["c"] = rec
        bucket["urls"].extend(
            [f"https://{h}" if h and "://" not in str(h) else str(h) for h in hosts]
        )

    # citations 表补 URL
    probe_ids = []
    for b in grouped.values():
        for key in ("a", "b", "c"):
            if b.get(key):
                probe_ids.append(b[key]["probe_id"])
    if probe_ids and await _table_exists(db, "geo_monitor_probe_citations"):
        try:
            cite_rows = (
                await db.execute(
                    text(
                        f"""
                        SELECT probe_result_id, url
                        FROM geo_monitor_probe_citations
                        WHERE probe_result_id IN ({",".join(str(i) for i in probe_ids[:80])})
                        """
                    )
                )
            ).all()
            by_probe: dict[int, list[str]] = {}
            for pid, url in cite_rows:
                if url:
                    by_probe.setdefault(int(pid), []).append(str(url))
            for b in grouped.values():
                for key in ("a", "b", "c"):
                    rec = b.get(key)
                    if rec:
                        extra_urls = by_probe.get(rec["probe_id"]) or []
                        b["urls"].extend(extra_urls)
        except Exception:
            logger.debug("cross_track_citations_skip", exc_info=True)

    items: list[dict[str, Any]] = []
    summary = {"mention_no_ours": 0, "framework_not_in_answer": 0, "ours_cited": 0, "gold": 0}
    for qid, bucket in grouped.items():
        a, b, c = bucket.get("a"), bucket.get("b"), bucket.get("c")
        mentioned = bool((c or b or a or {}).get("mentioned"))
        urls = list(dict.fromkeys([u for u in bucket["urls"] if u]))
        dims = list((a or {}).get("framework", {}).get("compare_dims") or []) if a else []
        snippet = str((c or b or {}).get("snippet") or "")
        diag = diagnose_tracks(
            mentioned=mentioned,
            urls=urls,
            official=official,
            competitors=competitors,
            wiki=wiki,
            compare_dims=dims,
            snippet=snippet,
            has_a=a is not None,
            has_b=b is not None or bool(urls),
            has_c=c is not None,
        )
        for f in diag["flags"]:
            if f in summary:
                summary[f] += 1
        hints = annotate_urls(urls, official=official, competitors=competitors, wiki=wiki)
        items.append(
            {
                "question_id": qid,
                "question_text": bucket["question_text"],
                "scene_id": bucket.get("scene_id"),
                "flags": diag["flags"],
                "unused_dims": diag["unused_dims"],
                "ours_cited": diag["ours_cited"],
                "mentioned": mentioned,
                "tracks_present": diag["tracks_present"],
                "source_hints": hints[:8],
                "probes": {
                    "framework_api": (a or {}).get("probe_id"),
                    "citation_or_cend": (b or {}).get("probe_id"),
                    "open_api": (c or {}).get("probe_id") if (c or {}).get("scheme") == "open_api" else (c or {}).get("probe_id"),
                },
            }
        )

    logger.info(
        "cross_track_built questions=%s mention_no_ours=%s framework_gap=%s gold=%s",
        len(items),
        summary["mention_no_ours"],
        summary["framework_not_in_answer"],
        summary["gold"],
    )
    return {"items": items, "summary": summary, "catalog": catalog}
