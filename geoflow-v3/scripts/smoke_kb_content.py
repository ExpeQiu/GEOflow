#!/usr/bin/env python3
"""小闭环验收：知识库入库 → RAG 召回 → 绑 Task 生成 → 正文含证据 → GEO 评估可过。

DoD:
  1. 知识库含唯一事实标记 FACT_MARKER
  2. sync-chunks 后 RAG sandbox 命中该标记
  3. Task 绑定该 KB 并产出文章
  4. 文章正文包含 FACT_MARKER（证明证据注入）
  5. eval_status ∈ {passed, advisory, pending→终态 passed/advisory}
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

API = "http://127.0.0.1:18081"
FACT_MARKER = "GEOFLOW_KB_FACT_ALPHA_7741"
FACT_SNIPPET = (
    f"技术参数 SSOT：峰值扭矩标定值为 420N·m（验证标记 {FACT_MARKER}）。"
    "该数值仅出现在本知识库，用于校验 RAG 是否进入正文。"
)


def log(msg: str) -> None:
    print(f"[kb-smoke] {msg}", flush=True)


def req(method: str, path: str, token: str, body: dict | None = None, timeout: int = 60) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{API}{path}", data=data, method=method, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        return json.loads(resp.read())


def wait_chunks(token: str, kb_id: int, tries: int = 40) -> dict:
    for i in range(1, tries + 1):
        detail = req("GET", f"/api/admin/knowledge-bases/{kb_id}/detail", token)["data"]
        chunks = detail.get("chunks") or []
        log(f"sync poll {i}: chunks={len(chunks)}")
        if chunks:
            return detail
        time.sleep(2)
        if i in {5, 15, 25}:
            req("POST", f"/api/admin/knowledge-bases/{kb_id}/sync-chunks", token, {})
            log("re-queued sync-chunks")
    raise RuntimeError("knowledge_chunks_timeout — 请确认 Celery worker 在跑（scripts/run-worker.sh）")


def main() -> int:
    login = req("POST", "/api/v1/auth/admin-login", "", {"username": "admin", "password": "password"})
    token = login["data"]["access_token"]
    log("JWT OK")

    kb = req(
        "POST",
        "/api/admin/knowledge-bases/create",
        token,
        {
            "name": f"KB Smoke {int(time.time())}",
            "description": "小闭环：知识库→合格内容",
            "content": (
                "# 验证用技术资料\n\n"
                f"{FACT_SNIPPET}\n\n"
                "补充说明：请在生成内容中忠实引用上述扭矩标定，不得臆造其它数值。"
            ),
        },
    )["data"]["item"]
    kb_id = int(kb["id"])
    log(f"kb created id={kb_id} sync_queued={kb.get('sync_queued')}")

    detail = wait_chunks(token, kb_id)
    preview = " | ".join((c.get("preview") or "")[:40] for c in detail["chunks"][:3])
    log(f"chunks ready preview={preview}")

    sandbox = req(
        "POST",
        "/api/admin/knowledge-bases/rag-sandbox",
        token,
        {"knowledge_base_id": kb_id, "query": FACT_MARKER, "limit": 5},
    )["data"]
    hits = sandbox.get("hits") or []
    hit_text = "\n".join(str(h.get("content") or "") for h in hits)
    if FACT_MARKER not in hit_text:
        log(f"FAIL: RAG 未召回标记 hits={len(hits)}")
        return 1
    top = hits[0] if hits else {}
    if top.get("source") == "fallback":
        log("WARN: 仅 fallback 召回（关键词未命中），继续生成验收")
    log(f"RAG OK hits={len(hits)} source={top.get('source')} score={top.get('score')}")

    opts = req("GET", "/api/admin/tasks/form-options", token)["data"]
    prompts = opts.get("prompts") or []
    models = opts.get("ai_models") or []
    if not prompts or not models:
        log("FAIL: 缺少 prompt 或 ai_model")
        return 1

    title_libs = opts.get("title_libraries") or []
    if not title_libs or (title_libs[0].get("count") or 0) <= 0:
        lib = req("POST", "/api/admin/materials/title-libraries", token, {"name": "KB Smoke 标题库"})["data"]["item"]
        title_lib_id = int(lib["id"])
        req(
            "POST",
            f"/api/admin/materials/title-libraries/{title_lib_id}/titles/bulk",
            token,
            {"titles": [f"峰值扭矩标定解读（含 {FACT_MARKER}）", "技术参数 SSOT 说明"]},
        )
    else:
        title_lib_id = int(title_libs[0]["id"])

    task = req(
        "POST",
        "/api/admin/tasks",
        token,
        {
            "task_name": f"KB Content Smoke {int(time.time())}",
            "title_library_id": title_lib_id,
            "prompt_id": int(prompts[0]["id"]),
            "ai_model_id": int(models[0]["id"]),
            "knowledge_base_id": kb_id,
            "status": "active",
            "article_limit": 3,
            "draft_limit": 3,
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
        },
    )["data"]["task"]
    task_id = int(task["id"])
    log(f"task created id={task_id} kb={kb_id}")

    enq = req("POST", f"/api/admin/tasks/{task_id}/enqueue", token)["data"]
    run = enq.get("job") or enq.get("run") or enq
    log(f"enqueued run_id={run.get('id')}")

    article = None
    final_status = "pending"
    for i in range(1, 41):
        time.sleep(3)
        panel = req("GET", "/api/admin/tasks", token)["data"]["tasks"]
        row = next((t for t in panel if int(t["id"]) == task_id), None)
        if not row:
            continue
        final_status = row.get("batch_status") or "pending"
        err = row.get("batch_error_message") or ""
        log(f"poll {i}: status={final_status} created={row.get('created_count')} err={err[:80]}")
        if final_status in {"completed", "failed", "cancelled"}:
            break

    articles = req("GET", "/api/admin/articles", token)["data"]["articles"]
    matched = [a for a in articles if a.get("task_id") == task_id]
    if final_status == "failed":
        log("FAIL: task run failed")
        return 1
    if not matched:
        log("FAIL: 无文章产出（Worker 未跑或超时）")
        return 1

    article = req("GET", f"/api/admin/articles/{matched[0]['id']}", token)["data"]["article"]
    content = str(article.get("content") or "")
    eval_status = str(article.get("eval_status") or "pending")
    log(f"article id={article['id']} eval={eval_status} content_len={len(content)}")

    if FACT_MARKER not in content:
        log("FAIL: 正文未包含知识库事实标记 — RAG 未注入或 mock 未写入证据")
        log(f"content_head={content[:240]!r}")
        return 1
    log("evidence_in_content OK")

    # 评估可能异步；最多再等一轮
    for i in range(1, 21):
        if eval_status in {"passed", "advisory", "failed", "skipped"}:
            break
        time.sleep(2)
        article = req("GET", f"/api/admin/articles/{matched[0]['id']}", token)["data"]["article"]
        eval_status = str(article.get("eval_status") or "pending")
        log(f"eval poll {i}: {eval_status}")

    if eval_status == "pending":
        # 主动触发重评
        try:
            req("POST", f"/api/admin/strategy/geo-eval/reevaluate/{article['id']}", token, {})
            log("reevaluate queued")
        except urllib.error.HTTPError as exc:
            log(f"reevaluate HTTP {exc.code}")
        for i in range(1, 16):
            time.sleep(2)
            article = req("GET", f"/api/admin/articles/{matched[0]['id']}", token)["data"]["article"]
            eval_status = str(article.get("eval_status") or "pending")
            log(f"eval poll2 {i}: {eval_status}")
            if eval_status in {"passed", "advisory", "failed", "skipped"}:
                break

    if eval_status not in {"passed", "advisory", "skipped"}:
        log(f"FAIL: eval_status={eval_status}（期望 passed/advisory/skipped）")
        return 1

    log(
        "SMOKE PASSED "
        f"kb_id={kb_id} article_id={article['id']} eval={eval_status} "
        f"marker={FACT_MARKER}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        log(f"HTTP {exc.code}: {body[:600]}")
        raise SystemExit(1) from exc
    except Exception as exc:  # noqa: BLE001
        log(f"FAIL: {exc}")
        raise SystemExit(1) from exc
