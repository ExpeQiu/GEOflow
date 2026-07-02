"""站点/安全/超管 CRUD — Admin BFF。"""

import hashlib
import logging
import secrets

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists
from app.services.admin.settings_service import build_site_settings_payload

logger = logging.getLogger(__name__)


class SiteSettingBody(BaseModel):
    setting_key: str = Field(min_length=1, max_length=100)
    setting_value: str = ""
    value_type: str = "string"
    group_name: str = "general"


class SensitiveWordsBody(BaseModel):
    words: str = ""


class AdminUserBody(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    email: str = ""
    display_name: str = ""


class ApiTokenBody(BaseModel):
    name: str = "default"
    scopes: list[str] = Field(default_factory=list)


class PasswordChangeBody(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6, max_length=100)


class AdminUserUpdateBody(BaseModel):
    email: str = ""
    display_name: str = ""
    password: str = ""
    status: str = Field(default="", pattern="^(|active|disabled)$")


async def _require_settings_table(db: AsyncSession) -> None:
    if not await _table_exists(db, "site_settings"):
        raise HTTPException(status_code=503, detail="site_settings_not_migrated")


async def get_site_settings_full(db: AsyncSession) -> dict:
    base = build_site_settings_payload()
    if not await _table_exists(db, "site_settings"):
        return {**base, "db_settings": [], "editable": False}
    rows = (await db.execute(text("SELECT setting_key, setting_value, value_type, group_name FROM site_settings ORDER BY group_name, setting_key"))).all()
    return {
        **base,
        "editable": True,
        "db_settings": [
            {"key": r[0], "value": r[1] or "", "value_type": r[2], "group": r[3]} for r in rows
        ],
    }


async def upsert_site_setting(db: AsyncSession, body: SiteSettingBody) -> dict:
    await _require_settings_table(db)
    await db.execute(
        text(
            """
            INSERT INTO site_settings (setting_key, setting_value, value_type, group_name)
            VALUES (:k, :v, :t, :g)
            ON CONFLICT (setting_key) DO UPDATE SET
                setting_value = EXCLUDED.setting_value,
                value_type = EXCLUDED.value_type,
                group_name = EXCLUDED.group_name,
                updated_at = CURRENT_TIMESTAMP
            """
        ),
        {"k": body.setting_key, "v": body.setting_value, "t": body.value_type, "g": body.group_name},
    )
    logger.info("site_setting_upsert key=%s", body.setting_key)
    return {"item": body.model_dump()}


async def get_sensitive_words(db: AsyncSession) -> dict:
    await _require_settings_table(db)
    row = (
        await db.execute(text("SELECT setting_value FROM site_settings WHERE setting_key = 'sensitive_words'"))
    ).first()
    return {"words": (row[0] if row else "") or ""}


async def save_sensitive_words(db: AsyncSession, body: SensitiveWordsBody) -> dict:
    await upsert_site_setting(
        db,
        SiteSettingBody(setting_key="sensitive_words", setting_value=body.words, group_name="security"),
    )
    return {"saved": True}


async def list_admin_users(db: AsyncSession) -> dict:
    rows = (
        await db.execute(text("SELECT id, username, email, display_name, role, status, last_login FROM admins ORDER BY id"))
    ).all()
    return {
        "items": [
            {
                "id": int(r[0]),
                "username": r[1],
                "email": r[2] or "",
                "display_name": r[3] or "",
                "role": r[4],
                "status": r[5],
                "last_login": r[6].isoformat() if r[6] else None,
            }
            for r in rows
        ]
    }


async def create_admin_user(db: AsyncSession, body: AdminUserBody) -> dict:
    from passlib.context import CryptContext

    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = pwd_ctx.hash(body.password)
    try:
        row = (
            await db.execute(
                text(
                    "INSERT INTO admins (username, password, email, display_name) VALUES (:u, :p, :e, :d) RETURNING id"
                ),
                {"u": body.username.strip(), "p": hashed, "e": body.email.strip(), "d": body.display_name.strip()},
            )
        ).first()
    except Exception as exc:
        raise HTTPException(status_code=422, detail="username_exists") from exc
    await db.flush()
    logger.info("admin_user_created id=%s username=%s", row[0], body.username)
    return {"item": {"id": int(row[0]), "username": body.username.strip()}}


async def list_api_tokens(db: AsyncSession) -> dict:
    if not await _table_exists(db, "api_access_tokens"):
        return {"items": []}
    rows = (
        await db.execute(
            text(
                "SELECT id, name, token_prefix, scopes, expires_at, revoked_at, last_used_at FROM api_access_tokens ORDER BY id DESC LIMIT 50"
            )
        )
    ).all()
    return {
        "items": [
            {
                "id": int(r[0]),
                "name": r[1],
                "token_prefix": r[2],
                "scopes": r[3] or [],
                "expires_at": r[4].isoformat() if r[4] else None,
                "revoked_at": r[5].isoformat() if r[5] else None,
                "last_used_at": r[6].isoformat() if r[6] else None,
            }
            for r in rows
        ]
    }


async def create_api_token(db: AsyncSession, admin_id: int, body: ApiTokenBody) -> dict:
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    prefix = raw[:8]
    row = (
        await db.execute(
            text(
                """
                INSERT INTO api_access_tokens (admin_id, name, token_hash, token_prefix, scopes)
                VALUES (:aid, :n, :h, :p, :s) RETURNING id
                """
            ),
            {"aid": admin_id, "n": body.name, "h": token_hash, "p": prefix, "s": body.scopes},
        )
    ).first()
    await db.flush()
    logger.info("api_token_created id=%s prefix=%s", row[0], prefix)
    return {"item": {"id": int(row[0]), "token": raw, "token_prefix": prefix}}


async def revoke_api_token(db: AsyncSession, token_id: int) -> dict:
    if not await _table_exists(db, "api_access_tokens"):
        raise HTTPException(status_code=503, detail="api_tokens_not_migrated")
    result = await db.execute(
        text("UPDATE api_access_tokens SET revoked_at = CURRENT_TIMESTAMP WHERE id = :id AND revoked_at IS NULL"),
        {"id": token_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="token_not_found")
    logger.info("api_token_revoked id=%s", token_id)
    return {"revoked": True, "id": token_id}


async def update_admin_user(db: AsyncSession, admin_id: int, body: AdminUserUpdateBody) -> dict:
    from passlib.context import CryptContext

    row = (await db.execute(text("SELECT id FROM admins WHERE id = :id"), {"id": admin_id})).first()
    if not row:
        raise HTTPException(status_code=404, detail="admin_not_found")
    params: dict = {"id": admin_id, "e": body.email.strip(), "d": body.display_name.strip()}
    sets = ["email = :e", "display_name = :d"]
    if body.password.strip():
        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        params["p"] = pwd_ctx.hash(body.password.strip())
        sets.append("password = :p")
    if body.status:
        params["s"] = body.status
        sets.append("status = :s")
    await db.execute(text(f"UPDATE admins SET {', '.join(sets)} WHERE id = :id"), params)
    logger.info("admin_user_updated id=%s", admin_id)
    return {"item": {"id": admin_id}}


async def toggle_admin_user(db: AsyncSession, admin_id: int) -> dict:
    row = (
        await db.execute(text("SELECT status FROM admins WHERE id = :id"), {"id": admin_id})
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="admin_not_found")
    new_status = "disabled" if row[0] == "active" else "active"
    await db.execute(text("UPDATE admins SET status = :s WHERE id = :id"), {"s": new_status, "id": admin_id})
    logger.info("admin_user_toggled id=%s status=%s", admin_id, new_status)
    return {"item": {"id": admin_id, "status": new_status}}


async def delete_admin_user(db: AsyncSession, admin_id: int) -> dict:
    result = await db.execute(text("DELETE FROM admins WHERE id = :id"), {"id": admin_id})
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="admin_not_found")
    logger.info("admin_user_deleted id=%s", admin_id)
    return {"deleted": True}


async def change_admin_password(db: AsyncSession, admin_id: int, body: PasswordChangeBody) -> dict:
    from passlib.context import CryptContext

    row = (
        await db.execute(text("SELECT password FROM admins WHERE id = :id"), {"id": admin_id})
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="admin_not_found")
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    if not pwd_ctx.verify(body.current_password, row[0]):
        raise HTTPException(status_code=422, detail="invalid_current_password")
    hashed = pwd_ctx.hash(body.new_password)
    await db.execute(text("UPDATE admins SET password = :p WHERE id = :id"), {"p": hashed, "id": admin_id})
    logger.info("admin_password_changed id=%s", admin_id)
    return {"changed": True}


async def list_activity_logs(db: AsyncSession) -> dict:
    if not await _table_exists(db, "admin_activity_logs"):
        return {"items": []}
    rows = (
        await db.execute(
            text(
                "SELECT id, admin_id, action, resource_type, resource_id, detail, created_at FROM admin_activity_logs ORDER BY id DESC LIMIT 100"
            )
        )
    ).all()
    return {
        "items": [
            {
                "id": int(r[0]),
                "admin_id": r[1],
                "action": r[2],
                "resource_type": r[3],
                "resource_id": r[4],
                "detail": r[5] or "",
                "created_at": r[6].isoformat() if r[6] else None,
            }
            for r in rows
        ]
    }


async def rotate_channel_secret(db: AsyncSession, channel_id: int) -> dict:
    if not await _table_exists(db, "distribution_channel_secrets"):
        raise HTTPException(status_code=503, detail="secrets_not_migrated")
    raw = secrets.token_urlsafe(24)
    secret_hash = hashlib.sha256(raw.encode()).hexdigest()
    prefix = raw[:8]
    await db.execute(
        text(
            """
            INSERT INTO distribution_channel_secrets (channel_id, secret_hash, secret_prefix, label)
            VALUES (:cid, :h, :p, 'rotated')
            """
        ),
        {"cid": channel_id, "h": secret_hash, "p": prefix},
    )
    logger.info("channel_secret_rotated channel_id=%s prefix=%s", channel_id, prefix)
    return {"secret": raw, "secret_prefix": prefix, "channel_id": channel_id}
