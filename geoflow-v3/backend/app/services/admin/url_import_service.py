"""URL 导入 — Admin BFF（DB 持久化 + Celery）。"""

import logging
from datetime import UTC, datetime

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists

logger = logging.getLogger(__name__)

_IMPORT_HISTORY: list[dict] = []


class UrlImportBody(BaseModel):
    url: str = Field(min_length=8, max_length=500)
    target: str = Field(default="knowledge", pattern="^(knowledge|title|keyword)$")
    library_id: int | None = None
    name: str = ""


async def _persist_job(db: AsyncSession, record: dict) -> None:
    if not await _table_exists(db, "url_import_jobs"):
        return
    await db.execute(
        text(
            """
            INSERT INTO url_import_jobs (id, url, target, library_id, name, status)
            VALUES (:id, :url, :target, :library_id, :name, :status)
            ON CONFLICT (id) DO UPDATE SET status = EXCLUDED.status, updated_at = CURRENT_TIMESTAMP
            """
        ),
        record,
    )


async def run_url_import(db: AsyncSession, body: UrlImportBody) -> dict:
    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="invalid_url")

    if await _table_exists(db, "url_import_jobs"):
        next_id = int(await db.scalar(text("SELECT COALESCE(MAX(id), 0) + 1 FROM url_import_jobs")) or 1)
    else:
        next_id = len(_IMPORT_HISTORY) + 1

    record = {
        "id": next_id,
        "url": url,
        "target": body.target,
        "library_id": body.library_id,
        "name": body.name.strip() or url,
        "status": "queued",
        "created_at": datetime.now(UTC).isoformat(),
    }
    _IMPORT_HISTORY.insert(0, record)
    if len(_IMPORT_HISTORY) > 100:
        _IMPORT_HISTORY.pop()

    await _persist_job(db, record)

    request_id = f"url-import-{record['id']}"
    try:
        from app.services.admin.content_agent_request_service import create_request

        await create_request(
            db,
            request_id=request_id,
            workflow_type="url_import",
            correlation_type="url_import_job",
            correlation_id=record["id"],
        )
    except Exception:
        logger.exception("url_import_request_track_failed id=%s", record["id"])

    try:
        from app.workers.celery_app import celery_app

        celery_app.send_task("app.workers.tasks.import_url_content", args=[record["id"], url, body.target])
    except Exception:
        logger.exception("url_import_queue_failed url=%s", url)
        record["status"] = "failed"
        if await _table_exists(db, "url_import_jobs"):
            await db.execute(
                text("UPDATE url_import_jobs SET status='failed' WHERE id=:id"),
                {"id": record["id"]},
            )

    logger.info("url_import_queued id=%s url=%s target=%s", record["id"], url, body.target)
    return {"job": record}


async def get_url_import_job(db: AsyncSession, job_id: int) -> dict:
    if await _table_exists(db, "url_import_jobs"):
        row = (
            await db.execute(
                text(
                    """
                    SELECT id, url, target, library_id, name, status, error_message, result_summary, result_json, created_at, updated_at
                    FROM url_import_jobs WHERE id=:id
                    """
                ),
                {"id": job_id},
            )
        ).first()
        if row:
            return {
                "job": {
                    "id": int(row[0]),
                    "url": row[1],
                    "target": row[2],
                    "library_id": row[3],
                    "name": row[4],
                    "status": row[5],
                    "error_message": row[6] or "",
                    "result_summary": row[7] or "",
                    "result_json": row[8],
                    "created_at": row[9].isoformat() if row[9] else None,
                    "updated_at": row[10].isoformat() if row[10] else None,
                }
            }
    for item in _IMPORT_HISTORY:
        if item["id"] == job_id:
            return {"job": item}
    raise HTTPException(status_code=404, detail="job_not_found")


async def commit_url_import_job(db: AsyncSession, job_id: int) -> dict:
    from app.models.knowledge import KnowledgeBase

    job = (await get_url_import_job(db, job_id))["job"]
    if job["status"] != "completed":
        raise HTTPException(status_code=422, detail="job_not_completed")

    result = job.get("result_json") if isinstance(job.get("result_json"), dict) else {}
    if not result and isinstance(job.get("result_json"), str):
        import json

        try:
            result = json.loads(job["result_json"])
        except json.JSONDecodeError:
            result = {}
    kb_id = None
    if job.get("target") == "knowledge":
        content = str(result.get("knowledge_markdown") or job.get("result_summary") or job.get("url", ""))
        kb_name = str(result.get("library_name") or job.get("name") or f"Import #{job_id}")
        kb = KnowledgeBase(
            name=kb_name,
            description=f"URL import: {job.get('url', '')}",
            content=content,
            character_count=len(content),
            word_count=len(content.split()),
        )
        db.add(kb)
        await db.flush()
        kb_id = kb.id
        logger.info("url_import_committed_kb id=%s kb_id=%s", job_id, kb_id)
        try:
            from app.workers.celery_app import celery_app

            celery_app.send_task("app.workers.tasks.sync_knowledge_chunks", args=[kb_id])
        except Exception:
            logger.exception("url_import_sync_chunks_queue_failed kb_id=%s", kb_id)
    elif job.get("target") == "title" and job.get("library_id"):
        from app.services.admin.materials_libraries_service import TitleBody, create_title

        titles = result.get("titles") if isinstance(result.get("titles"), list) else []
        for title in titles[:50]:
            t = str(title).strip()
            if t:
                await create_title(db, int(job["library_id"]), TitleBody(title=t))
    elif job.get("target") == "keyword" and job.get("library_id"):
        from app.services.admin.materials_libraries_service import KeywordBody, create_keyword

        keywords = result.get("keywords") if isinstance(result.get("keywords"), list) else []
        for kw in keywords[:30]:
            k = str(kw).strip()
            if k:
                await create_keyword(db, int(job["library_id"]), KeywordBody(keyword=k))

    if await _table_exists(db, "url_import_jobs"):
        await db.execute(
            text("UPDATE url_import_jobs SET status='committed', updated_at=CURRENT_TIMESTAMP WHERE id=:id"),
            {"id": job_id},
        )
    return {"committed": True, "job_id": job_id, "knowledge_base_id": kb_id}


async def list_url_import_history(db: AsyncSession | None = None) -> dict:
    if db and await _table_exists(db, "url_import_jobs"):
        rows = (
            await db.execute(
                text(
                    "SELECT id, url, target, name, status, created_at FROM url_import_jobs ORDER BY id DESC LIMIT 50"
                )
            )
        ).all()
        return {
            "items": [
                {
                    "id": int(r[0]),
                    "url": r[1],
                    "target": r[2],
                    "name": r[3],
                    "status": r[4],
                    "created_at": r[5].isoformat() if r[5] else None,
                }
                for r in rows
            ]
        }
    return {"items": _IMPORT_HISTORY[:50]}
