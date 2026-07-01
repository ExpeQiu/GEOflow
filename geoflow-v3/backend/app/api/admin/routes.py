"""Admin BFF API — geoflow-admin 专用。"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbSession, get_admin_jwt
from app.api.response import success
from app.models.task import Task, TaskRun
from app.models.tech_ip import TechIpAsset
from app.models.knowledge import KnowledgeBase
from app.services.geoflow.task_lifecycle import TaskLifecycleService
from app.ws.tasks import broadcast_tasks_overview

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard")
async def dashboard(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    tasks = (await db.execute(select(Task).limit(50))).scalars().all()
    assets = (await db.execute(select(TechIpAsset).limit(50))).scalars().all()
    return success(
        request,
        {
            "tasks_count": len(tasks),
            "tech_ip_assets_count": len(assets),
            "version": "3.0.0",
        },
    )


@router.get("/tasks/overview")
async def tasks_overview(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    tasks = (await db.execute(select(Task).order_by(Task.id.desc()).limit(30))).scalars().all()
    runs = (await db.execute(select(TaskRun).order_by(TaskRun.id.desc()).limit(15))).scalars().all()
    return success(
        request,
        {
            "tasks": [{"id": t.id, "name": t.name, "status": t.status, "created_count": t.created_count} for t in tasks],
            "recent_runs": [{"id": r.id, "status": r.status, "task_id": r.task_id} for r in runs],
        },
    )


class EnqueueBody(BaseModel):
    task_id: int


@router.post("/tasks/enqueue")
async def admin_enqueue(body: EnqueueBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    svc = TaskLifecycleService(db)
    run = await svc.enqueue(body.task_id)
    await broadcast_tasks_overview()
    return success(request, {"job": {"id": run.id, "status": run.status}})


@router.get("/tech-assets")
async def list_tech_assets(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    rows = (await db.execute(select(TechIpAsset).order_by(TechIpAsset.priority))).scalars().all()
    return success(request, {"items": [_asset_dict(a) for a in rows]})


class TechAssetBody(BaseModel):
    ip_id: str
    name: str
    mind_tag: str = ""
    wiki_type: str = "concept"
    priority: int = 100


@router.post("/tech-assets")
async def create_tech_asset(body: TechAssetBody, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    asset = TechIpAsset(**body.model_dump())
    db.add(asset)
    await db.flush()
    return success(request, {"item": _asset_dict(asset)}, status=201)


@router.get("/knowledge-bases")
async def list_knowledge_bases(request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    rows = (await db.execute(select(KnowledgeBase))).scalars().all()
    return success(request, {"items": [{"id": k.id, "name": k.name} for k in rows]})


@router.post("/knowledge-bases/{kb_id}/sync-chunks")
async def sync_kb_chunks(kb_id: int, request: Request, db: DbSession, jwt=Depends(get_admin_jwt)):
    from app.workers.celery_app import celery_app

    celery_app.send_task("app.workers.tasks.sync_knowledge_chunks", args=[kb_id])
    return success(request, {"queued": True, "knowledge_base_id": kb_id})


def _asset_dict(a: TechIpAsset) -> dict:
    return {
        "id": a.id,
        "ip_id": a.ip_id,
        "name": a.name,
        "mind_tag": a.mind_tag,
        "wiki_type": a.wiki_type,
        "wiki_slug": a.wiki_slug,
        "priority": a.priority,
        "status": a.status,
    }
