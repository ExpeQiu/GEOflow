"""引用轨扫描（scheme=citation_grounded）：答文 URL / 资料链 B+C，不进 open_api KPI。"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists
from app.services.geoeval.domain_catalog import load_domain_catalog
from app.services.geoeval.monitor_probe import _persist_probe, load_brand_keywords
from app.services.geoeval.platform_connectors.api_connector import ApiConnector
from app.services.geoeval.probe_scheme import SCHEME_CITATION, stamp_outcome

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 12
HARD_CAP = 12


def _platforms() -> list[str]:
    raw = os.getenv("CITATION_SCAN_PLATFORMS", "doubao,kimi")
    plats = [p.strip() for p in raw.split(",") if p.strip()]
    return plats or ["doubao"]


class CitationScanOrchestrator:
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
        catalog = await load_domain_catalog(self.db)
        official = list(catalog.get("official") or [])
        wiki = list(catalog.get("wiki") or [])
        questions = await self._load_questions(lim, min_priority, scene_id)
        if not questions:
            logger.info("citation_scan_empty min_priority=%s scene_id=%s", min_priority, scene_id)
            return {"scan_type": "citation_grounded", "probes": 0, "questions": 0, "run_id": None}

        run_id = await self._create_run(plats, len(questions))
        outcomes_n = 0
        with_b = 0
        ours_n = 0
        for qid, qtext, _prio, comps in questions:
            for platform in plats:
                outcome = await self._api.probe(
                    question_text=qtext,
                    priority=_prio,
                    platform=platform,
                    corpus=[],
                    brand_list=brands,
                    competitor_brands=comps,
                    scheme=SCHEME_CITATION,
                    official_domains=official,
                    wiki_domains=wiki,
                )
                if outcome is None:
                    logger.warning(
                        "citation_scan_skip platform=%s question_id=%s",
                        platform,
                        qid,
                    )
                    continue
                stamp_outcome(outcome, scheme=SCHEME_CITATION)
                outcome.question_id = qid
                await _persist_probe(self.db, run_id=run_id, outcome=outcome, question_text=qtext)
                outcomes_n += 1
                if "B" in (outcome.tracks or []):
                    with_b += 1
                if (outcome.match_type or "") == "domain_official":
                    ours_n += 1
                logger.info(
                    "citation_probe_ok scheme=%s tracks=%s match_type=%s urls=%s platform=%s question_id=%s run_id=%s",
                    outcome.scheme,
                    outcome.tracks,
                    outcome.match_type,
                    len(outcome.citation_urls or outcome.urls or []),
                    platform,
                    qid,
                    run_id,
                )

        await self._finish_run(run_id, outcomes_n)
        logger.info(
            "citation_scan_completed run_id=%s questions=%s probes=%s with_b=%s ours=%s platforms=%s sync_mock=%s",
            run_id,
            len(questions),
            outcomes_n,
            with_b,
            ours_n,
            plats,
            sync_mock,
        )
        return {
            "scan_type": "citation_grounded",
            "run_id": run_id,
            "questions": len(questions),
            "probes": outcomes_n,
            "with_b": with_b,
            "ours_cited": ours_n,
            "platforms": plats,
            "metric_kind": "citation_sample",
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
                    "plat": f"citation_grounded:{','.join(platforms)}"[:200],
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
