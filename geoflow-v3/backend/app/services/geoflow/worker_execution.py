"""Worker 执行器 — L2 生产素材 → AI 生成 → 文章落库。"""

import json
import re
import time
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.article import Article
from app.models.material import Prompt
from app.models.task import Task, TaskRun
from app.services.geoflow.rag.retrieval import KnowledgeRetrievalService
from app.services.geoflow.content_pipeline_context import ContentPipelineContextService
from app.services.geoflow.task_material_resolver import (
    TaskMaterialContext,
    bump_ai_model_usage,
    finalize_article_fields,
    normalize_evidence,
    resolve_task_materials,
    resolve_workflow_type,
)
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

        ctx: TaskMaterialContext | None = None
        workflow_type = "content"

        try:
            ctx = await resolve_task_materials(self.db, task, run_id)

            prompt_row = await self.db.get(Prompt, task.prompt_id)
            prompt_text = prompt_row.content if prompt_row else "请撰写一篇高质量 Markdown 文章。"
            prompt_text = self._compose_prompt(prompt_text, ctx)

            rag_query = f"{ctx.title}\n{prompt_text[:400]}"
            evidence: list[dict] = []
            if task.knowledge_base_id:
                evidence = normalize_evidence(await self.rag.retrieve(task.knowledge_base_id, rag_query, limit=8))

            workflow_type = resolve_workflow_type(task)
            payload: dict = {
                "prompt": prompt_text,
                "title": ctx.title,
                "user_request": ctx.title,
                "style_guide": ctx.style_guide,
                "evidence": evidence,
                "model": ctx.model,
                "ai_model_id": ctx.ai_model_id,
                "mock": settings.ai_mock_mode,
                "tech_ip": ctx.tech_ip,
            }

            if workflow_type == "content_pipeline":
                pipeline_data = await self.pipeline_ctx.build(task, rag_query)
                if ctx.style_guide:
                    pipeline_data["style_guide"] = ctx.style_guide
                payload.update(pipeline_data)
                if isinstance(payload.get("style_guide"), dict) and ctx.style_guide:
                    payload["style_guide"] = ctx.style_guide

            result = run_workflow_sync(workflow_type, payload)
            raw_content = result.get("content") or result.get("mdx") or f"# {ctx.title}\n\n（内容生成失败，请检查 AI 配置）"
            article_fields = await finalize_article_fields(self.db, task, ctx, raw_content)

            article_title = str(result.get("title") or ctx.title)
            slug = self._slugify(article_title)
            category_id = ctx.category_id or 1
            author_id = ctx.author_id or 1

            from app.services.admin.geo_eval_settings_service import get_geo_eval_gate_config

            gate = await get_geo_eval_gate_config(self.db)
            article = Article(
                title=article_title,
                slug=f"{slug}-{run.id}",
                content=article_fields["content"],
                excerpt=article_fields["meta_description"][:500],
                category_id=category_id,
                author_id=author_id,
                task_id=task.id,
                is_ai_generated=1,
                content_format=task.content_format or "article",
                keywords=article_fields["keywords"],
                original_keyword=article_fields["original_keyword"],
                meta_description=article_fields["meta_description"],
                eval_status="pending_eval" if gate["enabled"] else "skipped",
            )
            if task.is_wiki_mdx():
                wiki_meta = result.get("wiki_meta") if isinstance(result.get("wiki_meta"), dict) else {}
                wiki_meta.setdefault("type", task.wiki_page_type or "concept")
                if ctx.tech_ip:
                    wiki_meta.setdefault("ip_id", ctx.tech_ip.get("ip_id"))
                    wiki_meta.setdefault("tech_name", ctx.tech_ip.get("name"))
                article.wiki_meta = wiki_meta

            self.db.add(article)
            await self.db.flush()

            await bump_ai_model_usage(self.db, ctx.ai_model_id)

            run.article_id = article.id
            run.status = "completed"
            task.created_count += 1
            task.last_success_at = datetime.now(UTC).replace(tzinfo=None)

            from app.workers.celery_app import celery_app

            celery_app.send_task("app.workers.tasks.evaluate_article", args=[article.id, run.id])

            logger.info(
                "worker_run_completed run_id=%s article_id=%s title_id=%s workflow=%s",
                run_id,
                article.id,
                ctx.title_id,
                workflow_type,
            )
        except Exception as exc:  # noqa: BLE001
            run.status = "failed"
            run.error_message = str(exc)[:500]
            task.last_error_at = datetime.now(UTC).replace(tzinfo=None)
            task.last_error_message = run.error_message
            logger.exception("worker_run_failed run_id=%s error=%s", run_id, str(exc))
        finally:
            run.duration_ms = int((time.monotonic() - started) * 1000)
            run.finished_at = datetime.now(UTC).replace(tzinfo=None)
            run.meta = json.dumps(
                {
                    "workflow": workflow_type,
                    "title_id": ctx.title_id if ctx else None,
                    "ai_model_id": ctx.ai_model_id if ctx else task.ai_model_id,
                    "pipeline_mode": task.content_pipeline_mode,
                }
            )

    @staticmethod
    def _compose_prompt(base: str, ctx: TaskMaterialContext) -> str:
        parts = [base.strip(), f"文章标题：{ctx.title}"]
        if ctx.style_guide:
            parts.append(f"写作风格指南：\n{ctx.style_guide}")
        if ctx.tech_ip:
            parts.append(str(ctx.tech_ip.get("prompt_block") or ""))
        return "\n\n".join(p for p in parts if p)

    @staticmethod
    def _slugify(text: str) -> str:
        slug = re.sub(r"[^\w\s-]", "", text.lower())
        return re.sub(r"[\s_-]+", "-", slug).strip("-")[:80] or "article"
