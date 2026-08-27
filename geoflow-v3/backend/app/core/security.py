"""JWT 与 API Token 鉴权。"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.admin import Admin
from app.models.api_token import ApiAccessToken

settings = get_settings()

ALL_SCOPES = [
    "catalog:read",
    "tasks:read",
    "tasks:write",
    "jobs:read",
    "materials:read",
    "materials:write",
    "articles:read",
    "articles:write",
    "articles:publish",
]

ADMIN_COOKIE_NAME = "gf_token"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


def create_jwt(admin_id: int, username: str, role: str) -> str:
    expire = datetime.now(UTC) + timedelta(hours=settings.jwt_expire_hours)
    payload = {"sub": str(admin_id), "username": username, "role": role, "exp": expire, "type": "admin_jwt"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_jwt(token: str) -> dict[str, Any] | None:
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if data.get("type") != "admin_jwt":
            return None
        return data
    except JWTError:
        return None


def is_super_admin_role(role: str | None) -> bool:
    return (role or "").lower() in ("super_admin", "superadmin")


async def authenticate_admin(db: AsyncSession, username: str, password: str) -> Admin | None:
    result = await db.execute(select(Admin).where(Admin.username == username, Admin.status == "active"))
    admin = result.scalar_one_or_none()
    if admin is None or not verify_password(password, admin.password):
        return None
    return admin


async def load_active_admin(db: AsyncSession, admin_id: int) -> Admin | None:
    result = await db.execute(select(Admin).where(Admin.id == admin_id, Admin.status == "active"))
    return result.scalar_one_or_none()


async def create_api_token(
    db: AsyncSession,
    admin_id: int,
    name: str = "default",
    scopes: list[str] | None = None,
    expires_days: int | None = None,
) -> tuple[str, ApiAccessToken]:
    plain = f"gf_{uuid4().hex}{uuid4().hex[:16]}"
    token_hash = bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()
    ttl = settings.api_token_default_ttl_days if expires_days is None else max(1, min(int(expires_days), 3650))
    expires = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=ttl)
    row = ApiAccessToken(
        admin_id=admin_id,
        name=name,
        token_hash=token_hash,
        token_prefix=plain[:12],
        scopes=scopes or ALL_SCOPES,
        expires_at=expires,
    )
    db.add(row)
    await db.flush()
    return plain, row


async def resolve_api_token(db: AsyncSession, plain_token: str) -> tuple[Admin, list[str]] | None:
    prefix = plain_token[:12]
    result = await db.execute(
        select(ApiAccessToken).where(ApiAccessToken.token_prefix == prefix, ApiAccessToken.revoked_at.is_(None))
    )
    for row in result.scalars():
        if verify_password(plain_token, row.token_hash):
            if row.expires_at and row.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
                return None
            admin = await load_active_admin(db, int(row.admin_id))
            if admin is None:
                return None
            row.last_used_at = datetime.now(UTC).replace(tzinfo=None)
            return admin, row.scopes or ALL_SCOPES
    return None


def token_has_scope(scopes: list[str], required: str) -> bool:
    return "*" in scopes or required in scopes


def admin_cookie_max_age() -> int:
    return max(3600, int(settings.jwt_expire_hours) * 3600)
