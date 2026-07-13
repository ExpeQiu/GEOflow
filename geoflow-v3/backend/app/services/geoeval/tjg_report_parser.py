"""加我推荐官（TJG）诊断报告解析与 geo_eval 表导入。"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

PLATFORMS_CN = ("doubao", "deepseek", "tongyi", "yuanbao", "wenxin", "kimi")
RANK_WEIGHTS = {1: 6, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1}


async def _table_exists(db: AsyncSession, table_name: str) -> bool:
    from app.services.admin.production_service import _table_exists as _check

    return await _check(db, table_name)

TJG_PROVIDER = "tjg_youzan"
TJG_API_BASE = "https://tuijian.youzan.com"
TJG_SHARE_PATH_RE = re.compile(r"/share/diagnostic-report/([^/?#]+)")

TJG_PLATFORM_TO_SLUG: dict[str, str] = {
    "豆包": "doubao",
    "DeepSeek": "deepseek",
    "deepseek": "deepseek",
    "通义千问": "tongyi",
    "元宝": "yuanbao",
    "文心一言": "wenxin",
    "Kimi": "kimi",
}

INSIGHT_TYPE_MAP = {
    "竞品超越": "competitor_surpass",
    "核心场景": "core_scene",
    "权威背书": "authority_endorsement",
}


def calc_ranking_score(rank: int | None) -> float:
    if rank is None:
        return 0.0
    return float(RANK_WEIGHTS.get(rank, 0))


@dataclass
class TjgLayerMetrics:
    name: str
    visibility_pct: float
    rank_label: str = ""
    weighted_rank: float = 0.0
    gap_to_leader_pct: float = 0.0
    sentiment_pct: float = 0.0
    recommend_score: int = 0
    mention_count: int = 0
    total_responses: int = 0


@dataclass
class TjgCompetitorRow:
    name: str
    logo_url: str = ""
    is_self: bool = False
    layer: str = "brand"
    summary_visibility: float = 0.0
    summary_rank: float = 0.0
    platform_visibility: dict[str, float] = field(default_factory=dict)
    platform_rank: dict[str, float] = field(default_factory=dict)
    external_id: str = ""


@dataclass
class TjgSceneRow:
    persona: str
    scene_name: str
    intent: str
    weight_pct: float
    visibility_pct: float = 0.0
    gap_priority: str = "covered"
    industry: str = ""
    external_id: str = ""
    optimization_unit_id: str = ""
    article_count: int = 0
    node_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TjgTouchpointTree:
    highlight_node_id: str = ""
    stats: dict[str, Any] = field(default_factory=dict)
    tree: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TjgPromptRow:
    prompt_id: str
    content: str
    query_type: str
    optimization_unit_name: str
    avg_visibility: float
    avg_rank: float
    scene_id: int | None = None
    responses: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TjgParsedReport:
    external_report_id: str
    token: str
    content_source: str
    brand_name: str
    product_name: str
    period_start: date | None
    period_end: date | None
    industry: str
    brand_metrics: TjgLayerMetrics
    product_metrics: TjgLayerMetrics
    brand_competitors: list[TjgCompetitorRow]
    product_competitors: list[TjgCompetitorRow]
    scenes: list[TjgSceneRow]
    prompts: list[TjgPromptRow]
    insights: list[dict[str, Any]]
    strategy: dict[str, Any]
    difficulty: dict[str, Any]
    overview: dict[str, Any]
    sections: dict[str, Any]
    raw: dict[str, Any]
    touchpoint_tree: TjgTouchpointTree = field(default_factory=TjgTouchpointTree)
    brand_platform_breakdown: list[dict[str, Any]] = field(default_factory=list)
    product_platform_breakdown: list[dict[str, Any]] = field(default_factory=list)
    brand_visibility_trend: list[dict[str, Any]] = field(default_factory=list)
    product_visibility_trend: list[dict[str, Any]] = field(default_factory=list)


def extract_share_token(share_url: str) -> str:
    match = TJG_SHARE_PATH_RE.search(share_url.strip())
    if not match:
        raise ValueError("invalid_tjg_share_url")
    return match.group(1)


def normalize_tjg_platform(platform: str) -> str:
    slug = TJG_PLATFORM_TO_SLUG.get(platform.strip(), platform.strip().lower())
    return slug if slug in PLATFORMS_CN else slug


def _parse_competitor_mentions(raw: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for entry in raw or []:
        if isinstance(entry, dict):
            items.append(entry)
            continue
        if isinstance(entry, str):
            try:
                parsed = json.loads(entry)
                if isinstance(parsed, dict):
                    items.append(parsed)
            except json.JSONDecodeError:
                if entry.strip():
                    items.append({"name": entry.strip()})
    return items


def _build_platform_breakdown(platform_data: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in platform_data or []:
        label = str(item.get("platform") or "")
        rows.append(
            {
                "platform": normalize_tjg_platform(label),
                "label": label,
                "visibility_pct": float(item.get("current") or 0),
                "rank_label": str(item.get("rank") or ""),
                "leader_visibility_pct": float(item.get("top1") or 0),
                "leader_brand": str(item.get("top1_brand") or ""),
            }
        )
    return rows


def _build_visibility_trend(visibility_dto: dict[str, Any] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for plat in (visibility_dto or {}).get("platforms") or []:
        label = str(plat.get("platform") or "")
        summary = plat.get("summary") or {}
        daily = [
            {
                "date": str(d.get("date") or ""),
                "visibility_pct": float(d.get("visibility") or 0),
                "avg_rank": float(d.get("avg_rank") or 0),
            }
            for d in plat.get("daily") or []
        ]
        rows.append(
            {
                "platform": normalize_tjg_platform(label),
                "label": label,
                "avg_visibility": float(summary.get("avg_visibility") or 0),
                "avg_rank": float(summary.get("avg_rank") or 0),
                "daily": daily,
            }
        )
    return rows


def _extract_touchpoint_tree(product_metrics: dict[str, Any]) -> TjgTouchpointTree:
    touchpoint = product_metrics.get("touchpointTree") or {}
    return TjgTouchpointTree(
        highlight_node_id=str(touchpoint.get("highlightNodeId") or ""),
        stats=dict(touchpoint.get("stats") or {}),
        tree=list(touchpoint.get("tree") or []),
    )


def _unwrap_payload(envelope: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(envelope, dict):
        raise ValueError("invalid_tjg_payload")
    if "data" in envelope and isinstance(envelope["data"], dict):
        if envelope.get("code", 0) not in (0, None) and "brandReport" not in envelope:
            raise ValueError(f"tjg_api_error:{envelope.get('msg', 'unknown')}")
        return envelope["data"]
    return envelope


def _parse_percent(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text_val = str(value).strip().replace("%", "")
    try:
        return float(text_val)
    except ValueError:
        return default


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    raw = str(value)[:10]
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _metrics_from_brand_metrics(metrics: dict[str, Any], *, fallback_name: str) -> TjgLayerMetrics:
    mapped = {str(item.get("label", "")): item.get("value") for item in metrics.get("brandMetrics") or []}
    return TjgLayerMetrics(
        name=str(metrics.get("brandName") or fallback_name),
        visibility_pct=_parse_percent(mapped.get("品牌可见性指数")),
        rank_label=str(mapped.get("行业排名") or ""),
        gap_to_leader_pct=_parse_percent(mapped.get("可见性距行业首位")),
        sentiment_pct=_parse_percent(mapped.get("AI好感度")),
        recommend_score=int(metrics.get("score") or 0),
        mention_count=int(metrics.get("brandMentionCount") or 0),
        total_responses=int(metrics.get("totalAiResponses") or 0),
    )


def _self_brand_competitor(brand_name: str, brand_visibility: dict[str, Any]) -> TjgCompetitorRow:
    platform_visibility: dict[str, float] = {}
    platform_rank: dict[str, float] = {}
    for plat in brand_visibility.get("platforms") or []:
        slug = normalize_tjg_platform(str(plat.get("platform") or ""))
        summary = plat.get("summary") or {}
        platform_visibility[slug] = _parse_percent(summary.get("avg_visibility"))
        platform_rank[slug] = float(summary.get("avg_rank") or 0)
    summary = brand_visibility.get("summary") or {}
    return TjgCompetitorRow(
        name=brand_name,
        is_self=True,
        layer="brand",
        summary_visibility=_parse_percent(summary.get("avg_visibility")),
        summary_rank=float(summary.get("avg_rank") or 0),
        platform_visibility=platform_visibility,
        platform_rank=platform_rank,
    )


def _self_product_competitor(product_name: str, visibility_dto: dict[str, Any]) -> TjgCompetitorRow:
    platform_visibility: dict[str, float] = {}
    platform_rank: dict[str, float] = {}
    for plat in visibility_dto.get("platforms") or []:
        slug = normalize_tjg_platform(str(plat.get("platform") or ""))
        summary = plat.get("summary") or {}
        platform_visibility[slug] = _parse_percent(summary.get("avg_visibility"))
        platform_rank[slug] = float(summary.get("avg_rank") or 0)
    summary = visibility_dto.get("summary") or {}
    return TjgCompetitorRow(
        name=product_name,
        is_self=True,
        layer="product",
        summary_visibility=_parse_percent(summary.get("avg_visibility")),
        summary_rank=float(summary.get("avg_rank") or 0),
        platform_visibility=platform_visibility,
        platform_rank=platform_rank,
    )


def _map_competitors(
    items: list[dict[str, Any]],
    *,
    layer: str,
    self_names: set[str],
) -> list[TjgCompetitorRow]:
    rows: list[TjgCompetitorRow] = []
    for item in items or []:
        name = str(item.get("competitor_name") or "").strip()
        if not name:
            continue
        platform_visibility: dict[str, float] = {}
        platform_rank: dict[str, float] = {}
        for plat in item.get("platforms") or []:
            slug = normalize_tjg_platform(str(plat.get("platform") or ""))
            summary = plat.get("summary") or {}
            platform_visibility[slug] = _parse_percent(summary.get("avg_visibility"))
            rank_val = summary.get("avg_rank")
            platform_rank[slug] = float(rank_val) if rank_val is not None else 0.0
        summary = item.get("summary") or {}
        rows.append(
            TjgCompetitorRow(
                name=name,
                logo_url=str(item.get("logo") or ""),
                is_self=name in self_names,
                layer=layer,
                summary_visibility=_parse_percent(summary.get("avg_visibility")),
                summary_rank=float(summary.get("avg_rank") or 0),
                platform_visibility=platform_visibility,
                platform_rank=platform_rank,
                external_id=str(item.get("competitor_id") or ""),
            )
        )
    return rows


def _gap_priority_from_visibility(visibility_pct: float) -> str:
    if visibility_pct < 20:
        return "high"
    if visibility_pct < 40:
        return "medium"
    return "covered"


def _flatten_touchpoint_tree(
    tree: list[dict[str, Any]],
    *,
    industry: str,
    intent_weights: dict[str, float] | None = None,
) -> list[TjgSceneRow]:
    scenes: list[TjgSceneRow] = []
    weights = intent_weights or {}
    for persona_node in tree or []:
        persona = str(persona_node.get("label") or "")
        for scenario_node in persona_node.get("children") or []:
            scene_name = str(scenario_node.get("label") or "")
            for intent_node in scenario_node.get("children") or []:
                intent = str(intent_node.get("label") or "")
                unit = intent_node.get("optimization_unit") or {}
                visibility = _parse_percent(unit.get("avg_visibility"))
                intent_weight = float(weights.get(intent) or intent_node.get("priority") or 0)
                scenes.append(
                    TjgSceneRow(
                        persona=persona,
                        scene_name=scene_name,
                        intent=intent,
                        weight_pct=round(intent_weight, 2),
                        visibility_pct=visibility,
                        gap_priority=_gap_priority_from_visibility(visibility),
                        industry=industry,
                        external_id=str(intent_node.get("id") or ""),
                        optimization_unit_id=str(unit.get("id") or ""),
                        article_count=int(unit.get("articles_count") or 0),
                        node_metadata={
                            "persona_description": persona_node.get("description"),
                            "persona_description_kvs": persona_node.get("description_kvs") or {},
                            "scene_description_kvs": scenario_node.get("description_kvs") or {},
                            "intent_description_kvs": intent_node.get("description_kvs") or {},
                        },
                    )
                )
    return scenes


def _scenes_from_diagnosis_data(diagnosis_data: dict[str, Any], *, industry: str) -> list[TjgSceneRow]:
    scenes: list[TjgSceneRow] = []
    for intent in diagnosis_data.get("intents") or []:
        intent_name = str(intent.get("name") or "")
        weight = float(intent.get("priority") or 0)
        scenes.append(
            TjgSceneRow(
                persona="",
                scene_name="",
                intent=intent_name,
                weight_pct=weight,
                visibility_pct=0.0,
                gap_priority="medium",
                industry=industry,
            )
        )
    return scenes


def _parse_prompt_items(items: list[dict[str, Any]], *, query_type: str) -> list[TjgPromptRow]:
    prompts: list[TjgPromptRow] = []
    for item in items or []:
        summary = item.get("summary") or {}
        responses: list[dict[str, Any]] = []
        for resp in item.get("responses") or []:
            responses.append(
                {
                    "platform": normalize_tjg_platform(str(resp.get("ai_platform") or "")),
                    "mentioned": bool(resp.get("is_mentioned")),
                    "snippet": str(resp.get("content") or "")[:4000],
                    "citations": resp.get("citations") or [],
                    "competitor_mentions": _parse_competitor_mentions(resp.get("mentioned_competitors")),
                    "brand_rank": None,
                }
            )
        platform_rank_map = {
            normalize_tjg_platform(str(p.get("platform") or "")): (p.get("summary") or {}).get("avg_rank")
            for p in item.get("platforms") or []
        }
        for resp in responses:
            rank_val = platform_rank_map.get(resp["platform"])
            if rank_val is not None:
                try:
                    resp["brand_rank"] = int(float(rank_val))
                except (TypeError, ValueError):
                    resp["brand_rank"] = None
        prompts.append(
            TjgPromptRow(
                prompt_id=str(item.get("prompt_id") or ""),
                content=str(item.get("content") or "").strip(),
                query_type=query_type,
                optimization_unit_name=str(item.get("optimization_unit_name") or ""),
                avg_visibility=_parse_percent(summary.get("avg_visibility")),
                avg_rank=float(summary.get("avg_rank") or 0),
                responses=responses,
            )
        )
    return prompts


def _build_competitor_matrix(competitors: list[TjgCompetitorRow]) -> list[dict[str, Any]]:
    matrix: list[dict[str, Any]] = []
    for slug in PLATFORMS_CN:
        row = {"platform": slug, "brands": []}
        for comp in competitors:
            vis = comp.platform_visibility.get(slug)
            if vis is None:
                continue
            row["brands"].append(
                {
                    "name": comp.name,
                    "visibility_pct": vis,
                    "weighted_rank_score": comp.platform_rank.get(slug),
                    "is_self": comp.is_self,
                }
            )
        matrix.append(row)
    return matrix


def _build_sections(parsed: TjgParsedReport) -> dict[str, Any]:
    period = ""
    if parsed.period_start and parsed.period_end:
        period = f"{parsed.period_start} ~ {parsed.period_end}"
    return {
        "source": {
            "provider": TJG_PROVIDER,
            "external_report_id": parsed.external_report_id,
            "token": parsed.token,
            "content_source": parsed.content_source,
            "imported_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        },
        "cover": {
            "title": "封面",
            "items": [
                f"品牌：{parsed.brand_name}",
                f"产品：{parsed.product_name}",
                f"数据窗口：{period}",
                f"行业：{parsed.industry}",
            ],
        },
        "overview": {
            "title": "数据概况",
            "stats": parsed.overview,
        },
        "brand": {
            "title": "品牌现状",
            "kpis": {
                "visibility_pct": parsed.brand_metrics.visibility_pct,
                "rank_label": parsed.brand_metrics.rank_label,
                "sentiment_pct": parsed.brand_metrics.sentiment_pct,
                "recommend_score": parsed.brand_metrics.recommend_score,
                "gap_to_leader_pct": parsed.brand_metrics.gap_to_leader_pct,
                "total_responses": parsed.brand_metrics.total_responses,
            },
            "competitor_matrix": _build_competitor_matrix(parsed.brand_competitors),
            "platform_breakdown": parsed.brand_platform_breakdown,
            "visibility_trend": parsed.brand_visibility_trend,
            "insights": parsed.insights[:3],
            "sentiment": {
                "positive": parsed.raw.get("brand_positive_reasons") or [],
                "negative": parsed.raw.get("brand_negative_reasons") or [],
            },
        },
        "product": {
            "title": "产品现状",
            "kpis": {
                "visibility_pct": parsed.product_metrics.visibility_pct,
                "rank_label": parsed.product_metrics.rank_label,
                "sentiment_pct": parsed.product_metrics.sentiment_pct,
                "recommend_score": parsed.product_metrics.recommend_score,
                "gap_to_leader_pct": parsed.product_metrics.gap_to_leader_pct,
            },
            "competitor_matrix": _build_competitor_matrix(parsed.product_competitors),
            "touchpoint_tree": {
                "highlight_node_id": parsed.touchpoint_tree.highlight_node_id,
                "stats": parsed.touchpoint_tree.stats,
                "tree": parsed.touchpoint_tree.tree,
            },
            "scenes": [
                {
                    "persona": s.persona,
                    "scene_name": s.scene_name,
                    "intent": s.intent,
                    "weight_pct": s.weight_pct,
                    "visibility_pct": s.visibility_pct,
                    "gap_priority": s.gap_priority,
                    "external_id": s.external_id,
                    "optimization_unit_id": s.optimization_unit_id,
                    "article_count": s.article_count,
                    "node_metadata": s.node_metadata,
                }
                for s in parsed.scenes[:50]
            ],
            "platform_breakdown": parsed.product_platform_breakdown,
            "visibility_trend": parsed.product_visibility_trend,
            "sentiment": {
                "positive": parsed.raw.get("product_positive_reasons") or [],
                "negative": parsed.raw.get("product_negative_reasons") or [],
            },
        },
        "strategy": {
            "title": "优化策略",
            "market_opportunity": parsed.strategy.get("market_opportunity") or {},
            "platform_recommendation": parsed.strategy.get("platform_recommendation") or {},
            "scenario_priorities": parsed.strategy.get("scenario_priorities") or [],
            "suggestions": parsed.strategy.get("suggestions") or [],
        },
        "difficulty": {
            "title": "难度评估",
            "assessment": parsed.difficulty,
        },
    }


def parse_tjg_report(
    envelope: dict[str, Any],
    *,
    token: str = "",
) -> TjgParsedReport:
    """将 TJG resolveSharedReportContent JSON 映射为结构化报告。"""
    data = _unwrap_payload(envelope)
    brand_report = data.get("brandReport") or {}
    product_report = data.get("diagnosticReportResponseDTO") or {}
    strategy = data.get("optimizationStrategy") or {}
    difficulty = data.get("optimizationDifficultyAssessmentDTO") or {}

    brand_name = str(brand_report.get("brand_name") or "").strip()
    product_name = str(product_report.get("brand_name") or brand_name).strip()
    industry = str(strategy.get("industry_description") or "")

    brand_metrics = _metrics_from_brand_metrics(brand_report.get("metrics") or {}, fallback_name=brand_name)
    product_metrics = _metrics_from_brand_metrics(product_report.get("metrics") or {}, fallback_name=product_name)
    brand_vis_summary = (data.get("brandVisibility") or {}).get("summary") or {}
    product_vis_summary = (data.get("visibilityQueryResponseDTO") or {}).get("summary") or {}
    brand_metrics.weighted_rank = float(brand_vis_summary.get("avg_rank") or 0)
    product_metrics.weighted_rank = float(product_vis_summary.get("avg_rank") or 0)

    self_names = {brand_name, product_name}
    brand_competitors = _map_competitors(
        (data.get("brandCompetitors") or {}).get("items") or [],
        layer="brand",
        self_names=self_names,
    )
    if not any(c.is_self for c in brand_competitors):
        brand_competitors.append(_self_brand_competitor(brand_name, data.get("brandVisibility") or {}))
    product_competitors = _map_competitors(
        (data.get("competitorsQueryResponseDTO") or {}).get("items") or [],
        layer="product",
        self_names=self_names,
    )
    if not any(c.is_self for c in product_competitors):
        product_competitors.append(
            _self_product_competitor(product_name, data.get("visibilityQueryResponseDTO") or {})
        )

    diagnosis_data = product_report.get("diagnosis_data") or {}
    intent_weights = {
        str(item.get("name") or ""): float(item.get("priority") or 0)
        for item in diagnosis_data.get("intents") or []
    }
    touchpoint_tree_raw = _extract_touchpoint_tree(product_report.get("metrics") or {})
    scenes = _flatten_touchpoint_tree(touchpoint_tree_raw.tree, industry=industry, intent_weights=intent_weights)
    if not scenes:
        scenes = _scenes_from_diagnosis_data(diagnosis_data, industry=industry)

    brand_platform_breakdown = _build_platform_breakdown((brand_report.get("metrics") or {}).get("platformData"))
    product_platform_breakdown = _build_platform_breakdown((product_report.get("metrics") or {}).get("platformData"))
    brand_visibility_trend = _build_visibility_trend(data.get("brandVisibility") or {})
    product_visibility_trend = _build_visibility_trend(data.get("visibilityQueryResponseDTO") or {})

    prompts = _parse_prompt_items((data.get("promptsQueryResponseDTO") or {}).get("items") or [], query_type="product")

    brand_insights = [
        {
            "insight_type": INSIGHT_TYPE_MAP.get(str(s.get("title") or ""), "general"),
            "title": s.get("title"),
            "body": s.get("content"),
        }
        for s in (brand_report.get("metrics") or {}).get("optimizationSuggestions") or []
    ]
    product_insights = [
        {
            "insight_type": INSIGHT_TYPE_MAP.get(str(s.get("title") or ""), "general"),
            "title": s.get("title"),
            "body": s.get("content"),
        }
        for s in (product_report.get("metrics") or {}).get("optimizationSuggestions") or []
    ]

    overview = {
        "brand_scene_questions": int(
            ((brand_report.get("metrics") or {}).get("touchpointTree") or {}).get("stats", {}).get("total_prompts") or 0
        ),
        "brand_simulated_prompts": brand_metrics.total_responses,
        "product_scene_questions": int(
            ((product_report.get("metrics") or {}).get("touchpointTree") or {}).get("stats", {}).get("total_prompts") or 0
        ),
        "product_simulated_prompts": product_metrics.total_responses,
        "displayed_product_prompts": int((data.get("promptsQueryResponseDTO") or {}).get("total") or len(prompts)),
        "platform_count": int((data.get("visibilityQueryResponseDTO") or {}).get("total") or 6),
    }

    parsed = TjgParsedReport(
        external_report_id=str(data.get("reportId") or ""),
        token=token,
        content_source=str(data.get("contentSource") or ""),
        brand_name=brand_name,
        product_name=product_name,
        period_start=_parse_date(product_report.get("dataCollectedStartedAt")),
        period_end=_parse_date(product_report.get("dataCollectedEndedAt")),
        industry=industry,
        brand_metrics=brand_metrics,
        product_metrics=product_metrics,
        brand_competitors=brand_competitors,
        product_competitors=product_competitors,
        scenes=scenes,
        prompts=prompts,
        insights=brand_insights + product_insights,
        strategy={
            "market_opportunity": strategy.get("market_opportunity") or {},
            "platform_recommendation": strategy.get("platform_recommendation") or {},
            "scenario_priorities": strategy.get("scenario_priorities") or [],
            "suggestions": (product_report.get("metrics") or {}).get("optimizationSuggestions") or [],
        },
        difficulty={
            "difficulty_coefficient": _parse_percent(difficulty.get("difficultyCoefficient")),
            "regulation_compliance": {
                "score": _parse_percent((difficulty.get("regulationCompliance") or {}).get("graphScore")),
                "label": (difficulty.get("regulationCompliance") or {}).get("desc"),
            },
            "market_competition": {
                "score": _parse_percent((difficulty.get("corpusCrowdedness") or {}).get("graphScore")),
                "label": (difficulty.get("corpusCrowdedness") or {}).get("desc"),
            },
            "entity_foundation": {
                "score": _parse_percent((difficulty.get("brandFoundation") or {}).get("graphScore")),
                "label": (difficulty.get("brandFoundation") or {}).get("desc"),
            },
        },
        overview=overview,
        sections={},
        raw={
            "brand_positive_reasons": (brand_report.get("metrics") or {}).get("positiveReasons") or [],
            "brand_negative_reasons": (brand_report.get("metrics") or {}).get("negativeReasons") or [],
            "product_positive_reasons": (product_report.get("metrics") or {}).get("positiveReasons") or [],
            "product_negative_reasons": (product_report.get("metrics") or {}).get("negativeReasons") or [],
            "feature_flags": data.get("featureFlags") or {},
            "brand_favorability": (brand_report.get("metrics") or {}).get("favorabilityData") or [],
            "product_favorability": (product_report.get("metrics") or {}).get("favorabilityData") or [],
        },
        touchpoint_tree=touchpoint_tree_raw,
        brand_platform_breakdown=brand_platform_breakdown,
        product_platform_breakdown=product_platform_breakdown,
        brand_visibility_trend=brand_visibility_trend,
        product_visibility_trend=product_visibility_trend,
    )
    parsed.sections = _build_sections(parsed)
    logger.info(
        "tjg_report_parsed external_id=%s brand=%s product=%s scenes=%s prompts=%s",
        parsed.external_report_id,
        parsed.brand_name,
        parsed.product_name,
        len(parsed.scenes),
        len(parsed.prompts),
    )
    return parsed


async def fetch_tjg_report(token: str, *, timeout: float = 60.0) -> dict[str, Any]:
    url = f"{TJG_API_BASE}/share/diagnostic-report/{token}/api/resolveSharedReportContent.json"
    logger.info("tjg_report_fetch_start token=%s url=%s", token, url)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url, headers={"Accept": "application/json"})
        resp.raise_for_status()
        payload = resp.json()
    logger.info("tjg_report_fetch_done token=%s code=%s", token, payload.get("code"))
    return payload


async def _scene_table_columns(db: AsyncSession) -> set[str]:
    rows = (
        await db.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'geo_monitor_scenes'
                """
            )
        )
    ).all()
    return {str(r[0]) for r in rows}


