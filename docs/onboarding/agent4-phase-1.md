# Agent4 预警 · Phase 1 Productize Onboarding

**对应 worktree**：`D:\claude code\demo-agent4`（`feat/agent4-productize`）
**发布日期**：2026-04-19
**前置**：已读 `AGENT_IDENTITY.md` + `CLAUDE.md` + 本文 + `docs/review/agent4-phase-0-review.md` + `docs/handoff/decisions-log.md`（特别 A-012.D / A-013）+ `memory/project_agent_alert_pivot.md` + `memory/project_agent_functional_boundaries.md`
**目标**：把 Agent4 从「Phase 0 APPROVED @ `e881d24`，scorecard 57%」推到「Phase 1 productize APPROVED，scorecard ≥ 68%」，runner `py -m evaluation.runner --agent alert` verdict = **PASS**。

---

## 背景（3 行速读）

Phase 0 APPROVED @ `e881d24`（Signal `AGENT4-PHASE-0-READY-FOR-REVIEW`），review 记录 Top 3 Gap：
1. **合成 fixture** — 3/22/75 分布、180-2200ms 延迟、枚举 signal 都是人工拍的，不证"识别准不准"
2. **Phase C 真值缺失** — `cross_hit_precision` / `recall_on_known_bad` 当前全部 stub，Agent4 核心价值未量化
3. **无回归护栏** — `agent_alert/tests/` 只有 fixtures/，adapter 的 `_p95` / grade 阈值 / evidence 判定裸奔

Phase 1 对齐 agent1 Phase 1 定型契约（4 Task 全绿 @ `c408b3a` runner PASS，A-013 pending_metrics 白名单机制 + A-012.D SHA 不可变）把上面 3 条合拢，并把"可交付银行"层级从 L1 推到 L2/L3。

---

## 1. 范围 & 不做什么

### productize 定义（对齐 `memory/project_bank_delivery_dod.md`）

| 层 | 本 Phase 交付项 | 当前状态 |
|---|---|---|
| L0 最低起跑线 | runner 挂通 + 红线闸门全绿 | ✅ Phase 0 已达成 |
| L1 功能完整 | 批量扫描（双路命中）+ 分级榜单 | ✅ v3.1 不动 |
| L2 可审计可追溯 | runtime fixture + 原因码分类 + pending 语义诚实 | ❌ 本 Phase 做 |
| L3 可量化可验收 | runner `--agent alert` = **PASS** + 仪表盘设计稿 | ❌ 本 Phase 做 |

### 不做什么（明确排除，防 scope creep）

- ❌ **不做政策变更触发**：那是 **Agent5 合规**的边界（见 `memory/project_agent_functional_boundaries.md`）。Agent4 只在**客户行为变化**触发——在贷客户池 + 规则库 + 双路扫描。两者共享 `shared/kb_scan/` 底座但**不合并**
- ❌ **不做 autopilot**：红/黄灯客户清单仍需客户经理复核，不自动冻结额度 / 停贷
- ❌ **不做 Phase C 真值库落地**：`cross_hit_precision` / `recall_on_known_bad` 需要业务方标注 known-bad 清单，本 Phase 按 A-013 pending 语义走，不假装能跑
- ❌ **不做前端 Shell 实装**：Task D 只出设计稿，前端由 frontend Stage 3 CLI 实装
- ❌ **不做 Tavily 生产 key / 真外网扫描接入**：Phase 2 Batch 2 里程碑，与本 Phase 解耦
- ❌ **不做跨 Agent 编排**：Agent4 边界在「客户池扫描 → 分级榜单」，不触发 Agent3 决策 / Agent6 报告重生

---

## 2. 前置条件

- 主 CLI HEAD：`7e6438d`（`A-013 α kernel — pending_metrics whitelist in _verdict`）之后；worker 先 `git fetch upstream && git log upstream/chore/l0-infra --oneline -5` 确认 A-013 kernel patch 已拿到
- worker 起点：`feat/agent4-productize` @ `e881d24`（Phase 0 READY-FOR-REVIEW commit）
- `git fetch upstream && git rebase upstream/chore/l0-infra` 拿到本 onboarding + A-013 kernel + 主干最新，再开工
- Phase 0 红线闸门基线（`9dfcaf2` 已验证）：hallucination 0.00 / evidence 1.00 / task 1.00 / tool 0.9667 —— 本 Phase 不许倒退

