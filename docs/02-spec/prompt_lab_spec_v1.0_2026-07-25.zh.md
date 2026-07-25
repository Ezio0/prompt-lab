# Prompt Lab Technical Spec

**项目**: Prompt Lab
**日期**: 2026-07-25
**版本**: v1.0
**PRD**: [prompt_lab_prd_v1.0_2026-07-25.zh.md](../01-prd/prompt_lab_prd_v1.0_2026-07-25.zh.md)
**Positioning**: [prompt_lab_positioning_v1.0_2026-07-25.zh.md](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.zh.md)

---

## §1 Overview

Prompt Lab 是一个本地 CLI 工具，让开发者把 prompt 迭代从试错变成受控实验：注册版本、定义 case、跑 A/B 对比、用数据决定上不上线。

**消费者**：开发者（通过终端 CLI）

**系统上下文**：

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

引用 [PRD §4 功能需求](../01-prd/prompt_lab_prd_v1.0_2026-07-25.zh.md#4-功能需求)。

1. **版本管理**：每次 prompt 改动注册为不可变版本，支持 diff 和历史查看
2. **Case 管理**：支持理想态 case 和 bad case，可分组管理和批量导入
3. **A/B 对比**：同一 case 集合并行跑两个版本，记录完整指标（token、延迟、输出）
4. **对比报告**：终端表格 + JSON 双模式输出，逐 case diff + 汇总统计
5. **Provider 适配**：v1 支持 OpenAI 兼容 API，可配置 model / params / thinking mode

## §3 Non-Goals

镜像 [PRD §10 非目标](../01-prd/prompt_lab_prd_v1.0_2026-07-25.zh.md#10-非目标)。

1. 不做 prompt 自动优化（见 PRD §10.1）
2. 不做线上可观测性 / trace 监控（见 PRD §10.2）
3. 不做自定义评估指标引擎（见 PRD §10.3）
4. 不做 Web UI（见 PRD §10.4）
5. 不做 prompt 托管 / registry 服务（见 PRD §10.5）

## §4 Architecture

### §4.1 组件

| 组件 | 职责 | 拥有的数据 |
|------|------|-----------|
| **CLI Entry** (`cli/`) | 命令解析、参数校验、调用核心模块、输出格式化 | 无 |
| **Version Manager** (`core/version_manager.py`) | 版本注册、存储、查询、diff | `.prompt-lab/versions/` |
| **Case Manager** (`core/case_manager.py`) | Case 增删查、分组、导入 | `.prompt-lab/cases/` |
| **Run Engine** (`core/run_engine.py`) | A/B 执行：渲染 prompt → 调 LLM → 记录指标 | `.prompt-lab/runs/` |
| **Provider Adapter** (`core/provider.py`) | OpenAI 兼容 API 调用、参数封装、错误处理 | 无 |
| **Report Builder** (`core/report.py`) | 从 run 结果生成对比报告（表格 + JSON） | 无 |
| **Config** (`core/config.py`) | 读取 `prompt-lab.yaml`、解析 provider 设置 | `prompt-lab.yaml` |

### §4.2 数据流

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

### §4.3 部署拓扑

| 组件 | 运行位置 |
|------|---------|
| CLI + Core | 用户本地终端（Python 进程） |
| `.prompt-lab/` | 用户项目目录（本地文件系统） |
| LLM Provider | 外部 HTTP API |

无服务端组件。所有逻辑在用户机器上运行。

## §5 Data Model

所有数据以文件形式存储在 `.prompt-lab/` 下，无数据库。

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
  "change_note": "精简理论框架描述，砍掉学术引用",
  "prompt_file": "prompts/discovery.txt"
}
```

存储：`.prompt-lab/versions/v2.json`

### §5.2 Case

```json
{
  "id": "case-001",
  "type": "ideal",
  "input": {
    "known_models": "- 「思考，快与慢」→ 双系统认知",
    "thinking_patterns": "- 隐藏规则决定命运 (3 books)",
    "familiar_domains": "心理学 (5), 经济学 (3)",
    "n": 3
  },
  "expected_output": null,
  "expected_output_note": "推荐结果应包含跨领域认知模型，hook 信息密集不含营销词汇",
  "collection": "book-recommendation"
}
```

bad case 类型：
```json
{
  "id": "case-005",
  "type": "bad-case",
  "input": { ... },
  "actual_output": "你的大脑并不比石器时代的祖先更聪明——让你统治地球的...",
  "issue": "hook 使用营销词汇和悬念句式",
  "collection": "book-recommendation"
}
```

存储：`.prompt-lab/cases/<collection>/<case-id>.json`

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

存储：`.prompt-lab/runs/<run-id>/result.json`

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

Prompt Lab 是 CLI 工具，"API" 是命令行接口。

### §6.1 CLI Commands

#### `prompt-lab init`

初始化 Prompt Lab 项目。

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

注册一个 prompt 版本。

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

列出所有版本。

```
Usage: prompt-lab log [--limit <n>]

Output (table):
  Version  | Date                | Author | Changed Var | Note
  v2       | 2026-07-25 10:00    | ezio   | prompt      | 精简理论框架描述
  v1       | 2026-07-24 15:00    | ezio   | -           | initial version
```

#### `prompt-lab diff <v1> <v2>`

显示两个版本之间的文本差异。

```
Usage: prompt-lab diff <version_a> <version_b>

Output: unified diff format
```

#### `prompt-lab add case <id>`

添加一个 case。

```
Usage: prompt-lab add case <id> --file <path> --collection <name> --type <ideal|bad-case>

Required:
  --file <path>         Path to case JSON file
  --collection <name>   Collection name
  --type <type>         Case type: ideal or bad-case
```

#### `prompt-lab cases list`

列出 case。

```
Usage: prompt-lab cases list [--collection <name>] [--type <ideal|bad-case>]

Output (table):
  ID       | Type      | Collection           | Note
  case-001 | ideal     | book-recommendation  | 跨领域认知模型
  case-005 | bad-case  | book-recommendation  | hook 使用营销词汇
```

#### `prompt-lab run`

执行 A/B 对比运行。

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

生成对比报告。

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

### §6.2 Internal API (Python 模块接口)

供编程式使用和测试调用。

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

| 错误码 | 含义 | 可重试 | 用户可见消息 |
|--------|------|--------|------------|
| `E_VERSION_NOT_FOUND` | 版本不存在 | 否 | `Error: version 'v3' not found. Run 'prompt-lab log' to see available versions.` |
| `E_CASE_NOT_FOUND` | Case 集合或 case 不存在 | 否 | `Error: dataset 'books' not found. Run 'prompt-lab cases list' to see collections.` |
| `E_PROVIDER_TIMEOUT` | LLM API 超时 | 是 | `Warning: LLM call timed out for case-001 (60s). Retrying...` |
| `E_PROVIDER_AUTH` | API key 无效或过期 | 否 | `Error: provider authentication failed. Check your API key env var.` |
| `E_PROVIDER_RATE_LIMIT` | API 限流 | 是 | `Warning: rate limited. Waiting 2s before retry...` |
| `E_EMPTY_OUTPUT` | LLM 返回空 content | 否 | `Warning: empty output for case-001, version v2 (finish_reason=length)` |
| `E_CONFIG_INVALID` | 配置文件格式错误 | 否 | `Error: prompt-lab.yaml is invalid: <details>` |
| `E_ALREADY_EXISTS` | 版本名已存在 | 否 | `Error: version 'v2' already exists. Use a different name.` |

传播规则：
- `E_PROVIDER_TIMEOUT` 和 `E_PROVIDER_RATE_LIMIT`：重试 3 次，指数退避（1s, 2s, 4s）
- 其他错误：不重试，记录到 events.jsonl，继续处理下一个 case
- 单个 case 失败不中断整个 run

## §8 Failure Modes

| 场景 | 检测信号 | 恢复 |
|------|---------|------|
| LLM API 不可用（网络断、服务商宕机） | `httpx.ConnectError` / `httpx.TimeoutException` | 重试 3 次；全失败则该 case 标记 `E_PROVIDER_TIMEOUT`，run 继续 |
| API key 无效 | HTTP 401 | 不重试，报错退出，提示检查环境变量 |
| Case 输入变量与 prompt 模板占位符不匹配 | 渲染时 `KeyError` | 该 case 标记 `E_CASE_FORMAT`，跳过，run 继续 |
| 磁盘空间不足，写入失败 | `OSError` 写入异常 | 报错退出，提示清理 `.prompt-lab/runs/` |

## §9 Performance Budget

| 指标 | 目标 | 测量方式 |
|------|------|---------|
| 单 case LLM 调用 | p95 < 30s, timeout 60s | Run result 中 `latency_ms` |
| 10 case A/B run（串行） | < 5 分钟 | `run_completed.duration_ms` |
| CLI 命令启动（非 LLM 调用） | < 500ms | 手动计时 |
| 本地文件读写 | < 100ms per operation | 手动计时 |
| API 成本（10 case × 2 版本） | < $0.10 | `prompt_tokens` × provider 定价 |

## §10 Security & Privacy

### 认证

无应用层认证（本地 CLI 工具）。LLM API 认证通过环境变量传入 provider。

### 敏感数据

| 数据 | 敏感级别 | 保护措施 |
|------|---------|---------|
| API key | 高 | 只从环境变量读取，不写入任何文件 |
| Prompt 内容 | 中（可能含业务逻辑） | 本地存储，`.prompt-lab/` 在 `.gitignore` 中可选排除 |
| Run 结果 | 中（含 LLM 输出） | 本地存储，`.prompt-lab/runs/` 默认排除出 git |
| Case 输入 | 低（测试数据） | 本地存储 |

### 审计

版本变更和 run 记录都带时间戳和作者，可审计。无集中式审计日志（本地工具）。

## §11 Open Questions

| # | 问题 | 决策 | 截止日 |
|---|------|------|--------|
| 1 | Prompt 模板渲染使用什么引擎？（Jinja2 vs str.format vs 自定义） | **决策**：v1 用 Python `str.format()`，覆盖 `{variable}` 占位符。不引 Jinja2 依赖，保持零外部模板依赖。如需条件逻辑（`{% if %}`），v2 再评估。 | 2026-07-25 ✅ |
| 2 | 版本数据存储用文件还是 SQLite？ | **决策**：v1 用 JSON 文件。版本数量预期 < 100，文件够用且 git-friendly。SQLite 到 v2 再评估（需要查询和索引时）。 | 2026-07-25 ✅ |
| 3 | 并发运行支持到什么程度？ | **决策**：v1 默认串行（`concurrency: 1`）。Run Engine 内部用 asyncio，并发能力预留但 CLI 默认不开。避免 API 限流问题。 | 2026-07-25 ✅ |

## §12 References

- **Positioning Memo**: [prompt_lab_positioning_v1.0_2026-07-25.zh.md](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.zh.md)
- **PRD**: [prompt_lab_prd_v1.0_2026-07-25.zh.md](../01-prd/prompt_lab_prd_v1.0_2026-07-25.zh.md)
- **外部标准**: [DeepSeek API Docs](https://api-docs.deepseek.com/)（provider 参数）、[OpenAI API Reference](https://platform.openai.com/docs/api-reference)（兼容协议基础）
- **Kanban**: 待注册

---

签字：待 Ezio 审阅
