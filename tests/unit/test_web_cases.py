"""Unit tests for case management REST endpoints (T-203 cases part)."""

from pathlib import Path

from fastapi.testclient import TestClient

from prompt_lab.web.server import create_app


def _make_project(tmp_path: Path) -> Path:
    (tmp_path / ".prompt-lab" / "versions").mkdir(parents=True)
    (tmp_path / ".prompt-lab" / "cases").mkdir(parents=True)
    (tmp_path / ".prompt-lab" / "runs").mkdir(parents=True)
    (tmp_path / "prompt-lab.yaml").write_text(
        "provider:\n"
        "  base_url: https://api.openai.com/v1\n"
        "  api_key_env: OPENAI_API_KEY\n"
        "  model: gpt-4o-mini\n"
        "  default_params:\n"
        "    max_tokens: 1024\n"
        "run:\n"
        "  timeout_seconds: 60\n"
        "  concurrency: 1\n",
        encoding="utf-8",
    )
    return tmp_path


def _client(root: Path) -> TestClient:
    return TestClient(create_app(root))


def _add_case(root: Path, case_id: str, collection: str, case_type: str = "ideal"):
    from prompt_lab.core.case_manager import CaseManager
    from prompt_lab.core.models import Case

    case = Case(
        id=case_id,
        type=case_type,
        input={"name": "World"},
        collection=collection,
        expected_output="Hello World",
    )
    CaseManager(root).add_case(case)


def test_list_cases_empty(tmp_path):
    """GET /api/cases returns empty list when no cases exist."""
    client = _client(_make_project(tmp_path))
    response = client.get("/api/cases")
    assert response.status_code == 200
    assert response.json() == []


def test_list_cases_all(tmp_path):
    """GET /api/cases returns all cases across collections."""
    root = _make_project(tmp_path)
    _add_case(root, "case1", "col_a")
    _add_case(root, "case2", "col_b")

    client = _client(root)
    response = client.get("/api/cases")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    ids = {item["id"] for item in data}
    assert ids == {"case1", "case2"}


def test_list_cases_filtered_by_collection(tmp_path):
    """GET /api/cases?collection=X returns only cases in that collection."""
    root = _make_project(tmp_path)
    _add_case(root, "case1", "col_a")
    _add_case(root, "case2", "col_b")

    client = _client(root)
    response = client.get("/api/cases", params={"collection": "col_a"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "case1"


def test_list_cases_filtered_by_type(tmp_path):
    """GET /api/cases?type=ideal returns only ideal-type cases."""
    root = _make_project(tmp_path)
    _add_case(root, "case1", "col_a", "ideal")
    _add_case(root, "case2", "col_a", "bad-case")

    client = _client(root)
    response = client.get("/api/cases", params={"collection": "col_a", "type": "ideal"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "case1"
    assert data[0]["type"] == "ideal"


def test_list_cases_invalid_type_returns_400(tmp_path):
    """GET /api/cases?type=invalid returns 400."""
    client = _client(_make_project(tmp_path))
    response = client.get("/api/cases", params={"type": "invalid"})
    assert response.status_code == 400


def test_list_cases_nonexistent_collection_returns_empty(tmp_path):
    """GET /api/cases?collection=nonexistent returns empty list."""
    client = _client(_make_project(tmp_path))
    response = client.get("/api/cases", params={"collection": "nonexistent"})
    assert response.status_code == 200
    assert response.json() == []


def test_case_response_has_expected_fields(tmp_path):
    """Case response includes all expected fields."""
    root = _make_project(tmp_path)
    _add_case(root, "case1", "col_a", "ideal")

    client = _client(root)
    data = client.get("/api/cases").json()[0]
    assert data["id"] == "case1"
    assert data["type"] == "ideal"
    assert data["collection"] == "col_a"
    assert data["input"] == {"name": "World"}
    assert data["expected_output"] == "Hello World"
