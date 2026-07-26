"""Run management REST endpoints."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from prompt_lab.core.case_manager import CaseManager, CaseManagerError
from prompt_lab.core.config import Config, ConfigError
from prompt_lab.core.provider import Provider, ProviderError
from prompt_lab.core.run_engine import RunEngine
from prompt_lab.core.version_manager import VersionManager, VersionManagerError, VersionNotFoundError

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _runs_dir(project_root: Path) -> Path:
    return project_root / ".prompt-lab" / "runs"


@router.get("")
@router.get("/")
def list_runs(request: Request) -> list[dict[str, Any]]:
    """Return a summary list of all stored runs (newest first)."""
    runs_dir = _runs_dir(request.app.state.project_root)
    if not runs_dir.is_dir():
        return []

    runs: list[dict[str, Any]] = []
    for run_path in sorted(runs_dir.iterdir(), reverse=True):
        if not run_path.is_dir():
            continue
        result_file = run_path / "result.json"
        if not result_file.is_file():
            continue
        try:
            data = json.loads(result_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        runs.append({
            "run_id": data.get("run_id", run_path.name),
            "baseline_version": data.get("baseline_version"),
            "candidate_version": data.get("candidate_version"),
            "dataset": data.get("dataset"),
            "timestamp": data.get("timestamp"),
            "total_cases": len(data.get("cases", [])),
        })
    return runs


@router.get("/{run_id}")
def get_run(run_id: str, request: Request) -> dict[str, Any]:
    """Return the full ``result.json`` data for a single run."""
    result_file = _runs_dir(request.app.state.project_root) / run_id / "result.json"
    if not result_file.is_file():
        raise HTTPException(status_code=404, detail=f"run '{run_id}' not found")
    try:
        return json.loads(result_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=500, detail=f"invalid run data: {error}")


class RunTrigger(BaseModel):
    """Request body for triggering a new A/B run."""

    baseline: str
    candidate: str
    dataset: str
    model: str | None = None
    max_tokens: int | None = None
    thinking: str | None = None
    concurrency: int | None = None


@router.post("")
@router.post("/")
def trigger_run(body: RunTrigger, request: Request) -> dict[str, Any]:
    """Trigger a synchronous A/B run and return the full result."""
    root: Path = request.app.state.project_root
    try:
        config = Config.load(root)
        versions = VersionManager(root)
        baseline_version = versions.get_version(body.baseline)
        candidate_version = versions.get_version(body.candidate)
        case_set = CaseManager(root).get_cases(body.dataset)
        if not case_set:
            raise HTTPException(
                status_code=400,
                detail=f"dataset '{body.dataset}' not found or contains no cases",
            )
        run_config = config.run if body.concurrency is None else type(config.run)(
            config.run.timeout_seconds, body.concurrency
        )
        params = {
            key: value
            for key, value in {
                "model": body.model,
                "max_tokens": body.max_tokens,
                "thinking": body.thinking,
            }.items()
            if value is not None
        }
        result = asyncio.run(
            RunEngine(Provider(config.provider), run_config, project_root=root).run(
                baseline_version.prompt_text,
                candidate_version.prompt_text,
                case_set,
                baseline_version=body.baseline,
                candidate_version=body.candidate,
                dataset=body.dataset,
                provider_params=params,
            )
        )
    except HTTPException:
        raise
    except VersionNotFoundError:
        raise HTTPException(status_code=404, detail="one or both versions not found")
    except (ConfigError, VersionManagerError, CaseManagerError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error))
    except ProviderError as error:
        raise HTTPException(status_code=502, detail=str(error))
    except Exception as error:  # pragma: no cover — safety net for unexpected provider errors
        raise HTTPException(status_code=502, detail=str(error))

    # Return the serialized result as JSON.
    result_file = _runs_dir(root) / result.run_id / "result.json"
    return json.loads(result_file.read_text(encoding="utf-8"))
