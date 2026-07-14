"""Sync：全量切分 + embedding + 写 store（对齐 GEOFlow 删旧重建）。"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from ragc.config import RagSettings
from ragc.core.chunking import split_with_overlap
from ragc.core.embeddings import embed_text
from ragc.core.store import LocalStore
from ragc.utils.logger import get_logger

logger = get_logger("ragc.sync")


def sync_knowledge_base(store: LocalStore, kb_id: int, settings: RagSettings) -> dict[str, Any]:
    started = time.monotonic()
    kb = store.get_kb(kb_id)
    content = str(kb.get("content") or "")
    pieces = split_with_overlap(content, settings.chunk_size, settings.chunk_overlap)
    chunks: list[dict[str, Any]] = []
    for idx, piece in enumerate(pieces):
        vector = embed_text(piece, mock=settings.mock_mode, dim=settings.embedding_dim)
        chunks.append(
            {
                "chunk_index": idx,
                "content": piece,
                "content_hash": hashlib.sha256(piece.encode("utf-8")).hexdigest(),
                "embedding": vector,
                "embedding_dimensions": len(vector),
            }
        )
    store.replace_chunks(kb_id, chunks)
    duration_ms = int((time.monotonic() - started) * 1000)
    logger.info(
        "kb_synced id=%s chunks=%s mock=%s duration_ms=%s",
        kb_id,
        len(chunks),
        settings.mock_mode,
        duration_ms,
    )
    return {
        "knowledge_base_id": kb_id,
        "name": kb.get("name"),
        "chunks": len(chunks),
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "mock": settings.mock_mode,
        "duration_ms": duration_ms,
    }
