"""Content Agent 内部回调 — 替代 Laravel internal route。"""

import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.api.deps import DbSession
from app.api.response import success
from app.services.admin.content_agent_request_service import complete_from_callback

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal/content-agent", tags=["internal"])


class ContentAgentCallbackBody(BaseModel):
    request_id: str
    workflow_type: str
    status: str = "success"
    engine: str = ""
    result: dict | None = None
    error: str | None = None


@router.post("/callback")
async def content_agent_callback(body: ContentAgentCallbackBody, request: Request, db: DbSession):
    logger.info(
        "content_agent_callback request_id=%s workflow=%s status=%s",
        body.request_id,
        body.workflow_type,
        body.status,
    )
    outcome = await complete_from_callback(
        db,
        request_id=body.request_id,
        workflow_type=body.workflow_type,
        status=body.status,
        engine=body.engine,
        result=body.result,
        error=body.error,
    )
    await db.commit()
    return success(request, {"received": True, "request_id": body.request_id, **outcome})
