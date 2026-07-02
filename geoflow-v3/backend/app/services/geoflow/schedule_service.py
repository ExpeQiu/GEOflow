"""定时任务调度 — 扫描 schedule_enabled 任务并入队。"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.task import Task
from app.services.geoflow.task_lifecycle import TaskLifecycleService

logger = get_logger("geoflow.schedule")


async def run_scheduled_tasks(db: AsyncSession) -> dict:
    now = datetime.now(UTC)
    tasks = (
        await db.execute(
            select(Task).where(
                Task.status == "active",
                Task.schedule_enabled == 1,
                or_(Task.next_run_at.is_(None), Task.next_run_at <= now),
            )
        )
    ).scalars().all()

    enqueued = 0
    lifecycle = TaskLifecycleService(db)
    for task in tasks:
        try:
            await lifecycle.enqueue(task.id)
            interval = max(int(task.publish_interval or 3600), 60)
            task.next_run_at = now + timedelta(seconds=interval)
            enqueued += 1
            logger.info("schedule_task_enqueued task_id=%s next_run_at=%s", task.id, task.next_run_at)
        except Exception:
            logger.exception("schedule_task_failed task_id=%s", task.id)

    await db.flush()
    return {"enqueued": enqueued, "scanned": len(tasks)}
