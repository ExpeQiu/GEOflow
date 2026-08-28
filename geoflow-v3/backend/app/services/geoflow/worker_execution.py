"""Worker 执行器 — L2 生产素材 → AI 生成 → 文章落库。"""

import json
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
from app.services.geoflow.wiki_types import WIKI_CONTENT_FORMAT, ARTICLE_CONTENT_FORMAT, ascii_slug
from app.ai.workflow_runner import run_workflow_sync

logger = get_logger("geoflow.worker")
settings = get_settings()


def mining_from_theme_meta(meta: dict | None) -> dict:
    data = meta if isinstance(meta, dict) else {}
    mining = data.get("mining")
    return mining if isinstance(mining, dict) else {}


def mining_prompt_block(mining: dict, pack_type: str) -> str:
    """把 A 轨框架 / 信源缺口写进生产提示词。"""
    if not mining:
        return ""
    parts: list[str] = []
    digest = str(mining.get("thinking_digest") or "").strip()
    if digest:
        parts.append(f"思考摘要（正文必须覆盖这些决策路径）：{digest[:800]}")
    fw = mining.get("framework") if isinstance(mining.get("framework"), dict) else {}
    dims = [str(x).strip() for x in (fw.get("compare_dims") or []) if str(x).strip()]
    bars = [str(x).strip() for x in (fw.get("evidence_bars") or []) if str(x).strip()]
    constraints = [str(x).strip() for x in (fw.get("scene_constraints") or []) if str(x).strip()]
    gaps = [str(x).strip() for x in (fw.get("open_gaps") or []) if str(x).strip()]
    if pack_type == "compare" and dims:
        parts.append("对比页必须用下列维度做表，禁止另起无关维度：\n- " + "\n- ".join(d[:80] for d in dims[:6]))
    elif dims:
        parts.append("覆盖这些对比维度：" + "；".join(d[:60] for d in dims[:6]))
    if bars:
        parts.append("证据门槛（写明要核验什么，不能只喊口号）：" + "；".join(b[:80] for b in bars[:6]))
    if constraints:
        parts.append("场景约束：" + "；".join(c[:80] for c in constraints[:4]))
    if gaps:
        parts.append("未决缺口（优先补位）：" + "；".join(g[:80] for g in gaps[:4]))
    hints = mining.get("source_hints") if isinstance(mining.get("source_hints"), list) else []
    ours: list[str] = []
    others: list[str] = []
    for hint in hints:
        if not isinstance(hint, dict):
            continue
        label = str(hint.get("domain") or hint.get("title") or hint.get("url") or "").strip()
        if not label:
            continue
        if str(hint.get("owner") or "") == "ours":
            ours.append(label)
        else:
            others.append(label)
    if ours:
        parts.append("优先引用我方信源：" + "；".join(ours[:6]))
    if others:
        parts.append("当前答案常见外部信源（对照缺口）：" + "；".join(others[:6]))
    return "\n\n".join(parts)


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

            theme_id = None
            pack_type = task.wiki_page_type or "concept"
            mining: dict = {}
            try:
                from sqlalchemy import select as sa_select

                from app.models.theme import GeoTheme
                from app.services.geoeval.theme_service import pack_type_for_title

                theme = (
                    await self.db.execute(sa_select(GeoTheme).where(GeoTheme.task_id == task.id).limit(1))
                ).scalar_one_or_none()
                if theme:
                    theme_id = theme.id
                    pack_type = pack_type_for_title(
                        theme.pack_spec or [],
                        ctx.title,
                        task.created_count,
                        pack_type,
                    )
                    mining = mining_from_theme_meta(theme.meta)
            except Exception:  # noqa: BLE001
                logger.debug("theme_lookup_skipped task_id=%s", task.id, exc_info=True)

            prompt_text = self._compose_prompt(prompt_text, ctx, mining=mining, pack_type=pack_type)

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
                "pack_type": pack_type,
                "mining": mining,
                "framework": mining.get("framework") if mining else {},
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
            slug = ascii_slug(article_title, fallback="article")
            category_id = ctx.category_id or 1
            author_id = ctx.author_id or 1

            from app.services.admin.geo_eval_settings_service import get_geo_eval_gate_config

            gate = await get_geo_eval_gate_config(self.db)

            pack_type_normalized = str(pack_type or "concept").strip().lower()
            content_format = task.content_format or "article"
            # Theme 包产出 → 长文章（/operations/articles），不写 Wiki
            if theme_id:
                content_format = ARTICLE_CONTENT_FORMAT
                pack_type_normalized = "article"
            elif pack_type_normalized != "article":
                content_format = WIKI_CONTENT_FORMAT

            article = Article(
                title=article_title,
                slug=f"{slug}-{run.id}",
                content=article_fields["content"],
                excerpt=article_fields["meta_description"][:500],
                category_id=category_id,
                author_id=author_id,
                task_id=task.id,
                theme_id=theme_id,
                is_ai_generated=1,
                content_format=content_format,
                keywords=article_fields["keywords"],
                original_keyword=article_fields["original_keyword"],
                meta_description=article_fields["meta_description"],
                eval_status="pending_eval" if gate["enabled"] else "skipped",
            )
            if content_format == WIKI_CONTENT_FORMAT:
                wiki_meta = result.get("wiki_meta") if isinstance(result.get("wiki_meta"), dict) else {}
                wiki_meta["type"] = pack_type_normalized
                wiki_meta["wiki_page_type"] = pack_type_normalized
                if theme_id:
                    wiki_meta.setdefault("theme_id", theme_id)
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
                "worker_run_completed run_id=%s article_id=%s theme_id=%s title_id=%s workflow=%s pack_type=%s mining=%s",
                run_id,
                article.id,
                theme_id,
                ctx.title_id,
                workflow_type,
                pack_type,
                bool(mining),
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
    def _compose_prompt(
        base: str,
        ctx: TaskMaterialContext,
        *,
        mining: dict | None = None,
        pack_type: str = "concept",
    ) -> str:
        parts = [base.strip(), f"文章标题：{ctx.title}"]
        if ctx.style_guide:
            parts.append(f"写作风格指南：\n{ctx.style_guide}")
        if ctx.tech_ip:
            parts.append(str(ctx.tech_ip.get("prompt_block") or ""))
        mining_block = mining_prompt_block(mining or {}, pack_type)
        if mining_block:
            parts.append(mining_block)
        return "\n\n".join(p for p in parts if p)
