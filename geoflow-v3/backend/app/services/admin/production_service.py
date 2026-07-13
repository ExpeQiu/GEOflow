"""L2 生产 Hub — Admin BFF 聚合。"""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeBase, KnowledgeChunk
from app.models.material import AiModel, Author, Prompt
from app.models.task import Task, TaskRun

logger = logging.getLogger(__name__)

WORKFLOW_LABELS = {
    "content": "正文生成",
    "content_pipeline": "编辑部 Pipeline",
    "url_import": "URL 导入",
    "semantic_chunk": "语义切片",
}


def _utc_naive_hours_ago(hours: int = 24) -> datetime:
    """PostgreSQL TIMESTAMP WITHOUT TIME ZONE 需使用 naive UTC。"""
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).replace(tzinfo=None)


def _knowledge_health(stats: dict) -> str:
    if stats.get("knowledge_bases", 0) <= 0:
        return "empty"
    if stats.get("active_embedding_models", 0) <= 0:
        return "no_embed"
    if stats.get("unvectorized_chunks", 0) > 0:
        return "pending"
    return "ready"


async def build_production_overview(db: AsyncSession) -> dict:
    stats = await _material_stats(db)
    ai_stats = await _ai_stats(db)
    return {
        "stats": stats,
        "ai_stats": ai_stats,
        "knowledge_health": _knowledge_health(stats),
    }


async def build_materials_panel(db: AsyncSession) -> dict:
    return {"stats": await _material_stats(db)}


async def build_knowledge_panel(db: AsyncSession) -> dict:
    stats = await _material_stats(db)
    orch = await _orchestration_stats(db)
    rows = (await db.execute(select(KnowledgeBase).order_by(KnowledgeBase.id.desc()).limit(100))).scalars().all()
    kb_ids = [k.id for k in rows]
    chunk_counts: dict[int, int] = {}
    vector_counts: dict[int, int] = {}
    if kb_ids:
        for kb_id in kb_ids:
            chunk_counts[kb_id] = int(
                await db.scalar(
                    select(func.count()).select_from(KnowledgeChunk).where(KnowledgeChunk.knowledge_base_id == kb_id)
                )
                or 0
            )
            vector_counts[kb_id] = int(
                await db.scalar(
                    select(func.count())
                    .select_from(KnowledgeChunk)
                    .where(
                        KnowledgeChunk.knowledge_base_id == kb_id,
                        KnowledgeChunk.embedding_vector.is_not(None),
                    )
                )
                or 0
            )

    return {
        "stats": stats,
        "orchestration": orch,
        "items": [
            {
                "id": kb.id,
                "name": kb.name,
                "description": kb.description,
                "word_count": kb.word_count,
                "usage_count": kb.usage_count,
                "used_task_count": kb.used_task_count,
                "chunk_count": chunk_counts.get(kb.id, 0),
                "vectorized_count": vector_counts.get(kb.id, 0),
                "updated_at": kb.updated_at.isoformat() if kb.updated_at else None,
            }
            for kb in rows
        ],
    }


async def build_ai_config_panel(db: AsyncSession) -> dict:
    models = (await db.execute(select(AiModel).order_by(AiModel.failover_priority, AiModel.id))).scalars().all()
    prompts = (await db.execute(select(Prompt).order_by(Prompt.id.desc()).limit(50))).scalars().all()
    return {
        "ai_stats": await _ai_stats(db),
        "orchestration": await _orchestration_stats(db),
        "workflow_catalog": _workflow_catalog(),
        "models": [
            {
                "id": m.id,
                "name": m.name,
                "model_id": m.model_id,
                "model_type": m.model_type or "chat",
                "status": m.status,
                "used_today": m.used_today,
                "total_used": m.total_used,
                "daily_limit": m.daily_limit,
            }
            for m in models
        ],
        "prompts": [
            {"id": p.id, "name": p.name, "type": p.type, "preview": (p.content or "")[:80]}
            for p in prompts
        ],
    }


