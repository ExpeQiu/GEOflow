"""六平台 UAT 门禁：Open API 三家 vs C 端三家；live 缺 Key 跳过。"""

from __future__ import annotations

import os

import pytest

from app.services.geoeval.platform_connectors.api_connector import ApiConnector
from app.services.geoeval.platform_connectors.base import PLATFORMS_CN
from app.services.geoeval.platform_connectors.cend.registry import list_cend_platforms
from app.services.geoeval.probe_scheme import SCHEME_CITATION, SCHEME_OPEN_API

OPEN_API_ENV = {
    "deepseek": ("DEEPSEEK_API_KEY",),
    "doubao": ("DOUBAO_API_KEY", "ARK_API_KEY"),
    "kimi": ("KIMI_API_KEY", "MOONSHOT_API_KEY"),
}
CEND_ONLY = ("tongyi", "wenxin", "yuanbao")


def test_six_platforms_catalog():
    assert set(PLATFORMS_CN) == {"doubao", "deepseek", "tongyi", "yuanbao", "wenxin", "kimi"}
    assert set(list_cend_platforms()) == set(PLATFORMS_CN)


def test_open_api_vs_cend_split():
    assert set(OPEN_API_ENV) == {"deepseek", "doubao", "kimi"}
    assert set(CEND_ONLY).isdisjoint(OPEN_API_ENV)


def _has_any(keys: tuple[str, ...]) -> bool:
    return any(os.getenv(k) for k in keys)


@pytest.mark.live
@pytest.mark.asyncio
@pytest.mark.parametrize("platform", list(OPEN_API_ENV))
async def test_live_open_api_probe(platform: str):
    if os.getenv("GEOFLOW_LIVE_PROBE") != "1":
        pytest.skip("GEOFLOW_LIVE_PROBE!=1")
    if platform == "doubao" and not os.getenv("DOUBAO_MODEL"):
        pytest.skip("DOUBAO_MODEL missing")
    if not _has_any(OPEN_API_ENV[platform]):
        pytest.skip(f"{OPEN_API_ENV[platform][0]} missing")

    scheme = SCHEME_CITATION if platform == "kimi" else SCHEME_OPEN_API
    outcome = await ApiConnector().probe(
        question_text="家用纯电怎么选续航？",
        priority=80,
        platform=platform,
        corpus=[],
        brand_list=["吉利"],
        competitor_brands=["比亚迪"],
        scheme=scheme,
    )
    assert outcome is not None
    assert outcome.engine == "api"
    assert outcome.snippet
