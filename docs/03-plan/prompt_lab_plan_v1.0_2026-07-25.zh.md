# Prompt Lab Implementation Plan

**项目**: Prompt Lab
**日期**: 2026-07-25
**版本**: v1.0
**Spec**: [prompt_lab_spec_v1.0_2026-07-25.zh.md](../02-spec/prompt_lab_spec_v1.0_2026-07-25.zh.md)
**PRD**: [prompt_lab_prd_v1.0_2026-07-25.zh.md](../01-prd/prompt_lab_prd_v1.0_2026-07-25.zh.md)

---

## §1 概述

引用 [Spec §1 Overview](../02-spec/prompt_lab_spec_v1.0_2026-07-25.zh.md#1-overview)。

本计划将 Spec 中的 7 个模块拆分为可独立执行的 Task，按依赖顺序排列。

## §2 Phases

| Phase | 目标 | Tasks |
|-------|------|-------|
| **P0: 项目脚手架** | Python 项目结构、依赖管理、CLI 入口骨架 | T-001 |
| **P1: 核心数据层** | Config + Version Manager + Case Manager | T-002, T-003, T-004 |
| **P2: 执行层** | Provider Adapter + Run Engine | T-005, T-006 |
| **P3: 报告层** | Report Builder + compare 命令 | T-007 |
| **P4: 集成** | CLI 全链路串联、端到端测试 | T-008 |

## §3 Task Breakdown

### T-001: 项目脚手架 (P0, XS)

**依赖**: 无

**描述**: 搭建 Python 项目结构、pyproject.toml、CLI 入口点。

**验收标准**:
- [ ] `pyproject.toml` 配置完成（name=prompt-lab, Python ≥3.11）
- [ ] 依赖: `click` (CLI), `httpx` (HTTP), `pyyaml` (config), `rich` (terminal table)
- [ ] `prompt_lab/` 包结构: `__init__.py`, `cli.py`, `core/` 子包
- [ ] `prompt-lab --help` 能输出帮助信息
- [ ] `prompt-lab init` 创建 `.prompt-lab/` 目录 + `prompt-lab.yaml`
- [ ] 单元测试: test_init.py

**文件**:
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

### T-002: Config 模块 (P1, S)

**依赖**: T-001

**描述**: 读取和校验 `prompt-lab.yaml` 配置文件。

**验收标准**:
- [ ] `Config.load()` 从项目根目录读取 `prompt-lab.yaml`
- [ ] 返回 typed config 对象 (dataclass): provider settings, run settings
- [ ] API key 从环境变量读取（`api_key_env` 字段指定变量名）
- [ ] 配置缺失或格式错误时抛出 `E_CONFIG_INVALID`
- [ ] 单元测试: test_config.py (valid config, missing file, invalid yaml, missing api key)

**文件**: `prompt_lab/core/config.py`, `tests/unit/test_config.py`

### T-003: Version Manager (P1, M)

**依赖**: T-001

**描述**: Prompt 版本的注册、存储、查询、diff。

**验收标准**:
- [ ] `add_version()` 写入 JSON 到 `.prompt-lab/versions/<name>.json`
- [ ] 计算 content_hash (SHA-256)
- [ ] 版本名重复时抛出 `E_ALREADY_EXISTS`
- [ ] `get_version()` 读取并返回 Version 对象
- [ ] `list_versions()` 按时间倒序列出
- [ ] `diff()` 输出 unified diff 格式
- [ ] 版本不可变（已存在的版本不能覆盖）
- [ ] 单元测试: test_version_manager.py (add, get, list, diff, duplicate, immutability)

**文件**: `prompt_lab/core/version_manager.py`, `prompt_lab/core/models.py` (Version dataclass), `tests/unit/test_version_manager.py`

### T-004: Case Manager (P1, S)

**依赖**: T-001

**描述**: Case 的增删查、分组、批量导入。

**验收标准**:
- [ ] `add_case()` 写入 JSON 到 `.prompt-lab/cases/<collection>/<id>.json`
- [ ] `get_cases()` 按 collection 读取，可按 type 过滤
- [ ] `import_cases()` 从 JSON 文件批量导入（数组格式）
- [ ] Case 类型校验: 必须是 `ideal` 或 `bad-case`
- [ ] 单元测试: test_case_manager.py (add, get, filter, import, invalid type)

**文件**: `prompt_lab/core/case_manager.py`, `prompt_lab/core/models.py` (Case dataclass), `tests/unit/test_case_manager.py`

### T-005: Provider Adapter (P2, S)

**依赖**: T-002

**描述**: OpenAI 兼容 API 调用封装。

**验收标准**:
- [ ] `Provider.call()` 发送 POST 到 `/chat/completions`
- [ ] 支持 params: model, max_tokens, temperature, thinking mode
- [ ] 返回 ProviderResponse (content, prompt_tokens, completion_tokens, finish_reason)
- [ ] HTTP 401 → raise ProviderAuthError (不可重试)
- [ ] HTTP 429 → raise ProviderRateLimitError (可重试)
- [ ] Timeout → raise ProviderTimeoutError (可重试)
- [ ] 其他 HTTP 5xx → raise ProviderError (可重试)
- [ ] 单元测试: test_provider.py (mock httpx, 所有状态码路径)

**文件**: `prompt_lab/core/provider.py`, `prompt_lab/core/models.py` (ProviderResponse), `tests/unit/test_provider.py`

### T-006: Run Engine (P2, M)

**依赖**: T-003, T-004, T-005

**描述**: A/B 对比执行引擎。

**验收标准**:
- [ ] `RunEngine.run()` 接收 baseline_prompt, candidate_prompt, cases 列表
- [ ] 每个 case: 用 `str.format()` 渲染 prompt → 调 Provider → 记录指标
- [ ] 记录: output, prompt_tokens, completion_tokens, latency_ms, finish_reason, error
- [ ] 单 case 失败不中断 run
- [ ] Provider timeout/rate-limit 重试 3 次，指数退避
- [ ] 结果写入 `.prompt-lab/runs/<run-id>/result.json`
- [ ] events.jsonl 同步写入
- [ ] run 完成后返回 RunResult 对象（含 summary 统计）
- [ ] 单元测试: test_run_engine.py (mock provider, 正常/失败/重试/空输出)

**文件**: `prompt_lab/core/run_engine.py`, `prompt_lab/core/models.py` (RunResult, CaseResult), `tests/unit/test_run_engine.py`

### T-007: Report Builder (P3, S)

**依赖**: T-006

**描述**: 从 RunResult 生成对比报告。

**验收标准**:
- [ ] `build_table()` 使用 rich 库输出终端表格
- [ ] 表格包含: 逐 case 的 token/延迟对比 + 汇总统计
- [ ] `build_json()` 输出完整 JSON
- [ ] 汇总指标: avg_prompt_tokens, avg_latency_ms, non_empty_rate, error_rate
- [ ] Delta 列显示百分比变化
- [ ] 单元测试: test_report.py (table output, json output, empty results)

**文件**: `prompt_lab/core/report.py`, `tests/unit/test_report.py`

### T-008: CLI 集成 + E2E (P4, M)

**依赖**: T-003, T-004, T-006, T-007

**描述**: 将所有模块串联到 CLI 命令，端到端测试。

**验收标准**:
- [ ] `prompt-lab add version` → 调 VersionManager
- [ ] `prompt-lab log` → 格式化输出版本列表
- [ ] `prompt-lab diff` → 输出 unified diff
- [ ] `prompt-lab add case` → 调 CaseManager
- [ ] `prompt-lab cases list` → 格式化输出 case 列表
- [ ] `prompt-lab run` → 调 RunEngine，输出 run summary
- [ ] `prompt-lab compare` → 调 ReportBuilder
- [ ] E2E 测试覆盖 CUJ-1: init → add version → add case → run → compare
- [ ] 所有命令的错误路径有友好提示

**文件**: `prompt_lab/cli.py` (扩展), `tests/unit/test_cli.py`, `tests/integration/test_e2e.py`

## §4 依赖图

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

无环依赖。T-001 是所有 task 的前置。

## §5 执行策略

- 实现: **Codex CLI**
- 每个 Task 完成后跑对应单元测试确认通过
- T-008 完成后跑全量测试
- 全量通过后 commit + push

## §6 预估

| Task | Size | 预估时间 |
|------|------|---------|
| T-001 | XS | 15 min |
| T-002 | S | 20 min |
| T-003 | M | 40 min |
| T-004 | S | 20 min |
| T-005 | S | 20 min |
| T-006 | M | 40 min |
| T-007 | S | 20 min |
| T-008 | M | 30 min |
| **总计** | | **~3.5 小时** |

## §7 风险

| 风险 | 缓解 |
|------|------|
| Codex 对 pyproject.toml + Click 的集成不熟悉 | Spec §6 有完整接口签名，Codex 照着实现 |
| Run Engine 的 asyncio 异步逻辑复杂 | T-006 拆成 render + call + record 三步，每步可独立测试 |

## §8 定义"完成"

- [ ] 全部 8 个 Task 的验收标准都勾完
- [ ] 全量测试通过（unit + integration）
- [ ] `prompt-lab --help` 输出完整命令列表
- [ ] CUJ-1 端到端可执行
- [ ] commit + push 到 main

## §9 History

| 日期 | 事件 |
|------|------|
| 2026-07-25 | 初始创建 |

---

签字：待 Ezio 审阅
