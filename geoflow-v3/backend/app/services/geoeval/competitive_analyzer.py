"""竞品对标矩阵 — 从探针 competitor_mentions 聚合真实可见性。"""

import json
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists
from app.services.geoeval.entity_classifier import filter_matrix_by_entity, infer_entity_type, matrix_competitor_names
from app.services.geoeval.monitor_probe import aggregate_probe_kpis, load_brand_keywords

logger = logging.getLogger(__name__)

TJG_PROVIDER = "tjg_youzan"


def _recalc_matrix_stats(matrix: list[dict], fallback_self_visibility: float = 0) -> tuple[float, float]:
    all_vis = [float(b.get("visibility_pct") or 0) for row in matrix for b in row.get("brands") or []]
    leader_visibility = max(all_vis) if all_vis else 0.0
    self_visibility = next(
        (float(b.get("visibility_pct") or 0) for row in matrix for b in row.get("brands") or [] if b.get("is_self")),
        fallback_self_visibility,
    )
    return self_visibility, round(leader_visibility - self_visibility, 1)


async def load_tjg_layer_snapshot(db: AsyncSession, layer: str = "brand") -> dict | None:
    """读取最新 TJG 导入报告中的层级快照（矩阵 + KPI）。"""
    if not await _table_exists(db, "geo_visibility_reports"):
        return None
    row = (
        await db.execute(
            text(
                """
                SELECT sections FROM geo_visibility_reports
                WHERE sections->'source'->>'provider' = :provider
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"provider": TJG_PROVIDER},
        )
    ).first()
    if not row or not row[0]:
        return None

    sections = row[0]
    if isinstance(sections, str):
        try:
            sections = json.loads(sections)
        except json.JSONDecodeError:
            return None
    if not isinstance(sections, dict):
        return None

    layer_data = sections.get(layer) or {}
    matrix_rows = filter_matrix_by_entity(layer_data.get("competitor_matrix") or [], layer)
    if not matrix_rows:
        return None

    kpis = layer_data.get("kpis") or {}
    all_vis = [float(b.get("visibility_pct") or 0) for row in matrix_rows for b in row.get("brands") or []]
    leader_visibility = max(all_vis) if all_vis else 0.0
    self_visibility = next(
        (float(b.get("visibility_pct") or 0) for row in matrix_rows for b in row.get("brands") or [] if b.get("is_self")),
        float(kpis.get("visibility_pct") or 0),
    )
    competitors = matrix_competitor_names(matrix_rows)

    logger.info(
        "tjg_layer_snapshot_loaded layer=%s platforms=%s competitors=%s self_visibility=%s",
        layer,
        len(matrix_rows),
        len(competitors),
        self_visibility,
    )
    return {
        "matrix": matrix_rows,
        "self_visibility_pct": self_visibility,
        "gap_vs_leader": round(leader_visibility - self_visibility, 1),
        "competitors": competitors,
        "kpis": kpis,
        "source": "tjg_import",
    }


async def load_competitor_brands(db: AsyncSession, entity_type: str = "brand") -> list[dict]:
    if not await _table_exists(db, "geo_monitor_competitors"):
        return []
    has_type = False
    try:
        cols = (
            await db.execute(
                text(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'geo_monitor_competitors' AND column_name = 'entity_type'
                    """
                )
            )
        ).first()
        has_type = bool(cols)
    except Exception:
        pass

    sql = (
        """
        SELECT brand_name, aliases, is_self FROM geo_monitor_competitors
        WHERE status = 'active' {type_filter}
        ORDER BY is_self DESC, id ASC
        """
    )
    type_filter = f"AND entity_type = '{entity_type}'" if has_type else ""
    if entity_type == "product" and not has_type:
        return []

    rows = (await db.execute(text(sql.format(type_filter=type_filter)))).all()
    items = [
        {"brand_name": str(r[0]), "aliases": r[1] or [], "is_self": bool(r[2])}
        for r in rows
        if infer_entity_type(str(r[0])) == entity_type
    ]
    return items


def _normalize_competitor_names(competitors: list[dict]) -> dict[str, set[str]]:
    """brand_name -> set of match tokens (name + aliases, lowercased)."""
    mapping: dict[str, set[str]] = {}
    for comp in competitors:
        name = str(comp["brand_name"])
        tokens = {name.lower()}
        for alias in comp.get("aliases") or []:
            if alias:
                tokens.add(str(alias).lower())
        mapping[name] = tokens
    return mapping


