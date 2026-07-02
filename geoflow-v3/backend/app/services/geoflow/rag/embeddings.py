"""Embedding 客户端。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.material import AiModel

settings = get_settings()


class EmbeddingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def embed_text(self, text: str) -> list[float] | None:
        if settings.ai_mock_mode:
            import hashlib

            digest = hashlib.sha256(text.encode()).digest()
            return [((b / 255.0) * 2 - 1) for b in digest] * 12

        row = (
            await self.db.execute(
                select(AiModel)
                .where(AiModel.model_type == "embedding", AiModel.status == "active")
                .order_by(AiModel.failover_priority)
                .limit(1)
            )
        ).scalar_one_or_none()
        if row is None:
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
                return None
            data = resp.json()
            return data["data"][0]["embedding"]
        except Exception:
            return None
