# Agent2 风控 · Phase 1 Productize Onboarding

**对应 worktree**：`D:\claude code\demo-agent2`（`feat/agent2-productize`）
**发布日期**：2026-04-19
**前置**：已读 `AGENT_IDENTITY.md` + `CLAUDE.md` + 本文 + `docs/review/agent2-phase-0-review.md` + `docs/onboarding/agent1-phase-1.md`（契约形态对标）
**目标**：把 Agent2 从「Phase 0 APPROVED / scorecard 62%」推到「Phase 1 productize APPROVED」（scorecard ≥ 72%，runner `--agent riskctrl` **verdict = PASS**，不是 PARTIAL）。

---

## 背景（3 行速读）

Phase 0 @ `7a2579e` APPROVED（2026-04-19），review 明确 Top 3 Gap 是 Phase 1 强制吸收项：**fixture → runtime 实跑**（fixture 是合成 good-run，5 全绿只证明 adapter 能识别合格形态）、**Phase C 两 stub 语义落地**（对齐 A-013 `baseline.pending_metrics` 白名单）、**`false_positive_rate` 只到汇总层**（R002 高负债率等单条规则误杀率被掩盖，需 per-rule confusion matrix + 方差警戒）。今天同批次 Agent1 Phase 1 四 Task 全绿 @ `c408b3a`、runner verdict=PASS，Agent2 Phase 1 的契约形态须与之对齐（A-013 白名单 / SHA 不可变 / stop-and-wait Signal）。

---

## 1. 范围 & 不做什么

### productize 定义（对齐 `memory/project_bank_delivery_dod.md`）

| 层 | 本 Phase 交付项 | 当前状态 |
|---|---|---|
| L0 最低起跑线 | runner adapter 已挂 + fixture baseline 5/5 绿 | ✅ Phase 0 已达成 |
| L1 功能完整 | DSL 生成 + 回测（agent_riskctrl 三流程已跑通） | ✅ 不动 |
| L2 可审计可追溯 | runtime 产物链路 + per-rule FPR 暴露 + pending 语义诚实 | ❌ 本 Phase 做 |
| L3 可量化可验收 | runner `--agent riskctrl` = PASS（非 PARTIAL） | ❌ 本 Phase 做 |
| L1 bank delivery 门面 | 规则 ReadOnly 展示 + 导出 JSON（编辑器推 Phase 2） | ❌ 本 Phase 做（最小存根） |

### 不做什么（明确排除，防 scope creep）

- ❌ **不做完整规则编辑器**：DSL 所见即所得编辑 / 语法校验 / 在线回测——推 Phase 2
- ❌ **不做 ks_improvement 真值**：依赖 baseline_ruleset 对照组 + 人工基线 KS，Phase 1 按 pending 语义处理
- ❌ **不做 LLM-judge 实装**：`rule_interpretability` 同样 pending
- ❌ **不做 autopilot**：策略建议仍需人工审核，不下自动生产切换决策
- ❌ **不做跨 Agent 编排**：Agent2 边界在「DSL + 回测 + 规则展示」，不触发 Agent3 决策、不调用 Agent5 合规
- ❌ **不动 runner kernel**：A-013 已由主 CLI 落地 `baseline.pending_metrics` 白名单，worker **仅消费**，不改 `base_evaluator.py` / `registry.py` / `cli.py` / `__main__.py`
- ❌ **不动 `shared/` / `docs/contracts/` / `api_server.py` / `agent_*/api/` / `decisions-log.md`**（见 §4 红区）

---

## 2. 前置条件

