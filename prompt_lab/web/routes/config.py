"""Project configuration REST endpoint.

Only the ``api_key_env`` *name* is ever returned — never the actual key value.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from prompt_lab.core.config import Config, ConfigError

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config")
def get_config(request: Request) -> dict[str, Any]:
    """Return the project configuration with sensitive fields stripped."""
    try:
        config = Config.load(request.app.state.project_root)
    except ConfigError as error:
        raise HTTPException(status_code=500, detail=str(error))

    return {
        "provider": {
            "base_url": config.provider.base_url,
            "api_key_env": config.provider.api_key_env,
            "model": config.provider.model,
            "default_params": config.provider.default_params,
        },
        "run": {
            "timeout_seconds": config.run.timeout_seconds,
            "concurrency": config.run.concurrency,
        },
        "eval": {
            "enabled": config.eval.enabled,
            "metrics": [
                {"name": m.name, "params": m.params}
                for m in config.eval.metrics
            ],
            "model": config.eval.model,
            "api_key_env": config.eval.api_key_env,
        },
    }
