"""统一 API 响应格式。"""

from typing import Any

from fastapi import Request


def success(request: Request, data: Any, status: int = 200) -> dict:
    return {
        "success": True,
        "data": data,
        "meta": {"request_id": getattr(request.state, "request_id", "local")},
        "status": status,
    }