- 主 CLI HEAD：`c408b3a` 之后（Agent1 Phase 1 四 Task 全绿合并进 `chore/l0-infra`）；`git fetch upstream && git log upstream/chore/l0-infra --oneline -8` 确认
- worker 起点：`feat/agent2-productize` @ `ff1b1bd`（Phase 0 window-close commit）
- `git fetch upstream && git rebase upstream/chore/l0-infra` 拿本 onboarding + A-013 kernel patch + A-012.D SHA 不可变条款
- 红线闸门基线（Phase 0 已验证，**不允许倒退**）：halluc 0.0000 / evidence 1.0000 / task 1.0000 / tool 1.0000 / fpr 0.0673（严于 yaml 0.15）
- Phase 0 fixture 产物保留在 `agent_riskctrl/tests/fixtures/baseline_v1/` 作「回归锚」，不删

---

## 3. Task 清单（4 Task，预计 2-3 工时）

### Task A · Fixture → Runtime（对应 Phase 0 Gap #1）

**goal**：替换 fixture-based baseline 为真正跑 `RiskControlAgent.process_message` 端到端产物 —— 证明 Agent2 LLM 链路本身质量达标，而非只证明 adapter 能识别合格形态。fixture 降级为「回归锚」。

**modules**：
- `evaluation/manual/2_YYYYMMDD.yaml`（新建；runtime 固定输入样本 + 期望产物 schema；worker 起草 schema）
- `scripts/run_agent2_baseline.py`（新建；跑 `RiskControlAgent` 三流程 rule_config / backtest / error_analysis，落 `evaluation/runtime/2_<ts>/rules.json + sample_schema.json + backtest.json`）
- `evaluation/runner/adapters/agent2_riskctrl.py`（改；`_resolve_fixture_dir` 扩一层：`run.artifacts[0]` 缺省时优先读 `evaluation/runtime/2_latest/`，找不到再降级到 `fixtures/baseline_v1/`；fixture 路径保留作「回归锚」标识）
- `agent_riskctrl/tests/fixtures/baseline_v1/README.md`（改；补一段「回归锚」说明 —— 这个 fixture 是合成 good-run，值全绿仅证明 adapter 形态识别能力，生产基线走 runtime）

**deliverables**：
- Runtime 脚本固定 3 种输入：
  1. 文本策略需求（rule_config 流程，不上传 CSV，只验证 DSL 生成）
  2. 文本策略需求 + 历史样本 CSV（backtest 流程，产 rules.json + backtest.json）
  3. 差错案件描述（error_analysis 流程，不纳入 Phase 1 baseline，只冒烟不回归）
- Runtime 产物按 Phase 0 fixture 三文件 schema 落盘（`rules.json` / `sample_schema.json` / `backtest.json`）——adapter 零改动即可消费
- sample CSV 来自 `agent_riskctrl/tests/fixtures/` 已有样本或新建 ≤ 500 行小样本（真实字段，不合成）
- adapter 解析顺序：`run.artifacts[0]` → `evaluation/runtime/2_latest/` → `fixtures/baseline_v1/`（三级 fallback，最后一级明确标「回归锚，非当期基线」）
- `evaluation/agent2_riskctrl.yaml` baseline 区块由 runtime 产物回填（`fixture_dir` 改为 runtime 路径、`verdict` / `results` 重跑更新），fixture 值保留在注释里作历史对比

**DoD**：
- [ ] `evaluation/manual/2_20260419.yaml` 存在，含 runtime 固定输入 schema 定义
- [ ] `py scripts/run_agent2_baseline.py` 跑通，产出 `evaluation/runtime/2_<ts>/{rules,sample_schema,backtest}.json`（3 文件必须来自 `RiskControlAgent.process_message` 真实跑，不是手工构造）
- [ ] `py -m evaluation.runner --agent riskctrl` 默认走 runtime 路径（verdict 来自 runtime 产物），fixture 降级为 fallback
- [ ] `evaluation/agent2_riskctrl.yaml` baseline 区块 `fixture_dir` 指向 runtime 路径，`commit` 更新到最新 SHA，`verdict` / `results` 为 runtime 跑出的真实数字
- [ ] `agent_riskctrl/tests/fixtures/baseline_v1/README.md` 明确标「回归锚（regression anchor），非当期生产基线」
- [ ] 红线闸门 runtime 值不低于 fixture 值的 0.9x（即允许 LLM 链路有小幅退化，但不许塌陷；若塌陷则写 `docs/progress/agent2-phase-1-runtime-gap.md` 不强改 adapter 套值）

