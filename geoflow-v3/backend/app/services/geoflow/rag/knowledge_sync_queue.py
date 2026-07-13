"""知识库切片同步入队 — 创建/更新/上传后自动触发。"""

import logging

logger = logging.getLogger(__name__)


def queue_knowledge_chunk_sync(knowledge_base_id: int) -> bool:
    """将知识库切片同步任务推入 Celery 队列。"""
    try:
        from app.workers.celery_app import celery_app

        celery_app.send_task("app.workers.tasks.sync_knowledge_chunks", args=[knowledge_base_id])
        logger.info("knowledge_chunk_sync_queued kb_id=%s", knowledge_base_id)
        return True
    except Exception:
        logger.exception("knowledge_chunk_sync_queue_failed kb_id=%s", knowledge_base_id)
        return False
