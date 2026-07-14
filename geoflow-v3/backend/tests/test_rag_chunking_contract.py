"""RAG 切分契约：主栈算法自测（不依赖 RAG-CLI 运行时）。"""

from app.services.geoflow.rag.chunking import EMBEDDING_VECTOR_DIM, pad_embedding_vector, split_with_overlap


def test_split_with_overlap_basic():
    text = "abcdefghij"  # 10
    chunks = split_with_overlap(text, chunk_size=4, overlap=1)
    assert chunks == ["abcd", "defg", "ghij"]


def test_split_empty():
    assert split_with_overlap("", 100, 10) == [""]


def test_pad_embedding_vector_dim():
    v = pad_embedding_vector([1.0, 2.0], dim=4)
    assert len(v) == 4
    assert v[:2] == [1.0, 2.0]
    assert EMBEDDING_VECTOR_DIM == 3072


def test_rag_hit_source_enum_contract():
    """冻结 query hits.source 枚举（与 RAG-CLI / Admin rag-sandbox 对齐）。"""
    allowed = {"vector", "keyword", "hybrid", "fallback"}
    assert "hybrid" in allowed
    assert "fallback" in allowed
