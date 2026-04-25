# Phase 3-Final · 轨 5 · reason_codes 字典补齐 Onboarding

**状态**：Phase 3-Final GO（**主 CLI 本地代理 · 不外包 · 与 Wave 1 并行写**）
**发布日期**：2026-04-25
**Signal 入口**：N/A（主 CLI 自代理 · 无 worker ACK）
**前置**：commit `4f2132e ORCHESTRATOR-HANDOFF-PHASE-3-FINAL-PLANNED` + Q-032
**参照决策**：`docs/handoff/decisions-log.md` Q-032（Phase 3-F 8 轨规划） + `docs/handoff/session-2026-04-25-phase-3-final-handoff.md` §4.5 + `docs/scorecard/dod-current-status-2026-04-24.md` §2.3.2 L2-7/L2-8 reason_codes
**Final commit signal**：`READY-FOR-REASON-CODES-REVIEW`（subagent pre-review · 主 CLI 自审）

---

## 1. 背景与目标

L2 金融合规层有一组对标 **FCRA AAN（Fair Credit Reporting Act · Adverse Action Notice）** 的硬指标——**reason_codes**：拒贷 / 风险 / 合规违规结论必须可枚举、可解释、可固定。当前状态：

| 条 | 状态 | 缺口 |
|---|---|---|
| L2-7 Top-3~5 reason_codes | 🟡 Agent3 后端齐（agent3 branch `68985dc` · 由轨 2 带回 main） · 前端待渲染 | Agent4/5/1/2 后端 + 字典齐缺 |
| L2-8 reason_codes 字典固定可枚举 | 🔴 `docs/reason_codes/{agent}.yaml` 全部缺 · agent3 由轨 2 带 | Agent4/5（必）+ Agent1/2（可选） |
| L2-9 拒绝结论给"为什么 + 怎么改" | 🟡 后端 reason_codes 派生齐后即解 | UI 渲染待 Stage 2 / Stage 4 解 |

**本轨产物**：4 份 yaml 字典文件（Agent4 必 / Agent5 必 / Agent1 可选 / Agent2 可选），对标 FCRA AAN 的"原因 code + 描述 + 改进建议"三段式。

**硬边界**：本轨**只产** `docs/reason_codes/agent{4,5,1,2}.yaml`，**不动** 任何代码（`agent_*/` / `shared/` / `evaluation/` / `web/`）。后端 reason_codes 派生由对应 Agent 的 worker 在后续 Wave 实现，本轨只产字典 schema + 内容。

---

## 2. Task 清单

### Task A · Agent4 预警 reason_codes 字典（必）

**目标**：`docs/reason_codes/agent4_alert.yaml` · 预警拒因 Top-N 标准枚举。

**Schema**（每 entry）：
```yaml
- code: AL-EXT-001
  category: 外部信号
  trigger: 工商变更（法人/股东/经营范围）
  severity: yellow  # red / yellow / green
  description: 该客户 30 天内发生工商关键字段变更，需复核经营稳定性
  suggested_action:
    - 调取最新工商档案
    - 客户经理回访确认变更原因
    - 评估对授信结构的影响
  evidence_template: 工商变更记录截图 / 国家企业信用信息公示系统 URL
```

**最少条数**：≥ 8 条（覆盖外部信号 + 内部交易 + 双路交叉三大域）

**域分组**（参照 CLAUDE.md §3.2 Agent4 业务域）：
- 外部扫描（4 条）：工商变更 / 司法诉讼 / 经营异常 / 行政处罚
- 内部交易（3 条）：流水异动 / 大额支取 / 跨省高频
- 双路交叉（1 条）：外部 + 内部信号叠加触发

---

### Task B · Agent5 合规 reason_codes 字典（必）

**目标**：`docs/reason_codes/agent5_compliance.yaml` · 政策违规 Top-N 标准枚举。

**Schema**（每 entry）：
```yaml
- code: CO-POL-001
  category: 政策冲突
  trigger: 业务流程触碰 2026 年新规第 X 条
  severity: red
  description: 该业务流程与新政策冲突，需按新规更新
  reference_policy: 国家金融监督管理总局 2026 年 X 号文 第 Y 条
  suggested_action:
    - 暂停该业务流程
    - 修订内部 SOP
    - 提交合规委员会审议
  evidence_template: 新政策原文链接 + 内部 SOP 章节
```

**最少条数**：≥ 8 条（覆盖政策解析 + 业务矩阵 + 违规判定 + 缺陷分类四大域）

**域分组**（参照 CLAUDE.md §3.2 Agent5 业务域）：
- 政策解析冲突（3 条）：央行新规 / 银保监新规 / 行业自律新规
- 业务矩阵违规（3 条）：准入违规 / KYC 缺陷 / 风偏不一致
- 违规判定（1 条）：硬违规
- 缺陷分类（1 条）：流程缺陷

