"""Monitor 扫描 — daily / market，扫描后情感、缺口、洞察、快照。"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists
from app.services.geoeval.monitor_probe import (
    aggregate_monitor_snapshot,
    aggregate_probe_kpis,
    load_platforms,
    load_scan_limit,
    run_probes_for_questions,
)

logger = logging.getLogger("geoeval.monitor")


class MonitorScanOrchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _load_questions(self, scan_type: str) -> list[tuple]:
        limit = await load_scan_limit(self.db)
        has_extended = await _table_exists(self.db, "geo_monitor_scenes")

        if has_extended:
            sql = """
                SELECT id, question_text, priority, competitor_brands
                FROM geo_monitor_questions
                WHERE status = 'active'
                ORDER BY priority DESC, id ASC
                LIMIT :lim
            """
        else:
            sql = """
                SELECT id, question_text, priority, NULL as competitor_brands
                FROM geo_monitor_questions
                WHERE status = 'active'
                ORDER BY priority DESC, id ASC
                LIMIT :lim
            """

        rows = (await self.db.execute(text(sql), {"lim": limit})).all()
        if scan_type == "market":
            return rows
        return rows[:limit]

    async def run_scan(self, scan_type: str = "daily") -> dict:
        logger.info("monitor_scan_started scan_type=%s", scan_type)
        if not await _table_exists(self.db, "geo_monitor_questions"):
            return {"status": "skipped", "probes": 0, "reason": "questions_table_missing"}

        questions = await self._load_questions(scan_type)
        platforms = await load_platforms(self.db)

        run_id = None
        if await _table_exists(self.db, "geo_monitor_runs"):
            row = (
                await self.db.execute(
                    text(
                        """
                        INSERT INTO geo_monitor_runs (status, platform, question_count, probe_count, started_at)
                        VALUES ('running', :platform, :qc, 0, CURRENT_TIMESTAMP)
                        RETURNING id
                        """
                    ),
                    {"platform": ",".join(platforms), "qc": len(questions)},
                )
            ).first()
            run_id = int(row[0]) if row else None

        probe_count = 0
        if run_id and questions:
            parsed_questions = []
            for q in questions:
                qid, qtext, priority = int(q[0]), str(q[1]), int(q[2])
                comp_raw = q[3] if len(q) > 3 else None
                comp_list = None
                if comp_raw:
                    if isinstance(comp_raw, list):
                        comp_list = comp_raw
                    elif isinstance(comp_raw, str):
                        import json

                        try:
                            comp_list = json.loads(comp_raw)
                        except json.JSONDecodeError:
                            comp_list = None
                parsed_questions.append((qid, qtext, priority, comp_list))

            outcomes = await run_probes_for_questions(
                self.db,
                run_id=run_id,
                questions=parsed_questions,
            )
            probe_count = len(outcomes)

            for qid, _, _, _ in parsed_questions:
                await self.db.execute(
                    text(
                        """
                        UPDATE geo_monitor_questions
                        SET last_scan_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                        """
                    ),
                    {"id": qid},
                )

        if run_id and await _table_exists(self.db, "geo_monitor_runs"):
            await self.db.execute(
                text(
                    """
                    UPDATE geo_monitor_runs
                    SET status='completed', probe_count=:pc, completed_at=CURRENT_TIMESTAMP
                    WHERE id=:id
                    """
                ),
                {"pc": probe_count, "id": run_id},
            )

        from app.services.geoeval.sentiment_analyzer import batch_analyze_probe_sentiments
        from app.services.geoeval.scene_gap_analyzer import compute_all_scene_gaps
        from app.services.geoeval.insight_generator import generate_monitor_insights
        from app.services.geoeval.monitor_alerts import check_monitor_alerts

        await batch_analyze_probe_sentiments(self.db, run_id)
        gap_result = await compute_all_scene_gaps(self.db)
        if scan_type == "market":
            from app.services.geoeval.competitive_analyzer import build_competitor_matrix

            matrix = await build_competitor_matrix(self.db)
        else:
            matrix = {}
        await generate_monitor_insights(self.db)
        await aggregate_monitor_snapshot(self.db)

        from app.services.admin.distribution_citation_service import refresh_distribution_citation_cache

        citation_cache = await refresh_distribution_citation_cache(self.db)
        alerts = await check_monitor_alerts(self.db)

        kpis = await aggregate_probe_kpis(self.db)
        logger.info(
            "monitor_scan_completed scan_type=%s probes=%s run_id=%s visibility=%s",
            scan_type,
            probe_count,
            run_id,
            kpis.get("visibility_pct"),
        )
        return {
            "status": "completed",
            "scan_type": scan_type,
            "probes": probe_count,
            "run_id": run_id,
            "question_count": len(questions),
            "mention_rate": kpis.get("mention_rate", 0.0),
            "visibility_pct": kpis.get("visibility_pct", 0.0),
            "avg_brand_rank": kpis.get("avg_brand_rank"),
            "weighted_rank_score": kpis.get("weighted_rank_score"),
            "sentiment_score": kpis.get("sentiment_score"),
            "high_gap_scenes": gap_result.get("high_gap_count", 0),
            "competitor_matrix": matrix if scan_type == "market" else None,
            "alerts_created": alerts.get("alerts_created", 0),
            "citation_cache": {
                "indexed": citation_cache.get("indexed_count", 0),
                "not_indexed": citation_cache.get("not_indexed_count", 0),
                "alerts_created": citation_cache.get("alerts_created", 0),
            },
        }

    async def run_daily_scan(self) -> dict:
        return await self.run_scan("daily")
