"""API v1 路由聚合。"""

from fastapi import APIRouter

from app.api.v1 import articles, auth, catalog, jobs, materials, tasks

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router, tags=["auth"])
router.include_router(catalog.router, tags=["catalog"])
router.include_router(tasks.router, tags=["tasks"])
router.include_router(jobs.router, tags=["jobs"])
router.include_router(materials.router, tags=["materials"])
router.include_router(articles.router, tags=["articles"])
