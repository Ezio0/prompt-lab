"""Command-line interface for Prompt Lab."""

from pathlib import Path

import click
import yaml


INITIAL_CONFIG = {
    "provider": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-4o-mini",
        "default_params": {
            "max_tokens": 1024,
            "temperature": 0.0,
            "thinking": "disabled",
        },
    },
    "run": {"timeout_seconds": 60, "concurrency": 1},
}


@click.group()
def cli() -> None:
    """Manage prompt versions and run A/B comparisons."""


@cli.command()
@click.option("--name", default=None, help="Project name (defaults to the directory name).")
def init(name: str | None) -> None:
    """Initialize Prompt Lab in the current directory."""
    project_root = Path.cwd()
    state_dir = project_root / ".prompt-lab"
    for directory in (state_dir / "versions", state_dir / "cases", state_dir / "runs"):
        directory.mkdir(parents=True, exist_ok=True)

    config_path = project_root / "prompt-lab.yaml"
    if not config_path.exists():
        config_path.write_text(yaml.safe_dump(INITIAL_CONFIG, sort_keys=False), encoding="utf-8")

    gitignore_path = project_root / ".gitignore"
    ignore_entry = ".prompt-lab/runs/\n"
    if not gitignore_path.exists():
        gitignore_path.write_text(ignore_entry, encoding="utf-8")
    elif ignore_entry not in gitignore_path.read_text(encoding="utf-8"):
        with gitignore_path.open("a", encoding="utf-8") as gitignore:
            if gitignore.tell():
                gitignore.write("\n")
            gitignore.write(ignore_entry)

    click.echo("Created .prompt-lab/")
    click.echo("Created prompt-lab.yaml")
    click.echo("Created .gitignore")


if __name__ == "__main__":
    cli()
