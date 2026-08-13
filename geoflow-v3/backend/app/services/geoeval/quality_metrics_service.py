"""质量层指标：参数一致率 / 归因正确率（规则版 SSOT）。"""

from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

PARAM_THRESHOLD = 95.0
ATTRIBUTION_THRESHOLD = 90.0

# 常见技术参数正则 → SSOT 键
PARAM_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("compute_tops", re.compile(r"(\d+(?:\.\d+)?)\s*(?:TOPS|tops)")),
    ("lidar_count", re.compile(r"(\d+)\s*(?:颗|个)?\s*(?:激光雷达|LiDAR|lidar)")),
    ("noa_cities", re.compile(r"(?:开通|覆盖)\s*(\d+)\s*(?:城|个城市)")),
]


async def load_ssot_params(db: AsyncSession) -> dict[str, str]:
    """从 tech IP 资产 meta_json 抽取 SSOT 参数表。"""
    from app.services.admin.production_service import _table_exists

    ssot: dict[str, str] = {}
    if not await _table_exists(db, "tech_ip_assets"):
        return ssot
    try:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT name, meta_json
                    FROM tech_ip_assets
                    WHERE COALESCE(status, 'active') = 'active'
                    ORDER BY id DESC
                    LIMIT 50
                    """
                )
            )
        ).all()
    except Exception:
        logger.debug("ssot_load_failed", exc_info=True)
        return ssot

    for name, specs in rows:
        data: Any = specs or {}
        if isinstance(data, str):
            import json

            try:
                data = json.loads(data)
            except Exception:
                data = {}
        if not isinstance(data, dict):
            continue
        nested = data.get("ssot") if isinstance(data.get("ssot"), dict) else data
        for key in ("compute_tops", "lidar_count", "noa_cities", "算力", "激光雷达", "开通城市"):
            if key in nested and nested[key] is not None:
                norm = {
                    "算力": "compute_tops",
                    "激光雷达": "lidar_count",
                    "开通城市": "noa_cities",
                }.get(key, key)
                ssot[norm] = str(nested[key]).strip()
        if name:
            ssot["_aliases"] = f"{ssot.get('_aliases', '')},{name}".strip(",")
    logger.info("ssot_params_loaded keys=%s", [k for k in ssot if not k.startswith("_")])
    return ssot


def extract_params_from_text(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, pattern in PARAM_PATTERNS:
        m = pattern.search(text or "")
        if m:
            found[key] = m.group(1)
    return found


def score_param_consistency(snippets: list[str], ssot: dict[str, str]) -> dict:
    keys = [k for k in ("compute_tops", "lidar_count", "noa_cities") if k in ssot]
    if not keys or not snippets:
        return {
            "param_consistency_pct": None,
            "checked": 0,
            "matched": 0,
            "gate_pass": None,
            "status": "pending",
            "threshold": PARAM_THRESHOLD,
        }
    checked = 0
    matched = 0
    for snip in snippets:
        extracted = extract_params_from_text(snip)
        for key in keys:
            if key not in extracted:
                continue
            checked += 1
            if _values_equal(extracted[key], ssot[key]):
                matched += 1
    if checked == 0:
        return {
            "param_consistency_pct": None,
            "checked": 0,
            "matched": 0,
            "gate_pass": None,
            "status": "pending",
            "threshold": PARAM_THRESHOLD,
        }
    pct = round(matched / checked * 100, 1)
    return {
        "param_consistency_pct": pct,
        "checked": checked,
        "matched": matched,
        "gate_pass": pct >= PARAM_THRESHOLD,
        "status": "ok" if pct >= PARAM_THRESHOLD else "fail",
        "threshold": PARAM_THRESHOLD,
    }


def score_attribution(snippets: list[str], aliases: list[str], competitor_tokens: list[str]) -> dict:
    """提及参数时是否绑定到自有别名而非竞品。"""
    if not snippets or not aliases:
        return {
            "attribution_accuracy_pct": None,
            "checked": 0,
            "correct": 0,
            "threshold": ATTRIBUTION_THRESHOLD,
        }
    alias_l = [a.lower() for a in aliases if a]
    comp_l = [c.lower() for c in competitor_tokens if c]
    checked = 0
    correct = 0
    for snip in snippets:
        low = (snip or "").lower()
        has_param = any(p.search(snip or "") for _, p in PARAM_PATTERNS)
        if not has_param:
            continue
        checked += 1
        has_self = any(a in low for a in alias_l)
        has_comp = any(c in low for c in comp_l)
        if has_self and not (has_comp and not has_self):
            correct += 1
        elif has_self:
            correct += 1
    if checked == 0:
        return {
            "attribution_accuracy_pct": None,
            "checked": 0,
            "correct": 0,
            "threshold": ATTRIBUTION_THRESHOLD,
        }
    pct = round(correct / checked * 100, 1)
    return {
        "attribution_accuracy_pct": pct,
        "checked": checked,
        "correct": correct,
        "threshold": ATTRIBUTION_THRESHOLD,
        "pass": pct >= ATTRIBUTION_THRESHOLD,
    }


def _values_equal(a: str, b: str) -> bool:
    try:
        return abs(float(a) - float(b)) < 1e-6
    except ValueError:
        return str(a).strip().lower() == str(b).strip().lower()


async def compute_quality_gates(db: AsyncSession) -> dict:
    from app.services.admin.production_service import _table_exists

    ssot = await load_ssot_params(db)
    snippets: list[str] = []
    if await _table_exists(db, "geo_monitor_probe_results"):
        rows = (
            await db.execute(
                text(
                    """
                    SELECT snippet FROM geo_monitor_probe_results
                    WHERE mentioned = true AND snippet IS NOT NULL
                      AND COALESCE(engine, 'corpus') = 'api'
                    ORDER BY id DESC
                    LIMIT 200
                    """
                )
            )
        ).all()
        snippets = [str(r[0]) for r in rows if r[0]]

    param = score_param_consistency(snippets, ssot)
    aliases = [a for a in str(ssot.get("_aliases", "")).split(",") if a]
    if not aliases:
        try:
            from app.services.geoeval.monitor_probe import load_brand_keywords

            aliases = await load_brand_keywords(db)
        except Exception:
            aliases = []
    comps: list[str] = []
    if await _table_exists(db, "geo_monitor_competitors"):
        crow = (
            await db.execute(
                text(
                    """
                    SELECT brand_name FROM geo_monitor_competitors
                    WHERE COALESCE(is_self, false) = false AND status = 'active'
                    LIMIT 30
                    """
                )
            )
        ).all()
        comps = [str(r[0]) for r in crow]

    attr = score_attribution(snippets, aliases, comps)
    result = {
        **param,
        **{k: v for k, v in attr.items() if k != "checked"},
        "attribution_checked": attr.get("checked"),
        "kpi_track": "open_api",
        "ssot_keys": [k for k in ssot if not k.startswith("_")],
    }
    logger.info(
        "quality_gates_computed param=%s gate=%s attr=%s samples=%s",
        result.get("param_consistency_pct"),
        result.get("gate_pass"),
        result.get("attribution_accuracy_pct"),
        len(snippets),
    )
    return result