---

### Task B · pending_metrics 语义落地（对齐 A-013）

**goal**：Phase C 两个 stub（`ks_improvement` / `rule_interpretability`）不再以 `passed=None` 拖 verdict 至 PARTIAL，改为「诚实 pending」—— 走 A-013 kernel 白名单，runner 应 verdict = **PASS**。

**modules**：
- `evaluation/agent2_riskctrl.yaml`（`baseline` 区块加 `pending_metrics: [ks_improvement, rule_interpretability]` + `pending_reason`）
- `evaluation/runner/adapters/agent2_riskctrl.py`（两 stub 的 `MetricOutcome` 继续 `passed=None, method="manual"`，但 `note` 改为更明确的 pending 语义 —— 「等 Phase 2 runtime baseline_ruleset 对照组 / LLM-judge 实装」）

**deliverables**：
- yaml `baseline.pending_metrics: [ks_improvement, rule_interpretability]`
- yaml `baseline.pending_reason: "Phase-2 runtime baseline_ruleset 对照组依赖 + LLM-judge 未实装"`
- adapter 两 stub 的 `note` 字段对齐 yaml 的 pending_reason，一字节级同义（便于日后 grep 追溯）
- runner framework 已由 A-013 落地 `_verdict()` 白名单逻辑，worker 只需配 yaml + adapter note，**不得改 `base_evaluator.py`**

**DoD**：
- [ ] `evaluation/agent2_riskctrl.yaml` 含 `baseline.pending_metrics: [ks_improvement, rule_interpretability]` 与 `baseline.pending_reason` 字段
- [ ] `py -m evaluation.runner --agent riskctrl` verdict = **PASS**（不是 PARTIAL；pass+pending 组合命中 A-013 的豁免）
- [ ] runner 输出里两 stub 仍可见（Evidence-First：不是丢弃，而是「pending 不降档」），`note` 字段显式说明依赖
- [ ] `git diff evaluation/runner/base_evaluator.py` 为空（worker 零内核改动）
- [ ] 单测（若 worker 新增）：pass+pending → PASS / pass+fail → FAIL / 无 pending list → PARTIAL 三组回归

---

### Task C · per-rule fpr_spread 新指标（对应 Phase 0 Gap #3）

**goal**：当前 `false_positive_rate = 0.0673` 是全规则合并 FPR，R002 高负债率等单条规则误杀率被掩盖。Phase 1 扩 `per_rule_confusion_matrix` 并新增 `per_rule_fpr_spread` 警戒高方差 —— 治「规则集整体绿、单条规则偏激」的盲区。

**modules**：
- `agent_riskctrl/backtesting.py`（改；`BacktestResult.metrics.rule_stats` 现有结构扩 per-rule `{TP, FP, TN, FN}`；`run_backtest` 按 label_column × rule.action 逐条规则算混淆矩阵）
- `evaluation/runner/adapters/agent2_riskctrl.py`（改；`compute_domain_metrics` 新增 `per_rule_fpr_spread` 计算：从 `backtest.confusion_matrix.per_rule` 读每条规则的 FP/(FP+TN)，取方差或 max-min spread）
- `evaluation/agent2_riskctrl.yaml`（改；`metrics.domain` 追加 `per_rule_fpr_spread` 定义；target 需主 CLI 裁定，见 §8 Q-014）
- Runtime 产物 schema：`backtest.json.confusion_matrix.per_rule`（list-of-dict：`[{rule_id, FP, TN, FP_rate}]`，保持向后兼容，原 `confusion_matrix.{TP,FP,TN,FN}` 字段不删）