---

## 3. Task 清单（4 Task，预计 2-3 工时）

### Task A · Fixture → Runtime（Phase 0 Gap #1 对齐）

**goal**：把合成 fixture 替换为 `AlertAgent` 端到端产物；`evaluation/manual/4_YYYYMMDD.yaml` 从 runtime 回填；保留原 fixture 作「回归锚」（schema 对齐单测基线）。

**modules**：
- `agent_alert/customer_scanner.py` / `cross_matcher.py` / `alert_engine.py`（读）——确认 `scan()` 已能批量输出
- `agent_alert/ledger_exporter.py`（读 + 可能薄改）——产出 runtime dump 的落盘点
- `evaluation/runner/adapters/agent4_alert.py`（改 `load_artifacts` 优先吃 runtime dump，fallback 到 fixture）
- `evaluation/manual/4_20260419.yaml`（新增，从 runtime 回填 100 家客户样本）
- `agent_alert/tests/fixtures/phase0_scan_sample.json`（保留，注释为「回归锚」，schema 冻结）
- `agent_alert/tests/test_adapter_contract.py`（新增，锁 adapter 消费契约——见 Task C 配合）

**deliverables**：
- `AlertAgent.scan()`（或等价入口）跑一次 100 家客户（用现有 `knowledge_base.py` demo 客户池），dump JSON 到 `evaluation/manual/4_20260419.yaml`
- adapter `load_artifacts` 逻辑：`run.artifacts[0]` 存在且指向 runtime yaml → 走 runtime；否则 fallback 到 `DEFAULT_FIXTURE`（phase0_scan_sample.json）
- phase0 fixture 头部加注释块：`# regression anchor — schema frozen 2026-04-19，勿修改分布/延迟/枚举，仅供 adapter 回归单测使用`
- 更新 `evaluation/agent4_alert.yaml` 的 `baseline.artifact` 从 fixture 路径改为 `evaluation/manual/4_20260419.yaml`
- `baseline.notes` 补一段说明 runtime 来源（哪个 `git rev-parse HEAD` 跑的、kb 版本）

**DoD**：
- [ ] `evaluation/manual/4_20260419.yaml` 实存且 ≥ 100 条客户记录，每条含 `entity_id / grade / evidence / scan_time_ms / status`（schema 对齐 phase0_scan_sample.json）
- [ ] `evaluation/runner/adapters/agent4_alert.py` `load_artifacts` 读取 runtime yaml 路径成功
- [ ] `py -m evaluation.runner --agent alert` 仍可跑（verdict 由 Task B 决定）
- [ ] phase0_scan_sample.json 头部含「回归锚」注释
- [ ] `evaluation/agent4_alert.yaml` `baseline.artifact` 指向 runtime yaml

---

### Task B · pending_metrics 语义落地（对齐 A-013 α kernel）

**goal**：把 Phase C 人工指标（`cross_hit_precision` / `recall_on_known_bad`）纳入 A-013 pending 白名单；runner verdict 从 PARTIAL 升 **PASS**；不假装能跑、不静默 N/A。

**modules**：
- `evaluation/agent4_alert.yaml`（加 `baseline.pending_metrics: [...]` + `pending_reason`）
- `evaluation/runner/adapters/agent4_alert.py`（stub 分支保留 `value=None, method="manual"` + note 更明确说明 pending 去向；adapter 本身不需要改 verdict 逻辑——A-013 kernel 已在 base_evaluator 里兜底）

**deliverables**：
- yaml `baseline` 区块加：
  ```yaml
  pending_metrics:
    - cross_hit_precision
    - recall_on_known_bad
  pending_reason: "Phase 2 Batch 2 — 需业务方标注 known-bad 清单 + 真实外部源（Tavily/工商/司法）接入"
  ```
