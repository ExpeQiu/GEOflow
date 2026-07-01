"""FastAPI entrypoint."""

from __future__ import annotations

import logging
import os
import uuid

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.config.loader import config_dir, load_agents_config, load_workflows_config
from app.orchestration import create_backend

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(title="GEOFlow Content Agent", version="0.1.0")
backend = create_backend()

load_agents_config()
load_workflows_config()
logger = logging.getLogger("content_agent.main")
logger.info("content_agent_started config_dir=%s engine=%s", config_dir(), backend.engine_name())


class RunAsyncRequest(BaseModel):
    request_id: str | None = None
    contract_version: str = "1.0"
    callback_url: str | None = None
    payload: dict = Field(default_factory=dict)


@app.get("/v1/health")
async def health():
    return {
        "ok": True,
        "engine": backend.engine_name(),
        "contract_version": os.getenv("CONTENT_AGENT_CONTRACT_VERSION", "1.0"),
    }


@app.post("/v1/workflows/{workflow_type}/run_async")
async def run_async(workflow_type: str, body: RunAsyncRequest, background: BackgroundTasks):
    if workflow_type not in {"content", "content_pipeline", "url_import", "semantic_chunk"}:
        raise HTTPException(status_code=404, detail="workflow_not_found")

    request_id = body.request_id or str(uuid.uuid4())
    if body.callback_url:
        os.environ["LARAVEL_CALLBACK_URL"] = body.callback_url

    background.add_task(_execute, workflow_type, body.model_dump(), request_id)
    return {"request_id": request_id, "status": "accepted"}


async def _execute(workflow_type: str, envelope: dict, request_id: str) -> None:
    try:
        await backend.run_workflow(workflow_type, envelope, request_id)
    except Exception as exc:  # noqa: BLE001
        await _callback_error(request_id, workflow_type, str(exc))


async def _callback_error(request_id: str, workflow_type: str, error: str) -> None:
    callback_url = os.getenv("LARAVEL_CALLBACK_URL", "").strip()
    secret = os.getenv("CONTENT_AGENT_CALLBACK_SECRET", "").strip()
    if callback_url == "" or secret == "":
        return

    import hashlib
    import hmac
    import json
    import uuid
    from datetime import datetime, timezone

    import httpx

    body = json.dumps(
        {
            "contract_version": os.getenv("CONTENT_AGENT_CONTRACT_VERSION", "1.0"),
            "request_id": request_id,
            "workflow_type": workflow_type,
            "status": "failed",
            "engine": backend.engine_name(),
            "result": None,
            "error": error,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    path = "/internal/content-agent/callback"
    timestamp = datetime.now(timezone.utc).isoformat()
    nonce = str(uuid.uuid4())
    body_hash = hashlib.sha256(body).hexdigest()
    signature = hmac.new(
        secret.encode("utf-8"),
        f"POST\n{path}\n{timestamp}\n{nonce}\n{body_hash}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-Content-Agent-Timestamp": timestamp,
        "X-Content-Agent-Nonce": nonce,
        "X-Content-Agent-Signature": signature,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        await client.post(callback_url, content=body, headers=headers)
