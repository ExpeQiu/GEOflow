from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbSession, get_api_auth, require_scope
from app.api.response import success
from app.models.task import Task, TaskRun
from app.services.geoflow.task_lifecycle import TaskLifecycleService

router = APIRouter()


class TaskCreate(BaseModel):
    name: str
    title_library_id: int
    prompt_id: int
    ai_model_id: int
    knowledge_base_id: int | None = None
    content_format: str = "article"
    publish_scope: str = "local_and_distribution"


class TaskUpdate(BaseModel):
    name: str | None = None
    status: str | None = None


@router.get("/tasks")
async def list_tasks(request: Request, db: DbSession, auth=Depends(get_api_auth)):
    _, scopes = auth
    require_scope(scopes, "tasks:read")
    rows = (await db.execute(select(Task).order_by(Task.id.desc()).limit(100))).scalars().all()
    return success(request, {"tasks": [_task_dict(t) for t in rows]})


@router.post("/tasks")
async def create_task(request: Request, body: TaskCreate, db: DbSession, auth=Depends(get_api_auth)):
    _, scopes = auth
    require_scope(scopes, "tasks:write")
    svc = TaskLifecycleService(db)
    task = await svc.create(body.model_dump())
    return success(request, {"task": _task_dict(task)}, status=201)


@router.get("/tasks/{task_id}")
async def show_task(task_id: int, request: Request, db: DbSession, auth=Depends(get_api_auth)):
    _, scopes = auth
    require_scope(scopes, "tasks:read")
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task_not_found")
    return success(request, {"task": _task_dict(task)})


@router.patch("/tasks/{task_id}")
async def update_task(task_id: int, body: TaskUpdate, request: Request, db: DbSession, auth=Depends(get_api_auth)):
    _, scopes = auth
    require_scope(scopes, "tasks:write")
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task_not_found")
    if body.name is not None:
        task.name = body.name
    if body.status is not None:
        task.status = body.status
    return success(request, {"task": _task_dict(task)})


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, request: Request, db: DbSession, auth=Depends(get_api_auth)):
    _, scopes = auth
    require_scope(scopes, "tasks:write")
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task_not_found")
    await db.delete(task)
    return success(request, {"deleted": True})


@router.post("/tasks/{task_id}/start")
async def start_task(task_id: int, request: Request, db: DbSession, auth=Depends(get_api_auth)):
    _, scopes = auth
    require_scope(scopes, "tasks:write")
    svc = TaskLifecycleService(db)
    task = await svc.start(task_id)
    return success(request, {"task": _task_dict(task)})


@router.post("/tasks/{task_id}/stop")
async def stop_task(task_id: int, request: Request, db: DbSession, auth=Depends(get_api_auth)):
    _, scopes = auth
    require_scope(scopes, "tasks:write")
    svc = TaskLifecycleService(db)
    task = await svc.stop(task_id)
    return success(request, {"task": _task_dict(task)})


@router.post("/tasks/{task_id}/enqueue")
async def enqueue_task(task_id: int, request: Request, db: DbSession, auth=Depends(get_api_auth)):
    _, scopes = auth
    require_scope(scopes, "tasks:write")
    svc = TaskLifecycleService(db)
    run = await svc.enqueue(task_id)
    return success(request, {"job": _run_dict(run)})


@router.get("/tasks/{task_id}/jobs")
async def task_jobs(task_id: int, request: Request, db: DbSession, auth=Depends(get_api_auth)):
    _, scopes = auth
    require_scope(scopes, "tasks:read")
    rows = (
        await db.execute(select(TaskRun).where(TaskRun.task_id == task_id).order_by(TaskRun.id.desc()).limit(50))
    ).scalars().all()
    return success(request, {"jobs": [_run_dict(r) for r in rows]})


def _task_dict(task: Task) -> dict:
    return {
        "id": task.id,
        "name": task.name,
        "status": task.status,
        "content_format": task.content_format,
        "publish_scope": task.publish_scope,
        "created_count": task.created_count,
        "published_count": task.published_count,
        "knowledge_base_id": task.knowledge_base_id,
        "last_run_at": task.last_run_at.isoformat() if task.last_run_at else None,
    }


def _run_dict(run: TaskRun) -> dict:
    return {
        "id": run.id,
        "task_id": run.task_id,
        "status": run.status,
        "article_id": run.article_id,
        "error_message": run.error_message,
        "duration_ms": run.duration_ms,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }
