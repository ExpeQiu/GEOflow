"""GEO Monitor 探针 — 多平台连接器 + AIVIS 度量聚合。"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.article import Article
from app.models.knowledge import KnowledgeBase
from app.services.admin.production_service import _table_exists
from app.services.geoeval.platform_connectors.base import PLATFORMS_CN, ProbeOutcome, calc_ranking_score
from app.services.geoeval.platform_connectors.registry import load_platforms, load_probe_mode, probe_platform

logger = logging.getLogger(__name__)

PLATFORMS = PLATFORMS_CN


async def load_brand_keywords(db: AsyncSession) -> list[str]:
    keywords: list[str] = [get_settings().app_name]
    if await _table_exists(db, "site_settings"):
        rows = (
            await db.execute(
                text(
                    """
                    SELECT setting_key, setting_value FROM site_settings
                    WHERE setting_key IN ('brand_name', 'brand_aliases')
                    """
                )
            )
        ).all()
        for key, value in rows:
            if not value:
                continue
            if key == "brand_aliases":
                keywords.extend([p.strip() for p in str(value).split(",") if p.strip()])
            else:
                keywords.append(str(value).strip())
    seen: set[str] = set()
    out: list[str] = []
    for kw in keywords:
        low = kw.lower()
        if low and low not in seen:
            seen.add(low)
            out.append(kw)
    return out[:12]


async def load_scan_limit(db: AsyncSession) -> int:
    if not await _table_exists(db, "site_settings"):
        return 50
    row = (
        await db.execute(
            text("SELECT setting_value FROM site_settings WHERE setting_key = 'monitor_scan_limit' LIMIT 1")
        )
    ).scalar_one_or_none()
    try:
        return max(1, min(500, int(row))) if row else 50
    except (TypeError, ValueError):
        return 50


async def load_corpus(db: AsyncSession, limit: int = 80) -> list[dict]:
    from sqlalchemy import select

    corpus: list[dict] = []
    articles = (
        await db.execute(
            select(Article.title, Article.content)
            .where(Article.deleted_at.is_(None), Article.status == "published")
            .order_by(Article.id.desc())
            .limit(limit)
        )
    ).all()
    for title, content in articles:
        corpus.append({"title": title or "", "text": (content or "")[:3000]})

    kbs = (await db.execute(select(KnowledgeBase.name, KnowledgeBase.content).limit(20))).all()
    for name, content in kbs:
        corpus.append({"title": name or "", "text": (content or "")[:2000]})
    return corpus


async def _persist_probe(
    db: AsyncSession,
    *,
    run_id: int,
    outcome: ProbeOutcome,
) -> None:
    if not await _table_exists(db, "geo_monitor_probe_results"):
        return
    import json

    params = {
        "run_id": run_id,
        "qid": outcome.question_id,
        "platform": outcome.platform,
        "rank": outcome.brand_rank,
        "mentioned": outcome.mentioned,
        "snippet": outcome.snippet,
        "engine": outcome.engine,
        "ranking_score": outcome.ranking_score,
        "sentiment": json.dumps(outcome.sentiment) if outcome.sentiment else None,
        "competitor_mentions": json.dumps(outcome.competitor_mentions or []),
    }
    try:
        await db.execute(
            text(
                """
                INSERT INTO geo_monitor_probe_results
                    (run_id, question_id, platform, brand_rank, mentioned, snippet, engine,
                     ranking_score, sentiment, competitor_mentions)
                VALUES (:run_id, :qid, :platform, :rank, :mentioned, :snippet, :engine,
                        :ranking_score, CAST(:sentiment AS JSON), CAST(:competitor_mentions AS JSON))
                """
            ),
            params,
        )
    except Exception:
        await db.execute(
            text(
                """
                INSERT INTO geo_monitor_probe_results
                    (run_id, question_id, platform, brand_rank, mentioned, snippet, engine)
                VALUES (:run_id, :qid, :platform, :rank, :mentioned, :snippet, :engine)
                """
            ),
            {k: v for k, v in params.items() if k in ("run_id", "qid", "platform", "rank", "mentioned", "snippet", "engine")},
        )


async def run_probes_for_questions(
    db: AsyncSession,
    *,
    run_id: int,
    questions: list[tuple[int, str, int, list[str] | None]],
    brands: list[str] | None = None,
) -> list[ProbeOutcome]:
    brand_list = brands or await load_brand_keywords(db)
    corpus = await load_corpus(db)
    probe_mode = await load_probe_mode(db)
    platforms = await load_platforms(db)
    outcomes: list[ProbeOutcome] = []

    for q_idx, (qid, question_text, priority, competitor_brands) in enumerate(questions):
        for platform in platforms:
            outcome = await probe_platform(
                db,
                question_text=question_text,
                priority=priority,
                platform=platform,
                corpus=corpus,
                brand_list=brand_list,
                competitor_brands=competitor_brands,
                probe_mode=probe_mode,
                question_index=q_idx,
            )
            outcome.question_id = qid
            outcomes.append(outcome)
            await _persist_probe(db, run_id=run_id, outcome=outcome)

    logger.info(
        "monitor_probes_completed run_id=%s questions=%s probes=%s mode=%s platforms=%s",
        run_id,
        len(questions),
        len(outcomes),
        probe_mode,
        len(platforms),
    )
    return outcomes


async def aggregate_probe_kpis(db: AsyncSession, query_type: str | None = None) -> dict:
    empty = {
        "probe_count": 0,
        "avg_brand_rank": None,
        "mention_rate": 0.0,
        "visibility_pct": 0.0,
        "weighted_rank_score": None,
        "sentiment_score": None,
        "platform_summary": [],
        "platform_matrix": [],
        "query_type": query_type,
    }
    if not await _table_exists(db, "geo_monitor_probe_results"):
        return empty

    join_sql = ""
    where_extra = ""
    params: dict = {}
    if query_type and await _table_exists(db, "geo_monitor_questions"):
        join_sql = "JOIN geo_monitor_questions mq ON mq.id = pr.question_id"
        where_extra = "AND COALESCE(mq.query_type, 'brand') = :qt"
        params["qt"] = query_type

    total = int(
        await db.scalar(
            text(f"SELECT COUNT(*) FROM geo_monitor_probe_results pr {join_sql} WHERE 1=1 {where_extra}"),
            params,
        )
        or 0
    )
    mentioned = int(
        await db.scalar(
            text(
                f"""
                SELECT COUNT(*) FROM geo_monitor_probe_results pr {join_sql}
                WHERE pr.mentioned = true {where_extra}
                """
            ),
            params,
        )
        or 0
    )
    avg_rank = await db.scalar(
        text(
            f"""
            SELECT AVG(pr.brand_rank) FROM geo_monitor_probe_results pr {join_sql}
            WHERE pr.brand_rank IS NOT NULL {where_extra}
            """
        ),
        params,
    )
    avg_weighted = await db.scalar(
        text(
            f"""
            SELECT AVG(pr.ranking_score) FROM geo_monitor_probe_results pr {join_sql}
            WHERE pr.ranking_score > 0 {where_extra}
            """
        ),
        params,
    )

    sentiment_score = None
    try:
        pos = int(
            await db.scalar(
                text(
                    f"""
                    SELECT COUNT(*) FROM geo_monitor_probe_results pr {join_sql}
                    WHERE pr.sentiment IS NOT NULL
                      AND pr.sentiment->>'polarity' = 'positive'
                      {where_extra}
                    """
                ),
                params,
            )
            or 0
        )
        neg = int(
            await db.scalar(
                text(
                    f"""
                    SELECT COUNT(*) FROM geo_monitor_probe_results pr {join_sql}
                    WHERE pr.sentiment IS NOT NULL
                      AND pr.sentiment->>'polarity' = 'negative'
                      {where_extra}
                    """
                ),
                params,
            )
            or 0
        )
        if pos + neg > 0:
            sentiment_score = round(pos / (pos + neg) * 100, 1)
    except Exception:
        pass

    platform_rows = (
        await db.execute(
            text(
                f"""
                SELECT pr.platform,
                       COUNT(*) AS total,
                       SUM(CASE WHEN pr.mentioned THEN 1 ELSE 0 END) AS mentions,
                       AVG(pr.brand_rank) AS avg_rank,
                       AVG(NULLIF(pr.ranking_score, 0)) AS avg_weighted
                FROM geo_monitor_probe_results pr
                {join_sql}
                WHERE 1=1 {where_extra}
                GROUP BY pr.platform
                ORDER BY pr.platform
                """
            ),
            params,
        )
    ).all()

    visibility = round(mentioned / total * 100, 1) if total else 0.0
    platform_summary = [
        {
            "platform": str(r[0]),
            "total": int(r[1]),
            "mentions": int(r[2] or 0),
            "avg_rank": round(float(r[3]), 2) if r[3] is not None else None,
            "visibility_pct": round(int(r[2] or 0) / int(r[1]) * 100, 1) if r[1] else 0.0,
            "weighted_rank_score": round(float(r[4]), 2) if r[4] is not None else None,
        }
        for r in platform_rows
    ]

    return {
        "probe_count": total,
        "avg_brand_rank": round(float(avg_rank), 2) if avg_rank is not None else None,
        "mention_rate": round(mentioned / total, 3) if total else 0.0,
        "visibility_pct": visibility,
        "weighted_rank_score": round(float(avg_weighted), 2) if avg_weighted is not None else None,
        "sentiment_score": sentiment_score,
        "platform_summary": platform_summary,
        "platform_matrix": platform_summary,
        "query_type": query_type,
    }


async def aggregate_monitor_snapshot(db: AsyncSession) -> dict:
    """日快照写入 geo_monitor_snapshots。"""
    from datetime import date

    if not await _table_exists(db, "geo_monitor_snapshots"):
        return {"status": "skipped", "reason": "snapshots_table_missing"}

    kpis = await aggregate_probe_kpis(db)
    today = date.today()
    import json

    await db.execute(
        text(
            """
            INSERT INTO geo_monitor_snapshots
                (snapshot_date, mention_rate, visibility_pct, weighted_rank_score,
                 sentiment_score, platform_matrix)
            VALUES (:d, :mr, :vp, :wr, :ss, CAST(:pm AS JSON))
            ON CONFLICT (snapshot_date) DO UPDATE SET
                mention_rate = EXCLUDED.mention_rate,
                visibility_pct = EXCLUDED.visibility_pct,
                weighted_rank_score = EXCLUDED.weighted_rank_score,
                sentiment_score = EXCLUDED.sentiment_score,
                platform_matrix = EXCLUDED.platform_matrix
            """
        ),
        {
            "d": today,
            "mr": kpis.get("mention_rate", 0),
            "vp": kpis.get("visibility_pct", 0),
            "wr": kpis.get("weighted_rank_score") or 0,
            "ss": kpis.get("sentiment_score"),
            "pm": json.dumps(kpis.get("platform_matrix", [])),
        },
    )
    logger.info("monitor_snapshot_aggregated date=%s visibility=%s", today, kpis.get("visibility_pct"))
    return {"status": "ok", "snapshot_date": str(today), **kpis}
