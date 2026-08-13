"""Embedding 客户端。"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.material import AiModel
from app.services.geoflow.rag.chunking import pad_embedding_vector

settings = get_settings()
logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def embed_text(self, text: str) -> list[float] | None:
        if settings.ai_mock_mode:
            import hashlib

            digest = hashlib.sha256(text.encode()).digest()
            mock = [((b / 255.0) * 2 - 1) for b in digest] * 12
            logger.info("embedding_mock_mode length=%s", len(text))
            return pad_embedding_vector(mock)

        row = (
            await self.db.execute(
                select(AiModel)
                .where(AiModel.model_type == "embedding", AiModel.status == "active")
                .order_by(AiModel.failover_priority)
                .limit(1)
            )
        ).scalar_one_or_none()
        if row is None:
            logger.warning("embedding_model_missing ai_mock_mode=false — 上传后无法向量化，请配置 embedding 模型")
            return None

        import httpx

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{row.api_url.rstrip('/')}/embeddings",
                    headers={"Authorization": f"Bearer {row.api_key}"},
                    json={"input": text, "model": row.model_id},
                )
            if resp.status_code >= 400:
                logger.warning("embedding_api_error status=%s model_id=%s", resp.status_code, row.model_id)
                return None
            data = resp.json()
            vector = data["data"][0]["embedding"]
            logger.info("embedding_ok model_id=%s dims=%s", row.model_id, len(vector) if vector else 0)
            return pad_embedding_vector(vector)
        except Exception:
            logger.exception("embedding_request_failed model_id=%s", row.model_id)
            return None

    async def ensure_production_ready(self) -> dict:
        """Wave 9 验收：非 Mock 时必须有可用 embedding 模型。"""
        if settings.ai_mock_mode:
            return {"ready": True, "mode": "mock", "warning": "AI_MOCK_MODE=true"}
        row = (
            await self.db.execute(
                select(AiModel)
                .where(AiModel.model_type == "embedding", AiModel.status == "active")
                .limit(1)
            )
        ).scalar_one_or_none()
        ready = row is not None
        logger.info("embedding_production_ready=%s", ready)
        return {
            "ready": ready,
            "mode": "api",
            "model_id": row.model_id if row else None,
            "warning": None if ready else "missing_active_embedding_model",
        }