async def _aggregate_competitor_visibility(
    db: AsyncSession,
    competitors: list[dict],
    query_type: str | None = None,
) -> dict[str, dict[str, dict]]:
    """
    Returns: { platform: { brand_name: { visibility_pct, weighted_rank_score, mentions, total } } }
    """
    if not await _table_exists(db, "geo_monitor_probe_results"):
        return {}

    name_tokens = _normalize_competitor_names(competitors)
    self_names = {c["brand_name"] for c in competitors if c.get("is_self")}

    qfilter = ""
    params: dict = {}
    join_sql = ""
    if query_type and await _table_exists(db, "geo_monitor_questions"):
        join_sql = "JOIN geo_monitor_questions mq ON mq.id = pr.question_id"
        qfilter = "AND COALESCE(mq.query_type, 'brand') = :qt"
        params["qt"] = query_type

    rows = (
        await db.execute(
            text(
                f"""
                SELECT pr.platform, pr.mentioned, pr.brand_rank, pr.ranking_score,
                       pr.competitor_mentions, pr.snippet
                FROM geo_monitor_probe_results pr
                {join_sql}
                WHERE 1=1 {qfilter}
                """
            ),
            params,
        )
    ).all()

    plat_stats: dict[str, dict[str, dict]] = {}

    for platform, mentioned, brand_rank, ranking_score, comp_mentions_raw, snippet in rows:
        plat = str(platform)
        if plat not in plat_stats:
            plat_stats[plat] = {name: {"mentions": 0, "total": 0, "rank_scores": []} for name in name_tokens}

        for name in name_tokens:
            plat_stats[plat][name]["total"] += 1

        comp_list: list = []
        if comp_mentions_raw:
            if isinstance(comp_mentions_raw, list):
                comp_list = comp_mentions_raw
            elif isinstance(comp_mentions_raw, str):
                try:
                    comp_list = json.loads(comp_mentions_raw)
                except json.JSONDecodeError:
                    comp_list = []

        snippet_lower = (snippet or "").lower()

        for brand_name, tokens in name_tokens.items():
            is_self = brand_name in self_names
            hit = False
            if is_self and mentioned:
                hit = True
                if brand_rank and ranking_score:
                    plat_stats[plat][brand_name]["rank_scores"].append(float(ranking_score))
            elif not is_self:
                if any(t in snippet_lower for t in tokens):
                    hit = True
                elif any(
                    any(t in str(c).lower() for t in tokens)
                    for c in comp_list
                ):
                    hit = True
            if hit:
                plat_stats[plat][brand_name]["mentions"] += 1

    result: dict[str, dict[str, dict]] = {}
    for plat, brands in plat_stats.items():
        result[plat] = {}
        for name, stat in brands.items():
            total = stat["total"] or 1
            ranks = stat["rank_scores"]
            result[plat][name] = {
                "mentions": stat["mentions"],
                "total": stat["total"],
                "visibility_pct": round(stat["mentions"] / total * 100, 1),
                "weighted_rank_score": round(sum(ranks) / len(ranks), 2) if ranks else None,
            }
    return result


