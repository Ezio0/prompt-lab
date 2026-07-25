# Prompt Lab Technical Spec v2.0

**Project**: Prompt Lab
**Date**: 2026-07-26
**Version**: v2.0
**PRD**: [prompt_lab_prd_v2.0_2026-07-26.en.md](../01-prd/prompt_lab_prd_v2.0_2026-07-26.en.md)
**Previous Spec**: [prompt_lab_spec_v1.0_2026-07-25.en.md](./prompt_lab_spec_v1.0_2026-07-25.en.md)

---

## §1 Overview

Prompt Lab v2 adds **quality evaluation engine** (DeepEval integration) and **Web UI** (FastAPI + React SPA) on top of V1's CLI version management + A/B comparison, completing the "change prompt → compare → view data → decide" loop with the missing quality dimension.

**Consumers**: developers (CLI + Web), PM/operations (Web)

**System context**:

```
┌──────────────────────────────────────────────────────────┐
│                    User Machine (localhost)                │
│                                                            │
│  ┌──────────────┐         ┌──────────────────────────────┐│
│  │  CLI (V1)    │         │  Web UI (V2 new)              ││
│  │  prompt-lab  │         │                               ││
│  │              │         │  ┌───────────┐ ┌───────────┐ ││
│  │  init        │         │  │ React SPA │ │ FastAPI   │ ││
│  │  add version │         │  │ (Vite)    │←│ REST API  │ ││
│  │  run --eval  │         │  └───────────┘ └─────┬─────┘ ││
│  │  compare     │         │                      │       ││
│  │  serve  ←──────────────────────────────────────┘       ││
│  └──────┬───────┘         └──────────────────────────────┘│
│         │                           │                      │
│  ┌──────┴────────────────────────────┴──────────────────┐ │
│  │              Core Modules (V1 + V2 extensions)        │ │
│  │                                                       │ │
│  │  VersionManager  CaseManager  Config (+EvalConfig)    │ │
│  │  RunEngine       Provider     ReportBuilder (+Eval)   │ │
│  │                  Evaluator (V2 new)                    │ │
│  └──────────────────────────┬────────────────────────────┘ │
│                             │                              │
│         ┌───────────────────┴────────────────┐             │
│         │       .prompt-lab/ (local)         │             │
│         │  ├── versions/    cases/   runs/   │             │
│         │  └── prompt-lab.yaml (+eval block) │             │
│         └────────────────────────────────────┘             │
└──────────────────────────────────────────────────────────┘
                    │                        │
                    │ HTTP                   │ HTTP
                    ▼                        ▼
         ┌──────────────────┐    ┌──────────────────────┐
         │ LLM Provider     │    │ Eval LLM (same or    │
         │ (generation)     │    │ different)           │
         └──────────────────┘    └──────────────────────┘
```

## §2 Goals

