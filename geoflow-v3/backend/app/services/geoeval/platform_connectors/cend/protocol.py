"""C 端适配器协议与捕获结果。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class CendCaptureResult:
    """单次 C 端页面捕获的结构化结果。"""

    ok: bool
    platform: str
    answer_text: str = ""
    thinking_text: str = ""
    thinking_ms: int | None = None
    citations: list[dict[str, Any]] = field(default_factory=list)  # {title, url, position}
    source_hosts: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    rank_blocks: list[dict[str, Any]] = field(default_factory=list)
    decision_table: list[dict[str, Any]] = field(default_factory=list)
    capture_artifact: str | None = None
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


class CendAdapter(Protocol):
    platform: str
    start_url: str

    async def capture(self, page: Any, question_text: str, *, brand_list: list[str]) -> CendCaptureResult:
        """在已打开的 Playwright page 上发问并抽取结构化字段。"""
        ...
