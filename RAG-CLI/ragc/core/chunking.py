"""文本切片 — 对齐 GEOFlow split_with_overlap。"""

from __future__ import annotations

from ragc.config import EMBEDDING_VECTOR_DIM


def split_with_overlap(text: str, chunk_size: int, overlap: int) -> list[str]:
    if not text:
        return [""]
    stride = max(1, chunk_size - overlap)
    chunks: list[str] = []
    start = 0
    while start < len(text):
        piece = text[start : start + chunk_size]
        if piece:
            chunks.append(piece)
        if start + chunk_size >= len(text):
            break
        start += stride
    return chunks or [""]


def pad_embedding_vector(vector: list[float], dim: int = EMBEDDING_VECTOR_DIM) -> list[float]:
    if len(vector) >= dim:
        return vector[:dim]
    return vector + [0.0] * (dim - len(vector))
