"""Content Agent 请求追踪与回调落库。"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists

logger = logging.getLogger(__name__)


async def create_request(
    db: AsyncSession,
    *,
    request_id: str,
    workflow_type: str,
    correlation_type: str = "",
    correlation_id: int | None = None,
    engine: str = "langgraph",
) -> None:
    if not await _table_exists(db, "content_agent_requests"):
        return
    await db.execute(
        text(
            """
            INSERT INTO content_agent_requests
                (request_id, workflow_type, status, engine, correlation_type, correlation_id, submitted_at)
            VALUES (:rid, :wf, 'pending', :eng, :ct, :cid, CURRENT_TIMESTAMP)
            ON CONFLICT (request_id) DO NOTHING
            """
        ),
        {
            "rid": request_id,
            "wf": workflow_type,
            "eng": engine,
            "ct": correlation_type,
            "cid": correlation_id,
        },
    )
    logger.info("content_agent_request_created request_id=%s workflow=%s", request_id, workflow_type)


async def complete_from_callback(
    db: AsyncSession,
    *,
    request_id: str,
    workflow_type: str,
    status: str,
    engine: str = "",
    result: dict | None = None,
    error: str | None = None,
) -> dict:
    import json

    if not await _table_exists(db, "content_agent_requests"):
        logger.warning("content_agent_requests_table_missing request_id=%s", request_id)
        return {"updated": False}

    final_status = "completed" if status in ("success", "completed") else "failed"
    await db.execute(
        text(
            """
            UPDATE content_agent_requests
            SET status = :st,
                engine = COALESCE(NULLIF(:eng, ''), engine),
                error_message = :err,
                result_json = CAST(:res AS JSON),
                completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE request_id = :rid
            """
        ),
        {
            "st": final_status,
            "eng": engine or "",
            "err": (error or "")[:2000],
            "res": json.dumps(result, ensure_ascii=False) if result is not None else None,
            "rid": request_id,
        },
    )

    if workflow_type == "url_import" and result:
        row = (
            await db.execute(
                text(
                    "SELECT correlation_id FROM content_agent_requests WHERE request_id = :rid AND correlation_type = 'url_import_job'"
                ),
                {"rid": request_id},
            )
        ).first()
        if row and row[0]:
            summary = str(result.get("summary") or result.get("library_name") or "")[:500]
            await db.execute(
                text(
                    """
                    UPDATE url_import_jobs
                    SET status = :st,
                        result_summary = :summary,
                        result_json = CAST(:res AS JSON),
                        error_message = :err,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :jid
                    """
                ),
                {
                    "st": "completed" if final_status == "completed" else "failed",
                    "summary": summary,
                    "res": json.dumps(result, ensure_ascii=False),
                    "err": (error or "")[:2000],
                    "jid": int(row[0]),
                },
            )

    logger.info("content_agent_callback_persisted request_id=%s status=%s", request_id, final_status)
    return {"updated": True, "request_id": request_id, "status": final_status}


async def mark_request_running(db: AsyncSession, request_id: str) -> None:
    if not await _table_exists(db, "content_agent_requests"):
        return
    await db.execute(
        text("UPDATE content_agent_requests SET status='running', updated_at=CURRENT_TIMESTAMP WHERE request_id=:rid"),
        {"rid": request_id},
    )
