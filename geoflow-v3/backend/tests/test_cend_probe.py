"""Phase0/1：api URL 落 citations；C 端解析与 Mock 探针。"""

from __future__ import annotations

import os

import pytest

from app.services.geoeval.platform_connectors.base import ProbeOutcome
from app.services.geoeval.platform_connectors.cend.parse_helpers import (
    extract_keywords,
    extract_rank_blocks,
    extract_decision_table_heuristic,
)
from app.services.geoeval.platform_connectors.cend.connector import CendBrowserConnector
from app.services.geoeval.platform_connectors.cend.registry import list_cend_platforms, get_cend_adapter


def test_cend_platforms_six():
    plats = list_cend_platforms()
    assert set(plats) == {"yuanbao", "doubao", "tongyi", "kimi", "wenxin", "deepseek"}
    for p in plats:
        ad = get_cend_adapter(p)
        assert ad.platform == p
        assert ad.start_url.startswith("http")


def test_extract_rank_blocks_and_keywords():
    text = """
### 城区NOA第一梯队：小鹏阵营
1. 小鹏 G6
2. 吉利 银河
3. 问界 M5

### 华为乾崑ADS阵营
1. 问界 M5
2. 深蓝 S07
"""
    blocks = extract_rank_blocks(text, ["吉利", "银河"])
    assert len(blocks) >= 1
    assert any("阵营" in b["camp"] or "梯队" in b["camp"] for b in blocks)
    kws = extract_keywords(text, ["吉利"])
    assert "城区NOA" in kws or "智驾" in kws or "吉利" in kws


def test_decision_table_heuristic():
    md = """
| 诉求 | 首选 | 备选 |
| --- | --- | --- |
| 城区NOA最强 | 小鹏G6 | 吉利银河 |
| 华为生态 | 问界M5 | 深蓝S07 |
"""
    rows = extract_decision_table_heuristic(md)
    assert len(rows) >= 1


def test_cend_mock_outcome(monkeypatch):
    monkeypatch.setenv("CEND_MOCK_MODE", "true")
    conn = CendBrowserConnector()
    import asyncio

    outcome = asyncio.run(
        conn.probe(
            question_text="15-25万智能驾驶新能源有哪些？",
            platform="yuanbao",
            brand_list=["吉利"],
            competitor_brands=["小鹏", "比亚迪"],
            question_id=1,
        )
    )
    assert outcome.engine == "cend_browser"
    assert outcome.metric_kind == "cend_sample"
    assert outcome.evidence_level == "L2"
    assert outcome.thinking_text
    assert len(outcome.citation_urls) >= 1
    assert outcome.rank_blocks


def test_persist_url_citations_helper_signature():
    """确保 Phase0 辅助函数可导入。"""
    from app.services.geoeval.monitor_probe import _persist_url_citations, _insert_citation_row

    assert callable(_persist_url_citations)
    assert callable(_insert_citation_row)


def test_probe_outcome_cend_fields():
    o = ProbeOutcome(
        question_id=1,
        platform="yuanbao",
        brand_rank=2,
        mentioned=True,
        snippet="test",
        engine="cend_browser",
        thinking_text="思考",
        keywords=["城区NOA"],
        citation_urls=["https://www.autohome.com.cn/x"],
        metric_kind="cend_sample",
        evidence_level="L2",
    )
    assert o.citation_urls[0].startswith("http")
    assert o.metric_kind == "cend_sample"
