from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.api.deps import DbSession, get_api_auth, require_scope
from app.api.response import success
from app.models.material import AiModel, Author, Category, Prompt

router = APIRouter()


@router.get("/catalog")
async def catalog(
    request: Request,
    db: DbSession,
    auth=Depends(get_api_auth),
):
    admin, scopes = auth
    require_scope(scopes, "catalog:read")
    models = (await db.execute(select(AiModel).where(AiModel.status == "active"))).scalars().all()
    prompts = (await db.execute(select(Prompt))).scalars().all()
    categories = (await db.execute(select(Category).order_by(Category.sort_order))).scalars().all()
    authors = (await db.execute(select(Author))).scalars().all()
    return success(
        request,
        {
            "ai_models": [{"id": m.id, "name": m.name, "model_id": m.model_id, "model_type": m.model_type} for m in models],
            "prompts": [{"id": p.id, "name": p.name, "type": p.type} for p in prompts],
            "categories": [{"id": c.id, "name": c.name, "slug": c.slug} for c in categories],
            "authors": [{"id": a.id, "name": a.name} for a in authors],
        },
    )
