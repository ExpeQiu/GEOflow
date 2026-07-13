"""知识库检索沙箱与 RAG 设置。"""

import logging

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeBase
from app.services.admin.production_service import _table_exists
from app.services.admin.settings_crud_service import SiteSettingBody, upsert_site_setting

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS = {
    "knowledge_chunk_size": ("1200", "int", "knowledge"),
    "knowledge_chunk_overlap": ("200", "int", "knowledge"),
    "knowledge_retrieval_limit": ("8", "int", "knowledge"),
    "knowledge_hybrid_enabled": ("true", "bool", "knowledge"),
}


class KnowledgeSettingsBody(BaseModel):
    chunk_size: int = Field(default=1200, ge=200, le=8000)
    chunk_overlap: int = Field(default=200, ge=0, le=2000)
    retrieval_limit: int = Field(default=8, ge=1, le=50)
    hybrid_enabled: bool = True


class RagSandboxBody(BaseModel):
    knowledge_base_id: int = Field(ge=1)
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=8, ge=1, le=20)


async def get_knowledge_settings(db: AsyncSession) -> dict:
    settings = {k: {"value": v[0], "type": v[1]} for k, v in DEFAULT_SETTINGS.items()}
    if not await _table_exists(db, "site_settings"):
        return {"settings": settings, "editable": False}
    rows = (
        await db.execute(
            text(
                "SELECT setting_key, setting_value, value_type FROM site_settings WHERE group_name = 'knowledge'"
            )
        )
    ).all()
    for key, value, value_type in rows:
        settings[key] = {"value": value or "", "type": value_type or "string"}
    return {
        "settings": settings,
        "editable": True,
        "chunk_size": int(settings.get("knowledge_chunk_size", {}).get("value") or 1200),
        "chunk_overlap": int(settings.get("knowledge_chunk_overlap", {}).get("value") or 200),
        "retrieval_limit": int(settings.get("knowledge_retrieval_limit", {}).get("value") or 8),
        "hybrid_enabled": str(settings.get("knowledge_hybrid_enabled", {}).get("value", "true")).lower() == "true",
    }


async def save_knowledge_settings(db: AsyncSession, body: KnowledgeSettingsBody) -> dict:
    mapping = {
        "knowledge_chunk_size": (str(body.chunk_size), "int"),
        "knowledge_chunk_overlap": (str(body.chunk_overlap), "int"),
        "knowledge_retrieval_limit": (str(body.retrieval_limit), "int"),
        "knowledge_hybrid_enabled": ("true" if body.hybrid_enabled else "false", "bool"),
    }
    for key, (value, value_type) in mapping.items():
        await upsert_site_setting(
            db,
            SiteSettingBody(setting_key=key, setting_value=value, value_type=value_type, group_name="knowledge"),
        )
    logger.info("knowledge_settings_saved")
    return await get_knowledge_settings(db)


async def run_rag_sandbox(db: AsyncSession, body: RagSandboxBody) -> dict:
    from app.services.geoflow.rag.retrieval import KnowledgeRetrievalService

    kb = await db.get(KnowledgeBase, body.knowledge_base_id)
    if kb is None:
        raise HTTPException(status_code=404, detail="knowledge_base_not_found")
    svc = KnowledgeRetrievalService(db)
    chunks = await svc.retrieve(body.knowledge_base_id, body.query, limit=body.limit)
    logger.info("rag_sandbox_query kb_id=%s hits=%s", body.knowledge_base_id, len(chunks))
    return {
        "knowledge_base_id": body.knowledge_base_id,
        "knowledge_base_name": kb.name,
        "query": body.query,
        "hits": chunks,
        "hit_count": len(chunks),
    }
