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
            image_library_id=data.get("image_library_id"),
            image_count=int(data.get("image_count") or 0),
            author_id=data.get("author_id"),
            insight_template_id=data.get("insight_template_id"),
            fixed_category_id=data.get("fixed_category_id"),
            tech_ip_asset_id=data.get("tech_ip_asset_id"),
            content_format=data.get("content_format", "article"),
            wiki_page_type=data.get("wiki_page_type"),
            publish_scope=data.get("publish_scope", "local_and_distribution"),
            status=data.get("status", "active"),
            article_limit=int(data.get("article_limit") or 10),
            draft_limit=int(data.get("draft_limit") or 10),
            publish_interval=int(data.get("publish_interval") or 3600),
            need_review=int(data.get("need_review") or 0),
            is_loop=int(data.get("is_loop", 1)),
            category_mode=data.get("category_mode", "smart"),
            model_selection_mode=data.get("model_selection_mode", "fixed"),
            content_pipeline_mode=data.get("content_pipeline_mode", "legacy"),
            auto_keywords=int(data.get("auto_keywords", 1)),
            auto_description=int(data.get("auto_description", 1)),
            schedule_enabled=1 if data.get("status", "active") == "active" else 0,
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
        task.last_run_at = datetime.now(UTC).replace(tzinfo=None)
        _celery().send_task("app.workers.tasks.process_geoflow_task", args=[run.id])
        return run

    async def update(self, task_id: int, data: dict) -> Task:
        task = await self.db.get(Task, task_id)
        if task is None:
            raise ValueError("task_not_found")
        for key, value in data.items():
            if hasattr(task, key):
                setattr(task, key, value)
        if data.get("status") == "active":
            task.schedule_enabled = 1
        elif data.get("status") == "paused":
            task.schedule_enabled = 0
        await self.db.flush()
        return task

    async def delete(self, task_id: int) -> None:
        task = await self.db.get(Task, task_id)
        if task is None:
            raise ValueError("task_not_found")
        await self.db.delete(task)
        await self.db.flush()
