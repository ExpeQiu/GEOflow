"""知识库切片与 Embedding — 读取 knowledge-settings 参数。"""

import hashlib
import json
import logging

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeBase, KnowledgeChunk
from app.services.admin.knowledge_settings_service import get_knowledge_settings
from app.services.geoflow.rag.chunking import pad_embedding_vector, split_with_overlap
from app.services.geoflow.rag.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class KnowledgeChunkSyncService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embeddings = EmbeddingService(db)

    async def sync_chunks(
        self,
        knowledge_base_id: int,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> int:
        kb = await self.db.get(KnowledgeBase, knowledge_base_id)
        if kb is None:
            return 0

        kb_settings = await get_knowledge_settings(self.db)
        size = chunk_size or int(kb_settings.get("chunk_size") or 1200)
        overlap = chunk_overlap or int(kb_settings.get("chunk_overlap") or 200)

        await self.db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.knowledge_base_id == knowledge_base_id))

        content = kb.content or ""
        chunks = split_with_overlap(content, size, overlap)

        count = 0
        for idx, piece in enumerate(chunks):
            content_hash = hashlib.sha256(piece.encode()).hexdigest()
            raw_vector = await self.embeddings.embed_text(piece) if piece.strip() else None
            vector = pad_embedding_vector(raw_vector) if raw_vector else None
            row = KnowledgeChunk(
                knowledge_base_id=knowledge_base_id,
                chunk_index=idx,
                content=piece,
                content_hash=content_hash,
                embedding_json=json.dumps(raw_vector) if raw_vector else "",
                embedding_dimensions=len(raw_vector) if raw_vector else 0,
                embedding_vector=vector,
            )
            self.db.add(row)
            count += 1

        await self.db.flush()
        logger.info(
            "knowledge_chunks_synced kb_id=%s chunks=%s size=%s overlap=%s",
            knowledge_base_id,
            count,
            size,
            overlap,
        )
        return count
