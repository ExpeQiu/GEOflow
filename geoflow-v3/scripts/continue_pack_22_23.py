#!/usr/bin/env python3
"""补 Theme#21 整包门禁并 sync-pack；#22/#23 软门禁生产+分发。"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

API = "http://127.0.0.1:18081"
GEOWEB = "http://127.0.0.1:3070"
PREFIX = {
    "concept": "concepts",
    "compare": "compare",
    "guide": "guides",
    "topic": "topics",
    "article": "articles",
}


def log(msg: str) -> None:
    print(f"[pack-22-23] {msg}", flush=True)


def req(method: str, path: str, token: str, body: dict | None = None, timeout: int = 120) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{API}{path}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        log(f"HTTP {exc.code} {path}: {raw[:500]}")
        raise


def http_code(url: str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return int(resp.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except Exception:
        return 0


def wiki_page(token: str, article_id: int) -> dict:
    data = req("GET", f"/api/admin/wiki/{article_id}", token)["data"]
    return data.get("page") or data.get("item") or data


def enrich_compare_guide(token: str, theme_id: int) -> int:
    theme = req("GET", f"/api/admin/themes/{theme_id}", token)["data"]
    arts = theme.get("articles") or []
    pages = []
    for a in arts:
        try:
            pages.append(wiki_page(token, int(a["id"])))
        except Exception as exc:  # noqa: BLE001
            log(f"WARN wiki_get {a.get('id')} {exc}")
    paths = []
    for p in pages:
        wtype = p.get("wiki_page_type") or "article"
        slug = p.get("slug") or ""
        if slug:
            paths.append(f"{PREFIX.get(wtype, 'articles')}/{slug}")
    patched = 0
    for p in pages:
        wtype = p.get("wiki_page_type") or ""
        if wtype not in ("compare", "guide"):
            continue
        aid = int(p["id"])
        own = f"{PREFIX.get(wtype, 'articles')}/{p.get('slug')}"
        related = [x for x in paths if x and x != own][:4]
        faq = p.get("faq") or []
        if len(faq) < 3:
            title = str(p.get("title") or "本页")
            query = str(p.get("target_query") or title)
            faq = [
                {"q": f"{query}最该先看哪三点？", "a": f"先看安全与质保、续航/能力边界、以及是否匹配你的使用场景。详见「{title}」。"},
                {"q": "和竞品对比时容易漏掉什么？", "a": "除参数外，还要看接管率、售后网点、冬季/雨天边界，以及官方口径是否可核验。"},
                {"q": "看完这一页下一步去哪？", "a": "回到主题枢纽页，再读概念定义与选购指南，避免只看单篇结论。"},
            ]
        body = {
            "title": p.get("title") or title,
            "slug": p.get("slug"),
            "wiki_page_type": wtype,
            "body": p.get("body") or p.get("content") or "（正文）",
            "domain": p.get("domain") or "",
            "quick_answer": p.get("quick_answer") or "",
            "core_takeaway": p.get("core_takeaway") or "",
            "target_query": p.get("target_query") or "",
            "related": related,
            "faq": faq[:6],
            "schema_type": p.get("schema_type") or "TechArticle",
            "geo_theme_id": str(theme_id),
            "tags": p.get("tags") or [],
        }
        req("PATCH", f"/api/admin/wiki/{aid}", token, body)
        patched += 1
        log(f"enriched article_id={aid} type={wtype} related={len(related)} faq={len(faq)}")
    return patched


def wait_articles(token: str, theme_id: int, want: int, timeout_s: int = 480) -> list[dict]:
    deadline = time.time() + timeout_s
    arts: list[dict] = []
    while time.time() < deadline:
        d = req("GET", f"/api/admin/themes/{theme_id}", token)["data"]
        arts = d.get("articles") or []
        log(f"wait theme={theme_id} n={len(arts)} status={d.get('status')}")
        if len(arts) >= want:
            return arts
        time.sleep(10)
    return arts


def produce_and_ship(token: str, theme_id: int) -> bool:
    req("PATCH", f"/api/admin/themes/{theme_id}", token, {"gate_mode": "soft"})
    produced = req("POST", f"/api/admin/themes/{theme_id}/start-produce", token, {})["data"]
    log(
        f"produce theme={theme_id} status={produced.get('theme', {}).get('status')} "
        f"enqueued={produced.get('enqueued')} remaining={produced.get('remaining')}"
    )
    arts = wait_articles(token, theme_id, want=4)
    ids = [int(a["id"]) for a in arts]
    pending = [int(a["id"]) for a in arts if a.get("eval_status") == "pending_eval"]
    if pending:
        req("POST", "/api/admin/strategy/simulator/batch-reevaluate", token, {"article_ids": pending})
        deadline = time.time() + 180
        while time.time() < deadline:
            d = req("GET", f"/api/admin/themes/{theme_id}", token)["data"]
            left = [a for a in (d.get("articles") or []) if a.get("eval_status") == "pending_eval"]
            log(f"eval theme={theme_id} pending={len(left)}")
            if not left:
                break
            time.sleep(8)
    gate = req("POST", f"/api/admin/themes/{theme_id}/refresh-gate", token, {})["data"]
    gs = gate.get("gate_summary") or {}
    log(f"gate theme={theme_id} status={gate.get('status')} pack_ok={gs.get('pack_gate_ok')}")
    pub_n = 0
    for aid in ids:
        art = req("POST", f"/api/admin/articles/{aid}/publish", token, {})["data"]
        st = (art.get("article") or art).get("status")
        if st == "published":
            pub_n += 1
    enrich_compare_guide(token, theme_id)
    try:
        pack = req("POST", f"/api/admin/wiki/packs/{theme_id}/sync-pack", token, {}, timeout=90)["data"]
        log(f"sync_pack theme={theme_id} ok={pack.get('ok_count')} fail={pack.get('fail_count')}")
    except Exception as exc:  # noqa: BLE001
        log(f"WARN sync_pack theme={theme_id} {exc}")
    live = 0
    d = req("GET", f"/api/admin/themes/{theme_id}", token)["data"]
    for a in d.get("articles") or []:
        wtype = a.get("wiki_page_type") or "article"
        slug = a.get("slug") or ""
        if not slug:
            try:
                p = wiki_page(token, int(a["id"]))
                slug = p.get("slug") or ""
                wtype = p.get("wiki_page_type") or wtype
            except Exception:
                continue
        url = f"{GEOWEB}/{PREFIX.get(wtype, 'articles')}/{slug}"
        code = http_code(url)
        live += int(code == 200)
        log(f"geoweb {code} {url}")
    log(f"ship theme={theme_id} published={pub_n} live={live} status={d.get('status')}")
    return pub_n >= 4 and live >= 3


def main() -> int:
    login = req("POST", "/api/v1/auth/admin-login", "", {"username": "admin", "password": "password"})
    token = login["data"]["access_token"]
    log("jwt_ok")

    n = enrich_compare_guide(token, 21)
    log(f"theme21 enriched={n}")
    pack = req("POST", "/api/admin/wiki/packs/21/sync-pack", token, {}, timeout=90)["data"]
    log(f"sync_pack21 ok={pack.get('ok_count')} fail={pack.get('fail_count')} dry={pack.get('dry_run')}")
    for url in (
        f"{GEOWEB}/compare/ai-compare-34",
        f"{GEOWEB}/guides/ai-guide-35",
    ):
        log(f"recheck {http_code(url)} {url}")

    ok22 = produce_and_ship(token, 22)
    ok23 = produce_and_ship(token, 23)
    funnel = req("GET", "/api/admin/themes/funnel", token)["data"]
    log(f"funnel {funnel.get('by_status')} blockers={funnel.get('blockers')}")
    if not ok22 or not ok23:
        log(f"FAIL ship 22={ok22} 23={ok23}")
        return 1
    log("OK pack_and_22_23")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        log(f"FAIL: {exc}")
        raise SystemExit(1)
