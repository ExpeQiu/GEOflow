"""RAG 混合召回 — 关键词 + 向量（pgvector）。"""

import logging
import os

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeChunk
from app.services.geoflow.rag.chunking import pad_embedding_vector
from app.services.geoflow.rag.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


def _skip_pgvector() -> bool:
    return os.getenv("SKIP_PGVECTOR", "").lower() in ("1", "true", "yes")


class KnowledgeRetrievalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def retrieve(self, knowledge_base_id: int, query: str, limit: int | None = None) -> list[dict]:
        """混合召回：向量语义 + 关键词，受 knowledge-settings 控制。"""
        from app.services.admin.knowledge_settings_service import get_knowledge_settings

        settings_data = await get_knowledge_settings(self.db)
        effective_limit = limit or int(settings_data.get("retrieval_limit") or 8)
        hybrid_enabled = bool(settings_data.get("hybrid_enabled", True)) and not _skip_pgvector()
        keyword = query[:120].strip()

        merged: dict[int, dict] = {}

        if hybrid_enabled and keyword:
            embeddings = EmbeddingService(self.db)
            query_vector = await embeddings.embed_text(keyword)
            if query_vector:
                padded = pad_embedding_vector(query_vector)
                for hit in await self.vector_search(knowledge_base_id, padded, effective_limit * 2):
                    merged[hit["chunk_id"]] = hit

        for hit in await self._keyword_search(knowledge_base_id, keyword, effective_limit * 2):
            chunk_id = hit["chunk_id"]
            if chunk_id in merged:
                merged[chunk_id]["score"] = round(
                    max(merged[chunk_id]["score"], hit["score"]) * 0.6 + hit["score"] * 0.4,
                    4,
                )
                merged[chunk_id]["source"] = "hybrid"
            else:
                merged[chunk_id] = hit

        results = sorted(merged.values(), key=lambda item: item["score"], reverse=True)[:effective_limit]

        if not results:
            results = await self._fallback_chunks(knowledge_base_id, effective_limit)

        logger.info(
            "rag_retrieve kb_id=%s hybrid=%s keyword_len=%s hits=%s",
            knowledge_base_id,
            hybrid_enabled,
            len(keyword),
            len(results),
        )
        return results

    async def _keyword_search(self, knowledge_base_id: int, keyword: str, limit: int) -> list[dict]:
        if not keyword:
            return []
        term = keyword[:40]
        rows = (
            await self.db.execute(
                select(KnowledgeChunk)
                .where(
                    KnowledgeChunk.knowledge_base_id == knowledge_base_id,
                    KnowledgeChunk.content.ilike(f"%{term}%"),
                )
                .limit(limit)
            )
        ).scalars().all()
        return [
            {
                "chunk_id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "score": 0.55,
                "source": "keyword",
            }
            for chunk in rows
        ]

    async def _fallback_chunks(self, knowledge_base_id: int, limit: int) -> list[dict]:
        rows = (
            await self.db.execute(
                select(KnowledgeChunk)
                .where(KnowledgeChunk.knowledge_base_id == knowledge_base_id)
                .order_by(KnowledgeChunk.chunk_index)
                .limit(limit)
            )
        ).scalars().all()
        return [
            {
                "chunk_id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "score": 0.1,
                "source": "fallback",
            }
            for chunk in rows
        ]

    async def vector_search(self, knowledge_base_id: int, query_vector: list[float], limit: int = 8) -> list[dict]:
        if _skip_pgvector():
            logger.info("vector_search_skipped skip_pgvector=true kb_id=%s", knowledge_base_id)
            return []

        vector_literal = "[" + ",".join(str(float(v)) for v in query_vector) + "]"
        sql = text(
            """
            SELECT id, chunk_index, content, (embedding_vector <=> CAST(:qv AS vector)) AS distance
            FROM knowledge_chunks
            WHERE knowledge_base_id = :kb_id AND embedding_vector IS NOT NULL
            ORDER BY embedding_vector <=> CAST(:qv AS vector)
            LIMIT :lim
            """
        )
        try:
            # 用 savepoint，避免 pgvector 缺失时整事务 rollback 污染后续 keyword 查询
            async with self.db.begin_nested():
                result = await self.db.execute(
                    sql,
                    {"qv": vector_literal, "kb_id": knowledge_base_id, "lim": limit},
                )
                hits: list[dict] = []
                for row in result:
                    distance = float(row.distance)
                    hits.append(
                        {
                            "chunk_id": row.id,
                            "chunk_index": int(row.chunk_index),
                            "content": row.content,
                            "score": round(max(0.0, 1.0 - distance), 4),
                            "source": "vector",
                        }
                    )
                return hits
        except Exception:
            logger.exception("vector_search_failed kb_id=%s", knowledge_base_id)
            return []
