"""夹具加载（JSONL）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from simsb.utils.errors import FixtureError
from simsb.utils.logger import get_logger

logger = get_logger("simsb.fixtures")

REQUIRED_KEYS = ("id", "answer_text", "brand_list", "expected")


def load_fixture_file(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FixtureError(f"夹具文件不存在: {path}")
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise FixtureError(f"{path}:{lineno} JSON 无效: {exc}") from exc
        if not isinstance(obj, dict):
            raise FixtureError(f"{path}:{lineno} 期望 object")
        missing = [k for k in REQUIRED_KEYS if k not in obj]
        if missing:
            raise FixtureError(f"{path}:{lineno} 缺少字段 {missing}")
        obj["_source"] = str(path)
        rows.append(obj)
    logger.debug("loaded_fixtures path=%s count=%s", path, len(rows))
    return rows


def load_fixtures(path: Path) -> list[dict[str, Any]]:
    path = path.expanduser().resolve()
    if path.is_file():
        return load_fixture_file(path)
    if not path.is_dir():
        raise FixtureError(f"夹具路径不存在: {path}")
    files = sorted(
        f
        for f in path.rglob("*.jsonl")
        if f.is_file() and not f.name.startswith("._")
    )
    if not files:
        raise FixtureError(f"目录下无 .jsonl: {path}")
    rows: list[dict[str, Any]] = []
    for f in files:
        rows.extend(load_fixture_file(f))
    logger.info("fixtures_loaded dir=%s files=%s rows=%s", path, len(files), len(rows))
    return rows
