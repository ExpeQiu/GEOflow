"""RAG 混合召回 — 移植 KnowledgeRetrievalService 简化版。"""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeChunk


class KnowledgeRetrievalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def retrieve(self, knowledge_base_id: int, query: str, limit: int = 8) -> list[dict]:
        """关键词 + 向量召回（pgvector 可用时）。"""
        keyword = query[:120].strip()
        rows = (
            await self.db.execute(
                select(KnowledgeChunk)
                .where(
                    KnowledgeChunk.knowledge_base_id == knowledge_base_id,
                    KnowledgeChunk.content.ilike(f"%{keyword[:40]}%") if keyword else True,
                )
                .limit(limit)
            )
        ).scalars().all()

        if not rows:
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
                "content": chunk.content,
                "score": 1.0,
                "source": "knowledge_base",
            }
            for chunk in rows
        ]

    async def vector_search(self, knowledge_base_id: int, query_vector: list[float], limit: int = 8) -> list[dict]:
        sql = text(
            """
            SELECT id, content, (embedding_vector <=> :qv) AS distance
            FROM knowledge_chunks
            WHERE knowledge_base_id = :kb_id AND embedding_vector IS NOT NULL
            ORDER BY embedding_vector <=> :qv
            LIMIT :lim
            """
        )
        result = await self.db.execute(
            sql, {"qv": str(query_vector), "kb_id": knowledge_base_id, "lim": limit}
        )
        return [
            {"chunk_id": row.id, "content": row.content, "score": 1.0 - float(row.distance), "source": "vector"}
            for row in result
        ]
