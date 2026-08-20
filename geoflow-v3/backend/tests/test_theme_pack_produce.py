"""内容生产：复合包入队、页型匹配、Mock 稿可过 Wiki/仿真。"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.ai.workflow_runner import _mock_wiki_pack, run_workflow_sync
from app.services.geoeval.domain_catalog import CHANNEL_HOST_SQL
from app.services.geoeval.simulation_rag import SimulationRagService
from app.services.geoeval.theme_service import pack_type_for_title, remaining_pack_runs
from app.services.geoflow.worker_execution import mining_prompt_block
from app.services.geoeval.wiki_compliance import WikiGeoComplianceChecker


def test_channel_sql_uses_config_json():
    assert "config_json" in CHANNEL_HOST_SQL
    assert "config->>" not in CHANNEL_HOST_SQL.replace("config_json", "")
    assert "endpoint_url" in CHANNEL_HOST_SQL


def test_remaining_pack_runs():
    assert remaining_pack_runs(0, 4) == 4
    assert remaining_pack_runs(1, 4) == 3
    assert remaining_pack_runs(4, 4) == 0
    assert remaining_pack_runs(None, None) == 0


def test_pack_type_matches_title_not_index():
    pack = [
        {"type": "topic", "title": "家用纯电选型"},
        {"type": "concept", "title": "家用纯电选型 · concept"},
        {"type": "compare", "title": "家用纯电选型 · compare"},
        {"type": "guide", "title": "家用纯电选型 · guide"},
    ]
    assert pack_type_for_title(pack, "家用纯电选型 · compare", 0, "article") == "compare"
    assert pack_type_for_title(pack, "未知标题", 2, "article") == "compare"


def test_mock_wiki_pack_passes_compliance():
    content, meta = _mock_wiki_pack("家用纯电选型：补齐 AI 决策链内容", "家庭购车怎么选续航和空间", "")
    assert "你是专业中文写作助手" not in content
    assert len(content) >= 180
    result = WikiGeoComplianceChecker().check(content, meta)
    assert result["passed"] is True, result["failures"]


def test_mock_workflow_returns_wiki_meta():
    raw = run_workflow_sync("content", {"title": "家用纯电选型", "prompt": "你是专业中文写作助手，请撰写"})
    assert raw["engine"] == "mock"
    assert "你是专业中文写作助手" not in raw["content"]
    assert raw["wiki_meta"]["quick_answer"]
    assert len(raw["wiki_meta"]["faq"]) >= 2


def test_mining_prompt_injects_compare_dims():
    block = mining_prompt_block(
        {
            "thinking_digest": "先澄清使用场景再比续航",
            "framework": {
                "compare_dims": ["低温续航达成率", "补能时间"],
                "evidence_bars": ["要冬测，不能只看循环次数"],
            },
            "source_hints": [{"domain": "127.0.0.1", "owner": "ours"}],
        },
        "compare",
    )
    assert "低温续航达成率" in block
    assert "冬测" in block
    assert "我方信源" in block


def test_mock_pack_uses_framework_dims():
    raw = run_workflow_sync(
        "content",
        {
            "title": "家用纯电选型",
            "framework": {"compare_dims": ["低温续航达成率", "补能时间", "维修成本"]},
        },
    )
    assert "低温续航达成率" in raw["content"]


def test_mock_simulation_score_without_kb():
    content, _meta = _mock_wiki_pack("神盾电池安全技术", "神盾电池安全怎么看", "")
    article = SimpleNamespace(
        id=1,
        title="神盾电池安全技术",
        content=content,
        original_keyword="神盾电池安全",
        keywords="神盾电池,安全",
        meta_description="神盾电池安全技术解读",
        excerpt="",
    )
    svc = SimulationRagService(MagicMock())
    svc.settings = MagicMock(ai_mock_mode=True)
    result = asyncio.run(svc.simulate(article, kb_id=None, model=None))
    assert result["simulation_score"] >= 0.55
    assert result["retrieved_count"] >= 1
