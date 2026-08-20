"""Celery 应用配置。"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "geoflow",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
)

celery_app.conf.beat_schedule = {
    "schedule-tasks": {"task": "app.workers.tasks.schedule_tasks", "schedule": 60.0},
    "aggregate-adoption": {
        "task": "app.workers.tasks.aggregate_adoption_metrics",
        "schedule": crontab(hour=2, minute=0),
    },
    "monitor-scan-daily": {
        "task": "app.workers.tasks.run_monitor_scan",
        "schedule": crontab(hour=4, minute=0),
        "kwargs": {"scan_type": "daily"},
    },
    "monitor-scan-market": {
        "task": "app.workers.tasks.run_monitor_scan",
        "schedule": crontab(hour=3, minute=0, day_of_week=1),
        "kwargs": {"scan_type": "market"},
    },
    "aggregate-monitor-snapshots": {
        "task": "app.workers.tasks.aggregate_monitor_snapshots",
        "schedule": crontab(hour=4, minute=30),
    },
    "check-monitor-alerts": {
        "task": "app.workers.tasks.check_monitor_alerts",
        "schedule": crontab(hour=8, minute=45),
    },
    "check-adoption-alerts": {
        "task": "app.workers.tasks.check_adoption_alerts",
        "schedule": crontab(hour=8, minute=30),
    },
    "process-due-remediations": {
        "task": "app.workers.tasks.process_due_remediations",
        "schedule": 3600.0,
    },
    "framework-scan-weekly": {
        "task": "app.workers.tasks.run_framework_probe_scan",
        "schedule": crontab(hour=5, minute=0, day_of_week=1),
        "kwargs": {"limit": 12},
    },
    "citation-scan-weekly": {
        "task": "app.workers.tasks.run_citation_probe_scan",
        "schedule": crontab(hour=5, minute=30, day_of_week=1),
        "kwargs": {"limit": 12},
    },
}
