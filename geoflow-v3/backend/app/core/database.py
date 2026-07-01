"""SQLAlchemy 异步/同步引擎。"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import create_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=settings.debug, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

_sync_engine = None
_sync_session_factory = None


def get_sync_session_factory():
    global _sync_engine, _sync_session_factory
    if _sync_session_factory is None:
        _sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
        _sync_session_factory = sessionmaker(bind=_sync_engine, autocommit=False, autoflush=False)
    return _sync_session_factory


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
