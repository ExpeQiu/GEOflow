"""FastAPI 依赖注入。"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    ADMIN_COOKIE_NAME,
    decode_jwt,
    is_super_admin_role,
    load_active_admin,
    resolve_api_token,
    token_has_scope,
)
from app.models.admin import Admin

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_request_id(x_request_id: str | None = Header(default=None)) -> str:
    return x_request_id or "req-local"


def extract_bearer_or_cookie(request: Request, authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    cookie = request.cookies.get(ADMIN_COOKIE_NAME)
    if cookie:
        return cookie.strip()
    return None


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
    request: Request,
    db: DbSession,
    authorization: str | None = Header(default=None),
) -> dict:
    token = extract_bearer_or_cookie(request, authorization)
    if not token:
        raise HTTPException(status_code=401, detail="missing_jwt")
    payload = decode_jwt(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="invalid_jwt")
    admin_id = int(payload.get("sub") or 0)
    admin = await load_active_admin(db, admin_id)
    if admin is None:
        raise HTTPException(status_code=401, detail="admin_disabled_or_missing")
    payload["role"] = admin.role
    payload["username"] = admin.username
    return payload


async def require_super_admin(jwt: Annotated[dict, Depends(get_admin_jwt)]) -> dict:
    if not is_super_admin_role(jwt.get("role")):
        raise HTTPException(status_code=403, detail="super_admin_required")
    return jwt


def require_scope(scopes: list[str], required: str) -> None:
    if not token_has_scope(scopes, required):
        raise HTTPException(status_code=403, detail=f"missing_scope:{required}")
