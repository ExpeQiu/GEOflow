"""站点/安全/超管 CRUD — Admin BFF。"""

import hashlib
import logging
import secrets

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists
from app.services.admin.settings_service import build_security_runtime_payload, build_site_settings_payload

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
    expires_days: int | None = Field(default=None, ge=1, le=3650)


class PasswordChangeBody(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6, max_length=100)


class AdminUserUpdateBody(BaseModel):
    email: str = ""
    display_name: str = ""
    password: str = ""
    status: str = Field(default="", pattern="^(|active|disabled)$")


def _actor_id(jwt: dict | None) -> int:
    if not jwt:
        return 0
    return int(jwt.get("sub", 0) or 0)


async def _require_settings_table(db: AsyncSession) -> None:
    if not await _table_exists(db, "site_settings"):
        raise HTTPException(status_code=503, detail="site_settings_not_migrated")


async def write_activity_log(
    db: AsyncSession,
    admin_id: int,
    action: str,
    resource_type: str = "",
    resource_id: str = "",
    detail: str = "",
) -> None:
    if not await _table_exists(db, "admin_activity_logs"):
        return
    await db.execute(
        text(
            """
            INSERT INTO admin_activity_logs (admin_id, action, resource_type, resource_id, detail)
            VALUES (:aid, :a, :rt, :rid, :d)
            """
        ),
        {
            "aid": admin_id or None,
            "a": action[:100],
            "rt": (resource_type or "")[:50],
            "rid": str(resource_id or "")[:50],
            "d": (detail or "")[:2000],
        },
    )
    logger.info(
        "admin_activity action=%s admin_id=%s resource=%s:%s",
        action,
        admin_id,
        resource_type,
        resource_id,
    )


async def _count_admins(db: AsyncSession, *, active_only: bool = False) -> int:
    sql = "SELECT COUNT(*) FROM admins"
    if active_only:
        sql += " WHERE status = 'active'"
    row = (await db.execute(text(sql))).first()
    return int(row[0] if row else 0)


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
    words = ""
    if await _table_exists(db, "site_settings"):
        row = (
            await db.execute(text("SELECT setting_value FROM site_settings WHERE setting_key = 'sensitive_words'"))
        ).first()
        words = (row[0] if row else "") or ""
    return {"words": words, "security_runtime": build_security_runtime_payload()}


async def save_sensitive_words(db: AsyncSession, body: SensitiveWordsBody, actor_id: int = 0) -> dict:
    await upsert_site_setting(
        db,
        SiteSettingBody(setting_key="sensitive_words", setting_value=body.words, group_name="security"),
    )
    count = len([w for w in body.words.splitlines() if w.strip()])
    await write_activity_log(db, actor_id, "security.sensitive_words", "site_settings", "sensitive_words", f"count={count}")
    return {"saved": True, "count": count}


async def list_admin_users(db: AsyncSession, current_admin_id: int = 0) -> dict:
    rows = (
        await db.execute(text("SELECT id, username, email, display_name, role, status, last_login FROM admins ORDER BY id"))
    ).all()
    return {
        "current_admin_id": current_admin_id,
        "items": [
            {
                "id": int(r[0]),
                "username": r[1],
                "email": r[2] or "",
                "display_name": r[3] or "",
                "role": r[4],
                "status": r[5],
                "last_login": r[6].isoformat() if r[6] else None,
                "is_self": current_admin_id > 0 and int(r[0]) == current_admin_id,
            }
            for r in rows
        ]
    }


async def create_admin_user(db: AsyncSession, body: AdminUserBody, actor_id: int = 0) -> dict:
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
    new_id = int(row[0])
    await write_activity_log(db, actor_id, "admin.create", "admin", str(new_id), body.username.strip())
    logger.info("admin_user_created id=%s username=%s actor_id=%s", new_id, body.username, actor_id)
    return {"item": {"id": new_id, "username": body.username.strip()}}


async def list_api_tokens(db: AsyncSession) -> dict:
    from app.core.config import get_settings
    from app.core.security import ALL_SCOPES

    settings = get_settings()
    meta = {
        "available_scopes": list(ALL_SCOPES),
        "default_ttl_days": settings.api_token_default_ttl_days,
        "auth_header": "Authorization: Bearer <token>",
        "api_base_path": "/api/v1",
        "admin_cookie_name": (build_security_runtime_payload().get("admin_cookie_name") or "gf_token"),
        "security_runtime": build_security_runtime_payload(),
    }
    if not await _table_exists(db, "api_access_tokens"):
        return {"items": [], **meta}
    rows = (
        await db.execute(
            text(
                "SELECT id, name, token_prefix, scopes, expires_at, revoked_at, last_used_at FROM api_access_tokens ORDER BY id DESC LIMIT 50"
            )
        )
    ).all()
    return {
        **meta,
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
        ],
    }


