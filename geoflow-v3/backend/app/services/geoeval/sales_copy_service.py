"""销售口径 SSOT：话术 / 对比卖点 / 场景答法。"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists

logger = logging.getLogger(__name__)

COPY_TYPES = frozenset({"talking_point", "compare_sell", "scene_answer", "faq"})


async def list_sales_copy(
    db: AsyncSession,
    *,
    scene_id: int | None = None,
    copy_type: str | None = None,
    limit: int = 100,
) -> dict:
    if not await _table_exists(db, "geo_sales_copy_assets"):
        return {"items": [], "status": "table_missing"}
    where = "WHERE status = 'active'"
    params: dict[str, Any] = {"lim": limit}
    if scene_id is not None:
        where += " AND scene_id = :sid"
        params["sid"] = scene_id
    if copy_type:
        where += " AND copy_type = :ct"
        params["ct"] = copy_type
    rows = (
        await db.execute(
            text(
                f"""
                SELECT id, title, copy_type, body, scene_id, tech_ip_asset_id,
                       version, status, meta, created_at, updated_at
                FROM geo_sales_copy_assets
                {where}
                ORDER BY updated_at DESC, id DESC
                LIMIT :lim
                """
            ),
            params,
        )
    ).all()
    items = [
        {
            "id": int(r[0]),
            "title": str(r[1]),
            "copy_type": str(r[2]),
            "body": str(r[3]),
            "scene_id": int(r[4]) if r[4] else None,
            "tech_ip_asset_id": int(r[5]) if r[5] else None,
            "version": int(r[6] or 1),
            "status": str(r[7]),
            "meta": r[8] or {},
            "created_at": r[9].isoformat() if r[9] else None,
            "updated_at": r[10].isoformat() if r[10] else None,
        }
        for r in rows
    ]
    logger.info("sales_copy_listed count=%s scene_id=%s type=%s", len(items), scene_id, copy_type)
    return {"items": items, "status": "ok"}


async def upsert_sales_copy(
    db: AsyncSession,
    *,
    title: str,
    body: str,
    copy_type: str = "talking_point",
    scene_id: int | None = None,
    tech_ip_asset_id: int | None = None,
    meta: dict | None = None,
    asset_id: int | None = None,
) -> dict:
    if not await _table_exists(db, "geo_sales_copy_assets"):
        return {"status": "skipped", "reason": "table_missing"}
    ct = copy_type if copy_type in COPY_TYPES else "talking_point"
    payload = json.dumps(meta or {}, ensure_ascii=False)
    if asset_id:
        row = (
            await db.execute(
                text(
                    """
                    UPDATE geo_sales_copy_assets
                    SET title = :t, body = :b, copy_type = :ct, scene_id = :sid,
                        tech_ip_asset_id = :tip, meta = CAST(:meta AS JSON),
                        version = version + 1, updated_at = NOW()
                    WHERE id = :id
                    RETURNING id, version
                    """
                ),
                {
                    "t": title.strip(),
                    "b": body,
                    "ct": ct,
                    "sid": scene_id,
                    "tip": tech_ip_asset_id,
                    "meta": payload,
                    "id": asset_id,
                },
            )
        ).first()
        logger.info("sales_copy_updated id=%s version=%s", asset_id, row[1] if row else None)
        return {"status": "ok", "id": asset_id, "version": int(row[1]) if row else None}
    row = (
        await db.execute(
            text(
                """
                INSERT INTO geo_sales_copy_assets
                    (title, copy_type, body, scene_id, tech_ip_asset_id, meta)
                VALUES (:t, :ct, :b, :sid, :tip, CAST(:meta AS JSON))
                RETURNING id, version
                """
            ),
            {
                "t": title.strip(),
                "ct": ct,
                "b": body,
                "sid": scene_id,
                "tip": tech_ip_asset_id,
                "meta": payload,
            },
        )
    ).first()
    new_id = int(row[0]) if row else None
    logger.info("sales_copy_created id=%s type=%s scene_id=%s", new_id, ct, scene_id)
    return {"status": "ok", "id": new_id, "version": int(row[1]) if row else 1}


async def compute_win_rate(db: AsyncSession) -> dict:
    """对比题中自有品牌 rank 优于竞品提及的样本占比（启发式）。"""
    if not await _table_exists(db, "geo_monitor_probe_results"):
        return {"win_rate_pct": None, "compare_samples": 0}
    has_intent = False
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
        has_intent = bool(col)
    except Exception:
        pass
    intent_filter = "AND COALESCE(mq.intent_type, 'cognition') = 'compare'" if has_intent else ""
    rows = (
        await db.execute(
            text(
                f"""
                SELECT pr.mentioned, pr.brand_rank, pr.competitor_mentions
                FROM geo_monitor_probe_results pr
                JOIN geo_monitor_questions mq ON mq.id = pr.question_id
                WHERE COALESCE(pr.engine, 'corpus') = 'api'
                  {intent_filter}
                """
            )
        )
    ).all()
    samples = 0
    wins = 0
    for mentioned, brand_rank, comps in rows:
        samples += 1
        has_comp = bool(comps) and comps not in ("[]", None, {})
        if mentioned and brand_rank and int(brand_rank) <= 3:
            wins += 1
        elif mentioned and not has_comp:
            wins += 1
    pct = round(wins / samples * 100, 1) if samples else None
    logger.info("win_rate_computed pct=%s samples=%s wins=%s", pct, samples, wins)
    return {"win_rate_pct": pct, "compare_samples": samples, "wins": wins}
