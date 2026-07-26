"""Version management REST endpoints."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from prompt_lab.core.version_manager import (
    VersionAlreadyExistsError,
    VersionManager,
    VersionManagerError,
    VersionNotFoundError,
)

router = APIRouter(prefix="/api/versions", tags=["versions"])


def _version_summary(version: Any) -> dict[str, Any]:
    """Return version metadata *without* ``prompt_text`` (for list views)."""
    data = asdict(version)
    data.pop("prompt_text", None)
    return data


@router.get("")
@router.get("/")
def list_versions(request: Request, limit: int = 50) -> list[dict[str, Any]]:
    """Return a list of all registered versions (without prompt text)."""
    manager = VersionManager(request.app.state.project_root)
    return [_version_summary(v) for v in manager.list_versions(limit)]


@router.get("/{version_id}")
def get_version(version_id: str, request: Request) -> dict[str, Any]:
    """Return the full version record including ``prompt_text``."""
    manager = VersionManager(request.app.state.project_root)
    try:
        version = manager.get_version(version_id)
    except VersionNotFoundError:
        raise HTTPException(status_code=404, detail=f"version '{version_id}' not found")
    except VersionManagerError as error:
        raise HTTPException(status_code=500, detail=str(error))
    return asdict(version)


@router.get("/{version_a}/{version_b}/diff")
def diff_versions(version_a: str, version_b: str, request: Request) -> dict[str, str]:
    """Return a unified diff between two versions."""
    manager = VersionManager(request.app.state.project_root)
    try:
        diff_text = manager.diff(version_a, version_b)
    except VersionNotFoundError:
        raise HTTPException(status_code=404, detail="one or both versions not found")
    except VersionManagerError as error:
        raise HTTPException(status_code=500, detail=str(error))
    return {"diff": diff_text}


class VersionCreate(BaseModel):
    """Request body for registering a new version via the API."""

    name: str
    prompt_text: str
    changed_from: str | None = None
    changed_var: str = "prompt"
    change_note: str = ""
    author: str = ""


@router.post("")
@router.post("/")
def create_version(body: VersionCreate, request: Request) -> dict[str, Any]:
    """Register a new immutable prompt version."""
    manager = VersionManager(request.app.state.project_root)
    try:
        version = manager.add_version(
            body.name,
            body.prompt_text,
            changed_from=body.changed_from,
            changed_var=body.changed_var,
            change_note=body.change_note,
            author=body.author,
        )
    except VersionAlreadyExistsError:
        raise HTTPException(status_code=409, detail=f"version '{body.name}' already exists")
    except (VersionManagerError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error))
    return asdict(version)
