from datetime import UTC, datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.api.deps import DbSession
from app.api.response import success
from app.core.security import ALL_SCOPES, authenticate_admin, create_api_token, hash_password
from app.models.admin import Admin
from sqlalchemy import select

router = APIRouter()


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
async def login(request: Request, body: LoginBody, db: DbSession):
    admin = await authenticate_admin(db, body.username.strip(), body.password)
    if admin is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="invalid_credentials")
    admin.last_login = datetime.now(UTC)
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
    """geoflow-admin 专用 JWT 登录。"""
    from app.core.security import create_jwt

    admin = await authenticate_admin(db, body.username.strip(), body.password)
    if admin is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="invalid_credentials")
    admin.last_login = datetime.now(UTC)
    jwt_token = create_jwt(admin.id, admin.username, admin.role)
    return success(
        request,
        {
            "access_token": jwt_token,
            "token_type": "Bearer",
            "admin": {"id": admin.id, "username": admin.username, "name": admin.name, "role": admin.role},
        },
    )
