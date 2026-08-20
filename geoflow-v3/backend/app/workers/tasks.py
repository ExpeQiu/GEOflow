"""Celery 任务 — 对应 Laravel 7 Jobs + 定时命令。"""

import asyncio

from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger("celery.tasks")


def _run_async(coro):
    from app.core.database import engine

    async def _runner():
        try:
            return await coro
        finally:
            await engine.dispose()

    return asyncio.run(_runner())


@celery_app.task(name="app.workers.tasks.process_geoflow_task")
def process_geoflow_task(run_id: int) -> dict:
    async def _inner():
        async with async_session_factory() as db:
            from app.services.geoflow.worker_execution import WorkerExecutionService

            svc = WorkerExecutionService(db)
            await svc.execute_run(run_id)
            await db.commit()
        return {"run_id": run_id, "status": "done"}

    logger.info("process_geoflow_task_started", run_id=run_id)
    return _run_async(_inner())


@celery_app.task(name="app.workers.tasks.evaluate_article")
def evaluate_article(article_id: int, task_run_id: int | None = None) -> dict:
    async def _inner():
        async with async_session_factory() as db:
            from app.models.article import Article
            from app.services.admin.geo_eval_settings_service import get_geo_eval_gate_config
            from app.services.geoeval.article_evaluation import ArticleEvaluationService

            svc = ArticleEvaluationService(db)
            ev = await svc.evaluate(article_id, task_run_id)

            gate = await get_geo_eval_gate_config(db)
            hard = bool(gate["hard_gate"])
            can_auto = ev.status == "passed" or (ev.status == "advisory" and not hard)

            article = await db.get(Article, article_id)
            theme_id = article.theme_id if article else None
            pack_ok = False
            if theme_id:
                from app.services.geoeval.theme_service import refresh_theme_gate_summary

                summary = await refresh_theme_gate_summary(db, int(theme_id))
                pack_ok = bool((summary.get("gate_summary") or {}).get("pack_gate_ok"))
                logger.info(
                    "theme_gate_after_eval theme_id=%s article_id=%s pack_gate_ok=%s eval_status=%s",
                    theme_id,
                    article_id,
                    pack_ok,
                    ev.status,
                )

            await db.commit()

            if can_auto:
                celery_app.send_task("app.workers.tasks.try_publish_after_eval", args=[article_id])

            # 硬门禁整包通过后，补发此前暂缓分发的同 Theme 文章
            if theme_id and pack_ok:
                async with async_session_factory() as db2:
                    from sqlalchemy import select

                    from app.models.theme import GeoTheme

                    theme = await db2.get(GeoTheme, theme_id)
                    if theme and (theme.gate_mode or "soft") == "hard":
                        arts = (
                            await db2.execute(
                                select(Article.id).where(
                                    Article.theme_id == theme_id,
                                    Article.status == "published",
                                    Article.deleted_at.is_(None),
                                )
                            )
                        ).scalars().all()
                        for aid in arts:
                            celery_app.send_task("app.workers.tasks.process_article_distribution", args=[int(aid)])
                        logger.info(
                            "theme_pack_gate_passed_flush_distribution theme_id=%s articles=%s",
                            theme_id,
                            len(arts),
                        )

            logger.info(
                "evaluate_article_done article_id=%s eval_status=%s hard_gate=%s auto_publish=%s theme_id=%s",
                article_id,
                ev.status,
                hard,
                can_auto,
                theme_id,
            )
        return {"article_id": article_id, "status": "evaluated", "eval_status": ev.status}

    return _run_async(_inner())


@celery_app.task(name="app.workers.tasks.try_publish_after_eval")
def try_publish_after_eval(article_id: int) -> dict:
    async def _inner():
        from sqlalchemy import select

        from app.models.article import Article
        from app.services.geoflow.article_publish import ArticlePublishService

        async with async_session_factory() as db:
            article = await db.get(Article, article_id)
            if article and article.eval_status in ("passed", "advisory") and article.review_status in (
                "approved",
                "auto_approved",
                "pending",
            ):
                if article.review_status == "pending":
                    article.review_status = "auto_approved"
                svc = ArticlePublishService(db)
                await svc.publish(article_id)
                logger.info(
                    "try_publish_after_eval article_id=%s eval_status=%s",
                    article_id,
                    article.eval_status,
                )
            await db.commit()
        return {"article_id": article_id}

    return _run_async(_inner())


