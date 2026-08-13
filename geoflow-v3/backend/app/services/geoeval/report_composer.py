"""AIVIS 诊断报告生成 — 六章节 HTML + JSON sections。"""

import logging
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.admin.aivis_service import build_brand_panel, build_product_panel
from app.services.admin.production_service import _table_exists
from app.services.geoeval.aivis_analyzers import assess_difficulty, build_optimization_panel
from app.services.geoeval.competitive_analyzer import build_competitor_matrix, compute_optimization_potential  # noqa: F401 — matrix used for north-star
from app.services.geoeval.insight_generator import generate_monitor_insights
from app.services.geoeval.monitor_probe import aggregate_probe_kpis, load_brand_keywords
from app.services.geoeval.scene_gap_analyzer import compute_all_scene_gaps

logger = logging.getLogger(__name__)

PLATFORM_LABELS = {
    "doubao": "豆包",
    "deepseek": "DeepSeek",
    "tongyi": "通义千问",
    "yuanbao": "元宝",
    "wenxin": "文心一言",
    "kimi": "Kimi",
}


def _html_escape(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _closed_loop_items(
    rem_items: list[dict],
    completed_lifts: list[dict],
    alignment: dict,
    high_scenes: list[dict],
) -> list[str]:
    items: list[str] = []
    for r in completed_lifts[:8]:
        top3_bit = ""
        if r.get("delta_top3_pp") is not None:
            top3_bit = (
                f" · Top3 {r.get('baseline_top3_pct')}%→{r.get('post_top3_pct')}%"
                f"(Δ {r.get('delta_top3_pp')}pp)"
            )
        items.append(
            f"[{r.get('status')}] {r.get('scene_name') or r.get('scene_id')} "
            f"可见性 {r.get('baseline_visibility_pct')}% → {r.get('post_visibility_pct')}% "
            f"(Δ {r.get('delta_visibility_pct')}pp){top3_bit} task={r.get('task_id')}"
        )
    for r in rem_items:
        if r.get("status") == "completed":
            continue
        items.append(
            f"[进行中] {r.get('scene_name') or r.get('scene_id')} status={r.get('status')} "
            f"baseline={r.get('baseline_visibility_pct')}% top3={r.get('baseline_top3_pct')} "
            f"rescan_after={r.get('rescan_after')}"
        )
        if len([x for x in items if x.startswith("[进行中]")]) >= 5:
            break
    if not rem_items:
        items.append("暂无补缺实验记录：请从场景缺口「一键创建 Task」启动闭环")
    items.append(
        f"Gweb 对齐：匹配 {alignment.get('matched_count')} / "
        f"仅远端 {alignment.get('only_gweb_count')} / 仅本地 {alignment.get('only_local_count')} "
        f"(fetch={alignment.get('status')})"
    )
    for s in high_scenes:
        items.append(f"高优缺口场景：{s.get('scene_name')} ({float(s.get('gap_rate', 0))*100:.0f}%)")
    return items


def _render_matrix_html(matrix: list, title: str = "竞品对标矩阵") -> str:
    if not matrix:
        return "<p>暂无矩阵数据</p>"
    brands: list[str] = []
    for row in matrix:
        for b in row.get("brands") or []:
            if b["name"] not in brands:
                brands.append(b["name"])
    parts = [f"<h3>{_html_escape(title)}</h3><table><tr><th>平台</th>"]
    parts.extend(f"<th>{_html_escape(b)}</th>" for b in brands)
    parts.append("</tr>")
    for row in matrix:
        parts.append(f"<tr><td>{_html_escape(PLATFORM_LABELS.get(row['platform'], row['platform']))}</td>")
        brand_map = {b["name"]: b for b in row.get("brands") or []}
        for bname in brands:
            cell = brand_map.get(bname, {})
            top3 = cell.get("top3_pct")
            vis = cell.get("visibility_pct", 0)
            if top3 is not None:
                parts.append(f"<td>Top3 {top3}% <small>可见 {vis}%</small></td>")
            else:
                rank = cell.get("weighted_rank_score")
                parts.append(f"<td>{vis}%{f' / {rank}' if rank else ''}</td>")
        parts.append("</tr>")
    parts.append("</table>")
    return "".join(parts)


def _render_report_html(title: str, sections: dict) -> str:
    parts = [
        "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>",
        f"<title>{_html_escape(title)}</title>",
        "<style>body{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;color:#1a1a1a}",
        "h1{color:#5b21b6}h2{color:#6d28d9;margin-top:2rem;border-bottom:1px solid #e5e7eb;padding-bottom:.5rem}",
        "table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{border:1px solid #e5e7eb;padding:.5rem;text-align:left;font-size:.9rem}",
        "th{background:#f5f3ff}.badge-high{background:#fecaca;padding:.2rem .5rem;border-radius:4px}",
        ".badge-medium{background:#fef08a;padding:.2rem .5rem;border-radius:4px}.kpi{display:inline-block;margin:.5rem 1rem .5rem 0;padding:.75rem 1rem;background:#f5f3ff;border-radius:8px}",
        ".kpi strong{font-size:1.4rem;color:#5b21b6}</style></head><body>",
        f"<h1>{_html_escape(title)}</h1>",
    ]
    for key, block in sections.items():
        parts.append(f"<h2>{_html_escape(block.get('title', key))}</h2>")
        if block.get("html"):
            parts.append(block["html"])
        elif block.get("items"):
            parts.append("<ul>")
            for item in block["items"]:
                parts.append(f"<li>{_html_escape(str(item))}</li>")
            parts.append("</ul>")
    parts.append("</body></html>")
    return "".join(parts)


async def compose_visibility_report(db: AsyncSession, period_days: int = 7) -> dict:
    if not await _table_exists(db, "geo_visibility_reports"):
        return {"status": "skipped", "reason": "reports_table_missing"}

    brands = await load_brand_keywords(db)
    brand_name = brands[0] if brands else get_settings().app_name
    period_end = date.today()
    period_start = period_end - timedelta(days=period_days)

    kpis = await aggregate_probe_kpis(db, north_star=True)
    brand_kpis = await aggregate_probe_kpis(db, query_type="brand", north_star=True)
    product_kpis = await aggregate_probe_kpis(db, query_type="product", north_star=True)
    brand_panel = await build_brand_panel(db)
    product_panel = await build_product_panel(db)
    matrix = await build_competitor_matrix(db, north_star=True)
    gaps = await compute_all_scene_gaps(db)
    optimization = await build_optimization_panel(db)
    difficulty = await assess_difficulty(db)
    await generate_monitor_insights(db)
    insights = optimization.get("insights") or []

    from app.services.geoeval.quality_metrics_service import compute_quality_gates
    from app.services.geoeval.source_metrics_service import compute_source_shares

    quality = await compute_quality_gates(db)
    source = await compute_source_shares(db)

    opt = await compute_optimization_potential(
        float(brand_kpis.get("top3_pct") or brand_kpis.get("visibility_pct") or 0),
        float(matrix.get("leader_top3_pct") or matrix.get("self_visibility_pct") or 0)
        + float(matrix.get("gap_vs_leader_top3_pp") or matrix.get("gap_vs_leader") or 0),
    )
    high_scenes = [s for s in gaps.get("scenes", []) if s.get("gap_priority") == "high"][:3]

    from app.services.geoeval.remediation_service import list_remediations
    from app.services.geoeval.geoweb_alignment_service import compute_geoweb_alignment

    remediations = await list_remediations(db, limit=10)
    rem_items = remediations.get("items") or []
    completed_lifts = [r for r in rem_items if r.get("status") == "completed"]
    alignment = await compute_geoweb_alignment(db)

    from app.services.geoeval.gold_bias_service import compute_gold_bias
    from app.services.admin.geo_eval_settings_service import get_probe_standards

    gold_bias = await compute_gold_bias(db, days=max(period_days, 30))
    probe_std = await get_probe_standards(db)
    gold_footnote = gold_bias.get("footnote") or "金标辅轨：暂无对照样本"
    if not probe_std.get("footnote_on_bias", True):
        gold_footnote = "金标脚注已关闭（probe_footnote_on_bias=false）"

    qstats = {"brand": 0, "product": 0}
    if await _table_exists(db, "geo_monitor_questions"):
        rows = (
            await db.execute(
                text(
                    """
                    SELECT COALESCE(query_type, 'brand'), COUNT(*)
                    FROM geo_monitor_questions WHERE status = 'active'
                    GROUP BY COALESCE(query_type, 'brand')
                    """
                )
            )
        ).all()
        for qt, cnt in rows:
            if str(qt) in qstats:
                qstats[str(qt)] = int(cnt)

    platform_count = len(kpis.get("platform_matrix") or []) or 6
    gate_note = ""
    if quality.get("gate_pass") is False:
        gate_note = "<p><strong>否决：</strong>参数一致率未达 95%，结果层视为未达标。</p>"
    elif quality.get("gate_pass") is None:
        gate_note = "<p>参数一致率待标定（SSOT 或答文样本不足）。</p>"

    sections = {
        "cover": {
            "title": "封面",
            "items": [
                f"品牌：{brand_name}",
                f"数据窗口：{period_start} ~ {period_end}",
                f"口径：{kpis.get('kpi_track', 'open_api')}（Chat API ≠ C 端联网回答）",
                "实体层：L2 技术 IP · 题型子集：对比+决策",
            ],
        },
        "overview": {
            "title": "北极星摘要",
            "html": (
                f"<div class='kpi'>Top3 概率 <strong>{kpis.get('top3_pct') if kpis.get('top3_pct') is not None else '—'}%</strong></div>"
                f"<div class='kpi'>竞品差距 <strong>{matrix.get('gap_vs_leader_top3_pp') if matrix.get('gap_vs_leader_top3_pp') is not None else '—'}pp</strong></div>"
                f"<div class='kpi'>提及率 <strong>{kpis.get('mention_rate_pct', 0)}%</strong></div>"
                f"<div class='kpi'>有效样本 <strong>{kpis.get('valid_sample_n', 0)}</strong></div>"
                f"<div class='kpi'>平台数 <strong>{platform_count}</strong></div>"
                f"<div class='kpi'>品牌/产品题 <strong>{qstats['brand']}/{qstats['product']}</strong></div>"
                f"<p>探针总数 {kpis.get('probe_count', 0)} · API 口径 · 对比+决策子集</p>"
            ),
        },
        "brand": {
            "title": "结果层 · 品牌/技术 IP",
            "html": (
                f"<div class='kpi'>Top3 <strong>{brand_kpis.get('top3_pct') if brand_kpis.get('top3_pct') is not None else '—'}%</strong></div>"
                f"<div class='kpi'>Top5 <strong>{brand_kpis.get('top5_pct') if brand_kpis.get('top5_pct') is not None else '—'}%</strong></div>"
                f"<div class='kpi'>提及率 <strong>{brand_kpis.get('mention_rate_pct', 0)}%</strong></div>"
                f"<div class='kpi'>负向率 <strong>{brand_kpis.get('sentiment_negative_pct') if brand_kpis.get('sentiment_negative_pct') is not None else '—'}%</strong></div>"
                f"<p>相对最强竞品 Top3 差距 {matrix.get('gap_vs_leader_top3_pp')}pp"
                f"（可见性差距 {matrix.get('gap_vs_leader')}pp，过渡保留）</p>"
                + gate_note
                + _render_matrix_html(matrix.get("matrix") or [], "品牌竞品矩阵（Top3）")
            ),
            "items": [f"{i.get('title')}：{i.get('body')}" for i in insights if i.get("insight_type") != "core_scene"][:3],
        },
        "quality": {
            "title": "质量层 · 硬门槛",
            "html": (
                f"<div class='kpi'>参数一致率 <strong>{quality.get('param_consistency_pct') if quality.get('param_consistency_pct') is not None else '—'}%</strong></div>"
                f"<div class='kpi'>门槛 <strong>≥{quality.get('threshold', 95)}%</strong></div>"
                f"<div class='kpi'>归因正确率 <strong>{quality.get('attribution_accuracy_pct') if quality.get('attribution_accuracy_pct') is not None else '—'}%</strong></div>"
                f"<div class='kpi'>门禁 <strong>{'通过' if quality.get('gate_pass') else ('未达标' if quality.get('gate_pass') is False else '待标定')}</strong></div>"
            ),
            "items": [
                f"SSOT 键：{', '.join(quality.get('ssot_keys') or []) or '无'}",
                f"检查样本参数点：{quality.get('checked', 0)}，命中 {quality.get('matched', 0)}",
            ],
        },
        "product": {
            "title": "产品现状 · 场景缺口",
            "html": (
                f"<div class='kpi'>Top3 <strong>{product_kpis.get('top3_pct') if product_kpis.get('top3_pct') is not None else '—'}%</strong></div>"
                f"<div class='kpi'>提及率 <strong>{product_kpis.get('mention_rate_pct', 0)}%</strong></div>"
                f"<div class='kpi'>负向率 <strong>{product_kpis.get('sentiment_negative_pct') if product_kpis.get('sentiment_negative_pct') is not None else '—'}%</strong></div>"
            ),
            "items": [
                f"{s.get('scene_name')} — 缺口率 {float(s.get('gap_rate', 0))*100:.1f}% [{s.get('gap_priority')}]"
                for s in sorted(gaps.get("scenes", []), key=lambda x: x.get("gap_rate", 0), reverse=True)[:8]
            ]
            or ["暂无场景数据"],
        },
        "source": {
            "title": "信源层 · 为什么排不上",
            "html": (
                f"<div class='kpi'>官方信源占比 <strong>{source.get('official_share_pct') if source.get('official_share_pct') is not None else '—'}%</strong></div>"
                f"<div class='kpi'>第三方占比 <strong>{source.get('third_party_share_pct') if source.get('third_party_share_pct') is not None else '—'}%</strong></div>"
                f"<div class='kpi'>目标域名命中 <strong>{source.get('target_domain_hits', 0)}</strong></div>"
                f"<div class='kpi'>引用样本 <strong>{source.get('citation_count', 0)}</strong></div>"
            ),
            "items": [
                f"目标域名：{', '.join(source.get('target_domains') or []) or '未配置 official_domains'}",
                f"证据过滤 L1+：{source.get('evidence_filtered', 0)}/{source.get('evidence_total', 0)}",
            ],
        },
        "strategy": {
            "title": "优化策略",
            "items": [
                optimization["market_opportunity"]["summary"],
                *[f"{p['label']} 推荐分 {p['score']}" for p in optimization.get("platform_recommendations", [])[:3]],
                *[f"高优场景：{s.get('scene_name')} (缺口 {float(s.get('gap_rate', 0))*100:.1f}%)" for s in optimization.get("priority_scenes", [])],
                *[f"{i.get('title')}：{i.get('body')}" for i in insights[:3]],
            ],
        },
        "difficulty": {
            "title": "难度评估",
            "items": [
                f"监管合规 {difficulty['regulatory_compliance']['score']}/5（{difficulty['regulatory_compliance']['label']}）",
                f"市场竞争 {difficulty['market_competition']['score']}/5（{difficulty['market_competition']['label']}）",
                f"实体基础 {difficulty['entity_foundation']['score']}/5（{difficulty['entity_foundation']['label']}）",
                f"综合难度 {difficulty['overall_score']}/5",
                f"Top3 优化提升需 {opt.get('lift_needed')}%",
            ],
        },
        "closed_loop": {
            "title": "闭环验证 · 补缺 Lift（ΔTop3 优先）与数据质量",
            "html": (
                "<div class='kpi'>探针 engine 构成 <strong>"
                + (
                    ", ".join(f"{e['label']}:{e['count']}" for e in (kpis.get("engine_mix") or [])[:4])
                    or "—"
                )
                + "</strong></div>"
                f"<div class='kpi'>Gweb 对齐率 <strong>{alignment.get('alignment_pct', 0)}%</strong></div>"
                f"<div class='kpi'>Gweb 页数 <strong>{alignment.get('gweb_page_count', 0)}</strong></div>"
                f"<div class='kpi'>补缺实验 <strong>{len(rem_items)}</strong></div>"
                f"<p>口径脚注：open_api；{gold_footnote}</p>"
                f"<p>金标样本 n={gold_bias.get('sample_n', 0)} · 提及一致率="
                f"{gold_bias.get('mention_agreement') if gold_bias.get('mention_agreement') is not None else '—'} "
                f"· 平均 rank 偏移={gold_bias.get('mean_rank_delta') if gold_bias.get('mean_rank_delta') is not None else '—'} "
                f"（禁止覆盖 visibility_open_api）</p>"
            ),
            "items": _closed_loop_items(rem_items, completed_lifts, alignment, high_scenes),
            "gold_bias": {
                "sample_n": gold_bias.get("sample_n", 0),
                "mention_agreement": gold_bias.get("mention_agreement"),
                "mean_rank_delta": gold_bias.get("mean_rank_delta"),
                "footnote": gold_footnote,
            },
        },
    }

    title = f"{brand_name} AI 可见性诊断报告 ({period_start} ~ {period_end})"
    html = _render_report_html(title, sections)

    settings = get_settings()
    base = Path(settings.upload_path).parent if settings.upload_path else Path("storage")
    storage = base / "reports"
    storage.mkdir(parents=True, exist_ok=True)
    filename = f"visibility_report_{period_end.isoformat()}.html"
    html_path = storage / filename
    html_path.write_text(html, encoding="utf-8")

    import json

    row = (
        await db.execute(
            text(
                """
                INSERT INTO geo_visibility_reports
                    (title, period_start, period_end, sections, status, html_path)
                VALUES (:title, :ps, :pe, CAST(:sec AS JSON), 'published', :hp)
                RETURNING id
                """
            ),
            {
                "title": title,
                "ps": period_start,
                "pe": period_end,
                "sec": json.dumps(sections, ensure_ascii=False),
                "hp": str(html_path),
            },
        )
    ).first()
    report_id = int(row[0]) if row else None
    logger.info("report_composed id=%s path=%s sections=%s", report_id, html_path, list(sections.keys()))
    return {
        "report_id": report_id,
        "title": title,
        "html_path": str(html_path),
        "sections": sections,
        "kpis": kpis,
        "brand_kpis": brand_kpis,
        "product_kpis": product_kpis,
        "matrix": matrix,
        "difficulty": difficulty,
    }


async def get_visibility_report_detail(db: AsyncSession, report_id: int) -> dict:
    if not await _table_exists(db, "geo_visibility_reports"):
        return {"status": "not_found"}
    row = (
        await db.execute(
            text(
                """
                SELECT id, title, period_start, period_end, sections, status, html_path, created_at
                FROM geo_visibility_reports WHERE id = :id
                """
            ),
            {"id": report_id},
        )
    ).first()
    if not row:
        return {"status": "not_found"}
    html_content = ""
    if row[6]:
        try:
            html_content = Path(str(row[6])).read_text(encoding="utf-8")
        except OSError:
            logger.warning("report_html_read_failed path=%s", row[6])
    return {
        "id": int(row[0]),
        "title": row[1],
        "period_start": str(row[2]) if row[2] else None,
        "period_end": str(row[3]) if row[3] else None,
        "sections": row[4] or {},
        "status": row[5],
        "html_path": row[6],
        "html_content": html_content,
        "created_at": row[7].isoformat() if row[7] else None,
    }
