# Prompt Lab Test Plan v2.0

**Project**: Prompt Lab
**Date**: 2026-07-26
**Version**: v2.0
**Plan**: [prompt_lab_plan_v2.0_2026-07-26.en.md](../03-plan/prompt_lab_plan_v2.0_2026-07-26.en.md)
**Spec**: [prompt_lab_spec_v2.0_2026-07-26.en.md](../02-spec/prompt_lab_spec_v2.0_2026-07-26.en.md)
**Previous Test Plan**: [prompt_lab_test_plan_v1.0_2026-07-25.en.md](./prompt_lab_test_plan_v1.0_2026-07-25.en.md)

---

## §1 Scope

### In Scope

| CUJ | Description | Source |
|-----|-------------|--------|
| CUJ-4 | init → add version × 2 → add case (with expected_output) → run --eval → compare (with quality scores) | PRD v2 §3.x |
| CUJ-5 | serve → browser → version list → version detail → run report | PRD v2 §3.x |

### Out of Scope

- CUJ-6 (Web read-write full chain) — P1 priority, manual verification, no E2E automation required
- Real LLM API call tests — all tests mock provider and evaluator
- Real DeepEval call tests — mock `metric.measure()` to return fixed scores
- React component unit tests — manual verification, no Jest/Vitest setup (out of V2 scope)

## §2 Test Pyramid

```
        ╱  E2E  ╱          2 tests (CUJ-4 + CUJ-5)
       ╱────────╱
      ╱  Integ ╱           2 tests (eval chain + web API chain)
     ╱──────────╱
    ╱   Unit   ╱           ~60 tests (V1 ~38 + V2 ~22 new)
   ╱────────────╱
```

### V2 New Unit Tests

| Module | Test File | Est. Tests | Covered Paths |
|--------|-----------|-----------|---------------|
| Config (eval block) | test_config.py (extended) | +4 | eval block parsing / no eval block / missing api_key / metrics format |
| Models | test_run_engine.py (extended) | +3 | EvalResult serialization / V1 compat / eval_summary |
| Eval Model | test_eval_model.py | 3 | model creation / generate / get_model_name |
| Evaluator | test_evaluator.py | 6 | normal / skipped (no expected_output) / error / multi-metric / GEval criteria / baseline+candidate dual eval |
| Run Engine (eval) | test_run_engine.py (extended) | +4 | with eval / eval error non-blocking / eval_summary correct / no-eval compatible |
| Report (eval) | test_report.py (extended) | +3 | eval columns / eval-only mode / no-eval compatible |
| CLI (eval) | test_cli.py (extended) | +2 | run --eval / compare --eval-only |
| Web Server | test_web_server.py | 2 | create_app returns instance / health check |
| Web Versions API | test_web_versions.py | 4 | list / detail / diff / register |
| Web Cases API | test_web_cases.py | 2 | list / filter |
| Web Runs API | test_web_runs.py | 4 | list / detail / trigger / config |
| **V2 Subtotal** | | **~37** | |

### V2 New Integration Tests

| Test | File | Description |
|------|------|-------------|
| test_cuj4_eval_chain | test_e2e.py (extended) | init → add version × 2 → add case → run --eval → compare (with eval columns) |
| test_web_api_chain | test_web_e2e.py | create_app → GET versions → GET version detail → GET runs → GET run detail |

## §3 Mock Strategy

### V1 Mock Strategy (unchanged)

| Layer | Mock Target | Tool |
|-------|-------------|------|
| Provider | `httpx.AsyncClient` | `unittest.mock.patch` + `AsyncMock` |
| Filesystem | `tmp_path` fixture | pytest built-in |
| LLM Output | Fixed JSON strings | Test fixtures |

### V2 New Mock Strategy

| Layer | Mock Target | Tool | Notes |
|-------|-------------|------|-------|
| DeepEval metrics | `metric.measure()` | `unittest.mock.patch` | Returns fixed score + reason, no real LLM calls |
| DeepEval model | `CustomModel.generate()` | `unittest.mock.patch` | Returns fixed text, no real API calls |
| FastAPI HTTP | Not mocked | `fastapi.testclient.TestClient` | In-memory ASGI app invocation |
| React frontend | Not tested | — | Manual verification |

**Key Mock Pattern — DeepEval Evaluation**:

