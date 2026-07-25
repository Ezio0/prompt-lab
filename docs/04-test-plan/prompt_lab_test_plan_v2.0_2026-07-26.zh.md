# Prompt Lab Test Plan v2.0

**项目**: Prompt Lab
**日期**: 2026-07-26
**版本**: v2.0
**Plan**: [prompt_lab_plan_v2.0_2026-07-26.zh.md](../03-plan/prompt_lab_plan_v2.0_2026-07-26.zh.md)
**Spec**: [prompt_lab_spec_v2.0_2026-07-26.zh.md](../02-spec/prompt_lab_spec_v2.0_2026-07-26.zh.md)
**前序 Test Plan**: [prompt_lab_test_plan_v1.0_2026-07-25.zh.md](./prompt_lab_test_plan_v1.0_2026-07-25.zh.md)

---

## §1 Scope

### In Scope

| CUJ | 描述 | 来源 |
|-----|------|------|
| CUJ-4 | init → add version × 2 → add case (with expected_output) → run --eval → compare（含质量分数） | PRD v2 §3.x |
| CUJ-5 | serve → 浏览器 → 版本列表 → 版本详情 → run 报告 | PRD v2 §3.x |

### Out of Scope

- CUJ-6（Web 读写全链路）— P1 优先级，手动验证，不要求 E2E 自动化
- 真实 LLM API 调用测试 — 所有测试 mock provider 和 evaluator
- 真实 DeepEval 调用测试 — mock `metric.measure()` 返回固定分数
- React 组件单元测试 — 手动验证，不配 Jest/Vitest（V2 范围外）

## §2 Test Pyramid

```
        ╱  E2E  ╱          2 tests (CUJ-4 + CUJ-5)
       ╱────────╱
      ╱  Integ ╱           2 tests (eval chain + web API chain)
     ╱──────────╱
    ╱   Unit   ╱           ~60 tests (V1 ~38 + V2 ~22 new)
   ╱────────────╱
```

### V2 新增单元测试

| 模块 | 测试文件 | 预估测试数 | 覆盖路径 |
|------|---------|-----------|---------|
| Config (eval block) | test_config.py (扩展) | +4 | eval block 解析 / 无 eval block / 缺 api_key / metrics 格式 |
| Models | test_run_engine.py (扩展) | +3 | EvalResult 序列化 / V1 兼容 / eval_summary |
| Eval Model | test_eval_model.py | 3 | 模型创建 / generate / get_model_name |
| Evaluator | test_evaluator.py | 6 | 正常 / skipped (no expected_output) / error / 多指标 / GEval criteria / baseline+candidate 双评估 |
| Run Engine (eval) | test_run_engine.py (扩展) | +4 | 带 eval / eval error 不中断 / eval_summary 正确 / 无 eval 兼容 |
| Report (eval) | test_report.py (扩展) | +3 | eval 列 / eval-only 模式 / 无 eval 兼容 |
| CLI (eval) | test_cli.py (扩展) | +2 | run --eval / compare --eval-only |
| Web Server | test_web_server.py | 2 | create_app 返回实例 / health check |
| Web Versions API | test_web_versions.py | 4 | list / detail / diff / register |
| Web Cases API | test_web_cases.py | 2 | list / filter |
| Web Runs API | test_web_runs.py | 4 | list / detail / trigger / config |
| **V2 小计** | | **~37** | |

### V2 新增集成测试

| 测试 | 文件 | 描述 |
|------|------|------|
| test_cuj4_eval_chain | test_e2e.py (扩展) | init → add version × 2 → add case → run --eval → compare (含 eval 列) |
| test_web_api_chain | test_web_e2e.py | create_app → GET versions → GET version detail → GET runs → GET run detail |

## §3 Mock 策略

### V1 Mock 策略（不变）

| 层 | Mock 对象 | 工具 |
|----|---------|------|
| Provider | `httpx.AsyncClient` | `unittest.mock.patch` + `AsyncMock` |
| 文件系统 | `tmp_path` fixture | pytest 内置 |
| LLM 输出 | 固定 JSON 字符串 | 测试 fixture |

### V2 新增 Mock 策略

| 层 | Mock 对象 | 工具 | 说明 |
|----|---------|------|------|
| DeepEval metrics | `metric.measure()` | `unittest.mock.patch` | 返回固定 score + reason，不调真实 LLM |
| DeepEval model | `CustomModel.generate()` | `unittest.mock.patch` | 返回固定文本，不调真实 API |
| FastAPI HTTP | 不 mock | `fastapi.testclient.TestClient` | 内存中调用 ASGI app |
| React 前端 | 不测试 | — | 手动验证 |

**关键 Mock 模式 — DeepEval 评估**:

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

**关键 Mock 模式 — FastAPI TestClient**:

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

**速度预算**：全量测试（V1 + V2）< 15 秒（无真实 API 调用，无 DeepEval 调用）。

## §4 测试数据

### V1 测试数据（不变）

合成 prompt / case / provider response — 与 V1 Test Plan 一致。

### V2 新增测试数据

#### Fixture: 带 expected_output 的 case

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
  "expected_output_note": "高质量推荐应包含隐藏机制和跨领域连接",
  "collection": "test-eval"
}
```

#### Fixture: 合成 EvalResult

```python
EVAL_RESULTS_FIXTURE = [
    EvalResult(metric_name="faithfulness", score=0.85, reason="output is faithful to input", status="pass"),
    EvalResult(metric_name="answer_relevancy", score=0.72, reason="mostly relevant", status="pass"),
    EvalResult(metric_name="geval", score=0.0, reason="", status="skipped"),
    EvalResult(metric_name="faithfulness", score=0.0, reason="", status="error", error="API timeout"),
]
```

#### Fixture: 带 eval 数据的 RunResult

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

## §5 覆盖率门槛

| 层 | 覆盖率目标 |
|----|-----------|
| `prompt_lab/core/` (含 evaluator) | ≥ 80% |
| `prompt_lab/core/evaluator.py` | ≥ 85% |
| `prompt_lab/core/eval_model.py` | ≥ 80% |
| `prompt_lab/web/` | ≥ 80% |
| `prompt_lab/cli.py` | ≥ 70% |
| 总体 | ≥ 75% |

测量工具：`pytest --cov=prompt_lab --cov-report=term-missing`

## §6 向后兼容测试

V2 必须保证 V1 数据可用：

| 测试 | 描述 |
|------|------|
| V1 result.json 读取 | V1 格式的 result.json 被 V2 读取时 `evaluations` 为空列表 |
| V1 prompt-lab.yaml 读取 | V1 格式的 yaml 无 `eval` block 时正常加载 |
| V1 命令行为 | 无 `--eval` 时 run/compare 行为与 V1 完全一致 |
| V1 测试全通过 | V1 的全部 ~38 个测试在 V2 代码上全部通过（无回归） |

## §7 References

- **Plan**: [prompt_lab_plan_v2.0_2026-07-26.zh.md](../03-plan/prompt_lab_plan_v2.0_2026-07-26.zh.md)
- **Spec**: [prompt_lab_spec_v2.0_2026-07-26.zh.md](../02-spec/prompt_lab_spec_v2.0_2026-07-26.zh.md)
- **PRD**: [prompt_lab_prd_v2.0_2026-07-26.zh.md](../01-prd/prompt_lab_prd_v2.0_2026-07-26.zh.md)
- **前序 Test Plan**: [prompt_lab_test_plan_v1.0_2026-07-25.zh.md](./prompt_lab_test_plan_v1.0_2026-07-25.zh.md)

---

签字：待 Ezio 审阅
