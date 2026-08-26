#!/usr/bin/env python3
"""生产 Embedding 全库重嵌：关 Mock 后遍历知识库排队 sync-chunks。

用法：
  AI_MOCK_MODE=false 重启 API/Worker 后：
  python scripts/reindex_all_knowledge.py

护栏：embedding-ready.mode=mock 时拒绝（避免用 SHA256 假向量覆盖生产库）。
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

API = os.getenv("API_URL", "http://127.0.0.1:18081")
USER = os.getenv("GEOFLOW_ADMIN_USER", "admin")
PASSWORD = os.getenv("GEOFLOW_ADMIN_PASSWORD", "password")


def log(msg: str) -> None:
    print(f"[reindex] {msg}", flush=True)


def req(method: str, path: str, token: str = "", body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{API}{path}", data=data, method=method, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as resp:
        return json.loads(resp.read())


def main() -> int:
    token = req("POST", "/api/v1/auth/admin-login", "", {"username": USER, "password": PASSWORD})["data"]["access_token"]
    ready = req("GET", "/api/admin/knowledge-bases/embedding-ready", token)["data"]
    log(f"embedding ready={ready.get('ready')} mode={ready.get('mode')} model={ready.get('model_id')}")
    if ready.get("mode") == "mock":
        log("FAIL: AI_MOCK_MODE=true，拒绝全库重嵌。请关 Mock 并配置 embedding 模型后再跑。")
        return 2
    if not ready.get("ready"):
        log(f"FAIL: embedding 未就绪 warning={ready.get('warning')}")
        return 2
    result = req("POST", "/api/admin/knowledge-bases/reindex-all", token, {})["data"]
    log(f"queued count={result.get('count')} ids={result.get('knowledge_base_ids')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
