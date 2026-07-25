"""Command-line interface for Prompt Lab."""

import asyncio
import json
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table
import yaml

from prompt_lab.core.case_manager import CaseManager, CaseManagerError
from prompt_lab.core.config import Config, ConfigError
from prompt_lab.core.models import Case, CaseResult, ExecutionResult, RunResult
from prompt_lab.core.provider import Provider
from prompt_lab.core.report import ReportBuilder
from prompt_lab.core.run_engine import RunEngine
from prompt_lab.core.version_manager import VersionManager, VersionManagerError


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


@cli.group("add")
def add() -> None:
    """Register a prompt version or test case."""


@add.command("version")
@click.argument("name")
@click.option("--file", "file_path", type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True)
@click.option("--changed-from", default=None)
@click.option("--changed-var", type=click.Choice(["prompt", "model", "params", "data"]), default="prompt")
@click.option("--note", default="")
@click.option("--author", default="")
def add_version(
    name: str,
    file_path: Path,
    changed_from: str | None,
    changed_var: str,
    note: str,
    author: str,
) -> None:
    """Register an immutable prompt VERSION from FILE."""
    try:
        version = VersionManager(Path.cwd()).add_version(
            name,
            file_path.read_text(encoding="utf-8"),
            changed_from=changed_from,
            changed_var=changed_var,
            change_note=note,
            author=author,
        )
    except (OSError, VersionManagerError, ValueError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Registered version {version.id} ({version.content_hash})")


@add.command("case")
@click.argument("case_id")
@click.option("--file", "file_path", type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True)
@click.option("--collection", required=True)
@click.option("--type", "case_type", type=click.Choice(["ideal", "bad-case"]), required=True)
def add_case(case_id: str, file_path: Path, collection: str, case_type: str) -> None:
    """Add a case from a JSON FILE."""
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("case file must contain a JSON object")
        case = Case(
            id=case_id,
            type=case_type,
            input=data["input"],
            collection=collection,
            expected_output=data.get("expected_output"),
            expected_output_note=data.get("expected_output_note", data.get("note", "")),
            actual_output=data.get("actual_output"),
            issue=data.get("issue", ""),
        )
        CaseManager(Path.cwd()).add_case(case)
    except (OSError, json.JSONDecodeError, KeyError, ValueError, CaseManagerError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Added case {case_id} to {collection}")


@cli.command()
@click.option("--limit", default=50, type=click.IntRange(min=1))
def log(limit: int) -> None:
    """List registered prompt versions."""
    versions = VersionManager(Path.cwd()).list_versions(limit)
    table = Table(title="Prompt versions")
    for column in ("Version", "Date", "Author", "Changed var", "Note"):
        table.add_column(column)
    for version in versions:
        table.add_row(version.id, version.timestamp, version.author or "-", version.changed_var, version.change_note or "-")
    click.echo(_render_table(table))


@cli.command()
@click.argument("version_a")
@click.argument("version_b")
def diff(version_a: str, version_b: str) -> None:
    """Show the unified diff from VERSION_A to VERSION_B."""
    try:
        output = VersionManager(Path.cwd()).diff(version_a, version_b)
    except VersionManagerError as error:
        raise click.ClickException(str(error)) from error
    click.echo(output, nl=False)


@cli.group()
def cases() -> None:
    """Manage prompt test cases."""


@cases.command("list")
@click.option("--collection", default=None)
@click.option("--type", "case_type", type=click.Choice(["ideal", "bad-case"]), default=None)
def list_cases(collection: str | None, case_type: str | None) -> None:
    """List cases, optionally limited to a collection or type."""
    manager = CaseManager(Path.cwd())
    collections = [collection] if collection else sorted(
        path.name for path in manager.cases_dir.iterdir() if path.is_dir()
    ) if manager.cases_dir.is_dir() else []
    table = Table(title="Prompt cases")
    for column in ("ID", "Type", "Collection", "Note"):
        table.add_column(column)
    try:
        for item in collections:
            for case in manager.get_cases(item, case_type):
                table.add_row(case.id, case.type, case.collection, case.expected_output_note or case.issue or "-")
    except CaseManagerError as error:
        raise click.ClickException(str(error)) from error
    click.echo(_render_table(table))


@cases.command("import")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--collection", required=True)
def import_cases(file_path: Path, collection: str) -> None:
    """Import a JSON array of cases into COLLECTION."""
    try:
        count = CaseManager(Path.cwd()).import_cases(file_path, collection)
    except CaseManagerError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Imported {count} cases into {collection}")


@cli.command()
@click.option("--baseline", required=True)
@click.option("--candidate", required=True)
@click.option("--dataset", required=True)
@click.option("--model", default=None)
@click.option("--max-tokens", type=int, default=None)
@click.option("--thinking", type=click.Choice(["enabled", "disabled"]), default=None)
@click.option("--concurrency", type=click.IntRange(min=1), default=None)
def run(
    baseline: str,
    candidate: str,
    dataset: str,
    model: str | None,
    max_tokens: int | None,
    thinking: str | None,
    concurrency: int | None,
) -> None:
    """Run an A/B comparison for two versions on a case collection."""
    root = Path.cwd()
    try:
        config = Config.load(root)
        versions = VersionManager(root)
        baseline_version = versions.get_version(baseline)
        candidate_version = versions.get_version(candidate)
        case_set = CaseManager(root).get_cases(dataset)
        if not case_set:
            raise click.ClickException(
                f"E_CASE_NOT_FOUND: dataset '{dataset}' not found or contains no cases"
            )
        run_config = config.run if concurrency is None else type(config.run)(config.run.timeout_seconds, concurrency)
        params = {key: value for key, value in {"model": model, "max_tokens": max_tokens, "thinking": thinking}.items() if value is not None}
        result = asyncio.run(
            RunEngine(Provider(config.provider), run_config, project_root=root).run(
                baseline_version.prompt_text,
                candidate_version.prompt_text,
                case_set,
                baseline_version=baseline,
                candidate_version=candidate,
                dataset=dataset,
                provider_params=params,
            )
        )
    except click.ClickException:
        raise
    except (ConfigError, VersionManagerError, CaseManagerError, ValueError) as error:
        raise click.ClickException(str(error)) from error

    total = len(result.cases)
    failed = sum(
        execution.error not in (None, "E_EMPTY_OUTPUT")
        for case in result.cases
        for execution in (case.baseline, case.candidate)
    )
    baseline_summary = result.summary["baseline"]
    candidate_summary = result.summary["candidate"]
    click.echo(f"Run ID: {result.run_id}")
    click.echo(f"Cases: {total} total, {total * 2 - failed} successful calls, {failed} failed calls")
    click.echo(_summary_line("Baseline", baseline, baseline_summary))
    click.echo(_summary_line("Candidate", candidate, candidate_summary))
    click.echo(f"Report saved: .prompt-lab/runs/{result.run_id}/result.json")


@cli.command()
@click.argument("run_id")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
def compare(run_id: str, output_format: str) -> None:
    """Generate a comparison report for RUN_ID."""
    result_path = Path.cwd() / ".prompt-lab" / "runs" / run_id / "result.json"
    if not result_path.is_file():
        raise click.ClickException(f"run '{run_id}' not found")
    try:
        result = _run_result_from_json(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise click.ClickException(f"invalid run result: {error}") from error
    output = ReportBuilder.build_json(result) if output_format == "json" else ReportBuilder.build_table(result)
    click.echo(output)


def _render_table(table: Table) -> str:
    console = Console(record=True, width=120, force_terminal=False, color_system=None)
    console.print(table)
    return console.export_text()


def _summary_line(label: str, version: str, summary: dict[str, float]) -> str:
    return (
        f"{label} ({version}): avg {summary['avg_prompt_tokens']:.0f} tokens, "
        f"avg {summary['avg_latency_ms']:.0f}ms, {summary['non_empty_rate']:.0%} non-empty"
    )


def _run_result_from_json(contents: str) -> RunResult:
    data: dict[str, Any] = json.loads(contents)
    cases = [
        CaseResult(
            case_id=item["case_id"],
            baseline=ExecutionResult(**item["baseline"]),
            candidate=ExecutionResult(**item["candidate"]),
        )
        for item in data["cases"]
    ]
    return RunResult(
        run_id=data["run_id"],
        baseline_version=data["baseline_version"],
        candidate_version=data["candidate_version"],
        dataset=data["dataset"],
        provider_config=data["provider_config"],
        timestamp=data["timestamp"],
        cases=cases,
        summary=data["summary"],
    )


if __name__ == "__main__":
    cli()
