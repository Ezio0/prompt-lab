# Prompt Lab Test Plan

**Project**: Prompt Lab
**Date**: 2026-07-25
**Version**: v1.0
**Plan**: [prompt_lab_plan_v1.0_2026-07-25.en.md](../03-plan/prompt_lab_plan_v1.0_2026-07-25.en.md)
**Spec**: [prompt_lab_spec_v1.0_2026-07-25.en.md](../02-spec/prompt_lab_spec_v1.0_2026-07-25.en.md)

---

## §1 Scope

### In Scope

| CUJ | Description | Source |
|-----|-------------|--------|
| CUJ-1 | Init → register prompt → define case → run A/B → view report | PRD §3.x |
| CUJ-2 | Find bad case → import → modify prompt → register new version → A/B validate | PRD §3.x |

### Out of Scope

- CUJ-3 (model switch regression) — P1 priority, E2E coverage not required for v1
- Real LLM API call tests — all tests mock provider, no API costs
- Web UI tests — v1 has no frontend

## §2 Test Pyramid

```
        ╱ E2E ╱          1 test (CUJ-1 full chain)
       ╱──────╱
      ╱ Integ╱           1 test (CUJ-2 import + run)
     ╱──────╱
    ╱ Unit  ╱            ~35 tests (per module)
   ╱────────╱
```

### Unit Tests (~35)

| Module | Test File | Est. Tests | Covered Paths |
|--------|-----------|-----------|---------------|
| Config | test_config.py | 4 | valid / missing file / invalid yaml / missing api key |
| Version Manager | test_version_manager.py | 7 | add / get / list / diff / duplicate / immutability / not found |
| Case Manager | test_case_manager.py | 5 | add / get / filter by type / import / invalid type |
| Provider | test_provider.py | 6 | success / 401 / 429 / timeout / 5xx / empty content |
| Run Engine | test_run_engine.py | 7 | normal / single case fail / retry / empty output / all fail / render error / summary |
| Report | test_report.py | 4 | table output / json output / empty results / delta calculation |
| CLI | test_cli.py | 5 | init / add version / log / run / compare (using CliRunner) |
| **Total** | | **~38** | |

### Integration Tests (1)

| Test | File | Description |
|------|------|-------------|
| test_e2e_cuj1 | test_e2e.py::test_cuj1_full_chain | init → add version × 2 → add case × 3 → run → compare → verify result.json |

### E2E Tests (1)

| Test | File | Description |
|------|------|-------------|
| test_cuj2_bad_case_flow | test_e2e.py::test_cuj2_bad_case | import bad cases → add new version → run → compare → verify delta |

## §3 Mock Strategy

| Layer | Mock Target | Tool |
|-------|-------------|------|
| Provider | `httpx.AsyncClient` | `unittest.mock.patch` + `AsyncMock` |
| Filesystem | Not mocked, use `tmp_path` fixture | pytest built-in |
| LLM Output | Fixed JSON strings | Test fixtures |

**Speed Budget**: Full test suite < 10 seconds (no real API calls).

## §4 Test Data

All test data is synthetic. No real PII, no real API keys.

### Fixture: Synthetic prompt

```
You are a test discovery engine. Recommend books for the user.

User models:
{known_models}

Domains to avoid: {familiar_domains}

Generate {n} recommendations.
```

### Fixture: Synthetic case

```json
[
  {
    "id": "test-case-001",
    "type": "ideal",
    "input": {
      "known_models": "- 「Test Book」→ test model",
      "familiar_domains": "testing (3)",
      "n": 2
    },
    "expected_output": null,
    "collection": "test-collection"
  }
]
```

### Fixture: Synthetic provider response

```json
{
  "choices": [{"message": {"content": "Test output"}, "finish_reason": "stop"}],
  "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
}
```

## §5 Coverage Thresholds

| Layer | Coverage Target |
|-------|----------------|
| `prompt_lab/core/` | ≥ 80% |
| `prompt_lab/cli.py` | ≥ 70% (CliRunner tests main commands) |
| Overall | ≥ 75% |

Measurement: `pytest --cov=prompt_lab --cov-report=term-missing`

## §6 CI Integration (v1.1 planned)

v1 does not configure CI (manual test verification first). v1.1 adds GitHub Actions:
- `pytest --cov` full suite
- `ruff check` linting
- PR gate

## §7 References

- **Plan**: [prompt_lab_plan_v1.0_2026-07-25.en.md](../03-plan/prompt_lab_plan_v1.0_2026-07-25.en.md)
- **Spec**: [prompt_lab_spec_v1.0_2026-07-25.en.md](../02-spec/prompt_lab_spec_v1.0_2026-07-25.en.md)
- **PRD**: [prompt_lab_prd_v1.0_2026-07-25.en.md](../01-prd/prompt_lab_prd_v1.0_2026-07-25.en.md)
- **Positioning**: [prompt_lab_positioning_v1.0_2026-07-25.en.md](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.en.md)

---

Sign-off: Pending Ezio review
