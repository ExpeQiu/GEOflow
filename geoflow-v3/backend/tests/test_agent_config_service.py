"""Admin Content Agent 节点配置 API 测试。"""

from app.services.admin.agent_config_service import list_agents


def test_list_agents_from_yaml():
    data = list_agents()
    assert "items" in data
    assert len(data["items"]) >= 1
    ids = {item["id"] for item in data["items"]}
    assert "pipeline_writer" in ids or "content_drafter" in ids
    for item in data["items"]:
        assert item["system_prompt"]
        assert "temperature" in item
        assert "used_by" in item