async def create_api_token(db: AsyncSession, admin_id: int, body: ApiTokenBody) -> dict:
    from app.core.security import ALL_SCOPES, create_api_token as issue_api_token

    scopes = [s.strip() for s in body.scopes if str(s).strip()] or list(ALL_SCOPES)
    plain, row = await issue_api_token(
        db,
        admin_id,
        name=(body.name or "").strip() or "default",
        scopes=scopes,
        expires_days=body.expires_days,
    )
    await write_activity_log(db, admin_id, "api_token.create", "api_token", str(row.id), row.name)
    logger.info("api_token_created id=%s prefix=%s admin_id=%s", row.id, row.token_prefix, admin_id)
    return {
        "item": {
            "id": int(row.id),
            "token": plain,
            "token_prefix": row.token_prefix,
            "scopes": row.scopes or [],
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        }
    }


async def revoke_api_token(db: AsyncSession, token_id: int, actor_id: int = 0) -> dict:
    if not await _table_exists(db, "api_access_tokens"):
        raise HTTPException(status_code=503, detail="api_tokens_not_migrated")
    result = await db.execute(
        text("UPDATE api_access_tokens SET revoked_at = CURRENT_TIMESTAMP WHERE id = :id AND revoked_at IS NULL"),
        {"id": token_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="token_not_found")
    await write_activity_log(db, actor_id, "api_token.revoke", "api_token", str(token_id))
    logger.info("api_token_revoked id=%s actor_id=%s", token_id, actor_id)
    return {"revoked": True, "id": token_id}


async def update_admin_user(db: AsyncSession, admin_id: int, body: AdminUserUpdateBody, actor_id: int = 0) -> dict:
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
    await write_activity_log(db, actor_id, "admin.update", "admin", str(admin_id), body.display_name)
    logger.info("admin_user_updated id=%s actor_id=%s", admin_id, actor_id)
    return {"item": {"id": admin_id}}


async def toggle_admin_user(db: AsyncSession, admin_id: int, actor_id: int = 0) -> dict:
    row = (
        await db.execute(text("SELECT status FROM admins WHERE id = :id"), {"id": admin_id})
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="admin_not_found")
    new_status = "disabled" if row[0] == "active" else "active"
    if new_status == "disabled" and await _count_admins(db, active_only=True) <= 1:
        raise HTTPException(status_code=422, detail="cannot_disable_last_admin")
    await db.execute(text("UPDATE admins SET status = :s WHERE id = :id"), {"s": new_status, "id": admin_id})
    await write_activity_log(db, actor_id, "admin.toggle", "admin", str(admin_id), new_status)
    logger.info("admin_user_toggled id=%s status=%s actor_id=%s", admin_id, new_status, actor_id)
    return {"item": {"id": admin_id, "status": new_status}}


async def delete_admin_user(db: AsyncSession, admin_id: int, actor_id: int = 0) -> dict:
    if actor_id and admin_id == actor_id:
        raise HTTPException(status_code=422, detail="cannot_delete_self")
    if await _count_admins(db) <= 1:
        raise HTTPException(status_code=422, detail="cannot_delete_last_admin")
    result = await db.execute(text("DELETE FROM admins WHERE id = :id"), {"id": admin_id})
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="admin_not_found")
    await write_activity_log(db, actor_id, "admin.delete", "admin", str(admin_id))
    logger.info("admin_user_deleted id=%s actor_id=%s", admin_id, actor_id)
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
    await write_activity_log(db, admin_id, "security.password_change", "admin", str(admin_id))
    logger.info("admin_password_changed id=%s", admin_id)
    return {"changed": True}


async def list_activity_logs(db: AsyncSession) -> dict:
    if not await _table_exists(db, "admin_activity_logs"):
        return {"items": []}
    rows = (
        await db.execute(
            text(
                """
                SELECT l.id, l.admin_id, a.username, l.action, l.resource_type, l.resource_id, l.detail, l.created_at
                FROM admin_activity_logs l
                LEFT JOIN admins a ON a.id = l.admin_id
                ORDER BY l.id DESC
                LIMIT 100
                """
            )
        )
    ).all()
    return {
        "items": [
            {
                "id": int(r[0]),
                "admin_id": r[1],
                "username": r[2] or "",
                "action": r[3],
                "resource_type": r[4] or "",
                "resource_id": r[5] or "",
                "detail": r[6] or "",
                "created_at": r[7].isoformat() if r[7] else None,
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
