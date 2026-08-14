"""从答文启发式抽取关键词、阵营块、决策表。"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from app.services.geoeval.answer_parser import extract_list_items, parse_answer

_CAMP_RE = re.compile(
    r"^(?:#{1,6}\s*)?(?:[\d一二三四五六七八九十]+[\.、\)]\s*)?"
    r"(.+?(?:阵营|梯队|营|体系|平台|品牌)).*$"
)
_KW_HINTS = (
    "城区NOA",
    "城市NOA",
    "高速NOA",
    "XNGP",
    "ADS",
    "天神之眼",
    "激光雷达",
    "智驾",
    "端到端",
    "Orin",
    "800V",
)


def domain_of(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").replace("www.", "")
    except Exception:
        return ""


def extract_keywords(text: str, extra: list[str] | None = None) -> list[str]:
    found: list[str] = []
    body = text or ""
    for kw in list(_KW_HINTS) + list(extra or []):
        if kw and kw in body and kw not in found:
            found.append(kw)
    return found[:24]


def extract_rank_blocks(text: str, brand_list: list[str]) -> list[dict]:
    """按「阵营/梯队」标题切块，块内用列表序解析品牌。"""
    lines = (text or "").splitlines()
    blocks: list[dict] = []
    current_title: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_title, current_lines
        if not current_title:
            current_lines = []
            return
        body = "\n".join(current_lines)
        parsed = parse_answer(body, brand_list=brand_list)
        items = extract_list_items(body)
        models = [{"position": p, "text": t[:200]} for p, t in items[:12]]
        blocks.append(
            {
                "camp": current_title[:120],
                "brand_rank": parsed.brand_rank,
                "mentioned": parsed.mentioned,
                "models": models,
                "snippet": body[:400],
            }
        )
        current_title = None
        current_lines = []

    for line in lines:
        m = _CAMP_RE.match(line.strip())
        if m:
            flush()
            current_title = m.group(1).strip()
            current_lines = []
        elif current_title is not None:
            current_lines.append(line)
    flush()
    return blocks


def extract_decision_table_heuristic(text: str) -> list[dict]:
    """简易 markdown / 管道表解析。"""
    rows: list[dict] = []
    for line in (text or "").splitlines():
        if "|" not in line or re.match(r"^\s*\|?\s*-+", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        if any(h in cells[0] for h in ("诉求", "核心", "需求", "首选", "备选")) and len(rows) == 0:
            rows.append({"header": cells})
            continue
        if rows and "header" in rows[0] and len(cells) == len(rows[0]["header"]):
            header = rows[0]["header"]
            rows.append({header[i]: cells[i] for i in range(len(cells))})
        elif len(cells) >= 3:
            rows.append({"col0": cells[0], "col1": cells[1], "col2": cells[2]})
    # 去掉纯 header 行
    return [r for r in rows if "header" not in r][:20]


def citations_from_pairs(pairs: list[tuple[str, str]]) -> list[dict]:
    out = []
    for i, (title, url) in enumerate(pairs, start=1):
        if not url and not title:
            continue
        out.append({"title": (title or "")[:500], "url": (url or "")[:2000], "position": i})
    return out
