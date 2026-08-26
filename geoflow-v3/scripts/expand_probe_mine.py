#!/usr/bin/env python3
"""扩问题库 → A/B/C 探测 → 场景缺口主题挖掘验证。

断言：target_queries 为挖掘长尾，不得整集等于探针原文。
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

API = "http://127.0.0.1:18081"

NEW_QUESTIONS = [
    {
        "question_text": "吉利收购沃尔沃后质量口碑真的变好了吗？",
        "priority": 97,
        "query_type": "brand",
        "scene_id": 18,
        "competitor_brands": ["沃尔沃"],
    },
    {
        "question_text": "银河 E5 和宋 PLUS EV 怎么选续航和空间？",
        "priority": 94,
        "query_type": "product",
        "scene_id": 16,
        "competitor_brands": ["比亚迪"],
    },
    {
        "question_text": "银河 L7 高速 NOA 和理想 AD 比接管频率如何？",
        "priority": 91,
        "query_type": "product",
        "scene_id": 17,
        "competitor_brands": ["理想"],
    },
    {
        "question_text": "吉利银河星舰 7 适合带老人小孩长途吗？",
        "priority": 88,
        "query_type": "product",
        "scene_id": 16,
        "competitor_brands": [],
    },
    {
        "question_text": "极氪和银河分别适合什么人，会不会抢客？",
        "priority": 87,
        "query_type": "brand",
        "scene_id": 18,
        "competitor_brands": [],
    },
    {
        "question_text": "城市领航下雨天还能用吗，有哪些限制？",
        "priority": 86,
        "query_type": "product",
        "scene_id": 17,
        "competitor_brands": [],
    },
    {
        "question_text": "买银河会不会被当成低端吉利？",
        "priority": 85,
        "query_type": "brand",
        "scene_id": 18,
        "competitor_brands": [],
    },
    {
        "question_text": "吉利和长城坦克越野定位差在哪？",
        "priority": 84,
        "query_type": "competitor",
        "scene_id": 18,
        "competitor_brands": ["长城"],
    },
    {
        "question_text": "智驾保险和 NOA 责任划分该怎么问客服？",
        "priority": 83,
        "query_type": "product",
        "scene_id": 17,
        "competitor_brands": [],
    },
    {
        "question_text": "比亚迪刀片电池和吉利神盾谁更抗穿刺？",
        "priority": 82,
        "query_type": "competitor",
        "scene_id": 16,
        "competitor_brands": ["比亚迪"],
    },
]

TEMPLATES = [
    {
        "template_type": "competitor",
        "category": "家用纯电对比",
        "pattern": "{brand}和{competitor}在家用纯电上谁更适合家庭？",
        "scene_id": 16,
        "default_priority": 78,
        "status": "active",
    },
    {
        "template_type": "product",
        "category": "智驾边界",
        "pattern": "{product}城市领航边界怎么判断？",
        "scene_id": 17,
        "default_priority": 76,
        "status": "active",
    },
    {
        "template_type": "competitor",
        "category": "品牌口碑差",
        "pattern": "{brand}和{competitor}口碑差在哪？",
        "scene_id": 18,
        "default_priority": 77,
        "status": "active",
    },
]


def log(msg: str) -> None:
    print(f"[expand-probe-mine] {msg}", flush=True)


def req(method: str, path: str, token: str, body: dict | None = None, timeout: int = 60) -> dict:
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
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        log(f"HTTP {exc.code} {path}: {raw[:500]}")
        raise


def wait_run(token: str, *, after_id: int, prefix: str, timeout_s: int = 300) -> dict:
    deadline = time.time() + timeout_s
    last = {}
    while time.time() < deadline:
        data = req("GET", "/api/admin/strategy/monitor/runs", token).get("data") or {}
        items = data.get("items") or data.get("runs") or []
        for it in items:
            rid = int(it.get("id") or 0)
            plat = str(it.get("platform") or "")
            status = str(it.get("status") or "")
            if rid > after_id and plat.startswith(prefix):
                last = it
                if status in ("completed", "failed", "error"):
                    return it
        time.sleep(4)
    return last


def mining_ok(theme: dict, gap: dict | None, label: str) -> bool:
    meta = theme.get("meta") or {}
    mining = meta.get("mining") or {}
    queries = list(theme.get("target_queries") or mining.get("longtail_queries") or [])
    evidence = mining.get("probe_evidence") or []
    probe_texts = {
        str(u.get("question_text") or "").strip()
        for u in (gap or {}).get("unsupported_sample") or evidence
        if (u.get("question_text") if isinstance(u, dict) else None)
    }
    if isinstance(evidence, list):
        for u in evidence:
            if isinstance(u, dict) and u.get("question_text"):
                probe_texts.add(str(u["question_text"]).strip())
    overlap_all = bool(probe_texts and queries and set(q.strip() for q in queries) <= probe_texts)
    ok = bool(queries) and not overlap_all
    log(
        f"{label} theme_id={theme.get('id')} status={theme.get('status')} "
        f"queries={len(queries)} digest={bool(mining.get('thinking_digest'))} "
        f"llm={mining.get('llm_enhanced')} unused={meta.get('unused_dims') or mining.get('unused_dims')} "
        f"overlap_all={overlap_all} ok={ok}"
    )
    if queries:
        log(f"{label} sample_queries={queries[:3]}")
    return ok


def main() -> int:
    login = req("POST", "/api/v1/auth/admin-login", "", {"username": "admin", "password": "password"})
    token = login["data"]["access_token"]
    log("jwt_ok")

    bulk = req(
        "POST",
        "/api/admin/strategy/monitor/questions/bulk",
        token,
        {"items": NEW_QUESTIONS, "skip_duplicates": True},
    )["data"]
    log(f"bulk created={bulk.get('created')} skipped={bulk.get('skipped')} errors={bulk.get('errors')}")

    tpl_ids: list[int] = []
    for tpl in TEMPLATES:
        created = req("POST", "/api/admin/strategy/monitor/templates", token, tpl, timeout=30)
        item = (created.get("data") or {}).get("item") or {}
        tid = int(item.get("id") or 0)
        tpl_ids.append(tid)
        gen = req("POST", f"/api/admin/strategy/monitor/templates/{tid}/generate?limit=4", token, {})
        log(f"template_id={tid} generated={gen.get('data', {}).get('created')}")

    settings = req("GET", "/api/admin/strategy/monitor/settings", token)["data"]
    settings["monitor_scan_limit"] = 6
    saved = req("PATCH", "/api/admin/strategy/monitor/settings", token, settings)["data"]
    log(f"scan_limit={saved.get('monitor_scan_limit')} platforms={saved.get('monitor_platforms')} mock={saved.get('ai_mock_mode')}")

    runs_before = req("GET", "/api/admin/strategy/monitor/runs", token).get("data") or {}
    items_before = runs_before.get("items") or runs_before.get("runs") or []
    max_id = max((int(it.get("id") or 0) for it in items_before), default=0)
    log(f"runs_max_id={max_id}")

    req("POST", "/api/admin/strategy/monitor/scan?scan_type=daily", token, {})
    daily = wait_run(token, after_id=max_id, prefix="", timeout_s=360)
    # daily platform often "deepseek" without scheme prefix
    log(f"daily_run id={daily.get('id')} status={daily.get('status')} plat={daily.get('platform')} probes={daily.get('probe_count')}")

    fw_results = []
    for sid in (16, 17, 18):
        r = req(
            "POST",
            "/api/admin/strategy/framework/scan",
            token,
            {"platforms": ["deepseek"], "limit": 1, "min_priority": 80, "scene_id": sid, "sync": True},
            timeout=180,
        )["data"]
        fw_results.append(r)
        log(f"framework scene={sid} run_id={r.get('run_id')} probes={r.get('probes')} raw_cot={r.get('raw_cot')}")

    cite_results = []
    for sid in (16, 17, 18):
        r = req(
            "POST",
            "/api/admin/strategy/citation/scan",
            token,
            {"platforms": ["deepseek"], "limit": 1, "min_priority": 80, "scene_id": sid, "sync": True},
            timeout=180,
        )["data"]
        cite_results.append(r)
        log(f"citation scene={sid} run_id={r.get('run_id')} probes={r.get('probes')} with_b={r.get('with_b')}")

    mine_ok = 0
    for sid in (16, 17, 18):
        gap = req("POST", f"/api/admin/strategy/monitor/scenes/{sid}/compute-gap", token, {})["data"]
        log(
            f"gap scene={sid} status={gap.get('status')} gap_rate={gap.get('gap_rate')} "
            f"priority={gap.get('gap_priority')} unsupported={len(gap.get('unsupported_sample') or [])}"
        )
        draft = req("POST", f"/api/admin/themes/from-scene/{sid}", token, {}, timeout=90)
        theme = (draft.get("data") or {}).get("theme") or {}
        if mining_ok(theme, gap, f"from_scene_{sid}"):
            mine_ok += 1

    cross = req("GET", "/api/admin/strategy/cross-track?limit=40", token)["data"]
    spawn_item = None
    for it in cross.get("items") or []:
        if it.get("unused_dims"):
            spawn_item = it
            break
    if not spawn_item and (cross.get("items") or []):
        spawn_item = cross["items"][0]
    spawn_ok = False
    if spawn_item:
        spawned = req(
            "POST",
            "/api/admin/strategy/cross-track/spawn-theme",
            token,
            {
                "question_id": spawn_item.get("question_id"),
                "flags": spawn_item.get("flags") or [],
                "unused_dims": spawn_item.get("unused_dims") or [],
            },
            timeout=90,
        )["data"]
        st = spawned.get("theme") or {}
        spawn_ok = mining_ok(st, None, "spawn_cross")
        log(f"spawn question_id={spawn_item.get('question_id')} flags={spawn_item.get('flags')}")

    qs = req("GET", "/api/admin/strategy/monitor/questions?page_size=50&status=active", token)["data"]
    log(f"questions_active={qs.get('total')} mine_ok={mine_ok}/3 spawn_ok={spawn_ok}")

    if mine_ok < 3:
        log("FAIL: from-scene mining not ok for all scenes")
        return 1
    log("OK expand_probe_mine")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        log(f"FAIL: {exc}")
        raise SystemExit(1)
