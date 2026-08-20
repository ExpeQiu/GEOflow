"""ADR-012：三层探针口径、框架抽取、Mock 框架轨。"""

from __future__ import annotations

import pytest

from app.services.geoeval.framework_extractor import (
    digest_framework,
    extract_framework,
    longtail_from_framework,
)
from app.services.geoeval.platform_connectors.api_connector import (
    MOCK_COT,
    split_reasoning,
)
from app.services.geoeval.platform_connectors.base import ProbeOutcome
from app.services.geoeval.probe_scheme import (
    GRADE_NONE,
    GRADE_RAW,
    GRADE_SUMMARY,
    METRIC_FRAMEWORK,
    SCHEME_CEND,
    SCHEME_FRAMEWORK_API,
    SCHEME_OPEN_API,
    north_star_sql_filters,
    stamp_outcome,
)


def test_split_reasoning_field_and_think_tags():
    text, reason = split_reasoning({"reasoning_content": "内部推理", "content": "答案"}, "")
    assert reason == "内部推理"
    assert text == "答案"
    text2, reason2 = split_reasoning({}, "<think>先比安全</think>\n最终选 LFP")
    assert "安全" in reason2
    assert "LFP" in text2
    assert "<think>" not in text2


def test_stamp_open_api_is_c_track_only():
    o = ProbeOutcome(
        question_id=1,
        platform="deepseek",
        brand_rank=2,
        mentioned=True,
        snippet="答",
        engine="api",
        thinking_text="不该进日扫 A 轨",
        urls=["https://example.com"],
    )
    stamp_outcome(o, scheme=SCHEME_OPEN_API)
    assert o.scheme == SCHEME_OPEN_API
    assert o.tracks == ["B", "C"]
    assert o.reasoning_grade == GRADE_NONE
    assert o.metric_kind == "open_api"


def test_stamp_framework_raw_tracks():
    o = ProbeOutcome(
        question_id=1,
        platform="deepseek",
        brand_rank=1,
        mentioned=True,
        snippet="答",
        engine="api",
        thinking_text=MOCK_COT,
    )
    stamp_outcome(o, scheme=SCHEME_FRAMEWORK_API)
    assert o.tracks == ["A", "C"]
    assert o.reasoning_grade == GRADE_RAW
    assert o.metric_kind == METRIC_FRAMEWORK


def test_stamp_cend_summary_not_raw():
    o = ProbeOutcome(
        question_id=1,
        platform="yuanbao",
        brand_rank=2,
        mentioned=True,
        snippet="答",
        engine="cend_browser",
        thinking_text="UI 摘要",
        citation_urls=["https://www.autohome.com.cn/x"],
        metric_kind="cend_sample",
    )
    stamp_outcome(o, scheme=SCHEME_CEND)
    assert o.reasoning_grade == GRADE_SUMMARY
    assert "A" not in o.tracks
    assert o.tracks == ["B", "C"]
    assert "cend_sample" in north_star_sql_filters(has_scheme_col=True)
    sql = north_star_sql_filters(has_scheme_col=True)
    assert "engine" in sql and "open_api" in sql
    assert "framework_sample" in sql


def test_extract_framework_six_classes():
    fw = extract_framework(MOCK_COT, scene_name="三电", intent="怎么选")
    assert fw["sub_questions"]
    assert fw["compare_dims"]
    assert fw["evidence_bars"]
    assert fw["scene_constraints"]
    assert fw["open_gaps"]
    digest = digest_framework(fw)
    assert "维度" in digest or "拆解" in digest
    qs = longtail_from_framework(fw, scene_name="三电", probe_texts=["磷酸铁锂和三元锂到底怎么选？"])
    assert qs
    assert all("磷酸铁锂和三元锂到底怎么选" not in q for q in qs)


def test_digest_empty_does_not_use_snippet():
    assert "framework_api" in digest_framework(None)
    assert "framework_api" in digest_framework({})


@pytest.mark.asyncio
async def test_api_framework_mock(monkeypatch):
    monkeypatch.setenv("AI_MOCK_MODE", "true")
    from app.services.geoeval.platform_connectors.api_connector import ApiConnector

    conn = ApiConnector()
    outcome = await conn.probe(
        question_text="磷酸铁锂和三元锂到底怎么选？",
        priority=90,
        platform="deepseek",
        corpus=[],
        brand_list=["吉利"],
        scheme=SCHEME_FRAMEWORK_API,
    )
    assert outcome is not None
    assert outcome.engine == "api"
    assert outcome.scheme == SCHEME_FRAMEWORK_API
    assert outcome.reasoning_grade == GRADE_RAW
    assert "对比维度" in (outcome.thinking_text or "")
    assert "A" in outcome.tracks
    assert outcome.metric_kind == METRIC_FRAMEWORK


def test_cend_mock_stamped(monkeypatch):
    monkeypatch.setenv("CEND_MOCK_MODE", "true")
    from app.services.geoeval.platform_connectors.cend.connector import CendBrowserConnector
    import asyncio

    outcome = asyncio.run(
        CendBrowserConnector().probe(
            question_text="15-25万智能驾驶新能源有哪些？",
            platform="yuanbao",
            brand_list=["吉利"],
            competitor_brands=["小鹏"],
            question_id=1,
        )
    )
    assert outcome.scheme == SCHEME_CEND
    assert outcome.reasoning_grade == GRADE_SUMMARY
    assert outcome.metric_kind == "cend_sample"
