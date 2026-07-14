"""答文解析 Rank v2 + Citation L0/L1。

主栈自有实现（由 Sim-sandbox-CLI 验证成果沉淀），生产不 import simsb。
parser_version = v2。
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urlparse

PARSER_VERSION = "v2"
# 与 platform_connectors.base.RANK_WEIGHTS 对齐；不跨包 import，避免循环依赖
_RANK_WEIGHTS = {1: 6, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1}


def _calc_ranking_score(rank: int | None) -> float:
    if rank is None:
        return 0.0
    return float(_RANK_WEIGHTS.get(rank, 0))

_NUM_LIST = re.compile(r"^\s*(?:#{1,6}\s*)?(\d+)[\.、\)]\s*(.+)$")
_PAREN_LIST = re.compile(r"^\s*[（(](\d+)[）)]\s*(.+)$")
_CN_LIST = re.compile(r"^\s*([一二三四五六七八九十]+)[、.．]\s*(.+)$")

_CN_ORDINAL = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}

_URL_RE = re.compile(r"https?://[^\s\)\]\"'<>]+", re.IGNORECASE)


@dataclass
class ParseResult:
    mentioned: bool
    brand_rank: int | None
    rank_method: str  # list_order | first_mention | unknown
    confidence: float
    ranking_score: float
    competitor_mentions: list[str] = field(default_factory=list)
    mention_order: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    evidence_level: str = "L0"  # L0 | L1
    match_type: str = "none"  # domain_wiki | domain_official | none
    snippet: str = ""
    parser_version: str = PARSER_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_brands(brands: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for b in brands:
        name = (b or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(name)
    return out


def _find_brand_in_text(text: str, brand: str) -> int | None:
    if not text or not brand:
        return None
    idx = text.lower().find(brand.lower())
    return idx if idx >= 0 else None


def _cn_to_int(token: str) -> int | None:
    if token in _CN_ORDINAL:
        return _CN_ORDINAL[token]
    if token.startswith("十") and len(token) == 2:
        return 10 + (_CN_ORDINAL.get(token[1], 0) or 0)
    return None


def extract_list_items(text: str) -> list[tuple[int, str]]:
    """抽取有序列表项 -> (序位, 行正文)。"""
    items: list[tuple[int, str]] = []
    for raw in (text or "").splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m = _NUM_LIST.match(line) or _PAREN_LIST.match(line)
        if m:
            items.append((int(m.group(1)), m.group(2)))
            continue
        m_cn = _CN_LIST.match(line)
        if m_cn:
            ord_n = _cn_to_int(m_cn.group(1)) or (len(items) + 1)
            items.append((ord_n, m_cn.group(2)))
    items.sort(key=lambda x: x[0])
    return items


def _rank_by_list(
    text: str,
    brand_list: list[str],
    all_brands: list[str],
) -> tuple[int | None, list[str], list[str], float] | None:
    items = extract_list_items(text)
    if len(items) < 2:
        return None

    order: list[str] = []
    rank_map: dict[str, int] = {}
    for pos, body in items:
        for brand in all_brands:
            if _find_brand_in_text(body, brand) is not None and brand not in rank_map:
                rank_map[brand] = pos
                order.append(brand)

    if not order:
        return None

    self_ranks = [rank_map[b] for b in brand_list if b in rank_map]
    brand_rank = min(self_ranks) if self_ranks else None
    comps = [b for b in order if b not in brand_list]
    conf = min(0.95, 0.55 + 0.1 * len(order) + 0.05 * min(len(items), 6))
    return brand_rank, comps, order, conf


def _rank_by_first_mention(
    text: str,
    brand_list: list[str],
    all_brands: list[str],
) -> tuple[int | None, list[str], list[str], float]:
    found: list[tuple[int, str]] = []
    for brand in all_brands:
        idx = _find_brand_in_text(text, brand)
        if idx is not None:
            found.append((idx, brand))
    if not found:
        return None, [], [], 0.0
    found.sort(key=lambda x: x[0])
    order = [b for _, b in found]
    rank_by_brand = {b: i for i, b in enumerate(order, start=1)}
    self_ranks = [rank_by_brand[b] for b in brand_list if b in rank_by_brand]
    brand_rank = min(self_ranks) if self_ranks else None
    comps = [b for b in order if b not in brand_list]
    return brand_rank, comps, order, 0.45


def extract_urls(text: str) -> list[str]:
    urls: list[str] = []
    for m in _URL_RE.finditer(text or ""):
        u = m.group(0).rstrip(".,;，。；")
        if u not in urls:
            urls.append(u)
    return urls


def classify_evidence(
    urls: list[str],
    *,
    wiki_domains: list[str] | None = None,
    official_domains: list[str] | None = None,
) -> tuple[str, str]:
    wiki = {d.lower().lstrip(".") for d in (wiki_domains or ["wikipedia.org", "baike.baidu.com"])}
    official = {d.lower().lstrip(".") for d in (official_domains or [])}
    if not urls:
        return "L0", "none"
    for url in urls:
        host = (urlparse(url).hostname or "").lower()
        if not host:
            continue
        for d in wiki:
            if host == d or host.endswith("." + d):
                return "L1", "domain_wiki"
        for d in official:
            if host == d or host.endswith("." + d):
                return "L1", "domain_official"
    return "L1", "none"


def parse_answer(
    text: str,
    *,
    brand_list: list[str],
    competitor_brands: list[str] | None = None,
    wiki_domains: list[str] | None = None,
    official_domains: list[str] | None = None,
) -> ParseResult:
    brands = _normalize_brands(brand_list)
    comps_in = _normalize_brands(list(competitor_brands or []))
    all_brands = _normalize_brands(brands + comps_in)
    body = text or ""

    list_hit = _rank_by_list(body, brands, all_brands)
    if list_hit is not None:
        brand_rank, comps, order, conf = list_hit
        method = "list_order"
    else:
        brand_rank, comps, order, conf = _rank_by_first_mention(body, brands, all_brands)
        method = "first_mention" if order else "unknown"

    mentioned = any(b in order for b in brands)
    if not mentioned and any(_find_brand_in_text(body, b) is not None for b in brands):
        mentioned = True
        brand_rank, comps, order, conf = _rank_by_first_mention(body, brands, all_brands)
        method = "first_mention" if order else "unknown"

    urls = extract_urls(body)
    level, match_type = classify_evidence(
        urls, wiki_domains=wiki_domains, official_domains=official_domains
    )

    rank_method = method if mentioned else "unknown"

    snippet = body.strip().replace("\n", " ")[:240]
    return ParseResult(
        mentioned=bool(mentioned),
        brand_rank=brand_rank if mentioned else None,
        rank_method=rank_method,
        confidence=round(conf if mentioned else 0.0, 3),
        ranking_score=_calc_ranking_score(brand_rank if mentioned else None),
        competitor_mentions=comps,
        mention_order=order,
        urls=urls,
        evidence_level=level,
        match_type=match_type,
        snippet=snippet,
        parser_version=PARSER_VERSION,
    )
