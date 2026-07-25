# Prompt Lab PRD v2.0

**项目**: Prompt Lab
**日期**: 2026-07-26
**版本**: v2.0
**Positioning**: [prompt_lab_positioning_v1.0_2026-07-25.zh.md](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.zh.md)
**前序 PRD**: [prompt_lab_prd_v1.0_2026-07-25.zh.md](./prompt_lab_prd_v1.0_2026-07-25.zh.md)

---

## §1 产品背景

V1 解决了 prompt 版本管理和 A/B 运行的基础设施。但 V1 的对比报告只回答了两个问题：token 便宜了吗？更快了吗？它没回答最重要的第三个问题：**新版输出质量好不好？**

这个缺口在 Positioning 的 UNDERLYING LOGIC 中已明确指出："核心是让'改 prompt 好了还是坏了'从主观感受变成数据判断。"V1 做到了结构化对比，但质量维度仍靠肉眼。

V2 的两条主线都指向同一个目标——**让闭环完整**：

1. **质量评估**：把 DeepEval 的 50+ 指标集成进 A/B 对比工作流，让报告包含量化质量分数（faithfulness、answer relevance 等）。Positioning 已指出："DeepEval 已有 50+ metrics，直接用。我们做的是把评估包进对比工作流里。"

2. **Web UI**：V1 的 PRD §2 已将 PM/运营列为 v2 目标用户。他们不写代码，但需要改 prompt 文字、查看对比结果。CLI 无法服务他们。

## §2 目标用户

