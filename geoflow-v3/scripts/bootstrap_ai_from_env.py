#!/usr/bin/env python3
"""从环境变量注册真实 AI 模型到 Admin（OpenAI 兼容）。

支持：
  ZHIPU_API_KEY      → 智谱 GLM Chat + Embedding
  DEEPSEEK_API_KEY   → DeepSeek Chat
  OPENAI_API_KEY     → OpenAI Chat (+ 可选 Embedding)

用法：
  export ZHIPU_API_KEY=...
  python3 scripts/bootstrap_ai_from_env.py
  # 然后 AI_MOCK_MODE=false 并重启 API/Worker
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = os.getenv("GEOFLOW_API", "http://127.0.0.1:18081")


def log(msg: str) -> None:
    print(f"[ai-bootstrap] {msg}", flush=True)


def req(method: str, path: str, token: str = "", body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{API}{path}", data=data, method=method, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as resp:
        return json.loads(resp.read())


def upsert_model(
    token: str,
    *,
    name: str,
    model_id: str,
    model_type: str,
    api_url: str,
    api_key: str,
    priority: int,
) -> int:
    items = req("GET", "/api/admin/ai-models", token)["data"]["items"]
    existing = next((m for m in items if m.get("name") == name and m.get("model_type") == model_type), None)
    body = {
        "name": name,
        "model_id": model_id,
        "model_type": model_type,
        "api_url": api_url,
        "api_key": api_key,
        "failover_priority": priority,
        "status": "active",
    }
    if existing:
        mid = int(existing["id"])
        req("PATCH", f"/api/admin/ai-models/{mid}", token, body)
        log(f"updated id={mid} {name} ({model_type})")
        return mid
    created = req("POST", "/api/admin/ai-models", token, body)["data"]["item"]
    mid = int(created["id"])
    log(f"created id={mid} {name} ({model_type})")
    return mid


def deactivate_mock(token: str) -> None:
    items = req("GET", "/api/admin/ai-models", token)["data"]["items"]
    for m in items:
        if "mock" in str(m.get("name", "")).lower() or str(m.get("model_id", "")).startswith("mock"):
            body = {
                "name": m["name"],
                "model_id": m["model_id"],
                "model_type": m.get("model_type") or "chat",
                "api_url": m.get("api_url") or "https://api.openai.com/v1",
                "api_key": "mock",
                "failover_priority": 999,
                "status": "inactive",
            }
            req("PATCH", f"/api/admin/ai-models/{m['id']}", token, body)
            log(f"deactivated mock id={m['id']} {m['name']}")


def test_model(token: str, model_id: int) -> dict:
    return req("POST", f"/api/admin/ai-models/{model_id}/test", token, {})["data"]


def main() -> int:
    login = req("POST", "/api/v1/auth/admin-login", "", {"username": "admin", "password": "password"})
    token = login["data"]["access_token"]
    log("JWT OK")

    registered: list[int] = []
    zhipu = os.getenv("ZHIPU_API_KEY", "").strip()
    deepseek = os.getenv("DEEPSEEK_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    if zhipu:
        registered.append(
            upsert_model(
                token,
                name="智谱 GLM-4-Flash",
                model_id=os.getenv("ZHIPU_CHAT_MODEL", "glm-4-flash"),
                model_type="chat",
                api_url=os.getenv("ZHIPU_API_BASE", "https://open.bigmodel.cn/api/paas/v4"),
                api_key=zhipu,
                priority=10,
            )
        )
        registered.append(
            upsert_model(
                token,
                name="智谱 Embedding-3",
                model_id=os.getenv("ZHIPU_EMBED_MODEL", "embedding-3"),
                model_type="embedding",
                api_url=os.getenv("ZHIPU_API_BASE", "https://open.bigmodel.cn/api/paas/v4"),
                api_key=zhipu,
                priority=10,
            )
        )
    if deepseek:
        registered.append(
            upsert_model(
                token,
                name="DeepSeek Chat",
                model_id=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                model_type="chat",
                api_url=os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com"),
                api_key=deepseek,
                priority=20,
            )
        )
    if openai_key:
        registered.append(
            upsert_model(
                token,
                name="OpenAI Chat",
                model_id=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
                model_type="chat",
                api_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                api_key=openai_key,
                priority=30,
            )
        )
        registered.append(
            upsert_model(
                token,
                name="OpenAI Embedding",
                model_id=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
                model_type="embedding",
                api_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                api_key=openai_key,
                priority=30,
            )
        )

    if not registered:
        log("FAIL: 未发现可用 Key（ZHIPU_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY）")
        return 1

    deactivate_mock(token)

    for mid in registered:
        result = test_model(token, mid)
        log(f"test id={mid} ok={result.get('ok')} mock={result.get('mock')} msg={result.get('message')}")

    items = req("GET", "/api/admin/ai-models", token)["data"]["items"]
    active = [m for m in items if m.get("status") == "active"]
    log(
        "active_models=%s chat=%s embed=%s"
        % (
            len(active),
            sum(1 for m in active if m.get("model_type") == "chat"),
            sum(1 for m in active if m.get("model_type") == "embedding"),
        )
    )
    log("下一步：.env.local 设 AI_MOCK_MODE=false 后重启 API + Worker")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        log(f"HTTP {exc.code}: {body[:500]}")
        raise SystemExit(1) from exc
