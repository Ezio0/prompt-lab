"""Unit tests for the FastAPI app scaffold (T-201)."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from prompt_lab.web.server import create_app


def _make_project(tmp_path: Path) -> Path:
    """Create a minimal Prompt Lab project in *tmp_path*."""
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
        "    temperature: 0.0\n"
        "run:\n"
        "  timeout_seconds: 60\n"
        "  concurrency: 1\n",
        encoding="utf-8",
    )
    return tmp_path


def test_create_app_returns_fastapi_instance(tmp_path):
    """create_app must return a FastAPI instance."""
    app = create_app(_make_project(tmp_path))
    assert isinstance(app, FastAPI)


def test_create_app_has_project_root(tmp_path):
    """The app must store the project root on app.state."""
    root = _make_project(tmp_path)
    app = create_app(root)
    assert app.state.project_root == root


def test_health_endpoint(tmp_path):
    """GET /api/health returns 200 and status ok."""
    app = create_app(_make_project(tmp_path))
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_access_log_written(tmp_path):
    """The access log middleware writes to .prompt-lab/web.log."""
    root = _make_project(tmp_path)
    app = create_app(root)
    client = TestClient(app)
    client.get("/api/health")
    log_file = root / ".prompt-lab" / "web.log"
    assert log_file.is_file()
    content = log_file.read_text(encoding="utf-8")
    assert "/api/health" in content
    assert "GET" in content


def test_api_versions_route_registered(tmp_path):
    """The /api/versions route must be registered."""
    app = create_app(_make_project(tmp_path))
    client = TestClient(app)
    response = client.get("/api/versions")
    assert response.status_code == 200
    assert response.json() == []


def test_api_cases_route_registered(tmp_path):
    """The /api/cases route must be registered."""
    app = create_app(_make_project(tmp_path))
    client = TestClient(app)
    response = client.get("/api/cases")
    assert response.status_code == 200
    assert response.json() == []


def test_api_runs_route_registered(tmp_path):
    """The /api/runs route must be registered."""
    app = create_app(_make_project(tmp_path))
    client = TestClient(app)
    response = client.get("/api/runs")
    assert response.status_code == 200
    assert response.json() == []


def test_api_config_route_registered(tmp_path, monkeypatch):
    """The /api/config route must be registered."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    app = create_app(_make_project(tmp_path))
    client = TestClient(app)
    response = client.get("/api/config")
    assert response.status_code == 200


def test_serve_command_in_cli():
    """The serve command must exist in the CLI."""
    from prompt_lab.cli import cli
    assert "serve" in cli.commands


def test_serve_command_help():
    """serve command help shows expected options."""
    from click.testing import CliRunner
    from prompt_lab.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["serve", "--help"])
    assert result.exit_code == 0
    assert "--port" in result.output
    assert "--host" in result.output


# ---- T-204: Static files hosting tests ----


def test_frontend_not_built_returns_hint(tmp_path):
    """When no frontend build exists, GET / returns a JSON hint."""
    root = _make_project(tmp_path)
    app = create_app(root)
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data or "detail" in data


def test_static_file_served_from_dist(tmp_path):
    """When dist/ exists, static files are served."""
    root = _make_project(tmp_path)
    dist_dir = root / "web" / "frontend" / "dist"
    dist_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<html><body>SPA</body></html>", encoding="utf-8")

    app = create_app(root)
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "SPA" in response.text


def test_spa_fallback_returns_index_html(tmp_path):
    """Non-/api/ paths fall back to index.html for SPA routing."""
    root = _make_project(tmp_path)
    dist_dir = root / "web" / "frontend" / "dist"
    dist_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<html><body>SPA</body></html>", encoding="utf-8")

    app = create_app(root)
    client = TestClient(app)
    # A path that doesn't exist as a file should still return index.html
    response = client.get("/versions/v1")
    assert response.status_code == 200
    assert "SPA" in response.text


def test_api_routes_not_intercepted_by_spa(tmp_path):
    """API routes must return JSON, not be intercepted by SPA fallback."""
    root = _make_project(tmp_path)
    dist_dir = root / "web" / "frontend" / "dist"
    dist_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<html>SPA</html>", encoding="utf-8")

    app = create_app(root)
    client = TestClient(app)
    # Non-existent API endpoint should return 404 JSON, not index.html
    response = client.get("/api/nonexistent")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/json"


def test_static_asset_served(tmp_path):
    """Static assets in dist/ are served directly."""
    root = _make_project(tmp_path)
    dist_dir = root / "web" / "frontend" / "dist"
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<html>SPA</html>", encoding="utf-8")
    (assets_dir / "app.js").write_text("console.log('hello');", encoding="utf-8")

    app = create_app(root)
    client = TestClient(app)
    response = client.get("/assets/app.js")
    assert response.status_code == 200
    assert "console.log" in response.text
