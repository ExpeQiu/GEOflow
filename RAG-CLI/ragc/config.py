"""配置 — CLI 参数 > 环境变量 > 本地文件 > 默认。"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

EMBEDDING_VECTOR_DIM = 3072
DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_RETRIEVAL_LIMIT = 8


@dataclass
class RagSettings:
    chunk_size: int = DEFAULT_CHUNK_SIZE
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    retrieval_limit: int = DEFAULT_RETRIEVAL_LIMIT
    hybrid_enabled: bool = True
    mock_mode: bool = True
    store_path: str = ""
    embedding_dim: int = EMBEDDING_VECTOR_DIM

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_data_dir() -> Path:
    env = os.environ.get("RAGC_DATA_DIR", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return Path.home() / ".ragc"


def default_store_path() -> Path:
    env = os.environ.get("RAGC_STORE_PATH", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return default_data_dir() / "store.json"


def load_settings(
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    retrieval_limit: int | None = None,
    hybrid: bool | None = None,
    mock: bool | None = None,
    store_path: str | None = None,
    config_file: str | None = None,
) -> RagSettings:
    file_data: dict[str, Any] = {}
    cfg_path = Path(config_file) if config_file else Path("config.yaml")
    if cfg_path.is_file():
        with cfg_path.open(encoding="utf-8") as fh:
            loaded = yaml.safe_load(fh) or {}
        if isinstance(loaded, dict):
            file_data = loaded

    def env_bool(name: str, default: bool) -> bool:
        raw = os.environ.get(name)
        if raw is None:
            return default
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    settings = RagSettings(
        chunk_size=int(file_data.get("chunk_size") or os.environ.get("RAGC_CHUNK_SIZE") or DEFAULT_CHUNK_SIZE),
        chunk_overlap=int(
            file_data.get("chunk_overlap") or os.environ.get("RAGC_CHUNK_OVERLAP") or DEFAULT_CHUNK_OVERLAP
        ),
        retrieval_limit=int(
            file_data.get("retrieval_limit") or os.environ.get("RAGC_RETRIEVAL_LIMIT") or DEFAULT_RETRIEVAL_LIMIT
        ),
        hybrid_enabled=bool(file_data.get("hybrid_enabled", True)),
        mock_mode=env_bool("RAGC_MOCK_MODE", True),
        store_path=str(file_data.get("store_path") or default_store_path()),
        embedding_dim=int(file_data.get("embedding_dim") or EMBEDDING_VECTOR_DIM),
    )

    if chunk_size is not None:
        settings.chunk_size = chunk_size
    if chunk_overlap is not None:
        settings.chunk_overlap = chunk_overlap
    if retrieval_limit is not None:
        settings.retrieval_limit = retrieval_limit
    if hybrid is not None:
        settings.hybrid_enabled = hybrid
    if mock is not None:
        settings.mock_mode = mock
    if store_path is not None:
        settings.store_path = store_path

    # 与 GEOFlow Admin 约束大体对齐
    settings.chunk_size = max(200, min(8000, settings.chunk_size))
    settings.chunk_overlap = max(0, min(2000, settings.chunk_overlap))
    settings.retrieval_limit = max(1, min(50, settings.retrieval_limit))
    return settings
