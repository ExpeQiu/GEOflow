"""v1 API 幂等键处理。"""

import hashlib
import json
import logging

from fastapi import HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists

logger = logging.getLogger(__name__)


def _hash_body(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


async def check_idempotency(
    db: AsyncSession,
    request: Request,
    route_key: str,
    body_bytes: bytes,
) -> dict | None:
    """若命中幂等键则返回已缓存响应体，否则返回 None。"""
    key = request.headers.get("Idempotency-Key", "").strip()
    if not key or not await _table_exists(db, "api_idempotency_keys"):
        return None

    req_hash = _hash_body(body_bytes)
    row = (
        await db.execute(
            text(
                """
                SELECT response_body, response_status, request_hash
                FROM api_idempotency_keys
                WHERE idempotency_key = :k AND route_key = :r
                """
            ),
            {"k": key, "r": route_key},
        )
    ).first()
    if not row:
        return None
    if row[2] != req_hash:
        raise HTTPException(status_code=409, detail="idempotency_key_reused_with_different_body")
    logger.info("idempotency_cache_hit route=%s key=%s", route_key, key[:16])
    return {"body": json.loads(row[0]), "status": int(row[1])}


async def store_idempotency(
    db: AsyncSession,
    request: Request,
    route_key: str,
    body_bytes: bytes,
    response_body: dict,
    response_status: int,
) -> None:
    key = request.headers.get("Idempotency-Key", "").strip()
    if not key or not await _table_exists(db, "api_idempotency_keys"):
        return
    await db.execute(
        text(
            """
            INSERT INTO api_idempotency_keys
                (idempotency_key, route_key, request_hash, response_body, response_status)
            VALUES (:k, :r, :h, :b, :s)
            ON CONFLICT (idempotency_key, route_key) DO UPDATE SET
                request_hash = EXCLUDED.request_hash,
                response_body = EXCLUDED.response_body,
                response_status = EXCLUDED.response_status,
                updated_at = CURRENT_TIMESTAMP
            """
        ),
        {
            "k": key,
            "r": route_key,
            "h": _hash_body(body_bytes),
            "b": json.dumps(response_body, ensure_ascii=False),
            "s": response_status,
        },
    )
