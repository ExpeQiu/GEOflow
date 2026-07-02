"""素材三库 CRUD — 标题/关键词/图片。"""

import logging

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin.production_service import _table_exists

logger = logging.getLogger(__name__)


class LibraryBody(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""


class TitleBody(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    keyword: str = ""


class KeywordBody(BaseModel):
    keyword: str = Field(min_length=1, max_length=200)


class ImageMetaBody(BaseModel):
    original_name: str = Field(min_length=1, max_length=255)
    file_path: str = Field(min_length=1, max_length=500)
    mime_type: str = ""
    file_size: int = 0


async def _require_table(db: AsyncSession, table: str) -> None:
    if not await _table_exists(db, table):
        raise HTTPException(status_code=503, detail=f"{table}_not_migrated")


async def list_title_libraries(db: AsyncSession) -> dict:
    await _require_table(db, "title_libraries")
    rows = (
        await db.execute(
            text(
                """
                SELECT tl.id, tl.name, tl.description,
                       (SELECT COUNT(*) FROM titles t WHERE t.library_id = tl.id) AS cnt
                FROM title_libraries tl ORDER BY tl.id DESC
                """
            )
        )
    ).all()
    return {"items": [{"id": int(r[0]), "name": r[1], "description": r[2] or "", "count": int(r[3])} for r in rows]}


async def create_title_library(db: AsyncSession, body: LibraryBody) -> dict:
    await _require_table(db, "title_libraries")
    row = (
        await db.execute(
            text("INSERT INTO title_libraries (name, description) VALUES (:n, :d) RETURNING id"),
            {"n": body.name.strip(), "d": body.description.strip()},
        )
    ).first()
    await db.flush()
    logger.info("title_library_created id=%s", row[0])
    return {"item": {"id": int(row[0]), "name": body.name.strip(), "description": body.description.strip(), "count": 0}}


async def update_title_library(db: AsyncSession, library_id: int, body: LibraryBody) -> dict:
    await _require_table(db, "title_libraries")
    result = await db.execute(
        text("UPDATE title_libraries SET name=:n, description=:d, updated_at=CURRENT_TIMESTAMP WHERE id=:id"),
        {"n": body.name.strip(), "d": body.description.strip(), "id": library_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="library_not_found")
    return {"item": {"id": library_id, "name": body.name.strip(), "description": body.description.strip()}}


async def delete_title_library(db: AsyncSession, library_id: int) -> dict:
    await _require_table(db, "title_libraries")
    in_use = int(
        await db.scalar(text("SELECT COUNT(*) FROM tasks WHERE title_library_id = :id"), {"id": library_id}) or 0
    )
    if in_use > 0:
        raise HTTPException(status_code=422, detail="library_in_use")
    await db.execute(text("DELETE FROM title_libraries WHERE id = :id"), {"id": library_id})
    logger.info("title_library_deleted id=%s", library_id)
    return {"deleted": True}


async def list_titles(db: AsyncSession, library_id: int) -> dict:
    await _require_table(db, "titles")
    rows = (
        await db.execute(
            text("SELECT id, title, keyword, used_count FROM titles WHERE library_id=:lid ORDER BY id DESC LIMIT 500"),
            {"lid": library_id},
        )
    ).all()
    return {"items": [{"id": int(r[0]), "title": r[1], "keyword": r[2] or "", "used_count": int(r[3])} for r in rows]}


async def create_title(db: AsyncSession, library_id: int, body: TitleBody) -> dict:
    await _require_table(db, "titles")
    row = (
        await db.execute(
            text(
                "INSERT INTO titles (library_id, title, keyword) VALUES (:lid, :t, :k) RETURNING id"
            ),
            {"lid": library_id, "t": body.title.strip(), "k": body.keyword.strip()},
        )
    ).first()
    await db.execute(
        text("UPDATE title_libraries SET title_count = (SELECT COUNT(*) FROM titles WHERE library_id=:lid) WHERE id=:lid"),
        {"lid": library_id},
    )
    await db.flush()
    return {"item": {"id": int(row[0]), "title": body.title.strip(), "keyword": body.keyword.strip()}}


async def delete_title(db: AsyncSession, title_id: int) -> dict:
    await _require_table(db, "titles")
    lib = (
        await db.execute(text("SELECT library_id FROM titles WHERE id=:id"), {"id": title_id})
    ).first()
    if not lib:
        raise HTTPException(status_code=404, detail="title_not_found")
    await db.execute(text("DELETE FROM titles WHERE id=:id"), {"id": title_id})
    await db.execute(
        text("UPDATE title_libraries SET title_count = (SELECT COUNT(*) FROM titles WHERE library_id=:lid) WHERE id=:lid"),
        {"lid": lib[0]},
    )
    return {"deleted": True}


async def list_keyword_libraries(db: AsyncSession) -> dict:
    await _require_table(db, "keyword_libraries")
    rows = (
        await db.execute(
            text(
                """
                SELECT kl.id, kl.name, kl.description,
                       (SELECT COUNT(*) FROM keywords k WHERE k.library_id = kl.id) AS cnt
                FROM keyword_libraries kl ORDER BY kl.id DESC
                """
            )
        )
    ).all()
    return {"items": [{"id": int(r[0]), "name": r[1], "description": r[2] or "", "count": int(r[3])} for r in rows]}


async def delete_keyword_library(db: AsyncSession, library_id: int) -> dict:
    await _require_table(db, "keyword_libraries")
    in_use = int(
        await db.scalar(
            text("SELECT COUNT(*) FROM title_libraries WHERE keyword_library_id = :id"), {"id": library_id}
        )
        or 0
    )
    if in_use > 0:
        raise HTTPException(status_code=422, detail="library_in_use")
    await db.execute(text("DELETE FROM keyword_libraries WHERE id = :id"), {"id": library_id})
    logger.info("keyword_library_deleted id=%s", library_id)
    return {"deleted": True}


async def delete_keyword(db: AsyncSession, keyword_id: int) -> dict:
    await _require_table(db, "keywords")
    lib = (await db.execute(text("SELECT library_id FROM keywords WHERE id=:id"), {"id": keyword_id})).first()
    if not lib:
        raise HTTPException(status_code=404, detail="keyword_not_found")
    await db.execute(text("DELETE FROM keywords WHERE id=:id"), {"id": keyword_id})
    await db.execute(
        text(
            "UPDATE keyword_libraries SET keyword_count = (SELECT COUNT(*) FROM keywords WHERE library_id=:lid) WHERE id=:lid"
        ),
        {"lid": lib[0]},
    )
    return {"deleted": True}


async def create_keyword_library(db: AsyncSession, body: LibraryBody) -> dict:
    await _require_table(db, "keyword_libraries")
    row = (
        await db.execute(
            text("INSERT INTO keyword_libraries (name, description) VALUES (:n, :d) RETURNING id"),
            {"n": body.name.strip(), "d": body.description.strip()},
        )
    ).first()
    await db.flush()
    return {"item": {"id": int(row[0]), "name": body.name.strip(), "count": 0}}


async def list_keywords(db: AsyncSession, library_id: int) -> dict:
    await _require_table(db, "keywords")
    rows = (
        await db.execute(
            text("SELECT id, keyword, used_count FROM keywords WHERE library_id=:lid ORDER BY id DESC LIMIT 1000"),
            {"lid": library_id},
        )
    ).all()
    return {"items": [{"id": int(r[0]), "keyword": r[1], "used_count": int(r[2])} for r in rows]}


async def create_keyword(db: AsyncSession, library_id: int, body: KeywordBody) -> dict:
    await _require_table(db, "keywords")
    try:
        row = (
            await db.execute(
                text("INSERT INTO keywords (library_id, keyword) VALUES (:lid, :k) RETURNING id"),
                {"lid": library_id, "k": body.keyword.strip()},
            )
        ).first()
    except Exception as exc:
        raise HTTPException(status_code=422, detail="keyword_exists") from exc
    await db.flush()
    return {"item": {"id": int(row[0]), "keyword": body.keyword.strip()}}


async def list_image_libraries(db: AsyncSession) -> dict:
    await _require_table(db, "image_libraries")
    rows = (
        await db.execute(
            text(
                """
                SELECT il.id, il.name, il.description,
                       (SELECT COUNT(*) FROM images i WHERE i.library_id = il.id) AS cnt
                FROM image_libraries il ORDER BY il.name
                """
            )
        )
    ).all()
    return {"items": [{"id": int(r[0]), "name": r[1], "description": r[2] or "", "count": int(r[3])} for r in rows]}


async def create_image_library(db: AsyncSession, body: LibraryBody) -> dict:
    await _require_table(db, "image_libraries")
    row = (
        await db.execute(
            text("INSERT INTO image_libraries (name, description) VALUES (:n, :d) RETURNING id"),
            {"n": body.name.strip(), "d": body.description.strip()},
        )
    ).first()
    await db.flush()
    return {"item": {"id": int(row[0]), "name": body.name.strip(), "count": 0}}


async def delete_image_library(db: AsyncSession, library_id: int) -> dict:
    await _require_table(db, "image_libraries")
    in_use = int(
        await db.scalar(text("SELECT COUNT(*) FROM tasks WHERE image_library_id = :id"), {"id": library_id}) or 0
    )
    if in_use > 0:
        raise HTTPException(status_code=422, detail="library_in_use")
    await db.execute(text("DELETE FROM image_libraries WHERE id = :id"), {"id": library_id})
    logger.info("image_library_deleted id=%s", library_id)
    return {"deleted": True}


async def delete_image(db: AsyncSession, image_id: int) -> dict:
    await _require_table(db, "images")
    lib = (await db.execute(text("SELECT library_id FROM images WHERE id=:id"), {"id": image_id})).first()
    if not lib:
        raise HTTPException(status_code=404, detail="image_not_found")
    await db.execute(text("DELETE FROM images WHERE id=:id"), {"id": image_id})
    await db.execute(
        text(
            "UPDATE image_libraries SET image_count = (SELECT COUNT(*) FROM images WHERE library_id=:lid) WHERE id=:lid"
        ),
        {"lid": lib[0]},
    )
    return {"deleted": True}


async def list_images(db: AsyncSession, library_id: int) -> dict:
    await _require_table(db, "images")
    rows = (
        await db.execute(
            text(
                "SELECT id, original_name, file_path, mime_type, file_size FROM images WHERE library_id=:lid ORDER BY id DESC LIMIT 200"
            ),
            {"lid": library_id},
        )
    ).all()
    return {
        "items": [
            {"id": int(r[0]), "original_name": r[1], "file_path": r[2], "mime_type": r[3] or "", "file_size": int(r[4])}
            for r in rows
        ]
    }


async def create_image_meta(db: AsyncSession, library_id: int, body: ImageMetaBody) -> dict:
    await _require_table(db, "images")
    import os

    filename = os.path.basename(body.file_path)
    row = (
        await db.execute(
            text(
                """
                INSERT INTO images (library_id, filename, original_name, file_name, file_path, mime_type, file_size)
                VALUES (:lid, :fn, :on, :fn, :fp, :mt, :fs) RETURNING id
                """
            ),
            {
                "lid": library_id,
                "fn": filename,
                "on": body.original_name.strip(),
                "fp": body.file_path.strip(),
                "mt": body.mime_type,
                "fs": body.file_size,
            },
        )
    ).first()
    await db.flush()
    return {"item": {"id": int(row[0]), "original_name": body.original_name.strip(), "file_path": body.file_path.strip()}}


class BulkTitlesBody(BaseModel):
    titles: list[str] = Field(min_length=1, max_length=200)


class TitleGenerateBody(BaseModel):
    seed: str = ""
    count: int = Field(default=5, ge=1, le=20)


async def bulk_create_titles(db: AsyncSession, library_id: int, body: BulkTitlesBody) -> dict:
    created = 0
    for title in body.titles:
        t = title.strip()
        if not t:
            continue
        await create_title(db, library_id, TitleBody(title=t))
        created += 1
    logger.info("bulk_titles_created library_id=%s count=%s", library_id, created)
    return {"created": created}


async def generate_titles(db: AsyncSession, library_id: int, body: TitleGenerateBody) -> dict:
    await _require_table(db, "title_libraries")
    seed = body.seed.strip() or "技术品牌"
    titles = [f"{seed} · 洞察选题 {i}" for i in range(1, body.count + 1)]
    try:
        from app.ai.workflow_runner import run_workflow_sync

        wf = run_workflow_sync(
            "url_import",
            {"page_json": {"title": seed, "text": seed}, "url": "inline://generate"},
        )
        wf_titles = wf.get("titles") if isinstance(wf, dict) else []
        if isinstance(wf_titles, list) and wf_titles:
            titles = [str(t) for t in wf_titles[: body.count]]
    except Exception:
        logger.exception("generate_titles_workflow_fallback library_id=%s", library_id)
    created = 0
    for title in titles:
        await create_title(db, library_id, TitleBody(title=title))
        created += 1
    return {"created": created, "titles": titles}