**deliverables**：
- `BacktestResult` 里每条规则附自己的混淆矩阵（不仅是当前的 `hit_count / hit_rate`）
- adapter 计算 `per_rule_fpr_spread`：
  - 若 ≥ 2 条规则：取各规则 FP_rate 的总体方差（或 max-min，worker 选一报 Q-014，推荐方差）
  - 若 < 2 条规则：`value=None, note="少于 2 条规则，spread 不适用"`
- yaml `metrics.domain` 新条目结构与现有指标对齐：
  ```yaml
  - name: per_rule_fpr_spread
    desc: 各规则 FPR 方差（或 max-min），警戒「整体绿但单条偏激」
    target: "<= <TBD by main CLI via Q-014>"
  ```
- Baseline 跑出真实数字（Task A runtime 产物 + Task C 扩展计算 → yaml baseline.results 补 `per_rule_fpr_spread: <value>`）
- 警戒条款写入 yaml 注释：`# per_rule_fpr_spread 超阈值 → 即使整体 FPR 过线也视为红线`（作「正式条款待 Q-014」草案，主 CLI 裁决后固化）

**DoD**：
- [ ] `agent_riskctrl/backtesting.py` 的 `BacktestResult.metrics.rule_stats` 每条规则含 `{FP, TN, FP_rate}`（`TP`/`FN` 可选但推荐）
- [ ] `evaluation/runner/adapters/agent2_riskctrl.py` 的 `compute_domain_metrics` emit `per_rule_fpr_spread` MetricOutcome，`method="deterministic"`
- [ ] `evaluation/agent2_riskctrl.yaml` `metrics.domain` 含 `per_rule_fpr_spread`（target 先占位 `<TBD Q-014>`，A-014 下发后 worker 改实值）
- [ ] Baseline 跑出真实 `per_rule_fpr_spread` 数值并回填 yaml `baseline.results`
- [ ] `agent_riskctrl/tests/` 补 ≥ 1 条单测，构造 2 条规则的回测结果，验证 spread 计算正确
- [ ] 若计算得到的 spread 超 worker 自定的警戒草案值（Q-014 前用启发式，如 ≥ 0.2），adapter `MetricOutcome.passed=False` 并在 `note` 写「等 Q-014 最终阈值」

---

### Task D · 规则编辑器前端入口存根（对应 L1 bank delivery DoD gap）

**goal**：L1 bank delivery DoD 要求有「用户可见的策略入口」，但完整规则编辑器（DSL 所见即所得 + 语法校验 + 在线回测）是 Phase 2 工作量。Phase 1 只做**最小存根**：ReadOnly 规则展示页 + 导出 JSON 按钮，让客户经理/策略经理第一眼看到「规则集的样子」+「能把它拿走」。

**两选项，worker ACK 时明示选 D-frontend 还是 D-fallback**：

#### D-frontend 方案 · 接入现有 `web/src/app/riskctrl/page.tsx`

**modules**：
- `web/src/app/riskctrl/page.tsx`（改；现有骨架已有「基线策略 / 候选策略 / 样本池 / 规则命中率 / DSL diff」语义，补一个 ReadOnly 「规则详情」子区 + 「导出 JSON」按钮）
- `web/src/components/` 下新增 `<RuleReadOnlyList>` 组件（或复用现有 viz/Card）
- 数据源：Mock 一份 `web/public/mock/riskctrl_ruleset.json`（Phase 1 不接真实 API，等前端 Stage 3 workspace 解耦完再接）

**deliverables**：
- ReadOnly 规则展示：表格列 `rule_id / name / conditions (AND 合) / action (中文) / priority`；规则描述支持 markdown 折叠
- 「导出 JSON」按钮：点击下载 `ruleset.json`（从 mock 读，也可从 session state 读）
- 规则编辑器入口占位：一个 disabled 状态的「进入编辑器」按钮，hover tooltip「Phase 2 交付」
- 不动 `api_server.py` / 不加 `/api/riskctrl/*` 路由（红区）
- `web/src/app/riskctrl/page.tsx` 的改动范围**只**在现有页面骨架内增加子区域，不改其他 5 个 agent 路由