- adapter stub 的 `note` 字段从「Phase C stub」改为「pending: Phase 2 Batch 2 human ground-truth」，与 yaml pending_reason 语义一致
- 跑 `py -m evaluation.runner --agent alert`，verdict 应 = **PASS**（6 deterministic PASS + 2 pending 豁免，A-013 kernel 逻辑）

**DoD**：
- [ ] `py -m evaluation.runner --agent alert` verdict = **PASS**（实测截屏 / 日志落 commit message）
- [ ] `evaluation/agent4_alert.yaml` `baseline.pending_metrics` 字段存在，列出 2 个 pending 指标
- [ ] 红线闸门不倒退：hallucination ≤ 0.01 / evidence ≥ 0.95 / task ≥ 0.95 / tool ≥ 0.90
- [ ] adapter 的 pending stub `note` 里显式写 "pending: Phase 2 Batch 2"，不留"Phase C stub"模糊表述

---

### Task C · 原因码增强（Phase 0 Gap — 缺原因码）

**goal**：`AlertResult` / `AlertReport` 输出增 `trigger_reasons: list[str]` 字段；分类枚举（非关键词黑名单！），前端按原因码分桶展示用。

**关键纪律**：枚举**从已有结构推断**，不是硬编关键词黑名单——
- `AlertSignal.category` 已有 5 类（财务恶化/法律诉讼/经营异常/行业风险/关联风险）
- `RuleHit.route` 已有 2 路（external / internal）
- 本 Task 的 `trigger_reasons` 3 值枚举 = **外网信号 / 内部规则 / 交叉命中**，从 `route` 集合推断（external only → external_signal；internal only → internal_rule；both → cross_hit）

这是 CLAUDE.md §12 "通用机制（相似度比较、角色分类、结构推断），不要关键词/正则黑名单"的正面落地，review 会特别盯这点。

**modules**：
- `agent_alert/alert_engine.py`（`AlertReport` 加 `trigger_reasons: list[str] = Field(default_factory=list)`）
- `agent_alert/cross_matcher.py`（`match_customer` 返回结构里补 `trigger_reasons` 计算——读 hits 的 `route` 集合 → 枚举推断）
- `evaluation/runner/adapters/agent4_alert.py`（消费 `trigger_reasons` 作为 evidence 展示维度，不改现有指标语义）
- `agent_alert/tests/test_trigger_reasons.py`（新增，锁枚举推断逻辑——3 case：仅外 / 仅内 / 双路）
- `docs/design/alert-trigger-reasons-taxonomy.md`（新增，把 3 枚举定义成文档；**不是关键词表**，是语义规约 + 推断规则）

**deliverables**：
- 枚举值：`external_signal` / `internal_rule` / `cross_hit`（英文便于前端消费，文档里给中文映射）
- `AlertReport.trigger_reasons` 非空（除非 green 无任何触发）
- `docs/design/alert-trigger-reasons-taxonomy.md` 必含章节：
  1. 3 枚举语义定义（**不是**关键词列表）
  2. 推断规则（伪代码：`{hit.route for hit in hits}` → 枚举映射）
  3. 为什么不用关键词黑名单（引 CLAUDE.md §12 + §3.1 概率 vs 确定性）
  4. 前端展示约定（分桶色系 hook Stage 3 Task C/D，非本 Phase 实装）
- adapter 消费：`load_artifacts` 读 runtime yaml 里每条客户的 `trigger_reasons`，在 `compute_domain_metrics` 或 `compute_common_metrics` 的 `evidence` 字段里 pass-through（不新增指标）
- 单测：`test_trigger_reasons.py` ≥ 3 case，枚举推断逻辑 pin 死

