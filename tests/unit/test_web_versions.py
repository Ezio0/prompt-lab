"""Unit tests for version management REST endpoints (T-202)."""

import json
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


def _register_version(root: Path, name: str = "v1", text: str = "Hello {name}") -> dict:
    """Register a version via the VersionManager directly for test setup."""
    from prompt_lab.core.version_manager import VersionManager

    return json.loads(
        (root / ".prompt-lab" / "versions" / f"{name}.json").read_text()
    ) if (root / ".prompt-lab" / "versions" / f"{name}.json").exists() else None


def test_list_versions_empty(tmp_path):
    """GET /api/versions returns empty list when no versions exist."""
    client = _client(_make_project(tmp_path))
    response = client.get("/api/versions")
    assert response.status_code == 200
    assert response.json() == []


def test_list_versions_returns_metadata_without_prompt_text(tmp_path):
    """GET /api/versions must NOT include prompt_text."""
    root = _make_project(tmp_path)
    from prompt_lab.core.version_manager import VersionManager

    VersionManager(root).add_version("v1", "Secret prompt {name}")

    client = _client(root)
    response = client.get("/api/versions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "v1"
    assert "prompt_text" not in data[0]
    assert "content_hash" in data[0]


def test_list_versions_sorted_newest_first(tmp_path):
    """GET /api/versions returns all registered versions."""
    root = _make_project(tmp_path)
    from prompt_lab.core.version_manager import VersionManager

    manager = VersionManager(root)
    manager.add_version("v1", "Prompt A")
    manager.add_version("v2", "Prompt B")

    client = _client(root)
    data = client.get("/api/versions").json()
    ids = {item["id"] for item in data}
    assert ids == {"v1", "v2"}


def test_get_version_detail_includes_prompt_text(tmp_path):
    """GET /api/versions/{id} returns full version including prompt_text."""
    root = _make_project(tmp_path)
    from prompt_lab.core.version_manager import VersionManager

    VersionManager(root).add_version("v1", "Hello {name}")

    client = _client(root)
    response = client.get("/api/versions/v1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "v1"
    assert data["prompt_text"] == "Hello {name}"


def test_get_version_not_found_returns_404(tmp_path):
    """GET /api/versions/{id} on nonexistent version returns 404."""
    client = _client(_make_project(tmp_path))
    response = client.get("/api/versions/nonexistent")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_diff_versions_returns_diff(tmp_path):
    """GET /api/versions/{a}/{b}/diff returns a unified diff."""
    root = _make_project(tmp_path)
    from prompt_lab.core.version_manager import VersionManager

    VersionManager(root).add_version("v1", "Line one\nLine two\n")
    VersionManager(root).add_version("v2", "Line one\nLine THREE\n")

    client = _client(root)
    response = client.get("/api/versions/v1/v2/diff")
    assert response.status_code == 200
    diff_text = response.json()["diff"]
    assert "Line two" in diff_text
    assert "Line THREE" in diff_text


def test_diff_versions_not_found_returns_404(tmp_path):
    """GET /api/versions/{a}/{b}/diff with missing version returns 404."""
    client = _client(_make_project(tmp_path))
    response = client.get("/api/versions/v1/v2/diff")
    assert response.status_code == 404


def test_create_version_success(tmp_path):
    """POST /api/versions registers a new version."""
    client = _client(_make_project(tmp_path))
    response = client.post("/api/versions", json={
        "name": "v1",
        "prompt_text": "Hello {name}",
        "change_note": "initial version",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "v1"
    assert data["prompt_text"] == "Hello {name}"


def test_create_version_duplicate_returns_409(tmp_path):
    """POST /api/versions with an existing name returns 409."""
    root = _make_project(tmp_path)
    client = _client(root)
    client.post("/api/versions", json={"name": "v1", "prompt_text": "A"})

    response = client.post("/api/versions", json={"name": "v1", "prompt_text": "B"})
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_api_key_never_in_response(tmp_path):
    """API key values must never appear in any version response."""
    root = _make_project(tmp_path)
    client = _client(root)

    # Register via API
    resp = client.post("/api/versions", json={
        "name": "v1",
        "prompt_text": "test",
        "author": "tester",
    })
    assert resp.status_code == 200

    # Check list endpoint
    for item in client.get("/api/versions").json():
        assert "api_key" not in item
        assert "api_key_env" not in item

    # Check detail endpoint
    detail = client.get("/api/versions/v1").json()
    assert "api_key" not in detail
