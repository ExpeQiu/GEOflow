"""文件 ingest — 第一期支持 txt/md/csv/html 纯文本。"""

from __future__ import annotations

from pathlib import Path

from ragc.utils.errors import UsageError

SUPPORTED = {".txt", ".md", ".markdown", ".csv", ".html", ".htm"}
MAX_CHARS = 200_000


def read_ingest_file(path: str | Path) -> tuple[str, str]:
    p = Path(path)
    if not p.is_file():
        raise UsageError(f"文件不存在: {path}")
    suffix = p.suffix.lower()
    if suffix not in SUPPORTED:
        raise UsageError(f"暂不支持扩展名 {suffix}；支持: {', '.join(sorted(SUPPORTED))}")
    text = p.read_text(encoding="utf-8", errors="ignore")
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]
    return p.name, text