async def build_competitor_matrix(db: AsyncSession, query_type: str | None = None) -> dict:
    competitors = await load_competitor_brands(db, entity_type="brand")
    kpis = await aggregate_probe_kpis(db, query_type=query_type)
    self_brands = await load_brand_keywords(db)
    self_name = self_brands[0] if self_brands else "自有品牌"

    if not competitors:
        competitors = [{"brand_name": self_name, "aliases": self_brands[1:], "is_self": True}]

    vis_by_plat = await _aggregate_competitor_visibility(db, competitors, query_type=query_type)
    platform_matrix = kpis.get("platform_matrix") or []

    if not platform_matrix and vis_by_plat:
        platform_matrix = [{"platform": p} for p in vis_by_plat.keys()]

    matrix = []
    for plat in platform_matrix:
        plat_key = str(plat["platform"])
        plat_vis = vis_by_plat.get(plat_key, {})
        brands_row = []
        for comp in competitors:
            name = comp["brand_name"]
            stat = plat_vis.get(name, {"visibility_pct": 0.0, "weighted_rank_score": None})
            brands_row.append(
                {
                    "name": name,
                    "is_self": comp.get("is_self", False),
                    "visibility_pct": stat.get("visibility_pct", 0.0),
                    "weighted_rank_score": stat.get("weighted_rank_score"),
                }
            )
        matrix.append({"platform": plat_key, "brands": brands_row})

    all_vis = [b["visibility_pct"] for row in matrix for b in row["brands"]]
    leader_visibility = max(all_vis) if all_vis else 0
    self_visibility = next(
        (b["visibility_pct"] for row in matrix for b in row["brands"] if b.get("is_self")),
        kpis.get("visibility_pct", 0),
    )
    gap_vs_leader = round(leader_visibility - self_visibility, 1)

    if not matrix:
        tjg = await load_tjg_layer_snapshot(db, layer="brand" if query_type != "product" else "product")
        if tjg:
            logger.info("competitor_matrix_tjg_fallback query_type=%s", query_type)
            return {
                "matrix": tjg["matrix"],
                "self_visibility_pct": tjg["self_visibility_pct"],
                "gap_vs_leader": tjg["gap_vs_leader"],
                "competitors": tjg["competitors"],
                "source": tjg.get("source"),
            }

    matrix = filter_matrix_by_entity(matrix, "brand")
    self_visibility, gap_vs_leader = _recalc_matrix_stats(matrix, float(kpis.get("visibility_pct") or 0))

    logger.info(
        "competitor_matrix_built query_type=%s platforms=%s self_visibility=%s gap=%s",
        query_type,
        len(matrix),
        self_visibility,
        gap_vs_leader,
    )
    return {
        "matrix": matrix,
        "self_visibility_pct": self_visibility,
        "gap_vs_leader": gap_vs_leader,
        "competitors": [c["brand_name"] for c in competitors],
    }


async def build_product_competitor_matrix(db: AsyncSession) -> dict:
    tjg = await load_tjg_layer_snapshot(db, layer="product")
    if tjg:
        logger.info("product_competitor_matrix_tjg_primary")
        return {
            "matrix": tjg["matrix"],
            "self_visibility_pct": tjg["self_visibility_pct"],
            "gap_vs_leader": tjg["gap_vs_leader"],
            "competitors": tjg["competitors"],
            "self_product": next(
                (b["name"] for row in tjg["matrix"] for b in row.get("brands") or [] if b.get("is_self")),
                None,
            ),
            "source": tjg.get("source"),
        }

    products = await load_competitor_brands(db, entity_type="product")
    kpis = await aggregate_probe_kpis(db, query_type="product")
    self_item = next((p for p in products if p.get("is_self")), None)
    if not products:
        return {
            "matrix": [],
            "self_visibility_pct": float(kpis.get("visibility_pct") or 0),
            "gap_vs_leader": 0,
            "competitors": [],
            "self_product": None,
        }

    vis_by_plat = await _aggregate_competitor_visibility(db, products, query_type="product")
    platform_matrix = kpis.get("platform_matrix") or []
    if not platform_matrix and vis_by_plat:
        platform_matrix = [{"platform": p} for p in vis_by_plat.keys()]

    matrix = []
    for plat in platform_matrix:
        plat_key = str(plat["platform"])
        plat_vis = vis_by_plat.get(plat_key, {})
        brands_row = []
        for comp in products:
            name = comp["brand_name"]
            stat = plat_vis.get(name, {"visibility_pct": 0.0, "weighted_rank_score": None})
            brands_row.append(
                {
                    "name": name,
                    "is_self": comp.get("is_self", False),
                    "visibility_pct": stat.get("visibility_pct", 0.0),
                    "weighted_rank_score": stat.get("weighted_rank_score"),
                }
            )
        matrix.append({"platform": plat_key, "brands": brands_row})

    matrix = filter_matrix_by_entity(matrix, "product")
    self_visibility, gap_vs_leader = _recalc_matrix_stats(matrix, float(kpis.get("visibility_pct") or 0))
    competitor_names = matrix_competitor_names(matrix) or [c["brand_name"] for c in products]

    return {
        "matrix": matrix,
        "self_visibility_pct": self_visibility,
        "gap_vs_leader": gap_vs_leader,
        "competitors": competitor_names,
        "self_product": self_item["brand_name"] if self_item else None,
    }


async def compute_optimization_potential(current: float, benchmark: float) -> dict:
    gap = benchmark - current
    gap_pct = (gap / benchmark * 100) if benchmark > 0 else 0
    lift = ((benchmark - current) / current * 100) if current > 0 else 0
    difficulty = min(5, max(1, int(lift / 20) + 1)) if lift > 0 else 1
    return {
        "gap": round(gap, 1),
        "gap_percentage": round(gap_pct, 1),
        "lift_needed": round(lift, 1),
        "difficulty_score": difficulty,
    }
