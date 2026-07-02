from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, text

from app.api.deps import DbSession, get_api_auth, require_scope
from app.api.idempotency import check_idempotency, store_idempotency
from app.api.response import success
from app.models.knowledge import KnowledgeBase
from app.models.material import Author, Category, Prompt
from app.services.admin.production_service import _table_exists

router = APIRouter()

MATERIAL_TYPES = {"authors": Author, "categories": Category, "prompts": Prompt}
LIBRARY_TYPES = {"keyword-libraries", "title-libraries", "image-libraries", "knowledge-bases"}


@router.get("/materials")
async def materials_summary(request: Request, db: DbSession, auth=Depends(get_api_auth)):
    _, scopes = auth
    require_scope(scopes, "materials:read")
    summary = {}
    for name, model in MATERIAL_TYPES.items():
        count = len((await db.execute(select(model))).scalars().all())
        summary[name] = {"count": count}
    for lib in ("keyword-libraries", "title-libraries", "image-libraries"):
        table = lib.replace("-libraries", "_libraries")
        if await _table_exists(db, table):
            count = int(await db.scalar(text(f"SELECT COUNT(*) FROM {table}")) or 0)
            summary[lib] = {"count": count}
    kb_count = len((await db.execute(select(KnowledgeBase))).scalars().all())
    summary["knowledge-bases"] = {"count": kb_count}
    return success(request, {"summary": summary})


@router.get("/materials/{material_type}")
async def list_material(material_type: str, request: Request, db: DbSession, auth=Depends(get_api_auth)):
    _, scopes = auth
    require_scope(scopes, "materials:read")
    if material_type in LIBRARY_TYPES:
        return success(request, await _list_library(db, material_type))
    model = MATERIAL_TYPES.get(material_type)
    if model is None:
        raise HTTPException(status_code=404, detail="unknown_material_type")
    rows = (await db.execute(select(model).limit(200))).scalars().all()
    return success(request, {"items": [_serialize(row) for row in rows]})


class MaterialCreate(BaseModel):
    name: str
    slug: str | None = None
    type: str | None = None
    content: str | None = None
    description: str = ""


class MaterialUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    type: str | None = None
    content: str | None = None
    description: str | None = None


@router.post("/materials/{material_type}")
async def create_material(
    material_type: str, body: MaterialCreate, request: Request, db: DbSession, auth=Depends(get_api_auth)
):
    _, scopes = auth
    require_scope(scopes, "materials:write")
    route_key = f"POST:/materials/{material_type}"
    body_bytes = await request.body()
    cached = await check_idempotency(db, request, route_key, body_bytes)
    if cached:
        return success(request, cached["body"], status=cached["status"])

    if material_type in LIBRARY_TYPES:
        item = await _create_library(db, material_type, body)
        payload = {"item": item}
        await store_idempotency(db, request, route_key, body_bytes, payload, 201)
        return success(request, payload, status=201)
    model = MATERIAL_TYPES.get(material_type)
    if model is None:
        raise HTTPException(status_code=404, detail="unknown_material_type")
    if model is Author:
        row = Author(name=body.name)
    elif model is Category:
        row = Category(name=body.name, slug=body.slug or body.name.lower().replace(" ", "-"))
    else:
        row = Prompt(name=body.name, type=body.type or "content", content=body.content or "")
    db.add(row)
    await db.flush()
    payload = {"item": _serialize(row)}
    await store_idempotency(db, request, route_key, body_bytes, payload, 201)
    return success(request, payload, status=201)


@router.patch("/materials/{material_type}/{item_id}")
async def patch_material(
    material_type: str,
    item_id: int,
    body: MaterialUpdate,
    request: Request,
    db: DbSession,
    auth=Depends(get_api_auth),
):
    _, scopes = auth
    require_scope(scopes, "materials:write")
    route_key = f"PATCH:/materials/{material_type}/{item_id}"
    body_bytes = await request.body()
    cached = await check_idempotency(db, request, route_key, body_bytes)
    if cached:
        return success(request, cached["body"], status=cached["status"])

    if material_type in LIBRARY_TYPES:
        item = await _patch_library(db, material_type, item_id, body)
    else:
        item = await _patch_entity(db, material_type, item_id, body)
    payload = {"item": item}
    await store_idempotency(db, request, route_key, body_bytes, payload, 200)
    return success(request, payload)


@router.delete("/materials/{material_type}/{item_id}")
async def delete_material(
    material_type: str, item_id: int, request: Request, db: DbSession, auth=Depends(get_api_auth)
):
    _, scopes = auth
    require_scope(scopes, "materials:write")
    if material_type in LIBRARY_TYPES:
        deleted = await _delete_library(db, material_type, item_id)
    else:
        deleted = await _delete_entity(db, material_type, item_id)
    return success(request, deleted)


