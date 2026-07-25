# Prompt Lab PRD

**Project**: Prompt Lab
**Date**: 2026-07-25
**Version**: v1.0
**Positioning**: [prompt_lab_positioning_v1.0_2026-07-25.en.md](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.en.md)

---

## §1 Product Background

In LLM application development, prompts are core production assets, yet their iteration process is extremely primitive: developers edit a string in code, eyeball a few outputs, and commit if it feels "close enough." No version history, no validation set comparison, no quantitative metrics.

This pain point is defined in the [Positioning Memo §WHY](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.en.md#why): prompt changes are ad-hoc, and whether things improve or degrade is a guess. This document does not restate it.

Prompt Lab's goal: transform prompt iteration from guesswork into controlled experimentation. See [Positioning Memo §WHO](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.en.md#who) for specific scenarios.

## §2 Target Users

References [Positioning Memo §WHO](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.en.md#who).

| Role | Description | v1 Target |
|------|-------------|-----------|
| **Developer** | Engineers who integrate LLMs into projects, write and maintain prompts. Can run CLI, write config files. | ✅ v1 core |
| **PM / Operator** | Non-technical roles who need to adjust prompt text and output style. Need Web UI to modify prompts and view comparison results. | ⏳ v2 (v1 does CLI + comparison reports first, Web UI later) |

## §3 User Stories

### US-1: Initialize prompt project from scratch

> As a developer, I want to initialize Prompt Lab in my project, so I can start systematically managing prompt versions.

Acceptance criteria:
- [ ] `prompt-lab init` generates config file and directory structure in the current directory
- [ ] Config file includes LLM provider settings (base_url, model, api_key env var name)
- [ ] After initialization, the first prompt version can be registered immediately

### US-2: Register prompt version

> As a developer, I want to register each prompt change as a version, so I can track history and trace back.

Acceptance criteria:
- [ ] `prompt-lab add version <name> --file <path>` registers a prompt file as a new version
- [ ] Each version records: content hash, timestamp, author, change note (optional)
- [ ] `prompt-lab log` lists all versions with metadata
- [ ] Versions can be diffed

### US-3: Define ideal-state cases

> As a developer, I want to define ideal-state cases (input + expected output) for prompts, so I can establish a validation baseline.

Acceptance criteria:
- [ ] Case file format supports: input (variable key-value pairs) + expected output (handwritten or AI-assisted)
- [ ] Supports importing from production bad cases (input + issue description)
- [ ] Cases can be managed in groups (e.g., "book-recommendation", "summarization")
- [ ] `prompt-lab cases list` lists all cases with type (ideal / bad-case)

### US-4: Run A/B comparison

> As a developer, I want to run two prompt versions against the same set of cases simultaneously, so I can quantify the quality difference.

Acceptance criteria:
- [ ] `prompt-lab run --baseline <v1> --candidate <v2> --dataset <cases>` executes comparison
- [ ] Each case runs once per version, outputs isolated
- [ ] Comparison metrics: output text diff, token consumption, latency (ms), content non-empty rate
- [ ] Supports configuring LLM provider parameters (model, max_tokens, temperature, thinking mode)
- [ ] Results persisted locally after run (for subsequent review)

### US-5: View comparison report

> As a developer, I want to see a structured comparison report, so I can make a data-driven decision on which version is better.

Acceptance criteria:
- [ ] `prompt-lab compare <run-id>` outputs comparison report
- [ ] Report includes: per-case side-by-side output comparison, summary statistics table (avg tokens, avg latency, non-empty rate)
- [ ] Supports JSON output (for pipeline processing)
- [ ] Supports terminal table output (for manual review)

### US-6: Support single-variable control

> As a developer, I want to explicitly annotate "what changed" in comparisons, so I know which variable to attribute quality differences to.

Acceptance criteria:
- [ ] `prompt-lab add version` supports `--changed-from <prev_version>` with change description
- [ ] Comparison report displays change notes for baseline and candidate
- [ ] Non-prompt variable changes (model, params) also recorded in version metadata

### §3.x Critical User Journeys (CUJ)

| CUJ ID | Description | Modules | Priority |
|--------|-------------|---------|----------|
| CUJ-1 | Init project → register prompt → define cases → run A/B → view report → decide to ship | CLI full chain | P0 |
| CUJ-2 | Find bad case → import as case → modify prompt → register new version → A/B validate | CLI full chain | P0 |
| CUJ-3 | Switch model → register new version (non-prompt change) → A/B validate regression | CLI + provider config | P1 |

## §4 Functional Requirements

### FR-1: Project initialization

`prompt-lab init` generates in the current directory:
- `.prompt-lab/` directory (stores versions, cases, run results)
- `prompt-lab.yaml` config file (provider settings, default params)
- `.gitignore` (excludes `.prompt-lab/runs/`)

### FR-2: Prompt version management

- Versions stored under `.prompt-lab/versions/`, one JSON file per version
- Version content: prompt text, content hash, timestamp, author, change note, linked upstream version
- `prompt-lab log` lists versions in reverse chronological order
- `prompt-lab diff <v1> <v2>` outputs text diff

### FR-3: Case management

- Cases stored under `.prompt-lab/cases/`, grouped by collection
- Case format: `{ id, type (ideal|bad-case), input: {var: val}, expected_output?: str, note?: str }`
- Supports bulk import from JSON files
- `prompt-lab cases list [--type ideal|bad-case]` lists cases

### FR-4: A/B run engine

- `prompt-lab run --baseline <v> --candidate <v> --dataset <cases>` executes comparison
- For each case: render baseline prompt → call LLM → record output; repeat with candidate prompt
- Recorded metrics: output_text, prompt_tokens, completion_tokens, latency_ms, finish_reason, error
- Results stored under `.prompt-lab/runs/<run-id>/`

### FR-5: Comparison report

- `prompt-lab compare <run-id>` generates report
- Terminal mode: table output with summary statistics + per-case diff
- JSON mode: complete structured output
- Summary metrics: avg prompt_tokens, avg completion_tokens, avg latency_ms, content non-empty rate, error rate

### FR-6: LLM provider adapter

- v1 supports OpenAI-compatible API (covers OpenAI, DeepSeek, Anthropic via proxy, local vLLM, etc.)
- Config: base_url, api_key (env var name), model, default params (max_tokens, temperature, thinking mode)
- Each case run uses configured provider params, overridable in run command

### FR-7: Change tracking

- `prompt-lab add version` supports `--note "simplified theory framework"` for change description
- Supports `--changed-var prompt|model|params|data` to mark change type
- Comparison report shows change type and note for attribution

## §5 Non-Functional Requirements

| Dimension | Requirement |
|-----------|-------------|
| Performance | Single case LLM call timeout 60s. Multiple cases run concurrently (default serial, configurable) |
| Security | API key read from environment variables only, never stored in config files |
| Privacy | All data stored locally in `.prompt-lab/`, no external service communication |
| Extensibility | Provider adapter layer pluggable, can add non-OpenAI-compatible providers later |
| Observability | Each run records complete logs (timestamp, params, results), auditable |
| Rollback | Versions are immutable, cannot be deleted (only new ones added). Rollback = promote old version |

## §6 Data Migration

Not applicable. New project, no existing data. First `prompt-lab init` creates a fresh structure.

## §7 Data Observability

Data produced by Prompt Lab itself (for in-project analysis and external consumption):

- **Run records**: Each A/B run generates structured JSON with complete input/output and metrics per case
- **Version history**: All prompt versions with metadata
- **Case library**: Accumulated ideal-state cases and bad cases

Example query: `jq '.cases[] | select(.metrics.completion_tokens > 1000)' .prompt-lab/runs/latest/results.json` — find cases with excessive token consumption.

## §8 Frontend Changes

No frontend in v1. Pure CLI tool.

Web UI planned for v2 (not in this scope).

## §9 Risks

| Risk | Level | Mitigation |
|------|-------|------------|
| LLM output non-determinism makes A/B results non-reproducible | Medium | Each case supports temperature=0 config (default); multiple runs averaged |
| Provider API changes break adapter layer | Low | Adapter abstracted, depends only on OpenAI-compatible protocol |
| Case accumulation requires manual effort, users may skip | Medium | Provide tools to import bad cases from production logs, lowering case creation cost |

## §10 Non-Goals

1. **No prompt auto-optimization** — v1 does not auto-search or generate "better" prompts. Auto-optimization is a future direction, but requires version management and validation sets as foundation. (See [Positioning §ANTI-POSITIONING](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.en.md#anti-positioning))
2. **No production observability / trace monitoring** — Does not monitor production LLM calls. That's Langfuse / Phoenix's domain. We focus on pre-deployment decisions.
3. **No custom evaluation metric engine** — Does not build an evaluation metric library. v2 plans DeepEval integration as eval backend.
4. **No Web UI** — v1 is pure CLI. Web UI deferred to v2 to serve non-technical roles.
5. **No prompt hosting / registry service** — Does not provide hosted prompt storage and distribution API. Version management based on local files + git.

## §11 Acceptance Criteria

### Functional
- [ ] `prompt-lab init` successfully initializes project, config file editable
- [ ] `prompt-lab add version` registers versions, `prompt-lab log` shows history
- [ ] `prompt-lab run` executes A/B comparison, outputs result files
- [ ] `prompt-lab compare` generates readable comparison report
- [ ] `prompt-lab diff` shows text differences between versions

### Performance
- [ ] Single case LLM call completes or times out within 60s
- [ ] 10-case A/B run completes within 5 minutes (serial)

### Testing
- [ ] Core module unit test coverage ≥ 80%
- [ ] CLI end-to-end tests cover CUJ-1 and CUJ-2

### Rollback
- [ ] Versions are immutable; any erroneous operation recoverable by registering a new version

## §12 Observability Requirements

### §12.1 New Events

Prompt Lab is a CLI tool; "events" are stored as run logs under `.prompt-lab/runs/`.

| Event | Trigger | Key Fields | Purpose | Priority |
|-------|---------|------------|---------|----------|
| `run_started` | A/B run begins | baseline_version, candidate_version, dataset, provider_config, timestamp | Audit | P0 |
| `case_completed` | Single case completes | case_id, version, output, prompt_tokens, completion_tokens, latency_ms, finish_reason | Comparison data | P0 |
| `case_failed` | Single case fails | case_id, version, error_type, error_message | Diagnostics | P0 |
| `run_completed` | A/B run finishes | run_id, total_cases, success_count, fail_count, duration_ms | Audit | P0 |

### §12.2 Reused Events

Not applicable. New project, no existing events.

### §12.3 Event Schema

All events stored as JSON files (`.prompt-lab/runs/<run-id>/events.jsonl`, JSONL format). No database schema.

### §12.4 Acceptance Criteria

- [ ] Each `prompt-lab run` generates a complete events.jsonl
- [ ] `case_completed` covers all successfully executed cases (100%)
- [ ] `case_failed` covers all failed cases (100%)

### §12.5 Privacy Considerations

- Prompt content may contain user data (depending on use case), stored locally in `.prompt-lab/`
- `.gitignore` excludes `.prompt-lab/runs/` by default (run results not in git)
- API key read from environment variables only, never written to any file

## §13 Links

- **Positioning Memo**: [prompt_lab_positioning_v1.0_2026-07-25.en.md](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.en.md)
- **Kanban**: New project, pending registration
- **Prior PRD**: None (first version)
- **Framework**: Prompt Lab v1.0

---

Sign-off: Pending Ezio review