@celery_app.task(name="app.workers.tasks.process_article_distribution")
def process_article_distribution(article_id: int, channel_ids: list[int] | None = None) -> dict:
    async def _inner():
        async with async_session_factory() as db:
            from app.services.geoflow.distribution_orchestrator import DistributionOrchestrator

            svc = DistributionOrchestrator(db)
            await svc.distribute_article(article_id, channel_ids=channel_ids)
            await db.commit()
        return {"article_id": article_id, "channel_ids": channel_ids}

    return _run_async(_inner())


@celery_app.task(name="app.workers.tasks.sync_knowledge_chunks")
def sync_knowledge_chunks(knowledge_base_id: int) -> dict:
    async def _inner():
        async with async_session_factory() as db:
            from app.services.geoflow.rag.chunk_sync import KnowledgeChunkSyncService

            svc = KnowledgeChunkSyncService(db)
            count = await svc.sync_chunks(knowledge_base_id)
            await db.commit()
        return {"knowledge_base_id": knowledge_base_id, "chunks": count}

    return _run_async(_inner())


@celery_app.task(name="app.workers.tasks.run_monitor_scan")
def run_monitor_scan(scan_type: str = "daily") -> dict:
    async def _inner():
        async with async_session_factory() as db:
            from app.services.geoeval.monitor_scan import MonitorScanOrchestrator

            svc = MonitorScanOrchestrator(db)
            result = await svc.run_scan(scan_type)
            await db.commit()
            return result

    logger.info("monitor_scan", scan_type=scan_type)
    return _run_async(_inner())


@celery_app.task(name="app.workers.tasks.run_cend_probe_scan")
def run_cend_probe_scan(
    platforms: list[str] | None = None,
    limit: int = 5,
    min_priority: int = 80,
) -> dict:
    """C 端金标扫描（辅轨），不进入 open_api 北极星口径。"""

    async def _inner():
        async with async_session_factory() as db:
            from app.services.geoeval.cend_scan import CendScanOrchestrator

            result = await CendScanOrchestrator(db).run_scan(
                platforms=platforms,
                limit=limit,
                min_priority=min_priority,
            )
            await db.commit()
            return result

    logger.info("cend_probe_scan_queued", platforms=platforms, limit=limit)
    return _run_async(_inner())


@celery_app.task(name="app.workers.tasks.run_framework_probe_scan")
def run_framework_probe_scan(
    platforms: list[str] | None = None,
    limit: int = 12,
    min_priority: int = 80,
    scene_id: int | None = None,
) -> dict:
    """框架轨扫描（A+C），不进入 open_api 北极星口径。"""

    async def _inner():
        async with async_session_factory() as db:
            from app.services.geoeval.framework_scan import FrameworkScanOrchestrator

            result = await FrameworkScanOrchestrator(db).run_scan(
                platforms=platforms,
                limit=limit,
                min_priority=min_priority,
                scene_id=scene_id,
            )
            await db.commit()
            return result

    logger.info("framework_probe_scan_queued", platforms=platforms, limit=limit)
    return _run_async(_inner())


@celery_app.task(name="app.workers.tasks.run_citation_probe_scan")
def run_citation_probe_scan(
    platforms: list[str] | None = None,
    limit: int = 12,
    min_priority: int = 80,
    scene_id: int | None = None,
) -> dict:
    """引用轨扫描（B+C），不进入 open_api 北极星口径。"""

    async def _inner():
        async with async_session_factory() as db:
            from app.services.geoeval.citation_scan import CitationScanOrchestrator

            result = await CitationScanOrchestrator(db).run_scan(
                platforms=platforms,
                limit=limit,
                min_priority=min_priority,
                scene_id=scene_id,
            )
            await db.commit()
            return result

    logger.info("citation_probe_scan_queued", platforms=platforms, limit=limit)
    return _run_async(_inner())


@celery_app.task(name="app.workers.tasks.process_due_remediations")
def process_due_remediations() -> dict:
    async def _inner():
        async with async_session_factory() as db:
            from app.services.geoeval.remediation_service import process_due_remediations as run_due

            result = await run_due(db)
            await db.commit()
            return result

    logger.info("process_due_remediations")
    return _run_async(_inner())


