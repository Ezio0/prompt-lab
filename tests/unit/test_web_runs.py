"""Unit tests for run management REST endpoints (T-203 runs part)."""

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


def _create_run(root: Path, run_id: str = "20260101T000000Z") -> dict:
    """Write a fake result.json directly to disk for test setup."""
    run_dir = root / ".prompt-lab" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "run_id": run_id,
        "baseline_version": "v1",
        "candidate_version": "v2",
        "dataset": "test-col",
        "provider_config": {"model": "gpt-4o-mini"},
        "timestamp": "2026-01-01T00:00:00Z",
        "cases": [
            {
                "case_id": "case1",
                "baseline": {
                    "output": "baseline output",
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "latency_ms": 100.0,
                    "finish_reason": "stop",
                    "error": None,
                },
                "candidate": {
                    "output": "candidate output",
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "latency_ms": 120.0,
                    "finish_reason": "stop",
                    "error": None,
                },
            }
        ],
        "summary": {
            "baseline": {"avg_prompt_tokens": 10.0, "avg_latency_ms": 100.0, "non_empty_rate": 1.0, "error_rate": 0.0},
            "candidate": {"avg_prompt_tokens": 10.0, "avg_latency_ms": 120.0, "non_empty_rate": 1.0, "error_rate": 0.0},
        },
    }
    (run_dir / "result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


def test_list_runs_empty(tmp_path):
    """GET /api/runs returns empty list when no runs exist."""
    client = _client(_make_project(tmp_path))
    response = client.get("/api/runs")
    assert response.status_code == 200
    assert response.json() == []


def test_list_runs_returns_summaries(tmp_path):
    """GET /api/runs returns summary info for each run."""
    root = _make_project(tmp_path)
    _create_run(root, "20260101T000000Z")
    _create_run(root, "20260102T000000Z")

    client = _client(root)
    response = client.get("/api/runs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Newest first
    assert data[0]["run_id"] == "20260102T000000Z"
    assert data[0]["total_cases"] == 1
    assert data[0]["baseline_version"] == "v1"
    assert "cases" not in data[0]  # summary only, no case details


def test_get_run_detail(tmp_path):
    """GET /api/runs/{id} returns the full result.json data."""
    root = _make_project(tmp_path)
    _create_run(root, "20260101T000000Z")

    client = _client(root)
    response = client.get("/api/runs/20260101T000000Z")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == "20260101T000000Z"
    assert len(data["cases"]) == 1
    assert data["cases"][0]["case_id"] == "case1"


def test_get_run_not_found_returns_404(tmp_path):
    """GET /api/runs/{id} on nonexistent run returns 404."""
    client = _client(_make_project(tmp_path))
    response = client.get("/api/runs/nonexistent")
    assert response.status_code == 404


def test_trigger_run_success(tmp_path, monkeypatch):
    """POST /api/runs triggers a run and returns the result."""
    root = _make_project(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    # Register two versions
    from prompt_lab.core.version_manager import VersionManager
    manager = VersionManager(root)
    manager.add_version("v1", "Hello {name}")
    manager.add_version("v2", "Hi {name}")

    # Add a case
    from prompt_lab.core.case_manager import CaseManager
    from prompt_lab.core.models import Case
    CaseManager(root).add_case(Case(
        id="c1", type="ideal", input={"name": "World"}, collection="col1",
    ))

    # Monkeypatch the Provider so no real HTTP call is made
    from prompt_lab.core.models import ProviderResponse
    from prompt_lab.web.routes import runs as runs_module

    class FakeProvider:
        def __init__(self, config):
            self.config = config

        async def call(self, prompt, **params):
            return ProviderResponse(content="result", prompt_tokens=5, completion_tokens=3, finish_reason="stop")

    original_provider = runs_module.Provider
    runs_module.Provider = FakeProvider
    try:
        client = _client(root)
        response = client.post("/api/runs", json={
            "baseline": "v1",
            "candidate": "v2",
            "dataset": "col1",
        })
    finally:
        runs_module.Provider = original_provider

    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert data["baseline_version"] == "v1"
    assert data["candidate_version"] == "v2"
    assert len(data["cases"]) == 1


def test_trigger_run_dataset_not_found_returns_400(tmp_path, monkeypatch):
    """POST /api/runs with nonexistent dataset returns 400."""
    root = _make_project(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    from prompt_lab.core.version_manager import VersionManager
    manager = VersionManager(root)
    manager.add_version("v1", "Hello {name}")
    manager.add_version("v2", "Hi {name}")

    client = _client(root)
    response = client.post("/api/runs", json={
        "baseline": "v1",
        "candidate": "v2",
        "dataset": "nonexistent",
    })
    assert response.status_code == 400


def test_trigger_run_version_not_found_returns_404(tmp_path, monkeypatch):
    """POST /api/runs with nonexistent version returns 404."""
    root = _make_project(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    client = _client(root)
    response = client.post("/api/runs", json={
        "baseline": "v1",
        "candidate": "v2",
        "dataset": "col1",
    })
    assert response.status_code == 404


def test_api_key_never_in_run_response(tmp_path):
    """API key values must never appear in run responses."""
    root = _make_project(tmp_path)
    _create_run(root, "20260101T000000Z")

    client = _client(root)
    # Run detail
    detail = client.get("/api/runs/20260101T000000Z").json()
    detail_str = json.dumps(detail)
    assert "api_key" not in detail_str.lower() or "api_key_env" in detail_str  # provider_config doesn't have key
    assert "test-key" not in detail_str

    # Run list
    for item in client.get("/api/runs").json():
        assert "api_key" not in item
