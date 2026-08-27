"""安全硬化：CORS、回调签名、敏感词、enc:v1、登录锁定。"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.api_key_crypto import decrypt_api_key, encrypt_api_key
from app.core.config import Settings
from app.core.login_guard import clear_failures, is_locked, record_failure
from app.core.sensitive_filter import find_hits
from app.main import app


@pytest.mark.asyncio
async def test_uploads_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/uploads/nope.txt")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_internal_callback_rejects_unsigned():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/internal/content-agent/callback",
            json={"request_id": "r1", "workflow_type": "content", "status": "success"},
        )
    # debug/allow_insecure 下可能放行签名；强制校验路径用非默认 secret + 无签名应 401
    # 本测试环境 CONTENT_AGENT_CALLBACK_SECRET=test-callback-secret，无签名 → 401
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_internal_callback_accepts_valid_hmac():
    secret = "test-callback-secret"
    body = b'{"request_id":"r-hmac","workflow_type":"content","status":"success","engine":"t","result":{},"error":null}'
    ts = datetime.now(UTC).isoformat()
    nonce = str(uuid.uuid4())
    body_hash = hashlib.sha256(body).hexdigest()
    path = "/internal/content-agent/callback"
    sig = hmac.new(secret.encode(), f"POST\n{path}\n{ts}\n{nonce}\n{body_hash}".encode(), hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-Content-Agent-Timestamp": ts,
        "X-Content-Agent-Nonce": nonce,
        "X-Content-Agent-Signature": sig,
    }
    with patch(
        "app.api.internal.content_agent.complete_from_callback",
        new=AsyncMock(return_value={"ok": True}),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/internal/content-agent/callback", content=body, headers=headers)
    assert res.status_code == 200
    assert res.json()["data"]["received"] is True


def test_encrypt_decrypt_roundtrip():
    cipher = encrypt_api_key("sk-test-key", "unit-test-secret-material-32b!")
    assert cipher.startswith("enc:v1:")
    assert decrypt_api_key(cipher, "unit-test-secret-material-32b!") == "sk-test-key"


def test_sensitive_hits():
    assert find_hits("吉利内部绝密参数", ["绝密", "口令"]) == ["绝密"]
    assert find_hits("普通文案", ["绝密"]) == []


def test_login_lockout():
    clear_failures("lockuser", "1.1.1.1")
    for _ in range(5):
        record_failure("lockuser", "1.1.1.1")
    locked, remaining = is_locked("lockuser", "1.1.1.1")
    assert locked is True
    assert remaining > 0
    clear_failures("lockuser", "1.1.1.1")


def test_insecure_jwt_rejected_when_enforced():
    s = Settings(debug=False, allow_insecure_jwt=False, jwt_secret="change-me-in-production")
    with pytest.raises(RuntimeError, match="insecure_jwt_secret"):
        s.assert_secure_startup()
