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
from app.services.geoeval.competitive_analyzer import build_competitor_matrix, compute_optimization_potential
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
        items.append(
            f"[{r.get('status')}] {r.get('scene_name') or r.get('scene_id')} "
            f"基线 {r.get('baseline_visibility_pct')}% → 复测 {r.get('post_visibility_pct')}% "
            f"(Δ {r.get('delta_visibility_pct')}pp) task={r.get('task_id')}"
        )
    for r in rem_items:
        if r.get("status") == "completed":
            continue
        items.append(
            f"[进行中] {r.get('scene_name') or r.get('scene_id')} status={r.get('status')} "
            f"baseline={r.get('baseline_visibility_pct')}% rescan_after={r.get('rescan_after')}"
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
            vis = cell.get("visibility_pct", 0)
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

    kpis = await aggregate_probe_kpis(db)
    brand_kpis = await aggregate_probe_kpis(db, query_type="brand")
    product_kpis = await aggregate_probe_kpis(db, query_type="product")
    brand_panel = await build_brand_panel(db)
    product_panel = await build_product_panel(db)
    matrix = brand_panel["competitor_matrix"]
    gaps = await compute_all_scene_gaps(db)
    optimization = await build_optimization_panel(db)
    difficulty = await assess_difficulty(db)
    await generate_monitor_insights(db)
    insights = optimization.get("insights") or []

    opt = await compute_optimization_potential(
        float(brand_kpis.get("visibility_pct") or 0),
        float(matrix.get("self_visibility_pct") or 0) + float(matrix.get("gap_vs_leader") or 0),
    )
    high_scenes = [s for s in gaps.get("scenes", []) if s.get("gap_priority") == "high"][:3]

    from app.services.geoeval.remediation_service import list_remediations
    from app.services.geoeval.gweb_alignment_service import compute_gweb_alignment

    remediations = await list_remediations(db, limit=10)
    rem_items = remediations.get("items") or []
    completed_lifts = [r for r in rem_items if r.get("status") == "completed"]
    alignment = await compute_gweb_alignment(db)

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

    sections = {
        "cover": {
            "title": "封面",
            "items": [f"品牌：{brand_name}", f"数据窗口：{period_start} ~ {period_end}"],
        },
        "overview": {
            "title": "数据概况",
            "html": (
                f"<div class='kpi'>平台数 <strong>{platform_count}</strong></div>"
                f"<div class='kpi'>品牌问题 <strong>{qstats['brand']}</strong> 题</div>"
                f"<div class='kpi'>产品问题 <strong>{qstats['product']}</strong> 题</div>"
                f"<div class='kpi'>探针总数 <strong>{kpis.get('probe_count', 0)}</strong></div>"
            ),
        },
        "brand": {
            "title": "品牌现状",
            "html": (
                f"<div class='kpi'>可见性 <strong>{brand_kpis.get('visibility_pct')}%</strong></div>"
                f"<div class='kpi'>加权排名 <strong>{brand_kpis.get('weighted_rank_score') or '—'}</strong></div>"
                f"<div class='kpi'>好感度 <strong>{brand_kpis.get('sentiment_score') or '—'}%</strong></div>"
                f"<p>与领先者差距 {matrix.get('gap_vs_leader')}pp</p>"
                + _render_matrix_html(matrix.get("matrix") or [], "品牌竞品矩阵")
            ),
            "items": [f"{i.get('title')}：{i.get('body')}" for i in insights if i.get("insight_type") != "core_scene"][:3],
        },
        "product": {
            "title": "产品现状 · 场景缺口",
            "html": (
                f"<div class='kpi'>可见性 <strong>{product_kpis.get('visibility_pct')}%</strong></div>"
                f"<div class='kpi'>加权排名 <strong>{product_kpis.get('weighted_rank_score') or '—'}</strong></div>"
                f"<div class='kpi'>好感度 <strong>{product_kpis.get('sentiment_score') or '—'}%</strong></div>"
            ),
            "items": [
                f"{s.get('scene_name')} — 缺口率 {float(s.get('gap_rate', 0))*100:.1f}% [{s.get('gap_priority')}]"
                for s in sorted(gaps.get("scenes", []), key=lambda x: x.get("gap_rate", 0), reverse=True)[:8]
            ]
            or ["暂无场景数据"],
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
                f"优化提升需 {opt.get('lift_needed')}%",
            ],
        },
        "closed_loop": {
            "title": "闭环验证 · 补缺 Lift 与数据质量",
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
            ),
            "items": _closed_loop_items(rem_items, completed_lifts, alignment, high_scenes),
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