**DoD**：
- [ ] `AlertReport.trigger_reasons` 字段存在且在 demo 跑一次后非空（grep 证据：`grep -rn "trigger_reasons" evaluation/manual/4_20260419.yaml` ≥ 1 hit）
- [ ] `docs/design/alert-trigger-reasons-taxonomy.md` 4 章节齐全，**不含关键词清单**（review 会 grep 否定证据）
- [ ] `py -m pytest agent_alert/tests/test_trigger_reasons.py -v` ≥ 3 passed
- [ ] adapter 消费后能在 evidence 字段 / note 字段看到原因码串（grep `grep -n "external_signal\|internal_rule\|cross_hit" evaluation/runner/adapters/agent4_alert.py` ≥ 1 hit）

---

### Task D · 仪表盘 + 导出存根（L1 bank delivery DoD gap）

**goal**：低 fidelity 交付——出 `docs/design/alert-dashboard-stub.md` 设计稿；**不做**前端实装（归 frontend CLI Stage 3 或后续 stage）；产出实装 ticket 移交。

**modules**：
- `docs/design/alert-dashboard-stub.md`（新增）
- `docs/progress/agent4-phase-1-frontend-handoff.md`（新增，ticket 形态移交给 frontend CLI）

**deliverables**：
- 设计稿三块（低 fidelity，文字描述 + ASCII wireframe 即可，不要 HTML mockup）：
  1. **红/黄/绿客户数卡片**：当日扫描总数 + 3 level 计数 + 环比昨日
  2. **原因码分布**：Task C 的 3 枚举（外网 / 内部 / 交叉）横向堆叠条；交叉命中高亮（这是 Agent4 核心价值点）
  3. **近 30 天趋势**：每日红灯数折线 + 新增原因码来源面积图
- 每块设计稿含：目的 / 数据源（对 runtime yaml 的字段引用）/ 前端交互约定 / Stage 3 色系 hook 点（Canvas/Matcha/Dusk/Crimson 4 主题变量名，对齐 `docs/design/platform-shell-v1.md`）
- ticket 移交档 `docs/progress/agent4-phase-1-frontend-handoff.md` 含：
  - 依赖 commit / 分支（本 Phase 1 final commit SHA）
  - 需要 frontend CLI 实装的范围（3 卡片）
  - 数据源契约（runtime yaml schema，Task A 落地）
  - 建议 Stage（Stage 3 Task C/D 或之后）
  - 明确声明**不在本 Phase 实装**

**DoD**：
- [ ] `docs/design/alert-dashboard-stub.md` 三块设计稿齐全，含数据源字段引用
- [ ] `docs/progress/agent4-phase-1-frontend-handoff.md` ticket 存在
- [ ] **不碰** `web/` 任何文件（grep `git diff --stat upstream/chore/l0-infra..HEAD -- web/` = 0 行）

---

## 4. 红区 & 硬规则

### 红区字面枚举（agent4 特有：强化 shared/kb_scan）

❌ 以下路径 worker **不得改动**；遇冲突只许保 upstream + abort + Q：

- `shared/**`（**特别 `shared/kb_scan/`** —— agent4 与 agent5 共享的矩阵扫描底座；任何改动必须走 RFC，即使 add-only 也要 Q）
- `docs/contracts/**`
- `api_server.py`
- `agent_*/api/**`（含 `agent_alert/api/` 若存在，当前不存在也按红区对待——防未来误触）
- `evaluation/runner/__init__.py`
- `evaluation/runner/adapters/__init__.py`
- `evaluation/runner/base_evaluator.py`（A-013 kernel 已改，任何进一步改动必 Q）
- `evaluation/runner/registry.py`
- `evaluation/runner/cli.py`
- `evaluation/runner/__main__.py`
- `docs/handoff/decisions-log.md`（主 CLI 唯一写；add-only 也不行，必须 Q）

**特别强调**：Agent5 合规 CLI 可能在同期启动，`shared/kb_scan/` 双方共享；任何"顺手优化"冲动 → 立即 abort + Q，即使是看起来无害的 docstring / 注释也不自决。

允许 worker 动：