---

### Task C · Agent1 获客 reason_codes 字典（可选 · 优先级低）

**目标**：`docs/reason_codes/agent1_channel.yaml` · 获客筛选 Top-N 拒因。

**判断**：先看 Agent1 当前 lookalike 匹配评分逻辑是否已派生 reason_codes（在 `agent_channel/` grep）。
- **若已派生**：补字典文件即可，~ 5 条
- **若未派生**：本轨**不写代码**，只产 schema + 5 条占位条目，标 `pending_implementation: true`

**Schema**：参考 Agent4 / Agent5 的三段式（trigger / description / suggested_action）

---

### Task D · Agent2 风控 reason_codes 字典（可选 · 优先级低）

**目标**：`docs/reason_codes/agent2_riskctrl.yaml` · DSL 规则解释字典。

**判断**：Agent2 是 DSL 规则引擎，reason_codes 形态可能是"哪条 DSL 规则触发"而非通用 code。
- **若 batch-3 code-arch 轨已规划字典 schema**（grep `batch-3-code-arch-agent2-hardening.md`）：本轨对齐 schema 即可
- **若未规划**：留占位条目 ~ 3 条，标 `pending_dsl_alignment: true`

**Schema**：DSL 规则 ID + 触发条件 + 业务含义 + 改进建议

---

### Task E · Agent3 字典自检（已有 · 轨 2 带）

**目标**：轨 2 agent3-unfreeze 完成后（带 `68985dc feat(agent_credit): L2-7/L2-8 standard reason codes` commit），验证：
1. `agent_credit/reason_codes.yaml` 或 `docs/reason_codes/agent3_credit.yaml` 之一存在
2. 内容 ≥ 5 条标准条目（对标 FCRA AAN）
3. schema 与 Agent4/5 字典对齐（如有差异，本轨记 review note · 不强行统一）

**完成信号**：折叠进 commit body · 不单独 signal

---

## 3. 验收硬指标（T5-1 ~ T5-8 · 8 项）

| # | 指标 | 阈值 | 判定 |
|---|---|---|---|
| T5-1 | Agent4 字典落盘 | `docs/reason_codes/agent4_alert.yaml` 存在 + ≥ 8 条 + 三段式齐 | yaml.safe_load + count |
| T5-2 | Agent5 字典落盘 | `docs/reason_codes/agent5_compliance.yaml` 存在 + ≥ 8 条 | yaml.safe_load + count |
| T5-3 | Agent1 字典落盘（可选） | 有则 ≥ 5 条 · 无则 final body 写明跳过理由 | ls + body |
| T5-4 | Agent2 字典落盘（可选） | 同 T5-3 | ls + body |
| T5-5 | Agent3 字典自检 | 轨 2 合后 grep `agent3` reason_codes ≥ 5 条 | grep |
| T5-6 | FCRA AAN 对标声明 | 每份 yaml 头部含 `# 对标 FCRA AAN（Fair Credit Reporting Act · Adverse Action Notice）` 注释 | head |
| T5-7 | 红区 0 漂移 | 0 代码改动 · git diff 仅 `docs/reason_codes/` 范围 | git diff |
| T5-8 | Final commit body | 列 4 yaml 路径 + 行数 + 三段式占比 + 解 DoD L2-7/L2-8/L2-9 自检 | body grep |

---

## 4. 红线

- ❌ **不动代码**（任何 `agent_*/` / `shared/` / `evaluation/` / `web/` 改动 → 本轨 scope 外）
- ❌ **不写"实现"细节**（字典是 schema + 内容 · 不是代码）
- ❌ **不臆造 FCRA AAN 标准**（参考 https://www.consumerfinance.gov/rules-policy/regulations/1022/ 真实 AAN code 命名风格 · 但本字典是中文场景的对标 · 不直接抄）
- ❌ **不 git push**
- ✅ Schema 三段式齐：trigger / description / suggested_action（最低必须三段 · evidence_template 可选）
- ✅ Agent3 字典等轨 2 合后再校验 · 本轨不阻塞轨 2
- ✅ Agent1/Agent2 可选 · 不勉强（reason_codes 形态不匹配的可标 pending）

---

## 5. 工期

- Task A Agent4 字典 · 0.25 天
- Task B Agent5 字典 · 0.25 天
- Task C Agent1 字典（可选） · 0.15 天
- Task D Agent2 字典（可选） · 0.15 天
- Task E Agent3 自检（轨 2 后） · 0.1 天
- Final commit body · 0.1 天
- 合计 **~1 天**（主 CLI 代理 · 与 Wave 1 并行不阻塞）
