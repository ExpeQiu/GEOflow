#!/usr/bin/env python3
"""Smoke: 登录 → 准备素材 → 建任务 → 立即执行 → 检查文章产出。"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

API = "http://127.0.0.1:18081"


def log(msg: str) -> None:
    print(f"[smoke] {msg}", flush=True)


def req(method: str, path: str, token: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as resp:
        return json.loads(resp.read())


def main() -> int:
    login = req("POST", "/api/v1/auth/admin-login", "", {"username": "admin", "password": "password"})
    token = login["data"]["access_token"]
    log("JWT OK")

    opts = req("GET", "/api/admin/tasks/form-options", token)["data"]
    title_libs = opts.get("title_libraries") or []
    prompts = opts.get("prompts") or []
    models = opts.get("ai_models") or []
    if not prompts or not models:
        log("FAIL: 缺少 prompt 或 ai_model，请先 seed")
        return 1

    title_lib_id: int
    if not title_libs or (title_libs[0].get("count") or 0) <= 0:
        lib = req("POST", "/api/admin/materials/title-libraries", token, {"name": "Smoke 标题库"})["data"]["item"]
        title_lib_id = int(lib["id"])
        req(
            "POST",
            f"/api/admin/materials/title-libraries/{title_lib_id}/titles/bulk",
            token,
            {"titles": ["Smoke 测试：GEO 内容生产链路验证", "Smoke 测试：RAG 与 Worker 执行"]},
        )
        log(f"created title_library id={title_lib_id}")
    else:
        title_lib_id = int(title_libs[0]["id"])
        log(f"reuse title_library id={title_lib_id} count={title_libs[0].get('count')}")

    task_body = {
        "task_name": f"Smoke E2E {int(time.time())}",
        "title_library_id": title_lib_id,
        "prompt_id": int(prompts[0]["id"]),
        "ai_model_id": int(models[0]["id"]),
        "status": "active",
        "article_limit": 5,
        "draft_limit": 5,
        "publish_interval": 60,
        "category_mode": "smart",
        "model_selection_mode": "fixed",
        "content_pipeline_mode": "pipeline",
        "content_format": "article",
        "publish_scope": "local_only",
        "distribution_channel_ids": [],
        "need_review": False,
        "is_loop": False,
        "auto_keywords": True,
        "auto_description": True,
    }
    task = req("POST", "/api/admin/tasks", token, task_body)["data"]["task"]
    task_id = int(task["id"])
    log(f"task created id={task_id}")

    enq = req("POST", f"/api/admin/tasks/{task_id}/enqueue", token)["data"]
    run = enq.get("job") or enq.get("run") or enq
    run_id = run.get("id")
    log(f"enqueued run_id={run_id}")

    final_status = "pending"
    error_msg = ""
    created_count = 0
    for i in range(1, 31):
        time.sleep(3)
        panel = req("GET", "/api/admin/tasks", token)["data"]["tasks"]
        row = next((t for t in panel if int(t["id"]) == task_id), None)
        if not row:
            log(f"poll {i}: task not in list")
            continue
        final_status = row.get("batch_status") or "pending"
        error_msg = row.get("batch_error_message") or ""
        created_count = int(row.get("created_count") or 0)
        log(f"poll {i}: status={final_status} created={created_count} err={error_msg[:80]}")
        if final_status in {"completed", "failed", "cancelled"}:
            break

    articles = req("GET", "/api/admin/articles", token)["data"]["articles"]
    matched = [a for a in articles if a.get("task_id") == task_id]
    log(f"articles_for_task={len(matched)}")

    if final_status == "failed":
        log(f"FAIL: run failed — {error_msg}")
        return 1

    if not matched:
        log("FAIL: 无文章产出（Worker 可能未运行或执行超时）")
        return 1

    article = matched[0]
    detail = req("GET", f"/api/admin/articles/{article['id']}", token)["data"]["article"]
    checks = {
        "title": bool(detail.get("title")),
        "content": len(str(detail.get("content") or "")) > 50,
        "keywords": bool(detail.get("keywords")),
        "meta_description": bool(detail.get("meta_description")),
        "task_id": detail.get("task_id") == task_id,
    }
    log(f"article id={detail['id']} title={detail.get('title', '')[:60]}")
    log(f"keywords={str(detail.get('keywords', ''))[:100]}")
    log(f"meta={str(detail.get('meta_description', ''))[:80]}")
    log(f"content_len={len(str(detail.get('content') or ''))}")

    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        log(f"FAIL: 字段校验未通过 — {failed}")
        return 1

    log("SMOKE PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        log(f"HTTP {exc.code}: {body[:500]}")
        raise SystemExit(1) from exc
