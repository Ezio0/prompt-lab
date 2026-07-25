# Prompt Lab PRD v2.0

**Project**: Prompt Lab
**Date**: 2026-07-26
**Version**: v2.0
**Positioning**: [prompt_lab_positioning_v1.0_2026-07-25.en.md](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.en.md)
**Previous PRD**: [prompt_lab_prd_v1.0_2026-07-25.en.md](./prompt_lab_prd_v1.0_2026-07-25.en.md)

---

## §1 Product Context

V1 delivered the infrastructure for prompt version management and A/B execution. But V1's comparison report only answered two questions: did tokens get cheaper? Is it faster? It did not answer the most important third question: **is the new version's output quality actually good?**

This gap was explicitly identified in the Positioning's UNDERLYING LOGIC: "The core is to transform 'did the prompt change make things better or worse' from subjective feeling to data-driven judgment." V1 achieved structured comparison, but quality dimension still relied on eyeballing.

V2's two tracks both serve the same goal — **making the loop complete**:

1. **Quality Evaluation**: Integrate DeepEval's 50+ metrics into the A/B comparison workflow, so reports include quantified quality scores (faithfulness, answer relevancy, etc.). Positioning already stated: "DeepEval has 50+ metrics, just use them. What we do is wrap evaluation into the comparison workflow."

2. **Web UI**: V1's PRD §2 already listed PM/operations as v2 target users. They don't write code but need to adjust prompt text and view comparison results. CLI cannot serve them.

## §2 Target Users

