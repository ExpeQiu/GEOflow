"""本地 JSON 知识库存储（不依赖 GEOFlow DB）。"""

from __future__ import annotations

import json
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from ragc.utils.errors import StoreError, UsageError
from ragc.utils.logger import get_logger

logger = get_logger("ragc.store")


class LocalStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._data: dict[str, Any] = {"version": 1, "next_kb_id": 1, "next_chunk_id": 1, "knowledge_bases": {}}

    def load(self) -> None:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.save()
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise StoreError(f"store 损坏: {self.path}") from exc
        if not isinstance(raw, dict):
            raise StoreError("store 根节点必须是 object")
        self._data = raw
        self._data.setdefault("version", 1)
        self._data.setdefault("next_kb_id", 1)
        self._data.setdefault("next_chunk_id", 1)
        self._data.setdefault("knowledge_bases", {})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def list_kbs(self) -> list[dict[str, Any]]:
        items = []
        for kid, kb in self._data["knowledge_bases"].items():
            items.append(
                {
                    "id": int(kid),
                    "name": kb.get("name"),
                    "content_chars": len(str(kb.get("content") or "")),
                    "chunk_count": len(kb.get("chunks") or []),
                    "updated_at": kb.get("updated_at"),
                }
            )
        return sorted(items, key=lambda x: x["id"])

    def get_kb(self, kb_id: int) -> dict[str, Any]:
        kb = self._data["knowledge_bases"].get(str(kb_id))
        if kb is None:
            raise UsageError(f"知识库不存在: {kb_id}")
        return kb

    def create_kb(self, name: str, content: str = "") -> dict[str, Any]:
        kb_id = int(self._data["next_kb_id"])
        self._data["next_kb_id"] = kb_id + 1
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        kb = {
            "id": kb_id,
            "name": name,
            "content": content,
            "chunks": [],
            "created_at": now,
            "updated_at": now,
            "synced_at": None,
        }
        self._data["knowledge_bases"][str(kb_id)] = kb
        self.save()
        logger.info("kb_created id=%s name=%s", kb_id, name)
        return deepcopy(kb)

    def update_content(self, kb_id: int, content: str, *, append: bool = False, note: str = "") -> dict[str, Any]:
        kb = self.get_kb(kb_id)
        if append and kb.get("content"):
            prefix = f"\n\n---\n## {note}\n\n" if note else "\n\n"
            kb["content"] = str(kb["content"]) + prefix + content
        else:
            kb["content"] = content
        kb["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.save()
        return deepcopy(kb)

    def delete_kb(self, kb_id: int) -> None:
        key = str(kb_id)
        if key not in self._data["knowledge_bases"]:
            raise UsageError(f"知识库不存在: {kb_id}")
        del self._data["knowledge_bases"][key]
        self.save()
        logger.info("kb_deleted id=%s", kb_id)

    def replace_chunks(self, kb_id: int, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        kb = self.get_kb(kb_id)
        # 分配稳定 chunk id
        assigned = []
        for ch in chunks:
            cid = int(self._data["next_chunk_id"])
            self._data["next_chunk_id"] = cid + 1
            item = dict(ch)
            item["id"] = cid
            assigned.append(item)
        kb["chunks"] = assigned
        kb["synced_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        kb["updated_at"] = kb["synced_at"]
        self.save()
        return deepcopy(kb)
