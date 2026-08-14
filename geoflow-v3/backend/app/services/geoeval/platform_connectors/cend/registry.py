"""C 端适配器注册。"""

from __future__ import annotations

from app.services.geoeval.platform_connectors.cend.adapters import ADAPTERS
from app.services.geoeval.platform_connectors.cend.base_adapter import BaseCendAdapter


def list_cend_platforms() -> list[str]:
    return list(ADAPTERS.keys())


def get_cend_adapter(platform: str) -> BaseCendAdapter:
    cls = ADAPTERS.get(platform)
    if cls is None:
        raise KeyError(f"unsupported_cend_platform:{platform}")
    return cls()
