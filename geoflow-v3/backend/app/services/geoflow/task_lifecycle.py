"""任务生命周期 — 移植 TaskLifecycleService。"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskRun


def _celery():
    from app.workers.celery_app import celery_app

    return celery_app


class TaskLifecycleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> Task:
        task = Task(
            name=data["name"],
            title_library_id=data["title_library_id"],
            prompt_id=data["prompt_id"],
            ai_model_id=data["ai_model_id"],
            knowledge_base_id=data.get("knowledge_base_id"),
            content_format=data.get("content_format", "article"),
            publish_scope=data.get("publish_scope", "local_and_distribution"),
            status="active",
        )
        self.db.add(task)
        await self.db.flush()
        return task

    async def start(self, task_id: int) -> Task:
        task = await self.db.get(Task, task_id)
        if task is None:
            raise ValueError("task_not_found")
        task.status = "active"
        task.schedule_enabled = 1
        return task

    async def stop(self, task_id: int) -> Task:
        task = await self.db.get(Task, task_id)
        if task is None:
            raise ValueError("task_not_found")
        task.status = "paused"
        task.schedule_enabled = 0
        return task

    async def enqueue(self, task_id: int) -> TaskRun:
        task = await self.db.get(Task, task_id)
        if task is None:
            raise ValueError("task_not_found")
        run = TaskRun(task_id=task_id, status="queued")
        self.db.add(run)
        await self.db.flush()
        task.last_run_at = datetime.now(UTC)
        _celery().send_task("app.workers.tasks.process_geoflow_task", args=[run.id])
        return run
