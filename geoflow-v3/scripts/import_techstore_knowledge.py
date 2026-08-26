#!/usr/bin/env python3
"""从 Techstore 只读导入吉利知识库 + 技术 IP。

用法：
  python scripts/import_techstore_knowledge.py
  python scripts/import_techstore_knowledge.py --fixture
  python scripts/import_techstore_knowledge.py --dry-run

source=auto：配置了 TECHSTORE_DATABASE_URL 则 live，否则 fixture。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = os.getenv("API_URL", "http://127.0.0.1:18081")
USER = os.getenv("GEOFLOW_ADMIN_USER", "admin")
PASSWORD = os.getenv("GEOFLOW_ADMIN_PASSWORD", "password")


def log(msg: str) -> None:
    print(f"[techstore-import] {msg}", flush=True)


def req(method: str, path: str, token: str = "", body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(f"{API}{path}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        log(f"HTTP {exc.code} {path} {detail[:400]}")
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", action="store_true", help="强制仓内演示语料")
    parser.add_argument("--live", action="store_true", help="强制连 Techstore 库")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-sync", action="store_true", help="不排队切片")
    args = parser.parse_args()
    source = "fixture" if args.fixture else ("live" if args.live else "auto")

    token = req("POST", "/api/v1/auth/admin-login", "", {"username": USER, "password": PASSWORD})["data"]["access_token"]
    preview = req("GET", f"/api/admin/knowledge-bases/techstore-preview?source={source}", token)["data"]
    log(
        "preview source=%s connected=%s kbs=%s assets=%s counts=%s"
        % (
            preview.get("source"),
            preview.get("connected"),
            preview.get("kb_names"),
            preview.get("asset_count"),
            preview.get("counts"),
        )
    )
    result = req(
        "POST",
        "/api/admin/knowledge-bases/import-techstore",
        token,
        {"source": source, "sync_chunks": not args.no_sync, "dry_run": args.dry_run},
    )["data"]
    log(
        "done run_id=%s dry_run=%s kb=%s assets=%s queued=%s"
        % (
            result.get("run_id"),
            result.get("dry_run"),
            result.get("knowledge_bases") or result.get("kb_names"),
            result.get("tech_assets") or result.get("asset_count"),
            result.get("sync_queued"),
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
