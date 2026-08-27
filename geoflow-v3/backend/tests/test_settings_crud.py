"""站点/安全/超管设置：Token 鉴权对齐、最后一个管理员保护、活动日志。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.admin.settings_crud_service import (
    ApiTokenBody,
    create_api_token,
    delete_admin_user,
    toggle_admin_user,
    write_activity_log,
)


@pytest.mark.asyncio
async def test_delete_self_rejected():
    db = AsyncMock()
    with pytest.raises(HTTPException) as ei:
        await delete_admin_user(db, 3, actor_id=3)
    assert ei.value.status_code == 422
    assert ei.value.detail == "cannot_delete_self"
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_delete_last_admin_rejected():
    db = AsyncMock()
    result = MagicMock()
    result.first = lambda: (1,)
    db.execute = AsyncMock(return_value=result)
    with pytest.raises(HTTPException) as ei:
        await delete_admin_user(db, 2, actor_id=1)
    assert ei.value.detail == "cannot_delete_last_admin"


@pytest.mark.asyncio
async def test_disable_last_active_admin_rejected():
    db = AsyncMock()
    status_row = MagicMock()
    status_row.first = lambda: ("active",)
    count_row = MagicMock()
    count_row.first = lambda: (1,)
    db.execute = AsyncMock(side_effect=[status_row, count_row])
    with pytest.raises(HTTPException) as ei:
        await toggle_admin_user(db, 1, actor_id=1)
    assert ei.value.detail == "cannot_disable_last_admin"


@pytest.mark.asyncio
async def test_create_api_token_delegates_to_security():
    db = AsyncMock()
    fake_row = MagicMock()
    fake_row.id = 9
    fake_row.token_prefix = "gf_deadbeef12"
    fake_row.name = "cli"
    fake_row.scopes = ["articles:read"]
    fake_row.expires_at = None
    with patch("app.core.security.create_api_token", new=AsyncMock(return_value=("gf_plain_token", fake_row))) as mocked:
        with patch("app.services.admin.settings_crud_service.write_activity_log", new=AsyncMock()):
            result = await create_api_token(db, 1, ApiTokenBody(name="cli", scopes=["articles:read"], expires_days=30))
    assert result["item"]["token"] == "gf_plain_token"
    assert result["item"]["token_prefix"] == "gf_deadbeef12"
    mocked.assert_awaited()
    kwargs = mocked.await_args.kwargs
    assert kwargs["expires_days"] == 30
    assert kwargs["scopes"] == ["articles:read"]


@pytest.mark.asyncio
async def test_write_activity_log_noop_without_table():
    db = AsyncMock()
    with patch("app.services.admin.settings_crud_service._table_exists", new=AsyncMock(return_value=False)):
        await write_activity_log(db, 1, "admin.create")
    db.execute.assert_not_called()