async def _material_stats(db: AsyncSession) -> dict:
    knowledge_chunks = int(await db.scalar(select(func.count()).select_from(KnowledgeChunk)) or 0)
    vectorized_chunks = int(
        await db.scalar(
            select(func.count()).select_from(KnowledgeChunk).where(KnowledgeChunk.embedding_vector.is_not(None))
        )
        or 0
    )
    body_prompts = int(
        await db.scalar(select(func.count()).select_from(Prompt).where(Prompt.type == "body")) or 0
    )
    special_prompts = int(
        await db.scalar(select(func.count()).select_from(Prompt).where(Prompt.type == "special")) or 0
    )

    stats = {
        "keyword_libraries": await _safe_table_count(db, "keyword_libraries"),
        "total_keywords": await _safe_table_count(db, "keywords"),
        "title_libraries": await _safe_table_count(db, "title_libraries"),
        "total_titles": await _safe_table_count(db, "titles"),
        "image_libraries": await _safe_table_count(db, "image_libraries"),
        "total_images": await _safe_table_count(db, "images"),
        "knowledge_bases": int(await db.scalar(select(func.count()).select_from(KnowledgeBase)) or 0),
        "knowledge_chunks": knowledge_chunks,
        "vectorized_chunks": vectorized_chunks,
        "unvectorized_chunks": max(0, knowledge_chunks - vectorized_chunks),
        "knowledge_usage_count": int(
            await db.scalar(select(func.count()).select_from(Task).where(Task.knowledge_base_id.is_not(None))) or 0
        ),
        "active_embedding_models": int(
            await db.scalar(
                select(func.count()).select_from(AiModel).where(AiModel.status == "active", AiModel.model_type == "embedding")
            )
            or 0
        ),
        "authors": int(await db.scalar(select(func.count()).select_from(Author)) or 0),
        "body_prompts": body_prompts,
        "special_prompts": special_prompts,
    }
    return stats


async def _ai_stats(db: AsyncSession) -> dict:
    return {
        "model_count": int(
            await db.scalar(select(func.count()).select_from(AiModel).where(AiModel.status == "active")) or 0
        ),
        "chat_models": int(
            await db.scalar(
                select(func.count()).select_from(AiModel).where(AiModel.status == "active", AiModel.model_type == "chat")
            )
            or 0
        ),
        "embedding_models": int(
            await db.scalar(
                select(func.count())
                .select_from(AiModel)
                .where(AiModel.status == "active", AiModel.model_type == "embedding")
            )
            or 0
        ),
        "prompt_count": int(await db.scalar(select(func.count()).select_from(Prompt)) or 0),
        "total_usage": int(await db.scalar(select(func.coalesce(func.sum(AiModel.total_used), 0))) or 0),
        "today_usage": int(await db.scalar(select(func.coalesce(func.sum(AiModel.used_today), 0))) or 0),
    }


