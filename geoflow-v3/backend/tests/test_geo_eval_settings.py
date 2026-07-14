"""GEO 双轨配置：site_settings 覆盖 env、探针标准强制不覆盖主 KPI。"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.services.admin.geo_eval_settings_service import (
    GeoEvalGateBody,
    GeoEvalSettingsBody,
    ProbeStandardsBody,
    get_geo_eval_gate_config,
    get_probe_standards,
    save_geo_eval_settings,
)


@pytest.mark.asyncio
async def test_gate_config_falls_back_to_env_when_no_table():
    db = AsyncMock()
    with patch(
        "app.services.admin.geo_eval_settings_service._table_exists",
        new=AsyncMock(return_value=False),
    ):
        gate = await get_geo_eval_gate_config(db)
    assert "enabled" in gate
    assert gate["mode"] in ("soft", "hard")
    assert 0.0 <= gate["simulation_pass_score"] <= 1.0
    assert 0.0 <= gate["audit_pass_score"] <= 1.0
    assert "wiki_checks_enabled" in gate


@pytest.mark.asyncio
async def test_gate_config_site_settings_override_env():
    db = AsyncMock()
    rows = [
        ("geo_eval_enabled", "true"),
        ("geo_eval_hard_gate", "true"),
        ("geo_eval_wiki_gate_enabled", "false"),
        ("geo_eval_simulation_pass_score", "0.77"),
        ("geo_eval_audit_pass_score", "0.88"),
    ]
    result = AsyncMock()
    result.all = lambda: rows
    db.execute = AsyncMock(return_value=result)

    with patch(
        "app.services.admin.geo_eval_settings_service._table_exists",
        new=AsyncMock(return_value=True),
    ):
        gate = await get_geo_eval_gate_config(db)

    assert gate["enabled"] is True
    assert gate["hard_gate"] is True
    assert gate["gate_enabled"] is True
    assert gate["mode"] == "hard"
    assert gate["wiki_checks_enabled"] is False
    assert gate["simulation_pass_score"] == 0.77
    assert gate["audit_pass_score"] == 0.88


@pytest.mark.asyncio
async def test_probe_standards_defaults_and_forced_kpi_guard():
    db = AsyncMock()
    with patch(
        "app.services.admin.geo_eval_settings_service._table_exists",
        new=AsyncMock(return_value=False),
    ):
        standards = await get_probe_standards(db)
    assert standards["metric_primary"] == "open_api"
    assert standards["do_not_overwrite_open_api_kpi"] is True
    assert standards["forbid_corpus_as_l1"] is True
    assert standards["fixture_min_list_acc"] == 0.8
    assert "rank_report_weight" in standards
    assert standards["contract_fields"]


@pytest.mark.asyncio
async def test_save_probe_rejects_overwrite_kpi_false():
    db = AsyncMock()
    body = GeoEvalSettingsBody(
        probe_standards=ProbeStandardsBody(do_not_overwrite_open_api_kpi=False),
    )
    with pytest.raises(HTTPException) as exc:
        await save_geo_eval_settings(db, body)
    assert exc.value.status_code == 400
    assert exc.value.detail == "do_not_overwrite_open_api_kpi_required"


@pytest.mark.asyncio
async def test_save_empty_body_rejected():
    db = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await save_geo_eval_settings(db, GeoEvalSettingsBody())
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_save_gate_upserts_and_returns_bundle():
    db = AsyncMock()
    with (
        patch(
            "app.services.admin.geo_eval_settings_service.upsert_site_setting",
            new=AsyncMock(),
        ) as upsert,
        patch(
            "app.services.admin.geo_eval_settings_service.get_geo_eval_settings_bundle",
            new=AsyncMock(return_value={"gate": {"enabled": False}, "probe_standards": {}}),
        ),
    ):
        out = await save_geo_eval_settings(
            db,
            GeoEvalSettingsBody(
                gate=GeoEvalGateBody(
                    enabled=False,
                    hard_gate=True,
                    wiki_checks_enabled=True,
                    simulation_pass_score=0.5,
                    audit_pass_score=0.6,
                )
            ),
        )
    assert upsert.await_count == 5
    assert out["gate"]["enabled"] is False
