"""GEO 模拟 RAG — 检索语料 + LLM 模拟回答。"""

import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.article import Article
from app.models.material import AiModel
from app.services.geoflow.llm_client import chat_json
from app.services.geoflow.rag.retrieval import KnowledgeRetrievalService
from app.services.geoeval.platform_connectors.corpus_connector import _score_doc, _tokenize

logger = logging.getLogger(__name__)

SIMULATION_SYSTEM = (
    "你是 GEO 模拟 RAG 引擎。根据检索到的参考语料，模拟 AI 搜索引擎对用户问题的回答。"
    "仅基于语料作答，不要编造语料中不存在的事实。"
    '返回 JSON：{"answer": "200-400字模拟回答", "confidence": 0.0-1.0, "sources_used": [1,2]}'
)


def build_eval_query(article: Article) -> str:
    parts = [article.title.strip()]
    if article.original_keyword:
        parts.append(article.original_keyword.strip())
    elif article.keywords:
        parts.append(article.keywords.split(",")[0].strip())
    return " ".join(p for p in parts if p)[:200]


def _format_context(chunks: list[dict], article: Article) -> str:
    parts: list[str] = []
    for idx, chunk in enumerate(chunks[:5], start=1):
        content = (chunk.get("content") or "")[:700]
        parts.append(f"[{idx}] score={chunk.get('score', 0):.2f}\n{content}")
    article_excerpt = (article.content or "")[:800]
    parts.append(f"[article] {article.title}\n{article_excerpt}")
    return "\n\n".join(parts) if parts else "（无可用语料）"


def _retrieval_score(chunks: list[dict]) -> float:
    if not chunks:
        return 0.0
    top = sorted(chunks, key=lambda c: float(c.get("score") or 0), reverse=True)[:3]
    return round(sum(float(c.get("score") or 0) for c in top) / len(top), 4)


def _article_overlap_score(query: str, article: Article) -> float:
    q_tokens = _tokenize(query)
    if not q_tokens:
        return 0.0
    blob = f"{article.title} {article.content} {article.meta_description}"
    a_tokens = _tokenize(blob)
    overlap = len(q_tokens & a_tokens)
    return round(min(1.0, overlap / max(len(q_tokens), 1)), 4)


def _article_in_retrieval(chunks: list[dict], article: Article) -> bool:
    blob = f"{article.title} {article.content[:1200]}"
    a_tokens = _tokenize(blob)
    if not a_tokens:
        return False
    for chunk in chunks[:5]:
        c_tokens = _tokenize(chunk.get("content") or "")
        if len(a_tokens & c_tokens) >= 2:
            return True
    return False


def _mock_simulate(query: str, chunks: list[dict], article: Article) -> dict:
    corpus_doc = {"title": article.title, "text": article.content[:1200]}
    ranked = sorted(
        [{"title": article.title, "text": article.content[:1200]}] + [
            {"title": f"chunk-{c.get('chunk_id')}", "text": c.get("content") or ""} for c in chunks
        ],
        key=lambda d: _score_doc(query, d, "chatgpt"),
        reverse=True,
    )
    top = ranked[0] if ranked else corpus_doc
    answer = (top.get("text") or article.content or "")[:400]
    confidence = min(0.85, 0.35 + _retrieval_score(chunks) * 0.5 + _article_overlap_score(query, article) * 0.15)
    return {
        "answer": answer,
        "confidence": round(confidence, 4),
        "sources_used": [1] if chunks else ["article"],
    }


class SimulationRagService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def simulate(
        self,
        article: Article,
        *,
        kb_id: int | None,
        model: AiModel | None,
    ) -> dict:
        query = build_eval_query(article)
        chunks: list[dict] = []

        if kb_id:
            try:
                chunks = await KnowledgeRetrievalService(self.db).retrieve(kb_id, query, limit=6)
            except Exception:
                logger.exception("geo_eval_rag_retrieve_failed article_id=%s kb_id=%s", article.id, kb_id)

        retrieval_score = _retrieval_score(chunks)
        overlap_score = _article_overlap_score(query, article)
        in_retrieval = _article_in_retrieval(chunks, article)
        context = _format_context(chunks, article)

        engine = "mock"
        model_meta: dict = {}
        llm_result: dict

        use_llm = model is not None and not self.settings.ai_mock_mode
        if use_llm and model is not None:
            user = f"用户问题：{query}\n参考语料：\n{context}"
            try:
                llm_result = await chat_json(model, system=SIMULATION_SYSTEM, user=user)
                engine = "llm"
                model_meta = {"model_id": model.model_id, "model_name": model.name, "ai_model_id": model.id}
            except Exception:
                logger.exception("geo_eval_simulation_llm_failed article_id=%s", article.id)
                llm_result = _mock_simulate(query, chunks, article)
                engine = "mock_fallback"
        else:
            llm_result = _mock_simulate(query, chunks, article)

        confidence = float(llm_result.get("confidence") or 0.5)
        simulation_score = round(
            0.45 * retrieval_score + 0.25 * overlap_score + 0.20 * confidence + (0.10 if in_retrieval else 0.0),
            4,
        )

        result = {
            "query": query,
            "kb_id": kb_id,
            "retrieved_count": len(chunks),
            "retrieval_score": retrieval_score,
            "overlap_score": overlap_score,
            "article_in_retrieval": in_retrieval,
            "simulated_answer": str(llm_result.get("answer") or "")[:600],
            "confidence": confidence,
            "simulation_score": simulation_score,
            "engine": engine,
            "model": model_meta or None,
            "chunks_preview": [
                {"chunk_id": c.get("chunk_id"), "score": c.get("score"), "source": c.get("source")}
                for c in chunks[:3]
            ],
        }
        logger.info(
            "geo_eval_simulation article_id=%s engine=%s score=%s retrieval=%s",
            article.id,
            engine,
            simulation_score,
            retrieval_score,
        )
        return result
