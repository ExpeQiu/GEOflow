import json
from pathlib import Path

import pytest

from app.services.geoeval.tjg_report_parser import (
    TJG_PROVIDER,
    extract_share_token,
    normalize_tjg_platform,
    parse_tjg_report,
)


MINIMAL_FIXTURE = {
    "code": 0,
    "msg": "ok",
    "data": {
        "reportId": 1869322441326592,
        "contentSource": "HBASE",
        "brandReport": {
            "brand_name": "吉利汽车",
            "metrics": {
                "brandName": "吉利汽车",
                "score": 44,
                "brandMentionCount": 73,
                "totalAiResponses": 1800,
                "brandMetrics": [
                    {"label": "品牌可见性指数", "value": "40.6%"},
                    {"label": "行业排名", "value": "No. 6"},
                    {"label": "可见性距行业首位", "value": "29.4%"},
                    {"label": "AI好感度", "value": "84.0%"},
                ],
                "positiveReasons": [{"title": "极端安全", "content": "电池安全"}],
                "negativeReasons": [{"title": "智能化体验不佳", "content": "车机卡顿"}],
                "optimizationSuggestions": [{"title": "竞品超越", "content": "强化 DeepSeek"}],
                "touchpointTree": {"stats": {"total_prompts": 450}},
            },
        },
        "brandVisibility": {"summary": {"avg_rank": 3.5, "avg_visibility": 40.6}},
        "brandCompetitors": {
            "items": [
                {
                    "competitor_id": "c1",
                    "competitor_name": "比亚迪",
                    "logo": "https://example.com/byd.png",
                    "summary": {"avg_visibility": 70, "avg_rank": 2.8},
                    "platforms": [
                        {"platform": "豆包", "summary": {"avg_visibility": 76.7, "avg_rank": 2.1}},
                        {"platform": "DeepSeek", "summary": {"avg_visibility": 70, "avg_rank": 3.1}},
                    ],
                },
                {
                    "competitor_id": "c2",
                    "competitor_name": "吉利汽车",
                    "summary": {"avg_visibility": 40.6, "avg_rank": 3.5},
                    "platforms": [
                        {"platform": "豆包", "summary": {"avg_visibility": 56.7, "avg_rank": 4.9}},
                    ],
                },
            ]
        },
        "diagnosticReportResponseDTO": {
            "brand_name": "吉利汽车 千里浩瀚G-ASD",
            "dataCollectedStartedAt": "2026-06-29",
            "dataCollectedEndedAt": "2026-07-02",
            "diagnosis_data": {
                "intents": [{"name": "城市NOA智驾系统推荐对比", "priority": 11}],
            },
            "metrics": {
                "brandName": "吉利汽车 千里浩瀚G-ASD",
                "score": 30,
                "brandMentionCount": 38,
                "totalAiResponses": 522,
                "brandMetrics": [
                    {"label": "品牌可见性指数", "value": "21.1%"},
                    {"label": "行业排名", "value": "No. 6"},
                    {"label": "可见性距行业首位", "value": "29.5%"},
                    {"label": "AI好感度", "value": "88.9%"},
                ],
                "positiveReasons": [{"title": "提前预判风险", "content": "G-ASD 盲区预判"}],
                "negativeReasons": [{"title": "适配一般", "content": "低线城市无标线道路"}],
                "optimizationSuggestions": [{"title": "核心场景", "content": "城区 NOA 内容"}],
                "touchpointTree": {
                    "tree": [
                        {
                            "label": "智驾敏感型购车者",
                            "children": [
                                {
                                    "label": "城市通勤NOA选车",
                                    "children": [
                                        {
                                            "label": "城市NOA智驾系统推荐对比",
                                            "optimization_unit": {
                                                "avg_visibility": 16.7,
                                                "name": "智驾敏感型购车者/城市通勤NOA选车/城市NOA智驾系统推荐对比",
                                            },
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                    "stats": {"total_prompts": 87},
                },
            },
        },
        "visibilityQueryResponseDTO": {"summary": {"avg_rank": 5.2, "avg_visibility": 21.1}, "total": 6},
        "competitorsQueryResponseDTO": {
            "items": [
                {
                    "competitor_id": "p1",
                    "competitor_name": "小鹏 XNGP",
                    "summary": {"avg_visibility": 50, "avg_rank": 2.0},
                    "platforms": [{"platform": "豆包", "summary": {"avg_visibility": 70, "avg_rank": 2}}],
                },
                {
                    "competitor_id": "p2",
                    "competitor_name": "吉利汽车 千里浩瀚G-ASD",
                    "summary": {"avg_visibility": 21.1, "avg_rank": 5.2},
                    "platforms": [{"platform": "豆包", "summary": {"avg_visibility": 30, "avg_rank": 6.3}}],
                },
            ]
        },
        "promptsQueryResponseDTO": {
            "total": 1,
            "items": [
                {
                    "prompt_id": "prompt-1",
                    "content": "城市NOA哪个品牌的智驾体验最好",
                    "optimization_unit_name": "城市NOA智驾系统推荐对比",
                    "summary": {"avg_visibility": 16.7, "avg_rank": 4},
                    "platforms": [{"platform": "豆包", "summary": {"avg_visibility": 20, "avg_rank": 4}}],
                    "responses": [
                        {
                            "ai_platform": "豆包",
                            "is_mentioned": False,
                            "content": "推荐小鹏 XNGP",
                            "citations": [{"title": "评测", "url": "https://example.com"}],
                            "mentioned_competitors": [{"name": "小鹏 XNGP", "competitor_id": "p1"}],
                        }
                    ],
                }
            ],
        },
        "optimizationStrategy": {
            "industry_description": "汽车 — 智能驾驶新能源轿车",
            "market_opportunity": {
                "monthly_search_estimate": 56400,
                "industry_avg_visibility": 24.1,
                "visibility_gap_to_first": 29.5,
                "first_place_brand": "小鹏 XNGP",
            },
            "platform_recommendation": {
                "recommended_platforms": ["豆包", "文心一言"],
                "platform_scores": [{"platform": "豆包", "score": 88, "reasons": ["日活高"]}],
            },
            "scenario_priorities": [
                {
                    "unit_name": "智驾敏感型购车者/城市通勤NOA选车/城市NOA智驾系统推荐对比",
                    "priority": "高",
                    "current_visibility": 16.7,
                    "visibility_improvement_target": 50,
                    "reason": "ROI 高",
                    "prompts": [],
                }
            ],
        },
        "optimizationDifficultyAssessmentDTO": {
            "difficultyCoefficient": "2.7",
            "regulationCompliance": {"graphScore": "3", "desc": "中难度"},
            "corpusCrowdedness": {"graphScore": "3", "desc": "成熟市场"},
            "brandFoundation": {"graphScore": "2", "desc": "强实体"},
        },
        "featureFlags": {"sentimentClickable": True},
    },
}


def test_extract_share_token():
    token = extract_share_token("https://tuijian.youzan.com/share/diagnostic-report/vZR6M4fF1JKc")
    assert token == "vZR6M4fF1JKc"


def test_normalize_tjg_platform():
    assert normalize_tjg_platform("豆包") == "doubao"
    assert normalize_tjg_platform("DeepSeek") == "deepseek"


def test_parse_tjg_report_minimal():
    parsed = parse_tjg_report(MINIMAL_FIXTURE, token="vZR6M4fF1JKc")
    assert parsed.external_report_id == "1869322441326592"
    assert parsed.brand_name == "吉利汽车"
    assert parsed.product_name == "吉利汽车 千里浩瀚G-ASD"
    assert parsed.brand_metrics.visibility_pct == 40.6
    assert parsed.product_metrics.visibility_pct == 21.1
    assert parsed.product_metrics.weighted_rank == 5.2
    assert len(parsed.brand_competitors) == 2
    assert any(c.is_self for c in parsed.brand_competitors)
    assert len(parsed.scenes) == 1
    assert parsed.scenes[0].gap_priority == "high"
    assert len(parsed.prompts) == 1
    assert parsed.prompts[0].responses[0]["platform"] == "doubao"
    assert parsed.sections["source"]["provider"] == TJG_PROVIDER
    assert "brand" in parsed.sections
    assert "touchpoint_tree" in parsed.sections["product"]
    assert parsed.sections["strategy"]["scenario_priorities"][0]["visibility_improvement_target"] == 50


def test_parse_competitor_mentions_json_string():
    from app.services.geoeval.tjg_report_parser import _parse_competitor_mentions

    raw = ['{"name":"华为 ADS","competitor_id":"x"}', "比亚迪"]
    items = _parse_competitor_mentions(raw)
    assert items[0]["name"] == "华为 ADS"
    assert items[1]["name"] == "比亚迪"


def test_parse_tjg_report_synthesizes_self_brand_when_missing():
    payload = json.loads(json.dumps(MINIMAL_FIXTURE))
    items = payload["data"]["brandCompetitors"]["items"]
    payload["data"]["brandCompetitors"]["items"] = [i for i in items if i["competitor_name"] != "吉利汽车"]
    payload["data"]["brandVisibility"]["platforms"] = [
        {"platform": "豆包", "summary": {"avg_visibility": 56.7, "avg_rank": 4.9}},
        {"platform": "DeepSeek", "summary": {"avg_visibility": 40.0, "avg_rank": 5.1}},
    ]
    parsed = parse_tjg_report(payload, token="vZR6M4fF1JKc")
    assert len(parsed.brand_competitors) == 2
    self_rows = [c for c in parsed.brand_competitors if c.is_self]
    assert len(self_rows) == 1
    assert self_rows[0].name == "吉利汽车"
    matrix = parsed.sections["brand"]["competitor_matrix"]
    doubao = next(r for r in matrix if r["platform"] == "doubao")
    self_cell = next(b for b in doubao["brands"] if b["is_self"])
    assert self_cell["name"] == "吉利汽车"


@pytest.mark.skipif(not Path("/tmp/tjg_report.json").exists(), reason="live fixture not downloaded")
def test_parse_tjg_report_live_fixture():
    payload = json.loads(Path("/tmp/tjg_report.json").read_text(encoding="utf-8"))
    parsed = parse_tjg_report(payload, token="vZR6M4fF1JKc")
    assert parsed.brand_metrics.visibility_pct == pytest.approx(40.6, rel=0.01)
    assert parsed.product_metrics.visibility_pct == pytest.approx(21.1, rel=0.01)
    assert len(parsed.prompts) >= 1
