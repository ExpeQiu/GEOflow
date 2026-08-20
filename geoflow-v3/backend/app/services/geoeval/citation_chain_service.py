"""Query → Probe → Citation 第五层链路聚合。"""

import logging
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists
from app.services.geoeval.domain_catalog import classify_owner, load_domain_catalog

logger = logging.getLogger(__name__)

PLATFORM_LABELS = {
    "doubao": "豆包",
    "deepseek": "DeepSeek",
    "tongyi": "通义千问",
    "yuanbao": "元宝",
    "wenxin": "文心一言",
    "kimi": "Kimi",
}


def stamp_citation_owners(
    items: list[dict],
    *,
    official: list[str] | None = None,
    competitors: list[str] | None = None,
    wiki: list[str] | None = None,
) -> list[dict]:
    """给引用条目打 owner，不改 URL 本身。"""
    for item in items:
        item["owner"] = classify_owner(
            str(item.get("url") or item.get("domain") or ""),
            official=official,
            competitors=competitors,
            wiki=wiki,
        )
    return items


def _domain(url: str) -> str:
    try:
        host = urlparse(url).netloc or ""
        return host.replace("www.", "") if host else ""
    except Exception:
        return ""


async def _load_citations_for_probes(db: AsyncSession, probe_ids: list[int]) -> dict[int, list[dict]]:
    if not probe_ids or not await _table_exists(db, "geo_monitor_probe_citations"):
        return {}
    try:
        rows = (
            await db.execute(
                text(
                    f"""
                    SELECT id, probe_result_id, title, url, position, evidence_level, source
                    FROM geo_monitor_probe_citations
                    WHERE probe_result_id IN ({",".join(str(i) for i in probe_ids)})
                    ORDER BY probe_result_id, position ASC, id ASC
                    """
                ),
            )
        ).all()
        extended = True
    except Exception:
        rows = (
            await db.execute(
                text(
                    f"""
                    SELECT id, probe_result_id, title, url, position
                    FROM geo_monitor_probe_citations
                    WHERE probe_result_id IN ({",".join(str(i) for i in probe_ids)})
                    ORDER BY probe_result_id, position ASC, id ASC
                    """
                ),
            )
        ).all()
        extended = False
    grouped: dict[int, list[dict]] = {}
    for row in rows:
        cid, pid, title, url, pos = row[0], row[1], row[2], row[3], row[4]
        item = {
            "id": int(cid),
            "title": str(title or ""),
            "url": str(url or ""),
            "position": int(pos or 0),
            "domain": _domain(str(url or "")),
        }
        if extended and len(row) > 6:
            item["evidence_level"] = str(row[5] or "L0")
            item["source"] = str(row[6] or "unknown")
        grouped.setdefault(int(pid), []).append(item)

    if grouped:
        try:
            catalog = await load_domain_catalog(db)
            official = list(catalog.get("official") or [])
            competitors = list(catalog.get("competitor") or [])
            wiki = list(catalog.get("wiki") or [])
            for items in grouped.values():
                stamp_citation_owners(
                    items, official=official, competitors=competitors, wiki=wiki
                )
        except Exception:
            logger.debug("citation_owner_annotate_skip", exc_info=True)
    return grouped