- ✅ `evaluation/runner/adapters/agent4_alert.py`
- ✅ `evaluation/agent4_alert.yaml`
- ✅ `evaluation/results/4_*.yaml`（gitignored）
- ✅ `evaluation/manual/4_*.yaml`（Task A 落地）
- ✅ `agent_alert/**`（工具域内部，不含对外 API）
- ✅ `agent_alert/tests/**`（Task A/C 落地单测）
- ✅ `docs/design/alert-trigger-reasons-taxonomy.md`（Task C 新文件）
- ✅ `docs/design/alert-dashboard-stub.md`（Task D 新文件）
- ✅ `docs/progress/agent4-phase-1-*.md`（worker 自己的进度/handoff 文档）

### 硬规则

- **R-A smoke-must-test**：每 Task commit message 声称跑过的冒烟命令，必须在**提交分支当前 HEAD** 上实测过再入 commit（A-006）。违反 → review 自动 CONDITIONAL
- **R-B 一 commit 一 Signal**：`git log --format='%b' HEAD` 自检 trailer 数量 = 1
- **A-012.D SHA 不可变**：已被主 CLI review 文档引用的 commit SHA（例如本 onboarding 引用的 `e881d24` / `52d3f90` / `9dfcaf2`）不可 rebase/amend/force-push；纠错用新 commit 追加
- **Signal await semantics**（`memory/feedback_signal_await_semantics.md`）：每个 `READY-FOR-REVIEW` / `NEED-DECISION` / 每 Task `-DONE` 都是**隐式 await-proceed gate**，必须停下等主 CLI GO；不许自己一路推到底
- **无基线不改码**（CLAUDE.md §5.2）：质量类动作对标 runner 产物 `evaluation/results/4_*.yaml` 数字，不拍脑袋
- **分类枚举 ≠ 关键词黑名单**（CLAUDE.md §12）：Task C 必须从结构推断（`route` 集合），不许写关键词→枚举映射表

---

## 5. Signal 流程

| 时点 | Signal |
|---|---|
| 读完 onboarding | `AGENT4-PHASE-1-ACK` |
| Task A 完成 | `AGENT4-PHASE-1-TASK-A-DONE` |
| Task B 完成 | `AGENT4-PHASE-1-TASK-B-DONE` |
| Task C 完成 | `AGENT4-PHASE-1-TASK-C-DONE` |
| Task D 完成 | `AGENT4-PHASE-1-TASK-D-DONE` |
| 全部 ready | `AGENT4-PHASE-1-READY-FOR-REVIEW` |
| Review 通过收工 | `WINDOW-CLOSED-CLEAN` |
| 有疑问 | `NEED-DECISION Q-NNN`（下一个可用 **Q-014**——ACK 前 read `docs/handoff/decisions-log.md` 拿当前最大号 +1，因与 agent2 Phase 1 / agent6 Phase 2 共享编号空间，可能已被占用） |

ACK 命令：

```bash
git commit --allow-empty -m "ack(agent4): Phase 1 onboarding absorbed" -m "" -m "Signal: AGENT4-PHASE-1-ACK"
```

ACK commit trailer 里确认 Q-NNN 下一个可用编号（read decisions-log 确认后填）。

---

## 6. DoD 汇总 / 评估基线预期

### 全 Phase 终态

- [ ] runner `py -m evaluation.runner --agent alert` verdict = **PASS**（Phase 0 PARTIAL 升 PASS 的硬条件）
- [ ] 红线闸门不倒退：
  - `hallucination_rate ≤ 0.01`
  - `evidence_rate ≥ 0.95`
  - `task_completion_rate ≥ 0.95`
  - `tool_success_rate ≥ 0.90`
- [ ] `py -m pytest agent_alert/ -q` ≥ 3 passed（Task A/C 新增的回归护栏）
- [ ] `evaluation/results/4_YYYYMMDD.yaml` 新 baseline 落盘 verdict = PASS
- [ ] `evaluation/manual/4_20260419.yaml` runtime 回填样本 ≥ 100 条
- [ ] `AlertReport.trigger_reasons` 字段落地 + 3 枚举单测通过
- [ ] `docs/design/alert-trigger-reasons-taxonomy.md` + `docs/design/alert-dashboard-stub.md` + frontend handoff ticket 三件齐
- [ ] scorecard ≥ 68%（主 CLI review 更新 `docs/scorecard/GLOBAL.md`）

