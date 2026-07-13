"""语料启发式探针（降级模式）。"""

import re

from app.services.geoeval.platform_connectors.base import PLATFORM_BIAS, ProbeOutcome, calc_ranking_score


def _tokenize(text: str) -> set[str]:
    parts = re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z0-9]{3,}", text.lower())
    return set(parts)


def _score_doc(question: str, doc: dict, platform: str) -> float:
    q_tokens = _tokenize(question)
    if not q_tokens:
        return 0.0
    blob = f"{doc.get('title', '')} {doc.get('text', '')}".lower()
    doc_tokens = _tokenize(blob)
    overlap = len(q_tokens & doc_tokens)
    base = overlap / max(len(q_tokens), 1)
    bias = PLATFORM_BIAS.get(platform, 0) * 0.02
    title_bonus = 0.15 if any(t in (doc.get("title") or "").lower() for t in q_tokens) else 0.0
    return base + title_bonus - bias


def _brand_in_text(text: str, brands: list[str]) -> bool:
    low = text.lower()
    return any(b.lower() in low for b in brands if b)


class CorpusConnector:
    async def probe(
        self,
        *,
        question_text: str,
        priority: int,
        platform: str,
        corpus: list[dict],
        brand_list: list[str],
        competitor_brands: list[str] | None = None,
    ) -> ProbeOutcome:
        ranked_docs = sorted(corpus, key=lambda d: _score_doc(question_text, d, "chatgpt"), reverse=True)[:10]
        platform_docs = sorted(corpus, key=lambda d: _score_doc(question_text, d, platform), reverse=True)[:10]

        rank: int | None = None
        snippet = ""
        for idx, doc in enumerate(platform_docs, start=1):
            blob = f"{doc['title']}\n{doc['text']}"
            if _brand_in_text(blob, brand_list):
                rank = idx + (1 if platform == "yuanbao" and priority > 70 else 0)
                snippet = blob[:240]
                break

        if rank is None and ranked_docs:
            top = ranked_docs[0]
            snippet = f"{top['title']}\n{top['text']}"[:240]
            if priority >= 80 and _brand_in_text(question_text, brand_list):
                rank = 3

        competitors = competitor_brands or []
        comp_mentions = [c for c in competitors if _brand_in_text(snippet, [c])]

        return ProbeOutcome(
            question_id=0,
            platform=platform,
            brand_rank=rank,
            mentioned=rank is not None,
            snippet=snippet,
            engine="corpus",
            ranking_score=calc_ranking_score(rank),
            competitor_mentions=comp_mentions,
        )
