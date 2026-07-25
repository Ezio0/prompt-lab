"""Configuration loading and validation."""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when a project configuration cannot be used."""

    code = "E_CONFIG_INVALID"

    def __init__(self, detail: str) -> None:
        super().__init__(f"{self.code}: prompt-lab.yaml is invalid: {detail}")


@dataclass(frozen=True)
class ProviderConfig:
    """Connection settings for an OpenAI-compatible provider."""

    base_url: str
    api_key_env: str
    api_key: str
    model: str
    default_params: dict[str, Any]


@dataclass(frozen=True)
class RunConfig:
    """Runtime settings for a comparison run."""

    timeout_seconds: float
    concurrency: int


@dataclass(frozen=True)
class Config:
    """Full project configuration."""

    provider: ProviderConfig
    run: RunConfig

    @classmethod
    def load(cls, project_root: Path) -> "Config":
        """Load and validate ``prompt-lab.yaml`` from *project_root*."""
        config_path = project_root / "prompt-lab.yaml"
        if not config_path.is_file():
            raise ConfigError("file not found")

        try:
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as error:
            raise ConfigError(str(error)) from error

        if not isinstance(raw, dict):
            raise ConfigError("root must be a mapping")

        try:
            provider_data = _mapping(raw, "provider")
            run_data = _mapping(raw, "run")
            base_url = _string(provider_data, "base_url")
            api_key_env = _string(provider_data, "api_key_env")
            model = _string(provider_data, "model")
            default_params = _mapping(provider_data, "default_params")
            timeout_seconds = _number(run_data, "timeout_seconds")
            concurrency = _positive_int(run_data, "concurrency")
        except KeyError as error:
            raise ConfigError(f"missing required field '{error.args[0]}'") from error
        except TypeError as error:
            raise ConfigError(str(error)) from error

        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise ConfigError(f"environment variable '{api_key_env}' is not set")

        return cls(
            provider=ProviderConfig(
                base_url=base_url.rstrip("/"),
                api_key_env=api_key_env,
                api_key=api_key,
                model=model,
                default_params=dict(default_params),
            ),
            run=RunConfig(timeout_seconds=timeout_seconds, concurrency=concurrency),
        )


def _mapping(source: dict[str, Any], field: str) -> dict[str, Any]:
    value = source[field]
    if not isinstance(value, dict):
        raise TypeError(f"'{field}' must be a mapping")
    return value


def _string(source: dict[str, Any], field: str) -> str:
    value = source[field]
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"'{field}' must be a non-empty string")
    return value.strip()


def _number(source: dict[str, Any], field: str) -> float:
    value = source[field]
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise TypeError(f"'{field}' must be a positive number")
    return float(value)


def _positive_int(source: dict[str, Any], field: str) -> int:
    value = source[field]
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise TypeError(f"'{field}' must be a positive integer")
    return value
