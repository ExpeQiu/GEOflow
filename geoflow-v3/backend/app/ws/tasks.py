"""WebSocket 任务监控 — 替代 Laravel Reverb。"""

import json
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.models.task import Task, TaskRun

logger = get_logger("ws.tasks")

_connections: set[WebSocket] = set()


async def broadcast_tasks_overview() -> None:
    payload = await _build_overview()
    dead: list[WebSocket] = []
    for ws in _connections:
        try:
            await ws.send_json({"event": "tasks.overview.updated", "data": payload})
        except Exception:  # noqa: BLE001
            dead.append(ws)
    for ws in dead:
        _connections.discard(ws)


async def _build_overview() -> dict[str, Any]:
    async with async_session_factory() as db:
        tasks = (await db.execute(select(Task).order_by(Task.id.desc()).limit(20))).scalars().all()
        runs = (await db.execute(select(TaskRun).order_by(TaskRun.id.desc()).limit(10))).scalars().all()
    return {
        "tasks": [{"id": t.id, "name": t.name, "status": t.status} for t in tasks],
        "recent_runs": [{"id": r.id, "task_id": r.task_id, "status": r.status} for r in runs],
        "queue_overview": {"pending": sum(1 for r in runs if r.status == "queued")},
        "worker_overview": {"active": sum(1 for r in runs if r.status == "running")},
    }


async def tasks_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    _connections.add(websocket)
    logger.info("ws_connected", total=len(_connections))
    try:
        await websocket.send_json({"event": "tasks.overview.updated", "data": await _build_overview()})
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        _connections.discard(websocket)
