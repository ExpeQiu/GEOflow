"""AIVIS 五层聚合 BFF — 诊断总览、采集、品牌、产品。"""

import logging
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.monitor_aivis_service import list_monitor_insights, list_visibility_reports
from app.services.admin.production_service import _table_exists
from app.services.geoeval.aivis_analyzers import (
    assess_difficulty,
    build_optimization_panel,
    build_scene_funnel_tree,
    extract_sentiment_topics,
    score_platforms,
)
from app.services.geoeval.competitive_analyzer import (
    _recalc_matrix_stats,
    build_competitor_matrix,
    build_product_competitor_matrix,
    matrix_competitor_names,
)
from app.services.geoeval.entity_classifier import filter_matrix_by_entity
from app.services.geoeval.monitor_probe import aggregate_probe_kpis
from app.services.geoeval.platform_connectors.base import PLATFORMS_CN

logger = logging.getLogger(__name__)

PLATFORM_LABELS = {
    "doubao": "豆包",
    "deepseek": "DeepSeek",
    "tongyi": "通义千问",
    "yuanbao": "元宝",
    "wenxin": "文心一言",
    "kimi": "Kimi",
}


async def _question_stats(db: AsyncSession) -> dict:
    stats = {"brand": 0, "product": 0, "competitor": 0, "total": 0}
    if not await _table_exists(db, "geo_monitor_questions"):
        return stats
    try:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT COALESCE(query_type, 'brand') AS qt, COUNT(*) AS cnt
                    FROM geo_monitor_questions WHERE status = 'active'
                    GROUP BY COALESCE(query_type, 'brand')
                    """
                )
            )
        ).all()
        for qt, cnt in rows:
            key = str(qt) if str(qt) in stats else "brand"
            stats[key] = int(cnt)
            stats["total"] += int(cnt)
    except Exception:
        rows = (
            await db.execute(
                text("SELECT COUNT(*) FROM geo_monitor_questions WHERE status = 'active'")
            )
        ).scalar_one_or_none()
        stats["brand"] = int(rows or 0)
        stats["total"] = stats["brand"]
    return stats


async def _collection_window(db: AsyncSession) -> dict:
    if not await _table_exists(db, "geo_monitor_runs"):
        return {"period_start": None, "period_end": None}
    row = (
        await db.execute(
            text(
                """
                SELECT MIN(started_at)::date, MAX(completed_at)::date
                FROM geo_monitor_runs WHERE started_at IS NOT NULL
                """
            )
        )
    ).first()
    if not row:
        return {"period_start": None, "period_end": None}
    return {
        "period_start": str(row[0]) if row[0] else None,
        "period_end": str(row[1] if row[1] else row[0]) if row[0] else None,
    }


async def _platform_probe_counts(db: AsyncSession) -> list[dict]:
    """历史累计：各平台探针结果总数。"""
    if not await _table_exists(db, "geo_monitor_probe_results"):
        return [{"platform": p, "label": PLATFORM_LABELS.get(p, p), "probe_count": 0} for p in PLATFORMS_CN]
    rows = (
        await db.execute(
            text(
                """
                SELECT platform, COUNT(*) FROM geo_monitor_probe_results
                GROUP BY platform ORDER BY platform
                """
            )
        )
    ).all()
    counts = {str(r[0]): int(r[1]) for r in rows}
    return [
        {"platform": p, "label": PLATFORM_LABELS.get(p, p), "probe_count": counts.get(p, 0)}
        for p in PLATFORMS_CN
    ]


async def _next_scan_plan(db: AsyncSession, qstats: dict) -> dict:
    from app.services.admin.monitor_settings_service import get_monitor_settings
    from app.services.geoeval.monitor_probe import load_platforms, load_scan_limit

    settings = await get_monitor_settings(db)
    platforms = await load_platforms(db)
    scan_limit = await load_scan_limit(db)
    active_total = int(qstats.get("total") or 0)
    effective = min(active_total, scan_limit)
    plat_count = len(platforms)

    return {
        "active_questions": active_total,
        "effective_questions": effective,
        "scan_limit": scan_limit,
        "platform_count": plat_count,
        "total_probes_estimated": effective * plat_count,
        "probe_mode": settings.get("probe_mode", "corpus"),
        "platforms": [
            {"platform": p, "label": PLATFORM_LABELS.get(p, p), "estimate": effective}
            for p in platforms
        ],
    }


async def _engine_distribution(db: AsyncSession) -> list[dict]:
    if not await _table_exists(db, "geo_monitor_probe_results") or not await _table_exists(db, "geo_monitor_runs"):
        return []
    run_id = await db.scalar(text("SELECT id FROM geo_monitor_runs ORDER BY id DESC LIMIT 1"))
    if not run_id:
        return []
    rows = (
        await db.execute(
            text(
                """
                SELECT COALESCE(engine, 'corpus') AS eng, COUNT(*) AS cnt
                FROM geo_monitor_probe_results
                WHERE run_id = :rid
                GROUP BY COALESCE(engine, 'corpus')
                ORDER BY cnt DESC
                """
            ),
            {"rid": int(run_id)},
        )
    ).all()
    labels = {"corpus": "语料", "llm": "LLM 模拟", "api": "真实 API"}
    return [{"engine": str(r[0]), "label": labels.get(str(r[0]), str(r[0])), "count": int(r[1])} for r in rows]


async def _latest_run_status(db: AsyncSession) -> dict | None:
    if not await _table_exists(db, "geo_monitor_runs"):
        return None
    row = (
        await db.execute(
            text(
                """
                SELECT id, status, question_count, probe_count, started_at, completed_at
                FROM geo_monitor_runs ORDER BY id DESC LIMIT 1
                """
            )
        )
    ).first()
    if not row:
        return None
    return {
        "id": int(row[0]),
        "status": row[1],
        "question_count": int(row[2] or 0),
        "probe_count": int(row[3] or 0) if row[3] is not None else None,
        "started_at": row[4].isoformat() if row[4] else None,
        "completed_at": row[5].isoformat() if row[5] else None,
    }


async def build_collection_panel(db: AsyncSession) -> dict:
    from app.services.admin.monitor_settings_service import get_monitor_settings
    from app.services.admin.strategy_service import _recent_alerts

    qstats = await _question_stats(db)
    window = await _collection_window(db)
    platforms_historical = await _platform_probe_counts(db)
    kpis = await aggregate_probe_kpis(db)
    next_scan = await _next_scan_plan(db, qstats)
    settings = await get_monitor_settings(db)

    brand_questions = qstats["brand"]
    product_questions = qstats["product"]
    competitor_questions = qstats["competitor"]
    plat_count = next_scan["platform_count"]

    return {
        "platforms": platforms_historical,
        "platforms_next": next_scan["platforms"],
        "platform_count": plat_count,
        "question_stats": {
            "brand_questions": brand_questions,
            "product_questions": product_questions,
            "competitor_questions": competitor_questions,
            "total_questions": qstats["total"],
            "brand_probes_estimated": brand_questions * plat_count,
            "product_probes_estimated": product_questions * plat_count,
            "competitor_probes_estimated": competitor_questions * plat_count,
            "total_probes_estimated": next_scan["total_probes_estimated"],
        },
        "next_scan": next_scan,
        "probe_settings": {
            "brand_name": settings.get("brand_name", ""),
            "probe_mode": settings.get("probe_mode", "corpus"),
            "monitor_scan_limit": settings.get("monitor_scan_limit", 50),
            "platforms": settings.get("platforms", []),
            "ai_mock_mode": settings.get("ai_mock_mode", True),
            "strict_api": settings.get("strict_api", False),
            "remediation_delay_hours": settings.get("remediation_delay_hours", 72),
            "gap_rag_score_threshold": settings.get("gap_rag_score_threshold", 0.3),
        },
        "engine_distribution": await _engine_distribution(db),
        "latest_run": await _latest_run_status(db),
        "recent_alerts": await _recent_alerts(db, limit=5),
        "collection_window": window,
        "probe_count": kpis.get("probe_count", 0),
        "recent_runs": await _fetch_recent_runs(db),
    }


async def _fetch_recent_runs(db: AsyncSession, limit: int = 8) -> list[dict]:
    if not await _table_exists(db, "geo_monitor_runs"):
        return []
    rows = (
        await db.execute(
            text(
                """
                SELECT id, status, platform, question_count, probe_count, completed_at
                FROM geo_monitor_runs ORDER BY id DESC LIMIT :lim
                """
            ),
            {"lim": limit},
        )
    ).all()
    return [
        {
            "id": int(r[0]),
            "status": r[1],
            "platform": r[2],
            "question_count": int(r[3] or 0),
            "probe_count": int(r[4] or 0) if r[4] is not None else None,
            "completed_at": r[5].isoformat() if r[5] else None,
        }
        for r in rows
    ]


async def build_brand_panel(db: AsyncSession) -> dict:
    from app.services.geoeval.aivis_analyzers import _load_tjg_platform_breakdown
    from app.services.geoeval.competitive_analyzer import load_tjg_layer_snapshot

    kpis = await aggregate_probe_kpis(db, query_type="brand", north_star=True)
    matrix = await build_competitor_matrix(db, query_type="brand", north_star=True)
    topics = await extract_sentiment_topics(db)
    insights = (await list_monitor_insights(db)).get("items", [])
    brand_insights = [i for i in insights if i.get("insight_type") in ("competitor_surpass", "authority_endorsement")]
    platform_breakdown = await _load_tjg_platform_breakdown(db, layer="brand")

    metrics = {
        "visibility_pct": kpis.get("visibility_pct", 0),
        "visibility_open_api": kpis.get("visibility_open_api"),
        "weighted_rank_score": kpis.get("weighted_rank_score"),
        "sentiment_score": kpis.get("sentiment_score"),
        "sentiment_negative_pct": kpis.get("sentiment_negative_pct"),
        "top3_pct": kpis.get("top3_pct"),
        "top5_pct": kpis.get("top5_pct"),
        "mention_rate_pct": kpis.get("mention_rate_pct"),
        "gap_vs_leader_top3_pp": matrix.get("gap_vs_leader_top3_pp"),
        "kpi_track": kpis.get("kpi_track"),
        "probe_count": kpis.get("probe_count", 0),
    }
    if metrics["probe_count"] == 0:
        tjg = await load_tjg_layer_snapshot(db, layer="brand")
        if tjg:
            layer_kpis = tjg.get("kpis") or {}
            metrics["visibility_pct"] = float(layer_kpis.get("visibility_pct") or metrics["visibility_pct"])
            rank_label = str(layer_kpis.get("rank_label") or "")
            if rank_label.lower().startswith("no."):
                try:
                    metrics["weighted_rank_score"] = float(rank_label.split(".")[-1].strip())
                except ValueError:
                    pass
            metrics["sentiment_score"] = layer_kpis.get("sentiment_pct", metrics["sentiment_score"])
            metrics["probe_count"] = int(layer_kpis.get("total_responses") or 0) or metrics["probe_count"]

    return {
        "metrics": metrics,
        "competitor_matrix": matrix,
        "platform_summary": kpis.get("platform_summary", []),
        "platform_breakdown": platform_breakdown,
        "sentiment_topics": topics,
        "insights": brand_insights[:5],
    }


async def build_product_panel(db: AsyncSession) -> dict:
    from app.services.geoeval.aivis_analyzers import _load_tjg_platform_breakdown

    kpis = await aggregate_probe_kpis(db, query_type="product", north_star=True)
    matrix = await build_product_competitor_matrix(db)
    matrix["matrix"] = filter_matrix_by_entity(matrix.get("matrix") or [], "product")
    matrix["competitors"] = matrix_competitor_names(matrix["matrix"])
    if matrix["matrix"]:
        self_vis, gap = _recalc_matrix_stats(matrix["matrix"], float(kpis.get("visibility_pct") or 0))
        matrix["self_visibility_pct"] = self_vis
        matrix["gap_vs_leader"] = gap
    funnel = await build_scene_funnel_tree(db)
    platform_breakdown = await _load_tjg_platform_breakdown(db, layer="product")

    return {
        "metrics": {
            "visibility_pct": kpis.get("visibility_pct", 0),
            "visibility_open_api": kpis.get("visibility_open_api"),
            "weighted_rank_score": kpis.get("weighted_rank_score"),
            "sentiment_score": kpis.get("sentiment_score"),
            "sentiment_negative_pct": kpis.get("sentiment_negative_pct"),
            "top3_pct": kpis.get("top3_pct"),
            "top5_pct": kpis.get("top5_pct"),
            "mention_rate_pct": kpis.get("mention_rate_pct"),
            "kpi_track": kpis.get("kpi_track"),
            "probe_count": kpis.get("probe_count", 0),
        },
        "competitor_matrix": matrix,
        "platform_summary": kpis.get("platform_summary", []),
        "platform_breakdown": platform_breakdown,
        "scene_funnel": funnel,
    }


async def build_diagnosis_panel(db: AsyncSession) -> dict:
    from app.services.admin.strategy_service import _monitor_kpis

    collection = await build_collection_panel(db)
    brand = await build_brand_panel(db)
    product = await build_product_panel(db)
    optimization = await build_optimization_panel(db)
    difficulty = await assess_difficulty(db)
    reports = (await list_visibility_reports(db)).get("items", [])[:1]

    return {
        "collection": {
            "platform_count": collection["platform_count"],
            "question_stats": collection["question_stats"],
            "collection_window": collection["collection_window"],
        },
        "brand": brand["metrics"],
        "product": product["metrics"],
        "optimization": {
            "top_platform": optimization["platform_recommendations"][0] if optimization["platform_recommendations"] else None,
            "priority_scenes": optimization["priority_scenes"][:3],
            "insights": optimization["insights"][:3],
            "market_summary": (optimization.get("readiness") or {}).get("summary")
            or optimization["market_opportunity"]["summary"],
        },
        "difficulty": {
            "regulatory_compliance": difficulty["regulatory_compliance"]["score"],
            "market_competition": difficulty["market_competition"]["score"],
            "entity_foundation": difficulty["entity_foundation"]["score"],
            "overall_score": difficulty["overall_score"],
        },
        "latest_report": reports[0] if reports else None,
        "monitor": await _monitor_kpis(db),
    }
