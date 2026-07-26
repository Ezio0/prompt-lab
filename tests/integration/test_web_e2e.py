"""CUJ-5: Web API read-only browse — end-to-end via FastAPI TestClient."""

import json
from pathlib import Path

import pytest

fastapi_tc = pytest.importorskip("fastapi.testclient")


def _make_project(tmp_path: Path) -> Path:
    """Initialize a minimal prompt-lab project in *tmp_path*."""
    (tmp_path / ".prompt-lab" / "versions").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".prompt-lab" / "cases").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".prompt-lab" / "runs").mkdir(parents=True, exist_ok=True)
    config = {
        "provider": {
            "base_url": "https://example.test/v1",
            "api_key_env": "OPENAI_API_KEY",
            "model": "test-model",
            "default_params": {"max_tokens": 256, "temperature": 0.0},
        },
        "run": {"timeout_seconds": 10, "concurrency": 1},
    }
    import yaml

    (tmp_path / "prompt-lab.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    return tmp_path


def test_web_cuj5_version_browse(tmp_path, monkeypatch):
    """CUJ-5: create_app → GET /api/versions → GET /api/versions/{id} → GET diff."""
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    root = _make_project(tmp_path)

    from prompt_lab.core.version_manager import VersionManager
    from prompt_lab.web.server import create_app
    from fastapi.testclient import TestClient

    # Register two versions
    mgr = VersionManager(root)
    mgr.add_version("v1", "Recommend {topic}")
    mgr.add_version("v2", "Carefully recommend {topic}")

    app = create_app(root)
    client = TestClient(app)

    # Step 1: GET /api/versions
    resp = client.get("/api/versions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    ids = {item["id"] for item in data}
    assert ids == {"v1", "v2"}

    # Step 2: GET /api/versions/v2 (detail)
    resp = client.get("/api/versions/v2")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["id"] == "v2"
    assert "prompt_text" in detail
    assert "Carefully" in detail["prompt_text"]

    # Step 3: GET /api/versions/v1/v2/diff
    resp = client.get("/api/versions/v1/v2/diff")
    assert resp.status_code == 200
    diff_data = resp.json()
    assert "diff" in diff_data
    assert isinstance(diff_data["diff"], str)


def test_web_cuj5_run_browse(tmp_path, monkeypatch):
    """CUJ-5: create_app → GET /api/runs → GET /api/runs/{id}."""
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    root = _make_project(tmp_path)

    from prompt_lab.web.server import create_app
    from fastapi.testclient import TestClient

    # Create a fake run result
    run_dir = root / ".prompt-lab" / "runs" / "20260726T120000Z"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "result.json").write_text(json.dumps({
        "run_id": "20260726T120000Z",
        "baseline_version": "v1",
        "candidate_version": "v2",
        "dataset": "books",
        "provider_config": {},
        "timestamp": "2026-07-26T12:00:00Z",
        "cases": [{
            "case_id": "case-1",
            "baseline": {"output": "hello", "prompt_tokens": 10, "completion_tokens": 5, "latency_ms": 100, "finish_reason": "stop", "error": None},
            "candidate": {"output": "hi", "prompt_tokens": 8, "completion_tokens": 2, "latency_ms": 80, "finish_reason": "stop", "error": None},
            "evaluations": [],
        }],
        "summary": {
            "baseline": {"avg_prompt_tokens": 10, "avg_completion_tokens": 5, "avg_latency_ms": 100, "non_empty_rate": 1.0, "error_rate": 0.0},
            "candidate": {"avg_prompt_tokens": 8, "avg_completion_tokens": 2, "avg_latency_ms": 80, "non_empty_rate": 1.0, "error_rate": 0.0},
        },
    }), encoding="utf-8")

    app = create_app(root)
    client = TestClient(app)

    # Step 1: GET /api/runs
    resp = client.get("/api/runs")
    assert resp.status_code == 200
    runs = resp.json()
    assert len(runs) == 1
    assert runs[0]["run_id"] == "20260726T120000Z"
    assert runs[0]["baseline_version"] == "v1"

    # Step 2: GET /api/runs/{id}
    resp = client.get("/api/runs/20260726T120000Z")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["run_id"] == "20260726T120000Z"
    assert len(detail["cases"]) == 1

    # Step 3: GET /api/runs/nonexistent → 404
    resp = client.get("/api/runs/nonexistent")
    assert resp.status_code == 404


def test_web_config_no_api_key_leak(tmp_path, monkeypatch):
    """Ensure GET /api/config never returns the actual API key value."""
    monkeypatch.setenv("OPENAI_API_KEY", "super-secret-key-12345")
    root = _make_project(tmp_path)

    from prompt_lab.web.server import create_app
    from fastapi.testclient import TestClient

    app = create_app(root)
    client = TestClient(app)

    resp = client.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    # api_key_env name is fine
    assert body["provider"]["api_key_env"] == "OPENAI_API_KEY"
    # The actual key value must NOT appear
    assert "super-secret-key-12345" not in resp.text
