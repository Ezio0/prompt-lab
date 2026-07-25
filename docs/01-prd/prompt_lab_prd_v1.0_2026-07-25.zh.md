# Prompt Lab PRD

**项目**: Prompt Lab
**日期**: 2026-07-25
**版本**: v1.0
**Positioning**: [prompt_lab_positioning_v1.0_2026-07-25.zh.md](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.zh.md)

---

## §1 产品背景

在 LLM 应用开发中，prompt 是核心生产资产，但它的迭代方式极其原始：开发者在代码里改一个字符串，肉眼扫几条输出，感觉差不多就提交。没有版本历史，没有验证集对比，没有量化指标。

这个痛点在 [Positioning Memo §WHY](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.zh.md#why) 中已定义：改 prompt 随意，效果好坏全靠猜。本文档不重述。

Prompt Lab 的目标：把 prompt 迭代从试错变成受控实验。具体场景见 [Positioning Memo §WHO](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.zh.md#who)。

## §2 目标用户

引用 [Positioning Memo §WHO](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.zh.md#who)。

| 角色 | 描述 | v1 目标 |
|------|------|---------|
| **开发者** | 在项目中集成 LLM、编写和维护 prompt 的工程师。能跑 CLI、能写配置文件。 | ✅ v1 核心 |
| **PM / 运营** | 不写代码，但需要调整 prompt 文字和输出风格。需要 Web UI 修改 prompt、查看对比结果。 | ⏳ v2（v1 先做 CLI + 对比报告，Web UI 排后） |

## §3 用户故事

### US-1: 从零初始化 prompt 项目

> 作为开发者，我想要在项目里初始化 Prompt Lab，以便开始系统化管理 prompt 版本。

验收标准：
- [ ] `prompt-lab init` 在当前目录生成配置文件和目录结构
- [ ] 配置文件包含 LLM provider 设置（base_url、model、api_key 环境变量名）
- [ ] 初始化后可以立即注册第一个 prompt 版本

### US-2: 注册 prompt 版本

> 作为开发者，我想要把每次 prompt 改动注册为一个版本，以便追踪历史和回溯。

验收标准：
- [ ] `prompt-lab add version <name> --file <path>` 将一个 prompt 文件注册为新版本
- [ ] 每个版本记录：内容 hash、时间戳、作者、变更说明（可选）
- [ ] `prompt-lab log` 列出所有版本及其元数据
- [ ] 版本之间可以 diff

### US-3: 定义理想态 case

> 作为开发者，我想要为 prompt 定义理想态 case（输入 + 期望输出），以便建立验证基准。

验收标准：
- [ ] case 文件格式支持：输入（变量键值对）+ 理想输出（手写或 AI 协作生成）
- [ ] 支持从线上 bad case 导入（输入 + 问题说明）
- [ ] case 集合可以分组管理（如 "book-recommendation"、"summarization"）
- [ ] `prompt-lab cases list` 列出所有 case 及其类型（ideal / bad-case）

### US-4: 运行 A/B 对比

> 作为开发者，我想要用同一组 case 同时跑两个 prompt 版本，以便量化对比效果差异。

验收标准：
- [ ] `prompt-lab run --baseline <v1> --candidate <v2> --dataset <cases>` 执行对比
- [ ] 每个 case 两个版本各跑一次，输出隔离
- [ ] 对比维度：输出文本 diff、token 消耗、延迟（ms）、content 非空率
- [ ] 支持配置 LLM provider 参数（model、max_tokens、temperature、thinking mode）
- [ ] 跑完后结果持久化到本地（可后续查看）

### US-5: 查看对比报告

> 作为开发者，我想要看一份结构化的对比报告，以便用数据决定哪个版本更好。

验收标准：
- [ ] `prompt-lab compare <run-id>` 输出对比报告
- [ ] 报告包含：逐 case 的 side-by-side 输出对比、汇总统计表（平均 token、平均延迟、非空率）
- [ ] 支持 JSON 输出（便于管道处理）
- [ ] 支持终端表格输出（便于人工查看）

### US-6: 支持单一变量控制

> 作为开发者，我想要在对比时明确标注"改了什么"，以便知道效果差异归因于哪个变量。

验收标准：
- [ ] `prompt-lab add version` 时可关联 `--changed-from <prev_version>` 并填写变更说明
- [ ] 对比报告显示 baseline 和 candidate 的变更说明
- [ ] 非 prompt 变量的变更（model、参数）也在版本元数据中记录

### §3.x Critical User Journeys (CUJ)

| CUJ ID | 描述 | 涉及模块 | 优先级 |
|--------|------|---------|--------|
| CUJ-1 | 初始化项目 → 注册 prompt → 定义 case → 跑 A/B → 看报告 → 决定上不上 | CLI 全链路 | P0 |
| CUJ-2 | 发现 bad case → 导入为 case → 改 prompt → 注册新版本 → A/B 验证 | CLI 全链路 | P0 |
| CUJ-3 | 换模型 → 注册新版本（非 prompt 变更）→ A/B 验证回归 | CLI + provider config | P1 |

## §4 功能需求

### FR-1: 项目初始化

`prompt-lab init` 在当前目录生成：
- `.prompt-lab/` 目录（存储版本、case、运行结果）
- `prompt-lab.yaml` 配置文件（provider 设置、默认参数）
- `.gitignore`（排除 `.prompt-lab/runs/`）

### FR-2: Prompt 版本管理

- 版本存储在 `.prompt-lab/versions/` 下，每个版本一个 JSON 文件
- 版本内容：prompt 文本、content hash、时间戳、作者、变更说明、关联的上游版本
- `prompt-lab log` 按时间倒序列出版本
- `prompt-lab diff <v1> <v2>` 输出文本 diff

### FR-3: Case 管理

- Case 存储在 `.prompt-lab/cases/` 下，按集合分组
- Case 格式：`{ id, type (ideal|bad-case), input: {var: val}, expected_output?: str, note?: str }`
- 支持从 JSON 文件批量导入
- `prompt-lab cases list [--type ideal|bad-case]` 列出 case

### FR-4: A/B 运行引擎

- `prompt-lab run --baseline <v> --candidate <v> --dataset <cases>` 执行对比
- 对每个 case：用 baseline prompt 渲染 → 调 LLM → 记录输出；用 candidate prompt 重复
- 记录指标：output_text、prompt_tokens、completion_tokens、latency_ms、finish_reason、error
- 结果存储在 `.prompt-lab/runs/<run-id>/` 下

### FR-5: 对比报告

- `prompt-lab compare <run-id>` 生成报告
- 终端模式：表格输出汇总统计 + 逐 case diff
- JSON 模式：完整结构化输出
- 汇总指标：平均 prompt_tokens、平均 completion_tokens、平均 latency_ms、content 非空率、错误率

### FR-6: LLM Provider 适配

- v1 支持 OpenAI 兼容 API（覆盖 OpenAI、DeepSeek、Anthropic via proxy、本地 vLLM 等）
- 配置项：base_url、api_key（环境变量名）、model、default params（max_tokens、temperature、thinking mode）
- 每个 case 运行使用配置的 provider 参数，也可在 run 命令中覆盖

### FR-7: 变更追踪

- `prompt-lab add version` 支持 `--note "精简理论框架描述"` 记录变更说明
- 支持 `--changed-var prompt|model|params|data` 标记变更类型
- 对比报告中显示变更类型和说明，帮助归因

## §5 非功能需求

| 维度 | 要求 |
|------|------|
| 性能 | 单 case LLM 调用超时 60s。并发运行多个 case（默认串行，可配置并发数） |
| 安全 | API key 只从环境变量读取，不存储在配置文件中 |
| 隐私 | 所有数据存储在本地 `.prompt-lab/`，不发送到任何外部服务 |
| 可扩展 | Provider 适配层可插拔，后续可加非 OpenAI 兼容的 provider |
| 可观测 | 每次运行记录完整日志（时间戳、参数、结果），可审计 |
| 可回滚 | 版本不可变，不可删除（只能新增）。回滚 = promote 旧版本 |

## §6 数据迁移

不适用。新项目，无存量数据。首次运行 `prompt-lab init` 创建全新结构。

## §7 数据可观测性

Prompt Lab 本身产生的数据（供项目内分析和外部消费）：

- **运行记录**：每次 A/B run 生成结构化 JSON，包含每个 case 的完整输入输出和指标
- **版本历史**：所有 prompt 版本及其元数据
- **Case 库**：理想态 case 和 bad case 的累积记录

示例查询：`jq '.cases[] | select(.metrics.completion_tokens > 1000)' .prompt-lab/runs/latest/results.json` — 找出 token 消耗过高的 case。

## §8 前端改动

v1 无前端。纯 CLI 工具。

v2 规划 Web UI（不在本期范围）。

## §9 风险

| 风险 | 等级 | 缓解 |
|------|------|------|
| LLM 输出不确定性导致 A/B 结果不可复现 | 中 | 每个 case 支持配置 temperature=0（默认）；多次运行取均值 |
| Provider API 变更导致适配层失效 | 低 | 适配层抽象化，只依赖 OpenAI 兼容协议 |
| Case 积累需要人工投入，用户可能跳过 | 中 | 提供从线上日志导入 bad case 的工具，降低 case 创建成本 |

## §10 非目标

1. **不做 prompt 自动优化** — v1 不自动搜索或生成"更好的"prompt。自动优化是未来方向，但需要版本管理和验证集作为基座。（见 [Positioning §ANTI-POSITIONING](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.zh.md#anti-positioning)）
2. **不做线上可观测性 / trace 监控** — 不监控生产环境 LLM 调用。那是 Langfuse / Phoenix 的领域。我们聚焦上线前的决策。
3. **不做自定义评估指标引擎** — 不自建评估指标库。v2 规划集成 DeepEval 作为评估后端。
4. **不做 Web UI** — v1 是纯 CLI。Web UI 排到 v2，满足非技术角色需求。
5. **不做 prompt 托管 / registry 服务** — 不提供线上 prompt 存储和分发 API。版本管理基于本地文件 + git。

## §11 验收标准

### 功能
- [ ] `prompt-lab init` 成功初始化项目，配置文件可编辑
- [ ] `prompt-lab add version` 注册版本，`prompt-lab log` 可查看历史
- [ ] `prompt-lab run` 执行 A/B 对比，输出结果文件
- [ ] `prompt-lab compare` 生成可读的对比报告
- [ ] `prompt-lab diff` 显示版本间文本差异

### 性能
- [ ] 单 case LLM 调用在 60s 内完成或超时
- [ ] 10 个 case 的 A/B 运行在 5 分钟内完成（串行）

### 测试
- [ ] 核心模块单元测试覆盖率 ≥ 80%
- [ ] CLI 端到端测试覆盖 CUJ-1 和 CUJ-2

### 回滚
- [ ] 版本不可变，任何错误操作可通过注册新版本恢复

## §12 可观测性需求

### §12.1 新增事件

Prompt Lab 是 CLI 工具，"事件"以运行日志形式存储在 `.prompt-lab/runs/` 下。

| 事件 | 触发时机 | 关键字段 | 用途 | 优先级 |
|------|---------|---------|------|--------|
| `run_started` | A/B 运行开始 | baseline_version, candidate_version, dataset, provider_config, timestamp | 审计 | P0 |
| `case_completed` | 单个 case 完成 | case_id, version, output, prompt_tokens, completion_tokens, latency_ms, finish_reason | 对比数据 | P0 |
| `case_failed` | 单个 case 失败 | case_id, version, error_type, error_message | 诊断 | P0 |
| `run_completed` | A/B 运行完成 | run_id, total_cases, success_count, fail_count, duration_ms | 审计 | P0 |

### §12.2 复用现有事件

不适用。新项目，无现有事件。

### §12.3 事件 schema

所有事件存储为 JSON 文件（`.prompt-lab/runs/<run-id>/events.jsonl`，JSONL 格式）。无数据库 schema。

### §12.4 验收标准

- [ ] 每次 `prompt-lab run` 生成完整的 events.jsonl
- [ ] `case_completed` 覆盖所有成功执行的 case（100%）
- [ ] `case_failed` 覆盖所有失败的 case（100%）

### §12.5 隐私考量

- prompt 内容可能包含用户数据（取决于使用场景），存储在本地 `.prompt-lab/`
- `.gitignore` 默认排除 `.prompt-lab/runs/`（运行结果不进 git）
- API key 只从环境变量读取，不写入任何文件

## §13 关联

- **Positioning Memo**: [prompt_lab_positioning_v1.0_2026-07-25.zh.md](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.zh.md)
- **Kanban**: 新项目，待注册
- **前序 PRD**: 无（首版）
- **大框架**: Prompt Lab v1.0

---

签字：待 Ezio 审阅
