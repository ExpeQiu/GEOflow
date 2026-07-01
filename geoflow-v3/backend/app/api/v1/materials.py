from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbSession, get_api_auth, require_scope
from app.api.response import success
from app.models.material import Author, Category, Prompt

router = APIRouter()

MATERIAL_TYPES = {"authors": Author, "categories": Category, "prompts": Prompt}


@router.get("/materials")
async def materials_summary(request: Request, db: DbSession, auth=Depends(get_api_auth)):
    _, scopes = auth
    require_scope(scopes, "materials:read")
    summary = {}
    for name, model in MATERIAL_TYPES.items():
        count = len((await db.execute(select(model))).scalars().all())
        summary[name] = {"count": count}
    return success(request, {"summary": summary})


@router.get("/materials/{material_type}")
async def list_material(material_type: str, request: Request, db: DbSession, auth=Depends(get_api_auth)):
    _, scopes = auth
    require_scope(scopes, "materials:read")
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


@router.post("/materials/{material_type}")
async def create_material(
    material_type: str, body: MaterialCreate, request: Request, db: DbSession, auth=Depends(get_api_auth)
):
    _, scopes = auth
    require_scope(scopes, "materials:write")
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
    return success(request, {"item": _serialize(row)}, status=201)


def _serialize(row) -> dict:
    data = {"id": row.id}
    for field in ("name", "slug", "type", "bio", "description"):
        if hasattr(row, field):
            data[field] = getattr(row, field)
    return data