```python
@pytest.fixture
def mock_evaluator():
    """Mock evaluator that returns fixed scores."""
    evaluator = Mock()
    evaluator.evaluate = Mock(return_value=[
        EvalResult(metric_name="faithfulness", score=0.85, reason="good", status="pass"),
        EvalResult(metric_name="faithfulness", score=0.72, reason="ok", status="pass"),
    ])
    return evaluator
```

**Key Mock Pattern — FastAPI TestClient**:

```python
from fastapi.testclient import TestClient

def test_get_versions(tmp_path):
    # Setup: create a version file
    app = create_app(tmp_path)
    client = TestClient(app)
    response = client.get("/api/versions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

**Speed budget**: Full test suite (V1 + V2) < 15 seconds (no real API calls, no DeepEval calls).

## §4 Test Data

### V1 Test Data (unchanged)

Synthetic prompt / case / provider response — same as V1 Test Plan.

### V2 New Test Data

#### Fixture: case with expected_output

```json
{
  "id": "test-case-eval-001",
  "type": "ideal",
  "input": {
    "known_models": "- 「Test Book」→ test model",
    "familiar_domains": "testing (3)",
    "n": 2
  },
  "expected_output": "Recommended: 1. 「Book A」 — reveals hidden mechanism. 2. 「Book B」 — cross-domain insight.",
  "expected_output_note": "Quality recommendation should include hidden mechanisms and cross-domain connections",
  "collection": "test-eval"
}
```

#### Fixture: synthetic EvalResult

```python
EVAL_RESULTS_FIXTURE = [
    EvalResult(metric_name="faithfulness", score=0.85, reason="output is faithful to input", status="pass"),
    EvalResult(metric_name="answer_relevancy", score=0.72, reason="mostly relevant", status="pass"),
    EvalResult(metric_name="geval", score=0.0, reason="", status="skipped"),
    EvalResult(metric_name="faithfulness", score=0.0, reason="", status="error", error="API timeout"),
]
```

#### Fixture: RunResult with eval data

```json
{
  "cases": [{
    "case_id": "test-case-eval-001",
    "baseline": { "output": "...", "prompt_tokens": 100, ... },
    "candidate": { "output": "...", "prompt_tokens": 80, ... },
    "evaluations": [
      { "metric_name": "faithfulness", "score": 0.85, "reason": "...", "status": "pass" },
      { "metric_name": "faithfulness", "score": 0.72, "reason": "...", "status": "pass" }
    ]
  }],
  "summary": {
    "baseline": { "avg_prompt_tokens": 100, ... },
    "candidate": { "avg_prompt_tokens": 80, ... },
    "eval_summary": {
      "baseline": { "faithfulness": { "avg": 0.85, "count": 1 } },
      "candidate": { "faithfulness": { "avg": 0.72, "count": 1 } }
    }
  }
}
```

## §5 Coverage Thresholds

| Layer | Coverage Target |
|-------|----------------|
| `prompt_lab/core/` (including evaluator) | ≥ 80% |
| `prompt_lab/core/evaluator.py` | ≥ 85% |
| `prompt_lab/core/eval_model.py` | ≥ 80% |
| `prompt_lab/web/` | ≥ 80% |
| `prompt_lab/cli.py` | ≥ 70% |
| Overall | ≥ 75% |

Measurement: `pytest --cov=prompt_lab --cov-report=term-missing`

## §6 Backward Compatibility Tests

V2 must guarantee V1 data usability:

| Test | Description |
|------|-------------|
| V1 result.json read | V1-format result.json read by V2: `evaluations` is empty list |
| V1 prompt-lab.yaml read | V1-format yaml without `eval` block loads normally |
| V1 command behavior | Without `--eval`, run/compare behavior identical to V1 |
| V1 tests all pass | All ~38 V1 tests pass on V2 code (no regression) |

## §7 References

- **Plan**: [prompt_lab_plan_v2.0_2026-07-26.en.md](../03-plan/prompt_lab_plan_v2.0_2026-07-26.en.md)
- **Spec**: [prompt_lab_spec_v2.0_2026-07-26.en.md](../02-spec/prompt_lab_spec_v2.0_2026-07-26.en.md)
- **PRD**: [prompt_lab_prd_v2.0_2026-07-26.en.md](../01-prd/prompt_lab_prd_v2.0_2026-07-26.en.md)
- **Previous Test Plan**: [prompt_lab_test_plan_v1.0_2026-07-25.en.md](./prompt_lab_test_plan_v1.0_2026-07-25.en.md)

---

Sign-off: Pending Ezio review
