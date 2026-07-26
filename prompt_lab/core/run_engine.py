"""Asynchronous A/B comparison execution and local run persistence."""

import asyncio
from dataclasses import asdict
from datetime import UTC, datetime
import json
from pathlib import Path
import time
from typing import Any, Protocol

from prompt_lab.core.config import RunConfig
from prompt_lab.core.evaluator import Evaluator
from prompt_lab.core.models import Case, CaseResult, EvalResult, ExecutionResult, ProviderResponse, RunResult
from prompt_lab.core.provider import ProviderError


class ProviderProtocol(Protocol):
    """The minimal provider interface required by the run engine."""

    async def call(self, prompt: str, **params: Any) -> ProviderResponse: ...


class RunEngine:
    """Run two prompts against a case set and retain audit records locally."""

    def __init__(
        self, provider: ProviderProtocol, config: RunConfig, *, project_root: Path | None = None,
        evaluator: Evaluator | None = None,
    ) -> None:
        self.provider = provider
        self.config = config
        self.project_root = project_root or Path.cwd()
        self.evaluator = evaluator

    async def run(
        self,
        baseline_prompt: str,
        candidate_prompt: str,
        cases: list[Case],
        *,
        baseline_version: str = "",
        candidate_version: str = "",
        dataset: str = "",
        provider_params: dict[str, Any] | None = None,
        run_eval: bool = False,
    ) -> RunResult:
        """Execute a resilient A/B comparison and save ``result.json`` and events."""
        started = time.perf_counter()
        timestamp = self._timestamp()
        run_id, run_dir = self._create_run_dir(timestamp)
        params = dict(provider_params or {})
        params.setdefault("timeout_seconds", self.config.timeout_seconds)
        semaphore = asyncio.Semaphore(self.config.concurrency)

        async def process(case: Case) -> CaseResult:
            async with semaphore:
                return await self._run_case(
                    case, baseline_prompt, candidate_prompt, params, run_eval
                )

        case_results = list(await asyncio.gather(*(process(case) for case in cases)))
        summary = {
            "baseline": self._summary([case.baseline for case in case_results]),
            "candidate": self._summary([case.candidate for case in case_results]),
        }

        # Compute eval summary if any evaluations exist
        eval_summary: dict[str, Any] = {}
        if any(c.evaluations for c in case_results):
            # Split evaluations: baseline first half, candidate second half per case
            baseline_evals: list[EvalResult] = []
            candidate_evals: list[EvalResult] = []
            for case in case_results:
                half = len(case.evaluations) // 2
                baseline_evals.extend(case.evaluations[:half])
                candidate_evals.extend(case.evaluations[half:])
            eval_summary = {
                "baseline": Evaluator.compute_eval_summary(baseline_evals),
                "candidate": Evaluator.compute_eval_summary(candidate_evals),
            }

        result = RunResult(
            run_id=run_id,
            baseline_version=baseline_version,
            candidate_version=candidate_version,
            dataset=dataset,
            provider_config=self._provider_config(params),
            timestamp=timestamp,
            cases=case_results,
            summary={"baseline": summary["baseline"], "candidate": summary["candidate"], "eval_summary": eval_summary} if eval_summary else summary,
        )
        self._write_result(run_dir, result)
        self._write_events(run_dir, result, duration_ms=(time.perf_counter() - started) * 1000)
        return result

    async def _run_case(
        self,
        case: Case,
        baseline_prompt: str,
        candidate_prompt: str,
        params: dict[str, Any],
        run_eval: bool = False,
    ) -> CaseResult:
        baseline = await self._execute(baseline_prompt, case, params)
        candidate = await self._execute(candidate_prompt, case, params)

        evaluations: list[EvalResult] = []
        if run_eval and self.evaluator is not None:
            # Evaluate only if both outputs are non-empty
            if baseline.output and candidate.output:
                try:
                    evaluations = self.evaluator.evaluate(
                        case, baseline.output, candidate.output
                    )
                except Exception:
                    # Evaluation errors are non-blocking; already caught per-metric
                    pass

        return CaseResult(
            case_id=case.id,
            baseline=baseline,
            candidate=candidate,
            evaluations=evaluations,
        )

    async def _execute(self, template: str, case: Case, params: dict[str, Any]) -> ExecutionResult:
        try:
            rendered_prompt = template.format(**case.input)
        except (KeyError, IndexError, ValueError) as error:
            return ExecutionResult(error=f"E_CASE_FORMAT: {error}")

        started = time.perf_counter()
        try:
            response = await self._call_with_retry(rendered_prompt, params)
        except Exception as error:  # Individual failures must not abort the comparison.
            return ExecutionResult(
                latency_ms=(time.perf_counter() - started) * 1000,
                error=str(error),
            )

        empty_error = "E_EMPTY_OUTPUT" if not response.content else None
        return ExecutionResult(
            output=response.content,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            latency_ms=(time.perf_counter() - started) * 1000,
            finish_reason=response.finish_reason,
            error=empty_error,
        )

    async def _call_with_retry(self, prompt: str, params: dict[str, Any]) -> ProviderResponse:
        for attempt in range(4):
            try:
                return await self.provider.call(prompt, **params)
            except ProviderError as error:
                if not error.retryable or attempt == 3:
                    raise
                await asyncio.sleep(2**attempt)
        raise RuntimeError("unreachable")

    def _create_run_dir(self, timestamp: str) -> tuple[str, Path]:
        base_id = timestamp.replace("-", "").replace(":", "").replace("T", "T").replace("Z", "Z")
        runs_dir = self.project_root / ".prompt-lab" / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        run_id = base_id
        index = 1
        while (runs_dir / run_id).exists():
            run_id = f"{base_id}-{index}"
            index += 1
        run_dir = runs_dir / run_id
        run_dir.mkdir()
        return run_id, run_dir

    @staticmethod
    def _summary(records: list[ExecutionResult]) -> dict[str, float]:
        successful = [record for record in records if not RunEngine._is_failure(record)]
        denominator = len(records)
        metric_count = len(successful)
        return {
            "avg_prompt_tokens": sum(record.prompt_tokens for record in successful) / metric_count if metric_count else 0.0,
            "avg_completion_tokens": sum(record.completion_tokens for record in successful) / metric_count if metric_count else 0.0,
            "avg_latency_ms": sum(record.latency_ms for record in successful) / metric_count if metric_count else 0.0,
            "non_empty_rate": sum(bool(record.output) for record in records) / denominator if denominator else 0.0,
            "error_rate": sum(RunEngine._is_failure(record) for record in records) / denominator if denominator else 0.0,
        }

    @staticmethod
    def _is_failure(record: ExecutionResult) -> bool:
        return record.error is not None and record.error != "E_EMPTY_OUTPUT"

    def _provider_config(self, params: dict[str, Any]) -> dict[str, Any]:
        config = getattr(self.provider, "config", None)
        values = {
            "base_url": getattr(config, "base_url", None),
            "model": params.get("model", getattr(config, "model", None)),
            "max_tokens": params.get("max_tokens"),
            "temperature": params.get("temperature"),
            "thinking": params.get("thinking"),
        }
        return {key: value for key, value in values.items() if value is not None}

    @staticmethod
    def _write_result(run_dir: Path, result: RunResult) -> None:
        (run_dir / "result.json").write_text(
            json.dumps(asdict(result), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    @staticmethod
    def _write_events(run_dir: Path, result: RunResult, *, duration_ms: float) -> None:
        events: list[dict[str, Any]] = [
            {
                "event": "run_started",
                "run_id": result.run_id,
                "baseline_version": result.baseline_version,
                "candidate_version": result.candidate_version,
                "dataset": result.dataset,
                "timestamp": result.timestamp,
            }
        ]
        for case in result.cases:
            for version, execution in (("baseline", case.baseline), ("candidate", case.candidate)):
                event = {"case_id": case.case_id, "version": version, **asdict(execution)}
                event["event"] = "case_failed" if RunEngine._is_failure(execution) else "case_completed"
                events.append(event)
        events.append(
            {
                "event": "run_completed",
                "run_id": result.run_id,
                "total_cases": len(result.cases),
                "success_count": sum(
                    not RunEngine._is_failure(execution)
                    for case in result.cases
                    for execution in (case.baseline, case.candidate)
                ),
                "fail_count": sum(
                    RunEngine._is_failure(execution)
                    for case in result.cases
                    for execution in (case.baseline, case.candidate)
                ),
                "duration_ms": duration_ms,
            }
        )
        (run_dir / "events.jsonl").write_text(
            "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events), encoding="utf-8"
        )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
