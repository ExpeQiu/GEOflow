"""GEOFlow v3 FastAPI 入口。"""

from contextlib import asynccontextmanager
from uuid import uuid4

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.admin.routes import router as admin_router
from app.api.internal.content_agent import router as internal_router
from app.api.v1 import router as v1_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.ws.tasks import tasks_websocket

settings = get_settings()
setup_logging(settings.debug)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-Id") or str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-Id"] = request.state.request_id
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
app.mount("/uploads", StaticFiles(directory=str(_upload_root)), name="uploads")

app.websocket("/ws/admin/tasks")(tasks_websocket)
