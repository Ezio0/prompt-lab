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
