"""Immutable local prompt version storage."""

from dataclasses import asdict
from datetime import UTC, datetime
import difflib
import hashlib
import json
from pathlib import Path

from prompt_lab.core.models import Version


class VersionManagerError(ValueError):
    """Base error for version storage operations."""


class VersionAlreadyExistsError(VersionManagerError):
    """Raised when an immutable version name is reused."""

    def __init__(self, name: str) -> None:
        super().__init__(f"E_ALREADY_EXISTS: version '{name}' already exists")


class VersionNotFoundError(VersionManagerError):
    """Raised when a requested version is absent."""

    def __init__(self, name: str) -> None:
        super().__init__(f"E_VERSION_NOT_FOUND: version '{name}' not found")


class VersionManager:
    """Create, retrieve, list, and diff immutable prompt versions."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.versions_dir = project_root / ".prompt-lab" / "versions"

    def add_version(
        self,
        name: str,
        prompt_text: str,
        *,
        changed_from: str | None = None,
        changed_var: str = "prompt",
        change_note: str = "",
        author: str = "",
    ) -> Version:
        """Store a newly registered prompt without allowing overwrites."""
        version_path = self._path_for(name)
        if version_path.exists():
            raise VersionAlreadyExistsError(name)
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        content_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
        version = Version(
            id=name,
            content_hash=f"sha256:{content_hash}",
            prompt_text=prompt_text,
            timestamp=self._timestamp(),
            author=author,
            changed_from=changed_from,
            changed_var=changed_var,
            change_note=change_note,
        )
        version_path.write_text(
            json.dumps(asdict(version), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return version

    def get_version(self, name: str) -> Version:
        """Read a registered version by name."""
        version_path = self._path_for(name)
        if not version_path.is_file():
            raise VersionNotFoundError(name)
        try:
            data = json.loads(version_path.read_text(encoding="utf-8"))
            return Version(**data)
        except (OSError, json.JSONDecodeError, TypeError) as error:
            raise VersionManagerError(f"invalid version '{name}': {error}") from error

    def list_versions(self, limit: int = 50) -> list[Version]:
        """Return versions newest first, up to *limit* records."""
        if limit < 1 or not self.versions_dir.is_dir():
            return []
        versions = [self.get_version(path.stem) for path in self.versions_dir.glob("*.json")]
        return sorted(versions, key=lambda version: version.timestamp, reverse=True)[:limit]

    def diff(self, v1: str, v2: str) -> str:
        """Return a unified text diff from *v1* to *v2*."""
        before = self.get_version(v1)
        after = self.get_version(v2)
        return "".join(
            difflib.unified_diff(
                before.prompt_text.splitlines(keepends=True),
                after.prompt_text.splitlines(keepends=True),
                fromfile=v1,
                tofile=v2,
            )
        )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _path_for(self, name: str) -> Path:
        if not name or Path(name).name != name or name in {".", ".."}:
            raise ValueError("version name must be a single file name")
        return self.versions_dir / f"{name}.json"