async def _list_library(db: DbSession, material_type: str) -> dict:
    if material_type == "knowledge-bases":
        rows = (await db.execute(select(KnowledgeBase).limit(200))).scalars().all()
        return {"items": [{"id": r.id, "name": r.name, "description": r.description or ""} for r in rows]}
    table = material_type.replace("-libraries", "_libraries")
    if not await _table_exists(db, table):
        return {"items": []}
    rows = (await db.execute(text(f"SELECT id, name, description FROM {table} ORDER BY id DESC LIMIT 200"))).all()
    return {"items": [{"id": int(r[0]), "name": r[1], "description": r[2] or ""} for r in rows]}


async def _create_library(db: DbSession, material_type: str, body: MaterialCreate) -> dict:
    if material_type == "knowledge-bases":
        row = KnowledgeBase(name=body.name.strip(), description=body.description.strip(), content=body.content or "")
        db.add(row)
        await db.flush()
        return {"id": row.id, "name": row.name}
    table = material_type.replace("-libraries", "_libraries")
    if not await _table_exists(db, table):
        raise HTTPException(status_code=503, detail=f"{table}_not_migrated")
    result = (
        await db.execute(
            text(f"INSERT INTO {table} (name, description) VALUES (:n, :d) RETURNING id"),
            {"n": body.name.strip(), "d": body.description.strip()},
        )
    ).first()
    await db.flush()
    return {"id": int(result[0]), "name": body.name.strip()}


async def _patch_library(db: DbSession, material_type: str, item_id: int, body: MaterialUpdate) -> dict:
    if material_type == "knowledge-bases":
        row = await db.get(KnowledgeBase, item_id)
        if row is None:
            raise HTTPException(status_code=404, detail="not_found")
        if body.name is not None:
            row.name = body.name.strip()
        if body.description is not None:
            row.description = body.description.strip()
        if body.content is not None:
            row.content = body.content
        await db.flush()
        return {"id": row.id, "name": row.name}
    table = material_type.replace("-libraries", "_libraries")
    if not await _table_exists(db, table):
        raise HTTPException(status_code=503, detail=f"{table}_not_migrated")
    existing = (await db.execute(text(f"SELECT id FROM {table} WHERE id=:id"), {"id": item_id})).first()
    if not existing:
        raise HTTPException(status_code=404, detail="not_found")
    sets = []
    params: dict = {"id": item_id}
    if body.name is not None:
        sets.append("name=:n")
        params["n"] = body.name.strip()
    if body.description is not None:
        sets.append("description=:d")
        params["d"] = body.description.strip()
    if not sets:
        return {"id": item_id}
    await db.execute(text(f"UPDATE {table} SET {', '.join(sets)}, updated_at=CURRENT_TIMESTAMP WHERE id=:id"), params)
    await db.flush()
    return {"id": item_id, "name": params.get("n", "")}


async def _delete_library(db: DbSession, material_type: str, item_id: int) -> dict:
    if material_type == "knowledge-bases":
        row = await db.get(KnowledgeBase, item_id)
        if row is None:
            raise HTTPException(status_code=404, detail="not_found")
        await db.delete(row)
        await db.flush()
        return {"deleted": True, "id": item_id}
    table = material_type.replace("-libraries", "_libraries")
    if not await _table_exists(db, table):
        raise HTTPException(status_code=503, detail=f"{table}_not_migrated")
    result = await db.execute(text(f"DELETE FROM {table} WHERE id=:id"), {"id": item_id})
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="not_found")
    return {"deleted": True, "id": item_id}


async def _patch_entity(db: DbSession, material_type: str, item_id: int, body: MaterialUpdate) -> dict:
    model = MATERIAL_TYPES.get(material_type)
    if model is None:
        raise HTTPException(status_code=404, detail="unknown_material_type")
    row = await db.get(model, item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="not_found")
    if body.name is not None and hasattr(row, "name"):
        row.name = body.name.strip()
    if body.slug is not None and hasattr(row, "slug"):
        row.slug = body.slug.strip()
    if body.type is not None and hasattr(row, "type"):
        row.type = body.type.strip()
    if body.content is not None and hasattr(row, "content"):
        row.content = body.content
    await db.flush()
    return _serialize(row)


async def _delete_entity(db: DbSession, material_type: str, item_id: int) -> dict:
    model = MATERIAL_TYPES.get(material_type)
    if model is None:
        raise HTTPException(status_code=404, detail="unknown_material_type")
    row = await db.get(model, item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="not_found")
    await db.delete(row)
    await db.flush()
    return {"deleted": True, "id": item_id}


def _serialize(row) -> dict:
    data = {"id": row.id}
    for field in ("name", "slug", "type", "bio", "description"):
        if hasattr(row, field):
            data[field] = getattr(row, field)
    return data
