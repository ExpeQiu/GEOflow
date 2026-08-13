"""GEO Monitor 探针 — 多平台连接器 + AIVIS 度量聚合。"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.article import Article
from app.models.knowledge import KnowledgeBase
from app.services.admin.production_service import _table_exists
from app.services.geoeval.platform_connectors.base import PLATFORMS_CN, ProbeOutcome, calc_ranking_score
from app.services.geoeval.platform_connectors.registry import (
    load_platforms,
    load_probe_mode,
    load_strict_api,
    probe_platform,
)

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
            select(Article.title, Article.content, Article.slug)
            .where(Article.deleted_at.is_(None), Article.status == "published")
            .order_by(Article.id.desc())
            .limit(limit)
        )
    ).all()
    for title, content, slug in articles:
        corpus.append({
            "title": title or "",
            "text": (content or "")[:3000],
            "slug": slug or "",
            "url": f"/articles/{slug}" if slug else "",
        })

    kbs = (await db.execute(select(KnowledgeBase.name, KnowledgeBase.content).limit(20))).all()
    for name, content in kbs:
        corpus.append({"title": name or "", "text": (content or "")[:2000], "slug": "", "url": ""})
    return corpus


async def _persist_corpus_citations(
    db: AsyncSession,
    *,
    probe_id: int,
    question_text: str,
    corpus: list[dict],
    limit: int = 3,
) -> None:
    if not await _table_exists(db, "geo_monitor_probe_citations") or not corpus:
        return
    from app.services.geoeval.platform_connectors.corpus_connector import _score_doc

    ranked = sorted(corpus, key=lambda d: _score_doc(question_text, d, "chatgpt"), reverse=True)[:limit]
    for pos, doc in enumerate(ranked, start=1):
        title = str(doc.get("title") or "").strip()
        if not title:
            continue
        await db.execute(
            text(
                """
                INSERT INTO geo_monitor_probe_citations (probe_result_id, title, url, position)
                VALUES (:pid, :title, :url, :pos)
                """
            ),
            {"pid": probe_id, "title": title[:500], "url": str(doc.get("url") or "")[:500], "pos": pos},
        )


async def _persist_probe(
    db: AsyncSession,
    *,
    run_id: int,
    outcome: ProbeOutcome,
    question_text: str = "",
    corpus: list[dict] | None = None,
) -> int | None:
    if not await _table_exists(db, "geo_monitor_probe_results"):
        return None
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
        "rank_method": outcome.rank_method or "unknown",
        "evidence_level": outcome.evidence_level or "L0",
        "match_type": outcome.match_type or "none",
        "parser_version": outcome.parser_version,
    }
    probe_id: int | None = None
    try:
        row = (
            await db.execute(
                text(
                    """
                    INSERT INTO geo_monitor_probe_results
                        (run_id, question_id, platform, brand_rank, mentioned, snippet, engine,
                         ranking_score, sentiment, competitor_mentions,
                         rank_method, evidence_level, match_type, parser_version)
                    VALUES (:run_id, :qid, :platform, :rank, :mentioned, :snippet, :engine,
                            :ranking_score, CAST(:sentiment AS JSON), CAST(:competitor_mentions AS JSON),
                            :rank_method, :evidence_level, :match_type, :parser_version)
                    RETURNING id
                    """
                ),
                params,
            )
        ).first()
        probe_id = int(row[0]) if row else None
    except Exception:
        try:
            row = (
                await db.execute(
                    text(
                        """
                        INSERT INTO geo_monitor_probe_results
                            (run_id, question_id, platform, brand_rank, mentioned, snippet, engine,
                             ranking_score, sentiment, competitor_mentions)
                        VALUES (:run_id, :qid, :platform, :rank, :mentioned, :snippet, :engine,
                                :ranking_score, CAST(:sentiment AS JSON), CAST(:competitor_mentions AS JSON))
                        RETURNING id
                        """
                    ),
                    {k: v for k, v in params.items() if k not in ("rank_method", "evidence_level", "match_type", "parser_version")},
                )
            ).first()
            probe_id = int(row[0]) if row else None
        except Exception:
            row = (
                await db.execute(
                    text(
                        """
                        INSERT INTO geo_monitor_probe_results
                            (run_id, question_id, platform, brand_rank, mentioned, snippet, engine)
                        VALUES (:run_id, :qid, :platform, :rank, :mentioned, :snippet, :engine)
                        RETURNING id
                        """
                    ),
                    {k: v for k, v in params.items() if k in ("run_id", "qid", "platform", "rank", "mentioned", "snippet", "engine")},
                )
            ).first()
            probe_id = int(row[0]) if row else None

    if probe_id and corpus and question_text and outcome.engine == "corpus":
        await _persist_corpus_citations(db, probe_id=probe_id, question_text=question_text, corpus=corpus)
    return probe_id


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
    strict_api = await load_strict_api(db)
    outcomes: list[ProbeOutcome] = []
    engine_counts: dict[str, int] = {}

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
                strict_api=strict_api,
            )
            outcome.question_id = qid
            outcomes.append(outcome)
            engine_counts[outcome.engine] = engine_counts.get(outcome.engine, 0) + 1
            await _persist_probe(
                db,
                run_id=run_id,
                outcome=outcome,
                question_text=question_text,
                corpus=corpus,
            )

    logger.info(
        "monitor_probes_completed run_id=%s questions=%s probes=%s mode=%s platforms=%s strict_api=%s engines=%s",
        run_id,
        len(questions),
        len(outcomes),
        probe_mode,
        len(platforms),
        strict_api,
        engine_counts,
    )
    return outcomes


async def aggregate_probe_kpis(
    db: AsyncSession,
    query_type: str | None = None,
    *,
    scene_id: int | None = None,
    run_id: int | None = None,
    trusted_only: bool = False,
    intent_subset: list[str] | None = None,
    north_star: bool = False,
) -> dict:
    from app.services.geoeval.north_star_kpi import (
        NORTH_STAR_INTENTS,
        mention_rate_pct,
        sentiment_negative_pct,
        topn_pct,
    )

    if north_star and intent_subset is None:
        intent_subset = sorted(NORTH_STAR_INTENTS)

    empty = {
        "probe_count": 0,
        "avg_brand_rank": None,
        "mention_rate": 0.0,
        "mention_rate_pct": 0.0,
        "visibility_pct": 0.0,
        "visibility_open_api": 0.0,
        "weighted_rank_score": None,
        "sentiment_score": None,
        "sentiment_negative_pct": None,
        "top1_pct": None,
        "top3_pct": None,
        "top5_pct": None,
        "valid_sample_n": 0,
        "platform_summary": [],
        "platform_matrix": [],
        "query_type": query_type,
        "engine_mix": [],
        "trusted_only": trusted_only,
        "scene_id": scene_id,
        "run_id": run_id,
        "intent_subset": intent_subset,
        "kpi_track": "open_api" if trusted_only or north_star else "mixed",
    }
    if not await _table_exists(db, "geo_monitor_probe_results"):
        return empty

    join_sql = ""
    where_extra = ""
    params: dict = {}
    need_questions = bool(query_type or scene_id or intent_subset)
    has_intent_col = False
    if need_questions and await _table_exists(db, "geo_monitor_questions"):
        join_sql = "JOIN geo_monitor_questions mq ON mq.id = pr.question_id"
        if query_type:
            where_extra += " AND COALESCE(mq.query_type, 'brand') = :qt"
            params["qt"] = query_type
        if scene_id is not None:
            where_extra += " AND mq.scene_id = :sid"
            params["sid"] = scene_id
        if intent_subset:
            try:
                col = (
                    await db.execute(
                        text(
                            """
                            SELECT column_name FROM information_schema.columns
                            WHERE table_name = 'geo_monitor_questions' AND column_name = 'intent_type'
                            """
                        )
                    )
                ).first()
                has_intent_col = bool(col)
            except Exception:
                has_intent_col = False
            if has_intent_col:
                placeholders = []
                for i, intent in enumerate(intent_subset):
                    key = f"intent_{i}"
                    placeholders.append(f":{key}")
                    params[key] = intent
                where_extra += f" AND COALESCE(mq.intent_type, 'cognition') IN ({', '.join(placeholders)})"
            else:
                logger.debug("intent_type_column_missing skip_subset_filter")
    if run_id is not None:
        where_extra += " AND pr.run_id = :rid"
        params["rid"] = run_id
    if trusted_only or north_star:
        where_extra += " AND COALESCE(pr.engine, 'corpus') = 'api'"
    else:
        where_extra += " AND COALESCE(pr.engine, 'corpus') <> 'skipped'"

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

    rank_rows = (
        await db.execute(
            text(
                f"""
                SELECT pr.brand_rank FROM geo_monitor_probe_results pr
                {join_sql}
                WHERE pr.brand_rank IS NOT NULL {where_extra}
                """
            ),
            params,
        )
    ).all()
    ranks = [int(r[0]) for r in rank_rows if r[0] is not None]
    t1 = topn_pct(ranks, 1)
    t3 = topn_pct(ranks, 3)
    t5 = topn_pct(ranks, 5)
    valid_sample_n = len(ranks)

    sentiment_score = None
    sent_neg = None
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
        neu = int(
            await db.scalar(
                text(
                    f"""
                    SELECT COUNT(*) FROM geo_monitor_probe_results pr {join_sql}
                    WHERE pr.sentiment IS NOT NULL
                      AND pr.sentiment->>'polarity' = 'neutral'
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
        sent_neg = sentiment_negative_pct(pos, neu, neg)
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
                       AVG(NULLIF(pr.ranking_score, 0)) AS avg_weighted,
                       SUM(CASE WHEN pr.brand_rank IS NOT NULL AND pr.brand_rank <= 3 THEN 1 ELSE 0 END) AS top3_hits,
                       SUM(CASE WHEN pr.brand_rank IS NOT NULL THEN 1 ELSE 0 END) AS ranked_n
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
    mr_pct = mention_rate_pct(mentioned, total)
    platform_summary = [
        {
            "platform": str(r[0]),
            "total": int(r[1]),
            "mentions": int(r[2] or 0),
            "avg_rank": round(float(r[3]), 2) if r[3] is not None else None,
            "visibility_pct": round(int(r[2] or 0) / int(r[1]) * 100, 1) if r[1] else 0.0,
            "weighted_rank_score": round(float(r[4]), 2) if r[4] is not None else None,
            "top3_pct": round(int(r[5] or 0) / int(r[6]) * 100, 1) if r[6] else None,
        }
        for r in platform_rows
    ]

    engine_mix: list[dict] = []
    try:
        engine_rows = (
            await db.execute(
                text(
                    f"""
                    SELECT COALESCE(pr.engine, 'corpus') AS eng, COUNT(*) AS cnt
                    FROM geo_monitor_probe_results pr
                    {join_sql}
                    WHERE 1=1 {where_extra}
                    GROUP BY COALESCE(pr.engine, 'corpus')
                    ORDER BY cnt DESC
                    """
                ),
                params,
            )
        ).all()
        labels = {"corpus": "语料", "llm": "LLM 模拟", "api": "真实 API", "skipped": "跳过"}
        engine_mix = [
            {"engine": str(r[0]), "label": labels.get(str(r[0]), str(r[0])), "count": int(r[1])}
            for r in engine_rows
        ]
    except Exception:
        logger.debug("engine_mix_query_failed", exc_info=True)

    metric_meta: dict = {
        "metric_kind": "open_api" if (trusted_only or north_star) else "mixed",
        "footnote_on_bias": True,
        "do_not_overwrite_open_api_kpi": True,
        "subset": "compare+decision" if intent_subset else "all",
    }
    try:
        from app.services.admin.geo_eval_settings_service import get_probe_standards

        standards = await get_probe_standards(db)
        metric_meta = {
            "metric_kind": "open_api" if (trusted_only or north_star) else "mixed",
            "footnote_on_bias": bool(standards.get("footnote_on_bias", True)),
            "do_not_overwrite_open_api_kpi": True,
            "rank_report_weight": standards.get("rank_report_weight"),
            "min_evidence_level": standards.get("min_evidence_level"),
            "subset": "compare+decision" if intent_subset else "all",
        }
        logger.debug(
            "probe_kpi_standards_applied footnote=%s weight=%s top3=%s",
            metric_meta["footnote_on_bias"],
            metric_meta.get("rank_report_weight"),
            t3,
        )
    except Exception:
        logger.debug("probe_standards_kpi_attach_failed", exc_info=True)

    kpi_track = "open_api" if (trusted_only or north_star) else "mixed"
    logger.info(
        "probe_kpis_aggregated probes=%s top3=%s mention_pct=%s track=%s subset=%s",
        total,
        t3,
        mr_pct,
        kpi_track,
        intent_subset,
    )
    return {
        "probe_count": total,
        "avg_brand_rank": round(float(avg_rank), 2) if avg_rank is not None else None,
        "mention_rate": round(mentioned / total, 3) if total else 0.0,
        "mention_rate_pct": mr_pct,
        "visibility_pct": visibility,
        "visibility_open_api": visibility if kpi_track == "open_api" else None,
        "weighted_rank_score": round(float(avg_weighted), 2) if avg_weighted is not None else None,
        "sentiment_score": sentiment_score,
        "sentiment_negative_pct": sent_neg,
        "top1_pct": t1,
        "top3_pct": t3,
        "top5_pct": t5,
        "valid_sample_n": valid_sample_n,
        "platform_summary": platform_summary,
        "platform_matrix": platform_summary,
        "query_type": query_type,
        "engine_mix": engine_mix,
        "trusted_only": trusted_only or north_star,
        "scene_id": scene_id,
        "run_id": run_id,
        "intent_subset": intent_subset,
        "kpi_track": kpi_track,
        "metric_meta": metric_meta,
    }


