"""从 Techstore 只读快照写入 GEOFlow 知识库 + 技术 IP。

地图/FAQ 仍以 Techstore 为真源；本服务只灌 RAG 语料与 IP 身份证。
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.admin.knowledge_crud_service import upsert_knowledge_base_by_name
from app.services.admin.tech_assets_import_service import upsert_tech_asset_row
from app.services.admin.techstore_snapshot import (
    TechstoreSnapshot,
    build_kb_payloads,
    build_tech_asset_rows,
    fetch_live_snapshot,
    load_fixture_snapshot,
    preview_from_snapshot,
)
from app.services.geoflow.rag.knowledge_sync_queue import queue_knowledge_chunk_sync

logger = logging.getLogger(__name__)

SourceKind = Literal["auto", "live", "fixture"]


class TechstoreImportBody(BaseModel):
    source: SourceKind = "auto"
    sync_chunks: bool = True
    dry_run: bool = False


def resolve_source(requested: SourceKind) -> tuple[str, str]:
    """返回 (resolved_source, techstore_url_or_empty)。"""
    url = (get_settings().techstore_database_url or "").strip()
    if requested == "fixture":
        return "fixture", url
    if requested == "live":
        if not url:
            raise HTTPException(status_code=422, detail="techstore_database_url_missing")
        return "live", url
    if url:
        return "live", url
    return "fixture", url


async def load_snapshot(source: SourceKind) -> TechstoreSnapshot:
    resolved, url = resolve_source(source)
    if resolved == "fixture":
        snap = load_fixture_snapshot()
        logger.info("techstore_snapshot_loaded source=fixture")
        return snap
    try:
        snap = await asyncio.to_thread(fetch_live_snapshot, url)
        return snap
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("techstore_live_fetch_failed")
        raise HTTPException(status_code=503, detail=f"techstore_unreachable:{exc}") from exc


async def preview_techstore_import(source: SourceKind = "auto") -> dict:
    snap = await load_snapshot(source)
    payload = preview_from_snapshot(snap)
    payload["requested_source"] = source
    return payload


async def import_techstore_knowledge(db: AsyncSession, body: TechstoreImportBody) -> dict:
    run_id = uuid.uuid4().hex[:12]
    snap = await load_snapshot(body.source)
    assets = build_tech_asset_rows(snap)
    kbs = build_kb_payloads(snap)
    preview = preview_from_snapshot(snap)
    if body.dry_run:
        logger.info(
            "techstore_import_dry_run run_id=%s source=%s assets=%s kbs=%s",
            run_id,
            snap.source,
            len(assets),
            len(kbs),
        )
        return {"run_id": run_id, "dry_run": True, **preview}

    kb_created = 0
    kb_updated = 0
    queued: list[int] = []
    kb_items: list[dict] = []
    for payload in kbs:
        kb_id, action = await upsert_knowledge_base_by_name(
            db,
            name=payload["name"],
            description=payload["description"],
            content=payload["content"],
        )
        if action == "created":
            kb_created += 1
        else:
            kb_updated += 1
        kb_items.append({"id": kb_id, "name": payload["name"], "action": action})
        if body.sync_chunks:
            if queue_knowledge_chunk_sync(kb_id):
                queued.append(kb_id)

    asset_created = 0
    asset_updated = 0
    for raw in assets:
        action = await upsert_tech_asset_row(db, raw)
        if action == "created":
            asset_created += 1
        elif action == "updated":
            asset_updated += 1
    await db.flush()
    logger.info(
        "techstore_imported run_id=%s source=%s kb_created=%s kb_updated=%s "
        "asset_created=%s asset_updated=%s sync_queued=%s",
        run_id,
        snap.source,
        kb_created,
        kb_updated,
        asset_created,
        asset_updated,
        len(queued),
    )
    return {
        "run_id": run_id,
        "dry_run": False,
        "source": snap.source,
        "warning": snap.warning,
        "counts": snap.counts(),
        "knowledge_bases": {"created": kb_created, "updated": kb_updated, "items": kb_items},
        "tech_assets": {"created": asset_created, "updated": asset_updated},
        "sync_queued": queued,
    }
