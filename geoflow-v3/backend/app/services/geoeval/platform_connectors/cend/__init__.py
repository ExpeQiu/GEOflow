"""C 端浏览器探针：统一契约与适配器注册。"""

from .protocol import CendCaptureResult, CendAdapter
from .registry import get_cend_adapter, list_cend_platforms

__all__ = [
    "CendCaptureResult",
    "CendAdapter",
    "get_cend_adapter",
    "list_cend_platforms",
]
