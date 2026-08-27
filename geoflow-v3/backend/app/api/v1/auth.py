from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.api.deps import DbSession, get_admin_jwt
from app.api.response import success
from app.core.config import get_settings
from app.core.login_guard import clear_failures, is_locked, record_failure
from app.core.security import (
    ADMIN_COOKIE_NAME,
    ALL_SCOPES,
    admin_cookie_max_age,
    authenticate_admin,
    create_api_token,
    create_jwt,
)
from app.models.admin import Admin

router = APIRouter()


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=100)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


def _set_admin_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=not settings.debug,
        max_age=admin_cookie_max_age(),
        path="/",
    )


def _clear_admin_cookie(response: Response) -> None:
    response.delete_cookie(key=ADMIN_COOKIE_NAME, path="/")


@router.post("/auth/login")
async def login(request: Request, body: LoginBody, db: DbSession):
    ip = _client_ip(request)
    locked, remaining = is_locked(body.username, ip)
    if locked:
        raise HTTPException(status_code=429, detail=f"login_locked:{remaining}")
    admin = await authenticate_admin(db, body.username.strip(), body.password)
    if admin is None:
        record_failure(body.username, ip)
        raise HTTPException(status_code=401, detail="invalid_credentials")
    clear_failures(body.username, ip)
    admin.last_login = _utcnow()
    plain, token_row = await create_api_token(db, admin.id, scopes=ALL_SCOPES)
    return success(
        request,
        {
            "token": plain,
            "token_type": "Bearer",
            "expires_at": token_row.expires_at.isoformat() if token_row.expires_at else None,
            "scopes": token_row.scopes,
            "admin": {"id": admin.id, "username": admin.username, "name": admin.name, "role": admin.role},
        },
    )


@router.post("/auth/admin-login")
async def admin_login_jwt(request: Request, body: LoginBody, db: DbSession):
    """geoflow-admin 专用 JWT 登录；同时下发 HttpOnly Cookie。"""
    ip = _client_ip(request)
    locked, remaining = is_locked(body.username, ip)
    if locked:
        raise HTTPException(status_code=429, detail=f"login_locked:{remaining}")
    admin = await authenticate_admin(db, body.username.strip(), body.password)
    if admin is None:
        record_failure(body.username, ip)
        raise HTTPException(status_code=401, detail="invalid_credentials")
    clear_failures(body.username, ip)
    admin.last_login = _utcnow()
    jwt_token = create_jwt(admin.id, admin.username, admin.role)
    payload = {
        "access_token": jwt_token,
        "token_type": "Bearer",
        "admin": {"id": admin.id, "username": admin.username, "name": admin.name, "role": admin.role},
    }
    # 直接构造 Response 以设置 Cookie，同时保持 success 信封
    from fastapi.responses import JSONResponse

    body_out = {
        "success": True,
        "data": payload,
        "meta": {"request_id": getattr(request.state, "request_id", "local")},
        "status": 200,
    }
    resp = JSONResponse(content=body_out)
    _set_admin_cookie(resp, jwt_token)
    return resp


@router.post("/auth/admin-logout")
async def admin_logout(request: Request, response: Response, jwt=Depends(get_admin_jwt)):
    _clear_admin_cookie(response)
    return success(request, {"logged_out": True})


@router.get("/auth/admin-session")
async def admin_session(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    admin = await db.get(Admin, int(jwt.get("sub") or 0))
    if admin is None or admin.status != "active":
        raise HTTPException(status_code=401, detail="admin_disabled_or_missing")
    return success(
        request,
        {"admin": {"id": admin.id, "username": admin.username, "name": admin.name, "role": admin.role}},
    )
