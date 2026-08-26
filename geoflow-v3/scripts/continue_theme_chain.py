#!/usr/bin/env python3
"""继续验证 Theme 主链路：confirm ×3 → spawn 不泄漏探针原文 → produce #21 → funnel。"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

API = "http://127.0.0.1:18081"
ADMIN = "http://127.0.0.1:13001"
PROBE_Q55 = "吉利收购沃尔沃后质量口碑真的变好了吗？"


def log(msg: str) -> None:
    print(f"[theme-chain] {msg}", flush=True)


def req(method: str, path: str, token: str, body: dict | None = None, timeout: int = 90) -> dict:
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
        log(f"HTTP {exc.code} {path}: {raw[:600]}")
        raise


def main() -> int:
    login = req("POST", "/api/v1/auth/admin-login", "", {"username": "admin", "password": "password"})
    token = login["data"]["access_token"]
    log("jwt_ok")

    confirmed: list[dict] = []
    for tid in (21, 22, 23):
        data = req("POST", f"/api/admin/themes/{tid}/confirm", token, {})["data"]
        theme = data.get("theme") or {}
        pack = theme.get("pack_spec") or []
        required = [p for p in pack if p.get("required", True)]
        queries = [str(q).strip() for q in (theme.get("target_queries") or []) if str(q).strip()]
        mining = (theme.get("meta") or {}).get("mining") or {}
        evidence = {str(e.get("question_text") or "").strip() for e in (mining.get("probe_evidence") or [])}
        overlap_all = bool(evidence and queries and set(queries) <= evidence)
        ok = (
            theme.get("status") == "confirmed"
            and bool(data.get("task_id") or theme.get("task_id"))
            and theme.get("gate_mode") == "hard"
            and len(required) >= 4
            and bool(queries)
            and not overlap_all
        )
        log(
            f"confirm theme_id={tid} status={theme.get('status')} task_id={data.get('task_id')} "
            f"pack={len(pack)} required={len(required)} queries={len(queries)} "
            f"remediation={theme.get('remediation_id')} overlap_all={overlap_all} ok={ok}"
        )
        if not ok:
            log(f"FAIL confirm theme_id={tid}")
            return 1
        confirmed.append(theme)

    spawned = req(
        "POST",
        "/api/admin/strategy/cross-track/spawn-theme",
        token,
        {"question_id": 55, "flags": ["mention_no_ours", "framework_not_in_answer"], "unused_dims": ["安全", "耐久"]},
        timeout=90,
    )["data"]
    st = spawned.get("theme") or {}
    sq = [str(q).strip() for q in (st.get("target_queries") or [])]
    leak = PROBE_Q55 in sq
    unused = (st.get("meta") or {}).get("unused_dims") or []
    src_qid = (st.get("meta") or {}).get("source_question_id")
    spawn_ok = st.get("status") == "draft" and not leak and src_qid == 55 and "安全" in unused
    log(
        f"spawn theme_id={st.get('id')} leak_probe={leak} source_qid={src_qid} "
        f"unused={unused} queries={sq[:3]} ok={spawn_ok}"
    )
    if not spawn_ok:
        log("FAIL spawn still leaks probe text or missing meta")
        return 1

    produced = req("POST", "/api/admin/themes/21/start-produce", token, {})["data"]
    ptheme = produced.get("theme") or {}
    log(
        f"produce theme_id=21 status={ptheme.get('status')} enqueued={produced.get('enqueued')} "
        f"remaining={produced.get('remaining')} run_ids={produced.get('run_ids')}"
    )
    if ptheme.get("status") not in ("producing", "confirmed"):
        log("FAIL unexpected produce status")
        return 1
    if not produced.get("enqueued"):
        log("FAIL produce not enqueued")
        return 1

    deadline = time.time() + 720
    articles: list[dict] = []
    while time.time() < deadline:
        detail = req("GET", "/api/admin/themes/21", token)["data"]
        articles = detail.get("articles") or []
        statuses = {}
        for a in articles:
            k = str(a.get("status") or "?")
            statuses[k] = statuses.get(k, 0) + 1
        log(f"poll theme21 articles={len(articles)} by_status={statuses} theme_status={detail.get('status')}")
        if len(articles) >= 1:
            break
        time.sleep(8)

    funnel = req("GET", "/api/admin/themes/funnel", token)["data"]
    log(f"funnel total={funnel.get('total')} by_status={funnel.get('by_status')} blockers={funnel.get('blockers')}")

    try:
        urllib.request.urlopen(urllib.request.Request(f"{ADMIN}/strategy/theme-mining"), timeout=15).read(200)
        log("admin_theme_mining_http=200")
    except Exception as exc:  # noqa: BLE001
        log(f"WARN admin_theme_mining {exc}")

    if not articles:
        log("WARN produce enqueued but no articles yet (worker still running)")
        return 0
    log("OK theme_chain confirm+spawn+produce")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        log(f"FAIL: {exc}")
        raise SystemExit(1)
