"""Theme 包页面排序：子页先于 topic hub。"""

from __future__ import annotations

from typing import Any

PACK_TYPE_ORDER = {
    "concept": 0,
    "compare": 1,
    "guide": 2,
    "glossary": 3,
    "data": 4,
    "thread": 5,
    "article": 6,
    "certification": 7,
    "topic": 99,
}


def pack_sort_key(page_type: str) -> int:
    return PACK_TYPE_ORDER.get(page_type, 50)


def sort_pack_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        pages,
        key=lambda page: (
            pack_sort_key(str(page.get("wiki_page_type") or page.get("type") or "")),
            int(page.get("id") or 0),
        ),
    )
