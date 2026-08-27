"""登录失败锁定（进程内；多 worker 时各自计数，生产可换 Redis）。"""

from __future__ import annotations

import logging
import threading
import time

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_failures: dict[str, list[float]] = {}


def _key(username: str, ip: str) -> str:
    return f"{(username or '').strip().lower()}|{ip or '-'}"


def is_locked(username: str, ip: str = "") -> tuple[bool, int]:
    settings = get_settings()
    window = max(60, int(settings.login_lockout_seconds))
    max_fail = max(3, int(settings.login_max_failures))
    now = time.time()
    k = _key(username, ip)
    with _lock:
        stamps = [t for t in _failures.get(k, []) if now - t < window]
        _failures[k] = stamps
        if len(stamps) >= max_fail:
            remaining = int(window - (now - stamps[0]))
            return True, max(1, remaining)
    return False, 0


def record_failure(username: str, ip: str = "") -> int:
    settings = get_settings()
    window = max(60, int(settings.login_lockout_seconds))
    now = time.time()
    k = _key(username, ip)
    with _lock:
        stamps = [t for t in _failures.get(k, []) if now - t < window]
        stamps.append(now)
        _failures[k] = stamps
        count = len(stamps)
    logger.warning("login_failure username=%s ip=%s count=%s", username, ip, count)
    return count


def clear_failures(username: str, ip: str = "") -> None:
    k = _key(username, ip)
    with _lock:
        _failures.pop(k, None)
