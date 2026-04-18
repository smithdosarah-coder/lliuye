# Agent3 (授信/credit) Phase 2 Onboarding

**状态**：APPROVED（主 CLI 批示）
**发布日期**：2026-04-19
**Signal 入口**：`PHASE-2-ONBOARDING`
**前置**：
- `docs/handoff/decisions-log.md` Q-004 A-004（契约语义澄清）
- Agent3 Phase 1 APPROVED（commit `c101597` Signal: A-004-ACK）
- feat/agent3-productize Phase 1 交付物完整

---

## 本批次任务（2 条并行）

### 🟢 Task A — Agent3 evaluation adapter（Phase B runner 扩展）

**目标**：仿 `evaluation/runner/adapters/agent6_report.py` 写 Agent3 专属 adapter，让评估 runner 能覆盖 Agent3 产出。

**模块路径**：
- 新建：`evaluation/runner/adapters/agent3_credit.py`
- 注册：`@register_evaluator("credit")`（registry.py 已 lazy 占位）
- 消费：`agent_credit/advisor_formatter.py` 产出的 JSON

**指标划分**：
- **确定性指标优先**（Phase 2 必出）：
  - `ratio_consistency`：授信决策中引用的财务比率 vs `financial_analyzer` 计算一致率
  - `red_line_trigger_accuracy`：红线判定准确率
  - `score_monotonicity`：相同输入相同分数（决定论验证）
- **LLM-judge 类指标**（Phase A 走 stub，Phase C 启）：
  - `reasoning_quality`
  - `advice_specificity`

**冒烟命令**：
```bash
py -m evaluation.runner --agent credit --artifacts <agent3 output json>
```

**交付路径**：
- `feat/agent3-productize` 分支
- push 到 upstream mesh
- 冒烟 JSON 落 `evaluation/results/YYYY-MM-DD/credit_<commit>.json`

**工作量**：S-M（半天到 1 天）
**完成信号**：`Signal: TASK-A-DONE`

---

### 🟡 Task B — BLE001 lint 债清理（独立 chore PR）

**目标**：`agent_credit/advisor_formatter.py` / `api.py` 10+ 条 BLE001（bare except）改成明确异常类型。

**边界**：
- ❌ 不改业务逻辑
- ❌ 不合 `feat/agent3-productize`（独立 chore 分支）
- ✅ 只做 except 类型收窄

**分支命名**：`chore/agent3-lint-cleanup`
**基分支**：`chore/l0-infra`（取主 CLI 的基建层）
**工作量**：S（半天）
**完成信号**：`Signal: TASK-B-DONE`

---

## ⏸️ 暂 hold（延后执行）

### shared/enterprise_profile.py 嵌套迁移 RFC（A-004 Phase 2 延迟项）

**暂 hold 理由**：
- 等 Agent1 handoff contract 冒烟（Option 4）跑通后再评估必要性
- 有可能 C 方案就够了，A 方案永远不启
- **当前阶段不启 RFC 评估**

**解封条件**：Agent1 Option 4 跑通 → 主 CLI 二次评审是否需要 A 方案

---

## 边界约束（红线）

- ❌ 不碰红区：`shared/` + `docs/contracts/` 零改动（任何涉及改动 → 起 RFC）
- ❌ Task A 不跨 Agent 调用（只消费 Agent3 自身产出）
- ❌ Task B 不修改业务逻辑（纯 lint 清理）
- ✅ 两条 Task 可**并行**推进（不同分支）

---

## ACK 协议

Agent3 收到本 onboarding 后：
1. `feat/agent3-productize` 上做 commit trailer `Signal: PHASE-2-ONBOARDING-ACK`
2. 开始 Task A（主路径）
3. Task B 可以作为 windowing 填充（Task A 等评估数据时切过去做）
4. 两条 Task 都完成后回 `READY-FOR-PHASE-2-REVIEW`

---

**维护者**：主 CLI
**下次更新触发**：shared Pydantic 迁移解封 OR Batch 2 开启
