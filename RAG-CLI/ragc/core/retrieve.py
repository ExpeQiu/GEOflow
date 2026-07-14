"""混合召回 — 内存版向量 + 关键词（对齐 GEOFlow 合并规则）。"""

from __future__ import annotations

import math
from typing import Any

from ragc.config import RagSettings
from ragc.core.embeddings import embed_text
from ragc.core.store import LocalStore
from ragc.utils.logger import get_logger

logger = get_logger("ragc.retrieve")


def _cosine(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for i in range(n):
        x = float(a[i])
        y = float(b[i])
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / math.sqrt(na * nb)


def retrieve(
    store: LocalStore,
    kb_id: int,
    query: str,
    settings: RagSettings,
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    kb = store.get_kb(kb_id)
    effective_limit = limit or settings.retrieval_limit
    keyword = query[:120].strip()
    chunks = list(kb.get("chunks") or [])
    merged: dict[int, dict[str, Any]] = {}

    if settings.hybrid_enabled and keyword:
        qvec = embed_text(keyword, mock=settings.mock_mode, dim=settings.embedding_dim)
        scored: list[tuple[float, dict[str, Any]]] = []
        for ch in chunks:
            emb = ch.get("embedding")
            if not isinstance(emb, list):
                continue
            score = _cosine(qvec, emb)
            scored.append((score, ch))
        scored.sort(key=lambda x: x[0], reverse=True)
        for score, ch in scored[: effective_limit * 2]:
            cid = int(ch["id"])
            merged[cid] = {
                "chunk_id": cid,
                "chunk_index": ch.get("chunk_index"),
                "content": ch.get("content"),
                "score": round(float(score), 4),
                "source": "vector",
            }

    if keyword:
        term = keyword[:40].lower()
        for ch in chunks:
            content = str(ch.get("content") or "")
            if term and term in content.lower():
                cid = int(ch["id"])
                hit = {
                    "chunk_id": cid,
                    "chunk_index": ch.get("chunk_index"),
                    "content": content,
                    "score": 0.55,
                    "source": "keyword",
                }
                if cid in merged:
                    merged[cid]["score"] = round(
                        max(merged[cid]["score"], hit["score"]) * 0.6 + hit["score"] * 0.4,
                        4,
                    )
                    merged[cid]["source"] = "hybrid"
                else:
                    merged[cid] = hit

    results = sorted(merged.values(), key=lambda item: item["score"], reverse=True)[:effective_limit]

    if not results:
        for ch in sorted(chunks, key=lambda c: int(c.get("chunk_index") or 0))[:effective_limit]:
            results.append(
                {
                    "chunk_id": int(ch["id"]),
                    "chunk_index": ch.get("chunk_index"),
                    "content": ch.get("content"),
                    "score": 0.1,
                    "source": "fallback",
                }
            )

    logger.info(
        "rag_query kb_id=%s hybrid=%s hits=%s",
        kb_id,
        settings.hybrid_enabled,
        len(results),
    )
    return {
        "knowledge_base_id": kb_id,
        "knowledge_base_name": kb.get("name"),
        "query": query,
        "hits": results,
        "hit_count": len(results),
    }
