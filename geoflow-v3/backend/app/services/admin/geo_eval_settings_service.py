"""GEO 内容门禁 + 探针标准配置（site_settings；对齐 Sim-sandbox calibration.yml 语义）。"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.admin.production_service import _table_exists
from app.services.admin.settings_crud_service import SiteSettingBody, upsert_site_setting

logger = logging.getLogger(__name__)

GATE_KEYS = (
    "geo_eval_enabled",
    "geo_eval_hard_gate",
    "geo_eval_wiki_gate_enabled",
    "geo_eval_simulation_pass_score",
    "geo_eval_audit_pass_score",
)

PROBE_KEYS = (
    "probe_metric_primary",
    "probe_footnote_on_bias",
    "probe_do_not_overwrite_open_api_kpi",
    "probe_rank_report_weight",
    "probe_min_evidence_level",
    "probe_forbid_corpus_as_l1",
    "probe_fixture_min_list_acc",
    "probe_scan_platforms",
    "probe_priority_floor_daily",
)

DEFAULT_RANK_WEIGHT = {"list_order": 1.0, "first_mention": 0.3, "unknown": 0.0}
PROBE_CONTRACT_FIELDS = (
    {"field": "rank_method", "values": "list_order | first_mention | unknown"},
    {"field": "evidence_level", "values": "L0 | L1"},
    {"field": "match_type", "values": "domain_wiki | domain_official | none"},
    {"field": "parser_version", "values": "v2"},
)


class GeoEvalGateBody(BaseModel):
    enabled: bool = True
    hard_gate: bool = False
    wiki_checks_enabled: bool = True
    simulation_pass_score: float = Field(default=0.55, ge=0.0, le=1.0)
    audit_pass_score: float = Field(default=0.60, ge=0.0, le=1.0)


class RankReportWeightBody(BaseModel):
    list_order: float = Field(default=1.0, ge=0.0, le=1.0)
    first_mention: float = Field(default=0.3, ge=0.0, le=1.0)
    unknown: float = Field(default=0.0, ge=0.0, le=1.0)


class ProbeStandardsBody(BaseModel):
    footnote_on_bias: bool = True
    do_not_overwrite_open_api_kpi: bool = True
    rank_report_weight: RankReportWeightBody = Field(default_factory=RankReportWeightBody)
    min_evidence_level: str = Field(default="L1", pattern="^(L0|L1)$")
    forbid_corpus_as_l1: bool = True
    fixture_min_list_acc: float = Field(default=0.8, ge=0.0, le=1.0)
    scan_platforms: str = "doubao,deepseek"
    priority_floor_daily: int = Field(default=80, ge=0, le=1000)


class GeoEvalSettingsBody(BaseModel):
    gate: GeoEvalGateBody | None = None
    probe_standards: ProbeStandardsBody | None = None


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return str(value).lower() in ("1", "true", "yes", "on")


def _as_float(value: str | None, default: float) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: str | None, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


async def _load_kv(db: AsyncSession, keys: tuple[str, ...]) -> dict[str, str]:
    if not await _table_exists(db, "site_settings"):
        return {}
    placeholders = ", ".join(f":k{i}" for i in range(len(keys)))
    params = {f"k{i}": key for i, key in enumerate(keys)}
    rows = (
        await db.execute(
            text(f"SELECT setting_key, setting_value FROM site_settings WHERE setting_key IN ({placeholders})"),
            params,
        )
    ).all()
    return {str(k): ("" if v is None else str(v)) for k, v in rows}


def _parse_rank_weight(raw: str | None) -> dict[str, float]:
    out = dict(DEFAULT_RANK_WEIGHT)
    if not raw:
        return out
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            for key in ("list_order", "first_mention", "unknown"):
                if key in data:
                    out[key] = max(0.0, min(1.0, float(data[key])))
    except (TypeError, ValueError, json.JSONDecodeError):
        logger.warning("probe_rank_report_weight_invalid raw=%s", raw[:80] if raw else "")
    return out


async def get_geo_eval_gate_config(db: AsyncSession) -> dict[str, Any]:
    env = get_settings()
    kv = await _load_kv(db, GATE_KEYS)
    enabled = _as_bool(kv.get("geo_eval_enabled"), env.geo_eval_enabled)
    hard_gate = _as_bool(kv.get("geo_eval_hard_gate"), env.geo_eval_hard_gate)
    wiki = _as_bool(kv.get("geo_eval_wiki_gate_enabled"), env.geo_eval_wiki_gate_enabled)
    sim_score = _as_float(kv.get("geo_eval_simulation_pass_score"), env.geo_eval_simulation_pass_score)
    audit_score = _as_float(kv.get("geo_eval_audit_pass_score"), env.geo_eval_audit_pass_score)
    sim_score = max(0.0, min(1.0, sim_score))
    audit_score = max(0.0, min(1.0, audit_score))
    return {
        "enabled": enabled,
        "gate_enabled": hard_gate,
        "hard_gate": hard_gate,
        "wiki_checks_enabled": wiki,
        "mode": "hard" if hard_gate else "soft",
        "rollout_percent": 100,
        "simulation_pass_score": sim_score,
        "audit_pass_score": audit_score,
    }


async def get_probe_standards(db: AsyncSession) -> dict[str, Any]:
    kv = await _load_kv(db, PROBE_KEYS)
    weight = _parse_rank_weight(kv.get("probe_rank_report_weight"))
    min_level = kv.get("probe_min_evidence_level") or "L1"
    if min_level not in ("L0", "L1"):
        min_level = "L1"
    standards = {
        "metric_primary": "open_api",
        "footnote_on_bias": _as_bool(kv.get("probe_footnote_on_bias"), True),
        "do_not_overwrite_open_api_kpi": True,
        "rank_report_weight": weight,
        "min_evidence_level": min_level,
        "forbid_corpus_as_l1": _as_bool(kv.get("probe_forbid_corpus_as_l1"), True),
        "fixture_min_list_acc": max(0.0, min(1.0, _as_float(kv.get("probe_fixture_min_list_acc"), 0.8))),
        "scan_platforms": (kv.get("probe_scan_platforms") or "doubao,deepseek").strip(),
        "priority_floor_daily": max(0, min(1000, _as_int(kv.get("probe_priority_floor_daily"), 80))),
        "contract_fields": list(PROBE_CONTRACT_FIELDS),
        "effect_note": "生效于偏移报告脚注与 KPI 叙述权重；禁止改写 visibility_open_api。",
    }
    logger.debug(
        "probe_standards_loaded footnote=%s min_evidence=%s list_acc=%s weight=%s",
        standards["footnote_on_bias"],
        standards["min_evidence_level"],
        standards["fixture_min_list_acc"],
        weight,
    )
    return standards


async def get_geo_eval_settings_bundle(db: AsyncSession) -> dict[str, Any]:
    return {
        "gate": await get_geo_eval_gate_config(db),
        "probe_standards": await get_probe_standards(db),
    }


async def save_geo_eval_settings(db: AsyncSession, body: GeoEvalSettingsBody) -> dict[str, Any]:
    if body.gate is None and body.probe_standards is None:
        raise HTTPException(status_code=422, detail="empty_settings_body")

    if body.gate is not None:
        g = body.gate
        items = [
            ("geo_eval_enabled", "true" if g.enabled else "false", "boolean", "geo_eval"),
            ("geo_eval_hard_gate", "true" if g.hard_gate else "false", "boolean", "geo_eval"),
            ("geo_eval_wiki_gate_enabled", "true" if g.wiki_checks_enabled else "false", "boolean", "geo_eval"),
            ("geo_eval_simulation_pass_score", str(g.simulation_pass_score), "float", "geo_eval"),
            ("geo_eval_audit_pass_score", str(g.audit_pass_score), "float", "geo_eval"),
        ]
        for key, value, vtype, group in items:
            await upsert_site_setting(
                db,
                SiteSettingBody(setting_key=key, setting_value=value, value_type=vtype, group_name=group),
            )
        logger.info(
            "geo_eval_settings_updated enabled=%s hard_gate=%s wiki=%s sim_pass=%s audit_pass=%s",
            g.enabled,
            g.hard_gate,
            g.wiki_checks_enabled,
            g.simulation_pass_score,
            g.audit_pass_score,
        )

    if body.probe_standards is not None:
        p = body.probe_standards
        if p.do_not_overwrite_open_api_kpi is False:
            raise HTTPException(status_code=400, detail="do_not_overwrite_open_api_kpi_required")
        weight_json = json.dumps(p.rank_report_weight.model_dump(), ensure_ascii=False)
        items = [
            ("probe_metric_primary", "open_api", "string", "probe_standards"),
            ("probe_footnote_on_bias", "true" if p.footnote_on_bias else "false", "boolean", "probe_standards"),
            ("probe_do_not_overwrite_open_api_kpi", "true", "boolean", "probe_standards"),
            ("probe_rank_report_weight", weight_json, "json", "probe_standards"),
            ("probe_min_evidence_level", p.min_evidence_level, "string", "probe_standards"),
            ("probe_forbid_corpus_as_l1", "true" if p.forbid_corpus_as_l1 else "false", "boolean", "probe_standards"),
            ("probe_fixture_min_list_acc", str(p.fixture_min_list_acc), "float", "probe_standards"),
            ("probe_scan_platforms", p.scan_platforms.strip() or "doubao,deepseek", "string", "probe_standards"),
            ("probe_priority_floor_daily", str(p.priority_floor_daily), "integer", "probe_standards"),
        ]
        for key, value, vtype, group in items:
            await upsert_site_setting(
                db,
                SiteSettingBody(setting_key=key, setting_value=value, value_type=vtype, group_name=group),
            )
        logger.info(
            "probe_standards_updated footnote=%s min_evidence=%s list_acc=%s forbid_corpus_l1=%s platforms=%s",
            p.footnote_on_bias,
            p.min_evidence_level,
            p.fixture_min_list_acc,
            p.forbid_corpus_as_l1,
            p.scan_platforms,
        )

    return await get_geo_eval_settings_bundle(db)
