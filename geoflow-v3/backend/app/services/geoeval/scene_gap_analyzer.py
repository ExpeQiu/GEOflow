"""场景内容缺口分析 — Persona→Scene→Intent→Query→Citation。"""

import logging
import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.admin.production_service import _table_exists
from app.services.geoflow.rag.retrieval import KnowledgeRetrievalService
from app.services.geoeval.monitor_probe import load_corpus

logger = logging.getLogger(__name__)

GAP_HIGH = 0.5
GAP_MEDIUM = 0.2
RAG_SCORE_THRESHOLD = 0.3
KEYWORD_OVERLAP_MIN = 2


def _tokenize(text: str) -> set[str]:
    parts = re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z0-9]{3,}", text.lower())
    return set(parts)


def _keyword_overlap(question: str, content: str) -> int:
    q_tokens = _tokenize(question)
    c_tokens = _tokenize(content)
    return len(q_tokens & c_tokens)


def _gap_priority(gap_rate: float) -> str:
    if gap_rate > GAP_HIGH:
        return "high"
    if gap_rate >= GAP_MEDIUM:
        return "medium"
    return "covered"


async def _load_default_kb_id(db: AsyncSession) -> int | None:
    if not await _table_exists(db, "site_settings"):
        return None
    row = (
        await db.execute(
            text("SELECT setting_value FROM site_settings WHERE setting_key = 'default_knowledge_base_id' LIMIT 1")
        )
    ).scalar_one_or_none()
    try:
        return int(row) if row else None
    except (TypeError, ValueError):
        return None


async def _load_rag_score_threshold(db: AsyncSession) -> float:
    if not await _table_exists(db, "site_settings"):
        return RAG_SCORE_THRESHOLD
    row = (
        await db.execute(
            text("SELECT setting_value FROM site_settings WHERE setting_key = 'gap_rag_score_threshold' LIMIT 1")
        )
    ).scalar_one_or_none()
    try:
        val = float(row) if row is not None else RAG_SCORE_THRESHOLD
        return max(0.05, min(val, 0.95))
    except (TypeError, ValueError):
        return RAG_SCORE_THRESHOLD


async def question_has_content_support(
    db: AsyncSession,
    question_text: str,
    kb_id: int | None,
    corpus: list[dict] | None = None,
    *,
    rag_threshold: float = RAG_SCORE_THRESHOLD,
) -> dict:
    """双通道判定：已发布语料关键词命中，或 RAG score≥阈值。返回明细便于排查。"""
    docs = corpus or await load_corpus(db)
    keyword_hit = False
    keyword_title = None
    for doc in docs:
        if _keyword_overlap(question_text, f"{doc.get('title', '')} {doc.get('text', '')}") >= KEYWORD_OVERLAP_MIN:
            keyword_hit = True
            keyword_title = str(doc.get("title") or "")[:80]
            break

    rag_hit = False
    rag_top_score = None
    rag_mock = get_settings().ai_mock_mode
    if kb_id:
        try:
            chunks = await KnowledgeRetrievalService(db).retrieve(kb_id, question_text, limit=5)
            scored = [float(c.get("score") or 0) for c in chunks if c.get("source") != "fallback"]
            if scored:
                rag_top_score = max(scored)
                rag_hit = rag_top_score >= rag_threshold
            elif chunks:
                # fallback 低分兜底不视为有支撑
                rag_top_score = max(float(c.get("score") or 0) for c in chunks)
                rag_hit = False
        except Exception:
            logger.debug("rag_retrieve_skipped kb_id=%s", kb_id, exc_info=True)

    supported = keyword_hit or rag_hit
    return {
        "supported": supported,
        "keyword_hit": keyword_hit,
        "keyword_title": keyword_title,
        "rag_hit": rag_hit,
        "rag_top_score": rag_top_score,
        "rag_mock": rag_mock,
        "rag_threshold": rag_threshold,
    }


async def compute_scene_gap(db: AsyncSession, scene_id: int, kb_id: int | None = None) -> dict:
    if not await _table_exists(db, "geo_monitor_scenes"):
        return {"status": "skipped", "reason": "scenes_table_missing"}

    scene = (
        await db.execute(
            text(
                """
                SELECT id, persona, scene_name, intent, weight_pct
                FROM geo_monitor_scenes WHERE id = :id
                """
            ),
            {"id": scene_id},
        )
    ).first()
    if not scene:
        return {"status": "not_found", "scene_id": scene_id}

    kb = kb_id if kb_id is not None else await _load_default_kb_id(db)
    corpus = await load_corpus(db)
    rag_threshold = await _load_rag_score_threshold(db)

    questions = (
        await db.execute(
            text(
                """
                SELECT id, question_text FROM geo_monitor_questions
                WHERE scene_id = :sid AND status = 'active'
                """
            ),
            {"sid": scene_id},
        )
    ).all()

    total = len(questions)
    unsupported_questions: list[dict] = []
    if total == 0:
        gap_rate = 1.0
        supported = 0
    else:
        supported = 0
        for qid, qtext in questions:
            detail = await question_has_content_support(
                db, str(qtext), kb, corpus, rag_threshold=rag_threshold
            )
            if detail["supported"]:
                supported += 1
            else:
                unsupported_questions.append({"id": int(qid), "question_text": str(qtext)[:120]})
        gap_rate = round((total - supported) / total, 3)

    priority = _gap_priority(gap_rate)
    await db.execute(
        text(
            """
            UPDATE geo_monitor_scenes
            SET gap_rate = :gr, gap_priority = :gp, last_gap_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
            """
        ),
        {"gr": gap_rate, "gp": priority, "id": scene_id},
    )
    mock_warn = get_settings().ai_mock_mode
    logger.info(
        "scene_gap_computed scene_id=%s gap_rate=%s priority=%s supported=%s/%s rag_threshold=%s ai_mock=%s",
        scene_id,
        gap_rate,
        priority,
        supported,
        total,
        rag_threshold,
        mock_warn,
    )
    return {
        "scene_id": scene_id,
        "persona": scene[1],
        "scene_name": scene[2],
        "intent": scene[3],
        "weight_pct": float(scene[4] or 0),
        "question_count": total,
        "supported_count": supported,
        "gap_rate": gap_rate,
        "gap_priority": priority,
        "rag_threshold": rag_threshold,
        "ai_mock_mode": mock_warn,
        "unsupported_sample": unsupported_questions[:5],
    }


async def compute_all_scene_gaps(db: AsyncSession) -> dict:
    if not await _table_exists(db, "geo_monitor_scenes"):
        return {"scenes": [], "high_gap_count": 0}

    rows = (await db.execute(text("SELECT id FROM geo_monitor_scenes WHERE status = 'active'"))).all()
    results = []
    high = 0
    kb_id = await _load_default_kb_id(db)
    for (sid,) in rows:
        r = await compute_scene_gap(db, int(sid), kb_id)
        results.append(r)
        if r.get("gap_priority") == "high":
            high += 1

    logger.info("scene_gap_all_completed scenes=%s high_gap=%s", len(results), high)
    return {"scenes": results, "high_gap_count": high, "ai_mock_mode": get_settings().ai_mock_mode}
