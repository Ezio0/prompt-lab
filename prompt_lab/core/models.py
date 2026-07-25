"""Typed records persisted and exchanged by Prompt Lab."""

from dataclasses import dataclass


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
