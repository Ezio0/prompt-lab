import json

import pytest

from prompt_lab.core.case_manager import CaseManager, InvalidCaseTypeError
from prompt_lab.core.models import Case


def make_case(case_id: str = "case-1", case_type: str = "ideal") -> Case:
    return Case(
        id=case_id,
        type=case_type,
        input={"topic": "testing"},
        collection="books",
        expected_output_note="useful result",
    )


def test_add_case_writes_json_under_collection(tmp_path):
    manager = CaseManager(tmp_path)

    manager.add_case(make_case())

    stored = tmp_path / ".prompt-lab" / "cases" / "books" / "case-1.json"
    assert stored.is_file()
    assert json.loads(stored.read_text(encoding="utf-8"))["input"] == {"topic": "testing"}


def test_get_cases_reads_collection(tmp_path):
    manager = CaseManager(tmp_path)
    manager.add_case(make_case("case-1"))
    manager.add_case(make_case("case-2"))

    assert [case.id for case in manager.get_cases("books")] == ["case-1", "case-2"]


def test_get_cases_filters_by_type(tmp_path):
    manager = CaseManager(tmp_path)
    manager.add_case(make_case("ideal", "ideal"))
    manager.add_case(make_case("bad", "bad-case"))

    assert [case.id for case in manager.get_cases("books", "bad-case")] == ["bad"]


def test_import_cases_imports_json_array_into_collection(tmp_path):
    import_path = tmp_path / "cases.json"
    import_path.write_text(
        json.dumps(
            [
                {"id": "one", "type": "ideal", "input": {"x": 1}},
                {"id": "two", "type": "bad-case", "input": {"x": 2}, "issue": "bad"},
            ]
        ),
        encoding="utf-8",
    )

    count = CaseManager(tmp_path).import_cases(import_path, "imported")

    assert count == 2
    assert [case.id for case in CaseManager(tmp_path).get_cases("imported")] == ["one", "two"]


def test_invalid_case_type_is_rejected(tmp_path):
    invalid_case = make_case(case_type="unknown")

    with pytest.raises(InvalidCaseTypeError, match="ideal or bad-case"):
        CaseManager(tmp_path).add_case(invalid_case)