@celery_app.task(name="app.workers.tasks.aggregate_monitor_snapshots")
def aggregate_monitor_snapshots() -> dict:
    async def _inner():
        async with async_session_factory() as db:
            from app.services.geoeval.monitor_probe import aggregate_monitor_snapshot

            result = await aggregate_monitor_snapshot(db)
            await db.commit()
            return result

    logger.info("aggregate_monitor_snapshots")
    return _run_async(_inner())


@celery_app.task(name="app.workers.tasks.check_monitor_alerts")
def check_monitor_alerts_task() -> dict:
    async def _inner():
        async with async_session_factory() as db:
            from app.services.geoeval.monitor_alerts import check_monitor_alerts

            result = await check_monitor_alerts(db)
            await db.commit()
            return result

    logger.info("check_monitor_alerts")
    return _run_async(_inner())


@celery_app.task(name="app.workers.tasks.refresh_web_source")
def refresh_web_source(source_id: int) -> dict:
    return fetch_web_source(source_id)


@celery_app.task(name="app.workers.tasks.fetch_web_source")
def fetch_web_source(source_id: int) -> dict:
    async def _inner():
        from sqlalchemy import text

        async with async_session_factory() as db:
            row = (
                await db.execute(
                    text("SELECT id, url FROM geo_web_sources WHERE id = :id"),
                    {"id": source_id},
                )
            ).first()
            if not row:
                return {"source_id": source_id, "status": "not_found"}
            import httpx

            try:
                async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                    resp = await client.get(row[1])
                status = "ok" if resp.status_code < 400 else "error"
                await db.execute(
                    text(
                        "UPDATE geo_web_sources SET fetch_status=:s, last_fetched_at=CURRENT_TIMESTAMP WHERE id=:id"
                    ),
                    {"s": status, "id": source_id},
                )
                await db.commit()
                logger.info("fetch_web_source_done", source_id=source_id, status=status)
                return {"source_id": source_id, "status": status, "http_status": resp.status_code}
            except Exception as exc:
                await db.execute(
                    text(
                        "UPDATE geo_web_sources SET fetch_status='error', last_fetched_at=CURRENT_TIMESTAMP WHERE id=:id"
                    ),
                    {"id": source_id},
                )
                await db.commit()
                logger.warning("fetch_web_source_failed", source_id=source_id, error=str(exc))
                return {"source_id": source_id, "status": "error", "message": str(exc)[:200]}

    return _run_async(_inner())


@celery_app.task(name="app.workers.tasks.remine_insight_template")
def remine_insight_template(template_id: int) -> dict:
    async def _inner():
        from app.models.geoeval import InsightTemplate

        async with async_session_factory() as db:
            row = await db.get(InsightTemplate, template_id)
            if row is None:
                return {"template_id": template_id, "status": "not_found"}

            source_url = (row.source_url or "").strip()
            style_guide: dict = {}
            features: dict = {}
            score = float(row.eeat_score or 0.5)

            if source_url.startswith(("http://", "https://")):
                try:
                    from app.services.geoflow.url_fetch import fetch_page_json

                    page = fetch_page_json(source_url)
                    text = page.get("text", "")
                    title = page.get("title", row.name)
                    style_guide = {"tone": "professional", "source_title": title, "excerpt": text[:500]}
                    features = {"word_count": len(text.split()), "source_url": source_url}
                    score = min(0.95, 0.45 + min(len(text) / 5000, 0.5))
                except Exception as exc:
                    logger.warning("remine_fetch_failed template_id=%s err=%s", template_id, exc)
            else:
                try:
                    from app.ai.workflow_runner import run_workflow_sync

                    wf = run_workflow_sync(
                        "url_import",
                        {"page_json": {"title": row.name, "text": row.name}, "url": source_url or "inline://remine"},
                    )
                    if isinstance(wf, dict):
                        style_guide = {"summary": wf.get("summary", "")}
                        features = {"keywords": wf.get("keywords", [])}
                        score = min(0.9, 0.5 + len(str(wf.get("knowledge_markdown", ""))) / 8000)
                except Exception:
                    logger.exception("remine_workflow_fallback template_id=%s", template_id)

            row.style_guide = style_guide
            row.features = features
            row.eeat_score = round(score, 2)
            await db.commit()
            logger.info("remine_insight_template_done", template_id=template_id, eeat_score=row.eeat_score)
            return {"template_id": template_id, "status": "done", "eeat_score": float(row.eeat_score)}

    return _run_async(_inner())


