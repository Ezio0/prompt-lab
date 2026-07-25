import json
from pathlib import Path

from click.testing import CliRunner

from prompt_lab.cli import cli
from prompt_lab.core.models import ProviderResponse


class FakeProvider:
    def __init__(self, config):
        self.config = config

    async def call(self, prompt, **params):
        return ProviderResponse(content=f"output:{prompt}", prompt_tokens=10, completion_tokens=2, finish_reason="stop")


def invoke_in_project(runner, args):
    return runner.invoke(cli, args, catch_exceptions=False)


def test_init_command_creates_project_files(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = invoke_in_project(runner, ["init"])

        assert result.exit_code == 0
        assert Path("prompt-lab.yaml").is_file()


def test_add_version_log_and_diff_commands(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        invoke_in_project(runner, ["init"])
        Path("one.txt").write_text("first line\n", encoding="utf-8")
        Path("two.txt").write_text("second line\n", encoding="utf-8")

        assert invoke_in_project(runner, ["add", "version", "v1", "--file", "one.txt"]).exit_code == 0
        assert invoke_in_project(runner, ["add", "version", "v2", "--file", "two.txt"]).exit_code == 0
        assert "v2" in invoke_in_project(runner, ["log"]).output
        assert "+second line" in invoke_in_project(runner, ["diff", "v1", "v2"]).output


def test_add_case_and_cases_list_commands(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        invoke_in_project(runner, ["init"])
        Path("case.json").write_text(json.dumps({"input": {"topic": "books"}, "expected_output_note": "helpful"}))

        result = invoke_in_project(
            runner, ["add", "case", "case-1", "--file", "case.json", "--collection", "books", "--type", "ideal"]
        )

        assert result.exit_code == 0
        assert "case-1" in invoke_in_project(runner, ["cases", "list", "--collection", "books"]).output


def test_run_command_uses_run_engine_and_outputs_summary(tmp_path, monkeypatch):
    monkeypatch.setattr("prompt_lab.cli.Provider", FakeProvider)
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        invoke_in_project(runner, ["init"])
        Path("one.txt").write_text("base {topic}")
        Path("two.txt").write_text("candidate {topic}")
        Path("case.json").write_text(json.dumps({"input": {"topic": "books"}}))
        invoke_in_project(runner, ["add", "version", "v1", "--file", "one.txt"])
        invoke_in_project(runner, ["add", "version", "v2", "--file", "two.txt"])
        invoke_in_project(runner, ["add", "case", "case-1", "--file", "case.json", "--collection", "books", "--type", "ideal"])

        result = invoke_in_project(runner, ["run", "--baseline", "v1", "--candidate", "v2", "--dataset", "books"])

        assert result.exit_code == 0
        assert "Run ID:" in result.output
        assert list(Path(".prompt-lab/runs").glob("*/result.json"))


def test_compare_command_outputs_table_and_json(tmp_path, monkeypatch):
    monkeypatch.setattr("prompt_lab.cli.Provider", FakeProvider)
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        invoke_in_project(runner, ["init"])
        Path("one.txt").write_text("base")
        Path("two.txt").write_text("candidate")
        Path("case.json").write_text(json.dumps({"input": {}}))
        for args in (
            ["add", "version", "v1", "--file", "one.txt"],
            ["add", "version", "v2", "--file", "two.txt"],
            ["add", "case", "case-1", "--file", "case.json", "--collection", "books", "--type", "ideal"],
        ):
            assert invoke_in_project(runner, args).exit_code == 0
        run_output = invoke_in_project(runner, ["run", "--baseline", "v1", "--candidate", "v2", "--dataset", "books"]).output
        run_id = run_output.split("Run ID: ", 1)[1].splitlines()[0]

        assert "Summary" in invoke_in_project(runner, ["compare", run_id]).output
        assert '"run_id"' in invoke_in_project(runner, ["compare", run_id, "--format", "json"]).output
