# Prompt Lab Technical Spec v2.0

**项目**: Prompt Lab
**日期**: 2026-07-26
**版本**: v2.0
**PRD**: [prompt_lab_prd_v2.0_2026-07-26.zh.md](../01-prd/prompt_lab_prd_v2.0_2026-07-26.zh.md)
**前序 Spec**: [prompt_lab_spec_v1.0_2026-07-25.zh.md](./prompt_lab_spec_v1.0_2026-07-25.zh.md)

---

## §1 Overview

Prompt Lab v2 在 V1 的 CLI 版本管理 + A/B 对比基础上，新增**质量评估引擎**（DeepEval 集成）和 **Web UI**（FastAPI + React SPA），让"改 prompt → 对比 → 看数据 → 决策"这条闭环从缺少质量维度变为完整。

**消费者**：开发者（CLI + Web）、PM/运营（Web）

**系统上下文**：

```
┌──────────────────────────────────────────────────────────┐
│                    User Machine (localhost)                │
│                                                            │
│  ┌──────────────┐         ┌──────────────────────────────┐│
│  │  CLI (V1)    │         │  Web UI (V2 新增)             ││
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
│  │              Core Modules (V1 + V2 扩展)              │ │
│  │                                                       │ │
│  │  VersionManager  CaseManager  Config (+EvalConfig)    │ │
│  │  RunEngine       Provider     ReportBuilder (+Eval)   │ │
│  │                  Evaluator (V2 新增)                   │ │
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
         │ LLM Provider     │    │ Eval LLM (可同可不同) │
         │ (生成 prompt)    │    │ (DeepEval 调用)      │
         └──────────────────┘    └──────────────────────┘
```

## §2 Goals

