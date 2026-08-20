"""Monitor 运行与探针明细 — Admin BFF。"""

import logging

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists

logger = logging.getLogger(__name__)


async def list_monitor_runs(db: AsyncSession, limit: int = 20) -> dict:
    if not await _table_exists(db, "geo_monitor_runs"):
        return {"items": []}
    rows = (
        await db.execute(
            text(
                """
                SELECT id, status, platform, question_count, probe_count, started_at, completed_at
                FROM geo_monitor_runs
                ORDER BY id DESC
                LIMIT :lim
                """
            ),
            {"lim": limit},
        )
    ).all()
    return {
        "items": [
            {
                "id": int(r[0]),
                "status": r[1],
                "platform": r[2],
                "question_count": int(r[3] or 0),
                "probe_count": int(r[4] or 0),
                "started_at": r[5].isoformat() if r[5] else None,
                "completed_at": r[6].isoformat() if r[6] else None,
            }
            for r in rows
        ]
    }


async def build_monitor_run_detail(db: AsyncSession, run_id: int) -> dict:
    if not await _table_exists(db, "geo_monitor_runs"):
        raise HTTPException(status_code=404, detail="run_not_found")

    run = (
        await db.execute(
            text(
                """
                SELECT id, status, platform, question_count, probe_count, started_at, completed_at
                FROM geo_monitor_runs WHERE id = :id
                """
            ),
            {"id": run_id},
        )
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="run_not_found")

    probes: list[dict] = []
    if await _table_exists(db, "geo_monitor_probe_results"):
        rows = None
        try:
            rows = (
                await db.execute(
                    text(
                        """
                        SELECT pr.id, pr.question_id, pr.platform, pr.brand_rank, pr.mentioned,
                               pr.snippet, pr.engine, mq.question_text,
                               pr.scheme, pr.metric_kind, pr.match_type
                        FROM geo_monitor_probe_results pr
                        JOIN geo_monitor_questions mq ON mq.id = pr.question_id
                        WHERE pr.run_id = :rid
                        ORDER BY pr.question_id, pr.platform
                        """
                    ),
                    {"rid": run_id},
                )
            ).all()
        except Exception:
            logger.debug("monitor_run_detail_scheme_fallback", exc_info=True)
            rows = (
                await db.execute(
                    text(
                        """
                        SELECT pr.id, pr.question_id, pr.platform, pr.brand_rank, pr.mentioned,
                               pr.snippet, pr.engine, mq.question_text
                        FROM geo_monitor_probe_results pr
                        JOIN geo_monitor_questions mq ON mq.id = pr.question_id
                        WHERE pr.run_id = :rid
                        ORDER BY pr.question_id, pr.platform
                        """
                    ),
                    {"rid": run_id},
                )
            ).all()
        probes = [
            {
                "id": int(r[0]),
                "question_id": int(r[1]),
                "platform": r[2],
                "brand_rank": int(r[3]) if r[3] is not None else None,
                "mentioned": bool(r[4]),
                "snippet": r[5] or "",
                "engine": r[6] or "corpus",
                "question_text": r[7] or "",
                "scheme": str(r[8]) if len(r) > 8 and r[8] else "open_api",
                "metric_kind": str(r[9]) if len(r) > 9 and r[9] else None,
                "match_type": str(r[10]) if len(r) > 10 and r[10] else None,
            }
            for r in rows
        ]

    mentioned = sum(1 for p in probes if p["mentioned"])
    by_platform: dict[str, dict] = {}
    for p in probes:
        bucket = by_platform.setdefault(
            p["platform"],
            {"platform": p["platform"], "total": 0, "mentions": 0, "ranks": []},
        )
        bucket["total"] += 1
        if p["mentioned"]:
            bucket["mentions"] += 1
        if p["brand_rank"] is not None:
            bucket["ranks"].append(p["brand_rank"])

    platform_stats = []
    for plat, bucket in sorted(by_platform.items()):
        ranks = bucket["ranks"]
        platform_stats.append(
            {
                "platform": plat,
                "total": bucket["total"],
                "mentions": bucket["mentions"],
                "avg_rank": round(sum(ranks) / len(ranks), 2) if ranks else None,
            }
        )

    return {
        "run": {
            "id": int(run[0]),
            "status": run[1],
            "platform": run[2],
            "question_count": int(run[3] or 0),
            "probe_count": int(run[4] or 0),
            "started_at": run[5].isoformat() if run[5] else None,
            "completed_at": run[6].isoformat() if run[6] else None,
            "mention_rate": round(mentioned / len(probes), 3) if probes else 0.0,
        },
        "probes": probes,
        "platform_stats": platform_stats,
    }
