"""AIVIS 分析器 — 平台评分、难度评估、情感主题、场景漏斗。"""

import logging
import re
from collections import defaultdict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists
from app.services.geoeval.competitive_analyzer import compute_optimization_potential
from app.services.geoeval.monitor_probe import aggregate_probe_kpis

logger = logging.getLogger(__name__)

TJG_PROVIDER = "tjg_youzan"


async def _load_tjg_scene_visibility(db: AsyncSession) -> dict[str, dict[str, float | str | int | dict]]:
    """从最新 TJG 报告快照读取 intent 级可见性与元数据。"""
    if not await _table_exists(db, "geo_visibility_reports"):
        return {}
    row = (
        await db.execute(
            text(
                """
                SELECT sections->'product'->'scenes' AS scenes
                FROM geo_visibility_reports
                WHERE sections->'source'->>'provider' = :provider
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"provider": TJG_PROVIDER},
        )
    ).scalar_one_or_none()
    if not row or not isinstance(row, list):
        return {}

    mapping: dict[str, dict[str, float | str | int | dict]] = {}
    for item in row:
        if not isinstance(item, dict):
            continue
        key = f"{item.get('persona')}|{item.get('scene_name')}|{item.get('intent')}"
        mapping[key] = {
            "visibility_pct": float(item.get("visibility_pct") or 0),
            "gap_priority": str(item.get("gap_priority") or "covered"),
            "article_count": int(item.get("article_count") or 0),
            "external_id": str(item.get("external_id") or ""),
            "node_metadata": item.get("node_metadata") or {},
        }
    return mapping


async def _load_tjg_touchpoint_tree(db: AsyncSession) -> dict | None:
    if not await _table_exists(db, "geo_visibility_reports"):
        return None
    row = (
        await db.execute(
            text(
                """
                SELECT sections->'product'->'touchpoint_tree' AS tree
                FROM geo_visibility_reports
                WHERE sections->'source'->>'provider' = :provider
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"provider": TJG_PROVIDER},
        )
    ).scalar_one_or_none()
    return row if isinstance(row, dict) and row.get("tree") else None


