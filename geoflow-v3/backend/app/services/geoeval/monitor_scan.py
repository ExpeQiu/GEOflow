"""Monitor 扫描 — 读取问题、执行多平台探针并写入运行记录。"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists
from app.services.geoeval.monitor_probe import PLATFORMS, aggregate_probe_kpis, run_probes_for_questions

logger = logging.getLogger("geoeval.monitor")


class MonitorScanOrchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_daily_scan(self) -> dict:
        logger.info("monitor_scan_started", scan_type="daily")
        if not await _table_exists(self.db, "geo_monitor_questions"):
            return {"status": "skipped", "probes": 0, "reason": "questions_table_missing"}

        questions = (
            await self.db.execute(
                text(
                    """
                    SELECT id, question_text, priority, status
                    FROM geo_monitor_questions
                    WHERE status = 'active'
                    ORDER BY priority DESC, id ASC
                    LIMIT 50
                    """
                )
            )
        ).all()

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
                    {"platform": ",".join(PLATFORMS), "qc": len(questions)},
                )
            ).first()
            run_id = int(row[0]) if row else None

        probe_count = 0
        if run_id and questions:
            outcomes = await run_probes_for_questions(
                self.db,
                run_id=run_id,
                questions=[(int(q[0]), str(q[1]), int(q[2])) for q in questions],
            )
            probe_count = len(outcomes)

            for qid, _, _ in questions:
                await self.db.execute(
                    text(
                        """
                        UPDATE geo_monitor_questions
                        SET last_scan_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
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

        kpis = await aggregate_probe_kpis(self.db)
        logger.info("monitor_scan_completed probes=%s run_id=%s", probe_count, run_id)
        return {
            "status": "completed",
            "probes": probe_count,
            "run_id": run_id,
            "question_count": len(questions),
            "mention_rate": kpis.get("mention_rate", 0.0),
            "avg_brand_rank": kpis.get("avg_brand_rank"),
        }
