"""探针摘录情感分析 — AIVIS 好感度。"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists
from app.services.geoflow.llm_client import chat_json_or_mock

logger = logging.getLogger(__name__)

SENTIMENT_SYSTEM = (
    "你是品牌情感分析器。分析 AI 回答中对目标品牌的情感倾向。"
    '返回 JSON：{"polarity": "positive|negative|neutral", "score": 0.0-1.0, '
    '"topics": [{"category": "技术实力|产品体验|品牌感知", "label": "短语", "polarity": "positive|negative"}]}'
)


async def analyze_snippet_sentiment(
    db: AsyncSession,
    *,
    question_text: str,
    snippet: str,
    brand_name: str,
) -> dict:
    if not snippet.strip():
        return {"polarity": "neutral", "score": 0.5, "topics": []}

    user = f"用户问题：{question_text}\n目标品牌：{brand_name}\nAI 回答摘录：{snippet[:500]}"
    parsed = await chat_json_or_mock(db, system=SENTIMENT_SYSTEM, user=user)
    if not parsed:
        return {"polarity": "neutral", "score": 0.5, "topics": []}

    polarity = str(parsed.get("polarity") or "neutral")
    if polarity not in ("positive", "negative", "neutral"):
        polarity = "neutral"
    topics = parsed.get("topics") or []
    return {
        "polarity": polarity,
        "score": float(parsed.get("score") or 0.5),
        "topics": topics[:5],
    }


async def batch_analyze_probe_sentiments(db: AsyncSession, run_id: int | None = None) -> dict:
    if not await _table_exists(db, "geo_monitor_probe_results"):
        return {"updated": 0}

    from app.services.geoeval.monitor_probe import load_brand_keywords

    brands = await load_brand_keywords(db)
    brand_name = brands[0] if brands else "品牌"

    # json 列不能用 `= 'null'::json`（asyncpg: operator does not exist: json = json）
    where = (
        "mentioned = true AND (sentiment IS NULL OR CAST(sentiment AS TEXT) IN ('null', '\"null\"'))"
    )
    params: dict = {}
    if run_id:
        where += " AND run_id = :run_id"
        params["run_id"] = run_id

    rows = (
        await db.execute(
            text(
                f"""
                SELECT pr.id, pr.snippet, mq.question_text
                FROM geo_monitor_probe_results pr
                JOIN geo_monitor_questions mq ON mq.id = pr.question_id
                WHERE {where}
                LIMIT 100
                """
            ),
            params,
        )
    ).all()

    updated = 0
    import json

    for probe_id, snippet, question_text in rows:
        sentiment = await analyze_snippet_sentiment(
            db,
            question_text=str(question_text or ""),
            snippet=str(snippet or ""),
            brand_name=brand_name,
        )
        await db.execute(
            text("UPDATE geo_monitor_probe_results SET sentiment = CAST(:s AS JSON) WHERE id = :id"),
            {"s": json.dumps(sentiment, ensure_ascii=False), "id": probe_id},
        )
        updated += 1

    logger.info("sentiment_batch_completed updated=%s run_id=%s", updated, run_id)
    return {"updated": updated, "run_id": run_id}
