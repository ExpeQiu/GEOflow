"""场景内容缺口分析 — Persona→Scene→Intent→Query→Citation。"""

import logging
import re

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
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


async def question_has_content_support(
    db: AsyncSession,
    question_text: str,
    kb_id: int | None,
    corpus: list[dict] | None = None,
) -> bool:
    docs = corpus or await load_corpus(db)
    for doc in docs:
        if _keyword_overlap(question_text, f"{doc.get('title', '')} {doc.get('text', '')}") >= KEYWORD_OVERLAP_MIN:
            return True

    if kb_id:
        try:
            chunks = await KnowledgeRetrievalService(db).retrieve(kb_id, question_text, limit=5)
            if chunks:
                return True
        except Exception:
            logger.debug("rag_retrieve_skipped kb_id=%s", kb_id)

    return False


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
    if total == 0:
        gap_rate = 1.0
        supported = 0
    else:
        supported = 0
        for _, qtext in questions:
            if await question_has_content_support(db, str(qtext), kb, corpus):
                supported += 1
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
    logger.info(
        "scene_gap_computed scene_id=%s gap_rate=%s priority=%s supported=%s/%s",
        scene_id,
        gap_rate,
        priority,
        supported,
        total,
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
    return {"scenes": results, "high_gap_count": high}
