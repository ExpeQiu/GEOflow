"""Content Pipeline 双 RAG 上下文 — 移植 ContentPipelineContextService。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.services.geoflow.rag.retrieval import KnowledgeRetrievalService


class ContentPipelineContextService:
    def __init__(self, db: AsyncSession, rag: KnowledgeRetrievalService):
        self.db = db
        self.rag = rag

    async def build(self, task: Task, prompt: str) -> dict:
        research_pack: list[dict] = []
        brand_pack: list[dict] = []
        if task.knowledge_base_id:
            research_pack = await self.rag.retrieve(task.knowledge_base_id, prompt, limit=6)
            brand_pack = await self.rag.retrieve(task.knowledge_base_id, f"品牌 {task.name}", limit=4)

        return {
            "research_pack": research_pack,
            "brand_pack": brand_pack,
            "evidence": research_pack + brand_pack,
            "style_guide": {"tone": "professional", "language": "zh-CN"},
            "pipeline_mode": task.content_pipeline_mode or "standard",
        }
