"""主题挖掘：差距场景 → 思考链/信源/长尾 Query（监控题仅作证据）。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.admin.production_service import _table_exists

logger = logging.getLogger(__name__)

DECISION_SUFFIXES = [
    "怎么判断靠不靠谱",
    "和竞品比该看哪些点",
    "适合什么使用场景",
    "买车前要核实哪些参数",
    "AI 推荐时该信哪些口径",
]


def _domain(url: str) -> str:
    try:
        host = urlparse(url).netloc or ""
        return host.replace("www.", "") if host else ""
    except Exception:
        return ""


def _normalize_q(q: str) -> str:
    return re.sub(r"\s+", "", (q or "").strip().lower())


def _rewrite_longtail(
    *,
    persona: str,
    scene_name: str,
    intent: str,
    probe_texts: list[str],
) -> list[str]:
    """规则层：场景决策型长尾问法，避免与探针原文完全相同。"""
    base = scene_name or intent or "技术决策"
    intent_bit = intent or "选型对比"
    persona_bit = persona or "用户"
    seeds: list[str] = []

    # 战役级长尾（不照搬探针）
    seeds.append(f"{persona_bit}在「{base}」场景下，{intent_bit}时{DECISION_SUFFIXES[0]}？")
    seeds.append(f"面对{base}相关决策，{DECISION_SUFFIXES[1]}？")
    seeds.append(f"{base}能力边界与适用人群：{DECISION_SUFFIXES[2]}？")

    # 由探针证据改写（加决策框架，保证 ≠ 原文）
    for i, raw in enumerate(probe_texts[:3]):
        raw = (raw or "").strip()
        if not raw:
            continue
        # 去掉尾问号后套场景框架
        core = re.sub(r"[？?]+$", "", raw)
        suffix = DECISION_SUFFIXES[(i + 2) % len(DECISION_SUFFIXES)]
        rewritten = f"在{base}场景，关于「{core[:40]}」：{suffix}？"
        if _normalize_q(rewritten) != _normalize_q(raw):
            seeds.append(rewritten)

    # 去重保序，至少 3 条
    out: list[str] = []
    seen: set[str] = set()
    for q in seeds:
        key = _normalize_q(q)
        if not key or key in seen:
            continue
        # 禁止与任一探针原文完全相同
        if any(_normalize_q(p) == key for p in probe_texts):
            continue
        seen.add(key)
        out.append(q[:200])
    while len(out) < 3:
        n = len(out)
        filler = f"{base}：用户选型时{DECISION_SUFFIXES[n % len(DECISION_SUFFIXES)]}？（战役补充 {n + 1}）"
        if _normalize_q(filler) not in seen:
            out.append(filler[:200])
            seen.add(_normalize_q(filler))
        else:
            break
    return out[:8]


def _keyword_combos(scene_name: str, intent: str, probe_texts: list[str], keywords: list[str]) -> list[str]:
    combos: list[str] = []
    if scene_name and intent:
        combos.append(f"{scene_name}+{intent}")
    for kw in keywords[:6]:
        k = str(kw).strip()
        if k and scene_name:
            combos.append(f"{scene_name}+{k}")
    # 从探针题抽 2–4 字中文片段
    for t in probe_texts[:3]:
        parts = re.findall(r"[\u4e00-\u9fff]{2,6}", t or "")
        for p in parts[:2]:
            if intent:
                combos.append(f"{p}+{intent}")
    # 去重
    seen: set[str] = set()
    out: list[str] = []
    for c in combos:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out[:12]


def _digest_thinking(texts: list[str]) -> str:
    if not texts:
        return "暂无框架样本；请先跑 framework_api 扫描采集明文思维链。"
    chunks: list[str] = []
    for t in texts:
        t = (t or "").strip()
        if not t:
            continue
        # 取前几句作摘要
        lines = [ln.strip() for ln in re.split(r"[\n。；;]", t) if ln.strip()]
        chunks.extend(lines[:4])
    if not chunks:
        return "暂无框架样本；请先跑 framework_api 扫描采集明文思维链。"
    # 去重截断
    seen: set[str] = set()
    uniq: list[str] = []
    for c in chunks:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return "；".join(uniq[:8])[:800]


async def _load_scene_probe_context(db: AsyncSession, scene_id: int) -> dict[str, Any]:
    """同场景问题 → 仅 raw 思维链 / keywords / citations。禁止 snippet 冒充 A 轨。"""
    thinking_texts: list[str] = []
    keywords: list[str] = []
    source_hints: list[dict[str, str]] = []
    frameworks: list[dict[str, Any]] = []
    if not await _table_exists(db, "geo_monitor_questions"):
        return {"thinking_texts": [], "keywords": [], "source_hints": [], "frameworks": []}

    qids = (
        await db.execute(
            text(
                """
                SELECT id FROM geo_monitor_questions
                WHERE scene_id = :sid AND status = 'active'
                ORDER BY id ASC LIMIT 40
                """
            ),
            {"sid": scene_id},
        )
    ).all()
    question_ids = [int(r[0]) for r in qids]
    if not question_ids or not await _table_exists(db, "geo_monitor_probe_results"):
        return {"thinking_texts": thinking_texts, "keywords": keywords, "source_hints": source_hints, "frameworks": frameworks}

    id_list = ",".join(str(i) for i in question_ids)
    rows = []
    try:
        async with db.begin_nested():
            rows = (
                await db.execute(
                    text(
                        f"""
                    SELECT id, thinking_text, keywords, source_hosts, reasoning_grade, scheme, framework
                    FROM geo_monitor_probe_results
                    WHERE question_id IN ({id_list})
                    ORDER BY id DESC
                    LIMIT 30
                    """
                    )
                )
            ).all()
    except Exception:
        try:
            async with db.begin_nested():
                rows = (
                    await db.execute(
                        text(
                            f"""
                        SELECT id, thinking_text, keywords, source_hosts
                        FROM geo_monitor_probe_results
                        WHERE question_id IN ({id_list})
                        ORDER BY id DESC
                        LIMIT 30
                        """
                        )
                    )
                ).all()
        except Exception:
            logger.info("theme_mining_no_thinking_cols scene_id=%s", scene_id)
            rows = []

    probe_ids: list[int] = []
    for r in rows:
        probe_ids.append(int(r[0]))
        grade = str(r[4]).strip().lower() if len(r) > 4 and r[4] is not None else ""
        scheme = str(r[5]).strip() if len(r) > 5 and r[5] is not None else ""
        thinking = str(r[1] or "").strip() if len(r) > 1 else ""
        # 只收明文 A 轨；无 grade 列时仅 framework_api 且 thinking 非空可作 raw
        is_raw = grade == "raw" or (not grade and scheme == "framework_api" and len(thinking) >= 20)
        if is_raw and thinking:
            thinking_texts.append(thinking[:4000])
        if len(r) > 2 and r[2]:
            kw = r[2]
            if isinstance(kw, list):
                keywords.extend(str(x) for x in kw if x)
            elif isinstance(kw, str):
                try:
                    parsed = json.loads(kw)
                    if isinstance(parsed, list):
                        keywords.extend(str(x) for x in parsed if x)
                except Exception:
                    pass
        if len(r) > 3 and r[3]:
            hosts = r[3]
            if isinstance(hosts, list):
                for h in hosts[:5]:
                    source_hints.append({"title": str(h), "url": "", "domain": str(h)})
        if len(r) > 6 and r[6]:
            fw = r[6]
            if isinstance(fw, str):
                try:
                    fw = json.loads(fw)
                except Exception:
                    fw = None
            if isinstance(fw, dict) and any(fw.get(k) for k in ("compare_dims", "open_gaps", "sub_questions")):
                frameworks.append(fw)

    # citations
    if probe_ids and await _table_exists(db, "geo_monitor_probe_citations"):
        try:
            async with db.begin_nested():
                cite_rows = (
                    await db.execute(
                        text(
                            f"""
                        SELECT title, url FROM geo_monitor_probe_citations
                        WHERE probe_result_id IN ({",".join(str(i) for i in probe_ids[:20])})
                        ORDER BY position ASC, id ASC
                        LIMIT 20
                        """
                        )
                    )
                ).all()
            for title, url in cite_rows:
                source_hints.append(
                    {
                        "title": str(title or "")[:120],
                        "url": str(url or "")[:300],
                        "domain": _domain(str(url or "")),
                    }
                )
        except Exception:
            logger.debug("theme_mining_citations_skip", exc_info=True)

    # 信源去重 + 归属
    from app.services.geoeval.domain_catalog import classify_owner, load_domain_catalog

    catalog = await load_domain_catalog(db)
    seen_src: set[str] = set()
    uniq_src: list[dict[str, str]] = []
    for s in source_hints:
        key = s.get("domain") or s.get("url") or s.get("title") or ""
        if key and key not in seen_src:
            seen_src.add(key)
            owner = classify_owner(
                s.get("url") or s.get("domain") or "",
                official=list(catalog.get("official") or []),
                competitors=list(catalog.get("competitor") or []),
                wiki=list(catalog.get("wiki") or []),
            )
            uniq_src.append({**s, "owner": owner})

    return {
        "thinking_texts": thinking_texts[:8],
        "keywords": list(dict.fromkeys(keywords))[:20],
        "source_hints": uniq_src[:12],
        "frameworks": frameworks[:4],
    }


async def _maybe_llm_enhance(db: AsyncSession, mining: dict[str, Any], scene: dict[str, Any]) -> dict[str, Any]:
    """可选 LLM 扩写；失败/Mock 则原样返回。"""
    settings = get_settings()
    if settings.ai_mock_mode:
        mining["llm_enhanced"] = False
        mining["llm_skip_reason"] = "ai_mock_mode"
        return mining

    from app.services.geoflow.llm_client import get_active_chat_model
    from app.ai.llm_gateway import resolve_llm_endpoint

    model = await get_active_chat_model(db)
    if model is None:
        mining["llm_enhanced"] = False
        mining["llm_skip_reason"] = "no_chat_model"
        return mining
    ep = resolve_llm_endpoint(model)
    if not ep.base_url or not ep.api_key:
        mining["llm_enhanced"] = False
        mining["llm_skip_reason"] = "no_chat_model"
        return mining

    prompt = (
        "你是 GEO 主题挖掘助手。根据场景与探针证据，输出 JSON："
        '{"thinking_digest":"...","longtail_queries":["...","...","..."],'
        '"keyword_combos":["a+b","c+d"],"candidate_titles":["战役名1","战役名2"]}\n'
        "要求：longtail_queries 必须是用户向长尾问法，不能与探针原文完全相同。\n"
        f"场景: {json.dumps(scene, ensure_ascii=False)}\n"
        f"证据: {json.dumps({'probe_evidence': mining.get('probe_evidence'), 'thinking_sample': (mining.get('thinking_digest') or '')[:400]}, ensure_ascii=False)}"
    )
    try:
        import httpx

        base = ep.base_url.rstrip("/")
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {ep.api_key}", "Content-Type": "application/json"},
                json={
                    "model": ep.model_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 600,
                    "temperature": 0.3,
                },
            )
        if resp.status_code >= 400:
            logger.warning("theme_mining_llm_http status=%s", resp.status_code)
            mining["llm_enhanced"] = False
            return mining
        content = (((resp.json() or {}).get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        m = re.search(r"\{[\s\S]*\}", content)
        if not m:
            mining["llm_enhanced"] = False
            return mining
        data = json.loads(m.group(0))
        probe_set = {_normalize_q(p.get("question_text", "")) for p in (mining.get("probe_evidence") or [])}
        longtails = []
        for q in data.get("longtail_queries") or []:
            qs = str(q).strip()
            if qs and _normalize_q(qs) not in probe_set:
                longtails.append(qs[:200])
        if len(longtails) >= 3:
            mining["longtail_queries"] = longtails[:8]
        if data.get("thinking_digest"):
            mining["thinking_digest"] = str(data["thinking_digest"])[:800]
        if data.get("keyword_combos"):
            mining["keyword_combos"] = [str(x)[:80] for x in data["keyword_combos"][:12]]
        cands = [str(x).strip()[:120] for x in (data.get("candidate_titles") or []) if str(x).strip()]
        if cands:
            mining["candidate_titles"] = cands[:3]
        mining["llm_enhanced"] = True
        logger.info("theme_mining_llm_ok scene=%s longtails=%s", scene.get("scene_name"), len(mining["longtail_queries"]))
    except Exception as exc:
        logger.warning("theme_mining_llm_failed err=%s", exc)
        mining["llm_enhanced"] = False
        mining["llm_skip_reason"] = str(exc)[:120]
    return mining


async def mine_theme_from_gap(
    db: AsyncSession,
    *,
    scene_id: int,
    gap: dict[str, Any],
    persona: str | None,
    scene_name: str,
    intent: str | None,
) -> dict[str, Any]:
    """返回 mining 包 + candidates。"""
    unsupported = gap.get("unsupported_sample") or []
    probe_evidence = [
        {"id": u.get("id"), "question_text": str(u.get("question_text") or "")[:200]}
        for u in unsupported
        if u.get("question_text")
    ]
    probe_texts = [p["question_text"] for p in probe_evidence]

    ctx = await _load_scene_probe_context(db, scene_id)
    from app.services.geoeval.framework_extractor import digest_framework, extract_framework, longtail_from_framework

    merged_fw = {}
    if ctx.get("frameworks"):
        merged_fw = ctx["frameworks"][0]
    elif ctx.get("thinking_texts"):
        merged_fw = extract_framework(
            "\n".join(ctx["thinking_texts"][:3]),
            scene_name=str(scene_name or ""),
            intent=str(intent or ""),
        )
    thinking_digest = digest_framework(merged_fw) if merged_fw else _digest_thinking(ctx["thinking_texts"])
    fw_longtail = longtail_from_framework(
        merged_fw,
        scene_name=str(scene_name or ""),
        intent=str(intent or ""),
        probe_texts=probe_texts,
    )
    longtail = fw_longtail or _rewrite_longtail(
        persona=str(persona or ""),
        scene_name=str(scene_name or ""),
        intent=str(intent or ""),
        probe_texts=probe_texts,
    )
    combos = _keyword_combos(str(scene_name or ""), str(intent or ""), probe_texts, ctx["keywords"])

    campaign_title = f"{scene_name or '场景'}：补齐 AI 决策链内容"
    mining: dict[str, Any] = {
        "probe_evidence": probe_evidence,
        "thinking_digest": thinking_digest,
        "source_hints": ctx["source_hints"],
        "longtail_queries": longtail,
        "keyword_combos": combos,
        "pack_hint": ["topic", "concept", "compare", "guide"],
        "campaign_title": campaign_title,
        "framework": merged_fw or None,
        "candidate_titles": [
            f"{scene_name or '场景'}：对比决策内容战役",
            f"{intent or '意图'}长尾覆盖：用户场景展开",
        ],
    }

    scene_payload = {
        "scene_id": scene_id,
        "persona": persona,
        "scene_name": scene_name,
        "intent": intent,
        "gap_rate": gap.get("gap_rate"),
        "gap_priority": gap.get("gap_priority"),
    }
    mining = await _maybe_llm_enhance(db, mining, scene_payload)

    # 再校验：longtail 不得等于探针原文集合
    probe_norm = {_normalize_q(t) for t in probe_texts}
    mining["longtail_queries"] = [
        q for q in mining["longtail_queries"] if _normalize_q(q) not in probe_norm
    ] or longtail

    candidates = []
    for i, title in enumerate(mining.get("candidate_titles") or []):
        # 每候选用 longtail 的轮换子集
        qs = mining["longtail_queries"][i:] + mining["longtail_queries"][:i]
        candidates.append(
            {
                "index": i,
                "title": title[:300],
                "target_queries": qs[:5] or mining["longtail_queries"][:3],
                "keyword_combos": mining.get("keyword_combos") or [],
            }
        )

    logger.info(
        "theme_mined scene_id=%s longtails=%s evidence=%s sources=%s llm=%s",
        scene_id,
        len(mining["longtail_queries"]),
        len(probe_evidence),
        len(mining.get("source_hints") or []),
        mining.get("llm_enhanced"),
    )
    return {"mining": mining, "candidates": candidates[:2], "campaign_title": mining["campaign_title"]}