async def _purge_monitor_import_data(db: AsyncSession) -> dict[str, int]:
    """replace 导入前清理监控子表，避免场景/探针重复追加。"""
    counts: dict[str, int] = {}

    async def _delete(table: str, sql: str) -> None:
        if not await _table_exists(db, table):
            counts[table] = 0
            return
        result = await db.execute(text(sql))
        counts[table] = int(result.rowcount or 0)

    if await _table_exists(db, "geo_monitor_probe_results") and await _table_exists(db, "geo_monitor_questions"):
        if await _table_exists(db, "geo_monitor_probe_citations"):
            await _delete(
                "geo_monitor_probe_citations",
                """
                DELETE FROM geo_monitor_probe_citations
                WHERE probe_result_id IN (
                    SELECT id FROM geo_monitor_probe_results
                    WHERE question_id IN (SELECT id FROM geo_monitor_questions)
                )
                """,
            )
        await _delete(
            "geo_monitor_probe_results",
            "DELETE FROM geo_monitor_probe_results WHERE question_id IN (SELECT id FROM geo_monitor_questions)",
        )
    elif await _table_exists(db, "geo_monitor_probe_results"):
        await _delete("geo_monitor_probe_results", "DELETE FROM geo_monitor_probe_results")

    await _delete("geo_monitor_questions", "DELETE FROM geo_monitor_questions")
    await _delete("geo_monitor_scenes", "DELETE FROM geo_monitor_scenes")
    await _delete("geo_monitor_insights", "DELETE FROM geo_monitor_insights WHERE status = 'active'")
    await _delete("geo_monitor_runs", "DELETE FROM geo_monitor_runs")

    logger.info("tjg_import_purge_done counts=%s", counts)
    return counts


