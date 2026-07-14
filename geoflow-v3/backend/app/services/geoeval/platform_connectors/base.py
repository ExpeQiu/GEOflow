"""探针连接器基础类型与排名算法。"""

from dataclasses import dataclass, field
from typing import Protocol

PLATFORMS_CN = ("doubao", "deepseek", "tongyi", "yuanbao", "wenxin", "kimi")
RANK_WEIGHTS = {1: 6, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1}

PLATFORM_PROMPT = {
    "doubao": "模拟豆包中文问答风格",
    "deepseek": "模拟 DeepSeek 中文问答风格",
    "tongyi": "模拟通义千问综合回答风格",
    "yuanbao": "模拟腾讯元宝问答风格",
    "wenxin": "模拟文心一言问答风格",
    "kimi": "模拟 Kimi 长文本问答风格",
}

PLATFORM_BIAS = {
    "doubao": 1,
    "deepseek": 0,
    "tongyi": 1,
    "yuanbao": 2,
    "wenxin": 1,
    "kimi": 0,
}


def calc_ranking_score(rank: int | None) -> float:
    if rank is None:
        return 0.0
    return float(RANK_WEIGHTS.get(rank, 0))


@dataclass
class ProbeOutcome:
    question_id: int
    platform: str
    brand_rank: int | None
    mentioned: bool
    snippet: str
    engine: str = "corpus"
    ranking_score: float = 0.0
    sentiment: dict | None = None
    competitor_mentions: list = field(default_factory=list)
    # Rank v2 / Citation L0–L1（answer_parser）；旧路径可留默认
    rank_method: str = "unknown"  # list_order | first_mention | unknown
    evidence_level: str = "L0"  # L0 | L1
    match_type: str = "none"  # domain_wiki | domain_official | none
    parser_version: str | None = None
    urls: list = field(default_factory=list)


class PlatformConnector(Protocol):
    async def probe(
        self,
        *,
        question_text: str,
        priority: int,
        platform: str,
        corpus: list[dict],
        brand_list: list[str],
        competitor_brands: list[str] | None = None,
    ) -> ProbeOutcome: ...
