"""Access-log middleware for the Prompt Lab web server.

Each request is appended to ``.prompt-lab/web.log`` as a single JSON object
per line.  The log is created lazily on first request.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Write one JSON line per request to ``<project_root>/.prompt-lab/web.log``."""

    def __init__(self, app, log_path: Path) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.log_path = log_path

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def, override]
        start = time.perf_counter()
        method = request.method
        path = request.url.path

        try:
            response: Response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            self._append(method, path, status_code, time.perf_counter() - start)
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        self._append(method, path, status_code, duration_ms)
        return response

    def _append(self, method: str, path: str, status_code: int, duration_ms: float) -> None:
        entry = {
            "timestamp": _timestamp(),
            "method": method,
            "path": path,
            "status": status_code,
            "duration_ms": round(duration_ms, 2),
        }
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