async def aggregate_scene_visibility(
    db: AsyncSession,
    scene_id: int,
    *,
    run_id: int | None = None,
    trusted_only: bool = False,
) -> dict:
    """按场景聚合可见性与 Top3，供补缺实验 baseline/post 对比。"""
    kpis = await aggregate_probe_kpis(
        db,
        scene_id=scene_id,
        run_id=run_id,
        trusted_only=trusted_only,
        north_star=False,
    )
    # 场景闭环优先 Top3；无 rank 时退回 visibility
    latest_run_id = run_id
    if latest_run_id is None and await _table_exists(db, "geo_monitor_probe_results"):
        latest_run_id = await db.scalar(
            text(
                """
                SELECT pr.run_id FROM geo_monitor_probe_results pr
                JOIN geo_monitor_questions mq ON mq.id = pr.question_id
                WHERE mq.scene_id = :sid
                ORDER BY pr.id DESC
                LIMIT 1
                """
            ),
            {"sid": scene_id},
        )
    kpis["latest_run_id"] = int(latest_run_id) if latest_run_id else None
    logger.info(
        "scene_visibility_aggregated scene_id=%s visibility=%s top3=%s probes=%s trusted_only=%s",
        scene_id,
        kpis.get("visibility_pct"),
        kpis.get("top3_pct"),
        kpis.get("probe_count"),
        trusted_only,
    )
    return kpis


