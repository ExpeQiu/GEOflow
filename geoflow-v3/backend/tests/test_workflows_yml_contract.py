"""workflows.yml 类型白名单 — content-LangGraph-CLI 外挂对齐用（主栈真源）。"""

from pathlib import Path

import yaml

WORKFLOWS_YML = (
    Path(__file__).resolve().parents[1] / "app" / "ai" / "config" / "workflows.yml"
)

REQUIRED_TYPES = {"content", "content_pipeline", "url_import", "semantic_chunk"}


def test_workflows_yml_has_required_types():
    assert WORKFLOWS_YML.is_file(), f"missing {WORKFLOWS_YML}"
    data = yaml.safe_load(WORKFLOWS_YML.read_text(encoding="utf-8"))
    workflows = data.get("workflows") or {}
    missing = REQUIRED_TYPES - set(workflows)
    assert not missing, f"workflows.yml missing types: {missing}"


def test_each_workflow_has_nodes_and_edges():
    data = yaml.safe_load(WORKFLOWS_YML.read_text(encoding="utf-8"))
    for name in REQUIRED_TYPES:
        wf = data["workflows"][name]
        assert wf.get("nodes"), f"{name} missing nodes"
        assert wf.get("edges") is not None, f"{name} missing edges"
