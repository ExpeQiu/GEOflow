from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.deps import DbSession, get_api_auth, require_scope
from app.api.response import success
from app.models.task import TaskRun

router = APIRouter()


@router.get("/jobs/{job_id}")
async def show_job(job_id: int, request: Request, db: DbSession, auth=Depends(get_api_auth)):
    _, scopes = auth
    require_scope(scopes, "jobs:read")
    run = await db.get(TaskRun, job_id)
    if run is None:
        raise HTTPException(status_code=404, detail="job_not_found")
    return success(
        request,
        {
            "job": {
                "id": run.id,
                "task_id": run.task_id,
                "status": run.status,
                "article_id": run.article_id,
                "error_message": run.error_message,
                "duration_ms": run.duration_ms,
                "meta": run.meta,
            }
        },
    )
