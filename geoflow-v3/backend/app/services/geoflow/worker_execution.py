"""Worker 执行器 — 移植 WorkerExecutionService 核心链路。"""

import json
import re
import time
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.article import Article
from app.models.material import Category, Prompt
from app.models.task import Task, TaskRun
from app.services.geoflow.rag.retrieval import KnowledgeRetrievalService
from app.services.geoflow.content_pipeline_context import ContentPipelineContextService
from app.ai.workflow_runner import run_workflow_sync

logger = get_logger("geoflow.worker")
settings = get_settings()


class WorkerExecutionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rag = KnowledgeRetrievalService(db)
        self.pipeline_ctx = ContentPipelineContextService(db, self.rag)

    async def execute_run(self, run_id: int) -> None:
        run = await self.db.get(TaskRun, run_id)
        if run is None:
            return
        task = await self.db.get(Task, run.task_id)
        if task is None:
            run.status = "failed"
            run.error_message = "task_not_found"
            return

        started = time.monotonic()
        run.status = "running"
        await self.db.flush()

        try:
            prompt = await self.db.get(Prompt, task.prompt_id)
            prompt_text = prompt.content if prompt else "请撰写一篇高质量 Markdown 文章。"

            evidence = []
            if task.knowledge_base_id:
                evidence = await self.rag.retrieve(task.knowledge_base_id, prompt_text[:500], limit=8)

            workflow_type = "content_pipeline" if task.content_pipeline_mode else "content"
            payload: dict = {
                "prompt": prompt_text,
                "evidence": evidence,
                "mock": settings.ai_mock_mode,
            }

            if workflow_type == "content_pipeline":
                payload.update(await self.pipeline_ctx.build(task, prompt_text))

            result = run_workflow_sync(workflow_type, payload)
            content = result.get("content") or result.get("mdx") or "# Mock Article\n\nGenerated in v3."

            category_id = task.fixed_category_id
            if category_id is None:
                cat = (await self.db.execute(select(Category).limit(1))).scalar_one_or_none()
                category_id = cat.id if cat else 1

            slug = self._slugify(result.get("title") or task.name)
            article = Article(
                title=result.get("title") or task.name,
                slug=f"{slug}-{run.id}",
                content=content,
                category_id=category_id,
                author_id=task.author_id or 1,
                task_id=task.id,
                is_ai_generated=1,
                content_format=task.content_format or "article",
                eval_status="pending_eval" if settings.geo_eval_enabled else "skipped",
            )
            if task.is_wiki_mdx():
                article.wiki_meta = result.get("wiki_meta") or {"type": task.wiki_page_type or "concept"}

            self.db.add(article)
            await self.db.flush()

            run.article_id = article.id
            run.status = "completed"
            task.created_count += 1
            task.last_success_at = datetime.now(UTC)

            from app.workers.celery_app import celery_app

            celery_app.send_task("app.workers.tasks.evaluate_article", args=[article.id, run.id])

            logger.info("worker_run_completed", run_id=run_id, article_id=article.id)
        except Exception as exc:  # noqa: BLE001
            run.status = "failed"
            run.error_message = str(exc)[:500]
            task.last_error_at = datetime.now(UTC)
            task.last_error_message = run.error_message
            logger.exception("worker_run_failed", run_id=run_id, error=str(exc))
        finally:
            run.duration_ms = int((time.monotonic() - started) * 1000)
            run.finished_at = datetime.now(UTC)
            run.meta = json.dumps({"workflow": task.content_pipeline_mode or "content"})

    @staticmethod
    def _slugify(text: str) -> str:
        slug = re.sub(r"[^\w\s-]", "", text.lower())
        return re.sub(r"[\s_-]+", "-", slug).strip("-")[:80] or "article"
