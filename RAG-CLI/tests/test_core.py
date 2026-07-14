"""核心单元测试。"""

from __future__ import annotations

from pathlib import Path

from ragc.config import load_settings
from ragc.core.chunking import pad_embedding_vector, split_with_overlap
from ragc.core.embeddings import mock_embed
from ragc.core.retrieve import retrieve
from ragc.core.store import LocalStore
from ragc.core.sync import sync_knowledge_base


def test_split_overlap() -> None:
    text = "a" * 2500
    chunks = split_with_overlap(text, 1200, 200)
    assert len(chunks) >= 2
    assert all(len(c) <= 1200 for c in chunks)


def test_mock_embed_stable() -> None:
    a = mock_embed("hello")
    b = mock_embed("hello")
    assert a == b
    assert len(pad_embedding_vector(a)) == 3072


def test_sync_and_query(tmp_path: Path) -> None:
    store_path = tmp_path / "store.json"
    store = LocalStore(store_path)
    store.load()
    kb = store.create_kb(
        "t",
        "GEO 关注 AI 回答中的品牌可见性。RAG 通过切分与向量检索提供证据。",
    )
    settings = load_settings(store_path=str(store_path), mock=True, chunk_size=80, chunk_overlap=10)
    result = sync_knowledge_base(store, kb["id"], settings)
    assert result["chunks"] >= 1
    store.load()
    out = retrieve(store, kb["id"], "品牌可见性", settings, limit=3)
    assert out["hit_count"] >= 1
    assert out["hits"][0]["source"] in {"vector", "keyword", "hybrid", "fallback"}
