"""Content Agent 内部回调 — HMAC 签名校验。"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.api.deps import DbSession
from app.api.response import success
from app.core.config import get_settings
from app.services.admin.content_agent_request_service import complete_from_callback

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal/content-agent", tags=["internal"])

_SEEN_NONCES: dict[str, float] = {}
_NONCE_TTL = 600.0


class ContentAgentCallbackBody(BaseModel):
    request_id: str
    workflow_type: str
    status: str = "success"
    engine: str = ""
    result: dict | None = None
    error: str | None = None
    contract_version: str = "1.0"


def _purge_nonces(now: float) -> None:
    dead = [k for k, ts in _SEEN_NONCES.items() if now - ts > _NONCE_TTL]
    for k in dead:
        _SEEN_NONCES.pop(k, None)


def verify_content_agent_signature(request: Request, body: bytes) -> None:
    settings = get_settings()
    secret = (settings.content_agent_callback_secret or "").strip()
    if not secret or secret == "dev-callback-secret":
        if settings.debug or settings.allow_insecure_jwt:
            logger.warning("content_agent_callback_insecure_secret_allowed debug=%s", settings.debug)
            return
        raise HTTPException(status_code=503, detail="callback_secret_not_configured")

    ts = request.headers.get("X-Content-Agent-Timestamp") or ""
    nonce = request.headers.get("X-Content-Agent-Nonce") or ""
    sig = request.headers.get("X-Content-Agent-Signature") or ""
    if not ts or not nonce or not sig:
        raise HTTPException(status_code=401, detail="missing_callback_signature")

    try:
        # 支持 ISO8601
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        skew = abs(time.time() - parsed.timestamp())
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="invalid_callback_timestamp") from exc
    if skew > 300:
        raise HTTPException(status_code=401, detail="callback_timestamp_skew")

    now = time.time()
    _purge_nonces(now)
    if nonce in _SEEN_NONCES:
        raise HTTPException(status_code=401, detail="callback_nonce_replay")
    _SEEN_NONCES[nonce] = now

    body_hash = hashlib.sha256(body).hexdigest()
    path = "/internal/content-agent/callback"
    expected = hmac.new(
        secret.encode("utf-8"),
        f"POST\n{path}\n{ts}\n{nonce}\n{body_hash}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=401, detail="invalid_callback_signature")


@router.post("/callback")
async def content_agent_callback(request: Request, db: DbSession):
    raw = await request.body()
    verify_content_agent_signature(request, raw)
    try:
        body = ContentAgentCallbackBody.model_validate_json(raw)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="invalid_callback_body") from exc

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
