"""缺口补缺实验闭环：建 Task → 发布 → 延迟再扫 → lift。"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists
from app.services.geoeval.monitor_probe import aggregate_scene_visibility

logger = logging.getLogger(__name__)

STATUS_PENDING = "pending_publish"
STATUS_AWAITING = "awaiting_rescan"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"


async def _load_remediation_delay_hours(db: AsyncSession) -> int:
    if not await _table_exists(db, "site_settings"):
        return 72
    row = (
        await db.execute(
            text(
                "SELECT setting_value FROM site_settings WHERE setting_key = 'remediation_delay_hours' LIMIT 1"
            )
        )
    ).scalar_one_or_none()
    try:
        hours = int(row) if row is not None else 72
        return max(0, min(hours, 24 * 30))
    except (TypeError, ValueError):
        return 72


async def _load_strict_api(db: AsyncSession) -> bool:
    if not await _table_exists(db, "site_settings"):
        return False
    row = (
        await db.execute(
            text("SELECT setting_value FROM site_settings WHERE setting_key = 'monitor_strict_api' LIMIT 1")
        )
    ).scalar_one_or_none()
    return str(row or "").lower() in ("1", "true", "yes", "on")


async def create_remediation_for_gap(
    db: AsyncSession,
    *,
    scene_id: int,
    task_id: int,
    gap_rate: float,
    gap_priority: str | None = None,
    theme_id: int | None = None,
) -> dict:
    if not await _table_exists(db, "geo_gap_remediation_runs"):
        logger.warning("remediation_table_missing scene_id=%s task_id=%s", scene_id, task_id)
        return {"status": "skipped", "reason": "remediation_table_missing"}

    trusted_only = await _load_strict_api(db)
    baseline = await aggregate_scene_visibility(db, scene_id, trusted_only=trusted_only)
    meta = {
        "source": "monitor_gap" if not theme_id else "theme",
        "gap_priority": gap_priority,
        "trusted_only": trusted_only,
        "baseline_probe_count": baseline.get("probe_count", 0),
        "baseline_engine_mix": baseline.get("engine_mix", []),
        "baseline_top3_pct": baseline.get("top3_pct"),
        "theme_id": theme_id,
    }
    try:
        row = (
            await db.execute(
                text(
                    """
                    INSERT INTO geo_gap_remediation_runs
                        (scene_id, task_id, theme_id, status, gap_rate_at_create,
                         baseline_visibility_pct, baseline_top3_pct, baseline_run_id, meta)
                    VALUES
                        (:scene_id, :task_id, :theme_id, :status, :gap_rate,
                         :baseline_vis, :baseline_top3, :baseline_run, CAST(:meta AS JSON))
                    RETURNING id
                    """
                ),
                {
                    "scene_id": scene_id,
                    "task_id": task_id,
                    "theme_id": theme_id,
                    "status": STATUS_PENDING,
                    "gap_rate": gap_rate,
                    "baseline_vis": baseline.get("visibility_pct"),
                    "baseline_top3": baseline.get("top3_pct"),
                    "baseline_run": baseline.get("latest_run_id"),
                    "meta": json.dumps(meta, ensure_ascii=False),
                },
            )
        ).first()
    except Exception:
        logger.warning("remediation_insert_theme_fallback", exc_info=True)
        try:
            row = (
                await db.execute(
                    text(
                        """
                        INSERT INTO geo_gap_remediation_runs
                            (scene_id, task_id, status, gap_rate_at_create,
                             baseline_visibility_pct, baseline_top3_pct, baseline_run_id, meta)
                        VALUES
                            (:scene_id, :task_id, :status, :gap_rate,
                             :baseline_vis, :baseline_top3, :baseline_run, CAST(:meta AS JSON))
                        RETURNING id
                        """
                    ),
                    {
                        "scene_id": scene_id,
                        "task_id": task_id,
                        "status": STATUS_PENDING,
                        "gap_rate": gap_rate,
                        "baseline_vis": baseline.get("visibility_pct"),
                        "baseline_top3": baseline.get("top3_pct"),
                        "baseline_run": baseline.get("latest_run_id"),
                        "meta": json.dumps(meta, ensure_ascii=False),
                    },
                )
            ).first()
        except Exception:
            logger.warning("remediation_insert_top3_fallback", exc_info=True)
            row = (
                await db.execute(
                    text(
                        """
                        INSERT INTO geo_gap_remediation_runs
                            (scene_id, task_id, status, gap_rate_at_create,
                             baseline_visibility_pct, baseline_run_id, meta)
                        VALUES
                            (:scene_id, :task_id, :status, :gap_rate,
                             :baseline_vis, :baseline_run, CAST(:meta AS JSON))
                        RETURNING id
                        """
                    ),
                    {
                        "scene_id": scene_id,
                        "task_id": task_id,
                        "status": STATUS_PENDING,
                        "gap_rate": gap_rate,
                        "baseline_vis": baseline.get("visibility_pct"),
                        "baseline_run": baseline.get("latest_run_id"),
                        "meta": json.dumps(meta, ensure_ascii=False),
                    },
                )
            ).first()
    remediation_id = int(row[0]) if row else None
    logger.info(
        "remediation_created id=%s scene_id=%s task_id=%s theme_id=%s baseline_vis=%s baseline_top3=%s trusted_only=%s",
        remediation_id,
        scene_id,
        task_id,
        theme_id,
        baseline.get("visibility_pct"),
        baseline.get("top3_pct"),
        trusted_only,
    )
    return {
        "remediation_id": remediation_id,
        "scene_id": scene_id,
        "task_id": task_id,
        "theme_id": theme_id,
        "status": STATUS_PENDING,
        "baseline_visibility_pct": baseline.get("visibility_pct"),
        "baseline_top3_pct": baseline.get("top3_pct"),
        "gap_rate_at_create": gap_rate,
    }


async def mark_remediation_published(db: AsyncSession, *, task_id: int, article_id: int) -> dict:
    if not await _table_exists(db, "geo_gap_remediation_runs"):
        return {"status": "skipped", "reason": "remediation_table_missing"}

    rows = (
        await db.execute(
            text(
                """
                SELECT id, article_ids, status FROM geo_gap_remediation_runs
                WHERE task_id = :tid AND status IN (:p, :a)
                ORDER BY id DESC
                """
            ),
            {"tid": task_id, "p": STATUS_PENDING, "a": STATUS_AWAITING},
        )
    ).all()
    if not rows:
        return {"status": "skipped", "reason": "no_open_remediation"}

    delay_hours = await _load_remediation_delay_hours(db)
    now = datetime.utcnow()
    rescan_after = now + timedelta(hours=delay_hours)
    updated = 0
    for rid, article_ids, status in rows:
        ids: list[int] = []
        if isinstance(article_ids, list):
            ids = [int(x) for x in article_ids]
        elif isinstance(article_ids, str):
            try:
                ids = [int(x) for x in json.loads(article_ids)]
            except json.JSONDecodeError:
                ids = []
        if article_id not in ids:
            ids.append(article_id)
        await db.execute(
            text(
                """
                UPDATE geo_gap_remediation_runs
                SET status = :st,
                    article_ids = CAST(:aids AS JSON),
                    published_at = COALESCE(published_at, :now),
                    rescan_after = :rescan,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """
            ),
            {
                "st": STATUS_AWAITING,
                "aids": json.dumps(ids),
                "now": now,
                "rescan": rescan_after,
                "id": int(rid),
            },
        )
        updated += 1
        logger.info(
            "remediation_published id=%s task_id=%s article_id=%s rescan_after=%s prev_status=%s",
            rid,
            task_id,
            article_id,
            rescan_after.isoformat(),
            status,
        )
    return {
        "status": "ok",
        "updated": updated,
        "rescan_after": rescan_after.isoformat(),
        "delay_hours": delay_hours,
    }


async def complete_remediation_rescan(db: AsyncSession, remediation_id: int) -> dict:
    from app.services.geoeval.monitor_scan import MonitorScanOrchestrator

    if not await _table_exists(db, "geo_gap_remediation_runs"):
        return {"status": "skipped", "reason": "remediation_table_missing"}

    baseline_top3 = None
    try:
        row = (
            await db.execute(
                text(
                    """
                    SELECT id, scene_id, task_id, baseline_visibility_pct, status, meta,
                           baseline_top3_pct
                    FROM geo_gap_remediation_runs WHERE id = :id
                    """
                ),
                {"id": remediation_id},
            )
        ).first()
        if row and row[6] is not None:
            baseline_top3 = float(row[6])
    except Exception:
        row = None
    if not row:
        row = (
            await db.execute(
                text(
                    """
                    SELECT id, scene_id, task_id, baseline_visibility_pct, status, meta
                    FROM geo_gap_remediation_runs WHERE id = :id
                    """
                ),
                {"id": remediation_id},
            )
        ).first()
        if not row:
            return {"status": "not_found", "remediation_id": remediation_id}

    if str(row[4]) == STATUS_COMPLETED:
        return {"status": "already_completed", "remediation_id": remediation_id}

    scene_id = int(row[1])
    meta = row[5] if isinstance(row[5], dict) else {}
    if isinstance(row[5], str):
        try:
            meta = json.loads(row[5])
        except json.JSONDecodeError:
            meta = {}
    if baseline_top3 is None and meta.get("baseline_top3_pct") is not None:
        try:
            baseline_top3 = float(meta["baseline_top3_pct"])
        except (TypeError, ValueError):
            baseline_top3 = None
    trusted_only = bool(meta.get("trusted_only")) or await _load_strict_api(db)

    scan = await MonitorScanOrchestrator(db).run_scan("remediation", scene_id=scene_id)
    post = await aggregate_scene_visibility(
        db,
        scene_id,
        run_id=scan.get("run_id"),
        trusted_only=trusted_only,
    )
    baseline = float(row[3]) if row[3] is not None else None
    post_vis = post.get("visibility_pct")
    delta = None
    if baseline is not None and post_vis is not None:
        delta = round(float(post_vis) - float(baseline), 2)

    post_top3 = post.get("top3_pct")
    delta_top3 = None
    if baseline_top3 is not None and post_top3 is not None:
        delta_top3 = round(float(post_top3) - float(baseline_top3), 2)

    try:
        await db.execute(
            text(
                """
                UPDATE geo_gap_remediation_runs
                SET status = :st,
                    post_visibility_pct = :post_vis,
                    post_run_id = :post_run,
                    delta_visibility_pct = :delta,
                    post_top3_pct = :post_top3,
                    delta_top3_pp = :delta_top3,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """
            ),
            {
                "st": STATUS_COMPLETED,
                "post_vis": post_vis,
                "post_run": scan.get("run_id"),
                "delta": delta,
                "post_top3": post_top3,
                "delta_top3": delta_top3,
                "id": remediation_id,
            },
        )
    except Exception:
        logger.warning("remediation_update_top3_fallback", exc_info=True)
        await db.execute(
            text(
                """
                UPDATE geo_gap_remediation_runs
                SET status = :st,
                    post_visibility_pct = :post_vis,
                    post_run_id = :post_run,
                    delta_visibility_pct = :delta,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """
            ),
            {
                "st": STATUS_COMPLETED,
                "post_vis": post_vis,
                "post_run": scan.get("run_id"),
                "delta": delta,
                "id": remediation_id,
            },
        )
    logger.info(
        "remediation_completed id=%s scene_id=%s baseline=%s post=%s delta=%s delta_top3=%s run_id=%s",
        remediation_id,
        scene_id,
        baseline,
        post_vis,
        delta,
        delta_top3,
        scan.get("run_id"),
    )
    return {
        "status": STATUS_COMPLETED,
        "remediation_id": remediation_id,
        "scene_id": scene_id,
        "baseline_visibility_pct": baseline,
        "post_visibility_pct": post_vis,
        "delta_visibility_pct": delta,
        "baseline_top3_pct": baseline_top3,
        "post_top3_pct": post_top3,
        "delta_top3_pp": delta_top3,
        "scan": scan,
    }


async def process_due_remediations(db: AsyncSession, limit: int = 20) -> dict:
    if not await _table_exists(db, "geo_gap_remediation_runs"):
        return {"status": "skipped", "processed": 0}

    rows = (
        await db.execute(
            text(
                """
                SELECT id FROM geo_gap_remediation_runs
                WHERE status = :st
                  AND rescan_after IS NOT NULL
                  AND rescan_after <= CURRENT_TIMESTAMP
                ORDER BY rescan_after ASC
                LIMIT :lim
                """
            ),
            {"st": STATUS_AWAITING, "lim": limit},
        )
    ).all()
    results = []
    for (rid,) in rows:
        try:
            results.append(await complete_remediation_rescan(db, int(rid)))
        except Exception as exc:  # noqa: BLE001
            logger.exception("remediation_rescan_failed id=%s error=%s", rid, exc)
            results.append({"remediation_id": int(rid), "status": "error", "error": str(exc)[:200]})
    logger.info("remediation_due_processed count=%s", len(results))
    return {"status": "ok", "processed": len(results), "items": results}


async def list_remediations(db: AsyncSession, limit: int = 30) -> dict:
    if not await _table_exists(db, "geo_gap_remediation_runs"):
        return {"items": [], "status": "table_missing"}
    try:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT r.id, r.scene_id, r.task_id, r.status, r.gap_rate_at_create,
                           r.baseline_visibility_pct, r.post_visibility_pct, r.delta_visibility_pct,
                           r.published_at, r.rescan_after, r.created_at,
                           s.scene_name,
                           r.baseline_top3_pct, r.post_top3_pct, r.delta_top3_pp,
                           r.theme_id, t.title AS theme_title
                    FROM geo_gap_remediation_runs r
                    LEFT JOIN geo_monitor_scenes s ON s.id = r.scene_id
                    LEFT JOIN geo_themes t ON t.id = r.theme_id
                    ORDER BY r.id DESC
                    LIMIT :lim
                    """
                ),
                {"lim": limit},
            )
        ).all()
        has_top3 = True
        has_theme = True
    except Exception:
        try:
            rows = (
                await db.execute(
                    text(
                        """
                        SELECT r.id, r.scene_id, r.task_id, r.status, r.gap_rate_at_create,
                               r.baseline_visibility_pct, r.post_visibility_pct, r.delta_visibility_pct,
                               r.published_at, r.rescan_after, r.created_at,
                               s.scene_name,
                               r.baseline_top3_pct, r.post_top3_pct, r.delta_top3_pp
                        FROM geo_gap_remediation_runs r
                        LEFT JOIN geo_monitor_scenes s ON s.id = r.scene_id
                        ORDER BY r.id DESC
                        LIMIT :lim
                        """
                    ),
                    {"lim": limit},
                )
            ).all()
            has_top3 = True
            has_theme = False
        except Exception:
            rows = (
                await db.execute(
                    text(
                        """
                        SELECT r.id, r.scene_id, r.task_id, r.status, r.gap_rate_at_create,
                               r.baseline_visibility_pct, r.post_visibility_pct, r.delta_visibility_pct,
                               r.published_at, r.rescan_after, r.created_at,
                               s.scene_name
                        FROM geo_gap_remediation_runs r
                        LEFT JOIN geo_monitor_scenes s ON s.id = r.scene_id
                        ORDER BY r.id DESC
                        LIMIT :lim
                        """
                    ),
                    {"lim": limit},
                )
            ).all()
            has_top3 = False
            has_theme = False
    items = []
    for row in rows:
        items.append(
            {
                "id": int(row[0]),
                "scene_id": int(row[1]),
                "task_id": int(row[2]) if row[2] else None,
                "status": str(row[3]),
                "gap_rate_at_create": float(row[4] or 0),
                "baseline_visibility_pct": float(row[5]) if row[5] is not None else None,
                "post_visibility_pct": float(row[6]) if row[6] is not None else None,
                "delta_visibility_pct": float(row[7]) if row[7] is not None else None,
                "published_at": row[8].isoformat() if row[8] else None,
                "rescan_after": row[9].isoformat() if row[9] else None,
                "created_at": row[10].isoformat() if row[10] else None,
                "scene_name": str(row[11] or ""),
                "baseline_top3_pct": float(row[12]) if has_top3 and len(row) > 12 and row[12] is not None else None,
                "post_top3_pct": float(row[13]) if has_top3 and len(row) > 13 and row[13] is not None else None,
                "delta_top3_pp": float(row[14]) if has_top3 and len(row) > 14 and row[14] is not None else None,
                "theme_id": int(row[15]) if has_theme and len(row) > 15 and row[15] is not None else None,
                "theme_title": str(row[16] or "") if has_theme and len(row) > 16 else "",
            }
        )
    return {"items": items}
