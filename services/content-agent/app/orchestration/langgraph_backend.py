"""LangGraph-backed orchestration — reads config/workflows.yml + config/agents.yml."""

from __future__ import annotations

import json
import os
import re

import httpx

from app.workflows.content import run_content_workflow
from app.workflows.semantic_chunk import run_semantic_chunk_workflow
from app.workflows.url_import import run_url_import_workflow


class LangGraphBackend:
    def engine_name(self) -> str:
        return "langgraph"

    async def run_workflow(self, workflow_type: str, payload: dict, request_id: str) -> dict:
        inner = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload

        if workflow_type == "content":
            result = await run_content_workflow(inner)
        elif workflow_type == "url_import":
            result = await run_url_import_workflow(inner)
        elif workflow_type == "semantic_chunk":
            result = await run_semantic_chunk_workflow(inner)
        else:
            raise ValueError(f"unsupported workflow: {workflow_type}")

        await self._callback(request_id, workflow_type, result)
        return result

    async def _callback(self, request_id: str, workflow_type: str, result: dict) -> None:
        callback_url = os.getenv("LARAVEL_CALLBACK_URL", "").strip()
        secret = os.getenv("CONTENT_AGENT_CALLBACK_SECRET", "").strip()
        if callback_url == "" or secret == "":
            return

        body = json.dumps(
            {
                "contract_version": os.getenv("CONTENT_AGENT_CONTRACT_VERSION", "1.0"),
                "request_id": request_id,
                "workflow_type": workflow_type,
                "status": "success",
                "engine": self.engine_name(),
                "result": result,
                "error": None,
            },
            ensure_ascii=False,
        ).encode("utf-8")

        import hashlib
        import hmac
        import uuid
        from datetime import datetime, timezone

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
            for attempt in range(3):
                try:
                    response = await client.post(callback_url, content=body, headers=headers)
                    if response.status_code < 500:
                        return
                except httpx.HTTPError:
                    pass
                await _sleep_backoff(attempt)

    @staticmethod
    def _extract_json(text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


async def _sleep_backoff(attempt: int) -> None:
    import asyncio

    await asyncio.sleep(min(2 ** attempt, 8))