async def _find_existing_report_id(db: AsyncSession, external_report_id: str) -> int | None:
    if not await _table_exists(db, "geo_visibility_reports"):
        return None
    row = (
        await db.execute(
            text(
                """
                SELECT id FROM geo_visibility_reports
                WHERE sections->'source'->>'provider' = :provider
                  AND sections->'source'->>'external_report_id' = :ext_id
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"provider": TJG_PROVIDER, "ext_id": external_report_id},
        )
    ).scalar_one_or_none()
    return int(row) if row else None


async def _upsert_competitors(db: AsyncSession, competitors: list[TjgCompetitorRow]) -> int:
    if not await _table_exists(db, "geo_monitor_competitors"):
        return 0
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

    count = 0
    for comp in competitors:
        entity_type = comp.layer if comp.layer in ("brand", "product") else "brand"
        if has_type:
            existing = (
                await db.execute(
                    text(
                        """
                        SELECT id FROM geo_monitor_competitors
                        WHERE brand_name = :name AND entity_type = :etype
                        LIMIT 1
                        """
                    ),
                    {"name": comp.name, "etype": entity_type},
                )
            ).scalar_one_or_none()
        else:
            existing = (
                await db.execute(
                    text("SELECT id FROM geo_monitor_competitors WHERE brand_name = :name LIMIT 1"),
                    {"name": comp.name},
                )
            ).scalar_one_or_none()
        aliases = [comp.external_id] if comp.external_id else []
        if existing:
            await db.execute(
                text(
                    """
                    UPDATE geo_monitor_competitors
                    SET aliases = CAST(:aliases AS JSON), is_self = :is_self, status = 'active'
                    WHERE id = :id
                    """
                ),
                {"id": int(existing), "aliases": json.dumps(aliases, ensure_ascii=False), "is_self": comp.is_self},
            )
        elif has_type:
            await db.execute(
                text(
                    """
                    INSERT INTO geo_monitor_competitors (brand_name, aliases, is_self, status, entity_type)
                    VALUES (:name, CAST(:aliases AS JSON), :is_self, 'active', :etype)
                    """
                ),
                {
                    "name": comp.name,
                    "aliases": json.dumps(aliases, ensure_ascii=False),
                    "is_self": comp.is_self,
                    "etype": entity_type,
                },
            )
        else:
            await db.execute(
                text(
                    """
                    INSERT INTO geo_monitor_competitors (brand_name, aliases, is_self, status)
                    VALUES (:name, CAST(:aliases AS JSON), :is_self, 'active')
                    """
                ),
                {"name": comp.name, "aliases": json.dumps(aliases, ensure_ascii=False), "is_self": comp.is_self},
            )
        count += 1
    logger.info("tjg_competitors_upserted count=%s has_entity_type=%s", count, has_type)
    return count


async def _import_scenes(db: AsyncSession, scenes: list[TjgSceneRow]) -> dict[str, int]:
    if not await _table_exists(db, "geo_monitor_scenes"):
        return {}
    cols = await _scene_table_columns(db)
    scene_ids: dict[str, int] = {}
    for scene in scenes:
        key = f"{scene.persona}|{scene.scene_name}|{scene.intent}"
        params = {
            "p": scene.persona,
            "sn": scene.scene_name or scene.intent,
            "i": scene.intent,
            "w": scene.weight_pct,
            "ind": scene.industry,
            "gr": round(scene.visibility_pct / 100, 4) if scene.visibility_pct else 0,
            "gp": scene.gap_priority,
        }
        extra_cols = []
        extra_vals = []
        if "external_id" in cols:
            extra_cols.extend(["external_id", "optimization_unit_id", "article_count", "visibility_pct", "node_metadata"])
            extra_vals.extend([":ext_id", ":opt_id", ":articles", ":vis", "CAST(:meta AS JSON)"])
            params.update(
                {
                    "ext_id": scene.external_id,
                    "opt_id": scene.optimization_unit_id,
                    "articles": scene.article_count,
                    "vis": scene.visibility_pct,
                    "meta": json.dumps(scene.node_metadata, ensure_ascii=False),
                }
            )
        col_sql = ", ".join(
            ["persona", "scene_name", "intent", "weight_pct", "industry", "gap_rate", "gap_priority", "status"]
            + extra_cols
        )
        val_sql = ", ".join([":p", ":sn", ":i", ":w", ":ind", ":gr", ":gp", "'active'"] + extra_vals)
        row = (
            await db.execute(
                text(
                    f"""
                    INSERT INTO geo_monitor_scenes ({col_sql})
                    VALUES ({val_sql})
                    RETURNING id
                    """
                ),
                params,
            )
        ).first()
        if row:
            scene_ids[key] = int(row[0])
    return scene_ids


async def _import_probe_citations(db: AsyncSession, probe_id: int, citations: list[dict[str, Any]]) -> int:
    if not await _table_exists(db, "geo_monitor_probe_citations"):
        return 0
    count = 0
    for idx, cite in enumerate(citations or []):
        title = str(cite.get("title") or "")[:500]
        url = str(cite.get("url") or "")
        if not title and not url:
            continue
        await db.execute(
            text(
                """
                INSERT INTO geo_monitor_probe_citations (probe_result_id, title, url, position)
                VALUES (:pid, :title, :url, :pos)
                """
            ),
            {"pid": probe_id, "title": title, "url": url, "pos": idx},
        )
        count += 1
    return count


async def _import_questions_and_probes(
    db: AsyncSession,
    prompts: list[TjgPromptRow],
    *,
    scene_ids: dict[str, int],
) -> tuple[int, int, int]:
    if not await _table_exists(db, "geo_monitor_questions"):
        return 0, 0, 0

    run_id = None
    if await _table_exists(db, "geo_monitor_runs"):
        row = (
            await db.execute(
                text(
                    """
                    INSERT INTO geo_monitor_runs (status, platform, question_count, probe_count, started_at, completed_at)
                    VALUES ('completed', :platform, :qc, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id
                    """
                ),
                {"platform": ",".join(PLATFORMS_CN), "qc": len(prompts)},
            )
        ).first()
        run_id = int(row[0]) if row else None

    question_count = 0
    probe_count = 0
    citation_count = 0
    for prompt in prompts:
        scene_id = None
        if prompt.optimization_unit_name and scene_ids:
            for key, sid in scene_ids.items():
                if prompt.optimization_unit_name in key or key.endswith(prompt.optimization_unit_name):
                    scene_id = sid
                    break
        qrow = (
            await db.execute(
                text(
                    """
                    INSERT INTO geo_monitor_questions
                        (question_text, priority, status, scene_id, query_type, competitor_brands)
                    VALUES (:text, :priority, 'active', :scene_id, :qt, CAST(:comp AS JSON))
                    RETURNING id
                    """
                ),
                {
                    "text": prompt.content,
                    "priority": max(0, min(100, int(prompt.avg_visibility))),
                    "scene_id": scene_id,
                    "qt": prompt.query_type,
                    "comp": json.dumps([], ensure_ascii=False),
                },
            )
        ).first()
        if not qrow:
            continue
        question_id = int(qrow[0])
        question_count += 1

        if not run_id or not await _table_exists(db, "geo_monitor_probe_results"):
            continue
        for resp in prompt.responses:
            rank = resp.get("brand_rank")
            probe_row = (
                await db.execute(
                    text(
                        """
                        INSERT INTO geo_monitor_probe_results
                            (run_id, question_id, platform, brand_rank, mentioned, snippet, engine,
                             ranking_score, sentiment, competitor_mentions)
                        VALUES (:run_id, :qid, :platform, :rank, :mentioned, :snippet, 'api',
                                :ranking_score, NULL, CAST(:competitors AS JSON))
                        RETURNING id
                        """
                    ),
                    {
                        "run_id": run_id,
                        "qid": question_id,
                        "platform": resp.get("platform") or "doubao",
                        "rank": rank,
                        "mentioned": bool(resp.get("mentioned")),
                        "snippet": resp.get("snippet") or "",
                        "ranking_score": calc_ranking_score(rank),
                        "competitors": json.dumps(resp.get("competitor_mentions") or [], ensure_ascii=False),
                    },
                )
            ).first()
            if probe_row:
                probe_count += 1
                citation_count += await _import_probe_citations(db, int(probe_row[0]), resp.get("citations") or [])

    if run_id:
        await db.execute(
            text("UPDATE geo_monitor_runs SET probe_count = :pc WHERE id = :id"),
            {"pc": probe_count, "id": run_id},
        )
    return question_count, probe_count, citation_count


async def _import_snapshot(db: AsyncSession, parsed: TjgParsedReport) -> int | None:
    if not await _table_exists(db, "geo_monitor_snapshots") or not parsed.period_end:
        return None
    product_vis = parsed.product_metrics.visibility_pct
    platform_matrix = [
        {
            "layer": "product",
            "platform": slug,
            "visibility_pct": parsed.product_competitors[0].platform_visibility.get(slug, 0) if parsed.product_competitors else 0,
        }
        for slug in PLATFORMS_CN
    ]
    self_row = next((c for c in parsed.product_competitors if c.is_self), None)
    if self_row:
        platform_matrix = [
            {"layer": "product", "platform": slug, "visibility_pct": self_row.platform_visibility.get(slug, 0)}
            for slug in PLATFORMS_CN
        ]
    row = (
        await db.execute(
            text(
                """
                INSERT INTO geo_monitor_snapshots
                    (snapshot_date, mention_rate, visibility_pct, weighted_rank_score, sentiment_score, platform_matrix)
                VALUES (:d, :mr, :vis, :rank, :sent, CAST(:matrix AS JSON))
                ON CONFLICT (snapshot_date) DO UPDATE SET
                    mention_rate = EXCLUDED.mention_rate,
                    visibility_pct = EXCLUDED.visibility_pct,
                    weighted_rank_score = EXCLUDED.weighted_rank_score,
                    sentiment_score = EXCLUDED.sentiment_score,
                    platform_matrix = EXCLUDED.platform_matrix
                RETURNING id
                """
            ),
            {
                "d": parsed.period_end,
                "mr": round(product_vis / 100, 4),
                "vis": product_vis,
                "rank": parsed.product_metrics.weighted_rank,
                "sent": parsed.product_metrics.sentiment_pct,
                "matrix": json.dumps(platform_matrix, ensure_ascii=False),
            },
        )
    ).first()
    return int(row[0]) if row else None


async def _import_insights(db: AsyncSession, insights: list[dict[str, Any]]) -> int:
    if not await _table_exists(db, "geo_monitor_insights"):
        return 0
    count = 0
    for item in insights:
        await db.execute(
            text(
                """
                INSERT INTO geo_monitor_insights (insight_type, title, body, payload, status)
                VALUES (:type, :title, :body, CAST(:payload AS JSON), 'active')
                """
            ),
            {
                "type": item.get("insight_type") or "general",
                "title": str(item.get("title") or ""),
                "body": str(item.get("body") or ""),
                "payload": json.dumps(item, ensure_ascii=False),
            },
        )
        count += 1
    return count


async def _save_visibility_report(
    db: AsyncSession,
    parsed: TjgParsedReport,
    *,
    replace_existing: bool,
) -> int:
    if not await _table_exists(db, "geo_visibility_reports"):
        raise RuntimeError("geo_visibility_reports_table_missing")

    title = f"{parsed.brand_name} AI 可见性诊断报告（TJG 导入）"
    if parsed.period_start and parsed.period_end:
        title = f"{parsed.brand_name} AI 可见性诊断报告 ({parsed.period_start} ~ {parsed.period_end})"

    existing_id = await _find_existing_report_id(db, parsed.external_report_id)
    params = {
        "title": title,
        "ps": parsed.period_start,
        "pe": parsed.period_end,
        "sec": json.dumps(parsed.sections, ensure_ascii=False),
    }

    if existing_id and replace_existing:
        await db.execute(
            text(
                """
                UPDATE geo_visibility_reports
                SET title = :title, period_start = :ps, period_end = :pe,
                    sections = CAST(:sec AS JSON), status = 'published'
                WHERE id = :id
                """
            ),
            {**params, "id": existing_id},
        )
        logger.info("tjg_report_updated report_id=%s external_id=%s", existing_id, parsed.external_report_id)
        return existing_id

    row = (
        await db.execute(
            text(
                """
                INSERT INTO geo_visibility_reports (title, period_start, period_end, sections, status, html_path)
                VALUES (:title, :ps, :pe, CAST(:sec AS JSON), 'published', '')
                RETURNING id
                """
            ),
            params,
        )
    ).first()
    report_id = int(row[0]) if row else 0
    logger.info("tjg_report_inserted report_id=%s external_id=%s", report_id, parsed.external_report_id)
    return report_id


async def import_tjg_report(
    db: AsyncSession,
    envelope: dict[str, Any],
    *,
    token: str = "",
    replace_existing: bool = False,
) -> dict[str, Any]:
    """解析 TJG JSON 并写入 geo_eval 相关表。"""
    parsed = parse_tjg_report(envelope, token=token)

    existing_id = await _find_existing_report_id(db, parsed.external_report_id)
    if replace_existing and existing_id:
        await _purge_monitor_import_data(db)

    report_id = await _save_visibility_report(db, parsed, replace_existing=replace_existing)
    competitor_count = await _upsert_competitors(db, parsed.brand_competitors + parsed.product_competitors)
    scene_ids = await _import_scenes(db, parsed.scenes)
    question_count, probe_count, citation_count = await _import_questions_and_probes(db, parsed.prompts, scene_ids=scene_ids)
    snapshot_id = await _import_snapshot(db, parsed)
    insight_count = await _import_insights(db, parsed.insights)

    await db.commit()

    result = {
        "status": "imported",
        "provider": TJG_PROVIDER,
        "external_report_id": parsed.external_report_id,
        "report_id": report_id,
        "brand_name": parsed.brand_name,
        "product_name": parsed.product_name,
        "counts": {
            "competitors": competitor_count,
            "scenes": len(scene_ids),
            "questions": question_count,
            "probes": probe_count,
            "citations": citation_count,
            "insights": insight_count,
        },
        "snapshot_id": snapshot_id,
        "sections_keys": list(parsed.sections.keys()),
    }
    logger.info("tjg_report_import_done %s", result)
    return result


async def import_tjg_report_from_token(
    db: AsyncSession,
    token: str,
    *,
    replace_existing: bool = False,
) -> dict[str, Any]:
    payload = await fetch_tjg_report(token)
    return await import_tjg_report(db, payload, token=token, replace_existing=replace_existing)


async def import_tjg_report_from_url(
    db: AsyncSession,
    share_url: str,
    *,
    replace_existing: bool = False,
) -> dict[str, Any]:
    token = extract_share_token(share_url)
    return await import_tjg_report_from_token(db, token, replace_existing=replace_existing)
