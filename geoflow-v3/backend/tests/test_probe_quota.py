"""PROBE-TRUTH M1：配额护栏单测。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.geoeval.probe_quota import check_probe_quota, commit_probe_usage


@pytest.mark.asyncio
async def test_check_probe_quota_unlimited_when_limit_zero():
    model = SimpleNamespace(id=1, daily_limit=0, used_today=99)
    db = MagicMock()
    with patch("app.services.geoeval.probe_quota.resolve_probe_model", AsyncMock(return_value=model)):
        ok, reason, mid = await check_probe_quota(db, platform="doubao", engine_hint="api")
    assert ok is True
    assert reason == ""
    assert mid == 1


@pytest.mark.asyncio
async def test_check_probe_quota_blocks_when_exceeded():
    model = SimpleNamespace(id=7, daily_limit=10, used_today=10)
    db = MagicMock()
    with patch("app.services.geoeval.probe_quota.resolve_probe_model", AsyncMock(return_value=model)):
        ok, reason, mid = await check_probe_quota(db, platform="deepseek", engine_hint="llm")
    assert ok is False
    assert reason == "daily_limit"
    assert mid == 7


@pytest.mark.asyncio
async def test_check_probe_quota_allows_without_model():
    db = MagicMock()
    with patch("app.services.geoeval.probe_quota.resolve_probe_model", AsyncMock(return_value=None)):
        ok, reason, mid = await check_probe_quota(db, platform="kimi", engine_hint="api")
    assert ok is True
    assert mid is None


@pytest.mark.asyncio
async def test_commit_probe_usage_calls_bump():
    db = MagicMock()
    with patch("app.services.geoeval.probe_quota.bump_ai_model_usage", AsyncMock()) as bump:
        await commit_probe_usage(db, 3)
        bump.assert_awaited_once_with(db, 3)
        await commit_probe_usage(db, None)
        assert bump.await_count == 1