**deliverables（frontend 环境约束）**：
- 前提：`web/` 是 Next.js 16 新版本，不是 worker 训练数据里的版本。动手前读 `web/AGENTS.md`（已明示）+ `web/node_modules/next/dist/docs/` 相关章节
- 样式主题统一：沿用 `docs/design/platform-shell-v1.md` 的 `data-theme=Canvas` + `--r-md: 18px` 圆角 + JetBrains Mono 数字字体

**DoD（D-frontend）**：
- [ ] `web/src/app/riskctrl/page.tsx` ReadOnly 规则展示区域可见（`cd web && pnpm tsc --noEmit` 0 errors）
- [ ] `cd web && pnpm dev` → `curl -s http://localhost:3000/riskctrl` 返回 200
- [ ] 「导出 JSON」按钮点击可下载有效 JSON（`ruleset.json` schema 对齐 `rules.json` Phase 0 fixture）
- [ ] 「进入编辑器」按钮 disabled + tooltip 正确
- [ ] 无 `api_server.py` / `agent_*/api/` 改动（red zone clean）

#### D-fallback 方案 · 设计稿交付

**modules**：
- `docs/design/rule-editor-stub.md`（新建；最小设计稿）

**deliverables**：
- 3-4 张线框图（文字版也可；参考 `docs/design/platform-shell-v1.md` 写法）
- 明确 ReadOnly 子区的信息架构、「导出 JSON」交互、「进入编辑器」占位状态
- Phase 2 切入点清单（哪里扩 API / 哪里接状态机 / 哪里做 DSL 语法校验）

**DoD（D-fallback）**：
- [ ] `docs/design/rule-editor-stub.md` 存在，≥ 100 行有效内容
- [ ] 包含线框图（文字或 ASCII-art）+ 交互流 + Phase 2 切入清单
- [ ] 不动任何代码

**推荐**：D-frontend（现有 `web/src/app/riskctrl/page.tsx` 骨架已经有策略语义，边际改动小；且 bank delivery DoD L1 要求「可见门面」，设计稿不算交付）。worker ACK 时如有顾虑（Next.js 16 陌生 / 环境缺失）可选 D-fallback，主 CLI 不反对。

---

## 4. 红区 & 硬规则

### 红区字面枚举（含 Phase 1 新增）

❌ 以下路径 worker **不得改动**；遇冲突只许保 upstream + abort + Q：

- `shared/**`
- `docs/contracts/**`
- `api_server.py`
- `agent_*/api/**`
- `evaluation/runner/__init__.py`
- `evaluation/runner/adapters/__init__.py`
- `evaluation/runner/base_evaluator.py`
- `evaluation/runner/registry.py`
- `evaluation/runner/cli.py`
- `evaluation/runner/__main__.py`
- `docs/handoff/decisions-log.md`
- `docs/handoff/shared-change-protocol.md`（主 CLI 未来起草后写入矩阵，Phase 1 worker 仍只读）

**灰区澄清**：Agent1 Phase 1 已立规——`evaluation/runner/**/__init__.py` 与 `decisions-log.md` 即使 add-only docstring / dedup 删除也不行。本 Phase 2 同规则继承，任何「看似无害」的改动都必须先 Q-NNN。

允许 worker 动：