async def get_question_citation_detail(db: AsyncSession, question_id: int) -> dict:
    if not await _table_exists(db, "geo_monitor_questions"):
        return {"status": "missing", "reason": "questions_table_missing"}

    qrow = (
        await db.execute(
            text(
                """
                SELECT q.id, q.question_text, q.scene_id, q.query_type, q.priority,
                       s.persona, s.scene_name, s.intent, s.visibility_pct
                FROM geo_monitor_questions q
                LEFT JOIN geo_monitor_scenes s ON s.id = q.scene_id
                WHERE q.id = :id
                """
            ),
            {"id": question_id},
        )
    ).first()
    if not qrow:
        return {"status": "not_found", "question_id": question_id}

    probes: list[dict] = []
    if await _table_exists(db, "geo_monitor_probe_results"):
        try:
            probe_rows = (
                await db.execute(
                    text(
                        """
                        SELECT id, platform, brand_rank, mentioned, snippet, ranking_score,
                               engine, thinking_text, thinking_ms, keywords, rank_blocks,
                               decision_table, source_hosts, evidence_level, metric_kind, capture_artifact,
                               scheme, tracks, reasoning_grade
                        FROM geo_monitor_probe_results
                        WHERE question_id = :qid
                        ORDER BY id DESC
                        """
                    ),
                    {"qid": question_id},
                )
            ).all()
        except Exception:
            probe_rows = (
                await db.execute(
                    text(
                        """
                        SELECT id, platform, brand_rank, mentioned, snippet, ranking_score
                        FROM geo_monitor_probe_results
                        WHERE question_id = :qid
                        ORDER BY id DESC
                        """
                    ),
                    {"qid": question_id},
                )
            ).all()
        # 每平台取最新一条
        latest_by_plat: dict[str, tuple] = {}
        for r in probe_rows:
            plat = str(r[1])
            if plat not in latest_by_plat:
                latest_by_plat[plat] = r
        probe_rows = list(latest_by_plat.values())
        cite_map = await _load_citations_for_probes(db, [int(r[0]) for r in probe_rows])
        for row in probe_rows:
            pid = int(row[0])
            platform = str(row[1])
            rank = row[2]
            mentioned = row[3]
            snippet = row[4]
            ranking_score = row[5]
            engine = row[6] if len(row) > 6 else None
            thinking_text = row[7] if len(row) > 7 else None
            thinking_ms = row[8] if len(row) > 8 else None
            keywords = row[9] if len(row) > 9 else []
            rank_blocks = row[10] if len(row) > 10 else []
            decision_table = row[11] if len(row) > 11 else []
            source_hosts = row[12] if len(row) > 12 else []
            evidence_level = row[13] if len(row) > 13 else None
            metric_kind = row[14] if len(row) > 14 else None
            capture_artifact = row[15] if len(row) > 15 else None
            scheme = row[16] if len(row) > 16 else None
            tracks = row[17] if len(row) > 17 else None
            reasoning_grade = row[18] if len(row) > 18 else None
            citations = cite_map.get(pid, [])
            probes.append(
                {
                    "probe_id": pid,
                    "platform": platform,
                    "label": PLATFORM_LABELS.get(platform, platform),
                    "mentioned": bool(mentioned),
                    "brand_rank": int(rank) if rank is not None else None,
                    "ranking_score": float(ranking_score) if ranking_score is not None else None,
                    "snippet": str(snippet or ""),
                    "snippet_preview": (str(snippet or "")[:280] + "…") if len(str(snippet or "")) > 280 else str(snippet or ""),
                    "citations": citations,
                    "citation_count": len(citations),
                    "engine": engine,
                    "thinking_text": thinking_text,
                    "thinking_ms": thinking_ms,
                    "keywords": keywords or [],
                    "rank_blocks": rank_blocks or [],
                    "decision_table": decision_table or [],
                    "source_hosts": source_hosts or [],
                    "evidence_level": evidence_level,
                    "metric_kind": metric_kind,
                    "capture_artifact": capture_artifact,
                    "scheme": scheme,
                    "tracks": tracks or [],
                    "reasoning_grade": reasoning_grade,
                }
            )

    citation_count = sum(p["citation_count"] for p in probes)
    domains = sorted({c["domain"] for p in probes for c in p["citations"] if c.get("domain")})

    return {
        "status": "ok",
        "question": {
            "id": int(qrow[0]),
            "text": str(qrow[1]),
            "scene_id": int(qrow[2]) if qrow[2] is not None else None,
            "query_type": str(qrow[3] or "product"),
            "priority": int(qrow[4] or 0),
            "persona": str(qrow[5] or ""),
            "scene_name": str(qrow[6] or ""),
            "intent": str(qrow[7] or ""),
            "visibility_pct": float(qrow[8] or 0),
        },
        "probes": probes,
        "stats": {
            "probe_count": len(probes),
            "citation_count": citation_count,
            "unique_domains": len(domains),
            "domains": domains[:20],
        },
    }


async def get_scene_citation_chain(db: AsyncSession, scene_id: int) -> dict:
    if not await _table_exists(db, "geo_monitor_scenes"):
        return {"status": "missing", "reason": "scenes_table_missing"}

    scene = (
        await db.execute(
            text(
                """
                SELECT id, persona, scene_name, intent, weight_pct, visibility_pct,
                       gap_priority, external_id, article_count
                FROM geo_monitor_scenes WHERE id = :id
                """
            ),
            {"id": scene_id},
        )
    ).first()
    if not scene:
        return {"status": "not_found", "scene_id": scene_id}

    questions: list[dict] = []
    if await _table_exists(db, "geo_monitor_questions"):
        qrows = (
            await db.execute(
                text(
                    """
                    SELECT id, question_text, priority
                    FROM geo_monitor_questions
                    WHERE scene_id = :sid AND status = 'active'
                    ORDER BY priority DESC, id ASC
                    """
                ),
                {"sid": scene_id},
            )
        ).all()
        for qid, text_val, priority in qrows:
            detail = await get_question_citation_detail(db, int(qid))
            questions.append(
                {
                    "id": int(qid),
                    "text": str(text_val),
                    "priority": int(priority or 0),
                    "stats": detail.get("stats") or {},
                    "probes": detail.get("probes") or [],
                }
            )

    total_citations = sum((q.get("stats") or {}).get("citation_count", 0) for q in questions)
    total_probes = sum((q.get("stats") or {}).get("probe_count", 0) for q in questions)

    logger.info(
        "citation_chain_loaded scene_id=%s queries=%s citations=%s",
        scene_id,
        len(questions),
        total_citations,
    )
    return {
        "status": "ok",
        "scene": {
            "id": int(scene[0]),
            "persona": str(scene[1] or ""),
            "scene_name": str(scene[2] or ""),
            "intent": str(scene[3] or ""),
            "weight_pct": float(scene[4] or 0),
            "visibility_pct": float(scene[5] or 0),
            "gap_priority": str(scene[6] or "covered"),
            "external_id": str(scene[7] or ""),
            "article_count": int(scene[8] or 0),
        },
        "queries": questions,
        "stats": {
            "query_count": len(questions),
            "probe_count": total_probes,
            "citation_count": total_citations,
        },
    }
