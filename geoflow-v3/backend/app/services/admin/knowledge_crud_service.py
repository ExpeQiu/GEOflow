"""知识库 CRUD — Admin BFF。"""

import logging

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeBase, KnowledgeChunk

logger = logging.getLogger(__name__)


class KnowledgeBaseBody(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    content: str = Field(min_length=1)


async def list_knowledge_bases_detail(db: AsyncSession) -> dict:
    rows = (await db.execute(select(KnowledgeBase).order_by(KnowledgeBase.name))).scalars().all()
    return {
        "items": [
            {
                "id": kb.id,
                "name": kb.name,
                "description": kb.description or "",
                "character_count": kb.character_count,
                "word_count": kb.word_count,
                "used_task_count": kb.used_task_count,
            }
            for kb in rows
        ]
    }


async def get_knowledge_base(db: AsyncSession, kb_id: int) -> dict:
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(status_code=404, detail="knowledge_base_not_found")
    chunks = (
        await db.execute(
            select(KnowledgeChunk).where(KnowledgeChunk.knowledge_base_id == kb_id).order_by(KnowledgeChunk.chunk_index).limit(50)
        )
    ).scalars().all()
    return {
        "item": {
            "id": kb.id,
            "name": kb.name,
            "description": kb.description or "",
            "content": kb.content,
            "character_count": kb.character_count,
        },
        "chunks": [
            {"id": c.id, "chunk_index": c.chunk_index, "token_count": c.token_count, "preview": (c.content or "")[:120]}
            for c in chunks
        ],
    }


async def create_knowledge_base(db: AsyncSession, body: KnowledgeBaseBody) -> dict:
    kb = KnowledgeBase(
        name=body.name.strip(),
        description=body.description.strip(),
        content=body.content,
        character_count=len(body.content),
        word_count=len(body.content.split()),
    )
    db.add(kb)
    await db.flush()
    logger.info("knowledge_base_created id=%s", kb.id)
    return {"item": {"id": kb.id, "name": kb.name}}


async def update_knowledge_base(db: AsyncSession, kb_id: int, body: KnowledgeBaseBody) -> dict:
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(status_code=404, detail="knowledge_base_not_found")
    kb.name = body.name.strip()
    kb.description = body.description.strip()
    kb.content = body.content
    kb.character_count = len(body.content)
    kb.word_count = len(body.content.split())
    await db.flush()
    logger.info("knowledge_base_updated id=%s", kb_id)
    return {"item": {"id": kb.id, "name": kb.name}}


async def delete_knowledge_base(db: AsyncSession, kb_id: int) -> dict:
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(status_code=404, detail="knowledge_base_not_found")
    await db.delete(kb)
    logger.info("knowledge_base_deleted id=%s", kb_id)
    return {"deleted": True}


async def append_knowledge_file_content(db: AsyncSession, kb_id: int, content: str, filename: str) -> dict:
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(status_code=404, detail="knowledge_base_not_found")
    header = f"\n\n---\n## 文件导入: {filename}\n\n"
    kb.content = (kb.content or "") + header + content.strip()
    kb.character_count = len(kb.content)
    kb.word_count = len(kb.content.split())
    await db.flush()
    logger.info("knowledge_file_appended kb_id=%s file=%s", kb_id, filename)
    return {"item": {"id": kb.id, "character_count": kb.character_count}}
