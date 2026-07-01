"""Monitor 扫描 — 移植 MonitorScanOrchestrator 简化版。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger("geoeval.monitor")


class MonitorScanOrchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_daily_scan(self) -> dict:
        logger.info("monitor_scan_started", scan_type="daily")
        # 占位：读取 geo_monitor_questions 并执行探针
        return {"status": "completed", "probes": 0}
