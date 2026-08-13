"""北极星 KPI 纯函数单测。"""

from app.services.geoeval.north_star_kpi import (
    aggregate_domain_top3,
    gap_vs_leader_pp,
    is_north_star_intent,
    mention_rate_pct,
    normalize_intent_type,
    sentiment_negative_pct,
    topn_pct,
    win_rate_pct,
)
from app.services.geoeval.quality_metrics_service import extract_params_from_text, score_param_consistency
from app.services.geoeval.source_metrics_service import classify_domain


def test_topn_pct_basic():
    ranks = [1, 2, 3, 4, 5, None]
    assert topn_pct(ranks, 3) == 60.0  # 3/5
    assert topn_pct(ranks, 1) == 20.0
    assert topn_pct(ranks, 5) == 100.0
    assert topn_pct([], 3) is None


def test_gap_and_mention():
    assert gap_vs_leader_pp(40.0, 55.0) == -15.0
    assert gap_vs_leader_pp(60.0, 55.0) == 5.0
    assert mention_rate_pct(2, 5) == 40.0
    assert sentiment_negative_pct(2, 1, 1) == 25.0
    assert win_rate_pct(3, 10) == 30.0


def test_intent_normalize():
    assert normalize_intent_type("COMPARE") == "compare"
    assert is_north_star_intent("decision")
    assert not is_north_star_intent("cognition")


def test_domain_top3():
    samples = [("智驾", 1), ("智驾", 4), ("三电", 2), ("座舱", None)]
    out = aggregate_domain_top3(samples)
    assert out["智驾"] == 50.0
    assert out["三电"] == 100.0


def test_param_extract_and_consistency():
    text = "吉利智驾算力达 1440 TOPS，搭载 2 颗激光雷达，开通 100 城"
    found = extract_params_from_text(text)
    assert found["compute_tops"] == "1440"
    assert found["lidar_count"] == "2"
    ssot = {"compute_tops": "1440", "lidar_count": "2", "noa_cities": "100"}
    scored = score_param_consistency([text], ssot)
    assert scored["param_consistency_pct"] == 100.0
    assert scored["gate_pass"] is True


def test_classify_domain():
    assert classify_domain("https://wiki.geely.com/ai-facts", ["geely.com"]) == "official"
    assert classify_domain("https://www.dongchedi.com/article/1") == "third_party"