References [PRD §4 Functional Requirements](../01-prd/prompt_lab_prd_v2.0_2026-07-26.en.md#4-functional-requirements).

1. **Quality evaluation integration**: `run --eval` executes configured DeepEval metrics per case, 100% coverage (pass/skipped/error all recorded), single-metric eval p95 < 30s
2. **Report quality dimension**: `compare` report and Web UI both show baseline vs candidate quality scores, summary includes `avg_<metric>`
3. **Web API**: 9 REST endpoints covering version/case/run CRUD, p95 < 100ms (excluding LLM calls)
4. **Web SPA**: 3 pages (versions/runs/editor), page load p95 < 500ms
5. **Backward compatibility**: V1's `result.json` readable by V2; without `--eval`, behavior identical to V1

## §3 Non-Goals

Mirrors [PRD §10 Non-Goals](../01-prd/prompt_lab_prd_v2.0_2026-07-26.en.md#10-non-goals).

1. No automatic prompt optimization (PRD §10.1)
2. No user authentication / multi-user (PRD §10.2)
3. No custom evaluation metric engine (PRD §10.3)
4. No CI/CD integration (PRD §10.4)
5. No online observability / trace monitoring (PRD §10.5)

## §4 Architecture

### §4.1 Components

| Component | Responsibility | Data owned | V1/V2 |
|-----------|---------------|------------|-------|
| **CLI Entry** (`cli.py`) | Command parsing, calling core modules | None | V1 extended (+serve, +--eval) |
| **Version Manager** (`core/version_manager.py`) | Version registration, storage, query, diff | `.prompt-lab/versions/` | V1 unchanged |
| **Case Manager** (`core/case_manager.py`) | Case CRUD | `.prompt-lab/cases/` | V1 unchanged |
| **Run Engine** (`core/run_engine.py`) | A/B execution + eval orchestration | `.prompt-lab/runs/` | V1 extended |
| **Provider Adapter** (`core/provider.py`) | OpenAI-compatible API calls | None | V1 unchanged |
| **Evaluator** (`core/evaluator.py`) | DeepEval metric evaluation | None | **V2 new** |
| **Report Builder** (`core/report.py`) | Comparison report (+quality cols) | None | V1 extended |
| **Config** (`core/config.py`) | Config loading (+eval block) | `prompt-lab.yaml` | V1 extended |
| **Web Server** (`web/server.py`) | FastAPI REST API | None | **V2 new** |
| **Web Frontend** (`web/frontend/`) | React SPA | None | **V2 new** |

### §4.2 Data flow: `run --eval` full pipeline

```
User runs: prompt-lab run --baseline v1 --candidate v2 --dataset books --eval

CLI Entry
  │
  ├─→ Config.load() → provider settings + eval config (model, metrics)
  │
  ├─→ VersionManager: get v1 prompt, get v2 prompt
  │
  ├─→ CaseManager: load cases from "books"
  │
  ├─→ RunEngine.run(baseline, candidate, cases, eval=True):
  │     │
  │     │  for each case (async, semaphore-controlled):
  │     │    ├─→ render v1 prompt → Provider.call() → record result_A
  │     │    ├─→ render v2 prompt → Provider.call() → record result_B
  │     │    │
  │     │    │  if eval enabled:
  │     │    └─→ Evaluator.evaluate(case, result_A.output, result_B.output):
  │     │          ├─→ for each metric in config.eval.metrics:
  │     │          │    ├─→ if case lacks expected_output and metric needs it:
  │     │          │    │     → EvalResult(status=skipped)
  │     │          │    ├─→ call DeepEval metric.measure()
  │     │          │    │     (uses eval Provider → LLM API)
  │     │          │    └─→ EvalResult(metric, score, reason, status=pass)
  │     │          └─→ return [EvalResult, ...]
  │     │
  │     └─→ write result.json + events.jsonl to .prompt-lab/runs/<run-id>/
  │
  └─→ ReportBuilder: read run results → output table/JSON (with eval columns)
```

### §4.3 Data flow: `serve` (Web UI)

```
User runs: prompt-lab serve [--port 8765]

CLI Entry
  │
  └─→ uvicorn.run(web/server.py:app, host=127.0.0.1, port=8765)
        │
        ├─→ FastAPI mounts:
        │    ├── /api/*     → REST endpoints (JSON)
        │    └── /          → StaticFiles(web/frontend/dist/)
        │
        └─→ Browser loads:
             ├── GET /           → index.html (React SPA)
             ├── GET /api/versions  → version list JSON
             ├── GET /api/runs/{id} → run detail JSON
             └── POST /api/runs    → trigger A/B run → return result JSON
```

### §4.4 Deployment topology

| Component | Runs on |
|-----------|---------|
| CLI + Core + Evaluator | User local terminal (Python process) |
| Web Server (FastAPI) | User local terminal (uvicorn process, 127.0.0.1) |
| Web Frontend (React SPA) | User browser (FastAPI serves static files) |
| `.prompt-lab/` | User project directory (local filesystem) |
| LLM Provider (generation) | External HTTP API |
| LLM Provider (evaluation) | External HTTP API (can be same as generation) |

## §5 Data Model

### §5.1 V1 models (unchanged)

`Version`, `Case`, `ProviderResponse`, `RunConfig`, `Config` — structure identical to V1 Spec §5.

### §5.2 V2 extended models

#### EvalConfig (new)

```python
# core/config.py

@dataclass(frozen=True)
class EvalMetricConfig:
    """A single evaluation metric configuration."""
    name: str                    # e.g. "faithfulness", "answer_relevancy", "geval"
    params: dict[str, Any]       # metric-specific params (e.g. criteria for GEval)

@dataclass(frozen=True)
class EvalConfig:
    """Evaluation engine configuration."""
    enabled: bool                # false by default, --eval overrides to true
    metrics: list[EvalMetricConfig]
    model: str                   # LLM model for evaluation
    api_key_env: str             # env var name for eval API key
```

Config file format (`prompt-lab.yaml` V2 extension):
```yaml
# V1 fields unchanged
provider: { ... }
run: { ... }

# V2 new
eval:
  enabled: false
  metrics:
    - name: faithfulness
    - name: answer_relevancy
    - name: geval
      params:
        criteria: "Rate on accuracy and completeness (1-10)"
  model: deepseek-chat
  api_key_env: DEEPSEEK_API_KEY
```

Config.load() backward-compatible: returns `EvalConfig(enabled=False, metrics=[], ...)` when no `eval` block.

#### EvalResult (new)

```python
# core/models.py

@dataclass(frozen=True)
class EvalResult:
    """One metric evaluation outcome for one case-version pair."""
    metric_name: str             # e.g. "faithfulness"
    score: float                 # 0.0 - 1.0
    reason: str                  # human-readable explanation (may be empty)
    status: str                  # "pass" | "skipped" | "error"
    error: str | None = None     # error message when status == "error"
```

#### CaseResult (extended)

```python
# V1: CaseResult(case_id, baseline: ExecutionResult, candidate: ExecutionResult)
# V2 extended:

@dataclass(frozen=True)
class CaseResult:
    case_id: str
    baseline: ExecutionResult
    candidate: ExecutionResult
    evaluations: list[EvalResult] = field(default_factory=list)  # V2 new
```

Backward-compatible: V1 `result.json` deserializes with `evaluations` defaulting to empty list.

#### RunResult.summary extension

```json
{
  "summary": {
    "baseline": { "avg_prompt_tokens": 7400, ... },  // V1 unchanged
    "candidate": { "avg_prompt_tokens": 5400, ... },
    "eval_summary": {                                 // V2 new
      "baseline": { "faithfulness": {"avg": 0.82, "count": 3}, "answer_relevancy": {"avg": 0.75, "count": 3} },
      "candidate": { "faithfulness": {"avg": 0.88, "count": 3}, "answer_relevancy": {"avg": 0.71, "count": 3} }
    }
  }
}
```

Empty object `{}` when no eval data.

### §5.3 Storage

No database changes. All data still stored as JSON files in `.prompt-lab/`.

New: `.prompt-lab/web.log` (Web access log, combined log format).

## §6 API Surface

### §6.1 CLI Commands

#### V1 commands (unchanged)

`prompt-lab init`, `add version`, `add case`, `log`, `diff`, `cases list`, `cases import` — signatures identical to V1.

#### `prompt-lab run` (extended)

```
Usage: prompt-lab run --baseline <ver> --candidate <ver> --dataset <collection> [options]

Required:
  --baseline <ver>      Baseline version
  --candidate <ver>     Candidate version
  --dataset <name>      Case collection name

Options:
  --model <model>          Override provider model
  --max-tokens <n>         Override max_tokens
  --thinking <mode>        Override thinking mode (enabled|disabled)
  --concurrency <n>        Concurrent case execution
  --eval                   Enable quality evaluation (V2 new)
```

Without `--eval`, behavior identical to V1.

#### `prompt-lab compare` (extended)

```
Usage: prompt-lab compare <run-id> [--format <table|json>] [--eval-only]

Options:
  --format <type>      Output format: table (default) or json
  --eval-only          Show only evaluation metrics (V2 new)
```

When run results include `evaluations`, report automatically adds quality columns.

#### `prompt-lab serve` (V2 new)

```
Usage: prompt-lab serve [--port <port>] [--host <addr>]

Options:
  --port <n>      Port number (default: 8765)
  --host <addr>   Bind address (default: 127.0.0.1)

Output:
  Prompt Lab Web UI running at http://127.0.0.1:8765
  Press Ctrl+C to stop.
```

### §6.2 REST API (V2 new)

All APIs return JSON. Error response: `{"error": "<code>", "message": "<detail>"}`.

#### Version management

```
GET /api/versions
  → 200: [{ "id": "v2", "timestamp": "...", "author": "ezio", "changed_var": "prompt", "change_note": "...", "content_hash": "sha256:..." }]
```

```
GET /api/versions/{id}
  → 200: { "id": "v2", "prompt_text": "...", "timestamp": "...", ... }
  → 404: { "error": "E_VERSION_NOT_FOUND", "message": "version 'v3' not found" }
```

```
GET /api/versions/{id_a}/{id_b}/diff
  → 200: { "diff": "--- v1\n+++ v2\n@@ ...", "format": "unified" }
  → 404: { "error": "E_VERSION_NOT_FOUND", "message": "..." }
```

```
POST /api/versions
  Body: { "name": "v3", "prompt_text": "You are...", "changed_from": "v2", "changed_var": "prompt", "change_note": "...", "author": "ezio" }
  → 201: { "id": "v3", "content_hash": "sha256:...", "timestamp": "..." }
  → 409: { "error": "E_ALREADY_EXISTS", "message": "version 'v3' already exists" }
```

#### Case management

```
GET /api/cases?collection=<name>&type=<ideal|bad-case>
  → 200: [{ "id": "case-001", "type": "ideal", "collection": "books", "input": {...}, "expected_output": "...", ... }]
```

#### Run management

```
GET /api/runs
  → 200: [{ "run_id": "20260726T...", "baseline_version": "v1", "candidate_version": "v2", "dataset": "books", "timestamp": "...", "has_eval": true }]
```

```
GET /api/runs/{id}
  → 200: { complete RunResult JSON (same as result.json format) }
  → 404: { "error": "E_RUN_NOT_FOUND", "message": "run '...' not found" }
```

```
POST /api/runs
  Body: { "baseline": "v1", "candidate": "v2", "dataset": "books", "eval": true }
  → 200: { complete RunResult JSON }
  → 400: { "error": "E_VERSION_NOT_FOUND" | "E_CASE_NOT_FOUND" | "E_CONFIG_INVALID" }
  → 502: { "error": "E_PROVIDER_TIMEOUT" | "E_PROVIDER_AUTH" }
```

Note: POST `/api/runs` is synchronous — request blocks until run completes. Acceptable for local tool with small case counts (< 20).

#### Configuration

```
GET /api/config
  → 200: {
      "provider": { "base_url": "...", "model": "deepseek-v4-flash", "api_key_env": "DEEPSEEK_API_KEY" },
      "eval": { "enabled": false, "metrics": [...], "model": "deepseek-chat" },
      "run": { "timeout_seconds": 60, "concurrency": 1 }
    }
  Note: api_key value never returned, only api_key_env variable name
```

### §6.3 Internal API (Python module interface)

#### V1 modules (unchanged)

`VersionManager`, `CaseManager`, `Provider` — interfaces identical to V1 Spec §6.2.

#### Evaluator (V2 new)

```python
# core/evaluator.py

class Evaluator:
    """Run DeepEval metrics against prompt outputs."""

    def __init__(
        self,
        eval_config: EvalConfig,
        provider: Provider,          # reuses V1 Provider (OpenAI-compatible)
    ) -> None: ...

    async def evaluate(
        self,
        case: Case,
        baseline_output: str,
        candidate_output: str,
    ) -> list[EvalResult]:
        """Evaluate both baseline and candidate outputs for a case.
        Returns flat list: [EvalResult(baseline), EvalResult(candidate), ...]
        """
        ...
```

#### RunEngine (V1 extended)

```python
# V1: RunEngine.run(baseline_prompt, candidate_prompt, cases) -> RunResult
# V2 extended:

class RunEngine:
    def __init__(
        self,
        provider: Provider,
        config: RunConfig,
        *,
        project_root: Path | None = None,
        evaluator: Evaluator | None = None,   # V2 new, None = no eval
    ) -> None: ...

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
        run_eval: bool = False,               # V2 new
    ) -> RunResult: ...
```

#### ReportBuilder (V1 extended)

```python
class ReportBuilder:
    @staticmethod
    def build_table(run_result: RunResult) -> str: ...  # V2: auto-detect eval data

    @staticmethod
    def build_json(run_result: RunResult) -> str: ...    # V1 unchanged

    @staticmethod
    def build_eval_summary(run_result: RunResult) -> str:
        """Render eval-only summary table (V2 new)."""
        ...
```

#### Web Server (V2 new)

```python
# web/server.py

def create_app(project_root: Path) -> FastAPI:
    """Create FastAPI app with REST API + SPA static files."""
    ...
```

## §7 Error Model

### V1 error codes (unchanged)

`E_VERSION_NOT_FOUND`, `E_CASE_NOT_FOUND`, `E_PROVIDER_TIMEOUT`, `E_PROVIDER_AUTH`, `E_PROVIDER_RATE_LIMIT`, `E_EMPTY_OUTPUT`, `E_CONFIG_INVALID`, `E_ALREADY_EXISTS` — semantics identical to V1.

### V2 new error codes

| Code | Meaning | Retryable | User-facing message |
|------|---------|-----------|---------------------|
| `E_EVAL_NOT_INSTALLED` | `--eval` enabled but DeepEval not installed | No | `Error: evaluation requires DeepEval. Install with: pip install prompt-lab[eval]` |
| `E_EVAL_TIMEOUT` | Evaluation LLM call timeout | No | `Warning: eval timed out for case-001, metric faithfulness. Marked as error.` |
| `E_EVAL_MISSING_EXPECTED` | Metric requires expected_output but case lacks it | No | (Silently skipped, recorded as `skipped`, no error shown) |
| `E_EVAL_INTERNAL` | DeepEval internal exception | No | `Warning: eval error for case-001, metric faithfulness: <detail>` |
| `E_RUN_NOT_FOUND` | Run ID not found | No | `Error: run '<id>' not found.` |

### Propagation rules

- **Evaluation errors do not abort run**: single case's single metric failure (timeout/internal error) → record `EvalResult(status=error)`, continue
- **Evaluation errors do not retry**: unlike Provider retry logic, eval is advisory — one failure marks error
- **DeepEval not installed**: errors at CLI parsing stage (before run starts)
- **Web API errors**: return HTTP status code + JSON error body (§6.2)

## §8 Failure Modes

| Scenario | Detection signal | Recovery |
|----------|-----------------|----------|
| DeepEval package not installed but `--eval` enabled | `ImportError` at evaluator init | CLI errors out, suggests `pip install prompt-lab[eval]` |
| Eval LLM API timeout (single metric) | Eval Provider.call() timeout | Metric marked `EvalResult(status=error)`, run continues |
| Eval LLM returns unparseable result | DeepEval internal `ValueError` / `TypeError` | Metric marked `error`, run continues |
| Web server port occupied | uvicorn startup `OSError: address already in use` | CLI errors out, suggests different port |
| POST /api/runs triggered run partially fails | result.json case has error | API returns 200 + complete result (with error case), not 5xx |
| React build missing (dev mode, not built) | StaticFiles directory missing | FastAPI returns JSON: `{"error": "E_FRONTEND_NOT_BUILT", "message": "Run: cd web/frontend && npm run build"}` |
| V1 result.json read (backward compat) | `evaluations` field absent | `CaseResult` constructed with `evaluations` defaulting to empty list |

## §9 Performance Budget

| Metric | Target | Measurement |
|--------|--------|-------------|
| Web UI page load (first) | p95 < 500ms | Browser DevTools Network |
| Web UI page load (SPA route change) | p95 < 50ms | DevTools (pure frontend render) |
| REST API GET endpoint | p95 < 100ms | FastAPI middleware records `duration_ms` |
| REST API POST /api/runs | Depends on LLM calls | Same as V1 run performance |
| DeepEval single-metric eval | p95 < 30s, timeout 30s | EvalResult recorded `duration_ms` |
| 10 case × 3 metric eval | < 10 min (serial) | run_completed.duration_ms |
| Eval API cost (10 case × 2 versions × 3 metrics) | < $0.30 | Eval LLM `prompt_tokens` × pricing |
| Web server memory | < 100MB | `ps aux` |

## §10 Security & Privacy

### Authentication

**No application-layer auth.** Web server binds to `127.0.0.1` only, accessible from localhost.

### Authorization

| Role | Can access | Cannot access |
|------|-----------|---------------|
| Local user | All CLI commands + Web UI + all API endpoints | — |

No RBAC. Tool assumes the user is the machine owner.

### Sensitive data

| Data | Sensitivity | Protection |
|------|------------|------------|
| API key (generation + eval) | High | Read from env var only. Web API returns `api_key_env` variable name, **never the value** |
| Prompt content | Medium | Local storage. Web access log records request paths, **not request bodies** |
| Run results | Medium | Local storage, `.prompt-lab/runs/` in `.gitignore` by default |
| Case inputs | Low | Local storage |
| Eval results | Low | Local storage |

### Audit

- Web server access log: `.prompt-lab/web.log` (combined log format), records method/path/status/duration, **no request body**
- Version registration and run trigger events written to `events.jsonl`
- All audit data local, retention managed by user

## §11 Open Questions

| # | Question | Decision | Deadline |
|---|----------|----------|----------|
| 1 | How does DeepEval's GEval metric accept custom criteria? | **Decision**: Passed via `EvalMetricConfig.params` dict with `criteria` string. Evaluator passes it when constructing DeepEval `GEval` instance. Need to verify DeepEval API parameter name during implementation. | At spec sign-off ✅ (verify during impl) |
| 2 | POST /api/runs synchronous blocking vs async polling? | **Decision**: V2 uses synchronous blocking. Case count < 20, LLM calls < 5 min, HTTP timeout 10 min. Async polling adds complexity (job queue + status query), not in V2. Re-evaluate if case scale > 50. | 2026-07-26 ✅ |
| 3 | How to distribute React SPA build output? | **Decision**: `web/frontend/dist/` directory generated by `npm run build`, committed to git. FastAPI serves via `StaticFiles`. Users don't need Node.js (unless developing frontend). Dev uses Vite dev server proxy. | 2026-07-26 ✅ |
| 4 | Does eval model reuse generation Provider's API key? | **Decision**: Independently configured `eval.api_key_env`. Users can configure same env var (reuse key) or different (independent key). Defaults to same as provider's `api_key_env`. | 2026-07-26 ✅ |

## §12 References

- **Positioning Memo**: [prompt_lab_positioning_v1.0_2026-07-25.en.md](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.en.md)
- **PRD v2.0**: [prompt_lab_prd_v2.0_2026-07-26.en.md](../01-prd/prompt_lab_prd_v2.0_2026-07-26.en.md)
- **Previous Spec v1.0**: [prompt_lab_spec_v1.0_2026-07-25.en.md](./prompt_lab_spec_v1.0_2026-07-25.en.md)
- **External standards**:
  - [DeepEval docs](https://docs.confident-ai.com/) — evaluation metric API
  - [FastAPI docs](https://fastapi.tiangolo.com/) — web framework
  - [Vite docs](https://vitejs.dev/) — frontend build tool
  - [DeepSeek API Docs](https://api-docs.deepseek.com/) — provider parameters
- **Kanban**: github.com/Ezio0/prompt-lab

---

Sign-off: Pending Ezio review
