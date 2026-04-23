# code-urgent (紧急代码硬洞补齐) Phase 1 Onboarding

**状态**：APPROVED
**发布日期**：2026-04-23
**Signal 入口**：`PRODUCT-HARDENING-BATCH-1-DISPATCHED`
**前置**：
- 代码审计（Q-023 中一览）已完成
- Archive workspace 漂移处置 = 本批次 Task 0（不是外部前置）
- Platform Phase 1 Batch 1 已 MERGED（`f319ccb`）

---

## 你是谁

你是 **code-urgent** worker CLI，负责 **1 周内** 把 6 Agent 代码层最高 ROI 的紧急硬洞补齐。你是紧急补救手术台，不做架构重构（那是 code-arch 的事）。

- Worktree：`D:/claude code/demo-code-urgent`
- 分支：`feat/code-urgent`（从 `chore/l0-infra` 分出）
- Upstream remote：`D:/claude code/credit_report_agent_work`

---

## 本批次任务

### 🚑 Task 0 — archive workspace 归位（前置）

**目标**：把 ad-hoc 分支 `feat/agent6-dialog-shell` 上的 `web/src/app/archive/*/_components/*Workspace.tsx` + 相关 shared 组件归到本分支。让 `chore/l0-infra` 基 + 本 commit 后 `cd web && npm run dev` 能跑通 6 个 `/archive/[agent]` 路由。

**操作**：
```
git checkout feat/agent6-dialog-shell -- web/src/app/archive/
git status   # 检查 diff 是否只在 archive/ 下，没带别的 ad-hoc 代码
cd web && npx tsc --noEmit
```
按 tsc 报错补齐缺失的 api client（`web/src/lib/api.ts` 如缺 `streamChannelSearch` 等）/ shared 组件（`web/src/components/shared/` 下如有 CustomerSelector / ScanCTA）/ css 文件。若有别的目录 diff（如 `web/src/lib/*` / `web/src/components/*`），**单独过滤后带进来**，不要整分支合并。

**指标/验证**：
- `npm run dev` 后 `/archive/channel` / `/credit` / `/alert` / `/compliance` / `/report` / `/riskctrl` 全部能打开，无 import error
- 控制台 0 error

**工作量**：S（0.5 天）
**完成信号**：`Signal: ARCHIVE-WORKSPACE-REHOMED`

---

### 🔴 Task A — Agent3 接入 financial_analyzer（§3.1 反模式修复）

**目标**：`agent_credit/scoring_model_corporate.py:95 _score_financial()` 自己算财务比率，违反 CLAUDE.md §3.1（比率算逻辑分散）。改为消费 `financial_analyzer.format_for_prompt()` 三件套。

**模块路径**：
- 修改：`agent_credit/scoring_model_corporate.py`（`_score_financial` / `_score_corporate` 从 financial_analyzer 取确定性比率）
- 修改：`agent_credit/advisor_formatter.py`（prompt 的 evidence 改用 `financial_analyzer.format_for_prompt()`）
- 只读：`financial_analyzer.py`（不要改接口）

**指标/验证**：
- 同一组财务数据跑 agent_credit vs agent_report 比率一致（误差 < 0.01%）
- Grep 确认 LLM prompt 不再出现"请计算流动比率/资产负债率"这类让 LLM 算的指令

**工作量**：M（1 天）
**完成信号**：`Signal: CREDIT-FINANCIAL-ANALYZER-INTEGRATED`

---

### 🔴 Task B — 5 Agent 补占位符 QC blocker（§8 第 1 条闸门）

**目标**：除 Agent6 外，5 个 Agent 各补一个占位符扫描函数，检查输出含 `[待补充]` / `{{name}}` / `<占位>` / 三点省略 等残留。命中即阻断并标"未能自动填写"。

**模块路径**：
- 新建：`shared/qc/placeholder_guard.py`（共享 regex 库 + `scan(text) -> list[str]` 接口）
- 修改：`agent_channel/` / `agent_credit/` / `agent_alert/` / `agent_compliance/` / `agent_riskctrl/` 各自 api.py 或 output validator 最终输出前 call `placeholder_guard.scan()`
- 参考：`quality_scorer.py:936-942` 现有占位符检查逻辑（只读，不改）

**指标/验证**：
- 5 Agent 各喂一个故意带 `[待补充]` 的 mock 输出，全部被阻断
- 正常输出通过，无误报
- 新建 `tests/test_placeholder_guard.py` 覆盖 5 个 case

**工作量**：S（0.5 天）
**完成信号**：`Signal: QC-PLACEHOLDER-GUARD-5AGENTS-DONE`

---

### 🔴 Task C — Agent2 / Agent4 新建 api.py + 挂载

**目标**：`agent_riskctrl/api.py` 和 `agent_alert/api.py` 根本不存在。新建，模板抄 `agent_report/api.py` 的 FastAPI + SSE 骨架。挂进 `api_server.py:223-226` portal 解除 Phase 2 TODO。

**模块路径**：
- 新建：`agent_riskctrl/api.py`（POST `/api/riskctrl/backtest` + `/api/riskctrl/dsl_gen`，SSE）
- 新建：`agent_alert/api.py`（POST `/api/alert/scan`，SSE）
- 修改：`api_server.py:223-226` mount 这两个 sub-app
- 参考：`agent_report/api.py` / `agent_credit/api.py`（现有 SSE 实现范本）

**指标/验证**：
- `curl -N -X POST http://127.0.0.1:8000/api/riskctrl/dsl_gen` 收到 SSE 流
- 同 alert
- `api_server.py` 启动 log 显示 6/6 Agent sub-app 挂载成功

**工作量**：M（1.5 天）
**完成信号**：`Signal: AGENT2-AGENT4-API-WIRED`

---

## 完成后

所有 Task 做完：`Signal: READY-FOR-CODE-URGENT-REVIEW`

## 红线

- ❌ 不动 `financial_analyzer.py` 本身（只读消费）
- ❌ 不动 Agent6 代码（他已 🟢，不要动坏）
- ❌ 不动 `web/src/lib/store/*`（红区）
- ❌ 不动 `web/src/components/shell/*`（归主 CLI）
- ❌ 不碰其他 worker 地盘（code-arch / data-foundation / evaluation 各自领域）
- ❌ **不做架构重构**（工具域拆分、Evidence 三阶段 = code-arch 任务，不要抢）
- ✅ `agent_channel/` / `agent_credit/` / `agent_alert/` / `agent_compliance/` / `agent_riskctrl/` 代码修改你负责
- ✅ `shared/qc/` 新增你负责
- ✅ `api_server.py` mount 行你可以增量改
- ✅ `web/src/app/archive/` 归位（Task 0）你负责

## ACK 协议

1. Resume 后看到本文件 → commit 一条空 doc commit，trailer `Signal: PRODUCT-HARDENING-BATCH-1-ACK`
2. 按 Task 0 → A → B → C 顺序推进，每 Task 独立 commit 带对应 signal
3. 全 Task 完成 → `READY-FOR-CODE-URGENT-REVIEW`

**维护者**：主 CLI
**下次更新触发**：主 CLI APPROVE 或 REJECT
