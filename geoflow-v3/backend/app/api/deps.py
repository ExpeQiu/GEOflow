"""FastAPI 依赖注入。"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_jwt, resolve_api_token, token_has_scope
from app.models.admin import Admin

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_request_id(x_request_id: str | None = Header(default=None)) -> str:
    return x_request_id or "req-local"


async def get_api_auth(
    db: DbSession,
    authorization: str | None = Header(default=None),
) -> tuple[Admin, list[str]]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing_bearer_token")
    plain = authorization[7:].strip()
    resolved = await resolve_api_token(db, plain)
    if resolved is None:
        raise HTTPException(status_code=401, detail="invalid_token")
    return resolved


async def get_admin_jwt(
    authorization: str | None = Header(default=None),
) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing_jwt")
    payload = decode_jwt(authorization[7:].strip())
    if payload is None:
        raise HTTPException(status_code=401, detail="invalid_jwt")
    return payload


def require_scope(scopes: list[str], required: str) -> None:
    if not token_has_scope(scopes, required):
        raise HTTPException(status_code=403, detail=f"missing_scope:{required}")
