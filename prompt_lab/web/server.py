"""FastAPI application factory for the Prompt Lab web server."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from prompt_lab.web.middleware import AccessLogMiddleware
from prompt_lab.web.routes import cases as cases_routes
from prompt_lab.web.routes import config as config_routes
from prompt_lab.web.routes import runs as runs_routes
from prompt_lab.web.routes import versions as versions_routes


def create_app(project_root: Path) -> FastAPI:
    """Create and return a fully wired FastAPI application.

    Parameters
    ----------
    project_root:
        The Prompt Lab project directory (containing ``prompt-lab.yaml``
        and ``.prompt-lab/``).
    """
    app = FastAPI(title="Prompt Lab API", version="2.0.0")

    # Store the project root so route handlers can access it.
    app.state.project_root = Path(project_root)

    # CORS — allow localhost development (React dev server etc.).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost",
            "http://localhost:5173",
            "http://127.0.0.1",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8765",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Access log middleware — one JSON line per request.
    log_path = Path(project_root) / ".prompt-lab" / "web.log"
    app.add_middleware(AccessLogMiddleware, log_path=log_path)

    # ---- REST API routers ----
    app.include_router(versions_routes.router)
    app.include_router(cases_routes.router)
    app.include_router(runs_routes.router)
    app.include_router(config_routes.router)

    # ---- Health check ----
    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # ---- Static files / SPA hosting ----
    _mount_static(app, Path(project_root))

    return app


def _mount_static(app: FastAPI, project_root: Path) -> None:
    """Mount the React SPA build output and set up SPA fallback.

    When the frontend build directory exists, static files are served at ``/``
    and any non-``/api/`` GET request that doesn't match a file falls back to
    ``index.html`` (SPA history-mode routing).

    When the build directory is missing, ``GET /`` returns a JSON hint.
    """
    dist_dir = project_root / "web" / "frontend" / "dist"
    if dist_dir.is_dir():
        index_html = dist_dir / "index.html"

        # Serve static assets (JS, CSS, images) from /assets/ etc.
        app.mount(
            "/assets",
            StaticFiles(directory=str(dist_dir / "assets")) if (dist_dir / "assets").is_dir() else StaticFiles(directory=str(dist_dir)),
            name="assets",
        )

        @app.get("/{path:path}", response_model=None)
        def spa_fallback(path: str):  # type: ignore[no-untyped-def]
            """Serve a static file, or fall back to index.html for SPA routes."""
            # Never intercept API routes.
            if path.startswith("api/"):
                return JSONResponse(
                    status_code=404, content={"detail": "Not Found"}
                )
            candidate = dist_dir / path
            if path and candidate.is_file():
                return FileResponse(str(candidate))
            if index_html.is_file():
                return FileResponse(str(index_html))
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
    else:
        @app.get("/")
        def frontend_not_built() -> JSONResponse:  # type: ignore[no-untyped-def]
            return JSONResponse(
                status_code=200,
                content={
                    "message": "Frontend not built yet. Run 'npm run build' in web/frontend/.",
                    "docs": "See T-306 in the implementation plan.",
                },
            )
