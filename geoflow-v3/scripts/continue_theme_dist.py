#!/usr/bin/env python3
"""Theme #21 软门禁 → 发布 → GEOweb 分发 → 核对公开页。"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

API = "http://127.0.0.1:18081"
GEOWEB = "http://127.0.0.1:3070"
THEME_ID = 21
ARTICLE_IDS = [48, 51, 52, 53, 54]


def log(msg: str) -> None:
    print(f"[theme-dist] {msg}", flush=True)


def req(method: str, path: str, token: str, body: dict | None = None, timeout: int = 90, base: str = API) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{base}{path}",
        data=data,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        log(f"HTTP {exc.code} {path}: {raw[:500]}")
        raise


def http_code(url: str, timeout: int = 20) -> int:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return int(resp.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except Exception as exc:  # noqa: BLE001
        log(f"fetch_fail {url} {exc}")
        return 0


def main() -> int:
    login = req("POST", "/api/v1/auth/admin-login", "", {"username": "admin", "password": "password"})
    token = login["data"]["access_token"]
    log("jwt_ok")

    patched = req("PATCH", f"/api/admin/themes/{THEME_ID}", token, {"gate_mode": "soft"})["data"]
    theme = patched.get("theme") or patched
    log(f"patch gate_mode={theme.get('gate_mode')} status={theme.get('status')}")
    if theme.get("gate_mode") != "soft":
        log("FAIL gate_mode not soft")
        return 1

    gate = req("POST", f"/api/admin/themes/{THEME_ID}/refresh-gate", token, {})["data"]
    gs = gate.get("gate_summary") or {}
    log(
        f"gate status={gate.get('status')} pack_ok={gs.get('pack_gate_ok')} "
        f"passed={gs.get('passed_types')} required={gs.get('required_types')} eval={gs.get('by_eval_status')}"
    )
    if not gs.get("pack_gate_ok") or gate.get("status") not in ("gate_passed", "producing", "distributing", "published"):
        log("FAIL pack gate not ok after soft")
        return 1

    published_n = 0
    for aid in ARTICLE_IDS:
        data = req("POST", f"/api/admin/articles/{aid}/publish", token, {})["data"]
        art = data.get("article") or data
        st = art.get("status") or data.get("status")
        log(f"publish article_id={aid} status={st}")
        if st == "published":
            published_n += 1
    if published_n < 4:
        log(f"FAIL published_n={published_n}")
        return 1

    # 整包 sync（related 互链）
    try:
        pack = req("POST", f"/api/admin/wiki/packs/{THEME_ID}/sync-pack", token, {}, timeout=60)["data"]
        log(f"sync_pack ok_count={pack.get('ok_count')} fail={pack.get('fail_count')} dry={pack.get('dry_run')}")
    except Exception as exc:  # noqa: BLE001
        log(f"WARN sync_pack {exc}")

    deadline = time.time() + 90
    jobs = []
    while time.time() < deadline:
        time.sleep(4)
        rows = req("GET", f"/api/admin/themes/{THEME_ID}", token)["data"]
        arts = rows.get("articles") or []
        pub = sum(1 for a in arts if a.get("status") == "published")
        log(f"poll theme_status={rows.get('status')} published_articles={pub}/{len(arts)}")
        if pub >= 4:
            break

    # distribution jobs
    try:
        dist = req("GET", "/api/admin/operations/distribution", token).get("data") or {}
        items = dist.get("jobs") or dist.get("items") or dist.get("recent") or []
        log(f"distribution_panel keys={list(dist.keys())[:8]} n={len(items) if isinstance(items, list) else 'n/a'}")
    except Exception as exc:  # noqa: BLE001
        log(f"WARN distribution_panel {exc}")

    detail = req("GET", f"/api/admin/themes/{THEME_ID}", token)["data"]
    urls: list[str] = []
    for a in detail.get("articles") or []:
        meta = a.get("wiki_meta") or {}
        url = meta.get("geoweb_url") if isinstance(meta, dict) else None
        # get_theme 可能不返回 wiki_meta；走 articles 详情
        if not url:
            try:
                ad = req("GET", f"/api/admin/articles/{a['id']}", token)["data"]
                art = ad.get("article") or ad
                meta = art.get("wiki_meta") or {}
                url = meta.get("geoweb_url") if isinstance(meta, dict) else None
                slug = (meta.get("slug") if isinstance(meta, dict) else None) or art.get("slug")
                wtype = (meta.get("type") if isinstance(meta, dict) else None) or a.get("wiki_page_type")
                log(f"article {a['id']} status={art.get('status')} type={wtype} slug={slug} url={url}")
                if url:
                    urls.append(str(url))
            except Exception as exc:  # noqa: BLE001
                log(f"WARN article_detail {a['id']} {exc}")

    live = 0
    if not urls:
        # 回退：按 GEOweb 常见路由探测
        prefix = {
            "topic": "topics",
            "concept": "concepts",
            "compare": "compares",
            "guide": "guides",
            "article": "articles",
        }
        for a in detail.get("articles") or []:
            wtype = a.get("wiki_page_type") or "article"
            slug = a.get("slug") or ""
            if slug:
                urls.append(f"{GEOWEB}/{prefix.get(wtype, 'articles')}/{slug}")

    for url in urls:
        code = http_code(url)
        ok = code == 200
        live += int(ok)
        log(f"geoweb {code} {url} ok={ok}")

    funnel = req("GET", "/api/admin/themes/funnel", token)["data"]
    theme2 = req("GET", f"/api/admin/themes/{THEME_ID}", token)["data"]
    log(
        f"final theme_status={theme2.get('status')} live_pages={live}/{len(urls)} "
        f"funnel={funnel.get('by_status')} blockers={funnel.get('blockers')}"
    )

    admin_code = http_code("http://127.0.0.1:13001/production/themes")
    log(f"admin_themes_http={admin_code}")

    if live < 1:
        log("FAIL no live GEOweb page")
        return 1
    log("OK theme_dist")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        log(f"FAIL: {exc}")
        raise SystemExit(1)
