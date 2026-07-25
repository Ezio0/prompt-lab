"""Comparison report rendering for terminal and JSON consumers."""

from dataclasses import asdict
import json

from rich.console import Console
from rich.table import Table

from prompt_lab.core.models import RunResult


class ReportBuilder:
    """Render a completed run as a terminal table or structured JSON."""

    @staticmethod
    def build_table(run_result: RunResult) -> str:
        """Return a Rich-rendered per-case comparison and summary report."""
        console = Console(record=True, width=140, force_terminal=False, color_system=None)
        console.print(f"Run {run_result.run_id}: {run_result.baseline_version} → {run_result.candidate_version}")
        cases_table = Table(title="Case comparison")
        for column in (
            "Case",
            "Baseline tokens",
            "Candidate tokens",
            "Δ tokens",
            "Baseline ms",
            "Candidate ms",
            "Δ latency",
            "Baseline output",
            "Candidate output",
        ):
            cases_table.add_column(column)
        if not run_result.cases:
            cases_table.add_row("No cases were run", "", "", "", "", "", "", "", "")
        for case in run_result.cases:
            cases_table.add_row(
                case.case_id,
                str(case.baseline.prompt_tokens),
                str(case.candidate.prompt_tokens),
                ReportBuilder.delta(case.baseline.prompt_tokens, case.candidate.prompt_tokens),
                ReportBuilder._number(case.baseline.latency_ms),
                ReportBuilder._number(case.candidate.latency_ms),
                ReportBuilder.delta(case.baseline.latency_ms, case.candidate.latency_ms),
                case.baseline.output or case.baseline.error or "",
                case.candidate.output or case.candidate.error or "",
            )
        console.print(cases_table)

        summary_table = Table(title="Summary")
        summary_table.add_column("Metric")
        summary_table.add_column(f"Baseline ({run_result.baseline_version})")
        summary_table.add_column(f"Candidate ({run_result.candidate_version})")
        summary_table.add_column("Delta")
        baseline = run_result.summary.get("baseline", {})
        candidate = run_result.summary.get("candidate", {})
        for key, label, suffix in (
            ("avg_prompt_tokens", "Avg prompt tokens", ""),
            ("avg_completion_tokens", "Avg completion tokens", ""),
            ("avg_latency_ms", "Avg latency", "ms"),
            ("non_empty_rate", "Non-empty rate", "%"),
            ("error_rate", "Error rate", "%"),
        ):
            baseline_value = float(baseline.get(key, 0.0))
            candidate_value = float(candidate.get(key, 0.0))
            if suffix == "%":
                baseline_display = f"{baseline_value:.0%}"
                candidate_display = f"{candidate_value:.0%}"
            else:
                baseline_display = f"{ReportBuilder._number(baseline_value)}{suffix}"
                candidate_display = f"{ReportBuilder._number(candidate_value)}{suffix}"
            summary_table.add_row(
                label,
                baseline_display,
                candidate_display,
                ReportBuilder.delta(baseline_value, candidate_value),
            )
        console.print(summary_table)
        return console.export_text()

    @staticmethod
    def build_json(run_result: RunResult) -> str:
        """Return all run data as formatted JSON."""
        return json.dumps(asdict(run_result), ensure_ascii=False, indent=2)

    @staticmethod
    def delta(baseline: float, candidate: float) -> str:
        """Format the relative difference between two metrics."""
        if baseline == 0:
            return "0%" if candidate == 0 else "n/a"
        percent = (candidate - baseline) / baseline * 100
        return f"{percent:+.0f}%" if percent else "0%"

    @staticmethod
    def _number(value: float) -> str:
        return f"{value:.2f}".rstrip("0").rstrip(".")
