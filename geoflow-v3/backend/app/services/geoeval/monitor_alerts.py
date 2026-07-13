"""Monitor 告警 — visibility / gap / sentiment。"""

import json
import logging
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists
from app.services.geoeval.monitor_probe import aggregate_probe_kpis

logger = logging.getLogger(__name__)


async def _create_alert(db: AsyncSession, alert_type: str, message: str, payload: dict) -> None:
    if not await _table_exists(db, "geo_admin_alerts"):
        logger.warning("geo_admin_alerts_table_missing")
        return
    await db.execute(
        text(
            "INSERT INTO geo_admin_alerts (alert_type, message, payload_json) VALUES (:t, :m, CAST(:p AS JSON))"
        ),
        {"t": alert_type, "m": message, "p": json.dumps(payload, ensure_ascii=False)},
    )
    logger.info("monitor_alert_created type=%s", alert_type)


async def check_monitor_alerts(db: AsyncSession) -> dict:
    created = 0
    kpis = await aggregate_probe_kpis(db)

    if await _table_exists(db, "geo_monitor_snapshots"):
        week_ago = date.today() - timedelta(days=7)
        old_row = (
            await db.execute(
                text("SELECT visibility_pct FROM geo_monitor_snapshots WHERE snapshot_date <= :d ORDER BY snapshot_date DESC LIMIT 1"),
                {"d": week_ago},
            )
        ).scalar_one_or_none()
        if old_row is not None:
            current = float(kpis.get("visibility_pct") or 0)
            old = float(old_row)
            if old - current > 10:
                await _create_alert(
                    db,
                    "visibility_drop",
                    f"7 日可见性下降 {old - current:.1f}pp（{old}% → {current}%）",
                    {"old": old, "current": current},
                )
                created += 1

    if await _table_exists(db, "geo_monitor_scenes"):
        high_gap = int(
            await db.scalar(
                text("SELECT COUNT(*) FROM geo_monitor_scenes WHERE gap_priority = 'high' AND status = 'active'")
            )
            or 0
        )
        if high_gap > 0:
            await _create_alert(
                db,
                "gap_high",
                f"{high_gap} 个场景缺口率超过 50%",
                {"high_gap_scenes": high_gap},
            )
            created += 1

    try:
        neg_topics = int(
            await db.scalar(
                text(
                    """
                    SELECT COUNT(*) FROM geo_monitor_probe_results
                    WHERE sentiment IS NOT NULL AND sentiment->>'polarity' = 'negative'
                      AND created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
                    """
                )
            )
            or 0
        )
        if neg_topics >= 3:
            await _create_alert(
                db,
                "sentiment_negative_spike",
                f"近 7 日负向情感探针 {neg_topics} 条",
                {"negative_count": neg_topics},
            )
            created += 1
    except Exception:
        pass

    return {"alerts_created": created, "visibility_pct": kpis.get("visibility_pct")}
