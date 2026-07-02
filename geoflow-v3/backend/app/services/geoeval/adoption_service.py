"""采纳率指标聚合与告警写入。"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.geoeval import ArticleEvaluation
from app.models.task import TaskRun
from app.services.admin.production_service import _table_exists

logger = logging.getLogger(__name__)


async def aggregate_adoption_metrics(db: AsyncSession) -> dict:
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=24)
    published = int(
        await db.scalar(
            select(func.count()).select_from(Article).where(Article.status == "published", Article.updated_at >= since)
        )
        or 0
    )
    eval_passed = int(
        await db.scalar(
            select(func.count())
            .select_from(ArticleEvaluation)
            .where(ArticleEvaluation.status == "passed", ArticleEvaluation.updated_at >= since)
        )
        or 0
    )
    eval_failed = int(
        await db.scalar(
            select(func.count())
            .select_from(ArticleEvaluation)
            .where(ArticleEvaluation.status == "failed", ArticleEvaluation.updated_at >= since)
        )
        or 0
    )
    task_failed = int(
        await db.scalar(
            select(func.count()).select_from(TaskRun).where(TaskRun.status == "failed", TaskRun.created_at >= since)
        )
        or 0
    )
    metrics = {
        "published_24h": published,
        "eval_passed_24h": eval_passed,
        "eval_failed_24h": eval_failed,
        "task_failed_24h": task_failed,
        "aggregated_at": datetime.now(UTC).isoformat(),
    }
    logger.info("adoption_metrics_aggregated %s", metrics)
    return metrics


async def check_adoption_alerts(db: AsyncSession) -> dict:
    metrics = await aggregate_adoption_metrics(db)
    if not await _table_exists(db, "geo_admin_alerts"):
        logger.warning("geo_admin_alerts_table_missing")
        return {"alerts_created": 0, "metrics": metrics}

    created = 0
    alerts: list[tuple[str, str, dict]] = []

    if metrics["eval_failed_24h"] >= 3:
        alerts.append(
            (
                "eval_failure_spike",
                f"近 24h GEO 评估失败 {metrics['eval_failed_24h']} 次",
                {"eval_failed_24h": metrics["eval_failed_24h"]},
            )
        )
    if metrics["task_failed_24h"] >= 2:
        alerts.append(
            (
                "task_failure_spike",
                f"近 24h 任务运行失败 {metrics['task_failed_24h']} 次",
                {"task_failed_24h": metrics["task_failed_24h"]},
            )
        )
    if metrics["published_24h"] == 0 and metrics["eval_passed_24h"] == 0:
        alerts.append(
            (
                "adoption_stall",
                "近 24h 无发布且无评估通过，采纳链路可能停滞",
                metrics,
            )
        )

    for alert_type, message, payload in alerts:
        await db.execute(
            text(
                "INSERT INTO geo_admin_alerts (alert_type, message, payload_json) VALUES (:t, :m, :p)"
            ),
            {"t": alert_type, "m": message, "p": payload},
        )
        created += 1
        logger.info("adoption_alert_created type=%s", alert_type)

    return {"alerts_created": created, "metrics": metrics}
