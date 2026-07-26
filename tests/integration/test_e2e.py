import json
from pathlib import Path

from click.testing import CliRunner

from prompt_lab.cli import cli
from prompt_lab.core.models import ProviderResponse


class FakeProvider:
    def __init__(self, config):
        self.config = config

    async def call(self, prompt, **params):
        return ProviderResponse(content=f"fake output for {prompt}", prompt_tokens=20, completion_tokens=4, finish_reason="stop")


def test_cuj1_full_chain(tmp_path, monkeypatch):
    monkeypatch.setattr("prompt_lab.cli.Provider", FakeProvider)
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        assert runner.invoke(cli, ["init"], catch_exceptions=False).exit_code == 0
        Path("v1.txt").write_text("Recommend {topic}")
        Path("v2.txt").write_text("Carefully recommend {topic}")
        for name, filename in (("v1", "v1.txt"), ("v2", "v2.txt")):
            assert runner.invoke(cli, ["add", "version", name, "--file", filename], catch_exceptions=False).exit_code == 0
        for number in range(3):
            Path(f"case-{number}.json").write_text(json.dumps({"input": {"topic": f"topic-{number}"}}))
            assert runner.invoke(
                cli,
                ["add", "case", f"case-{number}", "--file", f"case-{number}.json", "--collection", "books", "--type", "ideal"],
                catch_exceptions=False,
            ).exit_code == 0

        run = runner.invoke(cli, ["run", "--baseline", "v1", "--candidate", "v2", "--dataset", "books"], catch_exceptions=False)
        assert run.exit_code == 0
        run_id = run.output.split("Run ID: ", 1)[1].splitlines()[0]
        result_path = Path(".prompt-lab/runs") / run_id / "result.json"
        assert len(json.loads(result_path.read_text())["cases"]) == 3
        assert "Summary" in runner.invoke(cli, ["compare", run_id], catch_exceptions=False).output


def test_cuj2_bad_case_import_and_validate(tmp_path, monkeypatch):
    monkeypatch.setattr("prompt_lab.cli.Provider", FakeProvider)
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        assert runner.invoke(cli, ["init"], catch_exceptions=False).exit_code == 0
        Path("old.txt").write_text("Old {topic}")
        Path("new.txt").write_text("New {topic}")
        for name, filename in (("v1", "old.txt"), ("v2", "new.txt")):
            assert runner.invoke(cli, ["add", "version", name, "--file", filename], catch_exceptions=False).exit_code == 0
        Path("bad.json").write_text(json.dumps([{"id": "bad-1", "type": "bad-case", "input": {"topic": "hooks"}, "issue": "marketing"}]))
        assert runner.invoke(cli, ["cases", "import", "bad.json", "--collection", "bad"], catch_exceptions=False).exit_code == 0
        run = runner.invoke(cli, ["run", "--baseline", "v1", "--candidate", "v2", "--dataset", "bad"], catch_exceptions=False)
        assert run.exit_code == 0
        assert '"summary"' in runner.invoke(cli, ["compare", run.output.split("Run ID: ", 1)[1].splitlines()[0], "--format", "json"], catch_exceptions=False).output


def test_cuj4_eval_with_mock_evaluator(tmp_path, monkeypatch):
    """CUJ-4: init → add version × 2 → add case → run (with mock eval) → compare."""
    from prompt_lab.core.models import EvalResult

    class MockEvaluator:
        """Fake evaluator returning fixed scores."""
        def evaluate(self, case, baseline_output, candidate_output):
            return [
                EvalResult(metric_name="faithfulness", score=0.85, reason="good baseline", status="pass"),
                EvalResult(metric_name="faithfulness", score=0.72, reason="ok candidate", status="pass"),
            ]

    def patched_run_engine_init(self, provider, config, *, project_root=None, evaluator=None):
        self.provider = provider
        self.config = config
        self.project_root = project_root or Path.cwd()
        self.evaluator = evaluator if evaluator is not None else MockEvaluator()

    monkeypatch.setattr("prompt_lab.core.run_engine.RunEngine.__init__", patched_run_engine_init)
    monkeypatch.setattr("prompt_lab.cli.Provider", FakeProvider)
    # Patch deepeval availability check + CustomModel/Evaluator imports in eval_model/evaluator
    import prompt_lab.core.eval_model as em
    monkeypatch.setattr(em, "_DEEPEVAL_AVAILABLE", True)
    monkeypatch.setattr(em, "is_deepeval_available", lambda: True)
    monkeypatch.setattr(em, "CustomModel", lambda **kw: MockEvaluator())
    import prompt_lab.core.evaluator as ev
    monkeypatch.setattr(ev, "Evaluator", lambda *a, **kw: MockEvaluator())
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        assert runner.invoke(cli, ["init"], catch_exceptions=False).exit_code == 0

        # Add eval config to yaml
        import yaml as yaml_mod
        config_path = Path("prompt-lab.yaml")
        config_data = yaml_mod.safe_load(config_path.read_text())
        config_data["eval"] = {
            "enabled": True,
            "metrics": [{"name": "faithfulness"}],
            "model": "test-model",
            "api_key_env": "OPENAI_API_KEY",
        }
        config_path.write_text(yaml_mod.safe_dump(config_data))

        Path("v1.txt").write_text("Recommend {topic}")
        Path("v2.txt").write_text("Carefully recommend {topic}")
        for name, filename in (("v1", "v1.txt"), ("v2", "v2.txt")):
            assert runner.invoke(cli, ["add", "version", name, "--file", filename], catch_exceptions=False).exit_code == 0

        Path("case-0.json").write_text(json.dumps({
            "input": {"topic": "books"},
            "expected_output": "A good book recommendation.",
        }))
        assert runner.invoke(cli, ["add", "case", "case-0", "--file", "case-0.json", "--collection", "books", "--type", "ideal"], catch_exceptions=False).exit_code == 0

        # Run with eval (the patched RunEngine will auto-inject evaluator)
        run = runner.invoke(cli, ["run", "--baseline", "v1", "--candidate", "v2", "--dataset", "books", "--eval"], catch_exceptions=False)
        assert run.exit_code == 0
        run_id = run.output.split("Run ID: ", 1)[1].splitlines()[0]

        result_path = Path(".prompt-lab/runs") / run_id / "result.json"
        result = json.loads(result_path.read_text())
        assert len(result["cases"][0]["evaluations"]) > 0
        assert "eval_summary" in result["summary"]

        compare_output = runner.invoke(cli, ["compare", run_id, "--eval-only"], catch_exceptions=False).output
        assert "Eval Summary" in compare_output
