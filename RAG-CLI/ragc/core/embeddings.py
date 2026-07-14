"""Embedding — mock 默认；可选 OpenAI-compatible。"""

from __future__ import annotations

import hashlib
import os
from typing import Any

from ragc.config import EMBEDDING_VECTOR_DIM
from ragc.core.chunking import pad_embedding_vector
from ragc.utils.logger import get_logger

logger = get_logger("ragc.embed")


def mock_embed(text: str, dim: int = EMBEDDING_VECTOR_DIM) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    mock = [((b / 255.0) * 2 - 1) for b in digest] * 12
    return pad_embedding_vector(mock, dim)


def embed_text(text: str, *, mock: bool = True, dim: int = EMBEDDING_VECTOR_DIM) -> list[float]:
    if mock:
        return mock_embed(text, dim)

    api_url = os.environ.get("RAGC_EMBEDDING_API_URL", "").strip()
    api_key = os.environ.get("RAGC_EMBEDDING_API_KEY", "").strip()
    model = os.environ.get("RAGC_EMBEDDING_MODEL", "text-embedding-3-large").strip()
    if not api_url or not api_key:
        logger.warning("live_embed_missing_credentials fallback_mock")
        return mock_embed(text, dim)

    try:
        import urllib.error
        import urllib.request
        import json

        payload = json.dumps({"input": text, "model": model}).encode("utf-8")
        req = urllib.request.Request(
            f"{api_url.rstrip('/')}/embeddings",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
        vector = data["data"][0]["embedding"]
        return pad_embedding_vector([float(x) for x in vector], dim)
    except Exception as exc:  # noqa: BLE001
        logger.warning("live_embed_failed fallback_mock error=%s", exc)
        return mock_embed(text, dim)
