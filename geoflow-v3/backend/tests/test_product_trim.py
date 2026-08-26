"""产品收口：legacy 直建 Task 已移除；渠道默认仅 GEOweb。"""

import pytest
from fastapi import HTTPException

from app.services.admin.distribution_form_service import build_distribution_form_options
from app.services.geoeval.gap_task_generator import create_task_from_scene_gap


@pytest.mark.asyncio
async def test_legacy_direct_task_returns_410():
    with pytest.raises(HTTPException) as exc:
        await create_task_from_scene_gap(None, 1, legacy_direct_task=True)  # type: ignore[arg-type]
    assert exc.value.status_code == 410
    assert "legacy_direct_task_removed" in str(exc.value.detail)


def test_distribution_form_defaults_to_geoweb_only():
    opts = build_distribution_form_options()
    assert opts["default_channel_type"] == "geoweb"
    assert opts["channel_types"] == ["geoweb"]
    assert "wordpress_rest" in opts["advanced_channel_types"]


def test_dashboard_automation_points_to_wiki_not_articles():
    from app.services.admin.dashboard_automation import build_automation

    auto = build_automation({"pending_review": 1, "knowledge_bases": 1})
    hrefs = [a["href"] for n in auto["flow_nodes"] for a in n["actions"]]
    hrefs += [r["href"] for r in auto["recommendations"]]
    hrefs += [row["href"] for lane in auto["lanes"] for row in lane["rows"]]
    assert "/operations/wiki" in hrefs
    assert "/operations/articles" not in hrefs

