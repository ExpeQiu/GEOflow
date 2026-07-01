"""URL 导入 — Admin BFF（简化流水线）。"""

import logging
from datetime import UTC, datetime

from fastapi import HTTPException
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_IMPORT_HISTORY: list[dict] = []


class UrlImportBody(BaseModel):
    url: str = Field(min_length=8, max_length=500)
    target: str = Field(default="knowledge", pattern="^(knowledge|title|keyword)$")
    library_id: int | None = None
    name: str = ""


async def run_url_import(db: AsyncSession, body: UrlImportBody) -> dict:
    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="invalid_url")

    record = {
        "id": len(_IMPORT_HISTORY) + 1,
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

    try:
        from app.workers.celery_app import celery_app

        celery_app.send_task("app.workers.tasks.import_url_content", args=[record["id"], url, body.target])
    except Exception:
        logger.exception("url_import_queue_failed url=%s", url)
        record["status"] = "failed"

    logger.info("url_import_queued id=%s url=%s target=%s", record["id"], url, body.target)
    return {"job": record}


async def list_url_import_history() -> dict:
    return {"items": _IMPORT_HISTORY[:50]}
