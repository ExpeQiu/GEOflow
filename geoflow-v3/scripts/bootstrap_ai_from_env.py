#!/usr/bin/env python3
"""从环境变量注册真实 AI 模型到 Admin（OpenAI 兼容）。

支持（优先级）：
  ENTERPRISE_AI_GATEWAY_API_KEY → 企业 AI Gateway Chat + Embedding
  LOBSTER_PROXY_TOKEN           → Eva Lobster 遗留（本地 dev）
  ZHIPU_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY → 供应商直连

用法：
  export ENTERPRISE_AI_GATEWAY_API_KEY=...
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
    vendor: str = "",
    connection_kind: str = "inherit",
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
        "vendor": vendor,
        "connection_kind": connection_kind,
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
    enterprise_key = os.getenv("ENTERPRISE_AI_GATEWAY_API_KEY", "").strip()
    enterprise_text_base = os.getenv(
        "ENTERPRISE_AI_TEXT_BASE_URL", "https://ai-gateway-office.zeekrlife.com/v1"
    ).strip()
    enterprise_chat_model = os.getenv("ENTERPRISE_AI_TEXT_MODEL", "gpt-4o").strip()
    enterprise_embed_model = os.getenv("ENTERPRISE_AI_EMBED_MODEL", "text-embedding-v3").strip()
    lobster_token = os.getenv("LOBSTER_PROXY_TOKEN", "").strip()
    zhipu = os.getenv("ZHIPU_API_KEY", "").strip()
    deepseek = os.getenv("DEEPSEEK_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    if enterprise_key:
        log("企业 AI Gateway Key 已配置，注册公司级模型（不写入厂商 Key）")
        registered.append(
            upsert_model(
                token,
                name="企业 Gateway Chat",
                model_id=enterprise_chat_model,
                model_type="chat",
                api_url=enterprise_text_base,
                api_key="",
                priority=3,
                vendor="enterprise",
                connection_kind="enterprise-gateway",
            )
        )
        registered.append(
            upsert_model(
                token,
                name="企业 Gateway Embedding",
                model_id=enterprise_embed_model,
                model_type="embedding",
                api_url=enterprise_text_base,
                api_key="",
                priority=3,
                vendor="enterprise",
                connection_kind="enterprise-gateway",
            )
        )

    if lobster_token and not enterprise_key:
        log("Lobster Token 已配置，注册企业网关模型（不写入厂商 Key）")
        registered.append(
            upsert_model(
                token,
                name="Lobster 智谱 Chat",
                model_id=os.getenv("ZHIPU_CHAT_MODEL", "glm-4-flash"),
                model_type="chat",
                api_url="https://open.bigmodel.cn/api/paas/v4",
                api_key="",
                priority=5,
                vendor="zhipu",
                connection_kind="lobster",
            )
        )
        registered.append(
            upsert_model(
                token,
                name="Lobster 智谱 Embedding",
                model_id=os.getenv("ZHIPU_EMBED_MODEL", "embedding-3"),
                model_type="embedding",
                api_url="https://open.bigmodel.cn/api/paas/v4",
                api_key="",
                priority=5,
                vendor="zhipu",
                connection_kind="lobster",
            )
        )
        registered.append(
            upsert_model(
                token,
                name="Lobster 通义 Chat",
                model_id=os.getenv("QWEN_CHAT_MODEL", "qwen-plus"),
                model_type="chat",
                api_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                api_key="",
                priority=8,
                vendor="qwen",
                connection_kind="lobster",
            )
        )

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
        log(
            "FAIL: 未发现可用凭证（ENTERPRISE_AI_GATEWAY_API_KEY / LOBSTER_PROXY_TOKEN / "
            "ZHIPU_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY）"
        )
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
    log("下一步：企业请确认 ENTERPRISE_AI_GATEWAY_API_KEY；.env.local 设 AI_MOCK_MODE=false 后重启 API + Worker")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        log(f"HTTP {exc.code}: {body[:500]}")
        raise SystemExit(1) from exc
