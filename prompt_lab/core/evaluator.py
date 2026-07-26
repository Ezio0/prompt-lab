"""Quality evaluation engine using DeepEval metrics."""

import asyncio
from typing import TYPE_CHECKING, Any, Protocol

from prompt_lab.core.config import EvalConfig, EvalMetricConfig
from prompt_lab.core.models import Case, EvalResult

if TYPE_CHECKING:
    pass


class EvalModelProtocol(Protocol):
    """Minimal interface the evaluator needs from an eval model."""

    def get_model_name(self) -> str: ...


class Evaluator:
    """Run DeepEval metrics against baseline and candidate prompt outputs.

    The evaluator is optional: if DeepEval is not installed, the Evaluator
    constructor raises ImportError. The caller (RunEngine) is responsible
    for catching this and skipping evaluation gracefully.
    """

    # Metrics that require expected_output (ground truth)
    _METRICS_NEED_EXPECTED = frozenset({"faithfulness", "geval"})

    def __init__(self, eval_config: EvalConfig, eval_model: Any) -> None:
        self.config = eval_config
        self.model = eval_model

    def evaluate(
        self,
        case: Case,
        baseline_output: str,
        candidate_output: str,
    ) -> list[EvalResult]:
        """Evaluate both baseline and candidate outputs for all configured metrics.

        Returns a flat list: [EvalResult for baseline metric 1, EvalResult for candidate metric 1, ...]
        Evaluation failures are caught and returned as EvalResult(status="error").
        """
        results: list[EvalResult] = []
        for metric_config in self.config.metrics:
            for version_label, output in (
                ("baseline", baseline_output),
                ("candidate", candidate_output),
            ):
                result = self._run_single_metric(metric_config, case, output)
                results.append(result)
        return results

    def _run_single_metric(
        self,
        metric_config: EvalMetricConfig,
        case: Case,
        output: str,
    ) -> EvalResult:
        """Execute one metric against one output. Never raises."""
        # Check if this metric needs expected_output
        if (
            metric_config.name in self._METRICS_NEED_EXPECTED
            and not case.expected_output
        ):
            return EvalResult(
                metric_name=metric_config.name,
                score=0.0,
                reason="Skipped: requires expected_output",
                status="skipped",
            )

        try:
            return self._execute_metric(metric_config, case, output)
        except Exception as error:
            return EvalResult(
                metric_name=metric_config.name,
                score=0.0,
                reason="",
                status="error",
                error=str(error),
            )

    def _execute_metric(
        self,
        metric_config: EvalMetricConfig,
        case: Case,
        output: str,
    ) -> EvalResult:
        """Build and run a single DeepEval metric. May raise."""
        from deepeval.metrics import (
            AnswerRelevancyMetric,
            FaithfulnessMetric,
            GEval,
        )
        from deepeval.test_case import LLMTestCase, SingleTurnParams

        # Build the LLMTestCase
        input_text = self._render_input(case)
        test_case = LLMTestCase(
            input=input_text,
            actual_output=output,
        )
        if case.expected_output:
            test_case.expected_output = case.expected_output

        # Build the metric based on config
        metric = self._build_metric(metric_config)

        # Run measurement
        metric.measure(test_case)

        return EvalResult(
            metric_name=metric_config.name,
            score=float(metric.score),
            reason=getattr(metric, "reason", "") or "",
            status="pass",
        )

    def _build_metric(self, config: EvalMetricConfig) -> Any:
        """Construct a DeepEval metric instance from config."""
        from deepeval.metrics import (
            AnswerRelevancyMetric,
            FaithfulnessMetric,
            GEval,
        )
        from deepeval.test_case import SingleTurnParams

        name = config.name
        if name == "faithfulness":
            return FaithfulnessMetric(model=self.model)
        elif name == "answer_relevancy":
            return AnswerRelevancyMetric(model=self.model)
        elif name == "geval":
            criteria = config.params.get("criteria", "Evaluate the output quality.")
            eval_steps = config.params.get("evaluation_steps")
            eval_params = [
                SingleTurnParams.INPUT,
                SingleTurnParams.ACTUAL_OUTPUT,
            ]
            if config.params.get("use_expected", True):
                eval_params.append(SingleTurnParams.EXPECTED_OUTPUT)

            geval_kwargs: dict[str, Any] = {
                "name": config.params.get("name", "Custom"),
                "evaluation_params": eval_params,
                "model": self.model,
            }
            if eval_steps:
                geval_kwargs["evaluation_steps"] = eval_steps
            else:
                geval_kwargs["criteria"] = criteria
            return GEval(**geval_kwargs)
        else:
            raise ValueError(f"Unknown metric: {name}")

    @staticmethod
    def _render_input(case: Case) -> str:
        """Render case input dict to a string for evaluation."""
        parts = [f"{k}: {v}" for k, v in case.input.items()]
        return "\n".join(parts)

    @staticmethod
    def compute_eval_summary(
        evaluations: list[EvalResult],
    ) -> dict[str, dict[str, float]]:
        """Compute average scores per metric from a list of EvalResults.

        Returns: { "faithfulness": {"avg": 0.82, "count": 3}, ... }
        Only includes non-skipped, non-error results.
        """
        by_metric: dict[str, list[float]] = {}
        for ev in evaluations:
            if ev.status != "pass":
                continue
            by_metric.setdefault(ev.metric_name, []).append(ev.score)

        return {
            name: {"avg": sum(scores) / len(scores), "count": len(scores)}
            for name, scores in by_metric.items()
            if scores
        }
