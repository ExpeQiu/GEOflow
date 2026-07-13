"""Query → Probe → Citation 第五层链路聚合。"""

import logging
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists

logger = logging.getLogger(__name__)

PLATFORM_LABELS = {
    "doubao": "豆包",
    "deepseek": "DeepSeek",
    "tongyi": "通义千问",
    "yuanbao": "元宝",
    "wenxin": "文心一言",
    "kimi": "Kimi",
}


def _domain(url: str) -> str:
    try:
        host = urlparse(url).netloc or ""
        return host.replace("www.", "") if host else ""
    except Exception:
        return ""


async def _load_citations_for_probes(db: AsyncSession, probe_ids: list[int]) -> dict[int, list[dict]]:
    if not probe_ids or not await _table_exists(db, "geo_monitor_probe_citations"):
        return {}
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
    grouped: dict[int, list[dict]] = {}
    for cid, pid, title, url, pos in rows:
        grouped.setdefault(int(pid), []).append(
            {
                "id": int(cid),
                "title": str(title or ""),
                "url": str(url or ""),
                "position": int(pos or 0),
                "domain": _domain(str(url or "")),
            }
        )
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
        probe_rows = (
            await db.execute(
                text(
                    """
                    SELECT id, platform, brand_rank, mentioned, snippet, ranking_score
                    FROM geo_monitor_probe_results
                    WHERE question_id = :qid
                    ORDER BY platform
                    """
                ),
                {"qid": question_id},
            )
        ).all()
        cite_map = await _load_citations_for_probes(db, [int(r[0]) for r in probe_rows])
        for pid, platform, rank, mentioned, snippet, ranking_score in probe_rows:
            citations = cite_map.get(int(pid), [])
            probes.append(
                {
                    "probe_id": int(pid),
                    "platform": str(platform),
                    "label": PLATFORM_LABELS.get(str(platform), str(platform)),
                    "mentioned": bool(mentioned),
                    "brand_rank": int(rank) if rank is not None else None,
                    "ranking_score": float(ranking_score) if ranking_score is not None else None,
                    "snippet": str(snippet or ""),
                    "snippet_preview": (str(snippet or "")[:280] + "…") if len(str(snippet or "")) > 280 else str(snippet or ""),
                    "citations": citations,
                    "citation_count": len(citations),
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
