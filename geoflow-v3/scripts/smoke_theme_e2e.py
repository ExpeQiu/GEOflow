#!/usr/bin/env python3
"""Theme E2E：登录 → 建场景(可选) → from-scene 草稿 → confirm → start-produce → 查 funnel。

依赖本地 API http://127.0.0.1:18081 与已 seed 的素材/模型。
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

API = "http://127.0.0.1:18081"


def log(msg: str) -> None:
    print(f"[theme-e2e] {msg}", flush=True)


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
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        log(f"HTTP {exc.code} {path}: {raw[:400]}")
        raise


def main() -> int:
    login = req("POST", "/api/v1/auth/admin-login", "", {"username": "admin", "password": "password"})
    token = login["data"]["access_token"]
    log("JWT OK")

    # 尽量复用已有场景，否则创建一个最小场景
    scenes = req("GET", "/api/admin/strategy/monitor/scenes", token).get("data") or {}
    items = scenes.get("items") or scenes.get("scenes") or []
    scene_id = None
    if items:
        scene_id = int(items[0].get("id") or items[0].get("scene_id"))
        log(f"reuse scene_id={scene_id}")
    else:
        created = req(
            "POST",
            "/api/admin/strategy/monitor/scenes",
            token,
            {
                "persona": "购车用户",
                "scene_name": f"Theme E2E {int(time.time())}",
                "intent": "决策对比",
                "weight_pct": 10,
            },
        )
        scene_id = int(created["data"].get("id") or created["data"].get("item", {}).get("id"))
        log(f"created scene_id={scene_id}")

    draft = req("POST", f"/api/admin/themes/from-scene/{scene_id}", token, {})
    theme = draft["data"]["theme"]
    theme_id = int(theme["id"])
    mining = draft["data"].get("mining") or (theme.get("meta") or {}).get("mining") or {}
    unsupported = (draft["data"].get("gap") or {}).get("unsupported_sample") or []
    target_queries = theme.get("target_queries") or []
    log(
        f"theme_draft theme_id={theme_id} status={theme.get('status')} "
        f"queries={len(target_queries)} gate={theme.get('gate_mode')} mining_keys={list(mining.keys())}"
    )

    if theme.get("status") != "draft":
        log("FAIL: expected draft status")
        return 1
    if theme.get("gate_mode") != "hard":
        log("FAIL: expected gate_mode=hard for gap theme")
        return 1
    if not mining or not mining.get("longtail_queries"):
        # meta may only be on theme after flush
        meta_mining = (theme.get("meta") or {}).get("mining") or {}
        if not meta_mining.get("longtail_queries") and not mining.get("longtail_queries"):
            log("FAIL: missing meta.mining.longtail_queries")
            return 1
        mining = mining or meta_mining
    probe_texts = {str(u.get("question_text") or "").strip() for u in unsupported if u.get("question_text")}
    overlap = [q for q in target_queries if str(q).strip() in probe_texts]
    if probe_texts and overlap and set(target_queries) <= probe_texts:
        log(f"FAIL: target_queries still equals probe evidence set: {overlap}")
        return 1
    log(f"mining_ok longtails={len(mining.get('longtail_queries') or [])} evidence={len(mining.get('probe_evidence') or [])}")

    try:
        confirmed = req("POST", f"/api/admin/themes/{theme_id}/confirm", token, {})
    except urllib.error.HTTPError:
        log("confirm failed — 检查 GEOweb 渠道 / prompt / 模型 / 分类是否就绪")
        return 1

    theme2 = confirmed["data"]["theme"]
    task_id = confirmed["data"].get("task_id") or theme2.get("task_id")
    log(
        f"theme_confirmed theme_id={theme_id} task_id={task_id} "
        f"channels={confirmed['data'].get('distribution_channel_ids')} "
        f"remediation_id={theme2.get('remediation_id')}"
    )
    if theme2.get("status") != "confirmed":
        log("FAIL: expected confirmed")
        return 1
    if not task_id:
        log("FAIL: missing task_id")
        return 1

    started = req("POST", f"/api/admin/themes/{theme_id}/start-produce", token, {})
    log(f"produce_started status={started['data']['theme'].get('status')}")

    funnel = req("GET", "/api/admin/themes/funnel", token)["data"]
    log(f"funnel total={funnel.get('total')} by_status={funnel.get('by_status')} blockers={funnel.get('blockers')}")

    detail = req("GET", f"/api/admin/themes/{theme_id}", token)["data"]
    log(
        f"detail theme_id={theme_id} status={detail.get('status')} "
        f"pack={len(detail.get('pack_spec') or [])} articles={len(detail.get('articles') or [])}"
    )

    log("OK theme_id=%s task_id=%s scene_id=%s" % (theme_id, task_id, scene_id))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        log(f"FAIL: {exc}")
        raise SystemExit(1)
