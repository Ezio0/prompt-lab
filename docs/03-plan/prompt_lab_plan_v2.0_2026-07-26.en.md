# Prompt Lab Implementation Plan v2.0

**Project**: Prompt Lab
**Date**: 2026-07-26
**Version**: v2.0
**Spec**: [prompt_lab_spec_v2.0_2026-07-26.en.md](../02-spec/prompt_lab_spec_v2.0_2026-07-26.en.md)
**PRD**: [prompt_lab_prd_v2.0_2026-07-26.en.md](../01-prd/prompt_lab_prd_v2.0_2026-07-26.en.md)
**Previous Plan**: [prompt_lab_plan_v1.0_2026-07-25.en.md](./prompt_lab_plan_v1.0_2026-07-25.en.md)

---

## §1 Overview

References [Spec §1 Overview](../02-spec/prompt_lab_spec_v2.0_2026-07-26.en.md#1-overview).

This plan breaks down V2's quality evaluation engine and Web UI into independently executable Tasks, ordered by dependency.

## §2 Phases

| Phase | Goal | Tasks |
|-------|------|-------|
| **P5: Evaluation Engine** | EvalConfig + Evaluator + RunEngine extension + Report extension | T-101 ~ T-109 |
| **P6: Web API** | FastAPI service layer + REST endpoints + serve command | T-201 ~ T-206 |
| **P7: React SPA** | Frontend project + pages + components + build integration | T-301 ~ T-309 |
| **P8: Integration Tests** | CUJ-4 (CLI+eval) + CUJ-5 (Web read-only) E2E | T-401 ~ T-402 |

## Pre-flight Environment Check

Must verify before implementation:

- [ ] **Python venv available** — `cd /Users/ezio/.local/prompt-lab && source .venv/bin/activate && python --version` returns 3.11+
- [ ] **DeepSeek API key set** — `echo $DEEPSEEK_API_KEY` non-empty
- [ ] **Node.js available** (P7 needed) — `node --version` returns 18+
- [ ] **npm available** — `npm --version` returns 9+
- [ ] **Port 8765 free** — `lsof -i :8765` no output
- [ ] **V1 tests all pass** — `cd /Users/ezio/.local/prompt-lab && source .venv/bin/activate && python -m pytest tests/ -q` all green

## §3 Task Breakdown

### Phase P5: Evaluation Engine

---

### T-101: EvalConfig Module (P5, S)

**Depends on**: V1 complete

**Description**: Extend `Config` to support `eval` config block.

**Acceptance criteria**:
- [ ] `EvalMetricConfig` dataclass: `name`, `params: dict`
- [ ] `EvalConfig` dataclass: `enabled`, `metrics: list[EvalMetricConfig]`, `model`, `api_key_env`
- [ ] `Config.load()` parses `eval` block, returns `EvalConfig(enabled=False, ...)` when absent
- [ ] `Config.load()` reads env var from `eval.api_key_env`
- [ ] Backward-compatible: V1 yaml without `eval` block loads normally
- [ ] Unit tests: with eval block / without / missing api_key / empty metrics

**Files**:
- Modify: `prompt_lab/core/config.py`
- Modify: `tests/unit/test_config.py`

---

### T-102: EvalResult + CaseResult Extension (P5, S)

**Depends on**: T-101

**Description**: Add `EvalResult` dataclass, extend `CaseResult` with `evaluations` field.

**Acceptance criteria**:
- [ ] `EvalResult` dataclass: `metric_name`, `score: float`, `reason: str`, `status: str`, `error: str | None`
- [ ] `CaseResult` gets `evaluations: list[EvalResult]` field, default empty list
- [ ] `RunResult.summary` gets optional `eval_summary` dict field
- [ ] V1 `result.json` deserializes with `evaluations` defaulting to empty list (backward-compatible)
- [ ] Unit tests: serialization with evaluations / V1 data compatibility

**Files**:
- Modify: `prompt_lab/core/models.py`
- Modify: `prompt_lab/core/run_engine.py` (`_write_result` and summary extension)
- Modify: `prompt_lab/cli.py` (`_run_result_from_json` compatibility)

---

### T-103: DeepEval Custom Model Adapter (P5, M)

**Depends on**: T-101

**Description**: Create DeepEval-compatible custom LLM model class for OpenAI-compatible APIs (DeepSeek, etc.).

**Key context**: DeepEval defaults to OpenAI endpoint. For non-OpenAI models (e.g. DeepSeek), create a `DeepEvalBaseLLM` subclass.

**Acceptance criteria**:
- [ ] `CustomModel` class inherits `DeepEvalBaseLLM`
- [ ] Reads `model`, `base_url`, `api_key` from EvalConfig
- [ ] `load_model()` returns OpenAI client (with base_url override)
- [ ] `generate()` implements text generation
- [ ] `get_model_name()` returns model name
- [ ] Eval model can differ from generation model
- [ ] Unit tests mock OpenAI client, verify call path

**Files**:
- Create: `prompt_lab/core/eval_model.py`
- Create: `tests/unit/test_eval_model.py`

**Implementation reference**:

```python
from deepeval.models import DeepEvalBaseLLM
from openai import OpenAI

class CustomModel(DeepEvalBaseLLM):
    def __init__(self, model: str, base_url: str, api_key: str):
        self.model_name = model
        self.base_url = base_url
        self.api_key = api_key

    def load_model(self):
        return OpenAI(base_url=self.base_url, api_key=self.api_key)

    def generate(self, prompt: str) -> str:
        client = self.load_model()
        resp = client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return resp.choices[0].message.content

    def get_model_name(self):
        return self.model_name
```

---

### T-104: Evaluator Module (P5, M)

**Depends on**: T-101, T-102, T-103

**Description**: Core evaluation engine, executes DeepEval metrics against baseline and candidate outputs.

**Acceptance criteria**:
- [ ] `Evaluator.__init__(eval_config, eval_model)` accepts config and model
- [ ] `Evaluator.evaluate(case, baseline_output, candidate_output) -> list[EvalResult]`
- [ ] For each output (baseline + candidate) × each metric: execute eval
- [ ] Build `LLMTestCase` (input=case.input concatenated, actual_output, expected_output, context)
- [ ] Metric mapping:
  - `faithfulness` → `FaithfulnessMetric(model=eval_model)`
  - `answer_relevancy` → `AnswerRelevancyMetric(model=eval_model)`
  - `geval` → `GEval(name, criteria/evaluation_steps, evaluation_params, model=eval_model)`
- [ ] Case lacking `expected_output` when metric needs it → `EvalResult(status="skipped")`
- [ ] DeepEval internal exception → `EvalResult(status="error", error=str(e))`, no abort
- [ ] Eval timeout (30s) → `EvalResult(status="error")`
- [ ] Unit tests: normal eval / skipped / error / multi-metric / GEval custom criteria

**Files**:
- Create: `prompt_lab/core/evaluator.py`
- Create: `tests/unit/test_evaluator.py`

**Implementation reference**:

```python
from deepeval.metrics import GEval, FaithfulnessMetric, AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase, SingleTurnParams

class Evaluator:
    def __init__(self, eval_config: EvalConfig, eval_model: CustomModel):
        self.config = eval_config
        self.model = eval_model

    def evaluate(self, case: Case, baseline_output: str, candidate_output: str) -> list[EvalResult]:
        results = []
        for metric_config in self.config.metrics:
            metric = self._build_metric(metric_config)
            for version_label, output in [("baseline", baseline_output), ("candidate", candidate_output)]:
                result = self._run_metric(metric, metric_config.name, case, output)
                results.append(result)
        return results

    def _build_metric(self, config: EvalMetricConfig):
        name = config.name
        if name == "faithfulness":
            return FaithfulnessMetric(model=self.model)
        elif name == "answer_relevancy":
            return AnswerRelevancyMetric(model=self.model)
        elif name == "geval":
            return GEval(
                name=config.params.get("name", "Custom"),
                criteria=config.params.get("criteria", ""),
                evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
                model=self.model,
            )
        else:
            raise ValueError(f"Unknown metric: {name}")
```

---

### T-105: RunEngine Extension (P5, M)

**Depends on**: T-104

**Description**: Integrate evaluation into A/B run, trigger eval after each case output completes.

**Acceptance criteria**:
- [ ] `RunEngine.__init__` adds optional `evaluator: Evaluator | None` parameter
- [ ] `RunEngine.run()` adds `run_eval: bool = False` parameter
- [ ] When `run_eval=True` and `evaluator` not None: call `evaluator.evaluate()` after each case output
- [ ] Eval results written to `CaseResult.evaluations`
- [ ] summary gets `eval_summary` block (per-metric baseline/candidate averages)
- [ ] Eval does not abort run (eval error marked, continues)
- [ ] events.jsonl adds `eval_completed` / `eval_skipped` / `eval_failed` events
- [ ] `run_completed` event extended with eval fields
- [ ] Without `run_eval`, behavior identical to V1
- [ ] Unit tests: with eval / without eval / eval error / eval skipped

**Files**:
- Modify: `prompt_lab/core/run_engine.py`
- Modify: `tests/unit/test_run_engine.py`

---

### T-106: ReportBuilder Extension (P5, S)

**Depends on**: T-105

**Description**: Comparison report adds quality evaluation columns.

**Acceptance criteria**:
- [ ] `build_table()` detects non-empty `evaluations` and adds eval columns
- [ ] Each column shows baseline vs candidate metric score
- [ ] summary adds eval_summary rows
- [ ] New `build_eval_summary(run_result)` method: eval-only output
- [ ] `--eval-only` option shows only eval data
- [ ] Without evaluations, report identical to V1
- [ ] Unit tests: table with eval / json with eval / eval-only / no-eval compatible

**Files**:
- Modify: `prompt_lab/core/report.py`
- Modify: `tests/unit/test_report.py`

---

### T-107: CLI run --eval + compare --eval-only (P5, S)

**Depends on**: T-105, T-106

**Description**: CLI commands integrate `--eval` and `--eval-only` flags.

**Acceptance criteria**:
- [ ] `run` command adds `--eval` flag
- [ ] `run --eval`:
  - [ ] Checks DeepEval installed, errors `E_EVAL_NOT_INSTALLED` if not
  - [ ] Loads EvalConfig from Config
  - [ ] Creates eval model + Evaluator
  - [ ] Passes to RunEngine, `run_eval=True`
- [ ] `compare` command adds `--eval-only` flag
- [ ] Without `--eval`, behavior unchanged
- [ ] CLI output includes eval info (when eval data present)
- [ ] Unit tests: run --eval / compare --eval-only / error when no deepeval

**Files**:
- Modify: `prompt_lab/cli.py`
- Modify: `tests/unit/test_cli.py`

---

### T-108: pyproject.toml Optional Dependencies (P5, XS)

**Depends on**: T-101

**Description**: Add `[eval]` optional dependency group.

**Acceptance criteria**:
- [ ] `pyproject.toml` adds `[project.optional-dependencies] eval = ["deepeval>=2.0", "openai>=1.0"]`
- [ ] `pip install prompt-lab[eval]` installs successfully
- [ ] Without eval deps: `import deepeval` raises ImportError
- [ ] version bump to 2.0.0

**Files**:
- Modify: `pyproject.toml`

---

### T-109: Phase P5 Integration Check (P5, S)

**Depends on**: T-101 ~ T-108

**Acceptance criteria**:
- [ ] Full unit test suite passes
- [ ] `prompt-lab run --eval` executable (mock provider + mock eval)
- [ ] `prompt-lab compare <run-id>` report includes eval columns (when run has eval data)
- [ ] V1 tests all pass (no regression)

---

### Phase P6: Web API (FastAPI)

---

### T-201: FastAPI App Scaffold + serve Command (P6, S)

**Depends on**: V1 complete

**Description**: Create FastAPI app scaffold and `prompt-lab serve` CLI command.

**Acceptance criteria**:
- [ ] `prompt_lab/web/__init__.py` created
- [ ] `prompt_lab/web/server.py` defines `create_app(project_root: Path) -> FastAPI`
- [ ] App includes CORS middleware (allow localhost)
- [ ] App includes access log middleware (write `.prompt-lab/web.log`)
- [ ] CLI adds `serve` command: `prompt-lab serve [--port 8765] [--host 127.0.0.1]`
- [ ] serve command calls `uvicorn.run(create_app(Path.cwd()), ...)`
- [ ] FastAPI and uvicorn added to dependencies
- [ ] Unit test: create_app returns FastAPI instance with basic routes

**Files**:
- Create: `prompt_lab/web/__init__.py`
- Create: `prompt_lab/web/server.py`
- Create: `prompt_lab/web/middleware.py` (access log middleware)
- Modify: `prompt_lab/cli.py`
- Modify: `pyproject.toml` (add fastapi, uvicorn)
- Create: `tests/unit/test_web_server.py`

---

### T-202: Version Management REST Endpoints (P6, M)

**Depends on**: T-201

**Description**: Version-related REST API endpoints.

**Acceptance criteria**:
- [ ] `GET /api/versions` — version list (without prompt_text)
- [ ] `GET /api/versions/{id}` — full version (with prompt_text)
- [ ] `GET /api/versions/{id_a}/{id_b}/diff` — diff
- [ ] `POST /api/versions` — register new version
- [ ] Error handling: 404 (not found), 409 (already exists)
- [ ] API key never in response
- [ ] Unit tests cover all endpoints + error paths

**Files**:
- Create: `prompt_lab/web/routes/versions.py`
- Create: `tests/unit/test_web_versions.py`

---

### T-203: Case + Run REST Endpoints (P6, M)

**Depends on**: T-201

**Description**: Case and Run-related REST API endpoints.

**Acceptance criteria**:
- [ ] `GET /api/cases` — case list (supports ?collection= and ?type= filters)
- [ ] `GET /api/runs` — run list
- [ ] `GET /api/runs/{id}` — run detail (full result.json data)
- [ ] `POST /api/runs` — trigger A/B run (synchronous return)
- [ ] `GET /api/config` — return config (api_key_env but not value)
- [ ] Error handling: 400 (bad params), 404 (not found), 502 (provider error)
- [ ] Unit tests cover all endpoints + error paths

**Files**:
- Create: `prompt_lab/web/routes/cases.py`
- Create: `prompt_lab/web/routes/runs.py`
- Create: `prompt_lab/web/routes/config.py`
- Create: `tests/unit/test_web_cases.py`
- Create: `tests/unit/test_web_runs.py`

---

### T-204: Static Files Hosting (P6, S)

**Depends on**: T-201, T-306 (frontend build)

**Description**: FastAPI serves React SPA static files.

**Acceptance criteria**:
- [ ] `create_app()` mounts `StaticFiles(directory="web/frontend/dist", html=True)` at `/`
- [ ] When build output missing, returns JSON hint
- [ ] SPA history fallback (all non-/api/ paths return index.html)
- [ ] Unit tests: static file accessible / fallback

**Files**:
- Modify: `prompt_lab/web/server.py`

---

### Phase P7: React SPA

---

### T-301: Vite + React + TypeScript Project Init (P7, S)

**Depends on**: None

**Description**: Create React SPA project in `web/frontend/`.

**Acceptance criteria**:
- [ ] `web/frontend/` directory created
- [ ] `npm create vite@latest . -- --template react-ts` executed
- [ ] Dependencies installed: `react`, `react-dom`, `react-router-dom`, `axios`
- [ ] UI libs installed: `tailwindcss`, `postcss`, `autoprefixer`
- [ ] Component libs installed: `recharts` (charts), `react-diff-viewer-continued` (diff)
- [ ] `tailwind.config.js` configured
- [ ] `npm run dev` starts locally
- [ ] Vite proxy config: `/api` → `http://localhost:8765`

**Files**:
- Create: `web/frontend/` full scaffold
- Create: `web/frontend/vite.config.ts` (with proxy config)

---

### T-302: API Client + TypeScript Types (P7, S)

**Depends on**: T-301

**Description**: Frontend API layer and type definitions.

**Acceptance criteria**:
- [ ] `src/types/index.ts` defines all types (Version, Case, RunResult, EvalResult, etc.)
- [ ] `src/api/client.ts` wraps all API calls
- [ ] API functions: `getVersions()`, `getVersion(id)`, `getDiff(a, b)`, `createVersion(...)`, `getCases(...)`, `getRuns()`, `getRun(id)`, `triggerRun(...)`, `getConfig()`

**Files**:
- Create: `web/frontend/src/types/index.ts`
- Create: `web/frontend/src/api/client.ts`

---

### T-303: Version List + Detail + Diff Pages (P7, M)

**Depends on**: T-302

**Description**: Version management pages and components.

**Acceptance criteria**:
- [ ] `VersionList` component: table showing version list
- [ ] `VersionDetail` page: shows full prompt (monospace)
- [ ] `DiffViewer` component: side-by-side diff
- [ ] React Router routes configured
- [ ] Empty state messages
- [ ] Pages manually verifiable (`npm run dev`)

**Files**:
- Create: `web/frontend/src/pages/VersionList.tsx`
- Create: `web/frontend/src/pages/VersionDetail.tsx`
- Create: `web/frontend/src/components/DiffViewer.tsx`
- Create: `web/frontend/src/App.tsx` (routes)

---

### T-304: Run List + Report Pages (P7, M)

**Depends on**: T-302

**Description**: Run report pages and components.

**Acceptance criteria**:
- [ ] `RunList` component: table showing run list
- [ ] `RunReport` page: summary cards + per-case table + output comparison
- [ ] `EvalScoreCard` component: eval score card
- [ ] `MetricChart` component: bar chart comparison (recharts)
- [ ] Eval score highlighting (pass=green, skipped=gray, error=red)
- [ ] JSON download button
- [ ] Pages manually verifiable

**Files**:
- Create: `web/frontend/src/pages/RunList.tsx`
- Create: `web/frontend/src/pages/RunReport.tsx`
- Create: `web/frontend/src/components/EvalScoreCard.tsx`
- Create: `web/frontend/src/components/MetricChart.tsx`

---

### T-305: Prompt Editor Page (P7, M)

**Depends on**: T-302, T-303

**Description**: Web UI prompt editing and registration.

**Acceptance criteria**:
- [ ] `PromptEditor` component: monospace textarea
- [ ] Variable placeholder hints
- [ ] Registration form: version name, change note, change type
- [ ] Pre-registration diff preview (compare with previous version)
- [ ] After registration, redirect to version list
- [ ] Cannot overwrite existing version (API 409 handling)
- [ ] Confirmation dialog ("This cannot be undone")
- [ ] Pages manually verifiable

**Files**:
- Create: `web/frontend/src/pages/PromptEditor.tsx`
- Create: `web/frontend/src/components/VersionForm.tsx`

---

### T-306: Build + Static Files Integration (P7, S)

**Depends on**: T-303, T-304, T-305, T-204

**Description**: Frontend build and integration with FastAPI.

**Acceptance criteria**:
- [ ] `npm run build` generates `web/frontend/dist/`
- [ ] `dist/` committed to git
- [ ] FastAPI `create_app()` serves `dist/` as static files
- [ ] SPA fallback works correctly
- [ ] `prompt-lab serve` → browser accesses full Web UI
- [ ] API + frontend on same port

**Files**:
- Modify: `web/frontend/` (build config)
- Modify: `.gitignore` (don't ignore `dist/`)

---

### Phase P8: Integration Tests

---

### T-401: CUJ-4 E2E — CLI Quality Eval Full Chain (P8, M)

**Depends on**: T-107

**Acceptance criteria**:
- [ ] E2E test covers: init → add version × 2 → add case (with expected_output) → run --eval → compare
- [ ] Verify result.json includes evaluations field
- [ ] Verify eval_summary includes averages
- [ ] Mock provider + mock evaluator (no real LLM calls)

**Files**:
- Modify: `tests/integration/test_e2e.py`

---

### T-402: CUJ-5 E2E — Web Read-Only Browse (P8, M)

**Depends on**: T-202, T-203

**Acceptance criteria**:
- [ ] E2E test covers: create_app → GET /api/versions → GET /api/versions/{id} → GET /api/runs → GET /api/runs/{id}
- [ ] Verify API response format
- [ ] Verify error paths (404)
- [ ] Use FastAPI TestClient (no real server)

**Files**:
- Create: `tests/integration/test_web_e2e.py`

---

## §4 Dependency Graph

```
Phase P5 (Eval Engine):
T-101 (EvalConfig)
  ├── T-102 (EvalResult + CaseResult) ── T-105 (RunEngine ext)
  │                                         └── T-106 (Report ext) ── T-107 (CLI)
  ├── T-103 (DeepEval model adapter)
  │     └── T-104 (Evaluator) ────────── T-105
  └── T-108 (pyproject.toml)
        └── T-109 (P5 integration check)

Phase P6 (Web API):
T-201 (FastAPI scaffold + serve)
  ├── T-202 (Version REST)
  ├── T-203 (Case + Run REST)
  └── T-204 (Static files) ←── T-306 (frontend build)

Phase P7 (React SPA):
T-301 (Vite project)
  └── T-302 (API client + types)
        ├── T-303 (Version pages)
        ├── T-304 (Run pages)
        └── T-305 (Editor page)
              └── T-306 (Build + integrate)

Phase P8 (Integration):
T-107 ←── T-401 (CUJ-4 CLI eval E2E)
T-203 ←── T-402 (CUJ-5 Web E2E)
```

## §5 Execution Strategy

- **Phase P5** (eval engine) and **Phase P6** (Web API) can run in parallel
- **Phase P7** (React SPA) depends on P6 completion
- **Phase P8** (integration tests) after P5/P6 complete
- Run corresponding unit tests after each Task
- Run full test suite after each Phase
- P5 can be released independently (`run --eval` usable)
- P6+P7 release complete V2 (`serve` usable)

## §6 Definition of Done

- [ ] All Tasks' acceptance criteria checked off
- [ ] Full test suite passes (unit + integration)
- [ ] `prompt-lab run --eval` executable (mock mode)
- [ ] `prompt-lab serve` starts and browser accesses Web UI
- [ ] Web UI version list/detail/run report/editor functional
- [ ] V1 tests all pass (no regression)
- [ ] Committed + pushed to main

## §7 History

| Date | Event |
|------|-------|
| 2026-07-26 | Initial creation |

---

Sign-off: Pending Ezio review
