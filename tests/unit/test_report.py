import json

from prompt_lab.core.models import CaseResult, ExecutionResult, RunResult
from prompt_lab.core.report import ReportBuilder


def run_result(cases=None) -> RunResult:
    cases = cases if cases is not None else [
        CaseResult(
            "case-1",
            ExecutionResult(output="base", prompt_tokens=100, completion_tokens=10, latency_ms=200),
            ExecutionResult(output="candidate", prompt_tokens=80, completion_tokens=9, latency_ms=150),
        )
    ]
    return RunResult(
        run_id="run-1",
        baseline_version="v1",
        candidate_version="v2",
        dataset="books",
        provider_config={"model": "test"},
        timestamp="2026-01-01T00:00:00Z",
        cases=cases,
        summary={
            "baseline": {
                "avg_prompt_tokens": 100,
                "avg_completion_tokens": 10,
                "avg_latency_ms": 200,
                "non_empty_rate": 1.0,
                "error_rate": 0.0,
            },
            "candidate": {
                "avg_prompt_tokens": 80,
                "avg_completion_tokens": 9,
                "avg_latency_ms": 150,
                "non_empty_rate": 1.0,
                "error_rate": 0.0,
            },
        },
    )


def test_build_table_includes_per_case_and_summary_metrics():
    table = ReportBuilder.build_table(run_result())

    assert "case-1" in table
    assert "Baseline tokens" in table
    assert "Summary" in table
    assert "Avg prompt tokens" in table


def test_build_json_outputs_complete_run_data():
    report = json.loads(ReportBuilder.build_json(run_result()))

    assert report["run_id"] == "run-1"
    assert report["cases"][0]["candidate"]["output"] == "candidate"
    assert report["summary"]["baseline"]["avg_latency_ms"] == 200


def test_build_table_handles_empty_results():
    table = ReportBuilder.build_table(run_result(cases=[]))

    assert "No cases" in table
    assert "Summary" in table


def test_delta_formats_percentage_change():
    assert ReportBuilder.delta(100, 80) == "-20%"
    assert ReportBuilder.delta(100, 125) == "+25%"
    assert ReportBuilder.delta(0, 0) == "0%"
