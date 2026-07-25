"""Collection-based local case storage."""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from prompt_lab.core.models import Case


class CaseManagerError(ValueError):
    """Base error for case storage operations."""


class InvalidCaseTypeError(CaseManagerError):
    """Raised when a case type is outside the v1 taxonomy."""

    def __init__(self, case_type: str) -> None:
        super().__init__(f"case type must be ideal or bad-case, got '{case_type}'")


class CaseManager:
    """Store and retrieve cases grouped by collection."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.cases_dir = project_root / ".prompt-lab" / "cases"

    def add_case(self, case: Case) -> None:
        """Persist a case in its declared collection."""
        self._validate_case(case)
        collection_dir = self._collection_dir(case.collection)
        collection_dir.mkdir(parents=True, exist_ok=True)
        (collection_dir / f"{case.id}.json").write_text(
            json.dumps(asdict(case), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def get_cases(self, collection: str, case_type: str | None = None) -> list[Case]:
        """Return cases in *collection*, optionally filtered by type."""
        if case_type is not None:
            self._validate_type(case_type)
        collection_dir = self._collection_dir(collection)
        if not collection_dir.is_dir():
            return []
        cases = [self._read_case(path) for path in sorted(collection_dir.glob("*.json"))]
        if case_type is not None:
            return [case for case in cases if case.type == case_type]
        return cases

    def import_cases(self, file_path: Path, collection: str) -> int:
        """Import an array of case objects, assigning them to *collection*."""
        try:
            raw = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise CaseManagerError(f"could not import cases: {error}") from error
        if not isinstance(raw, list):
            raise CaseManagerError("import file must contain a JSON array")

        cases = [self._case_from_mapping(item, collection) for item in raw]
        for case in cases:
            self.add_case(case)
        return len(cases)

    def _read_case(self, path: Path) -> Case:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return self._case_from_mapping(raw, collection=None)
        except (OSError, json.JSONDecodeError, TypeError, KeyError) as error:
            raise CaseManagerError(f"invalid case file '{path.name}': {error}") from error

    def _case_from_mapping(self, raw: Any, collection: str | None) -> Case:
        if not isinstance(raw, dict):
            raise CaseManagerError("case must be a JSON object")
        values = dict(raw)
        if collection is not None:
            values["collection"] = collection
        try:
            case = Case(
                id=values["id"],
                type=values["type"],
                input=values["input"],
                collection=values["collection"],
                expected_output=values.get("expected_output"),
                expected_output_note=values.get("expected_output_note", ""),
                actual_output=values.get("actual_output"),
                issue=values.get("issue", ""),
            )
        except KeyError as error:
            raise CaseManagerError(f"missing case field '{error.args[0]}'") from error
        self._validate_case(case)
        return case

    def _validate_case(self, case: Case) -> None:
        self._validate_type(case.type)
        if not case.id or Path(case.id).name != case.id:
            raise CaseManagerError("case id must be a single file name")
        if not isinstance(case.input, dict):
            raise CaseManagerError("case input must be an object")
        self._collection_dir(case.collection)

    @staticmethod
    def _validate_type(case_type: str) -> None:
        if case_type not in {"ideal", "bad-case"}:
            raise InvalidCaseTypeError(case_type)

    def _collection_dir(self, collection: str) -> Path:
        if not collection or Path(collection).name != collection or collection in {".", ".."}:
            raise CaseManagerError("collection must be a single directory name")
        return self.cases_dir / collection
