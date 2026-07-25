"""Typed records persisted and exchanged by Prompt Lab."""

from dataclasses import dataclass
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
