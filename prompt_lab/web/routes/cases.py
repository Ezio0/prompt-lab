"""Case management REST endpoints."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from prompt_lab.core.case_manager import CaseManager, CaseManagerError, InvalidCaseTypeError

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("")
@router.get("/")
def list_cases(
    request: Request,
    collection: str | None = Query(default=None),
    type: str | None = Query(default=None, alias="type"),
) -> list[dict[str, Any]]:
    """Return cases, optionally filtered by *collection* and/or *type*."""
    manager = CaseManager(request.app.state.project_root)

    if collection:
        try:
            cases = manager.get_cases(collection, type)
        except InvalidCaseTypeError as error:
            raise HTTPException(status_code=400, detail=str(error))
        except CaseManagerError as error:
            raise HTTPException(status_code=400, detail=str(error))
        return [asdict(c) for c in cases]

    # No collection specified — scan all collection directories.
    cases_dir = manager.cases_dir
    if not cases_dir.is_dir():
        return []

    if type is not None:
        try:
            manager._validate_type(type)
        except InvalidCaseTypeError as error:
            raise HTTPException(status_code=400, detail=str(error))

    results: list[dict[str, Any]] = []
    for child in sorted(cases_dir.iterdir()):
        if not child.is_dir():
            continue
        try:
            for case in manager.get_cases(child.name, type):
                results.append(asdict(case))
        except CaseManagerError:
            continue
    return results