- ✅ `evaluation/runner/adapters/agent2_riskctrl.py`
- ✅ `evaluation/agent2_riskctrl.yaml`
- ✅ `evaluation/results/2_*.yaml`
- ✅ `evaluation/manual/2_*.yaml`
- ✅ `evaluation/runtime/2_*/`（新目录，runtime 产物）
- ✅ `agent_riskctrl/**`（工具域内部，不含对外 API）
- ✅ `agent_riskctrl/tests/**`
- ✅ `scripts/run_agent2_baseline.py`（新建）
- ✅ `web/src/app/riskctrl/page.tsx` + `web/src/components/**`（仅 Task D-frontend 选中时）
- ✅ `web/public/mock/riskctrl_*.json`（仅 Task D-frontend）
- ✅ `docs/progress/agent2-phase-1-*.md`（worker 自己的进度档）
- ✅ `docs/design/rule-editor-stub.md`（仅 Task D-fallback 选中时）

### 硬规则

- **R-A smoke-must-test**：每 Task commit message 声称跑过的冒烟命令，必须在**提交分支当前 HEAD** 上实测过（A-006）。违反 → review 自动 CONDITIONAL
- **R-B 一 commit 一 Signal**：`git log --format='%b' HEAD` 自检 trailer 数量 = 1
- **R-C cherry-pick amend trailer**：本 Phase worker 不会 cherry-pick，但若真遇到则必须 amend 从 worker signal 改主 CLI 视角
- **A-012.D SHA 不可变**：已被主 CLI review 文档引用过的 commit（如 `b21737e` / `f7e98d1` / `3f69075` / `7a2579e` / `ff1b1bd`）**禁止 rebase / amend / force-push**；纠错只许新 commit
- **Signal await semantics**（`memory/feedback_signal_await_semantics.md`）：worker 每个 `READY-FOR-REVIEW` / `TASK-X-DONE` / `NEED-DECISION` 都是**隐式 await-proceed gate**，必须停下等主 CLI GO；不许自己一路推到底。Phase 0 progress doc 已自陈违规一次，Phase 1 零容忍
- **无基线不改码**（CLAUDE.md §5.2）：Task C 新指标落地前必须先跑基线拿真实 spread，再讨论阈值；不许拍脑袋定 target
- **A-013 白名单只消费不改动**：kernel 白名单逻辑由主 CLI 已落地，worker 只配 yaml + adapter `note`，碰 `base_evaluator.py` 即越界

---

## 5. Signal 流程

| 时点 | Signal |
|---|---|
| 读完 onboarding | `AGENT2-PHASE-1-ACK` |
| Task A 完成 | `AGENT2-PHASE-1-TASK-A-DONE` |
| Task B 完成 | `AGENT2-PHASE-1-TASK-B-DONE` |
| Task C 完成 | `AGENT2-PHASE-1-TASK-C-DONE` |
| Task D 完成 | `AGENT2-PHASE-1-TASK-D-DONE` |
| 全部 ready | `AGENT2-PHASE-1-READY-FOR-REVIEW` |
| Review 通过收工 | `WINDOW-CLOSED-CLEAN` |
| 有疑问 | `NEED-DECISION Q-NNN`（下一个可用 **Q-014**） |

ACK 命令：

```bash
git commit --allow-empty -m "ack(agent2): Phase 1 onboarding absorbed" -m "" -m "Signal: AGENT2-PHASE-1-ACK"
```

ACK commit 里同时**明示两件事**：
1. Task D 选 D-frontend 还是 D-fallback
2. Q-014 问 `per_rule_fpr_spread` 的 target 阈值（worker 给推荐值 + rationale，主 CLI 裁定）

---

## 6. DoD 汇总 / 评估基线预期

### 全 Phase 终态

- [ ] runner `py -m evaluation.runner --agent riskctrl` verdict = **PASS**（这是 Phase 0 PARTIAL 升 Phase 1 APPROVED 的硬条件）
- [ ] 红线闸门不倒退（相对 Phase 0 fixture 基线 0.9x 容忍）：
  - `hallucination_rate ≤ 0.01`
  - `evidence_rate ≥ 0.98`
  - `task_completion_rate ≥ 0.95`
  - `tool_success_rate ≥ 0.95`
  - `false_positive_rate ≤ 0.15`（runtime 值允许 > 0.0673 但不破 0.15）
  - `per_rule_fpr_spread ≤ <A-014 值>`（新增红线）
