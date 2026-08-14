"""探针连接器基础类型与排名算法。"""

from dataclasses import dataclass, field
from typing import Any, Protocol

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

# C 端 Web 入口（Playwright）；登录态靠持久 Profile
CEND_PLATFORM_URLS = {
    "yuanbao": "https://yuanbao.tencent.com/",
    "doubao": "https://www.doubao.com/chat/",
    "tongyi": "https://tongyi.aliyun.com/qianwen/",
    "kimi": "https://kimi.moonshot.cn/",
    "wenxin": "https://yiyan.baidu.com/",
    "deepseek": "https://chat.deepseek.com/",
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
    # Rank v2 / Citation L0–L2
    rank_method: str = "unknown"  # list_order | first_mention | unknown | camp_block
    evidence_level: str = "L0"  # L0 | L1 | L2
    match_type: str = "none"  # domain_wiki | domain_official | none
    parser_version: str | None = None
    urls: list = field(default_factory=list)
    # C 端辅轨扩展
    thinking_text: str | None = None
    thinking_ms: int | None = None
    keywords: list = field(default_factory=list)
    entities: list = field(default_factory=list)
    rank_blocks: list = field(default_factory=list)
    decision_table: list = field(default_factory=list)
    citation_urls: list = field(default_factory=list)
    citation_titles: list = field(default_factory=list)
    source_hosts: list = field(default_factory=list)
    capture_artifact: str | None = None
    metric_kind: str = "mixed"  # open_api | cend_sample | corpus | llm_sim | mixed
    cend_meta: dict[str, Any] = field(default_factory=dict)


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
