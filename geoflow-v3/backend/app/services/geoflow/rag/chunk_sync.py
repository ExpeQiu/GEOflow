"""知识库切片与 Embedding — 移植 KnowledgeChunkSyncService 简化版。"""

import hashlib
import json

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.knowledge import KnowledgeBase, KnowledgeChunk
from app.services.geoflow.rag.embeddings import EmbeddingService

settings = get_settings()


class KnowledgeChunkSyncService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embeddings = EmbeddingService()

    async def sync_chunks(self, knowledge_base_id: int, chunk_size: int = 800) -> int:
        kb = await self.db.get(KnowledgeBase, knowledge_base_id)
        if kb is None:
            return 0

        await self.db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.knowledge_base_id == knowledge_base_id))

        text = kb.content or ""
        chunks = [text[i : i + chunk_size] for i in range(0, max(len(text), 1), chunk_size)] or [""]

        count = 0
        for idx, content in enumerate(chunks):
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            vector = await self.embeddings.embed_text(content) if content.strip() else None
            row = KnowledgeChunk(
                knowledge_base_id=knowledge_base_id,
                chunk_index=idx,
                content=content,
                content_hash=content_hash,
                embedding_json=json.dumps(vector) if vector else "",
                embedding_dimensions=len(vector) if vector else 0,
                embedding_vector=vector,
            )
            self.db.add(row)
            count += 1

        await self.db.flush()
        return count
