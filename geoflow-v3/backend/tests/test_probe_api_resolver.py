"""采集平台 API 配置解析。"""

from types import SimpleNamespace
from unittest.mock import patch

from app.services.geoeval.probe_api_resolver import resolve_probe_api_endpoint


def test_resolve_enterprise_gateway():
    cfg = {"global_mode": "enterprise-gateway", "platforms": {}}
    fake = SimpleNamespace(
        enterprise_ai_gateway_api_key="ent-key",
        enterprise_ai_text_base_url="https://ai-gateway-office.zeekrlife.com/v1",
        enterprise_ai_text_model="gpt-4o",
        lobster_proxy_token="",
        lobster_proxy_base="http://127.0.0.1:56045",
        lobster_api_root="v1",
    )
    with patch("app.services.geoeval.probe_api_resolver.get_settings", return_value=fake):
        with patch("app.services.geoeval.probe_api_resolver.enterprise_ready", return_value=True):
            ep = resolve_probe_api_endpoint("deepseek", cfg)
    assert ep is not None
    assert ep.via == "enterprise-gateway"
    assert ep.api_key == "ent-key"
    assert "ai-gateway-office" in ep.base_url


def test_cend_platform_returns_none():
    assert resolve_probe_api_endpoint("yuanbao", {}) is None
