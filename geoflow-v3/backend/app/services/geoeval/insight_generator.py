"""AIVIS 三类洞察自动生成。"""

import json
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists
from app.services.geoeval.competitive_analyzer import build_competitor_matrix, compute_optimization_potential
from app.services.geoeval.monitor_probe import aggregate_probe_kpis

logger = logging.getLogger(__name__)

INSIGHT_TYPES = ("competitor_surpass", "core_scene", "authority_endorsement")


async def generate_monitor_insights(db: AsyncSession) -> list[dict]:
    if not await _table_exists(db, "geo_monitor_insights"):
        return []

    kpis = await aggregate_probe_kpis(db)
    matrix_data = await build_competitor_matrix(db)
    insights: list[dict] = []

    opt = await compute_optimization_potential(
        float(kpis.get("visibility_pct") or 0),
        float(matrix_data.get("self_visibility_pct") or 0) + float(matrix_data.get("gap_vs_leader") or 0),
    )
    if matrix_data.get("gap_vs_leader", 0) > 0 and opt.get("lift_needed", 100) < 30:
        insights.append(
            {
                "insight_type": "competitor_surpass",
                "title": "竞品超越机会",
                "body": f"与领先者差距 {matrix_data['gap_vs_leader']}pp，预计提升 {opt['lift_needed']}% 可接近标杆。",
                "payload": {"gap_vs_leader": matrix_data["gap_vs_leader"], **opt},
            }
        )

    if await _table_exists(db, "geo_monitor_scenes"):
        scenes = (
            await db.execute(
                text(
                    """
                    SELECT scene_name, weight_pct, gap_rate, gap_priority
                    FROM geo_monitor_scenes
                    WHERE status = 'active' AND weight_pct >= 10
                    ORDER BY weight_pct DESC
                    LIMIT 5
                    """
                )
            )
        ).all()
        avg_vis = float(kpis.get("visibility_pct") or 0)
        for name, weight, gap_rate, priority in scenes:
            if float(weight or 0) >= 10 and avg_vis < 30:
                insights.append(
                    {
                        "insight_type": "core_scene",
                        "title": f"核心场景：{name}",
                        "body": f"场景权重 {weight}%，缺口率 {float(gap_rate or 0)*100:.1f}%，优先级 {priority}。",
                        "payload": {"scene_name": name, "weight_pct": float(weight or 0), "gap_rate": float(gap_rate or 0)},
                    }
                )
                break

    wiki_pct = 0.0
    try:
        from app.services.admin.strategy_service import build_strategy_overview

        overview = await build_strategy_overview(db)
        wiki_pct = float((overview.get("tech_brand") or {}).get("wiki_compliance_pct") or 0)
    except Exception:
        pass

    sentiment = kpis.get("sentiment_score")
    if wiki_pct >= 70 and (sentiment is None or sentiment < 70):
        insights.append(
            {
                "insight_type": "authority_endorsement",
                "title": "权威背书强化",
                "body": "Wiki 合规率高但 AI 好感度偏低，建议强化 Schema/FAQ 与 Gweb 同步。",
                "payload": {"wiki_compliance_pct": wiki_pct, "sentiment_score": sentiment},
            }
        )

    for item in insights[:5]:
        await db.execute(
            text(
                """
                INSERT INTO geo_monitor_insights (insight_type, title, body, payload, status)
                VALUES (:t, :title, :body, CAST(:payload AS JSON), 'active')
                """
            ),
            {
                "t": item["insight_type"],
                "title": item["title"],
                "body": item["body"],
                "payload": json.dumps(item["payload"], ensure_ascii=False),
            },
        )

    logger.info("monitor_insights_generated count=%s", len(insights))
    return insights
