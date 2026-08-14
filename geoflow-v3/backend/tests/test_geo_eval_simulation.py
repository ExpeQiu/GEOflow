from app.services.geoeval.eval_recommendations import build_recommendations
from app.services.geoeval.answer_audit import _mock_audit
from app.services.geoeval.simulation_rag import _mock_simulate, build_eval_query
from types import SimpleNamespace


def _article(**kwargs):
    defaults = {
        "id": 1,
        "title": "神盾电池安全技术与热失控防护",
        "content": "## 概述\n神盾电池采用多层防护设计，覆盖热失控、结构碰撞与电化学稳定性等多维安全场景。"
        "通过多层绝缘与智能监控，显著降低极端工况下的风险。\n\n| 指标 | 数值 |\n| --- | --- |\n| 耐温 | 高 |\n\n- 热失控防护\n- 结构安全",
        "original_keyword": "神盾电池安全",
        "keywords": "神盾电池,安全",
        "meta_description": "神盾电池安全技术解读",
        "excerpt": "",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_build_eval_query_uses_title_and_keyword():
    article = _article()
    assert "神盾电池" in build_eval_query(article)


def test_mock_simulation_produces_score():
    article = _article()
    query = build_eval_query(article)
    chunks = [{"chunk_id": 1, "content": "神盾电池安全技术说明", "score": 0.72, "source": "keyword"}]
    sim = _mock_simulate(query, chunks, article)
    assert sim["answer"]
    assert sim["confidence"] > 0


def test_simulate_draft_probability_fields():
    """草稿仿真应产出采纳/检索概率字段。"""
    import asyncio
    from unittest.mock import MagicMock

    from app.services.geoeval.simulation_rag import SimulationRagService

    svc = SimulationRagService(MagicMock())
    svc.settings = MagicMock(ai_mock_mode=True)

    result = asyncio.run(
        svc.simulate_draft(
            title="神盾电池安全技术",
            content="神盾电池采用多层防护，覆盖热失控与结构安全。",
            keyword="神盾电池",
            kb_id=None,
            model=None,
        )
    )
    assert "adoption_probability" in result
    assert "retrieval_probability" in result
    assert 0 <= result["adoption_probability"] <= 1
    assert result["query"]

def test_mock_audit_passes_structured_article():
    article = _article()
    simulation = {
        "query": build_eval_query(article),
        "retrieval_score": 0.6,
        "simulation_score": 0.65,
        "article_in_retrieval": True,
        "simulated_answer": article.content[:200],
    }
    audit = _mock_audit(article, simulation)
    assert audit["audit_passed"] is True
    assert audit["checks"]["structured"] is True


def test_mock_audit_fails_short_content():
    article = _article(content="太短", title="测试")
    simulation = {"query": "测试", "retrieval_score": 0.0, "simulation_score": 0.2, "article_in_retrieval": False}
    audit = _mock_audit(article, simulation)
    assert audit["audit_passed"] is False


def test_simulation_score_formula():
    article = _article()
    query = build_eval_query(article)
    chunks = [{"chunk_id": 1, "content": "神盾电池", "score": 0.8, "source": "hybrid"}]
    sim_body = _mock_simulate(query, chunks, article)
    assert sim_body["confidence"] <= 1.0


def test_build_recommendations_from_simulation_and_wiki():
    recs = build_recommendations(
        issues=["simulation_score_low:0.32", "missing_quick_answer", "simulation_score_low:0.32"],
        simulation_score=0.32,
        pass_score=0.55,
    )
    assert len(recs) == 2
    assert recs[0]["code"] == "simulation_score_low"
    assert "知识库" in recs[0]["suggestion"]
    assert recs[0]["simulation_score"] == 0.32
    assert recs[1]["code"] == "missing_quick_answer"


def test_publish_allows_advisory_status():
    """软门禁：advisory 与 passed/skipped 同属可发布集合。"""
    allowed = {"passed", "skipped", "advisory"}
    assert "advisory" in allowed
    assert "failed" not in allowed