引用 [Positioning Memo §WHO](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.zh.md#who)。

| 角色 | 描述 | v2 目标 |
|------|------|---------|
| **开发者** | 已在 V1 使用的 CLI 用户。 | ✅ 质量评估，通过 CLI 使用 |
| **PM / 运营** | 不写代码，但需要调整 prompt 文字和查看对比结果。需要 Web UI 修改 prompt、查看报告。 | ✅ Web UI |

## §3 用户故事

### US-7: 运行带质量评估的 A/B 对比

> 作为开发者，我想要在 A/B 对比中自动评估输出质量（faithfulness、answer relevance 等），以便用数据判断新版 prompt 质量有没有退化。

验收标准：
- [ ] `prompt-lab run` 新增 `--eval` flag，启用后对每个 case 输出执行 DeepEval 评估
- [ ] 支持在 `prompt-lab.yaml` 中配置评估指标列表和参数
- [ ] 评估指标至少支持：Faithfulness、Answer Relevancy、GEval（自定义评分标准）
- [ ] 评估需要 case 定义 `expected_output`（理想态输出）作为 ground truth
- [ ] 无 `expected_output` 的 case 跳过需要 ground truth 的指标，记录为 `skipped`
- [ ] 每个 case 的评估结果包含：指标名、分数（0-1）、可选的 reason
- [ ] 评估失败不中断 A/B run（降级为 `eval_error` 标记）

### US-8: 查看含质量分数的对比报告

> 作为开发者，我想要对比报告包含质量评估分数，以便同时看到运营指标（token/延迟）和质量指标（faithfulness 等）。

验收标准：
- [ ] `prompt-lab compare <run-id>` 报告新增质量指标列
- [ ] 终端表格模式：每个 case 显示 baseline vs candidate 的质量分数
- [ ] JSON 模式：包含完整评估结果（分数 + reason）
- [ ] 汇总统计新增 `avg_<metric>` 行（baseline 和 candidate 各一组）
- [ ] 支持 `--eval-only` 参数只输出质量指标（隐藏 token/延迟）

### US-9: 通过 Web UI 查看 prompt 版本

> 作为 PM/运营，我想要在浏览器中查看所有 prompt 版本及其内容，以便了解迭代历史。

验收标准：
- [ ] `prompt-lab serve` 启动 Web 服务器（默认 http://localhost:8765）
- [ ] 版本列表页：按时间倒序显示所有版本，含 hash、时间、作者、变更说明
- [ ] 版本详情页：显示完整 prompt 内容，支持 monospace 渲染
- [ ] 版本对比页：side-by-side 显示两个版本的 diff
- [ ] 页面加载时间 < 500ms（本地数据，无网络请求）

### US-10: 通过 Web UI 查看 A/B 对比报告

> 作为 PM/运营，我想要在浏览器中查看 A/B 对比报告，以便直观地理解两个版本的效果差异。

验收标准：
- [ ] Run 列表页：按时间倒序显示所有 run，含版本对、case 数、运行时间
- [ ] Run 详情页：展示对比报告，含运营指标（token/延迟）和质量指标（评估分数）
- [ ] 逐 case 对比视图：baseline vs candidate 的输出并排展示，质量分数高亮
- [ ] 汇总统计图表：bar chart 对比 baseline 和 candidate 的关键指标
- [ ] 支持 JSON 下载（导出完整 run 结果）

### US-11: 通过 Web UI 编辑和注册 prompt

> 作为 PM/运营，我想要在浏览器中编辑 prompt 文字并注册为新版本，以便不依赖开发者也能迭代。

验收标准：
- [ ] 版本编辑器：monospace textarea，支持变量占位符提示（`{variable_name}`）
- [ ] 注册时填写：版本名、变更说明（note）、变更类型（prompt/model/params/data）
- [ ] 注册前预览：显示与上一个版本的 diff
- [ ] 注册成功后跳转到版本列表页，新版本高亮
- [ ] 不允许覆盖已存在版本（与 CLI 一致，不可变性约束）

### §3.x Critical User Journeys (CUJ)

| CUJ ID | 描述 | 涉及模块 | 优先级 |
|--------|------|---------|--------|
| CUJ-4 | init → add version → add case (with expected_output) → run --eval → compare（含质量分数） | CLI + DeepEval 集成 | P0 |
| CUJ-5 | serve → 浏览器打开 → 查看版本列表 → 查看版本详情 → 查看 run 报告 | Web UI (只读) | P0 |
| CUJ-6 | serve → 编辑 prompt → 预览 diff → 注册新版本 → 触发 run → 查看报告 | Web UI (读写) | P1 |

## §4 功能需求

### FR-8: 评估配置

`prompt-lab.yaml` 新增 `eval` 配置块：

```yaml
eval:
  enabled: false           # 默认关闭，run --eval 开启
  metrics:
    - name: faithfulness
    - name: answer_relevancy
    - name: geval
      params:
        criteria: "Rate the response on accuracy and completeness (1-10)"
  model: deepseek-chat     # 评估使用的 LLM model（可与生成 model 不同）
  api_key_env: DEEPSEEK_API_KEY  # 评估 model 的 API key 环境变量名
```

### FR-9: 质量评估引擎

新增 `prompt_lab/core/evaluator.py` 模块：

- `Evaluator` 类：接收 `(input, actual_output, expected_output, context)` + 指标列表，返回 `EvalResult` 列表
- 每个指标返回：`metric_name`, `score` (0.0-1.0), `reason` (str, 可选), `status` (`pass` / `skipped` / `error`)
- `skipped`：case 缺少 `expected_output` 但指标需要它
- `error`：DeepEval 内部异常（如 API 超时），不中断 run
- 评估 LLM 调用复用 V1 的 Provider adapter（OpenAI 兼容格式）
- 评估 model 可与生成 model 不同（独立配置 `eval.model`）

### FR-10: 评估结果存储

- `CaseResult` 扩展：新增 `evaluations` 字段（`list[EvalResult]`），仅当 `--eval` 启用时填充
- `RunResult.summary` 扩展：新增 `eval_summary` 块，含每个指标的平均分
- `result.json` 结构保持向后兼容：无评估数据时 `evaluations` 为空列表
- `events.jsonl` 新增 `eval_completed` / `eval_skipped` / `eval_failed` 事件

### FR-11: 对比报告扩展

- `ReportBuilder.build_table()` 新增评估指标列（当 run 包含评估数据时）
- `ReportBuilder.build_json()` 包含完整评估结果
- 新增 `build_eval_summary()`：输出评估指标汇总表

### FR-12: Web API 服务层

新增 `prompt_lab/web/` 子包：

- `prompt-lab serve [--port 8765]` 启动 FastAPI 服务器
- REST API 端点：
  - `GET /api/versions` — 版本列表
  - `GET /api/versions/{id}` — 版本详情
  - `GET /api/versions/{id_a}/{id_b}/diff` — 版本 diff
  - `POST /api/versions` — 注册新版本
  - `GET /api/cases` — Case 列表（支持 `?collection=` 和 `?type=` 过滤）
  - `GET /api/runs` — Run 列表
  - `GET /api/runs/{id}` — Run 详情（含完整对比报告）
  - `POST /api/runs` — 触发新 run（同步返回结果）
  - `GET /api/config` — 当前项目配置
- API key 不通过 API 暴露（返回 `***`）
- CORS：默认仅允许 `localhost`

### FR-13: React SPA 前端

新增 `web/frontend/` 目录：

- **技术栈**：React + Vite + TypeScript + TailwindCSS
- **页面**：
  - `/versions` — 版本列表 + 版本详情 + diff 对比
  - `/runs` — Run 列表 + Run 报告详情
  - `/editor` — Prompt 编辑器（注册新版本）
- **组件**：
  - `<VersionList />` — 版本列表表格
  - `<PromptViewer />` — prompt 内容展示（monospace）
  - `<DiffViewer />` — side-by-side diff（基于 react-diff-viewer）
  - `<RunReport />` — A/B 对比报告（表格 + 汇总卡片）
  - `<EvalScoreCard />` — 质量评估分数卡片
  - `<PromptEditor />` — prompt 编辑器 + 注册表单
  - `<MetricChart />` — 指标对比 bar chart（基于 recharts）
- FastAPI 同时托管 SPA 静态文件（build 产物），单端口部署

## §5 非功能需求

引用 [Positioning §WHY NOW](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.zh.md#why-now)。

| 维度 | 要求 |
|------|------|
| 性能 | Web UI 页面加载 < 500ms。API 响应 < 100ms（本地数据）。触发 run 时 API 异步处理，支持轮询进度。DeepEval 单指标评估超时 30s。 |
| 安全 | Web 服务器默认仅绑定 `127.0.0.1`。API key 不通过 API 返回。Web UI 不传输 API key 到前端。POST `/api/runs` 需确认 prompt 版本存在。 |
| 隐私 | 所有数据仍在本地。Web 服务器不向外部发送任何数据。DeepEval 评估通过用户配置的 LLM API 进行，不经第三方。 |
| 可扩展 | 评估指标可插拔（V2 支持 DeepEval，未来可加自定义评估器）。Web API 保持 RESTful，易于扩展。 |
| 可观测 | Web 服务器输出 access log。所有 API 调用记录到 `.prompt-lab/web.log`。 |
| 可回滚 | V2 不修改 V1 的存储格式（仅扩展）。无 `--eval` 时行为与 V1 完全一致。`prompt-lab serve` 是可选功能，不影响 CLI。 |

## §6 数据迁移

**无 schema 迁移。**

V2 对 V1 的 `result.json` 结构做了**向后兼容的扩展**：
- `CaseResult` 新增 `evaluations` 字段，默认空列表
- V1 的 `result.json` 可被 V2 正常读取（`evaluations` 自动填充为空列表）
- V2 的 `result.json` 包含 `evaluations`，V1 读取时忽略该字段（dataclass 构造容忍额外字段）

**迁移策略**：无需迁移。V1 用户升级到 V2 后，历史 run 的对比报告照常显示，只是没有评估列。

## §7 数据可观测性

Prompt Lab 产生的数据（供用户分析）：

**新增数据流（V2）**：

- **评估结果**：每次 `--eval` run 生成结构化评估数据，含每个 case 的逐指标分数和 reason
- **Web 访问日志**：API 调用记录，可供审计

示例查询：
```bash
# 找出 faithfulness 分数低于 0.7 的 case
jq '.cases[] | select(.evaluations[]?.metric_name == "faithfulness" and .evaluations[]?.score < 0.7) | .case_id' \
  .prompt-lab/runs/<run-id>/result.json

# 对比 baseline 和 candidate 的平均 faithfulness
jq '.summary.eval_summary | {baseline: .baseline.faithfulness.avg, candidate: .candidate.faithfulness.avg}' \
  .prompt-lab/runs/<run-id>/result.json
```

## §8 前端改动

**V2 首次引入前端。**

### 组件清单

| 页面 | 核心组件 | UX 要点 |
|------|---------|---------|
| 版本列表 | `<VersionList />` | 表格：版本名、时间、作者、变更类型、变更说明。点击行进入详情。 |
| 版本详情 | `<PromptViewer />` | monospace 渲染 prompt 内容。变量占位符 `{xxx}` 高亮。 |
| 版本对比 | `<DiffViewer />` | side-by-side diff。变更行红绿标记。 |
| Run 列表 | `<RunList />` | 表格：run ID、版本对、case 数、有无评估、时间。点击行进入报告。 |
| Run 报告 | `<RunReport />` | 汇总卡片（token/延迟/质量分数）+ 逐 case 表格 + 输出对比。 |
| 质量分数 | `<EvalScoreCard />` | 每个指标一张卡片：分数（0-1）、状态（pass/skipped/error）、reason 折叠展开。 |
| Prompt 编辑器 | `<PromptEditor />` | monospace textarea + 变量提示 + 注册表单。预览 diff 后确认提交。 |

### UX 文案

- 空状态（无版本）：`No versions yet. Run: prompt-lab add version <name> --file prompt.txt`
- 空状态（无 run）：`No runs yet. Run: prompt-lab run --baseline <v1> --candidate <v2> --dataset <cases>`
- 评估跳过提示：`Skipped: requires expected_output (define in case)`
- 评估错误提示：`Eval error: <error message> (non-blocking)`
- 注册确认：`Register version "{name}"? This cannot be undone.`
- run 触发确认：`Run A/B comparison: {baseline} vs {candidate} on {dataset}?`

### 时区处理

- 所有时间戳使用 ISO 8601 UTC（与 V1 一致）
- Web UI 显示时转换为浏览器本地时区
- API 返回 UTC ISO 字符串，前端负责格式化

## §9 风险

| 风险 | 等级 | 缓解 |
|------|------|------|
| DeepEval 依赖过重（安装复杂、版本冲突） | 中 | 评估功能为可选依赖（`pip install prompt-lab[eval]`）。无评估依赖时 `--eval` 报错提示安装。 |
| DeepEval 评估结果不稳定（LLM-as-judge 波动） | 中 | 评估 model 默认 temperature=0。文档建议多次运行取均值。评估结果标注为 `advisory`（参考性）而非 `deterministic`。 |
| Web UI 开发周期长，阻塞 V2 发布 | 中 | Web UI 分两个 Phase 交付：P1 只读（查看版本和报告），P2 读写（编辑和触发 run）。只读即可服务 PM/运营的核心需求（查看对比结果）。 |
| React 构建产物与 FastAPI 集成复杂 | 低 | FastAPI 使用 `StaticFiles` 托管 Vite build 产物。开发时 Vite proxy 转发 API 请求到 FastAPI。 |
| 评估 LLM 调用成本（每个 case × 每个指标） | 中 | 文档标注成本估算。支持配置只在 bad-case 上运行评估。 |

## §10 非目标

1. **不做自动 prompt 优化（仍不做）** — V2 增加了质量评估能力，但不自动搜索或生成"更好的"prompt。自动优化是未来方向，但需要 V2 的评估基础设施作为基座才能开始。引用 [Positioning §ANTI-POSITIONING](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.zh.md#anti-positioning)。

2. **不做用户认证/多用户** — V2 的 Web UI 是单用户本地工具。不做登录、权限、多用户。工具运行在开发者本地机器上，用户就是开发者本人。多用户协作是未来 SaaS 方向，不在本期范围。

3. **不做自定义评估指标** — V2 集成 DeepEval 现有的 50+ 指标。不自建评估指标引擎（复用 DeepEval）。未来可考虑支持自定义评估器接口。

4. **不做 CI/CD 集成** — V2 不提供 GitHub Actions 集成、PR check、自动门禁等功能。这些是未来方向（对标 Confident AI 的 eval-as-merge-gate），但需要先验证本地 CLI + Web UI 的核心价值。

5. **不做线上可观测性/trace 监控（仍不做）** — 引用 Positioning §ANTI-POSITIONING。我们聚焦上线前的决策，不是线上监控。

## §11 验收标准

### 功能
- [ ] `prompt-lab run --eval` 对每个 case 执行配置的 DeepEval 评估指标
- [ ] `prompt-lab compare <run-id>` 报告包含质量评估列
- [ ] `prompt-lab serve` 启动 Web 服务器，浏览器可访问
- [ ] Web UI 版本列表 + 版本详情 + diff 对比正常工作
- [ ] Web UI Run 报告页展示含质量分数的对比报告
- [ ] Web UI Prompt 编辑器可注册新版本

### 性能
- [ ] Web UI 页面加载 < 500ms
- [ ] API 响应 < 100ms（不含 LLM 调用）
- [ ] DeepEval 单指标评估在 30s 内完成或超时

### 兼容性
- [ ] V1 的 `result.json` 可被 V2 正常读取
- [ ] 无 `--eval` flag 时行为与 V1 完全一致
- [ ] `prompt-lab serve` 未运行时 CLI 所有命令正常工作

### 测试
- [ ] 评估引擎单元测试覆盖率 ≥ 80%
- [ ] Web API 端点测试覆盖率 ≥ 80%
- [ ] CUJ-4（CLI + 评估）端到端测试
- [ ] CUJ-5（Web 只读）端到端测试

### 回滚
- [ ] 评估功能为可选依赖，卸载不影响核心功能
- [ ] Web 服务器是可选功能，不启动不影响 CLI

## §12 可观测性需求

### §12.1 新增事件

Prompt Lab 是 CLI + Web 工具，"事件"以运行日志和 Web access log 形式存储。

**评估事件**（写入 `events.jsonl`）：

| 事件 | 触发时机 | 关键字段 | 用途 | 优先级 |
|------|---------|---------|------|--------|
| `eval_started` | 评估引擎开始处理一个 case 的指标 | case_id, metric_name, timestamp | 审计 | P0 |
| `eval_completed` | 单指标评估成功 | case_id, version, metric_name, score, reason, duration_ms | 对比数据 | P0 |
| `eval_skipped` | 指标跳过（缺 expected_output 等） | case_id, version, metric_name, reason | 诊断 | P1 |
| `eval_failed` | 评估失败（API 错误等） | case_id, version, metric_name, error_type, error_message | 诊断 | P0 |

**Web 服务事件**（写入 `.prompt-lab/web.log`）：

| 事件 | 触发时机 | 关键字段 | 用途 | 优先级 |
|------|---------|---------|------|--------|
| `api_request` | 每个 API 请求 | method, path, status_code, duration_ms, client_ip | 审计 | P1 |
| `web_run_triggered` | 通过 Web UI 触发 run | baseline_version, candidate_version, dataset, eval_enabled | 审计 | P1 |
| `web_version_registered` | 通过 Web UI 注册版本 | version_id, changed_var, author | 审计 | P1 |

### §12.2 复用现有事件

扩展 V1 的 `run_completed` 事件：
- 新增 `eval_enabled` 字段（bool）：本次 run 是否启用评估
- 新增 `eval_metrics` 字段（list[str]）：执行的指标名称列表
- 新增 `eval_success_count` / `eval_skip_count` / `eval_fail_count` 字段

### §12.3 事件 schema

所有事件仍存储为 JSONL 文件（`.prompt-lab/runs/<run-id>/events.jsonl`），无数据库 schema 改动。

Web log 为标准 HTTP access log 格式（combined log format），写入 `.prompt-lab/web.log`。

### §12.4 验收标准

- [ ] 每次 `--eval` run 生成完整的评估事件（`eval_completed` / `eval_skipped` / `eval_failed` 覆盖 100% 的 case × metric 组合）
- [ ] `run_completed` 事件包含评估汇总字段（当 `eval_enabled=true` 时）
- [ ] Web 服务器运行时 `web.log` 持续写入
- [ ] 通过 Web UI 触发的操作（run / register）有对应审计事件

### §12.5 隐私考量

- prompt 内容可能包含用户数据，存储在本地 `.prompt-lab/`
- Web 服务器仅绑定 `127.0.0.1`，不暴露到网络
- Web access log 记录请求路径但不记录请求体（prompt 内容不进 access log）
- API key 从环境变量读取，不写入任何文件，不通过 API 返回
- DeepEval 评估通过用户配置的 LLM API 进行，评估输入（prompt + output）发送到用户的 LLM provider，不经第三方

## §13 关联

- **Positioning Memo**: [prompt_lab_positioning_v1.0_2026-07-25.zh.md](../00-positioning/prompt_lab_positioning_v1.0_2026-07-25.zh.md)
- **前序 PRD**: [prompt_lab_prd_v1.0_2026-07-25.zh.md](./prompt_lab_prd_v1.0_2026-07-25.zh.md)
- **前序 Spec**: [prompt_lab_spec_v1.0_2026-07-25.zh.md](../02-spec/prompt_lab_spec_v1.0_2026-07-25.zh.md)
- **Kanban**: github.com/Ezio0/prompt-lab（公开 repo，使用 GitHub Issues 管理任务）
- **大框架**: Prompt Lab v2.0

---

签字：待 Ezio 审阅
