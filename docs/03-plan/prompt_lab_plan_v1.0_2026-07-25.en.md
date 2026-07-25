# Prompt Lab Implementation Plan

**Project**: Prompt Lab
**Date**: 2026-07-25
**Version**: v1.0
**Spec**: [prompt_lab_spec_v1.0_2026-07-25.en.md](../02-spec/prompt_lab_spec_v1.0_2026-07-25.en.md)
**PRD**: [prompt_lab_prd_v1.0_2026-07-25.en.md](../01-prd/prompt_lab_prd_v1.0_2026-07-25.en.md)

---

## §1 Overview

References [Spec §1 Overview](../02-spec/prompt_lab_spec_v1.0_2026-07-25.en.md#1-overview).

This plan breaks down the 7 modules from the Spec into independently executable Tasks, ordered by dependency.

## §2 Phases

| Phase | Goal | Tasks |
|-------|------|-------|
| **P0: Project scaffold** | Python project structure, dependency management, CLI entry skeleton | T-001 |
| **P1: Core data layer** | Config + Version Manager + Case Manager | T-002, T-003, T-004 |
| **P2: Execution layer** | Provider Adapter + Run Engine | T-005, T-006 |
| **P3: Reporting layer** | Report Builder + compare command | T-007 |
| **P4: Integration** | CLI full chain, end-to-end tests | T-008 |

## §3 Task Breakdown

### T-001: Project scaffold (P0, XS)

**Depends on**: None

**Description**: Set up Python project structure, pyproject.toml, CLI entry point.

**Acceptance criteria**:
- [ ] `pyproject.toml` configured (name=prompt-lab, Python ≥3.11)
- [ ] Dependencies: `click` (CLI), `httpx` (HTTP), `pyyaml` (config), `rich` (terminal table)
- [ ] `prompt_lab/` package structure: `__init__.py`, `cli.py`, `core/` subpackage
- [ ] `prompt-lab --help` outputs help info
- [ ] `prompt-lab init` creates `.prompt-lab/` directory + `prompt-lab.yaml`
- [ ] Unit test: test_init.py

**Files**:
```
prompt-lab/
├── pyproject.toml
├── prompt_lab/
│   ├── __init__.py
│   ├── cli.py           # Click CLI entry point
│   └── core/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   └── unit/
│       ├── __init__.py
│       └── test_init.py
└── (existing docs/)
```

### T-002: Config module (P1, S)

**Depends on**: T-001

**Description**: Read and validate `prompt-lab.yaml` configuration.

**Acceptance criteria**:
- [ ] `Config.load()` reads `prompt-lab.yaml` from project root
- [ ] Returns typed config object (dataclass): provider settings, run settings
- [ ] API key read from environment variable (`api_key_env` field names the variable)
- [ ] Missing or malformed config raises `E_CONFIG_INVALID`
- [ ] Unit test: test_config.py (valid config, missing file, invalid yaml, missing api key)

**Files**: `prompt_lab/core/config.py`, `tests/unit/test_config.py`

### T-003: Version Manager (P1, M)

**Depends on**: T-001

**Description**: Prompt version registration, storage, query, diff.

**Acceptance criteria**:
- [ ] `add_version()` writes JSON to `.prompt-lab/versions/<name>.json`
- [ ] Computes content_hash (SHA-256)
- [ ] Duplicate version name raises `E_ALREADY_EXISTS`
- [ ] `get_version()` reads and returns Version object
- [ ] `list_versions()` returns reverse chronological list
- [ ] `diff()` outputs unified diff format
- [ ] Versions are immutable (existing versions cannot be overwritten)
- [ ] Unit test: test_version_manager.py (add, get, list, diff, duplicate, immutability)

**Files**: `prompt_lab/core/version_manager.py`, `prompt_lab/core/models.py` (Version dataclass), `tests/unit/test_version_manager.py`

### T-004: Case Manager (P1, S)

**Depends on**: T-001

**Description**: Case CRUD, grouping, bulk import.

**Acceptance criteria**:
- [ ] `add_case()` writes JSON to `.prompt-lab/cases/<collection>/<id>.json`
- [ ] `get_cases()` reads by collection, filterable by type
- [ ] `import_cases()` bulk import from JSON file (array format)
- [ ] Case type validation: must be `ideal` or `bad-case`
- [ ] Unit test: test_case_manager.py (add, get, filter, import, invalid type)

**Files**: `prompt_lab/core/case_manager.py`, `prompt_lab/core/models.py` (Case dataclass), `tests/unit/test_case_manager.py`

### T-005: Provider Adapter (P2, S)

**Depends on**: T-002

**Description**: OpenAI-compatible API call wrapper.

**Acceptance criteria**:
- [ ] `Provider.call()` sends POST to `/chat/completions`
- [ ] Supports params: model, max_tokens, temperature, thinking mode
- [ ] Returns ProviderResponse (content, prompt_tokens, completion_tokens, finish_reason)
- [ ] HTTP 401 → raise ProviderAuthError (not retryable)
- [ ] HTTP 429 → raise ProviderRateLimitError (retryable)
- [ ] Timeout → raise ProviderTimeoutError (retryable)
- [ ] Other HTTP 5xx → raise ProviderError (retryable)
- [ ] Unit test: test_provider.py (mock httpx, all status code paths)

**Files**: `prompt_lab/core/provider.py`, `prompt_lab/core/models.py` (ProviderResponse), `tests/unit/test_provider.py`

### T-006: Run Engine (P2, M)

**Depends on**: T-003, T-004, T-005

**Description**: A/B comparison execution engine.

**Acceptance criteria**:
- [ ] `RunEngine.run()` takes baseline_prompt, candidate_prompt, cases list
- [ ] For each case: render prompt with `str.format()` → call Provider → record metrics
- [ ] Records: output, prompt_tokens, completion_tokens, latency_ms, finish_reason, error
- [ ] Single case failure does not abort run
- [ ] Provider timeout/rate-limit retries 3 times with exponential backoff
- [ ] Results written to `.prompt-lab/runs/<run-id>/result.json`
- [ ] events.jsonl written alongside
- [ ] Returns RunResult object with summary stats on completion
- [ ] Unit test: test_run_engine.py (mock provider, normal/failure/retry/empty output)

**Files**: `prompt_lab/core/run_engine.py`, `prompt_lab/core/models.py` (RunResult, CaseResult), `tests/unit/test_run_engine.py`

### T-007: Report Builder (P3, S)

**Depends on**: T-006

**Description**: Generate comparison report from RunResult.

**Acceptance criteria**:
- [ ] `build_table()` uses rich library for terminal table output
- [ ] Table includes: per-case token/latency comparison + summary stats
- [ ] `build_json()` outputs complete JSON
- [ ] Summary metrics: avg_prompt_tokens, avg_latency_ms, non_empty_rate, error_rate
- [ ] Delta columns show percentage change
- [ ] Unit test: test_report.py (table output, json output, empty results)

**Files**: `prompt_lab/core/report.py`, `tests/unit/test_report.py`

### T-008: CLI Integration + E2E (P4, M)

**Depends on**: T-003, T-004, T-006, T-007

**Description**: Wire all modules into CLI commands, end-to-end tests.

**Acceptance criteria**:
- [ ] `prompt-lab add version` → calls VersionManager
- [ ] `prompt-lab log` → formatted version list output
- [ ] `prompt-lab diff` → unified diff output
- [ ] `prompt-lab add case` → calls CaseManager
- [ ] `prompt-lab cases list` → formatted case list output
- [ ] `prompt-lab run` → calls RunEngine, outputs run summary
- [ ] `prompt-lab compare` → calls ReportBuilder
- [ ] E2E test covers CUJ-1: init → add version → add case → run → compare
- [ ] All command error paths have friendly messages

**Files**: `prompt_lab/cli.py` (extend), `tests/unit/test_cli.py`, `tests/integration/test_e2e.py`

## §4 Dependency Graph

```
T-001 (scaffold)
  ├── T-002 (config)
  │     └── T-005 (provider)
  ├── T-003 (version manager)
  ├── T-004 (case manager)
  └── T-006 (run engine) ←── T-003 + T-004 + T-005
        └── T-007 (report)
              └── T-008 (CLI integration) ←── T-003 + T-004 + T-006 + T-007
```

No cyclic dependencies. T-001 is prerequisite for all tasks.

## §5 Execution Strategy

- Implementation: **Codex CLI**
- Run corresponding unit tests after each Task
- Run full test suite after T-008
- Commit + push after full suite passes

## §6 Estimates

| Task | Size | Estimated Time |
|------|------|---------------|
| T-001 | XS | 15 min |
| T-002 | S | 20 min |
| T-003 | M | 40 min |
| T-004 | S | 20 min |
| T-005 | S | 20 min |
| T-006 | M | 40 min |
| T-007 | S | 20 min |
| T-008 | M | 30 min |
| **Total** | | **~3.5 hours** |

## §7 Risks

| Risk | Mitigation |
|------|------------|
| Codex unfamiliar with pyproject.toml + Click integration | Spec §6 has complete interface signatures, Codex follows them |
| Run Engine asyncio logic complexity | T-006 split into render + call + record steps, each independently testable |

## §8 Definition of Done

- [ ] All 8 Tasks' acceptance criteria checked off
- [ ] Full test suite passes (unit + integration)
- [ ] `prompt-lab --help` outputs complete command list
- [ ] CUJ-1 end-to-end executable
- [ ] Committed + pushed to main

## §9 History

| Date | Event |
|------|-------|
| 2026-07-25 | Initial creation |

---

Sign-off: Pending Ezio review