References [Positioning Memo §WHO](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.en.md#who).

| Role | Description | v2 Target |
|------|-------------|-----------|
| **Developer** | CLI user already using V1. | ✅ Quality evaluation, via CLI |
| **PM / Operations** | Non-coders who need to adjust prompt text and view comparison results. Need Web UI to modify prompts and view reports. | ✅ Web UI |

## §3 User Stories

### US-7: Run A/B Comparison with Quality Evaluation

> As a developer, I want to automatically evaluate output quality (faithfulness, answer relevancy, etc.) in A/B comparisons, so I can use data to determine if the new prompt version's quality degraded.

Acceptance criteria:
- [ ] `prompt-lab run` adds `--eval` flag; when enabled, executes DeepEval evaluation for each case
- [ ] Supports configuring evaluation metric list and parameters in `prompt-lab.yaml`
- [ ] Metrics supported at minimum: Faithfulness, Answer Relevancy, GEval (custom scoring criteria)
- [ ] Evaluation requires case `expected_output` (ideal-state output) as ground truth
- [ ] Cases without `expected_output` skip metrics requiring ground truth, recorded as `skipped`
- [ ] Each case's evaluation result includes: metric name, score (0-1), optional reason
- [ ] Evaluation failure does not abort A/B run (degrades to `eval_error` marker)

### US-8: View Comparison Report with Quality Scores

> As a developer, I want the comparison report to include quality evaluation scores, so I can see both operational metrics (tokens/latency) and quality metrics (faithfulness, etc.) together.

Acceptance criteria:
- [ ] `prompt-lab compare <run-id>` report adds quality metric columns
- [ ] Terminal table mode: each case shows baseline vs candidate quality scores
- [ ] JSON mode: includes complete evaluation results (score + reason)
- [ ] Summary statistics add `avg_<metric>` rows (one set each for baseline and candidate)
- [ ] Supports `--eval-only` parameter to output only quality metrics (hide tokens/latency)

### US-9: View Prompt Versions via Web UI

> As a PM/operations, I want to view all prompt versions and their content in a browser, so I can understand the iteration history.

Acceptance criteria:
- [ ] `prompt-lab serve` starts web server (default http://localhost:8765)
- [ ] Version list page: reverse chronological list of all versions, with hash, time, author, change note
- [ ] Version detail page: full prompt content with monospace rendering
- [ ] Version comparison page: side-by-side diff of two versions
- [ ] Page load time < 500ms (local data, no network requests)

### US-10: View A/B Comparison Report via Web UI

> As a PM/operations, I want to view A/B comparison reports in a browser, so I can intuitively understand the performance difference between two versions.

Acceptance criteria:
- [ ] Run list page: reverse chronological list of all runs, with version pair, case count, run time
- [ ] Run detail page: comparison report with operational metrics (tokens/latency) and quality metrics (eval scores)
- [ ] Per-case comparison view: baseline vs candidate output side-by-side, quality scores highlighted
- [ ] Summary statistics chart: bar chart comparing baseline and candidate key metrics
- [ ] Supports JSON download (export complete run results)

### US-11: Edit and Register Prompt via Web UI

> As a PM/operations, I want to edit prompt text in a browser and register it as a new version, so I can iterate without depending on developers.

Acceptance criteria:
- [ ] Version editor: monospace textarea with variable placeholder hints (`{variable_name}`)
- [ ] Registration fields: version name, change note, change type (prompt/model/params/data)
- [ ] Pre-registration preview: shows diff against previous version
- [ ] On successful registration, redirects to version list page with new version highlighted
- [ ] Cannot overwrite existing versions (consistent with CLI, immutability constraint)

### §3.x Critical User Journeys (CUJ)

| CUJ ID | Description | Modules | Priority |
|--------|-------------|---------|----------|
| CUJ-4 | init → add version → add case (with expected_output) → run --eval → compare (with quality scores) | CLI + DeepEval integration | P0 |
| CUJ-5 | serve → open browser → view version list → view version detail → view run report | Web UI (read-only) | P0 |
| CUJ-6 | serve → edit prompt → preview diff → register new version → trigger run → view report | Web UI (read-write) | P1 |

## §4 Functional Requirements

### FR-8: Evaluation Configuration

`prompt-lab.yaml` adds `eval` config block:

```yaml
eval:
  enabled: false           # off by default, enabled via run --eval
  metrics:
    - name: faithfulness
    - name: answer_relevancy
    - name: geval
      params:
        criteria: "Rate the response on accuracy and completeness (1-10)"
  model: deepseek-chat     # LLM model used for evaluation (can differ from generation model)
  api_key_env: DEEPSEEK_API_KEY  # API key env var name for eval model
```

### FR-9: Quality Evaluation Engine

New module `prompt_lab/core/evaluator.py`:

- `Evaluator` class: accepts `(input, actual_output, expected_output, context)` + metric list, returns `EvalResult` list
- Each metric returns: `metric_name`, `score` (0.0-1.0), `reason` (str, optional), `status` (`pass` / `skipped` / `error`)
- `skipped`: case missing `expected_output` but metric requires it
- `error`: DeepEval internal exception (e.g. API timeout), does not abort run
- Evaluation LLM calls reuse V1's Provider adapter (OpenAI-compatible format)
- Evaluation model can differ from generation model (separate `eval.model` config)

### FR-10: Evaluation Result Storage

- `CaseResult` extended: new `evaluations` field (`list[EvalResult]`), populated only when `--eval` enabled
- `RunResult.summary` extended: new `eval_summary` block with per-metric average scores
- `result.json` structure backward-compatible: `evaluations` is empty list when no eval data
- `events.jsonl` adds `eval_completed` / `eval_skipped` / `eval_failed` events

### FR-11: Comparison Report Extension

- `ReportBuilder.build_table()` adds evaluation metric columns (when run includes eval data)
- `ReportBuilder.build_json()` includes complete evaluation results
- New `build_eval_summary()`: outputs evaluation metric summary table

### FR-12: Web API Service Layer

New `prompt_lab/web/` subpackage:

- `prompt-lab serve [--port 8765]` starts FastAPI server
- REST API endpoints:
  - `GET /api/versions` — version list
  - `GET /api/versions/{id}` — version detail
  - `GET /api/versions/{id_a}/{id_b}/diff` — version diff
  - `POST /api/versions` — register new version
  - `GET /api/cases` — case list (supports `?collection=` and `?type=` filters)
  - `GET /api/runs` — run list
  - `GET /api/runs/{id}` — run detail (with complete comparison report)
  - `POST /api/runs` — trigger new run (returns result synchronously)
  - `GET /api/config` — current project config
- API key not exposed through API (returns `***`)
- CORS: localhost only by default

### FR-13: React SPA Frontend

New `web/frontend/` directory:

- **Stack**: React + Vite + TypeScript + TailwindCSS
- **Pages**:
  - `/versions` — version list + version detail + diff comparison
  - `/runs` — run list + run report detail
  - `/editor` — prompt editor (register new version)
- **Components**:
  - `<VersionList />` — version list table
  - `<PromptViewer />` — prompt content display (monospace)
  - `<DiffViewer />` — side-by-side diff (based on react-diff-viewer)
  - `<RunReport />` — A/B comparison report (table + summary cards)
  - `<EvalScoreCard />` — quality evaluation score card
  - `<PromptEditor />` — prompt editor + registration form
  - `<MetricChart />` — metric comparison bar chart (based on recharts)
- FastAPI also serves SPA static files (build output), single-port deployment

## §5 Non-Functional Requirements

References [Positioning §WHY NOW](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.en.md#why-now).

| Dimension | Requirement |
|-----------|-------------|
| Performance | Web UI page load < 500ms. API response < 100ms (local data). Triggering run: API processes asynchronously, supports progress polling. DeepEval single-metric evaluation timeout 30s. |
| Security | Web server binds to `127.0.0.1` by default. API key not returned through API. Web UI does not transmit API key to frontend. POST `/api/runs` requires prompt versions to exist. |
| Privacy | All data remains local. Web server sends no data externally. DeepEval evaluation via user-configured LLM API, not through third parties. |
| Extensibility | Evaluation metrics pluggable (V2 supports DeepEval, future can add custom evaluators). Web API stays RESTful, easy to extend. |
| Observability | Web server outputs access log. All API calls recorded to `.prompt-lab/web.log`. |
| Rollback | V2 does not modify V1's storage format (extends only). Without `--eval`, behavior identical to V1. `prompt-lab serve` is optional, does not affect CLI. |

## §6 Data Migration

**No schema migration.**

V2 makes **backward-compatible extensions** to V1's `result.json` structure:
- `CaseResult` adds `evaluations` field, defaults to empty list
- V1's `result.json` can be read normally by V2 (`evaluations` auto-populated as empty list)
- V2's `result.json` includes `evaluations`; V1 ignores the field when reading

**Migration strategy**: none needed. V1 users upgrading to V2 see historical run comparison reports as normal, just without evaluation columns.

## §7 Data Observability

Data produced by Prompt Lab (for user analysis):

**New data flows (V2)**:

- **Evaluation results**: each `--eval` run generates structured evaluation data with per-case per-metric scores and reasons
- **Web access logs**: API call records for audit

Example queries:
```bash
# Find cases where faithfulness score is below 0.7
jq '.cases[] | select(.evaluations[]?.metric_name == "faithfulness" and .evaluations[]?.score < 0.7) | .case_id' \
  .prompt-lab/runs/<run-id>/result.json

# Compare baseline and candidate average faithfulness
jq '.summary.eval_summary | {baseline: .baseline.faithfulness.avg, candidate: .candidate.faithfulness.avg}' \
  .prompt-lab/runs/<run-id>/result.json
```

## §8 Frontend Changes

**V2 introduces frontend for the first time.**

### Component inventory

| Page | Core component | UX notes |
|------|---------------|----------|
| Version list | `<VersionList />` | Table: version name, time, author, change type, change note. Click row for detail. |
| Version detail | `<PromptViewer />` | Monospace prompt content rendering. Variable placeholders `{xxx}` highlighted. |
| Version comparison | `<DiffViewer />` | Side-by-side diff. Changed lines marked red/green. |
| Run list | `<RunList />` | Table: run ID, version pair, case count, has eval, time. Click row for report. |
| Run report | `<RunReport />` | Summary cards (tokens/latency/quality scores) + per-case table + output comparison. |
| Quality score | `<EvalScoreCard />` | One card per metric: score (0-1), status (pass/skipped/error), reason collapsible. |
| Prompt editor | `<PromptEditor />` | Monospace textarea + variable hints + registration form. Preview diff before confirming. |

### UX copy

- Empty state (no versions): `No versions yet. Run: prompt-lab add version <name> --file prompt.txt`
- Empty state (no runs): `No runs yet. Run: prompt-lab run --baseline <v1> --candidate <v2> --dataset <cases>`
- Eval skip notice: `Skipped: requires expected_output (define in case)`
- Eval error notice: `Eval error: <error message> (non-blocking)`
- Registration confirm: `Register version "{name}"? This cannot be undone.`
- Run trigger confirm: `Run A/B comparison: {baseline} vs {candidate} on {dataset}?`

### Timezone handling

- All timestamps use ISO 8601 UTC (consistent with V1)
- Web UI converts to browser local timezone for display
- API returns UTC ISO strings, frontend handles formatting

## §9 Risks

| Risk | Level | Mitigation |
|------|-------|------------|
| DeepEval dependency heavy (complex install, version conflicts) | Medium | Evaluation is optional dependency (`pip install prompt-lab[eval]`). Without eval dependency, `--eval` errors with install hint. |
| DeepEval eval results unstable (LLM-as-judge variance) | Medium | Eval model defaults temperature=0. Docs recommend multiple runs for average. Results labeled `advisory` not `deterministic`. |
| Web UI dev cycle long, blocks V2 release | Medium | Web UI delivered in two phases: P1 read-only (view versions and reports), P2 read-write (edit and trigger runs). Read-only already serves PM/operations core needs. |
| React build integration with FastAPI complex | Low | FastAPI uses `StaticFiles` to serve Vite build output. Dev: Vite proxy forwards API requests to FastAPI. |
| Eval LLM call cost (per case × per metric) | Medium | Docs note cost estimates. Support configuring eval to run only on bad-cases. |

## §10 Non-Goals

1. **No automatic prompt optimization (still not)** — V2 adds quality evaluation capability but does not auto-search or generate "better" prompts. Auto-optimization is a future direction, but requires V2's evaluation infrastructure as foundation. References [Positioning §ANTI-POSITIONING](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.en.md#anti-positioning).

2. **No user authentication / multi-user** — V2's Web UI is a single-user local tool. No login, permissions, multi-user. The tool runs on the developer's local machine; the user is the developer. Multi-user collaboration is a future SaaS direction, not in scope.

3. **No custom evaluation metrics** — V2 integrates DeepEval's existing 50+ metrics. Does not build custom evaluation metric engine (reuse DeepEval). Future: may support custom evaluator interface.

4. **No CI/CD integration** — V2 does not provide GitHub Actions integration, PR check, automatic gating. These are future directions (competing with Confident AI's eval-as-merge-gate), but need to first validate core value of local CLI + Web UI.

5. **No online observability / trace monitoring (still not)** — References Positioning §ANTI-POSITIONING. We focus on pre-launch decisions, not online monitoring.

## §11 Acceptance Criteria

### Functional
- [ ] `prompt-lab run --eval` executes configured DeepEval evaluation metrics for each case
- [ ] `prompt-lab compare <run-id>` report includes quality evaluation columns
- [ ] `prompt-lab serve` starts web server, accessible via browser
- [ ] Web UI version list + version detail + diff comparison work correctly
- [ ] Web UI Run report page shows comparison report with quality scores
- [ ] Web UI Prompt editor can register new versions

### Performance
- [ ] Web UI page load < 500ms
- [ ] API response < 100ms (excluding LLM calls)
- [ ] DeepEval single-metric evaluation completes within 30s or times out

### Compatibility
- [ ] V1's `result.json` can be read normally by V2
- [ ] Without `--eval` flag, behavior identical to V1
- [ ] When `prompt-lab serve` is not running, all CLI commands work normally

### Testing
- [ ] Evaluation engine unit test coverage ≥ 80%
- [ ] Web API endpoint test coverage ≥ 80%
- [ ] CUJ-4 (CLI + eval) end-to-end test
- [ ] CUJ-5 (Web read-only) end-to-end test

### Rollback
- [ ] Evaluation is optional dependency, uninstall does not affect core functionality
- [ ] Web server is optional, not starting it does not affect CLI

## §12 Observability Requirements

### §12.1 New Events

Prompt Lab is a CLI + Web tool; "events" are stored as run logs and web access logs.

**Evaluation events** (written to `events.jsonl`):

| Event | Trigger | Key fields | Purpose | Priority |
|-------|---------|------------|---------|----------|
| `eval_started` | Evaluation engine begins processing a case's metric | case_id, metric_name, timestamp | Audit | P0 |
| `eval_completed` | Single metric evaluation succeeded | case_id, version, metric_name, score, reason, duration_ms | Comparison data | P0 |
| `eval_skipped` | Metric skipped (missing expected_output, etc.) | case_id, version, metric_name, reason | Diagnosis | P1 |
| `eval_failed` | Evaluation failed (API error, etc.) | case_id, version, metric_name, error_type, error_message | Diagnosis | P0 |

**Web service events** (written to `.prompt-lab/web.log`):

| Event | Trigger | Key fields | Purpose | Priority |
|-------|---------|------------|---------|----------|
| `api_request` | Each API request | method, path, status_code, duration_ms, client_ip | Audit | P1 |
| `web_run_triggered` | Run triggered via Web UI | baseline_version, candidate_version, dataset, eval_enabled | Audit | P1 |
| `web_version_registered` | Version registered via Web UI | version_id, changed_var, author | Audit | P1 |

### §12.2 Reused Events

Extends V1's `run_completed` event:
- New `eval_enabled` field (bool): whether this run enabled evaluation
- New `eval_metrics` field (list[str]): list of executed metric names
- New `eval_success_count` / `eval_skip_count` / `eval_fail_count` fields

### §12.3 Event Schema

All events still stored as JSONL files (`.prompt-lab/runs/<run-id>/events.jsonl`), no database schema changes.

Web log is standard HTTP access log format (combined log format), written to `.prompt-lab/web.log`.

### §12.4 Acceptance Criteria

- [ ] Each `--eval` run generates complete evaluation events (`eval_completed` / `eval_skipped` / `eval_failed` covering 100% of case × metric combinations)
- [ ] `run_completed` event includes evaluation summary fields (when `eval_enabled=true`)
- [ ] Web server running: `web.log` continuously written
- [ ] Actions triggered via Web UI (run / register) have corresponding audit events

### §12.5 Privacy Considerations

- Prompt content may contain user data, stored locally in `.prompt-lab/`
- Web server binds only to `127.0.0.1`, not exposed to network
- Web access log records request paths but not request bodies (prompt content not in access log)
- API key read from environment variable, not written to any file, not returned through API
- DeepEval evaluation via user-configured LLM API; evaluation inputs (prompt + output) sent to user's LLM provider, not through third parties

## §13 Links

- **Positioning Memo**: [prompt_lab_positioning_v1.0_2026-07-25.en.md](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.en.md)
- **Previous PRD**: [prompt_lab_prd_v1.0_2026-07-25.en.md](./prompt_lab_prd_v1.0_2026-07-25.en.md)
- **Previous Spec**: [prompt_lab_spec_v1.0_2026-07-25.en.md](../02-spec/prompt_lab_spec_v1.0_2026-07-25.en.md)
- **Kanban**: github.com/Ezio0/prompt-lab (public repo, uses GitHub Issues for task management)
- **Framework**: Prompt Lab v2.0

---

Sign-off: Pending Ezio review
