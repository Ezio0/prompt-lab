# Prompt Lab Implementation Plan v2.0

**项目**: Prompt Lab
**日期**: 2026-07-26
**版本**: v2.0
**Spec**: [prompt_lab_spec_v2.0_2026-07-26.zh.md](../02-spec/prompt_lab_spec_v2.0_2026-07-26.zh.md)
**PRD**: [prompt_lab_prd_v2.0_2026-07-26.zh.md](../01-prd/prompt_lab_prd_v2.0_2026-07-26.zh.md)
**前序 Plan**: [prompt_lab_plan_v1.0_2026-07-25.zh.md](./prompt_lab_plan_v1.0_2026-07-25.zh.md)

---

## §1 概述

引用 [Spec §1 Overview](../02-spec/prompt_lab_spec_v2.0_2026-07-26.zh.md#1-overview)。

本计划将 V2 的质量评估引擎和 Web UI 拆分为可独立执行的 Task，按依赖顺序排列。

## §2 Phases

| Phase | 目标 | Tasks |
|-------|------|-------|
| **P5: 质量评估引擎** | EvalConfig + Evaluator + RunEngine 扩展 + 报告扩展 | T-101 ~ T-109 |
| **P6: Web API** | FastAPI 服务层 + REST 端点 + serve 命令 | T-201 ~ T-206 |
| **P7: React SPA** | 前端项目 + 页面 + 组件 + 构建集成 | T-301 ~ T-309 |
| **P8: 集成测试** | CUJ-4 (CLI+eval) + CUJ-5 (Web 只读) E2E | T-401 ~ T-402 |

## Pre-flight Environment Check

实现前必须确认：

- [ ] **Python venv 可用** — `cd /Users/ezio/.local/prompt-lab && source .venv/bin/activate && python --version` 返回 3.11+
- [ ] **DeepSeek API key 设置** — `echo $DEEPSEEK_API_KEY` 非空
- [ ] **Node.js 可用**（P7 需要）— `node --version` 返回 18+
- [ ] **npm 可用** — `npm --version` 返回 9+
- [ ] **端口 8765 空闲** — `lsof -i :8765` 无输出
- [ ] **V1 测试全通过** — `cd /Users/ezio/.local/prompt-lab && source .venv/bin/activate && python -m pytest tests/ -q` 全绿

## §3 Task Breakdown

### Phase P5: 质量评估引擎

---

### T-101: EvalConfig 配置模块 (P5, S)

**依赖**: V1 完成

**描述**: 扩展 `Config` 支持 `eval` 配置块。

**验收标准**:
- [ ] `EvalMetricConfig` dataclass: `name`, `params: dict`
- [ ] `EvalConfig` dataclass: `enabled`, `metrics: list[EvalMetricConfig]`, `model`, `api_key_env`
- [ ] `Config.load()` 解析 `eval` block，缺失时返回 `EvalConfig(enabled=False, ...)`
- [ ] `Config.load()` 从 `eval.api_key_env` 读取环境变量
- [ ] 向后兼容：V1 的 yaml 无 `eval` block 时正常加载
- [ ] 单元测试覆盖：有 eval block / 无 eval block / 缺 api_key / metrics 为空

**文件**:
- 修改: `prompt_lab/core/config.py`
- 修改: `tests/unit/test_config.py`

---

### T-102: EvalResult + CaseResult 扩展 (P5, S)

**依赖**: T-101

**描述**: 新增 `EvalResult` dataclass，扩展 `CaseResult` 添加 `evaluations` 字段。

**验收标准**:
- [ ] `EvalResult` dataclass: `metric_name`, `score: float`, `reason: str`, `status: str`, `error: str | None`
- [ ] `CaseResult` 新增 `evaluations: list[EvalResult]` 字段，默认空列表
- [ ] `RunResult.summary` 可选 `eval_summary` dict 字段
- [ ] V1 的 `result.json` 反序列化时 `evaluations` 默认空列表（向后兼容）
- [ ] 单元测试覆盖：带 evaluations 的序列化/反序列化 / V1 数据兼容

**文件**:
- 修改: `prompt_lab/core/models.py`
- 修改: `prompt_lab/core/run_engine.py`（`_write_result` 和 summary 扩展）
- 修改: `prompt_lab/cli.py`（`_run_result_from_json` 兼容扩展）

---

### T-103: DeepEval 自定义模型适配器 (P5, M)

**依赖**: T-101

**描述**: 创建 DeepEval 兼容的自定义 LLM 模型类，支持 OpenAI 兼容 API（DeepSeek 等）。

**关键上下文**: DeepEval 默认使用 OpenAI endpoint。对非 OpenAI 模型（如 DeepSeek），需创建 `DeepEvalBaseLLM` 子类。

**验收标准**:
- [ ] `DeepSeekModel` 类继承 `DeepEvalBaseLLM`
- [ ] 从 EvalConfig 读取 `model`, `base_url`, `api_key`
- [ ] `load_model()` 返回 OpenAI client（兼容 base_url）
- [ ] `generate()` 实现文本生成
- [ ] `get_model_name()` 返回 model 名称
- [ ] 评估 model 与生成 model 可不同
- [ ] 单元测试 mock OpenAI client，验证调用路径

**文件**:
- 创建: `prompt_lab/core/eval_model.py`
- 创建: `tests/unit/test_eval_model.py`

**实现参考**:

```python
from deepeval.models import DeepEvalBaseLLM
from openai import OpenAI

class CustomModel(DeepEvalBaseLLM):
    def __init__(self, model: str, base_url: str, api_key: str):
        self.model_name = model
        self.base_url = base_url
        self.api_key = api_key

    def load_model(self):
        return OpenAI(base_url=self.base_url, api_key=self.api_key)

    def generate(self, prompt: str) -> str:
        client = self.load_model()
        resp = client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return resp.choices[0].message.content

    def get_model_name(self):
        return self.model_name
```

---

### T-104: Evaluator 模块 (P5, M)

**依赖**: T-101, T-102, T-103

**描述**: 核心评估引擎，对 baseline 和 candidate 输出执行 DeepEval 指标。

**验收标准**:
- [ ] `Evaluator.__init__(eval_config, eval_model)` 接收配置和模型
- [ ] `Evaluator.evaluate(case, baseline_output, candidate_output) -> list[EvalResult]`
- [ ] 对每个输出（baseline + candidate）× 每个 metric 执行评估
- [ ] 构建 `LLMTestCase`（input=case.input 拼接, actual_output, expected_output, context）
- [ ] 指标映射：
  - `faithfulness` → `FaithfulnessMetric(model=eval_model)`
  - `answer_relevancy` → `AnswerRelevancyMetric(model=eval_model)`
  - `geval` → `GEval(name, criteria/evaluation_steps, evaluation_params, model=eval_model)`
- [ ] case 无 `expected_output` 且 metric 需要时 → `EvalResult(status="skipped")`
- [ ] DeepEval 内部异常 → `EvalResult(status="error", error=str(e))`，不中断
- [ ] 评估超时（30s）→ `EvalResult(status="error")`
- [ ] 单元测试覆盖：正常评估 / skipped / error / 多指标 / GEval 自定义 criteria

**文件**:
- 创建: `prompt_lab/core/evaluator.py`
- 创建: `tests/unit/test_evaluator.py`

**实现参考**:

```python
from deepeval.metrics import GEval, FaithfulnessMetric, AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase, SingleTurnParams

class Evaluator:
    def __init__(self, eval_config: EvalConfig, eval_model: CustomModel):
        self.config = eval_config
        self.model = eval_model

    def evaluate(self, case: Case, baseline_output: str, candidate_output: str) -> list[EvalResult]:
        results = []
        for metric_config in self.config.metrics:
            metric = self._build_metric(metric_config)
            for version_label, output in [("baseline", baseline_output), ("candidate", candidate_output)]:
                result = self._run_metric(metric, metric_config.name, case, output)
                results.append(result)
        return results

    def _build_metric(self, config: EvalMetricConfig):
        name = config.name
        if name == "faithfulness":
            return FaithfulnessMetric(model=self.model)
        elif name == "answer_relevancy":
            return AnswerRelevancyMetric(model=self.model)
        elif name == "geval":
            return GEval(
                name=config.params.get("name", "Custom"),
                criteria=config.params.get("criteria", ""),
                evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
                model=self.model,
            )
        else:
            raise ValueError(f"Unknown metric: {name}")
```

---

### T-105: RunEngine 扩展 (P5, M)

**依赖**: T-104

**描述**: 在 A/B run 中集成评估，每个 case 的输出跑完后触发评估。

**验收标准**:
- [ ] `RunEngine.__init__` 新增可选 `evaluator: Evaluator | None` 参数
- [ ] `RunEngine.run()` 新增 `run_eval: bool = False` 参数
- [ ] 当 `run_eval=True` 且 `evaluator` 非 None 时，每个 case 输出完成后调用 `evaluator.evaluate()`
- [ ] 评估结果写入 `CaseResult.evaluations`
- [ ] summary 新增 `eval_summary` 块（每个 metric 的 baseline/candidate 平均分）
- [ ] 评估不中断 run（eval error 标记后继续）
- [ ] events.jsonl 新增 `eval_completed` / `eval_skipped` / `eval_failed` 事件
- [ ] `run_completed` 事件扩展 eval 字段
- [ ] 无 `run_eval` 时行为与 V1 完全一致
- [ ] 单元测试覆盖：带 eval / 不带 eval / eval error / eval skipped

**文件**:
- 修改: `prompt_lab/core/run_engine.py`
- 修改: `tests/unit/test_run_engine.py`

---

### T-106: ReportBuilder 扩展 (P5, S)

**依赖**: T-105

**描述**: 对比报告新增质量评估列。

**验收标准**:
- [ ] `build_table()` 检测 `evaluations` 非空时自动新增评估列
- [ ] 每列显示 baseline vs candidate 的 metric 分数
- [ ] summary 新增 eval_summary 行
- [ ] 新增 `build_eval_summary(run_result)` 方法：只输出评估指标
- [ ] `--eval-only` 选项只显示评估数据
- [ ] 无 evaluations 时报告与 V1 完全一致
- [ ] 单元测试覆盖：带 eval 的 table / 带 eval 的 json / eval-only / 无 eval 兼容

**文件**:
- 修改: `prompt_lab/core/report.py`
- 修改: `tests/unit/test_report.py`

---

### T-107: CLI run --eval + compare --eval-only (P5, S)

**依赖**: T-105, T-106

**描述**: CLI 命令集成 `--eval` 和 `--eval-only` flag。

**验收标准**:
- [ ] `run` 命令新增 `--eval` flag
- [ ] `run --eval` 时：
  - [ ] 检查 DeepEval 是否安装，未安装报 `E_EVAL_NOT_INSTALLED`
  - [ ] 从 Config 加载 EvalConfig
  - [ ] 创建 eval model + Evaluator
  - [ ] 传入 RunEngine，`run_eval=True`
- [ ] `compare` 命令新增 `--eval-only` flag
- [ ] 无 `--eval` 时行为不变
- [ ] CLI 输出汇总含评估信息（当有 eval 数据时）
- [ ] 单元测试覆盖 run --eval / compare --eval-only / 无 deepeval 时报错

**文件**:
- 修改: `prompt_lab/cli.py`
- 修改: `tests/unit/test_cli.py`

---

### T-108: pyproject.toml 可选依赖 (P5, XS)

**依赖**: T-101

**描述**: 添加 `[eval]` optional dependency group。

**验收标准**:
- [ ] `pyproject.toml` 新增 `[project.optional-dependencies] eval = ["deepeval>=2.0", "openai>=1.0"]`
- [ ] `pip install prompt-lab[eval]` 可安装
- [ ] 不安装 eval 依赖时 `import deepeval` 抛 ImportError
- [ ] version bump 到 2.0.0

**文件**:
- 修改: `pyproject.toml`

---

### T-109: Phase P5 集成验证 (P5, S)

**依赖**: T-101 ~ T-108

**验收标准**:
- [ ] 全量单元测试通过
- [ ] `prompt-lab run --eval` 命令可执行（mock provider + mock eval）
- [ ] `prompt-lab compare <run-id>` 报告含评估列（当 run 含 eval 数据时）
- [ ] V1 测试全部通过（无回归）

---

### Phase P6: Web API (FastAPI)

---

### T-201: FastAPI app 骨架 + serve 命令 (P6, S)

**依赖**: V1 完成

**描述**: 创建 FastAPI 应用骨架和 `prompt-lab serve` CLI 命令。

**验收标准**:
- [ ] `prompt_lab/web/__init__.py` 创建
- [ ] `prompt_lab/web/server.py` 定义 `create_app(project_root: Path) -> FastAPI`
- [ ] app 含 CORS 中间件（允许 localhost）
- [ ] app 含 access log 中间件（写 `.prompt-lab/web.log`）
- [ ] CLI 新增 `serve` 命令：`prompt-lab serve [--port 8765] [--host 127.0.0.1]`
- [ ] serve 命令调用 `uvicorn.run(create_app(Path.cwd()), ...)`
- [ ] FastAPI 和 uvicorn 加入 dependencies
- [ ] 单元测试：create_app 返回 FastAPI 实例，含基本路由

**文件**:
- 创建: `prompt_lab/web/__init__.py`
- 创建: `prompt_lab/web/server.py`
- 创建: `prompt_lab/web/middleware.py`（access log 中间件）
- 修改: `prompt_lab/cli.py`
- 修改: `pyproject.toml`（添加 fastapi, uvicorn）
- 创建: `tests/unit/test_web_server.py`

---

### T-202: 版本管理 REST 端点 (P6, M)

**依赖**: T-201

**描述**: 版本相关的 REST API 端点。

**验收标准**:
- [ ] `GET /api/versions` — 返回版本列表（不含 prompt_text）
- [ ] `GET /api/versions/{id}` — 返回完整版本（含 prompt_text）
- [ ] `GET /api/versions/{id_a}/{id_b}/diff` — 返回 diff
- [ ] `POST /api/versions` — 注册新版本
- [ ] 错误处理：404（不存在）、409（已存在）
- [ ] API key 不在响应中出现
- [ ] 单元测试覆盖所有端点 + 错误路径

**文件**:
- 创建: `prompt_lab/web/routes/versions.py`
- 创建: `tests/unit/test_web_versions.py`

---

### T-203: Case + Run REST 端点 (P6, M)

**依赖**: T-201

**描述**: Case 和 Run 相关的 REST API 端点。

**验收标准**:
- [ ] `GET /api/cases` — Case 列表（支持 ?collection= 和 ?type= 过滤）
- [ ] `GET /api/runs` — Run 列表
- [ ] `GET /api/runs/{id}` — Run 详情（完整 result.json 数据）
- [ ] `POST /api/runs` — 触发 A/B run（同步返回结果）
- [ ] `GET /api/config` — 返回配置（api_key_env 但不返回值）
- [ ] 错误处理：400（参数错误）、404（不存在）、502（provider 错误）
- [ ] 单元测试覆盖所有端点 + 错误路径

**文件**:
- 创建: `prompt_lab/web/routes/cases.py`
- 创建: `prompt_lab/web/routes/runs.py`
- 创建: `prompt_lab/web/routes/config.py`
- 创建: `tests/unit/test_web_cases.py`
- 创建: `tests/unit/test_web_runs.py`

---

### T-204: Static files 托管 (P6, S)

**依赖**: T-201, T-301 (前端 build 产物)

**描述**: FastAPI 托管 React SPA 静态文件。

**验收标准**:
- [ ] `create_app()` 挂载 `StaticFiles(directory="web/frontend/dist", html=True)` 到 `/`
- [ ] build 产物不存在时返回 JSON 提示
- [ ] SPA history fallback（所有非 /api/ 路径返回 index.html）
- [ ] 单元测试覆盖：static 文件可访问 / fallback

**文件**:
- 修改: `prompt_lab/web/server.py`

---

### Phase P7: React SPA

---

### T-301: Vite + React + TypeScript 项目初始化 (P7, S)

**依赖**: 无

**描述**: 在 `web/frontend/` 下创建 React SPA 项目。

**验收标准**:
- [ ] `web/frontend/` 目录创建
- [ ] `npm create vite@latest . -- --template react-ts` 执行
- [ ] 依赖安装：`react`, `react-dom`, `react-router-dom`, `axios`
- [ ] UI 库安装：`tailwindcss`, `postcss`, `autoprefixer`
- [ ] 组件库安装：`recharts`（图表）, `react-diff-viewer-continued`（diff）
- [ ] `tailwind.config.js` 配置完成
- [ ] `npm run dev` 本地可启动
- [ ] Vite proxy 配置：`/api` → `http://localhost:8765`

**文件**:
- 创建: `web/frontend/` 全部脚手架文件
- 创建: `web/frontend/vite.config.ts`（含 proxy 配置）

---

### T-302: API client + TypeScript types (P7, S)

**依赖**: T-301

**描述**: 前端 API 调用层和类型定义。

**验收标准**:
- [ ] `src/types/index.ts` 定义所有类型（Version, Case, RunResult, EvalResult 等）
- [ ] `src/api/client.ts` 封装所有 API 调用
- [ ] API 函数：`getVersions()`, `getVersion(id)`, `getDiff(a, b)`, `createVersion(...)`, `getCases(...)`, `getRuns()`, `getRun(id)`, `triggerRun(...)`, `getConfig()`

**文件**:
- 创建: `web/frontend/src/types/index.ts`
- 创建: `web/frontend/src/api/client.ts`

---

### T-303: 版本列表 + 详情 + Diff 页面 (P7, M)

**依赖**: T-302

**描述**: 版本管理相关的页面和组件。

**验收标准**:
- [ ] `VersionList` 组件：表格展示版本列表
- [ ] `VersionDetail` 页面：显示 prompt 全文（monospace）
- [ ] `DiffViewer` 组件：side-by-side diff
- [ ] React Router 路由配置
- [ ] 空状态提示
- [ ] 页面可手动验证（`npm run dev`）

**文件**:
- 创建: `web/frontend/src/pages/VersionList.tsx`
- 创建: `web/frontend/src/pages/VersionDetail.tsx`
- 创建: `web/frontend/src/components/DiffViewer.tsx`
- 创建: `web/frontend/src/App.tsx`（路由）

---

### T-304: Run 列表 + 报告页面 (P7, M)

**依赖**: T-302

**描述**: Run 报告相关的页面和组件。

**验收标准**:
- [ ] `RunList` 组件：表格展示 run 列表
- [ ] `RunReport` 页面：汇总卡片 + 逐 case 表格 + 输出对比
- [ ] `EvalScoreCard` 组件：评估分数卡片
- [ ] `MetricChart` 组件：bar chart 对比（recharts）
- [ ] 评估分数高亮（pass=绿, skipped=灰, error=红）
- [ ] JSON 下载按钮
- [ ] 页面可手动验证

**文件**:
- 创建: `web/frontend/src/pages/RunList.tsx`
- 创建: `web/frontend/src/pages/RunReport.tsx`
- 创建: `web/frontend/src/components/EvalScoreCard.tsx`
- 创建: `web/frontend/src/components/MetricChart.tsx`

---

### T-305: Prompt 编辑器页面 (P7, M)

**依赖**: T-302, T-303

**描述**: Web UI 上的 prompt 编辑和注册。

**验收标准**:
- [ ] `PromptEditor` 组件：monospace textarea
- [ ] 变量占位符提示
- [ ] 注册表单：版本名、变更说明、变更类型
- [ ] 注册前 diff 预览（与上一个版本对比）
- [ ] 注册成功后跳转版本列表
- [ ] 不可覆盖已存在版本（API 409 处理）
- [ ] 确认对话框（"This cannot be undone"）
- [ ] 页面可手动验证

**文件**:
- 创建: `web/frontend/src/pages/PromptEditor.tsx`
- 创建: `web/frontend/src/components/VersionForm.tsx`

---

### T-306: 构建 + 静态文件集成 (P7, S)

**依赖**: T-303, T-304, T-305, T-204

**描述**: 前端 build 并与 FastAPI 集成。

**验收标准**:
- [ ] `npm run build` 生成 `web/frontend/dist/`
- [ ] `dist/` 提交到 git
- [ ] FastAPI `create_app()` 托管 `dist/` 为静态文件
- [ ] SPA fallback 正常工作
- [ ] `prompt-lab serve` 后浏览器可访问完整 Web UI
- [ ] API + 前端在同一端口

**文件**:
- 修改: `web/frontend/`（build 配置）
- 修改: `.gitignore`（不忽略 `dist/`）

---

### Phase P8: 集成测试

---

### T-401: CUJ-4 E2E — CLI 质量评估全链路 (P8, M)

**依赖**: T-107

**验收标准**:
- [ ] E2E 测试覆盖：init → add version × 2 → add case (with expected_output) → run --eval → compare
- [ ] 验证 result.json 包含 evaluations 字段
- [ ] 验证 eval_summary 包含平均分
- [ ] Mock provider + mock evaluator（不调真实 LLM）

**文件**:
- 修改: `tests/integration/test_e2e.py`

---

### T-402: CUJ-5 E2E — Web 只读浏览 (P8, M)

**依赖**: T-202, T-203

**验收标准**:
- [ ] E2E 测试覆盖：create_app → GET /api/versions → GET /api/versions/{id} → GET /api/runs → GET /api/runs/{id}
- [ ] 验证 API 响应格式
- [ ] 验证错误路径（404）
- [ ] 使用 FastAPI TestClient（不启动真实 server）

**文件**:
- 创建: `tests/integration/test_web_e2e.py`

---

## §4 依赖图

```
Phase P5 (Eval Engine):
T-101 (EvalConfig)
  ├── T-102 (EvalResult + CaseResult) ── T-105 (RunEngine ext)
  │                                         └── T-106 (Report ext) ── T-107 (CLI)
  ├── T-103 (DeepEval model adapter)
  │     └── T-104 (Evaluator) ────────── T-105
  └── T-108 (pyproject.toml)
        └── T-109 (P5 integration check)

Phase P6 (Web API):
T-201 (FastAPI scaffold + serve)
  ├── T-202 (Version REST)
  ├── T-203 (Case + Run REST)
  └── T-204 (Static files) ←── T-306 (frontend build)

Phase P7 (React SPA):
T-301 (Vite project)
  └── T-302 (API client + types)
        ├── T-303 (Version pages)
        ├── T-304 (Run pages)
        └── T-305 (Editor page)
              └── T-306 (Build + integrate)

Phase P8 (Integration):
T-107 ←── T-401 (CUJ-4 CLI eval E2E)
T-203 ←── T-402 (CUJ-5 Web E2E)
```

## §5 执行策略

- **Phase P5**（质量评估）和 **Phase P6**（Web API）可以并行
- **Phase P7**（React SPA）依赖 P6 完成
- **Phase P8**（集成测试）在 P5/P6 完成后执行
- 每个 Task 完成后跑对应单元测试
- 每个 Phase 完成后跑全量测试
- P5 完成后可独立发布（`run --eval` 功能可用）
- P6+P7 完成后发布完整 V2（`serve` 可用）

## §6 定义"完成"

- [ ] 全部 Task 的验收标准勾完
- [ ] 全量测试通过（unit + integration）
- [ ] `prompt-lab run --eval` 可执行（mock 模式）
- [ ] `prompt-lab serve` 启动后浏览器可访问 Web UI
- [ ] Web UI 版本列表/详情/run 报告/编辑器功能正常
- [ ] V1 测试全部通过（无回归）
- [ ] commit + push 到 main

## §7 History

| 日期 | 事件 |
|------|------|
| 2026-07-26 | 初始创建 |

---

签字：待 Ezio 审阅
