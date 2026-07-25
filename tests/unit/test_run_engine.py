import json

import pytest

from prompt_lab.core.config import RunConfig
from prompt_lab.core.models import Case, ProviderResponse
from prompt_lab.core.provider import ProviderError, ProviderTimeoutError
from prompt_lab.core.run_engine import RunEngine


def case(case_id: str = "case-1", **inputs) -> Case:
    return Case(id=case_id, type="ideal", input=inputs or {"topic": "books"}, collection="set")


class FakeProvider:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.prompts = []

    async def call(self, prompt, **params):
        self.prompts.append((prompt, params))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def response(content="output", prompt_tokens=10, completion_tokens=5):
    return ProviderResponse(content, prompt_tokens, completion_tokens, "stop")


@pytest.mark.asyncio
async def test_run_renders_both_prompts_records_metrics_and_persists_files(tmp_path):
    provider = FakeProvider([response("base", 12), response("candidate", 8)])
    engine = RunEngine(provider, RunConfig(timeout_seconds=1, concurrency=1), project_root=tmp_path)

    result = await engine.run(
        "baseline {topic}", "candidate {topic}", [case()], baseline_version="v1", candidate_version="v2", dataset="set"
    )

    assert [prompt for prompt, _ in provider.prompts] == ["baseline books", "candidate books"]
    assert result.cases[0].baseline.output == "base"
    assert result.cases[0].candidate.prompt_tokens == 8
    assert result.summary["baseline"]["avg_prompt_tokens"] == 12
    run_dir = tmp_path / ".prompt-lab" / "runs" / result.run_id
    assert json.loads((run_dir / "result.json").read_text(encoding="utf-8"))["run_id"] == result.run_id
    assert len((run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()) >= 4


@pytest.mark.asyncio
async def test_one_case_side_failure_does_not_abort_run(tmp_path):
    provider = FakeProvider([ProviderError("down", retryable=False), response("candidate")])
    result = await RunEngine(provider, RunConfig(1, 1), project_root=tmp_path).run("base", "candidate", [case()])

    assert result.cases[0].baseline.error == "down"
    assert result.cases[0].candidate.output == "candidate"
    assert result.summary["baseline"]["error_rate"] == 1.0


@pytest.mark.asyncio
async def test_timeout_is_retried_with_exponential_backoff(tmp_path, monkeypatch):
    provider = FakeProvider([ProviderTimeoutError("slow"), ProviderTimeoutError("slow"), response(), response()])
    waits = []

    async def fake_sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr("prompt_lab.core.run_engine.asyncio.sleep", fake_sleep)
    result = await RunEngine(provider, RunConfig(1, 1), project_root=tmp_path).run("base", "candidate", [case()])

    assert result.cases[0].baseline.error is None
    assert waits == [1, 2]


@pytest.mark.asyncio
async def test_empty_output_is_recorded_without_aborting_run(tmp_path):
    provider = FakeProvider([response(""), response("candidate")])
    result = await RunEngine(provider, RunConfig(1, 1), project_root=tmp_path).run("base", "candidate", [case()])

    assert result.cases[0].baseline.output == ""
    assert result.cases[0].baseline.error == "E_EMPTY_OUTPUT"
    assert result.summary["baseline"]["non_empty_rate"] == 0.0


@pytest.mark.asyncio
async def test_all_failures_are_summarized(tmp_path):
    provider = FakeProvider([ProviderError("base failed", retryable=False), ProviderError("candidate failed", retryable=False)])
    result = await RunEngine(provider, RunConfig(1, 1), project_root=tmp_path).run("base", "candidate", [case()])

    assert result.summary["baseline"]["error_rate"] == 1.0
    assert result.summary["candidate"]["error_rate"] == 1.0


@pytest.mark.asyncio
async def test_render_error_is_recorded_for_the_case(tmp_path):
    result = await RunEngine(FakeProvider([]), RunConfig(1, 1), project_root=tmp_path).run(
        "base {missing}", "candidate {missing}", [case()]
    )

    assert result.cases[0].baseline.error.startswith("E_CASE_FORMAT")
    assert result.cases[0].candidate.error.startswith("E_CASE_FORMAT")


@pytest.mark.asyncio
async def test_summary_averages_successful_records(tmp_path):
    provider = FakeProvider([response("a", 10), response("b", 20), response("c", 30), response("d", 40)])
    result = await RunEngine(provider, RunConfig(1, 1), project_root=tmp_path).run(
        "base", "candidate", [case("one"), case("two")]
    )

    assert result.summary["baseline"]["avg_prompt_tokens"] == 20
    assert result.summary["candidate"]["avg_prompt_tokens"] == 30
