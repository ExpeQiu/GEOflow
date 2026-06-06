"""graph_runner 单元测试（线性路径，无需 LangGraph 包）。"""

from __future__ import annotations

import pytest

from app.orchestration import graph_runner
from app.workflows.handlers import cite_check, content_finalize


@pytest.mark.asyncio
async def test_resolve_next_nodes_needs_revision():
    edges = [
        {"from": "cite_check", "to": "revise", "when": "needs_revision"},
        {"from": "cite_check", "to": "finalize", "when": "ok"},
    ]
    assert graph_runner._resolve_next_nodes("cite_check", edges, {"needs_revision": True}) == ["revise"]
    assert graph_runner._resolve_next_nodes("cite_check", edges, {"needs_revision": False}) == ["finalize"]


@pytest.mark.asyncio
async def test_cite_check_sets_needs_revision():
    state = {
        "content": "无引用正文",
        "payload": {"evidence": [{"id": "K1", "content": "证据"}]},
        "trace": [],
    }
    patch = await cite_check(state)
    assert patch.get("needs_revision") is True
    assert "cite_check" in patch.get("trace", [])


@pytest.mark.asyncio
async def test_content_finalize_assembles_result():
    state = {
        "content": "# 标题\n正文 [K1]",
        "citations": ["K1"],
        "trace": ["draft", "cite_check"],
    }
    patch = await content_finalize(state)
    assert patch["result"]["content"] == "# 标题\n正文 [K1]"
    assert patch["result"]["citations"] == ["K1"]
    assert "finalize" in patch["trace"]


def test_extract_result_prefers_state_result():
    state = {
        "result": {"content": "hello", "citations": []},
        "trace": ["draft", "finalize"],
    }
    result = graph_runner._extract_result("content", state)
    assert result["content"] == "hello"
    assert result["trace"]["steps"] == ["draft", "finalize"]


def test_config_cache_key_changes_with_workflow_type():
    key_a = graph_runner._config_cache_key("content")
    key_b = graph_runner._config_cache_key("semantic_chunk")
    assert key_a != key_b


def test_matches_when_fast_and_deep_mode():
    assert graph_runner._matches_when("fast_mode", {"pipeline_path": "fast"})
    assert graph_runner._matches_when("deep_mode", {"pipeline_path": "deep"})
    assert not graph_runner._matches_when("fast_mode", {"pipeline_path": "deep"})


def test_matches_when_skip_compliance_and_compliance():
    assert graph_runner._matches_when("skip_compliance", {"skip_compliance": True, "needs_revision": False})
    assert graph_runner._matches_when("compliance_pass", {"compliance": {"passed": True}})
    assert graph_runner._matches_when("compliance_reject", {"compliance": {"passed": False}})


@pytest.mark.asyncio
async def test_pipeline_finalize_assembles_structured_result():
    from app.workflows.handlers.content_pipeline import pipeline_finalize

    state = {
        "content": "# 标题\n正文 [K1]",
        "citations": ["K1"],
        "chief_brief": "brief",
        "pipeline_path": "deep",
        "cross_checks": [{"node": "post_writer", "passed": True}],
        "compliance": {"passed": True, "violations": []},
        "memory_patch": {"summary": "s"},
        "trace": ["chief"],
    }
    patch = await pipeline_finalize(state)
    assert patch["result"]["content"] == "# 标题\n正文 [K1]"
    assert patch["result"]["pipeline_mode"] == "deep"
    assert patch["result"]["memory_patch"]["summary"] == "s"
