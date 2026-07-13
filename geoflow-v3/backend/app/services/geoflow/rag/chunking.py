"""知识库文本切片工具。"""

EMBEDDING_VECTOR_DIM = 3072


def split_with_overlap(text: str, chunk_size: int, overlap: int) -> list[str]:
    """按固定窗口与重叠切分文本。"""
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
    """将 embedding 向量填充/截断到 pgvector 列维度。"""
    if len(vector) >= dim:
        return vector[:dim]
    return vector + [0.0] * (dim - len(vector))