async def aggregate_monitor_snapshot(db: AsyncSession) -> dict:
    """日快照写入 geo_monitor_snapshots（含北极星 TopN）。"""
    from datetime import date
    import json

    from app.services.geoeval.competitive_analyzer import build_competitor_matrix

    if not await _table_exists(db, "geo_monitor_snapshots"):
        return {"status": "skipped", "reason": "snapshots_table_missing"}

    kpis = await aggregate_probe_kpis(db, north_star=True)
    matrix = await build_competitor_matrix(db, north_star=True)
    gap_top3 = matrix.get("gap_vs_leader_top3_pp")
    today = date.today()
    meta = {
        "kpi_track": kpis.get("kpi_track"),
        "valid_sample_n": kpis.get("valid_sample_n"),
        "intent_subset": kpis.get("intent_subset"),
        "top5_pct": kpis.get("top5_pct"),
        "self_top3_pct": matrix.get("self_top3_pct"),
        "leader_top3_pct": matrix.get("leader_top3_pct"),
    }

    # 兼容旧库：优先写扩展列，失败则回退基础列
    try:
        await db.execute(
            text(
                """
                INSERT INTO geo_monitor_snapshots
                    (snapshot_date, mention_rate, visibility_pct, weighted_rank_score,
                     sentiment_score, platform_matrix,
                     top1_pct, top3_pct, top5_pct, gap_vs_leader_top3_pp,
                     mention_rate_pct, sentiment_negative_pct, kpi_track, north_star_meta)
                VALUES (:d, :mr, :vp, :wr, :ss, CAST(:pm AS JSON),
                        :t1, :t3, :t5, :gap, :mrp, :snp, :track, CAST(:meta AS JSON))
                ON CONFLICT (snapshot_date) DO UPDATE SET
                    mention_rate = EXCLUDED.mention_rate,
                    visibility_pct = EXCLUDED.visibility_pct,
                    weighted_rank_score = EXCLUDED.weighted_rank_score,
                    sentiment_score = EXCLUDED.sentiment_score,
                    platform_matrix = EXCLUDED.platform_matrix,
                    top1_pct = EXCLUDED.top1_pct,
                    top3_pct = EXCLUDED.top3_pct,
                    top5_pct = EXCLUDED.top5_pct,
                    gap_vs_leader_top3_pp = EXCLUDED.gap_vs_leader_top3_pp,
                    mention_rate_pct = EXCLUDED.mention_rate_pct,
                    sentiment_negative_pct = EXCLUDED.sentiment_negative_pct,
                    kpi_track = EXCLUDED.kpi_track,
                    north_star_meta = EXCLUDED.north_star_meta
                """
            ),
            {
                "d": today,
                "mr": kpis.get("mention_rate", 0),
                "vp": kpis.get("visibility_pct", 0),
                "wr": kpis.get("weighted_rank_score") or 0,
                "ss": kpis.get("sentiment_score"),
                "pm": json.dumps(kpis.get("platform_matrix", [])),
                "t1": kpis.get("top1_pct"),
                "t3": kpis.get("top3_pct"),
                "t5": kpis.get("top5_pct"),
                "gap": gap_top3,
                "mrp": kpis.get("mention_rate_pct"),
                "snp": kpis.get("sentiment_negative_pct"),
                "track": kpis.get("kpi_track", "open_api"),
                "meta": json.dumps(meta, ensure_ascii=False),
            },
        )
    except Exception:
        logger.warning("snapshot_north_star_columns_missing falling_back", exc_info=True)
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
    kpis["gap_vs_leader_top3_pp"] = gap_top3
    logger.info(
        "monitor_snapshot_aggregated date=%s top3=%s gap_top3=%s track=%s",
        today,
        kpis.get("top3_pct"),
        gap_top3,
        kpis.get("kpi_track"),
    )
    return {"status": "ok", "snapshot_date": str(today), **kpis}
