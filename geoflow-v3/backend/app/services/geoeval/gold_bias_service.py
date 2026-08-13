"""辅轨金标：导入 / 列表 / Open-API 偏移（不覆盖 visibility_open_api）。"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists

logger = logging.getLogger(__name__)


async def list_gold_labels(db: AsyncSession, *, limit: int = 100) -> dict:
    if not await _table_exists(db, "geo_probe_gold_labels"):
        return {"items": [], "status": "table_missing"}
    rows = (
        await db.execute(
            text(
                """
                SELECT id, question_id, platform, source, mentioned, brand_rank,
                       snippet, cited_urls, open_api_probe_id, notes, captured_at, created_at
                FROM geo_probe_gold_labels
                ORDER BY captured_at DESC NULLS LAST, id DESC
                LIMIT :lim
                """
            ),
            {"lim": limit},
        )
    ).all()
    items = []
    for r in rows:
        cited = r[7]
        if isinstance(cited, str):
            try:
                cited = json.loads(cited)
            except json.JSONDecodeError:
                cited = []
        items.append(
            {
                "id": int(r[0]),
                "question_id": int(r[1]) if r[1] is not None else None,
                "platform": r[2],
                "source": r[3],
                "mentioned": bool(r[4]),
                "brand_rank": int(r[5]) if r[5] is not None else None,
                "snippet": r[6] or "",
                "cited_urls": cited or [],
                "open_api_probe_id": int(r[8]) if r[8] is not None else None,
                "notes": r[9] or "",
                "captured_at": r[10].isoformat() if r[10] else None,
                "created_at": r[11].isoformat() if r[11] else None,
            }
        )
    return {"items": items, "status": "ok", "count": len(items)}


async def upsert_gold_label(db: AsyncSession, body: dict[str, Any]) -> dict:
    if not await _table_exists(db, "geo_probe_gold_labels"):
        return {"status": "table_missing"}
    question_id = body.get("question_id")
    platform = str(body.get("platform") or "").strip()
    if not platform:
        raise ValueError("platform_required")
    cited = body.get("cited_urls") or []
    if not isinstance(cited, list):
        cited = []
    captured_at = body.get("captured_at")
    row = (
        await db.execute(
            text(
                """
                INSERT INTO geo_probe_gold_labels
                    (question_id, platform, source, mentioned, brand_rank, snippet,
                     cited_urls, open_api_probe_id, notes, captured_at)
                VALUES
                    (:qid, :plat, :src, :men, :rank, :snip,
                     CAST(:urls AS JSONB), :opid, :notes, COALESCE(:cap, CURRENT_TIMESTAMP))
                RETURNING id
                """
            ),
            {
                "qid": int(question_id) if question_id is not None else None,
                "plat": platform,
                "src": str(body.get("source") or "manual")[:32],
                "men": bool(body.get("mentioned", False)),
                "rank": int(body["brand_rank"]) if body.get("brand_rank") is not None else None,
                "snip": str(body.get("snippet") or "")[:2000],
                "urls": json.dumps(cited, ensure_ascii=False),
                "opid": int(body["open_api_probe_id"]) if body.get("open_api_probe_id") is not None else None,
                "notes": str(body.get("notes") or "")[:1000],
                "cap": captured_at,
            },
        )
    ).first()
    await db.flush()
    logger.info("gold_label_upserted id=%s platform=%s qid=%s", row[0] if row else None, platform, question_id)
    return {"id": int(row[0]) if row else None, "status": "ok"}


async def import_gold_jsonl(db: AsyncSession, lines: list[str]) -> dict:
    created = 0
    errors: list[str] = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            body = json.loads(line)
            if not isinstance(body, dict):
                raise ValueError("not_object")
            await upsert_gold_label(db, body)
            created += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"line {i + 1}: {exc}")
    return {"status": "ok", "created": created, "errors": errors[:20]}


async def compute_gold_bias(db: AsyncSession, *, days: int = 30) -> dict:
    """对照同题同平台最近 open_api 探针与金标，输出偏移摘要（不改写主 KPI）。"""
    if not await _table_exists(db, "geo_probe_gold_labels"):
        return {"status": "table_missing", "sample_n": 0}
    if not await _table_exists(db, "geo_monitor_probe_results"):
        return {"status": "probe_table_missing", "sample_n": 0}

    golds = (
        await db.execute(
            text(
                """
                SELECT id, question_id, platform, mentioned, brand_rank, captured_at
                FROM geo_probe_gold_labels
                WHERE captured_at >= CURRENT_TIMESTAMP - (:days || ' days')::interval
                   OR created_at >= CURRENT_TIMESTAMP - (:days || ' days')::interval
                ORDER BY captured_at DESC NULLS LAST
                LIMIT 200
                """
            ),
            {"days": str(int(days))},
        )
    ).all()

    pairs = []
    mention_deltas = []
    rank_deltas = []
    for g in golds:
        gid, qid, platform, g_men, g_rank, _cap = g
        if qid is None:
            continue
        probe = (
            await db.execute(
                text(
                    """
                    SELECT id, mentioned, brand_rank, engine
                    FROM geo_monitor_probe_results
                    WHERE question_id = :qid AND platform = :plat
                      AND COALESCE(engine, '') IN ('api', 'llm')
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ),
                {"qid": int(qid), "plat": str(platform)},
            )
        ).first()
        if not probe:
            continue
        api_men = bool(probe[1])
        api_rank = int(probe[2]) if probe[2] is not None else None
        gold_men = bool(g_men)
        gold_rank = int(g_rank) if g_rank is not None else None
        mention_deltas.append((1 if api_men else 0) - (1 if gold_men else 0))
        if api_rank is not None and gold_rank is not None:
            rank_deltas.append(api_rank - gold_rank)
        pairs.append(
            {
                "gold_id": int(gid),
                "question_id": int(qid),
                "platform": platform,
                "probe_id": int(probe[0]),
                "api_mentioned": api_men,
                "gold_mentioned": gold_men,
                "api_rank": api_rank,
                "gold_rank": gold_rank,
            }
        )

    sample_n = len(pairs)
    mean_mention_delta = round(sum(mention_deltas) / sample_n, 3) if sample_n else None
    mean_rank_delta = round(sum(rank_deltas) / len(rank_deltas), 2) if rank_deltas else None
    mention_agree = (
        round(sum(1 for p in pairs if p["api_mentioned"] == p["gold_mentioned"]) / sample_n, 3)
        if sample_n
        else None
    )

    result = {
        "status": "ok",
        "metric_kind": "cend_sample_bias",
        "do_not_overwrite_open_api_kpi": True,
        "sample_n": sample_n,
        "days": days,
        "mean_mention_delta": mean_mention_delta,
        "mean_rank_delta": mean_rank_delta,
        "mention_agreement": mention_agree,
        "pairs": pairs[:30],
        "footnote": (
            f"金标辅轨 n={sample_n}：提及一致率 "
            f"{(mention_agree * 100):.0f}%" if mention_agree is not None else f"金标辅轨 n={sample_n}：样本不足"
        )
        + (
            f"；平均 rank 偏移 {mean_rank_delta:+.1f}" if mean_rank_delta is not None else ""
        )
        + "（不覆盖 visibility_open_api）",
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info(
        "gold_bias_computed sample_n=%s mention_agree=%s rank_delta=%s",
        sample_n,
        mention_agree,
        mean_rank_delta,
    )
    return result
