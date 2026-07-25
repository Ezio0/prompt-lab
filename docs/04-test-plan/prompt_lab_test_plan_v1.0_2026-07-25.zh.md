# Prompt Lab Test Plan

**项目**: Prompt Lab
**日期**: 2026-07-25
**版本**: v1.0
**Plan**: [prompt_lab_plan_v1.0_2026-07-25.zh.md](../03-plan/prompt_lab_plan_v1.0_2026-07-25.zh.md)
**Spec**: [prompt_lab_spec_v1.0_2026-07-25.zh.md](../02-spec/prompt_lab_spec_v1.0_2026-07-25.zh.md)

---

## §1 Scope

### In Scope

| CUJ | 描述 | 来源 |
|-----|------|------|
| CUJ-1 | 初始化 → 注册 prompt → 定义 case → 跑 A/B → 看报告 | PRD §3.x |
| CUJ-2 | 发现 bad case → 导入 → 改 prompt → 注册新版本 → A/B 验证 | PRD §3.x |

### Out of Scope

- CUJ-3（换模型回归）— P1 优先级，v1 不要求 E2E 覆盖
- LLM 真实 API 调用测试 — 所有测试 mock provider，不产生 API 费用
- Web UI 测试 — v1 无前端

## §2 Test Pyramid

```
        ╱ E2E ╱          1 test (CUJ-1 full chain)
       ╱──────╱
      ╱ Integ╱           1 test (CUJ-2 import + run)
     ╱──────╱
    ╱ Unit  ╱            ~35 tests (per module)
   ╱────────╱
```

### Unit Tests（~35 个）

| 模块 | 测试文件 | 预估测试数 | 覆盖路径 |
|------|---------|-----------|---------|
| Config | test_config.py | 4 | valid / missing file / invalid yaml / missing api key |
| Version Manager | test_version_manager.py | 7 | add / get / list / diff / duplicate / immutability / not found |
| Case Manager | test_case_manager.py | 5 | add / get / filter by type / import / invalid type |
| Provider | test_provider.py | 6 | success / 401 / 429 / timeout / 5xx / empty content |
| Run Engine | test_run_engine.py | 7 | normal / single case fail / retry / empty output / all fail / render error / summary |
| Report | test_report.py | 4 | table output / json output / empty results / delta calculation |
| CLI | test_cli.py | 5 | init / add version / log / run / compare (使用 CliRunner) |
| **小计** | | **~38** | |

### Integration Tests（1 个）

| 测试 | 文件 | 描述 |
|------|------|------|
| test_e2e_cuj1 | test_e2e.py::test_cuj1_full_chain | init → add version × 2 → add case × 3 → run → compare → verify result.json |

### E2E Tests（1 个）

| 测试 | 文件 | 描述 |
|------|------|------|
| test_cuj2_bad_case_flow | test_e2e.py::test_cuj2_bad_case | import bad cases → add new version → run → compare → verify delta |

## §3 Mock 策略

| 层 | Mock 对象 | 工具 |
|----|---------|------|
| Provider | `httpx.AsyncClient` | `unittest.mock.patch` + `AsyncMock` |
| 文件系统 | 不 mock，使用 `tmp_path` fixture | pytest 内置 |
| LLM 输出 | 固定 JSON 字符串 | 测试 fixture |

**速度预算**：全量测试 < 10 秒完成（无真实 API 调用）。

## §4 测试数据

所有测试数据为合成数据。无真实 PII，无真实 API key。

### Fixture: 合成 prompt

```
You are a test discovery engine. Recommend books for the user.

User models:
{known_models}

Domains to avoid: {familiar_domains}

Generate {n} recommendations.
```

### Fixture: 合成 case

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

### Fixture: 合成 provider response

```json
{
  "choices": [{"message": {"content": "Test output"}, "finish_reason": "stop"}],
  "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
}
```

## §5 覆盖率门槛

| 层 | 覆盖率目标 |
|----|-----------|
| `prompt_lab/core/` | ≥ 80% |
| `prompt_lab/cli.py` | ≥ 70%（CliRunner 测试主要命令） |
| 总体 | ≥ 75% |

测量工具：`pytest --cov=prompt_lab --cov-report=term-missing`

## §6 CI 集成（v1.1 规划）

v1 不配 CI（先手动跑测试验证）。v1.1 加 GitHub Actions：
- `pytest --cov` 全量测试
- `ruff check` 语法检查
- PR gate

## §7 References

- **Plan**: [prompt_lab_plan_v1.0_2026-07-25.zh.md](../03-plan/prompt_lab_plan_v1.0_2026-07-25.zh.md)
- **Spec**: [prompt_lab_spec_v1.0_2026-07-25.zh.md](../02-spec/prompt_lab_spec_v1.0_2026-07-25.zh.md)
- **PRD**: [prompt_lab_prd_v1.0_2026-07-25.zh.md](../01-prd/prompt_lab_prd_v1.0_2026-07-25.zh.md)
- **Positioning**: [prompt_lab_positioning_v1.0_2026-07-25.zh.md](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.zh.md)

---

签字：待 Ezio 审阅
