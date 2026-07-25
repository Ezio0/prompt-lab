# Prompt Lab Technical Spec

**Project**: Prompt Lab
**Date**: 2026-07-25
**Version**: v1.0
**PRD**: [prompt_lab_prd_v1.0_2026-07-25.en.md](../01-prd/prompt_lab_prd_v1.0_2026-07-25.en.md)
**Positioning**: [prompt_lab_positioning_v1.0_2026-07-25.en.md](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.en.md)

---

## §1 Overview

Prompt Lab is a local CLI tool that lets developers turn prompt iteration from guesswork into controlled experimentation: register versions, define cases, run A/B comparisons, and make data-driven decisions on whether to ship.

**Consumers**: Developers (via terminal CLI)

**System Context**:

```
┌─────────────────────────────────────────────────────┐
│                   Developer Terminal                  │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │              prompt-lab CLI                       │ │
│  │                                                   │ │
│  │  ┌──────────┐  ┌──────────┐  ┌───────────────┐ │ │
│  │  │ Version  │  │  Case    │  │  A/B Run      │ │ │
│  │  │ Manager  │  │ Manager  │  │  Engine       │ │ │
│  │  └────┬─────┘  └────┬─────┘  └──────┬────────┘ │ │
│  │       │              │               │          │ │
│  │       └──────────────┴───────────────┘          │ │
│  │                      │                           │ │
│  │              ┌───────┴────────┐                  │ │
│  │              │ Report Builder │                  │ │
│  │              └────────────────┘                  │ │
│  └──────────────────────┬──────────────────────────┘ │
│                         │                             │
│          ┌──────────────┴──────────────┐              │
│          │    .prompt-lab/ (local)     │              │
│          │  ├── versions/              │              │
│          │  ├── cases/                 │              │
│          │  ├── runs/                  │              │
│          │  └── prompt-lab.yaml        │              │
│          └─────────────────────────────┘              │
└─────────────────────────────────────────────────────┘
                          │
                          │ HTTP (OpenAI-compatible API)
                          ▼
          ┌─────────────────────────────┐
          │     LLM Provider (external)  │
          │  OpenAI / DeepSeek / vLLM    │
          └─────────────────────────────┘
```

## §2 Goals