async def _load_tjg_platform_breakdown(db: AsyncSession, layer: str = "brand") -> list[dict]:
    if not await _table_exists(db, "geo_visibility_reports"):
        return []
    layer_key = "brand" if layer == "brand" else "product"
    row = (
        await db.execute(
            text(
                f"""
                SELECT sections->'{layer_key}'->'platform_breakdown' AS breakdown
                FROM geo_visibility_reports
                WHERE sections->'source'->>'provider' = :provider
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"provider": TJG_PROVIDER},
        )
    ).scalar_one_or_none()
    return list(row) if isinstance(row, list) else []

PLATFORM_LABELS = {
    "doubao": "豆包",
    "deepseek": "DeepSeek",
    "tongyi": "通义千问",
    "yuanbao": "元宝",
    "wenxin": "文心一言",
    "kimi": "Kimi",
}

SENTIMENT_TOPIC_RULES: dict[str, list[str]] = {
    "技术实力": ["电池", "安全", "智驾", "芯片", "雷达", "架构", "自研", "算法", "NOA", "L3"],
    "产品体验": ["互联", "座舱", "续航", "空间", "舒适", "体验", "配置", "屏幕", "音响"],
    "品牌感知": ["口碑", "品牌", "历史", "进步", "信任", "服务", "售后", "形象"],
}


async def _load_market_settings(db: AsyncSession) -> dict:
    defaults = {"monthly_search_volume": 50000, "ai_platform_mau": 820000000}
    if not await _table_exists(db, "site_settings"):
        return defaults
    rows = (
        await db.execute(
            text(
                """
                SELECT setting_key, setting_value FROM site_settings
                WHERE setting_key IN ('aivis_monthly_search_volume', 'aivis_ai_platform_mau')
                """
            )
        )
    ).all()
    for key, value in rows:
        try:
            if key == "aivis_monthly_search_volume":
                defaults["monthly_search_volume"] = int(value)
            elif key == "aivis_ai_platform_mau":
                defaults["ai_platform_mau"] = int(value)
        except (TypeError, ValueError):
            pass
    return defaults


async def score_platforms(db: AsyncSession, query_type: str | None = None) -> list[dict]:
    """平台选择建议：可见性 40% + 排名 30% + 好感度 30%。

    无探针样本时返回空列表（禁止用 0 分伪装「优先推荐」）。
    """
    kpis = await aggregate_probe_kpis(db, query_type=query_type)
    platform_rows = [r for r in (kpis.get("platform_summary") or []) if (r.get("total") or 0) > 0]
    if not platform_rows:
        logger.info("platform_scored skipped reason=no_probe_samples")
        return []

    max_vis = max((r.get("visibility_pct") or 0) for r in platform_rows) or 1
    max_rank = max((r.get("weighted_rank_score") or 0) for r in platform_rows) or 1
    sentiment = kpis.get("sentiment_score") or 50

    scored: list[dict] = []
    for row in platform_rows:
        vis = float(row.get("visibility_pct") or 0)
        rank = float(row.get("weighted_rank_score") or 0)
        top3 = row.get("top3_pct")
        vis_norm = vis / max_vis * 100
        rank_norm = rank / max_rank * 100 if max_rank else 0
        sent_norm = float(sentiment)
        score = round(vis_norm * 0.4 + rank_norm * 0.3 + sent_norm * 0.3)
        plat = str(row["platform"])
        reason_parts = [f"可见性 {vis:.0f}%"]
        if top3 is not None:
            reason_parts.append(f"Top3 {float(top3):.0f}%")
        if rank:
            reason_parts.append(f"加权排名 {rank:.1f}")
        scored.append(
            {
                "platform": plat,
                "label": PLATFORM_LABELS.get(plat, plat),
                "score": score,
                "visibility_pct": vis,
                "top3_pct": top3,
                "sample_n": int(row.get("total") or 0),
                "weighted_rank_score": row.get("weighted_rank_score"),
                "sentiment_score": sentiment,
                "reason": " · ".join(reason_parts),
            }
        )
    scored.sort(key=lambda x: x["score"], reverse=True)
    logger.info("platform_scored count=%s top=%s", len(scored), scored[0]["platform"] if scored else "none")
    return scored


async def assess_difficulty(db: AsyncSession) -> dict:
    """三维难度评估：监管合规、市场竞争、实体基础。"""
    from app.services.admin.strategy_service import _tech_brand_metrics
    from app.services.geoeval.competitive_analyzer import build_competitor_matrix

    matrix = await build_competitor_matrix(db)
    tech = await _tech_brand_metrics(db)
    kpis = await aggregate_probe_kpis(db)

    gap = float(matrix.get("gap_vs_leader") or 0)
    competitor_count = len(matrix.get("competitors") or [])

    # 市场竞争：差距越大 + 竞品越多 → 难度越高
    if gap >= 30:
        market_score = 5
    elif gap >= 20:
        market_score = 4
    elif gap >= 10:
        market_score = 3
    elif gap >= 5:
        market_score = 2
    else:
        market_score = 1
    if competitor_count >= 8:
        market_score = min(5, market_score + 1)

    # 实体基础：Wiki/GEOweb/资产覆盖越高 → 难度越低（分越低越容易）
    wiki = float(tech.get("wiki_compliance_pct") or 0)
    geoweb = float(tech.get("geoweb_sync_rate_pct") or tech.get("gweb_sync_rate_pct") or 0)
    p0 = float(tech.get("p0_coverage_pct") or 0)
    entity_avg = (wiki + geoweb + p0) / 3
    if entity_avg >= 80:
        entity_score = 1
    elif entity_avg >= 60:
        entity_score = 2
    elif entity_avg >= 40:
        entity_score = 3
    elif entity_avg >= 20:
        entity_score = 4
    else:
        entity_score = 5

    # 监管合规：默认中等，可从 site_settings 覆盖
    regulatory_score = 3
    if await _table_exists(db, "site_settings"):
        row = (
            await db.execute(
                text("SELECT setting_value FROM site_settings WHERE setting_key = 'aivis_regulatory_score' LIMIT 1")
            )
        ).scalar_one_or_none()
        if row:
            try:
                regulatory_score = max(1, min(5, int(row)))
            except (TypeError, ValueError):
                pass

    overall = round((regulatory_score + market_score + entity_score) / 3, 1)
    opt = await compute_optimization_potential(
        float(kpis.get("visibility_pct") or 0),
        float(matrix.get("self_visibility_pct") or 0) + gap,
    )

    return {
        "regulatory_compliance": {"score": regulatory_score, "label": _score_label(regulatory_score), "description": "监管与合规要求"},
        "market_competition": {"score": market_score, "label": _score_label(market_score), "description": f"竞品 {competitor_count} 个，差距 {gap}pp"},
        "entity_foundation": {"score": entity_score, "label": _score_label(entity_score), "description": f"Wiki {wiki}% · Gweb {geoweb}% · P0 {p0}%"},
        "overall_score": overall,
        "overall_label": _score_label(round(overall)),
        "lift_needed_pct": opt.get("lift_needed"),
        "difficulty_score": opt.get("difficulty_score"),
    }


def _score_label(score: int | float) -> str:
    s = int(score)
    labels = {1: "低难度", 2: "较低", 3: "中等", 4: "较高", 5: "高难度"}
    return labels.get(s, "中等")


async def extract_sentiment_topics(db: AsyncSession, limit: int = 20) -> list[dict]:
    """从探针 snippet 提取正负向主题标签。"""
    if not await _table_exists(db, "geo_monitor_probe_results"):
        return []

    rows = (
        await db.execute(
            text(
                """
                SELECT snippet, sentiment FROM geo_monitor_probe_results
                WHERE snippet IS NOT NULL AND snippet != ''
                ORDER BY id DESC LIMIT 200
                """
            )
        )
    ).all()

    topic_counts: dict[tuple[str, str], int] = defaultdict(int)
    for snippet, sentiment in rows:
        polarity = "positive"
        if isinstance(sentiment, dict):
            polarity = str(sentiment.get("polarity") or "neutral")
        elif sentiment:
            polarity = str(sentiment)
        if polarity not in ("positive", "negative"):
            continue
        text_lower = str(snippet).lower()
        for category, keywords in SENTIMENT_TOPIC_RULES.items():
            if any(kw.lower() in text_lower for kw in keywords):
                topic_counts[(category, polarity)] += 1

    items = [
        {"category": cat, "polarity": pol, "count": cnt, "label": f"{'正向' if pol == 'positive' else '负向'}·{cat}"}
        for (cat, pol), cnt in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
    ]
    return items[:limit]


async def build_scene_funnel_tree(db: AsyncSession) -> dict:
    """Persona → Scene → Intent → Query 五层漏斗树（对齐 TJG 场景图谱层级）。"""
    if not await _table_exists(db, "geo_monitor_scenes"):
        return {"personas": [], "stats": {"persona_count": 0, "scene_count": 0, "intent_count": 0, "query_count": 0}}

    scenes = (
        await db.execute(
            text(
                """
                SELECT id, persona, scene_name, intent, weight_pct, gap_rate, gap_priority
                FROM geo_monitor_scenes WHERE status = 'active'
                ORDER BY weight_pct DESC, id ASC
                """
            )
        )
    ).all()

    has_qtype = await _table_exists(db, "geo_monitor_questions")
    tjg_visibility = await _load_tjg_scene_visibility(db)
    persona_map: dict[str, dict] = {}

    for sid, persona, scene_name, intent, weight, gap_rate, gap_priority in scenes:
        persona_key = str(persona or "未分类画像")
        if persona_key not in persona_map:
            persona_map[persona_key] = {"name": persona_key, "weight_pct": 0.0, "scenes": {}}

        scene_key = str(scene_name or intent or "未命名场景")
        scene_bucket = persona_map[persona_key]["scenes"]
        if scene_key not in scene_bucket:
            scene_bucket[scene_key] = {"name": scene_key, "weight_pct": 0.0, "intents": []}

        queries: list[dict] = []
        if has_qtype:
            cite_join = ""
            cite_select = "0 AS citation_count"
            if await _table_exists(db, "geo_monitor_probe_citations") and await _table_exists(db, "geo_monitor_probe_results"):
                cite_join = """
                    LEFT JOIN geo_monitor_probe_results pr ON pr.question_id = mq.id
                    LEFT JOIN geo_monitor_probe_citations pc ON pc.probe_result_id = pr.id
                """
                cite_select = "COUNT(DISTINCT pc.id) AS citation_count"
            qrows = (
                await db.execute(
                    text(
                        f"""
                        SELECT mq.id, mq.question_text, {cite_select}
                        FROM geo_monitor_questions mq
                        {cite_join}
                        WHERE mq.scene_id = :sid AND mq.status = 'active'
                        GROUP BY mq.id, mq.question_text
                        ORDER BY mq.id
                        LIMIT 20
                        """
                    ),
                    {"sid": int(sid)},
                )
            ).all()
            queries = [
                {"id": int(q[0]), "text": str(q[1]), "citation_count": int(q[2] or 0)}
                for q in qrows
            ]

        tjg_key = f"{persona_key}|{scene_key}|{intent or scene_name}"
        tjg_meta = tjg_visibility.get(tjg_key, {})
        visibility_pct = float(tjg_meta.get("visibility_pct") or 0)
        intent_gap_priority = str(tjg_meta.get("gap_priority") or gap_priority or "covered")
        if not visibility_pct:
            visibility_pct = round(float(gap_rate or 0) * 100, 1)

        article_count = int(tjg_meta.get("article_count") or 0)
        node_metadata = tjg_meta.get("node_metadata") or {}
        if not article_count and queries:
            article_count = 0

        scene_bucket[scene_key]["intents"].append(
            {
                "id": int(sid),
                "name": str(intent or scene_name or "未命名意图"),
                "visibility_pct": visibility_pct,
                "gap_rate": float(gap_rate or 0),
                "gap_priority": intent_gap_priority,
                "queries": queries,
                "query_count": len(queries),
                "citation_count": sum(int(q.get("citation_count") or 0) for q in queries),
                "article_count": article_count,
                "external_id": str(tjg_meta.get("external_id") or ""),
                "node_metadata": node_metadata if isinstance(node_metadata, dict) else {},
            }
        )
        scene_bucket[scene_key]["weight_pct"] += float(weight or 0)
        persona_map[persona_key]["weight_pct"] += float(weight or 0)

    personas: list[dict] = []
    scene_count = 0
    intent_count = 0
    query_count = 0
    for persona in sorted(persona_map.values(), key=lambda p: p["weight_pct"], reverse=True):
        scene_list = sorted(persona["scenes"].values(), key=lambda s: s["weight_pct"], reverse=True)
        for scene in scene_list:
            deduped: dict[str, dict] = {}
            for intent in scene["intents"]:
                key = str(intent.get("name") or intent.get("id"))
                prev = deduped.get(key)
                if not prev or intent.get("query_count", 0) > prev.get("query_count", 0):
                    deduped[key] = intent
            scene["intents"] = sorted(deduped.values(), key=lambda i: i.get("visibility_pct", 0))
            scene_count += 1
            intent_count += len(scene["intents"])
            query_count += sum(i.get("query_count", 0) for i in scene["intents"])
        persona["scenes"] = scene_list
        personas.append(persona)

    touchpoint = await _load_tjg_touchpoint_tree(db)
    return {
        "personas": personas,
        "stats": {
            "persona_count": len(personas),
            "scene_count": scene_count,
            "intent_count": intent_count,
            "query_count": query_count,
        },
        "touchpoint_tree": touchpoint,
        "highlight_node_id": str((touchpoint or {}).get("highlight_node_id") or ""),
    }


async def build_optimization_panel(db: AsyncSession) -> dict:
    """优化策略决策台：就绪度 + 可行动作 + 真实探针/缺口洞察。"""
    from app.services.admin.monitor_aivis_service import list_monitor_insights
    from app.services.geoeval.competitive_analyzer import build_competitor_matrix
    from app.services.geoeval.scene_gap_analyzer import compute_all_scene_gaps

    market = await _load_market_settings(db)
    kpis = await aggregate_probe_kpis(db, north_star=True)
    platform_scores = await score_platforms(db)
    difficulty = await assess_difficulty(db)
    matrix = await build_competitor_matrix(db)

    question_count = 0
    scene_count = 0
    competitor_count = 0
    stored_scenes: list[dict] = []

    if await _table_exists(db, "geo_monitor_questions"):
        question_count = int(
            (
                await db.execute(
                    text("SELECT COUNT(*) FROM geo_monitor_questions WHERE status = 'active'")
                )
            ).scalar_one()
            or 0
        )
    if await _table_exists(db, "geo_monitor_scenes"):
        scene_rows = (
            await db.execute(
                text(
                    """
                    SELECT id, scene_name, persona, intent, weight_pct, gap_rate, gap_priority
                    FROM geo_monitor_scenes
                    WHERE status = 'active'
                    ORDER BY COALESCE(gap_rate, 0) * COALESCE(weight_pct, 1) DESC, weight_pct DESC
                    LIMIT 8
                    """
                )
            )
        ).all()
        scene_count = int(
            (await db.execute(text("SELECT COUNT(*) FROM geo_monitor_scenes WHERE status = 'active'"))).scalar_one()
            or 0
        )
        stored_scenes = [
            {
                "scene_id": int(r[0]),
                "scene_name": r[1],
                "persona": r[2],
                "intent": r[3],
                "weight_pct": float(r[4] or 0),
                "gap_rate": float(r[5] or 0),
                "gap_priority": str(r[6] or "covered"),
            }
            for r in scene_rows
        ]
    if await _table_exists(db, "geo_monitor_competitors"):
        competitor_count = int(
            (
                await db.execute(
                    text("SELECT COUNT(*) FROM geo_monitor_competitors WHERE status = 'active'")
                )
            ).scalar_one_or_none()
            or 0
        )

    probe_count = int(kpis.get("probe_count") or 0)
    valid_n = kpis.get("valid_sample_n")
    has_scan = probe_count > 0

    # 有场景时才算缺口（避免空库全量扫描）
    gaps: dict = {"scenes": [], "high_gap_count": 0}
    if scene_count > 0:
        try:
            gaps = await compute_all_scene_gaps(db)
        except Exception:
            logger.exception("optimization_gap_compute_failed")

    gap_scenes = sorted(
        gaps.get("scenes") or [],
        key=lambda s: (float(s.get("gap_rate") or 0) * float(s.get("weight_pct") or 1)),
        reverse=True,
    )
    top_scenes = gap_scenes[:5] if gap_scenes else stored_scenes[:5]
    priority_scenes = [
        {
            "scene_id": s.get("scene_id") or s.get("id"),
            "scene_name": s.get("scene_name"),
            "persona": s.get("persona"),
            "intent": s.get("intent"),
            "gap_rate": float(s.get("gap_rate") or 0),
            "gap_priority": s.get("gap_priority") or "covered",
            "weight_pct": float(s.get("weight_pct") or 0),
            "question_count": s.get("question_count"),
            "supported_count": s.get("supported_count"),
            "unsupported_sample": s.get("unsupported_sample") or [],
        }
        for s in top_scenes
    ]

    blockers: list[str] = []
    if question_count == 0:
        blockers.append("尚未配置监控问题库")
    if scene_count == 0:
        blockers.append("尚未建立场景图谱")
    if competitor_count == 0:
        blockers.append("尚未配置竞品对照")
    if not has_scan:
        blockers.append("尚无有效探针样本（需先全量扫描）")

    actions: list[dict] = []
    if question_count == 0:
        actions.append(
            {
                "id": "setup_questions",
                "priority": "high",
                "title": "配置监控问题库",
                "body": "按对比/决策题型录入问题，作为探针与缺口分析入口。",
                "href": "/strategy/question-bank",
                "cta": "去问题库",
            }
        )
    if scene_count == 0:
        actions.append(
            {
                "id": "setup_scenes",
                "priority": "high",
                "title": "建立场景图谱",
                "body": "画像→场景→意图→Query；也可导入 TJG 报告快速铺场景。",
                "href": "/strategy/scene-graph",
                "cta": "去场景图谱",
            }
        )
    if competitor_count == 0:
        actions.append(
            {
                "id": "setup_competitors",
                "priority": "medium",
                "title": "配置竞品品牌",
                "body": "竞品对照决定「相对竞品 pp」与平台优先级解释。",
                "href": "/strategy/brand",
                "cta": "去品牌可见性",
            }
        )
    if question_count > 0 and not has_scan:
        actions.append(
            {
                "id": "run_scan",
                "priority": "high",
                "title": "执行全量探针扫描",
                "body": "产出 Top3 / 提及率 / 平台可见性，才能生成平台投入建议。",
                "href": "/strategy/collection",
                "cta": "去数据采集",
            }
        )
    high_gap = [s for s in priority_scenes if s.get("gap_priority") == "high"]
    if high_gap:
        top = high_gap[0]
        actions.append(
            {
                "id": "close_gap",
                "priority": "high",
                "title": f"挖主题：{top.get('scene_name')}",
                "body": f"缺口率 {float(top.get('gap_rate') or 0)*100:.0f}% · 权重 {top.get('weight_pct') or 0}% —— 生成主题草稿（含挖掘摘要），再到内容生产确认。",
                "href": "/production/themes",
                "cta": "去主题包",
                "scene_id": top.get("scene_id"),
            }
        )
    entity = difficulty.get("entity_foundation") or {}
    if int(entity.get("score") or 0) >= 4:
        actions.append(
            {
                "id": "strengthen_entity",
                "priority": "medium",
                "title": "夯实实体基础（Wiki / 技术 IP）",
                "body": entity.get("description") or "Wiki/P0 覆盖偏低，会抬高可见性难度。",
                "href": "/production/tech-assets",
                "cta": "去技术 IP",
            }
        )
    if not actions:
        actions.append(
            {
                "id": "review_report",
                "priority": "low",
                "title": "复盘诊断报告",
                "body": "主路径已就绪，查看北极星章与闭环验证，决定下一轮投入。",
                "href": "/strategy/reports",
                "cta": "看报告",
            }
        )

    insights = (await list_monitor_insights(db)).get("items", [])
    if not insights and blockers:
        insights = [
            {
                "id": f"ready-{i}",
                "insight_type": "readiness",
                "title": "策略就绪阻塞",
                "body": b,
            }
            for i, b in enumerate(blockers[:3])
        ]

    gap_pp = matrix.get("gap_vs_leader")
    opt_potential = await compute_optimization_potential(
        float(kpis.get("top3_pct") or kpis.get("visibility_pct") or 0),
        float(kpis.get("top3_pct") or kpis.get("visibility_pct") or 0) + float(gap_pp or 0),
    )

    ready = question_count > 0 and has_scan
    summary = (
        f"就绪：问题 {question_count} · 场景 {scene_count} · 探针 {probe_count}"
        if ready
        else f"未就绪：{blockers[0] if blockers else '缺少策略输入'}"
    )

    return {
        "market_opportunity": {
            "monthly_search_volume": market["monthly_search_volume"],
            "ai_platform_mau": market["ai_platform_mau"],
            "summary": f"月搜索量 {market['monthly_search_volume']:,}+，AI 平台月活 {market['ai_platform_mau'] / 1e8:.1f} 亿",
        },
        "platform_recommendations": platform_scores[:5],
        "priority_scenes": priority_scenes,
        "insights": insights[:8],
        "north_star": {
            "top3_pct": kpis.get("top3_pct"),
            "gap_vs_leader_top3_pp": kpis.get("gap_vs_leader_top3_pp"),
            "mention_rate_pct": kpis.get("mention_rate_pct")
            or round(float(kpis.get("mention_rate") or 0) * 100, 1),
            "valid_sample_n": valid_n,
            "probe_count": probe_count,
            "kpi_track": kpis.get("kpi_track") or "open_api",
        },
        "readiness": {
            "question_count": question_count,
            "scene_count": scene_count,
            "probe_count": probe_count,
            "competitor_count": competitor_count,
            "high_gap_count": int(gaps.get("high_gap_count") or len(high_gap)),
            "has_scan": has_scan,
            "ready": ready,
            "blockers": blockers,
            "summary": summary,
        },
        "actions": actions,
        "difficulty": {
            "overall_score": difficulty.get("overall_score"),
            "overall_label": difficulty.get("overall_label"),
            "market_competition": difficulty.get("market_competition"),
            "entity_foundation": difficulty.get("entity_foundation"),
            "lift_needed_pct": difficulty.get("lift_needed_pct"),
        },
        "competitor_gap": {
            "gap_vs_leader": gap_pp,
            "self_visibility_pct": matrix.get("self_visibility_pct"),
            "competitors": matrix.get("competitors") or [],
            "lift_needed_pct": opt_potential.get("lift_needed"),
        },
    }
