"""框架轨扫描（scheme=framework_api）：明文 CoT + C 回答，不进 open_api KPI。"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists
from app.services.geoeval.framework_extractor import extract_framework
from app.services.geoeval.monitor_probe import _persist_probe, load_brand_keywords
from app.services.geoeval.platform_connectors.api_connector import ApiConnector
from app.services.geoeval.probe_scheme import SCHEME_FRAMEWORK_API, stamp_outcome

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 12
HARD_CAP = 12


def _platforms() -> list[str]:
    raw = os.getenv("FRAMEWORK_SCAN_PLATFORMS", "deepseek")
    plats = [p.strip() for p in raw.split(",") if p.strip()]
    return plats or ["deepseek"]


class FrameworkScanOrchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._api = ApiConnector()

    async def run_scan(
        self,
        *,
        platforms: list[str] | None = None,
        limit: int = DEFAULT_LIMIT,
        min_priority: int = 80,
        scene_id: int | None = None,
        sync_mock: bool = False,
    ) -> dict:
        plats = platforms or _platforms()
        lim = max(1, min(HARD_CAP, int(limit)))
        brands = await load_brand_keywords(self.db)
        questions = await self._load_questions(lim, min_priority, scene_id)
        if not questions:
            logger.info("framework_scan_empty min_priority=%s scene_id=%s", min_priority, scene_id)
            return {"scan_type": "framework_api", "probes": 0, "questions": 0, "run_id": None}

        run_id = await self._create_run(plats, len(questions))
        outcomes_n = 0
        raw_n = 0
        for qid, qtext, _prio, comps in questions:
            for platform in plats:
                outcome = await self._api.probe(
                    question_text=qtext,
                    priority=_prio,
                    platform=platform,
                    corpus=[],
                    brand_list=brands,
                    competitor_brands=comps,
                    scheme=SCHEME_FRAMEWORK_API,
                )
                if outcome is None:
                    logger.warning(
                        "framework_scan_skip platform=%s question_id=%s",
                        platform,
                        qid,
                    )
                    continue
                stamp_outcome(outcome, scheme=SCHEME_FRAMEWORK_API)
                outcome.question_id = qid
                fw = extract_framework(outcome.thinking_text or "", scene_name="", intent="")
                outcome.framework = fw
                await _persist_probe(self.db, run_id=run_id, outcome=outcome, question_text=qtext)
                outcomes_n += 1
                if (outcome.reasoning_grade or "") == "raw":
                    raw_n += 1
                logger.info(
                    "framework_probe_ok scheme=%s tracks=%s reasoning_grade=%s platform=%s question_id=%s run_id=%s",
                    outcome.scheme,
                    outcome.tracks,
                    outcome.reasoning_grade,
                    platform,
                    qid,
                    run_id,
                )

        await self._finish_run(run_id, outcomes_n)
        logger.info(
            "framework_scan_completed run_id=%s questions=%s probes=%s raw_cot=%s platforms=%s sync_mock=%s",
            run_id,
            len(questions),
            outcomes_n,
            raw_n,
            plats,
            sync_mock,
        )
        return {
            "scan_type": "framework_api",
            "run_id": run_id,
            "questions": len(questions),
            "probes": outcomes_n,
            "raw_cot": raw_n,
            "platforms": plats,
            "metric_kind": "framework_sample",
        }

    async def _load_questions(
        self, limit: int, min_priority: int, scene_id: int | None
    ) -> list[tuple[int, str, int, list[str] | None]]:
        if not await _table_exists(self.db, "geo_monitor_questions"):
            return []
        params: dict = {"lim": limit, "floor": min_priority}
        extra = ""
        if scene_id is not None:
            extra = " AND scene_id = :sid"
            params["sid"] = scene_id
        rows = (
            await self.db.execute(
                text(
                    f"""
                    SELECT id, question_text, priority, competitor_brands
                    FROM geo_monitor_questions
                    WHERE status = 'active' AND priority >= :floor {extra}
                    ORDER BY priority DESC, id ASC
                    LIMIT :lim
                    """
                ),
                params,
            )
        ).all()
        out: list[tuple[int, str, int, list[str] | None]] = []
        for r in rows:
            comps = r[3]
            if isinstance(comps, str):
                try:
                    comps = json.loads(comps)
                except Exception:
                    comps = [p.strip() for p in comps.split(",") if p.strip()]
            out.append((int(r[0]), str(r[1] or ""), int(r[2] or 0), list(comps) if comps else None))
        return out

    async def _create_run(self, platforms: list[str], qcount: int) -> int | None:
        if not await _table_exists(self.db, "geo_monitor_runs"):
            return None
        row = (
            await self.db.execute(
                text(
                    """
                    INSERT INTO geo_monitor_runs (status, platform, question_count, probe_count, started_at)
                    VALUES ('running', :plat, :qc, 0, :ts)
                    RETURNING id
                    """
                ),
                {
                    "plat": f"framework_api:{','.join(platforms)}"[:200],
                    "qc": qcount,
                    "ts": datetime.now(timezone.utc).replace(tzinfo=None),
                },
            )
        ).first()
        return int(row[0]) if row else None

    async def _finish_run(self, run_id: int | None, probe_count: int) -> None:
        if not run_id or not await _table_exists(self.db, "geo_monitor_runs"):
            return
        await self.db.execute(
            text(
                """
                UPDATE geo_monitor_runs
                SET status = 'completed', probe_count = :pc, completed_at = :ts
                WHERE id = :id
                """
            ),
            {"pc": probe_count, "ts": datetime.now(timezone.utc).replace(tzinfo=None), "id": run_id},
        )