### 任一红线不过

→ 写 `docs/progress/agent4-phase-1-gap.md` 记录 gap 原因，**不要**强改 adapter / fixture / 枚举让指标达标（CLAUDE.md §12 + Evidence-First）。

---

## 7. 时限 & 推进顺序

- 建议 2-3 工时（含 Task C 枚举文档 + 单测）
- 顺序：**A → B → C → D → READY-FOR-REVIEW**
- Task A 是后续所有 Task 的数据基座；Task B 依赖 A 的 runtime yaml 生成；Task C 改 AlertReport schema 后需回跑 A 重生 runtime yaml；Task D 独立可并行但建议放最后（依赖 Task C 的 trigger_reasons 作为仪表盘中间块的数据源）
- 每 Task `-DONE` 后主 CLI 可能发 mid-review 指令，worker 停等 GO 再进下一 Task

---

## 8. Q/A

疑问 → `docs/handoff/decisions-log.md` append `## [Q-NNN]`（ACK 前先 read 拿当前最大号 +1）→ trailer `Signal: NEED-DECISION Q-NNN` → 等主 CLI append `### [A-NNN]`。

**特别注意**：
- 红区冲突 **立即 abort + Q**，任何"优化 / dedup / add-only" 都不自决（特别是 `shared/kb_scan/`，agent5 可能在动）
- Task A runtime 生成若发现 AlertAgent 入口不稳 / 抛异常 → 先 Q 再动，不自己魔改 customer_scanner
- Task C 枚举推断若发现 `RuleHit.route` 现有字段不足以支撑 3 值区分 → Q（不要擅自扩 route 枚举）

---

## 9. 与 Agent5 的边界（再次强调）

Agent4 **不是**政策变更驱动，Agent5 才是。

| 维度 | Agent4 预警 | Agent5 合规 |
|---|---|---|
| 触发源 | **客户行为变化**（流水/工商/舆情动了） | **政策变更事件**（新监管办法发布） |
| 输入 | 在贷客户池 + 规则库 | 新政策 + 业务制度库 |
| 输出 | 红/黄/绿客户榜单 | 违规冲突点明细 |
| 共享底座 | `shared/kb_scan/`（共用，不合并） | `shared/kb_scan/`（共用，不合并） |

Task C 的 `trigger_reasons` 枚举命名和 Agent5 的"冲突点分类"不要混用——前者是**客户触发路径**，后者是**政策冲突类型**。跨 Agent 编排归 `api_server.py` 路由层（红区），Agent4 内部绝不直接调 Agent5 模块。

---

## 附：参考文件速查

- Review 依据：`docs/review/agent4-phase-0-review.md`（Top 3 Gap + APPROVED 裁决）
- 协议基线：`docs/handoff/decisions-log.md` A-006（R-A/B/C）/ A-008~A-009（批量授权矩阵）/ A-012.D（SHA 不可变）/ A-013（pending_metrics α kernel）
- Runner framework：`evaluation/runner/base_evaluator.py` / `registry.py` / `cli.py` / `__main__.py`（红区，只读；A-013 kernel 已 patch）
- Adapter 参考：`evaluation/runner/adapters/agent6_report.py`（Phase A 模式）/ `evaluation/runner/adapters/agent4_alert.py`（Phase 0，本 Phase 1 改造）
- Onboarding 模板：`docs/onboarding/agent1-phase-1.md`（格式 + 契约形态）
- Agent4 定位：`memory/project_agent_alert_pivot.md` + `memory/project_agent_functional_boundaries.md`
- 前端规约：`docs/design/platform-shell-v1.md`（Task D 设计稿要引其色系变量）
- DoD 定义：`docs/scorecard/definition-of-done.md` v1.0 / `memory/project_bank_delivery_dod.md`
- 全局看板：`docs/scorecard/GLOBAL.md`
- CLAUDE.md 关键条：§3.1（确定性 vs 概率性）/ §5（评估框架双轨）/ §12（不黑名单兜底）
