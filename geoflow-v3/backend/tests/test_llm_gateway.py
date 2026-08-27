"""LLM 网关：企业 AI Gateway 与 Lobster 遗留解析。"""

from types import SimpleNamespace
from unittest.mock import patch

from app.ai.llm_gateway import (
    configured_api_resource,
    effective_gateway_mode,
    enterprise_ready,
    infer_vendor,
    public_model_view,
    resolve_llm_endpoint,
    set_runtime_api_resource,
)


def test_infer_vendor_zhipu_and_kimi():
    assert infer_vendor("glm-4-flash", "https://open.bigmodel.cn/api/paas/v4", "智谱") == "zhipu"
    assert infer_vendor("kimi-k2.6", "", "Kimi") == "moonshot"
    assert infer_vendor("qwen-plus", "", "") == "qwen"
    assert infer_vendor("gpt-4o", "https://ai-gateway-office.zeekrlife.com/v1", "企业") == "enterprise"


def test_resource_switch_vendor_vs_geely():
    fake = SimpleNamespace(
        llm_gateway_mode="enterprise-gateway",
        enterprise_ai_gateway_api_key="ent-key",
        enterprise_ai_text_base_url="https://ai-gateway-office.zeekrlife.com/v1",
        enterprise_ai_text_model="gpt-4o",
        lobster_proxy_token="",
        lobster_proxy_base="http://127.0.0.1:56045",
        lobster_api_root="v1",
    )
    with patch("app.ai.llm_gateway.get_settings", return_value=fake):
        set_runtime_api_resource("vendor")
        assert configured_api_resource() == "vendor"
        assert effective_gateway_mode() == "direct"
        set_runtime_api_resource("geely")
        assert configured_api_resource() == "geely"
        assert effective_gateway_mode() == "enterprise-gateway"
    set_runtime_api_resource(None)


def test_enterprise_resolve_uses_gateway_key_not_vendor_key():
    model = SimpleNamespace(
        id=1,
        name="企业 Gateway Chat",
        model_id="gpt-4o",
        api_url="https://ai-gateway-office.zeekrlife.com/v1",
        api_key="sk-vendor-secret",
        vendor="enterprise",
        connection_kind="inherit",
        model_type="chat",
        failover_priority=10,
        status="active",
    )
    fake = SimpleNamespace(
        llm_gateway_mode="enterprise-gateway",
        enterprise_ai_gateway_api_key="ent-key-abc",
        enterprise_ai_text_base_url="https://ai-gateway-office.zeekrlife.com/v1",
        enterprise_ai_text_model="gpt-4o",
        lobster_proxy_token="",
        lobster_proxy_base="http://127.0.0.1:56045",
        lobster_api_root="v1",
    )
    set_runtime_api_resource("geely")
    with patch("app.ai.llm_gateway.get_settings", return_value=fake):
        ep = resolve_llm_endpoint(model)
        view = public_model_view(model)
    assert ep.via == "enterprise-gateway"
    assert ep.api_key == "ent-key-abc"
    assert ep.base_url == "https://ai-gateway-office.zeekrlife.com/v1"
    assert view["resolved_via"] == "enterprise-gateway"
    assert "sk-vendor" not in str(view)
    set_runtime_api_resource(None)


def test_lobster_resolve_uses_proxy_token_not_vendor_key():
    model = SimpleNamespace(
        id=1,
        name="智谱 GLM",
        model_id="glm-4-flash",
        api_url="https://open.bigmodel.cn/api/paas/v4",
        api_key="sk-vendor-secret",
        vendor="zhipu",
        connection_kind="lobster",
        model_type="chat",
        failover_priority=10,
        status="active",
    )
    fake = SimpleNamespace(
        llm_gateway_mode="lobster",
        enterprise_ai_gateway_api_key="",
        enterprise_ai_text_base_url="https://ai-gateway-office.zeekrlife.com/v1",
        enterprise_ai_text_model="gpt-4o",
        lobster_proxy_token="proxy-token-abc",
        lobster_proxy_base="http://127.0.0.1:56045",
        lobster_api_root="v1",
    )
    with patch("app.ai.llm_gateway.get_settings", return_value=fake):
        ep = resolve_llm_endpoint(model)
        view = public_model_view(model)
    assert ep.via == "lobster"
    assert ep.api_key == "proxy-token-abc"
    assert ep.base_url == "http://127.0.0.1:56045/v1/geely/zhipu/v1"
    assert view["resolved_via"] == "lobster"
    set_runtime_api_resource(None)


def test_openai_not_on_lobster_falls_back_direct():
    model = SimpleNamespace(
        name="OpenAI",
        model_id="gpt-4o-mini",
        api_url="https://api.openai.com/v1",
        api_key="sk-openai",
        vendor="openai",
        connection_kind="lobster",
    )
    fake = SimpleNamespace(
        llm_gateway_mode="lobster",
        enterprise_ai_gateway_api_key="",
        enterprise_ai_text_base_url="https://ai-gateway-office.zeekrlife.com/v1",
        enterprise_ai_text_model="gpt-4o",
        lobster_proxy_token="proxy-token-abc",
        lobster_proxy_base="http://127.0.0.1:56045",
        lobster_api_root="v1",
    )
    with patch("app.ai.llm_gateway.get_settings", return_value=fake):
        ep = resolve_llm_endpoint(model)
    assert ep.via == "direct"
    assert ep.api_key == "sk-openai"
    set_runtime_api_resource(None)


def test_auto_without_token_is_direct():
    model = SimpleNamespace(
        name="DeepSeek",
        model_id="deepseek-chat",
        api_url="https://api.deepseek.com",
        api_key="sk-ds",
        vendor="deepseek",
        connection_kind="inherit",
    )
    fake = SimpleNamespace(
        llm_gateway_mode="auto",
        enterprise_ai_gateway_api_key="",
        enterprise_ai_text_base_url="https://ai-gateway-office.zeekrlife.com/v1",
        enterprise_ai_text_model="gpt-4o",
        lobster_proxy_token="",
        lobster_proxy_base="http://127.0.0.1:56045",
        lobster_api_root="v1",
    )
    set_runtime_api_resource("auto")
    with patch("app.ai.llm_gateway.get_settings", return_value=fake):
        ep = resolve_llm_endpoint(model)
    assert ep.via == "direct"
    assert ep.base_url == "https://api.deepseek.com"
    set_runtime_api_resource(None)


def test_enterprise_ready():
    fake = SimpleNamespace(
        enterprise_ai_gateway_api_key="key",
        enterprise_ai_text_base_url="https://ai-gateway-office.zeekrlife.com/v1",
    )
    with patch("app.ai.llm_gateway.get_settings", return_value=fake):
        assert enterprise_ready() is True
    fake2 = SimpleNamespace(
        enterprise_ai_gateway_api_key="",
        enterprise_ai_text_base_url="https://ai-gateway-office.zeekrlife.com/v1",
    )
    with patch("app.ai.llm_gateway.get_settings", return_value=fake2):
        assert enterprise_ready() is False