@celery_app.task(name="app.workers.tasks.import_url_content")
def import_url_content(job_id: int, url: str, target: str) -> dict:
    async def _inner():
        import json

        from sqlalchemy import text

        from app.services.admin.production_service import _table_exists
        from app.services.geoflow.url_fetch import fetch_page_json

        async with async_session_factory() as db:
            request_id = f"url-import-{job_id}"
            if await _table_exists(db, "url_import_jobs"):
                await db.execute(
                    text("UPDATE url_import_jobs SET status='running', updated_at=CURRENT_TIMESTAMP WHERE id=:id"),
                    {"id": job_id},
                )
                await db.commit()

            try:
                page_json = fetch_page_json(url)
                if page_json.get("status_code", 500) >= 400:
                    raise RuntimeError(f"http_{page_json.get('status_code')}")

                from app.ai.workflow_runner import run_workflow_sync

                wf_result = run_workflow_sync("url_import", {"page_json": page_json, "url": url, "target": target})
                if not isinstance(wf_result, dict):
                    wf_result = {"summary": str(wf_result)[:500]}
                summary = str(wf_result.get("summary") or wf_result.get("library_name") or page_json.get("title") or url)[:500]

                if await _table_exists(db, "url_import_jobs"):
                    await db.execute(
                        text(
                            """
                            UPDATE url_import_jobs
                            SET status='completed', result_summary=:s, result_json=CAST(:j AS JSON), error_message='', updated_at=CURRENT_TIMESTAMP
                            WHERE id=:id
                            """
                        ),
                        {"s": summary, "j": json.dumps(wf_result, ensure_ascii=False), "id": job_id},
                    )
                if await _table_exists(db, "content_agent_requests"):
                    await db.execute(
                        text(
                            """
                            UPDATE content_agent_requests
                            SET status='completed', result_json=CAST(:j AS JSON), completed_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP
                            WHERE request_id=:rid
                            """
                        ),
                        {"j": json.dumps(wf_result, ensure_ascii=False), "rid": request_id},
                    )
                await db.commit()
                logger.info("import_url_content_done", job_id=job_id, url=url, target=target)
                return {"job_id": job_id, "status": "completed", "summary": summary, "request_id": request_id}
            except Exception as exc:
                err = str(exc)[:500]
                if await _table_exists(db, "url_import_jobs"):
                    await db.execute(
                        text(
                            "UPDATE url_import_jobs SET status='failed', error_message=:e, updated_at=CURRENT_TIMESTAMP WHERE id=:id"
                        ),
                        {"e": err, "id": job_id},
                    )
                await db.commit()
                logger.warning("import_url_content_failed job_id=%s err=%s", job_id, err)
                return {"job_id": job_id, "status": "failed", "error": err}

    return _run_async(_inner())


@celery_app.task(name="app.workers.tasks.schedule_tasks")
def schedule_tasks() -> dict:
    async def _inner():
        async with async_session_factory() as db:
            from app.services.geoflow.schedule_service import run_scheduled_tasks

            result = await run_scheduled_tasks(db)
            await db.commit()
            return result

    logger.info("schedule_tasks_tick")
    return _run_async(_inner())


@celery_app.task(name="app.workers.tasks.aggregate_adoption_metrics")
def aggregate_adoption_metrics() -> dict:
    async def _inner():
        async with async_session_factory() as db:
            from app.services.geoeval.adoption_service import aggregate_adoption_metrics as agg

            result = await agg(db)
            await db.commit()
            return result

    logger.info("aggregate_adoption_metrics")
    return _run_async(_inner())


@celery_app.task(name="app.workers.tasks.check_adoption_alerts")
def check_adoption_alerts() -> dict:
    async def _inner():
        async with async_session_factory() as db:
            from app.services.geoeval.adoption_service import check_adoption_alerts as check

            result = await check(db)
            await db.commit()
            return result

    logger.info("check_adoption_alerts")
    return _run_async(_inner())
