"""Typed records persisted and exchanged by Prompt Lab."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Version:
    """An immutable registered prompt version."""

    id: str
    content_hash: str
    prompt_text: str
    timestamp: str
    author: str = ""
    changed_from: str | None = None
    changed_var: str = "prompt"
    change_note: str = ""
    prompt_file: str | None = None


@dataclass(frozen=True)
class Case:
    """A reusable prompt input, either ideal-state or a production bad case."""

    id: str
    type: str
    input: dict[str, Any]
    collection: str
    expected_output: str | None = None
    expected_output_note: str = ""
    actual_output: str | None = None
    issue: str = ""


@dataclass(frozen=True)
class ProviderResponse:
    """Normalized OpenAI-compatible completion response."""

    content: str
    prompt_tokens: int
    completion_tokens: int
    finish_reason: str | None


@dataclass(frozen=True)
class ExecutionResult:
    """Metrics and outcome for one prompt applied to one case."""

    output: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    finish_reason: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class EvalResult:
    """One metric evaluation outcome for one case-version pair."""

    metric_name: str
    score: float
    reason: str
    status: str               # "pass" | "skipped" | "error"
    error: str | None = None


@dataclass(frozen=True)
class CaseResult:
    """Baseline and candidate outcomes for a single case."""

    case_id: str
    baseline: ExecutionResult
    candidate: ExecutionResult
    evaluations: list[EvalResult] = field(default_factory=list)


@dataclass(frozen=True)
class RunResult:
    """A complete persisted A/B comparison run."""

    run_id: str
    baseline_version: str
    candidate_version: str
    dataset: str
    provider_config: dict[str, Any]
    timestamp: str
    cases: list[CaseResult]
    summary: dict[str, dict[str, float]]