引用 [PRD §4 功能需求](../01-prd/prompt_lab_prd_v2.0_2026-07-26.zh.md#4-功能需求)。

1. **质量评估集成**：`run --eval` 对每个 case 执行配置的 DeepEval 指标，评估覆盖率 100%（pass/skipped/error 全记录），单指标评估 p95 < 30s
2. **报告质量维度**：`compare` 报告和 Web UI 均展示 baseline vs candidate 质量分数，汇总含 `avg_<metric>`
3. **Web API**：9 个 REST 端点覆盖版本/case/run CRUD，p95 < 100ms（不含 LLM 调用）
4. **Web SPA**：3 个页面（versions/runs/editor），页面加载 p95 < 500ms
5. **向后兼容**：V1 的 `result.json` 可被 V2 正常读取；无 `--eval` 时行为与 V1 完全一致

## §3 Non-Goals

镜像 [PRD §10 非目标](../01-prd/prompt_lab_prd_v2.0_2026-07-26.zh.md#10-非目标)。

1. 不做自动 prompt 优化（见 PRD §10.1）
2. 不做用户认证/多用户（见 PRD §10.2）
3. 不做自定义评估指标引擎（见 PRD §10.3）
4. 不做 CI/CD 集成（见 PRD §10.4）
5. 不做线上可观测性/trace 监控（见 PRD §10.5）

## §4 Architecture

### §4.1 组件

| 组件 | 职责 | 拥有的数据 | V1/V2 |
|------|------|-----------|-------|
| **CLI Entry** (`cli.py`) | 命令解析、调用核心模块 | 无 | V1 扩展（+serve, +--eval） |
| **Version Manager** (`core/version_manager.py`) | 版本注册、存储、查询、diff | `.prompt-lab/versions/` | V1 不变 |
| **Case Manager** (`core/case_manager.py`) | Case 增删查 | `.prompt-lab/cases/` | V1 不变 |
| **Run Engine** (`core/run_engine.py`) | A/B 执行 + 评估编排 | `.prompt-lab/runs/` | V1 扩展 |
| **Provider Adapter** (`core/provider.py`) | OpenAI 兼容 API 调用 | 无 | V1 不变 |
| **Evaluator** (`core/evaluator.py`) | DeepEval 指标评估 | 无 | **V2 新增** |
| **Report Builder** (`core/report.py`) | 对比报告（+质量列） | 无 | V1 扩展 |
| **Config** (`core/config.py`) | 配置加载（+eval block） | `prompt-lab.yaml` | V1 扩展 |
| **Web Server** (`web/server.py`) | FastAPI REST API | 无 | **V2 新增** |
| **Web Frontend** (`web/frontend/`) | React SPA | 无 | **V2 新增** |

### §4.2 数据流：`run --eval` 完整链路

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

### §4.3 数据流：`serve` (Web UI)

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

### §4.4 部署拓扑

| 组件 | 运行位置 |
|------|---------|
| CLI + Core + Evaluator | 用户本地终端（Python 进程） |
| Web Server (FastAPI) | 用户本地终端（uvicorn 进程，127.0.0.1） |
| Web Frontend (React SPA) | 用户浏览器（FastAPI 托管静态文件） |
| `.prompt-lab/` | 用户项目目录（本地文件系统） |
| LLM Provider（生成） | 外部 HTTP API |
| LLM Provider（评估） | 外部 HTTP API（可与生成相同） |

## §5 Data Model

### §5.1 V1 模型（不变）

`Version`, `Case`, `ProviderResponse`, `RunConfig`, `Config` — 结构与 V1 Spec §5 完全一致。

### §5.2 V2 扩展模型

#### EvalConfig（新增）

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

配置文件格式 (`prompt-lab.yaml` V2 扩展)：
```yaml
# V1 字段不变
provider: { ... }
run: { ... }

# V2 新增
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

Config.load() 向后兼容：无 `eval` block 时返回 `EvalConfig(enabled=False, metrics=[], ...)`。

#### EvalResult（新增）

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

#### CaseResult（扩展）

```python
# V1: CaseResult(case_id, baseline: ExecutionResult, candidate: ExecutionResult)
# V2 扩展:

@dataclass(frozen=True)
class CaseResult:
    case_id: str
    baseline: ExecutionResult
    candidate: ExecutionResult
    evaluations: list[EvalResult] = field(default_factory=list)  # V2 新增
```

向后兼容：V1 的 `result.json` 反序列化时 `evaluations` 默认空列表。

#### RunResult.summary 扩展

```json
{
  "summary": {
    "baseline": { "avg_prompt_tokens": 7400, ... },  // V1 不变
    "candidate": { "avg_prompt_tokens": 5400, ... },
    "eval_summary": {                                 // V2 新增
      "baseline": { "faithfulness": {"avg": 0.82, "count": 3}, "answer_relevancy": {"avg": 0.75, "count": 3} },
      "candidate": { "faithfulness": {"avg": 0.88, "count": 3}, "answer_relevancy": {"avg": 0.71, "count": 3} }
    }
  }
}
```

无评估数据时 `eval_summary` 为空对象 `{}`。

### §5.3 存储

无数据库改动。所有数据仍以 JSON 文件存储在 `.prompt-lab/`。

新增：`.prompt-lab/web.log`（Web access log，combined log format）。

## §6 API Surface

### §6.1 CLI Commands

#### V1 命令（不变）

`prompt-lab init`, `add version`, `add case`, `log`, `diff`, `cases list`, `cases import` — 签名与 V1 一致。

#### `prompt-lab run`（扩展）

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
  --eval                   Enable quality evaluation (V2 新增)
```

无 `--eval` 时行为与 V1 完全一致。

#### `prompt-lab compare`（扩展）

```
Usage: prompt-lab compare <run-id> [--format <table|json>] [--eval-only]

Options:
  --format <type>      Output format: table (default) or json
  --eval-only          Show only evaluation metrics (V2 新增)
```

当 run 结果包含 `evaluations` 时，报告自动新增质量列。

#### `prompt-lab serve`（V2 新增）

```
Usage: prompt-lab serve [--port <port>] [--host <addr>]

Options:
  --port <n>      Port number (default: 8765)
  --host <addr>   Bind address (default: 127.0.0.1)

Output:
  Prompt Lab Web UI running at http://127.0.0.1:8765
  Press Ctrl+C to stop.
```

### §6.2 REST API (V2 新增)

所有 API 返回 JSON。错误响应：`{"error": "<code>", "message": "<detail>"}`。

#### 版本管理

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

#### Case 管理

```
GET /api/cases?collection=<name>&type=<ideal|bad-case>
  → 200: [{ "id": "case-001", "type": "ideal", "collection": "books", "input": {...}, "expected_output": "...", ... }]
```

#### Run 管理

```
GET /api/runs
  → 200: [{ "run_id": "20260726T...", "baseline_version": "v1", "candidate_version": "v2", "dataset": "books", "timestamp": "...", "has_eval": true }]
```

```
GET /api/runs/{id}
  → 200: { 完整 RunResult JSON (同 result.json 格式) }
  → 404: { "error": "E_RUN_NOT_FOUND", "message": "run '...' not found" }
```

```
POST /api/runs
  Body: { "baseline": "v1", "candidate": "v2", "dataset": "books", "eval": true }
  → 200: { 完整 RunResult JSON }
  → 400: { "error": "E_VERSION_NOT_FOUND" | "E_CASE_NOT_FOUND" | "E_CONFIG_INVALID" }
  → 502: { "error": "E_PROVIDER_TIMEOUT" | "E_PROVIDER_AUTH" }
```

注意：POST `/api/runs` 是同步的——请求阻塞直到 run 完成。因为本地工具，case 数量少（<20），延迟可接受。

#### 配置

```
GET /api/config
  → 200: {
      "provider": { "base_url": "...", "model": "deepseek-v4-flash", "api_key_env": "DEEPSEEK_API_KEY" },
      "eval": { "enabled": false, "metrics": [...], "model": "deepseek-chat" },
      "run": { "timeout_seconds": 60, "concurrency": 1 }
    }
  注意：api_key 值不返回，只返回 api_key_env 变量名
```

### §6.3 Internal API (Python 模块接口)

#### V1 模块（不变）

`VersionManager`, `CaseManager`, `Provider` — 接口与 V1 Spec §6.2 一致。

#### Evaluator（V2 新增）

```python
# core/evaluator.py

class Evaluator:
    """Run DeepEval metrics against prompt outputs."""

    def __init__(
        self,
        eval_config: EvalConfig,
        provider: Provider,          # 复用 V1 Provider (OpenAI-compatible)
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

#### RunEngine（V1 扩展）

```python
# V1: RunEngine.run(baseline_prompt, candidate_prompt, cases) -> RunResult
# V2 扩展:

class RunEngine:
    def __init__(
        self,
        provider: Provider,
        config: RunConfig,
        *,
        project_root: Path | None = None,
        evaluator: Evaluator | None = None,   # V2 新增，None 时不做评估
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
        run_eval: bool = False,               # V2 新增
    ) -> RunResult: ...
```

#### ReportBuilder（V1 扩展）

```python
class ReportBuilder:
    @staticmethod
    def build_table(run_result: RunResult) -> str: ...  # V2: 自动检测 eval 数据

    @staticmethod
    def build_json(run_result: RunResult) -> str: ...    # V1 不变

    @staticmethod
    def build_eval_summary(run_result: RunResult) -> str:
        """Render eval-only summary table (V2 新增)."""
        ...
```

#### Web Server（V2 新增）

```python
# web/server.py

def create_app(project_root: Path) -> FastAPI:
    """Create FastAPI app with REST API + SPA static files."""
    ...
```

## §7 Error Model

### V1 错误码（不变）

`E_VERSION_NOT_FOUND`, `E_CASE_NOT_FOUND`, `E_PROVIDER_TIMEOUT`, `E_PROVIDER_AUTH`, `E_PROVIDER_RATE_LIMIT`, `E_EMPTY_OUTPUT`, `E_CONFIG_INVALID`, `E_ALREADY_EXISTS` — 语义与 V1 一致。

### V2 新增错误码

| 错误码 | 含义 | 可重试 | 用户可见消息 |
|--------|------|--------|------------|
| `E_EVAL_NOT_INSTALLED` | `--eval` 启用但 DeepEval 未安装 | 否 | `Error: evaluation requires DeepEval. Install with: pip install prompt-lab[eval]` |
| `E_EVAL_TIMEOUT` | 评估 LLM 调用超时 | 否 | `Warning: eval timed out for case-001, metric faithfulness. Marked as error.` |
| `E_EVAL_MISSING_EXPECTED` | 指标需要 expected_output 但 case 未定义 | 否 | （静默跳过，记录为 `skipped`，不报错） |
| `E_EVAL_INTERNAL` | DeepEval 内部异常 | 否 | `Warning: eval error for case-001, metric faithfulness: <detail>` |
| `E_RUN_NOT_FOUND` | Run ID 不存在 | 否 | `Error: run '<id>' not found.` |

### 传播规则

- **评估错误不中断 run**：单个 case 的单个指标失败（timeout/internal error）→ 记录 `EvalResult(status=error)`，继续下一个
- **评估错误不重试**：与 Provider 的 retry 逻辑不同，评估是 advisory 的，一次失败就标记 error
- **DeepEval 未安装**：在 CLI 解析阶段报错退出（不进入 run）
- **Web API 错误**：返回 HTTP 状态码 + JSON error body（§6.2）

## §8 Failure Modes

| 场景 | 检测信号 | 恢复 |
|------|---------|------|
| DeepEval 包未安装但 `--eval` 启用 | `ImportError` at evaluator 初始化 | CLI 报错退出，提示 `pip install prompt-lab[eval]` |
| 评估 LLM API 超时（单指标） | 评估 Provider.call() 超时 | 该指标标记 `EvalResult(status=error)`，run 继续 |
| 评估 LLM 返回不可解析结果 | DeepEval 内部 `ValueError` / `TypeError` | 该指标标记 `error`，run 继续 |
| Web 服务器端口被占用 | uvicorn 启动报 `OSError: address already in use` | CLI 报错退出，提示换端口 |
| POST /api/runs 触发的 run 部分失败 | result.json 中 case 有 error | API 返回 200 + 完整 result（含 error case），不返回 5xx |
| React build 产物缺失（开发模式未 build） | StaticFiles 目录不存在 | FastAPI 返回 JSON 提示：`{"error": "E_FRONTEND_NOT_BUILT", "message": "Run: cd web/frontend && npm run build"}` |
| V1 result.json 读取（向后兼容） | `evaluations` 字段不存在 | `CaseResult` 构造时 `evaluations` 默认空列表 |

## §9 Performance Budget

| 指标 | 目标 | 测量方式 |
|------|------|---------|
| Web UI 页面加载（首次） | p95 < 500ms | 浏览器 DevTools Network |
| Web UI 页面加载（SPA 路由切换） | p95 < 50ms | DevTools（纯前端渲染） |
| REST API GET 端点 | p95 < 100ms | FastAPI middleware 记录 `duration_ms` |
| REST API POST /api/runs | 取决于 LLM 调用 | 同 V1 run 性能 |
| DeepEval 单指标评估 | p95 < 30s, timeout 30s | EvalResult 记录的 `duration_ms` |
| 10 case × 3 metric eval | < 10 分钟（串行） | run_completed.duration_ms |
| 评估 API 成本（10 case × 2 版本 × 3 metric） | < $0.30 | eval LLM `prompt_tokens` × 定价 |
| Web 服务器内存 | < 100MB | `ps aux` |

## §10 Security & Privacy

### 认证

**无应用层认证。** Web 服务器仅绑定 `127.0.0.1`，只有本机可访问。

### 授权

| 角色 | 可访问 | 不可访问 |
|------|--------|---------|
| 本机用户 | 所有 CLI 命令 + Web UI + 所有 API 端点 | — |

无 RBAC。工具假设使用者就是机器拥有者。

### 敏感数据

| 数据 | 敏感级别 | 保护措施 |
|------|---------|---------|
| API key（生成 + 评估） | 高 | 仅从环境变量读取。Web API 返回 `api_key_env` 变量名，**不返回值** |
| Prompt 内容 | 中 | 本地存储。Web access log 记录请求路径，**不记录请求体** |
| Run 结果 | 中 | 本地存储，`.prompt-lab/runs/` 默认在 `.gitignore` 中 |
| Case 输入 | 低 | 本地存储 |
| 评估结果 | 低 | 本地存储 |

### 审计

- Web 服务器 access log：`.prompt-lab/web.log`（combined log format），记录 method/path/status/duration，**不含请求体**
- 版本注册和 run 触发事件写入 `events.jsonl`
- 所有审计数据在本地，保留期由用户自行管理

## §11 Open Questions

| # | 问题 | 决策 | 截止日 |
|---|------|------|--------|
| 1 | DeepEval 的 GEval 指标如何接收自定义 criteria？ | **决策**：通过 `EvalMetricConfig.params` 字典传入 `criteria` 字符串。Evaluator 在构造 DeepEval `GEval` 实例时传递。需要实测 DeepEval API 确认参数名。 | Spec 签字时 ✅（实现时验证） |
| 2 | POST /api/runs 同步阻塞 vs 异步轮询？ | **决策**：V2 用同步阻塞。case 数量 < 20，LLM 调用 < 5 分钟，HTTP 超时设 10 分钟。异步轮询增加复杂度（job queue + 状态查询），V2 不做。如果未来 case 规模 > 50 再评估。 | 2026-07-26 ✅ |
| 3 | React SPA 构建产物如何分发？ | **决策**：`web/frontend/dist/` 目录由 `npm run build` 生成，提交到 git。FastAPI 用 `StaticFiles` 托管。用户安装后无需 Node.js（除非开发前端）。开发时用 Vite dev server proxy。 | 2026-07-26 ✅ |
| 4 | DeepEval 评估模型是否复用生成 Provider 的 API key？ | **决策**：独立配置 `eval.api_key_env`。用户可配置相同的 env var（复用 key）或不同的（独立 key）。默认值与 provider 的 `api_key_env` 相同。 | 2026-07-26 ✅ |

## §12 References

- **Positioning Memo**: [prompt_lab_positioning_v1.0_2026-07-25.zh.md](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.zh.md)
- **PRD v2.0**: [prompt_lab_prd_v2.0_2026-07-26.zh.md](../01-prd/prompt_lab_prd_v2.0_2026-07-26.zh.md)
- **前序 Spec v1.0**: [prompt_lab_spec_v1.0_2026-07-25.zh.md](./prompt_lab_spec_v1.0_2026-07-25.zh.md)
- **外部标准**:
  - [DeepEval 文档](https://docs.confident-ai.com/) — 评估指标 API
  - [FastAPI 文档](https://fastapi.tiangolo.com/) — Web 框架
  - [Vite 文档](https://vitejs.dev/) — 前端构建工具
  - [DeepSeek API Docs](https://api-docs.deepseek.com/) — provider 参数
- **Kanban**: github.com/Ezio0/prompt-lab

---

签字：待 Ezio 审阅
