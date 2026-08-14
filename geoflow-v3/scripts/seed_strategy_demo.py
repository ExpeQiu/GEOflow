#!/usr/bin/env python3
"""策略与分析（L1）演示数据种子 — 幂等。

覆盖主链路可读样例：
  探针问题库 → 探针结果（排名/思考链/信源）→ 场景缺口 → 可挖主题草稿

用法（在 geoflow-v3/backend 下）:
  .venv/bin/python ../scripts/seed_strategy_demo.py
  .venv/bin/python ../scripts/seed_strategy_demo.py --force   # 清掉旧 demo 再种

日志键: seed_strategy_demo
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text  # noqa: E402

from app.core.database import async_session_factory  # noqa: E402
from app.services.admin.production_service import _table_exists  # noqa: E402
from app.services.geoeval.platform_connectors.base import calc_ranking_score  # noqa: E402

logging.basicConfig(level=logging.INFO, format="[seed_strategy_demo] %(message)s")
logger = logging.getLogger("seed_strategy_demo")

DEMO_MARKER = "strategy_demo_seeded"
DEMO_TAG = "demo:"
BRAND = "吉利汽车"
BRAND_ALIASES = ["吉利", "Geely", "银河", "极氪"]
COMPETITORS = [
    ("比亚迪", ["BYD", "王朝", "海洋"], False),
    ("理想", ["理想汽车", "Li Auto"], False),
    ("小鹏", ["XPeng", "小鹏汽车"], False),
    (BRAND, BRAND_ALIASES, True),
]

# 产品层（entity_type=product）— 产品可见性矩阵依赖此项
PRODUCTS = [
    ("千里浩瀚 G-ASD", ["G-ASD", "千里浩瀚", "浩瀚"], True),
    ("小鹏 XNGP", ["XNGP", "小鹏智驾"], False),
    ("理想 AD Max", ["AD Max", "理想智驾"], False),
    ("华为 ADS", ["ADS", "华为智驾"], False),
]

# persona / scene / intent / weight / external_id suffix
SCENES = [
    ("家庭购车用户", "家用纯电选型", "对比决策", 30, "family-bev"),
    ("科技尝鲜用户", "智能驾驶体验", "能力边界", 25, "ad-capability"),
    ("品牌认知用户", "品牌可信度", "口碑核实", 20, "brand-trust"),
]

# scene_suffix -> list of (question, query_type, priority, intent_type)
QUESTIONS = {
    "family-bev": [
        ("家用纯电 SUV 怎么选，吉利银河和比亚迪唐该看哪些点？", "product", 95, "compare"),
        ("吉利银河 L7 续航和空间适合家庭吗？", "product", 90, "decision"),
        ("买家用电动车要核实哪些安全与质保参数？", "product", 88, "decision"),
    ],
    "ad-capability": [
        ("吉利智驾 NOA 能力和理想、小鹏比怎么样？", "product", 92, "compare"),
        ("高速 NOA 适用场景与接管率该怎么判断？", "product", 88, "decision"),
        ("城市领航功能边界是什么，适合哪些用户？", "product", 85, "decision"),
    ],
    "brand-trust": [
        ("吉利汽车口碑怎么样？", "brand", 96, "cognition"),
        ("吉利汽车和比亚迪技术实力谁更强？", "competitor", 93, "compare"),
        ("买吉利汽车靠谱吗？售后与保值率如何？", "brand", 90, "decision"),
    ],
}

PLATFORMS = ("doubao", "deepseek", "yuanbao", "tongyi", "kimi")

# question_suffix key not needed — assign ranks by scene + platform pattern
# rank patterns: self often mid-pack on product, weaker on AD, better on brand
RANK_BY_SCENE = {
    "family-bev": {"doubao": 4, "deepseek": 3, "yuanbao": 5, "tongyi": 2, "kimi": None},
    "ad-capability": {"doubao": 6, "deepseek": None, "yuanbao": 7, "tongyi": 5, "kimi": None},
    "brand-trust": {"doubao": 2, "deepseek": 1, "yuanbao": 3, "tongyi": 2, "kimi": 4},
}

COMP_MENTIONS = {
    "family-bev": ["比亚迪", "理想", "吉利汽车", "千里浩瀚 G-ASD"],
    "ad-capability": ["小鹏 XNGP", "理想 AD Max", "华为 ADS", "千里浩瀚 G-ASD"],
    "brand-trust": ["比亚迪", "吉利汽车", "长城"],
}

THINKING = {
    "family-bev": (
        "先看家庭使用场景：空间、续航、安全配置；再对比价位带竞品参数；"
        "最后核对官方口径与第三方测评是否一致，再给出推荐排序。"
    ),
    "ad-capability": (
        "对比智驾需拆能力边界：高速 NOA、城市领航、接管率与地图依赖；"
        "再看品牌公布里程与用户真实反馈；缺少权威信源时不宜给绝对结论。"
    ),
    "brand-trust": (
        "品牌可信度从口碑、技术叙事、售后网络与长期质量稳定性四维评估；"
        "引用权威媒体与官方技术白皮书，避免只看短视频口碑。"
    ),
}

SOURCES = {
    "family-bev": ["geely.com", "autohome.com.cn", "dongchedi.com"],
    "ad-capability": ["geely.com", "36kr.com", "ithome.com"],
    "brand-trust": ["geely.com", "people.com.cn", "xinhuanet.com"],
}


async def _upsert_setting(db, key: str, value: str, group: str = "monitor") -> None:
    exists = (
        await db.execute(text("SELECT id FROM site_settings WHERE setting_key = :k"), {"k": key})
    ).first()
    if exists:
        await db.execute(
            text("UPDATE site_settings SET setting_value = :v, updated_at = CURRENT_TIMESTAMP WHERE setting_key = :k"),
            {"v": value, "k": key},
        )
    else:
        await db.execute(
            text(
                """
                INSERT INTO site_settings (setting_key, setting_value, value_type, group_name)
                VALUES (:k, :v, 'string', :g)
                """
            ),
            {"k": key, "v": value, "g": group},
        )


async def _clear_demo(db) -> None:
    scene_ids = [
        int(r[0])
        for r in (
            await db.execute(
                text("SELECT id FROM geo_monitor_scenes WHERE external_id LIKE :p"),
                {"p": f"{DEMO_TAG}%"},
            )
        ).all()
    ]
    if not scene_ids:
        logger.info("clear_demo skip (no demo scenes)")
        return
    id_list = ",".join(str(i) for i in scene_ids)
    qids = [
        int(r[0])
        for r in (await db.execute(text(f"SELECT id FROM geo_monitor_questions WHERE scene_id IN ({id_list})"))).all()
    ]
    if qids:
        qlist = ",".join(str(i) for i in qids)
        probe_ids = [
            int(r[0])
            for r in (
                await db.execute(text(f"SELECT id FROM geo_monitor_probe_results WHERE question_id IN ({qlist})"))
            ).all()
        ]
        if probe_ids and await _table_exists(db, "geo_monitor_probe_citations"):
            plist = ",".join(str(i) for i in probe_ids)
            await db.execute(text(f"DELETE FROM geo_monitor_probe_citations WHERE probe_result_id IN ({plist})"))
        await db.execute(text(f"DELETE FROM geo_monitor_probe_results WHERE question_id IN ({qlist})"))
        await db.execute(text(f"DELETE FROM geo_monitor_questions WHERE id IN ({qlist})"))
    if await _table_exists(db, "geo_themes"):
        # 演示场景关联 + 孤儿草稿一并清理
        await db.execute(
            text(
                f"""
                DELETE FROM geo_themes
                WHERE scene_id IN ({id_list})
                   OR scene_id IS NULL
                   OR COALESCE(meta->>'source', '') = 'strategy_demo'
                   OR title LIKE '【演示】%'
                   OR title LIKE '%：补齐 AI 决策链内容'
                """
            )
        )
    await db.execute(text(f"DELETE FROM geo_monitor_scenes WHERE id IN ({id_list})"))
    logger.info("clear_demo scenes=%s questions=%s", len(scene_ids), len(qids))


async def _upsert_competitor(
    db,
    name: str,
    aliases: list[str],
    is_self: bool,
    *,
    entity_type: str,
) -> None:
    row = (
        await db.execute(
            text(
                """
                SELECT id FROM geo_monitor_competitors
                WHERE brand_name = :n AND COALESCE(entity_type, 'brand') = :et
                LIMIT 1
                """
            ),
            {"n": name, "et": entity_type},
        )
    ).first()
    if row:
        await db.execute(
            text(
                """
                UPDATE geo_monitor_competitors
                SET aliases = CAST(:a AS JSON), is_self = :s, status = 'active', entity_type = :et
                WHERE id = :id
                """
            ),
            {
                "a": json.dumps(aliases, ensure_ascii=False),
                "s": is_self,
                "et": entity_type,
                "id": int(row[0]),
            },
        )
    else:
        await db.execute(
            text(
                """
                INSERT INTO geo_monitor_competitors (brand_name, aliases, is_self, status, entity_type)
                VALUES (:n, CAST(:a AS JSON), :s, 'active', :et)
                """
            ),
            {
                "n": name,
                "a": json.dumps(aliases, ensure_ascii=False),
                "s": is_self,
                "et": entity_type,
            },
        )


async def seed(force: bool = False) -> dict:
    async with async_session_factory() as db:
        required = [
            "geo_monitor_scenes",
            "geo_monitor_questions",
            "geo_monitor_competitors",
            "geo_monitor_probe_results",
            "geo_monitor_runs",
            "site_settings",
        ]
        for t in required:
            if not await _table_exists(db, t):
                raise RuntimeError(f"missing_table:{t}")

        already = (
            await db.execute(
                text("SELECT setting_value FROM site_settings WHERE setting_key = :k"),
                {"k": DEMO_MARKER},
            )
        ).scalar_one_or_none()
        demo_scenes = (
            await db.execute(
                text("SELECT COUNT(*) FROM geo_monitor_scenes WHERE external_id LIKE :p"),
                {"p": f"{DEMO_TAG}%"},
            )
        ).scalar_one()
        if already and int(demo_scenes or 0) > 0 and not force:
            logger.info("already_seeded marker=%s scenes=%s (use --force to reseeds)", already, demo_scenes)
            return {"status": "skipped", "scenes": int(demo_scenes)}

        if force:
            await _clear_demo(db)

        await _upsert_setting(db, "brand_name", BRAND, "monitor")
        await _upsert_setting(db, "brand_aliases", json.dumps(BRAND_ALIASES, ensure_ascii=False), "monitor")
        await _upsert_setting(db, "monitor_platforms", ",".join(PLATFORMS), "monitor")

        # competitors (brand + product)
        for name, aliases, is_self in COMPETITORS:
            await _upsert_competitor(db, name, aliases, is_self, entity_type="brand")
        for name, aliases, is_self in PRODUCTS:
            await _upsert_competitor(db, name, aliases, is_self, entity_type="product")
        logger.info("competitors_upserted brands=%s products=%s", len(COMPETITORS), len(PRODUCTS))

        scene_id_by_suffix: dict[str, int] = {}
        for persona, scene_name, intent, weight, suffix in SCENES:
            ext = f"{DEMO_TAG}{suffix}"
            existing = (
                await db.execute(
                    text("SELECT id FROM geo_monitor_scenes WHERE external_id = :e LIMIT 1"),
                    {"e": ext},
                )
            ).first()
            if existing:
                sid = int(existing[0])
                await db.execute(
                    text(
                        """
                        UPDATE geo_monitor_scenes
                        SET persona=:p, scene_name=:sn, intent=:i, weight_pct=:w, status='active'
                        WHERE id=:id
                        """
                    ),
                    {"p": persona, "sn": scene_name, "i": intent, "w": weight, "id": sid},
                )
            else:
                sid = int(
                    (
                        await db.execute(
                            text(
                                """
                                INSERT INTO geo_monitor_scenes
                                    (persona, scene_name, intent, weight_pct, status, external_id, gap_rate, gap_priority)
                                VALUES (:p, :sn, :i, :w, 'active', :e, 0, 'covered')
                                RETURNING id
                                """
                            ),
                            {"p": persona, "sn": scene_name, "i": intent, "w": weight, "e": ext},
                        )
                    ).scalar_one()
                )
            scene_id_by_suffix[suffix] = sid
        logger.info("scenes_ready %s", scene_id_by_suffix)

        question_ids: list[tuple[str, int, str]] = []  # suffix, qid, text
        for suffix, items in QUESTIONS.items():
            sid = scene_id_by_suffix[suffix]
            for qtext, qtype, priority, intent_type in items:
                exist_q = (
                    await db.execute(
                        text(
                            """
                            SELECT id FROM geo_monitor_questions
                            WHERE scene_id = :sid AND question_text = :q LIMIT 1
                            """
                        ),
                        {"sid": sid, "q": qtext},
                    )
                ).first()
                if exist_q:
                    qid = int(exist_q[0])
                    await db.execute(
                        text(
                            """
                            UPDATE geo_monitor_questions
                            SET priority=:p, status='active', query_type=:qt, intent_type=:it,
                                competitor_brands=CAST(:cb AS JSON)
                            WHERE id=:id
                            """
                        ),
                        {
                            "p": priority,
                            "qt": qtype,
                            "it": intent_type,
                            "cb": json.dumps(["比亚迪", "理想", "小鹏"], ensure_ascii=False),
                            "id": qid,
                        },
                    )
                else:
                    qid = int(
                        (
                            await db.execute(
                                text(
                                    """
                                    INSERT INTO geo_monitor_questions
                                        (question_text, priority, status, scene_id, query_type,
                                         competitor_brands, intent_type)
                                    VALUES (:q, :p, 'active', :sid, :qt, CAST(:cb AS JSON), :it)
                                    RETURNING id
                                    """
                                ),
                                {
                                    "q": qtext,
                                    "p": priority,
                                    "sid": sid,
                                    "qt": qtype,
                                    "cb": json.dumps(["比亚迪", "理想", "小鹏"], ensure_ascii=False),
                                    "it": intent_type,
                                },
                            )
                        ).scalar_one()
                    )
                question_ids.append((suffix, qid, qtext))
        logger.info("questions_ready n=%s", len(question_ids))

        run_id = int(
            (
                await db.execute(
                    text(
                        """
                        INSERT INTO geo_monitor_runs
                            (status, platform, question_count, probe_count, started_at, completed_at)
                        VALUES ('completed', 'all', :qc, 0, :st, :ct)
                        RETURNING id
                        """
                    ),
                    {
                        "qc": len(question_ids),
                        "st": datetime.utcnow() - timedelta(hours=1),
                        "ct": datetime.utcnow(),
                    },
                )
            ).scalar_one()
        )

        probe_count = 0
        for suffix, qid, qtext in question_ids:
            ranks = RANK_BY_SCENE[suffix]
            thinking = THINKING[suffix]
            comps = COMP_MENTIONS[suffix]
            hosts = SOURCES[suffix]
            for plat in PLATFORMS:
                rank = ranks.get(plat)
                mentioned = rank is not None
                score = calc_ranking_score(rank)
                snippet = (
                    f"【演示探针】针对「{qtext[:40]}…」，平台 {plat} "
                    + (f"将{BRAND}排在第 {rank} 位；竞品对比涉及 {', '.join(comps)}。" if mentioned else f"未明确提及{BRAND}。")
                )
                row = (
                    await db.execute(
                        text(
                            """
                            INSERT INTO geo_monitor_probe_results
                                (run_id, question_id, platform, brand_rank, mentioned, snippet, engine,
                                 ranking_score, sentiment, competitor_mentions,
                                 rank_method, evidence_level, match_type, parser_version,
                                 thinking_text, thinking_ms, keywords, source_hosts, metric_kind)
                            VALUES
                                (:run_id, :qid, :platform, :rank, :mentioned, :snippet, 'api',
                                 :score, CAST(:sentiment AS JSON), CAST(:comps AS JSON),
                                 'list_order', 'L1', 'demo', 'v2',
                                 :thinking, 1200, CAST(:keywords AS JSON), CAST(:hosts AS JSON), 'open_api')
                            RETURNING id
                            """
                        ),
                        {
                            "run_id": run_id,
                            "qid": qid,
                            "platform": plat,
                            "rank": rank,
                            "mentioned": mentioned,
                            "snippet": snippet,
                            "score": score,
                            "sentiment": json.dumps({"label": "neutral", "score": 0.5}, ensure_ascii=False),
                            "comps": json.dumps(comps, ensure_ascii=False),
                            "thinking": thinking,
                            "keywords": json.dumps(
                                ["选型对比", "能力边界", "官方口径", suffix],
                                ensure_ascii=False,
                            ),
                            "hosts": json.dumps(hosts, ensure_ascii=False),
                        },
                    )
                ).first()
                probe_id = int(row[0]) if row else None
                probe_count += 1
                if probe_id and await _table_exists(db, "geo_monitor_probe_citations"):
                    for pos, host in enumerate(hosts[:3], start=1):
                        await db.execute(
                            text(
                                """
                                INSERT INTO geo_monitor_probe_citations
                                    (probe_result_id, title, url, position, evidence_level, source)
                                VALUES (:pid, :title, :url, :pos, 'L1', 'demo')
                                """
                            ),
                            {
                                "pid": probe_id,
                                "title": f"{host} · {suffix} 参考页",
                                "url": f"https://{host}/demo/{suffix}",
                                "pos": pos,
                            },
                        )

        await db.execute(
            text("UPDATE geo_monitor_runs SET probe_count = :n WHERE id = :id"),
            {"n": probe_count, "id": run_id},
        )
        logger.info("probes_inserted run_id=%s probe_count=%s", run_id, probe_count)

        # 缺口：无 KB 支撑时默认 unsupported → 高缺口，便于挖主题
        from app.services.geoeval.scene_gap_analyzer import compute_all_scene_gaps
        from app.services.geoeval.monitor_probe import aggregate_monitor_snapshot

        gaps = await compute_all_scene_gaps(db)
        kpis = await aggregate_monitor_snapshot(db)
        logger.info(
            "gaps_kpis high=%s top3=%s mention=%s probes=%s",
            gaps.get("high_gap_count"),
            kpis.get("top3_pct"),
            kpis.get("mention_rate_pct"),
            kpis.get("probe_count"),
        )

        # 高缺口场景生成一主题草稿，便于「挖掘主题」页有样例
        theme_id = None
        high = [
            s
            for s in (gaps.get("scenes") or [])
            if s.get("gap_priority") == "high" and int(s.get("scene_id") or 0) in scene_id_by_suffix.values()
        ]
        if high:
            from app.services.geoeval.theme_service import create_theme_from_scene

            try:
                mined = await create_theme_from_scene(db, int(high[0]["scene_id"]))
                theme = mined.get("theme") or {}
                theme_id = theme.get("id")
                if theme_id:
                    await db.execute(
                        text(
                            """
                            UPDATE geo_themes
                            SET title = :t,
                                meta = CAST(:m AS JSON)
                            WHERE id = :id
                            """
                        ),
                        {
                            "t": f"【演示】{theme.get('title') or '场景内容战役'}"[:300],
                            "m": json.dumps(
                                {
                                    **(theme.get("meta") if isinstance(theme.get("meta"), dict) else {}),
                                    "source": "strategy_demo",
                                },
                                ensure_ascii=False,
                            ),
                            "id": int(theme_id),
                        },
                    )
                logger.info("theme_draft_created theme_id=%s scene_id=%s", theme_id, high[0]["scene_id"])
            except Exception as exc:
                logger.warning("theme_draft_skip err=%s", exc)
                # 若草稿已落库但后处理失败，尽量回读最新草稿
                try:
                    row = (
                        await db.execute(
                            text(
                                """
                                SELECT id FROM geo_themes
                                WHERE status = 'draft'
                                ORDER BY id DESC LIMIT 1
                                """
                            )
                        )
                    ).first()
                    if row:
                        theme_id = int(row[0])
                except Exception:
                    pass

        await _upsert_setting(db, DEMO_MARKER, datetime.utcnow().isoformat(timespec="seconds"), "demo")
        await db.commit()

        summary = {
            "status": "ok",
            "brand": BRAND,
            "scenes": len(scene_id_by_suffix),
            "questions": len(question_ids),
            "run_id": run_id,
            "probe_count": probe_count,
            "high_gap_count": gaps.get("high_gap_count"),
            "top3_pct": kpis.get("top3_pct"),
            "theme_id": theme_id,
        }
        logger.info("seed_done %s", summary)
        return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed L1 strategy demo data")
    parser.add_argument("--force", action="store_true", help="清除旧 demo 后重种")
    args = parser.parse_args()
    try:
        result = asyncio.run(seed(force=args.force))
    except Exception as exc:
        logger.exception("seed_failed err=%s", exc)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in ("ok", "skipped") else 1


if __name__ == "__main__":
    raise SystemExit(main())
