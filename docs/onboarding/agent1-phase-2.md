# Agent1 (获客/channel) Phase 2 Onboarding

**状态**：APPROVED（主 CLI 批示）
**发布日期**：2026-04-19
**Signal 入口**：`PHASE-2-BATCH-1-APPROVED`
**前置**：`docs/proposals/agent1-phase-2-draft.md` + `docs/handoff/decisions-log.md` Q-001..Q-004

---

## 本批次裁决结果（对应 proposal 4 条候选）

### ✅ Option 4 — 批（立启，目标修正）

**原提案问题**：原稿验 `EnterpriseProfile.model_validate()` **违反 A-004 §〇**（"禁止 `shared.EnterpriseProfile` 当 handoff 载体反序列化"）。

**修正后目标**：验 handoff JSON dict 符合 `docs/contracts/enterprise_profile.md` 嵌套结构——
- 必填：`profile_id` / `company_name`
- 子结构字段类型：`FinancialAnchors` / `GuaranteeInfo` / `RelatedPartyInfo` / `ExistingCredit` / `CreditRequest` / `Chapters` / `AgentOutputs`
- 实现方式：**jsonschema 或手写字段断言**，**不走 Pydantic.validate**

**交付物**：`agent_channel/tests/test_handoff_contract.py`
**工作量**：S（半天 / 1 commit）
**分支**：`feat/agent1-productize`
**完成信号**：commit trailer `Signal: OPTION-4-DONE`

---

### 🟡 Option 2 — 批代码侧，回录侧 hold

**立启部分**：
- `evaluation/runner/adapters/agent1_channel.py` —— 仿 `adapters/agent6_report.py` 写
- 注册 `"channel"` evaluator（registry.py 已 lazy 占位）
- 确定性/启发式指标优先：
  - `source_url_reachable_rate`（domain）
  - `signal_type_diversity`（domain，每候选客户 ≥ 2 种信号类型）
- 抽样 CSV 生成器：`scripts/agent1_sampling.py`（从 baseline results 抽 Top10）
- 冒烟：`py -m evaluation.runner --agent channel --artifacts <path>`

**Hold 部分**：审贷员人工回录流程——外部依赖用户触发

**工作量**：S（可启部分）
**分支**：`feat/agent1-productize`
**完成信号**：`Signal: OPTION-2-CODE-DONE`

---

### ⏸️ Option 1 — 暂 hold（外部阻塞）

Tavily 生产 key + 合规批文是**用户侧外部依赖**，Agent1 无自主启动权限。

标记状态：`PHASE-2-BLOCKED-EXTERNAL`
触发条件：用户提供生产 key + 合规批文 → 重新下发启动信号

---

### ❌ Option 3 — 驳回（移出 Phase 2 scope）

**驳回理由**：数据飞轮第 4 环（few-shot 注入）需要**真实审贷员使用数据**才有信号。当前无真实用户量，注入等于空转。

**延迟路径**：推到有生产使用数据后重启（非 Phase 2 目标）

---

## 启动顺序

1. **Option 4（spec 修正版）** —— 立启，S 量级，半天搞定
2. **Option 2 代码侧** —— Option 4 完成后接力
3. Option 1 → 等用户外部触发
4. Option 3 → 永久驳回

---

## 边界约束（红线）

- ❌ 不碰 `shared/`（Q-004 A-004 §〇 已明确）
- ❌ 不动 `docs/contracts/`（红区，走 RFC）
- ❌ 不跨 Agent 调用（只消费 Agent1 域内产出）
- ✅ Handoff 契约验证是"消费侧"验证，不修改契约本身
- ✅ evaluation adapter 按 `agent6_report.py` 模板扩写

---

## ACK 协议

Agent1 收到本 onboarding 后：
1. 在 `feat/agent1-productize` 上 commit trailer 带 `Signal: PHASE-2-BATCH-1-ACK`
2. 开始 Option 4 实施
3. Option 4 / Option 2 每条完成独立 commit，trailer 带对应 DONE signal
4. Batch 全完成回 `READY-FOR-PHASE-2-REVIEW`

---

**维护者**：主 CLI
**下次更新触发**：Option 1 解封 OR Option 2 回录侧解封 OR Batch 2 开启
