"""LLM 模拟探针。"""

from app.services.geoflow.llm_client import chat_json_or_mock
from app.services.geoeval.platform_connectors.base import PLATFORM_PROMPT, ProbeOutcome, calc_ranking_score
from app.services.geoeval.platform_connectors.corpus_connector import _brand_in_text
from sqlalchemy.ext.asyncio import AsyncSession


def _corpus_excerpt(corpus: list[dict], question_text: str, limit: int = 3) -> str:
    from app.services.geoeval.platform_connectors.corpus_connector import _score_doc

    ranked = sorted(corpus, key=lambda d: _score_doc(question_text, d, "chatgpt"), reverse=True)[:limit]
    parts: list[str] = []
    for idx, doc in enumerate(ranked, start=1):
        parts.append(f"[{idx}] {doc.get('title', '')}\n{(doc.get('text') or '')[:600]}")
    return "\n\n".join(parts) if parts else "（无可用语料）"


class LlmConnector:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def probe(
        self,
        *,
        question_text: str,
        priority: int,
        platform: str,
        corpus: list[dict],
        brand_list: list[str],
        competitor_brands: list[str] | None = None,
    ) -> ProbeOutcome | None:
        style = PLATFORM_PROMPT.get(platform, "模拟 AI 搜索回答")
        brands = ", ".join(brand_list[:8])
        competitors = ", ".join((competitor_brands or [])[:8])
        system = (
            f"你是 GEO 品牌监控探针。{style}。"
            "仅根据参考语料判断目标品牌是否被提及及相对排名。"
            '返回 JSON：{"mentioned": bool, "brand_rank": number|null, "snippet": "简短摘录", '
            '"competitor_mentions": ["竞品名"]}'
        )
        user = (
            f"用户问题：{question_text}\n"
            f"监控品牌：{brands}\n"
            f"竞品列表：{competitors or '无'}\n"
            f"参考语料：\n{_corpus_excerpt(corpus, question_text)}\n"
            f"模拟平台：{platform}"
        )
        parsed = await chat_json_or_mock(self.db, system=system, user=user)
        if parsed is None:
            return None

        mentioned = bool(parsed.get("mentioned"))
        rank_raw = parsed.get("brand_rank")
        rank = int(rank_raw) if mentioned and rank_raw is not None else None
        snippet = str(parsed.get("snippet") or "")[:240]
        if mentioned and not snippet:
            snippet = _corpus_excerpt(corpus, question_text, limit=1)[:240]

        comp_raw = parsed.get("competitor_mentions") or []
        comp_mentions = [str(c) for c in comp_raw if c]

        return ProbeOutcome(
            question_id=0,
            platform=platform,
            brand_rank=rank,
            mentioned=mentioned,
            snippet=snippet,
            engine="llm",
            ranking_score=calc_ranking_score(rank),
            competitor_mentions=comp_mentions,
        )
