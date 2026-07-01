"""初始化种子数据。"""

import asyncio

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models.admin import Admin
from app.models.material import Author, Category, Prompt
from app.models.material import AiModel


async def seed() -> None:
    async with async_session_factory() as db:
        existing = (await db.execute(select(Admin).where(Admin.username == "admin"))).scalar_one_or_none()
        if existing is None:
            db.add(
                Admin(
                    username="admin",
                    password=hash_password("password"),
                    email="admin@example.com",
                    display_name="Administrator",
                    role="super_admin",
                )
            )

        if (await db.execute(select(Category).limit(1))).scalar_one_or_none() is None:
            db.add(Category(name="默认分类", slug="default", description="系统默认"))

        if (await db.execute(select(Author).limit(1))).scalar_one_or_none() is None:
            db.add(Author(name="GEOFlow Editor", bio="AI 内容编辑"))

        if (await db.execute(select(Prompt).limit(1))).scalar_one_or_none() is None:
            db.add(
                Prompt(
                    name="默认正文",
                    type="content",
                    content="你是专业中文写作助手，请基于提供的证据撰写 Markdown 文章。",
                )
            )

        if (await db.execute(select(AiModel).limit(1))).scalar_one_or_none() is None:
            db.add(
                AiModel(
                    name="Mock Chat",
                    model_id="mock-gpt",
                    api_key="mock",
                    model_type="chat",
                    status="active",
                )
            )

        await db.commit()
    print("Seed completed.")


if __name__ == "__main__":
    asyncio.run(seed())