References [PRD §4 Functional Requirements](../01-prd/prompt_lab_prd_v1.0_2026-07-25.en.md#4-functional-requirements).

1. **Version management**: Each prompt change registered as an immutable version, with diff and history support
2. **Case management**: Ideal-state cases and bad cases, with grouping and bulk import
3. **A/B comparison**: Run two versions against the same case set in parallel, recording full metrics (tokens, latency, output)
4. **Comparison report**: Terminal table + JSON dual-mode output, per-case diff + summary statistics
5. **Provider adapter**: v1 supports OpenAI-compatible API, configurable model / params / thinking mode

## §3 Non-Goals

Mirrors [PRD §10 Non-Goals](../01-prd/prompt_lab_prd_v1.0_2026-07-25.en.md#10-non-goals).

1. No prompt auto-optimization (see PRD §10.1)
2. No production observability / trace monitoring (see PRD §10.2)
3. No custom evaluation metric engine (see PRD §10.3)
4. No Web UI (see PRD §10.4)
5. No prompt hosting / registry service (see PRD §10.5)

## §4 Architecture

### §4.1 Components

| Component | Responsibility | Owns Data |
|-----------|---------------|-----------|
| **CLI Entry** (`cli/`) | Command parsing, arg validation, core module dispatch, output formatting | None |
| **Version Manager** (`core/version_manager.py`) | Version registration, storage, query, diff | `.prompt-lab/versions/` |
| **Case Manager** (`core/case_manager.py`) | Case CRUD, grouping, import | `.prompt-lab/cases/` |
| **Run Engine** (`core/run_engine.py`) | A/B execution: render prompt → call LLM → record metrics | `.prompt-lab/runs/` |
| **Provider Adapter** (`core/provider.py`) | OpenAI-compatible API calls, param packaging, error handling | None |
| **Report Builder** (`core/report.py`) | Generate comparison reports from run results (table + JSON) | None |
| **Config** (`core/config.py`) | Read `prompt-lab.yaml`, parse provider settings | `prompt-lab.yaml` |

### §4.2 Data Flow

```
User runs: prompt-lab run --baseline v1 --candidate v2 --dataset books

CLI Entry
  │
  ├─→ Config.load() → provider settings, default params
  │
  ├─→ Version Manager: get v1 prompt, get v2 prompt
  │
  ├─→ Case Manager: load cases from dataset "books"
  │
  ├─→ Run Engine:
  │     │
  │     │  for each case:
  │     │    ├─→ render v1 prompt with case.input → call Provider → record result_A
  │     │    └─→ render v2 prompt with case.input → call Provider → record result_B
  │     │
  │     └─→ write results to .prompt-lab/runs/<run-id>/
  │
  └─→ Report Builder: read run results → output table/JSON
```

### §4.3 Deployment Topology

| Component | Runtime |
|-----------|---------|
| CLI + Core | User's local terminal (Python process) |
| `.prompt-lab/` | User's project directory (local filesystem) |
| LLM Provider | External HTTP API |

No server-side components. All logic runs on the user's machine.

## §5 Data Model

All data stored as files under `.prompt-lab/`. No database.

### §5.1 Version

```json
{
  "id": "v2",
  "content_hash": "sha256:abc123...",
  "prompt_text": "You are EgoZone's discovery engine...",
  "timestamp": "2026-07-25T10:00:00Z",
  "author": "ezio",
  "changed_from": "v1",
  "changed_var": "prompt",
  "change_note": "Simplified theory framework, removed academic citations",
  "prompt_file": "prompts/discovery.txt"
}
```

Storage: `.prompt-lab/versions/v2.json`

### §5.2 Case

Ideal-state case:
```json
{
  "id": "case-001",
  "type": "ideal",
  "input": {
    "known_models": "- 「思考，快与慢」→ dual system cognition",
    "thinking_patterns": "- hidden rules determine fate (3 books)",
    "familiar_domains": "psychology (5), economics (3)",
    "n": 3
  },
  "expected_output": null,
  "expected_output_note": "Results should include cross-domain cognitive models; hooks should be information-dense without marketing language",
  "collection": "book-recommendation"
}
```

Bad case:
```json
{
  "id": "case-005",
  "type": "bad-case",
  "input": { ... },
  "actual_output": "Your brain is no smarter than your Stone Age ancestors...",
  "issue": "Hook uses marketing language and suspense",
  "collection": "book-recommendation"
}
```

Storage: `.prompt-lab/cases/<collection>/<case-id>.json`

### §5.3 Run Result

```json
{
  "run_id": "20260725T100000Z",
  "baseline_version": "v1",
  "candidate_version": "v2",
  "dataset": "book-recommendation",
  "provider_config": {
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-v4-flash",
    "max_tokens": 8192,
    "thinking": "disabled"
  },
  "timestamp": "2026-07-25T10:00:00Z",
  "cases": [
    {
      "case_id": "case-001",
      "baseline": {
        "output": "...",
        "prompt_tokens": 7400,
        "completion_tokens": 1200,
        "latency_ms": 3200,
        "finish_reason": "stop"
      },
      "candidate": {
        "output": "...",
        "prompt_tokens": 5400,
        "completion_tokens": 1100,
        "latency_ms": 2800,
        "finish_reason": "stop"
      }
    }
  ],
  "summary": {
    "baseline": { "avg_prompt_tokens": 7400, "avg_latency_ms": 3200, "non_empty_rate": 1.0 },
    "candidate": { "avg_prompt_tokens": 5400, "avg_latency_ms": 2800, "non_empty_rate": 1.0 }
  }
}
```

Storage: `.prompt-lab/runs/<run-id>/result.json`

### §5.4 Config (`prompt-lab.yaml`)

```yaml
provider:
  base_url: "https://api.deepseek.com/v1"
  api_key_env: "DEEPSEEK_API_KEY"
  model: "deepseek-v4-flash"
  default_params:
    max_tokens: 8192
    temperature: 0.7
    thinking: "disabled"

run:
  timeout_seconds: 60
  concurrency: 1  # serial by default
```

## §6 API Surface

Prompt Lab is a CLI tool; its "API" is the command-line interface.

### §6.1 CLI Commands

#### `prompt-lab init`

Initialize a Prompt Lab project.

```
Usage: prompt-lab init [--name <project-name>]

Options:
  --name    Project name (default: current directory name)

Output:
  Created .prompt-lab/
  Created prompt-lab.yaml
  Created .gitignore
```

#### `prompt-lab add version <name>`

Register a prompt version.

```
Usage: prompt-lab add version <name> --file <path> [options]

Arguments:
  name              Version identifier (e.g., "v1", "v2-slim-prompt")

Required:
  --file <path>     Path to prompt text file

Options:
  --changed-from <ver>    Previous version this changes from
  --changed-var <type>    Change type: prompt|model|params|data (default: prompt)
  --note <text>           Change description

Output:
  Registered version v2 (sha256:abc123...)
```

#### `prompt-lab log`

List all versions.

```
Usage: prompt-lab log [--limit <n>]

Output (table):
  Version  | Date                | Author | Changed Var | Note
  v2       | 2026-07-25 10:00    | ezio   | prompt      | Simplified theory framework
  v1       | 2026-07-24 15:00    | ezio   | -           | initial version
```

#### `prompt-lab diff <v1> <v2>`

Show text differences between two versions.

```
Usage: prompt-lab diff <version_a> <version_b>

Output: unified diff format
```

#### `prompt-lab add case <id>`

Add a case.

```
Usage: prompt-lab add case <id> --file <path> --collection <name> --type <ideal|bad-case>

Required:
  --file <path>         Path to case JSON file
  --collection <name>   Collection name
  --type <type>         Case type: ideal or bad-case
```

#### `prompt-lab cases list`

List cases.

```
Usage: prompt-lab cases list [--collection <name>] [--type <ideal|bad-case>]

Output (table):
  ID       | Type      | Collection           | Note
  case-001 | ideal     | book-recommendation  | cross-domain cognitive models
  case-005 | bad-case  | book-recommendation  | hook uses marketing language
```

#### `prompt-lab run`

Execute an A/B comparison run.

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
  --concurrency <n>        Concurrent case execution (default: from config)

Output:
  Run ID: 20260725T100000Z
  Cases: 10 total, 10 success, 0 failed
  Baseline (v1): avg 7400 tokens, avg 3200ms, 100% non-empty
  Candidate (v2): avg 5400 tokens, avg 2800ms, 100% non-empty
  Report saved: .prompt-lab/runs/20260725T100000Z/result.json
```

#### `prompt-lab compare <run-id>`

Generate a comparison report.

```
Usage: prompt-lab compare <run-id> [--format <table|json>]

Options:
  --format <type>    Output format: table (default) or json

Output (table):
  Case     | Baseline tokens | Candidate tokens | Δ     | Baseline ms | Candidate ms | Δ
  case-001 | 7400            | 5400             | -27%  | 3200        | 2800         | -13%
  ...

  Summary:
  Metric           | Baseline (v1) | Candidate (v2) | Delta
  Avg prompt tokens| 7400          | 5400           | -27%
  Avg latency      | 3200ms        | 2800ms         | -13%
  Non-empty rate   | 100%          | 100%           | 0%
  Error rate       | 0%            | 0%             | 0%
```

### §6.2 Internal API (Python Module Interface)

For programmatic use and testing.

```python
# core/version_manager.py
class VersionManager:
    def __init__(self, project_root: Path) -> None: ...
    def add_version(
        self, name: str, prompt_text: str, *,
        changed_from: str | None = None,
        changed_var: str = "prompt",
        change_note: str = "",
        author: str = "",
    ) -> Version: ...
    def get_version(self, name: str) -> Version: ...
    def list_versions(self, limit: int = 50) -> list[Version]: ...
    def diff(self, v1: str, v2: str) -> str: ...

# core/case_manager.py
class CaseManager:
    def __init__(self, project_root: Path) -> None: ...
    def add_case(self, case: Case) -> None: ...
    def get_cases(
        self, collection: str, case_type: str | None = None
    ) -> list[Case]: ...
    def import_cases(self, file_path: Path, collection: str) -> int: ...

# core/run_engine.py
class RunEngine:
    def __init__(
        self, provider: Provider, config: RunConfig
    ) -> None: ...
    async def run(
        self,
        baseline_prompt: str,
        candidate_prompt: str,
        cases: list[Case],
    ) -> RunResult: ...

# core/provider.py
class Provider:
    def __init__(self, config: ProviderConfig) -> None: ...
    async def call(
        self, prompt: str, **params
    ) -> ProviderResponse: ...

# core/report.py
class ReportBuilder:
    @staticmethod
    def build_table(run_result: RunResult) -> str: ...
    @staticmethod
    def build_json(run_result: RunResult) -> str: ...
```

## §7 Error Model

| Code | Meaning | Retryable | User-Facing Message |
|------|---------|-----------|-------------------|
| `E_VERSION_NOT_FOUND` | Version doesn't exist | No | `Error: version 'v3' not found. Run 'prompt-lab log' to see available versions.` |
| `E_CASE_NOT_FOUND` | Case collection or case doesn't exist | No | `Error: dataset 'books' not found. Run 'prompt-lab cases list' to see collections.` |
| `E_PROVIDER_TIMEOUT` | LLM API timed out | Yes | `Warning: LLM call timed out for case-001 (60s). Retrying...` |
| `E_PROVIDER_AUTH` | API key invalid or expired | No | `Error: provider authentication failed. Check your API key env var.` |
| `E_PROVIDER_RATE_LIMIT` | API rate limited | Yes | `Warning: rate limited. Waiting 2s before retry...` |
| `E_EMPTY_OUTPUT` | LLM returned empty content | No | `Warning: empty output for case-001, version v2 (finish_reason=length)` |
| `E_CONFIG_INVALID` | Config file malformed | No | `Error: prompt-lab.yaml is invalid: <details>` |
| `E_ALREADY_EXISTS` | Version name already taken | No | `Error: version 'v2' already exists. Use a different name.` |

Propagation rules:
- `E_PROVIDER_TIMEOUT` and `E_PROVIDER_RATE_LIMIT`: retry 3 times with exponential backoff (1s, 2s, 4s)
- Other errors: no retry, logged to events.jsonl, continue to next case
- Single case failure does not abort the entire run

## §8 Failure Modes

| Scenario | Detection | Recovery |
|----------|-----------|----------|
| LLM API unavailable (network down, provider outage) | `httpx.ConnectError` / `httpx.TimeoutException` | Retry 3 times; if all fail, mark case `E_PROVIDER_TIMEOUT`, run continues |
| API key invalid | HTTP 401 | No retry, error exit, prompt to check env var |
| Case input variables don't match prompt template placeholders | `KeyError` during render | Mark case `E_CASE_FORMAT`, skip, run continues |
| Disk full, write fails | `OSError` on write | Error exit, suggest cleaning `.prompt-lab/runs/` |

## §9 Performance Budget

| Metric | Target | Measurement |
|--------|--------|-------------|
| Single case LLM call | p95 < 30s, timeout 60s | Run result `latency_ms` |
| 10-case A/B run (serial) | < 5 minutes | `run_completed.duration_ms` |
| CLI command startup (non-LLM) | < 500ms | Manual timing |
| Local file I/O | < 100ms per operation | Manual timing |
| API cost (10 cases × 2 versions) | < $0.10 | `prompt_tokens` × provider pricing |

## §10 Security & Privacy

### Authentication

No application-layer auth (local CLI tool). LLM API auth passed via environment variables to provider.

### Sensitive Data

| Data | Sensitivity | Protection |
|------|-------------|------------|
| API key | High | Read from env vars only, never written to any file |
| Prompt content | Medium (may contain business logic) | Local storage; `.prompt-lab/` optionally excluded from git |
| Run results | Medium (contains LLM outputs) | Local storage; `.prompt-lab/runs/` excluded from git by default |
| Case inputs | Low (test data) | Local storage |

### Audit

Version changes and run records carry timestamps and author info, auditable. No centralized audit log (local tool).

## §11 Open Questions

| # | Question | Decision | Deadline |
|---|----------|----------|----------|
| 1 | Which template engine for prompt rendering? (Jinja2 vs str.format vs custom) | **Decision**: v1 uses Python `str.format()` covering `{variable}` placeholders. No Jinja2 dependency. If conditional logic needed, evaluate in v2. | 2026-07-25 ✅ |
| 2 | File storage or SQLite for version data? | **Decision**: v1 uses JSON files. Expected < 100 versions; files are sufficient and git-friendly. SQLite evaluation deferred to v2. | 2026-07-25 ✅ |
| 3 | How much concurrency support? | **Decision**: v1 defaults to serial (`concurrency: 1`). Run Engine uses asyncio internally; concurrency capability reserved but CLI default is off. Avoids API rate limit issues. | 2026-07-25 ✅ |

## §12 References

- **Positioning Memo**: [prompt_lab_positioning_v1.0_2026-07-25.en.md](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.en.md)
- **PRD**: [prompt_lab_prd_v1.0_2026-07-25.en.md](../01-prd/prompt_lab_prd_v1.0_2026-07-25.en.md)
- **External Standards**: [DeepSeek API Docs](https://api-docs.deepseek.com/) (provider params), [OpenAI API Reference](https://platform.openai.com/docs/api-reference) (compatible protocol base)
- **Kanban**: Pending registration

---

Sign-off: Pending Ezio review
