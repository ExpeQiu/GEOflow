"""Celery 任务 — 对应 Laravel 7 Jobs + 定时命令。"""

import asyncio

from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger("celery.tasks")


def _run_async(coro):
    return asyncio.run(coro)


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
            from app.services.geoeval.article_evaluation import ArticleEvaluationService

            svc = ArticleEvaluationService(db)
            ev = await svc.evaluate(article_id, task_run_id)
            await db.commit()
            if ev.status == "passed":
                celery_app.send_task("app.workers.tasks.try_publish_after_eval", args=[article_id])
        return {"article_id": article_id, "status": "evaluated"}

    return _run_async(_inner())


@celery_app.task(name="app.workers.tasks.try_publish_after_eval")
def try_publish_after_eval(article_id: int) -> dict:
    async def _inner():
        from sqlalchemy import select

        from app.models.article import Article
        from app.services.geoflow.article_publish import ArticlePublishService

        async with async_session_factory() as db:
            article = await db.get(Article, article_id)
            if article and article.eval_status == "passed" and article.review_status in (
                "approved",
                "auto_approved",
                "pending",
            ):
                if article.review_status == "pending":
                    article.review_status = "auto_approved"
                svc = ArticlePublishService(db)
                await svc.publish(article_id)
            await db.commit()
        return {"article_id": article_id}

    return _run_async(_inner())


@celery_app.task(name="app.workers.tasks.process_article_distribution")
def process_article_distribution(article_id: int) -> dict:
    async def _inner():
        async with async_session_factory() as db:
            from app.services.geoflow.distribution_orchestrator import DistributionOrchestrator

            svc = DistributionOrchestrator(db)
            await svc.distribute_article(article_id)
            await db.commit()
        return {"article_id": article_id}

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
            return await svc.run_daily_scan()

    logger.info("monitor_scan", scan_type=scan_type)
    return _run_async(_inner())


@celery_app.task(name="app.workers.tasks.refresh_web_source")
def refresh_web_source(source_id: int) -> dict:
    logger.info("refresh_web_source", source_id=source_id)
    return {"source_id": source_id, "status": "skipped"}


@celery_app.task(name="app.workers.tasks.schedule_tasks")
def schedule_tasks() -> dict:
    logger.info("schedule_tasks_tick")
    return {"status": "ok"}


@celery_app.task(name="app.workers.tasks.aggregate_adoption_metrics")
def aggregate_adoption_metrics() -> dict:
    logger.info("aggregate_adoption_metrics")
    return {"status": "ok"}


@celery_app.task(name="app.workers.tasks.check_adoption_alerts")
def check_adoption_alerts() -> dict:
    logger.info("check_adoption_alerts")
    return {"status": "ok"}
