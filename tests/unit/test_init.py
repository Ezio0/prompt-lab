from click.testing import CliRunner
from pathlib import Path

from prompt_lab.cli import cli


def test_init_creates_project_files(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["init"], catch_exceptions=False)

        assert result.exit_code == 0
        project_root = Path.cwd()
        assert (project_root / ".prompt-lab").is_dir()
        assert (project_root / ".prompt-lab" / "versions").is_dir()
        assert (project_root / ".prompt-lab" / "cases").is_dir()
        assert (project_root / ".prompt-lab" / "runs").is_dir()
        assert (project_root / "prompt-lab.yaml").is_file()
        assert (project_root / ".gitignore").is_file()