- [ ] `py -m pytest agent_riskctrl/ -q` 全绿（含 Task C 新增单测）
- [ ] `evaluation/results/2_YYYYMMDD.yaml` 新 baseline 落盘，verdict = PASS
- [ ] `evaluation/runtime/2_latest/` 有 runtime 产物
- [ ] scorecard ≥ 72%（主 CLI review 更新 `docs/scorecard/GLOBAL.md`）

### 任一红线不过

→ 写 `docs/progress/agent2-phase-1-gap.md` 记录 gap 原因，**不要**强改 adapter / fixture 让指标达标（CLAUDE.md §12）。

---

## 7. 时限 & 推进顺序

- 建议 2-3 工时（不含 Task D 耗时：D-frontend +1 工时 / D-fallback +0.5 工时）
- 顺序：**A → B → C → (等 A-014) → D → READY-FOR-REVIEW**
- Task A / B 有序但逻辑独立（A 落 runtime 产物后，B 只改 yaml + adapter note，可在 A 未完成时并行起草）
- Task C 依赖 A 的 runtime 产物（per-rule matrix 从 runtime backtest 跑出来才有意义）
- Task D 可与 A/B/C 并行（不依赖评估链路）
- 每 Task DONE 后主 CLI 可能发 mid-review 指令，worker 停等 GO 再进下一个 Task

---

## 8. Q/A

疑问 → `docs/handoff/decisions-log.md` append `## [Q-014]`（下一个可用）→ trailer `Signal: NEED-DECISION Q-014` → 等主 CLI append `### [A-014]`。

**特别注意**：

- 红区冲突 **立即 abort + Q**，任何「优化 / dedup / add-only」都不自决（Agent1 Phase 1 已立规）
- Task C `per_rule_fpr_spread` target 必须通过 Q-014 拿主 CLI 裁定 —— 推荐 worker 在 ACK commit 或独立 commit 给**两个选项**：
  - 方差 σ² ≤ 0.03（保守）
  - max-min spread ≤ 0.15（宽松）
  - 附 rationale：Phase 0 fixture 跑出的 per-rule spread 作基础参考
- Task D 若选 D-frontend 但 Next.js 16 API 陌生到无法 2 工时内搞定，可中途切 D-fallback，但要发独立进度 commit 说明（不算违规，算诚实降级）

---

## 附：参考文件速查

- Review 依据：`docs/review/agent2-phase-0-review.md`（Top 3 Gap）
- 契约对标：`docs/onboarding/agent1-phase-1.md`（格式模板 + Signal 序列）
- 协议基线：`docs/handoff/decisions-log.md` A-006（R-A/B/C）/ A-008 / A-009（rebase 批量授权矩阵）/ A-012（SHA 不可变 + pending 语义）/ A-013（`baseline.pending_metrics` 白名单 kernel patch）
- Runner framework：`evaluation/runner/base_evaluator.py` / `registry.py` / `cli.py` / `__main__.py`（红区，只读）
- Adapter 参考：`evaluation/runner/adapters/agent6_report.py`（Phase A 模式）/ `evaluation/runner/adapters/agent1_channel.py`（Phase 1 契约形态 + pending 落地）/ `evaluation/runner/adapters/agent2_riskctrl.py`（Phase 0 现状）
- 前端 spec：`docs/design/platform-shell-v1.md`（Task D-frontend 样式基线）/ `web/AGENTS.md`（Next.js 16 新版本提示）
- 已存在页面骨架：`web/src/app/riskctrl/page.tsx`（Task D-frontend 切入点）
- DoD 定义：`docs/scorecard/definition-of-done.md` v1.0 / `memory/project_bank_delivery_dod.md`
- 全局看板：`docs/scorecard/GLOBAL.md`
