"""P2：citation_grounded 口径、域名归属、交叉判定、Mock 引用轨。"""

from __future__ import annotations

import pytest

from app.services.geoeval.cross_track_service import (
    FLAG_FRAMEWORK_GAP,
    FLAG_GOLD,
    FLAG_MENTION_NO_OURS,
    FLAG_OURS_CITED,
    diagnose_tracks,
)
from app.services.geoeval.domain_catalog import (
    OWNER_COMPETITOR,
    OWNER_OURS,
    OWNER_THIRD,
    annotate_urls,
    classify_owner,
)
from app.services.geoeval.platform_connectors.api_connector import MOCK_CITATION_ANSWER
from app.services.geoeval.platform_connectors.base import ProbeOutcome
from app.services.geoeval.probe_scheme import (
    GRADE_NONE,
    METRIC_CITATION,
    SCHEME_CITATION,
    north_star_sql_filters,
    stamp_outcome,
)


def test_stamp_citation_tracks_and_kpi_excluded():
    o = ProbeOutcome(
        question_id=1,
        platform="doubao",
        brand_rank=1,
        mentioned=True,
        snippet="答",
        engine="api",
        urls=["https://127.0.0.1:3070/concepts/x"],
        citation_urls=["https://127.0.0.1:3070/concepts/x"],
    )
    stamp_outcome(o, scheme=SCHEME_CITATION)
    assert o.scheme == SCHEME_CITATION
    assert o.tracks == ["B", "C"]
    assert o.reasoning_grade == GRADE_NONE
    assert o.metric_kind == METRIC_CITATION
    sql = north_star_sql_filters(has_scheme_col=True)
    assert "citation_sample" in sql
    assert "framework_sample" in sql
    assert "cend_sample" in sql


def test_classify_owner_geoweb_official_vs_wiki():
    official = ["127.0.0.1", "localhost"]
    wiki = ["wikipedia.org", "baike.baidu.com"]
    comps = ["xiaopeng.com"]
    assert classify_owner("https://127.0.0.1:3070/concepts/lfp", official=official, wiki=wiki) == OWNER_OURS
    assert classify_owner("https://zh.wikipedia.org/wiki/x", official=official, wiki=wiki) == OWNER_THIRD
    assert classify_owner("https://www.autohome.com.cn/x", official=official, wiki=wiki) == OWNER_THIRD
    assert classify_owner("https://www.xiaopeng.com/a", official=official, competitors=comps, wiki=wiki) == OWNER_COMPETITOR
    hints = annotate_urls(
        ["https://127.0.0.1:3070/a", "https://www.autohome.com.cn/b"],
        official=official,
        wiki=wiki,
    )
    assert hints[0]["owner"] == OWNER_OURS
    assert hints[1]["owner"] == OWNER_THIRD


def test_cross_mention_no_ours():
    d = diagnose_tracks(
        mentioned=True,
        urls=["https://www.autohome.com.cn/x"],
        official=["127.0.0.1"],
        snippet="吉利值得看",
        has_c=True,
        has_b=True,
    )
    assert FLAG_MENTION_NO_OURS in d["flags"]
    assert FLAG_OURS_CITED not in d["flags"]


def test_cross_framework_not_in_answer():
    d = diagnose_tracks(
        mentioned=True,
        urls=["https://127.0.0.1:3070/x"],
        official=["127.0.0.1"],
        compare_dims=["对比维度：安全、低温续航、循环寿命"],
        snippet="吉利口碑不错，推荐入手。",
        has_a=True,
        has_c=True,
        has_b=True,
    )
    assert FLAG_FRAMEWORK_GAP in d["flags"]
    assert d["unused_dims"]


def test_cross_gold_abc():
    d = diagnose_tracks(
        mentioned=True,
        urls=["https://127.0.0.1:3070/concepts/lfp"],
        official=["127.0.0.1"],
        compare_dims=["对比维度：安全"],
        snippet="安全与低温续航是选型关键，吉利可参考。",
        has_a=True,
        has_b=True,
        has_c=True,
    )
    assert FLAG_OURS_CITED in d["flags"]
    assert FLAG_GOLD in d["flags"]
    assert FLAG_MENTION_NO_OURS not in d["flags"]


@pytest.mark.asyncio
async def test_api_citation_mock(monkeypatch):
    monkeypatch.setenv("AI_MOCK_MODE", "true")
    from app.services.geoeval.platform_connectors.api_connector import ApiConnector

    conn = ApiConnector()
    outcome = await conn.probe(
        question_text="磷酸铁锂和三元锂到底怎么选？",
        priority=90,
        platform="kimi",
        corpus=[],
        brand_list=["吉利"],
        scheme=SCHEME_CITATION,
        official_domains=["127.0.0.1", "localhost"],
        wiki_domains=["wikipedia.org"],
    )
    assert outcome is not None
    assert outcome.scheme == SCHEME_CITATION
    assert outcome.metric_kind == METRIC_CITATION
    assert "B" in outcome.tracks
    assert outcome.citation_urls or outcome.urls
    assert outcome.match_type in ("domain_official", "domain_wiki")
    assert outcome.citation_method == "mock"
    assert "autohome" in MOCK_CITATION_ANSWER
    assert "127.0.0.1" in MOCK_CITATION_ANSWER