async def _orchestration_stats(db: AsyncSession) -> dict:
    base = {
        "backend": "internal",
        "sidecar_healthy": True,
        "driver_hint": "langgraph",
        "totals_24h": {"completed": 0, "failed": 0, "pending": 0, "running": 0, "expired": 0},
        "by_workflow": {},
        "recent_failures": [],
        "knowledge_pending": 0,
    }

    if not await _table_exists(db, "content_agent_requests"):
        try:
            since = _utc_naive_hours_ago(24)
            runs = (
                await db.execute(
                    select(TaskRun.status, func.count())
                    .where(TaskRun.created_at >= since)
                    .group_by(TaskRun.status)
                )
            ).all()
            counts = {str(s): int(c) for s, c in runs}
            base["totals_24h"] = {
                "completed": counts.get("completed", 0),
                "failed": counts.get("failed", 0),
                "pending": counts.get("pending", 0) + counts.get("queued", 0),
                "running": counts.get("running", 0),
                "expired": 0,
            }
            base["by_workflow"] = {
                "content_pipeline": {
                    "completed": counts.get("completed", 0),
                    "failed": counts.get("failed", 0),
                    "pending": counts.get("pending", 0) + counts.get("queued", 0),
                }
            }
        except Exception:
            logger.exception("orchestration_task_run_fallback_failed")
            await db.rollback()
        return base

    try:
        since = _utc_naive_hours_ago(24)
        rows = (
            await db.execute(
                text(
                    """
                    SELECT status, COUNT(*) AS c
                    FROM content_agent_requests
                    WHERE submitted_at >= :since
                    GROUP BY status
                    """
                ),
                {"since": since},
            )
        ).all()
        status_counts = {str(r[0]): int(r[1]) for r in rows}
        base["totals_24h"] = {
            "completed": status_counts.get("completed", 0),
            "failed": status_counts.get("failed", 0),
            "pending": status_counts.get("pending", 0),
            "running": status_counts.get("running", 0),
            "expired": status_counts.get("expired", 0),
        }

        wf_rows = (
            await db.execute(
                text(
                    """
                    SELECT workflow_type, status, COUNT(*) AS c
                    FROM content_agent_requests
                    WHERE submitted_at >= :since
                    GROUP BY workflow_type, status
                    """
                ),
                {"since": since},
            )
        ).all()
        by_workflow: dict[str, dict[str, int]] = {}
        for wf_type, status, count in wf_rows:
            bucket = by_workflow.setdefault(str(wf_type), {})
            bucket[str(status)] = int(count)
        for wf_key in WORKFLOW_LABELS:
            stats = by_workflow.get(wf_key, {})
            base["by_workflow"][wf_key] = {
                "completed": stats.get("completed", 0),
                "failed": stats.get("failed", 0),
                "pending": stats.get("pending", 0) + stats.get("running", 0),
            }

        fail_rows = (
            await db.execute(
                text(
                    """
                    SELECT request_id, workflow_type, error_message
                    FROM content_agent_requests
                    WHERE status = 'failed'
                    ORDER BY id DESC
                    LIMIT 5
                    """
                )
            )
        ).all()
        base["recent_failures"] = [
            {"request_id": r[0], "workflow_type": r[1], "error_message": (r[2] or "")[:120]} for r in fail_rows
        ]

        pending = await db.scalar(
            text(
                """
                SELECT COUNT(*) FROM content_agent_requests
                WHERE correlation_type = 'knowledge_base'
                  AND status IN ('pending', 'running')
                """
            )
        )
        base["knowledge_pending"] = int(pending or 0)
    except Exception:
        logger.exception("orchestration_stats_query_failed")
        await db.rollback()

    return base


def _workflow_catalog() -> dict:
    path = Path(__file__).resolve().parents[2] / "ai" / "config" / "workflows.yml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        logger.exception("workflow_catalog_load_failed path=%s", path)
        return {"default_workflow": "content_pipeline", "workflows": {}}

    workflows = data.get("workflows", {})
    catalog: dict[str, dict] = {}
    for key, wf in workflows.items():
        if not isinstance(wf, dict):
            continue
        nodes = wf.get("nodes", [])
        steps = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            steps.append(
                {
                    "id": node.get("id", ""),
                    "label": node.get("id", ""),
                    "type": node.get("type", "rule"),
                    "agent": node.get("agent"),
                }
            )
        catalog[key] = {
            "description": wf.get("description", ""),
            "visual_layout": "linear",
            "visual_steps": steps,
        }

    return {"default_workflow": "content_pipeline", "workflows": catalog}


async def _safe_table_count(db: AsyncSession, table: str) -> int:
    if not await _table_exists(db, table):
        return 0
    try:
        return int(await db.scalar(text(f"SELECT COUNT(*) FROM {table}")) or 0)
    except Exception:
        logger.exception("safe_table_count_failed table=%s", table)
        await db.rollback()
        return 0


async def _table_exists(db: AsyncSession, table: str) -> bool:
    """用 information_schema 探测表是否存在，避免 SELECT FROM 缺失表导致事务中止。"""
    if not table.replace("_", "").isalnum():
        return False
    try:
        exists = await db.scalar(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = :table
                )
                """
            ),
            {"table": table},
        )
        return bool(exists)
    except Exception:
        logger.exception("table_exists_check_failed table=%s", table)
        await db.rollback()
        return False
