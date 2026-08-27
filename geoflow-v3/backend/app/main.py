"""GEOFlow v3 FastAPI 入口。"""

from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.admin.routes import router as admin_router
from app.api.deps import get_admin_jwt
from app.api.internal.content_agent import router as internal_router
from app.api.v1 import router as v1_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.ws.tasks import tasks_websocket

settings = get_settings()
setup_logging(settings.debug)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.assert_secure_startup()
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

_cors_origins = settings.cors_origins_list()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["http://127.0.0.1:13001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-Id") or str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-Id"] = request.state.request_id
    # 基础安全头（Admin 侧 Next 也会加 CSP）
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version}


@app.get("/up")
async def up():
    return {"status": "ok"}


app.include_router(v1_router)
app.include_router(admin_router)
app.include_router(internal_router)

_upload_root = Path(settings.upload_path).resolve()
_upload_root.mkdir(parents=True, exist_ok=True)


@app.get("/uploads/{file_path:path}")
async def protected_upload(file_path: str, jwt=Depends(get_admin_jwt)):
    """上传文件需 Admin JWT（Bearer 或 HttpOnly Cookie）。"""
    target = (_upload_root / file_path).resolve()
    try:
        target.relative_to(_upload_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_path") from exc
    if not target.is_file():
        raise HTTPException(status_code=404, detail="file_not_found")
    return FileResponse(target)


app.websocket("/ws/admin/tasks")(tasks_websocket)
