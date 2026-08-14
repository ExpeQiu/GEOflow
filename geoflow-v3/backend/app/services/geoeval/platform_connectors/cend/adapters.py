"""六大平台 C 端适配器。"""

from __future__ import annotations

from app.services.geoeval.platform_connectors.base import CEND_PLATFORM_URLS
from app.services.geoeval.platform_connectors.cend.base_adapter import BaseCendAdapter


class YuanbaoCendAdapter(BaseCendAdapter):
    platform = "yuanbao"
    start_url = CEND_PLATFORM_URLS["yuanbao"]
    input_selectors = (
        "textarea",
        "[contenteditable='true']",
        "div.chat-input textarea",
        "[class*='editor']",
    )
    thinking_selectors = (
        "text=已深度思考",
        "text=深度思考",
        "[class*='think']",
    )
    citation_link_selectors = ("a[href^='http']",)


class DoubaoCendAdapter(BaseCendAdapter):
    platform = "doubao"
    start_url = CEND_PLATFORM_URLS["doubao"]
    thinking_selectors = (
        "text=深度思考",
        "text=已完成思考",
        "[class*='think']",
        "[class*='reasoning']",
    )


class TongyiCendAdapter(BaseCendAdapter):
    platform = "tongyi"
    start_url = CEND_PLATFORM_URLS["tongyi"]
    thinking_selectors = (
        "text=思考过程",
        "text=深度思考",
        "[class*='think']",
    )


class KimiCendAdapter(BaseCendAdapter):
    platform = "kimi"
    start_url = CEND_PLATFORM_URLS["kimi"]
    thinking_selectors = (
        "text=深度思考",
        "[class*='think']",
        "[class*='reasoning']",
    )


class WenxinCendAdapter(BaseCendAdapter):
    platform = "wenxin"
    start_url = CEND_PLATFORM_URLS["wenxin"]
    thinking_selectors = (
        "text=深度思考",
        "text=思考中",
        "[class*='think']",
    )


class DeepseekCendAdapter(BaseCendAdapter):
    platform = "deepseek"
    start_url = CEND_PLATFORM_URLS["deepseek"]
    thinking_selectors = (
        "text=已深度思考",
        "text=DeepThink",
        "[class*='think']",
        "[class*='reasoning']",
    )


ADAPTERS = {
    "yuanbao": YuanbaoCendAdapter,
    "doubao": DoubaoCendAdapter,
    "tongyi": TongyiCendAdapter,
    "kimi": KimiCendAdapter,
    "wenxin": WenxinCendAdapter,
    "deepseek": DeepseekCendAdapter,
}
