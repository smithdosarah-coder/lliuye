# Decisions Log

**协议**：`docs/contracts/decision-log-protocol.md`
**使用**：append-only。子 CLI 发起 `## [Q-NNN]`，主 CLI 紧邻 append `### [A-NNN]`。
**发布**：2026-04-18

---

## [Q-001] 2026-04-18 15:30 · report(v16) · section_generator 年份前缀 regex 补丁

**CLI**: report
**Priority**: P1
**Blocking**: yes
**Related**: stash@{0} `v16-section-gen-regex-polish-park`

### 选项
- **A** 治本：stash 掉下游 regex 补丁 + 在 V16 REWRITE prompt 加硬约束禁止前置年份同比
- **B** 治标：RFC 补 regex 到 `section_generator.py`（红区变更）
- **C** 现场 RFC 扶正 B 方案

### 推荐
A —— 符合 CLAUDE.md §12"不写关键词/正则黑名单兜底幻觉"

### 上下文
LLM 输出 "2025年同比增长 14.9%" 这种前置年份格式，下游 regex 漏抓。

### [A-001] 2026-04-18 15:45 · 主 CLI

**Decision**: A
**Rationale**: 治本路径符合 CLAUDE.md §12 + §3.1 确定性/概率性计算边界；下游 regex 打补丁永远列不全变体（2025 年后还有 FY2025 / 去年 / 上年等）；骨架型 QC 88.5 非 blocker。
**Follow-up**: v16 CLI 在 REWRITE prompt 加 Rule 16，stash regex 待 Rule 16 回归确认后 drop。已落 `b1c4d13`。

---

## [Q-002] 2026-04-18 23:30 · report(v16) · Phase 1 DoD 调整（评估 runner + 对公素材）

**CLI**: report
**Priority**: P1
**Blocking**: no

### 坑 1
`evaluation/` 无 runner 实现，`agent6_report.yaml` 里的 halluc/evidence 阈值无基线数据可跑。
写 evaluator 是 0→1 建基线（~0.5-1 天），跨 Agent 有复用（Agent2 风控回测）。

### 坑 2
`customer/` 不存在，samples/ 只有模板 docx。对公 matched 真实材料需业务侧提供。

### 推荐
- 坑 1：单独 RFC 派发，不占 v16 Phase 1
- 坑 2：放宽 DoD 到骨架型 QC ≥ 75，对公推 Phase 2

### [A-002] 2026-04-18 23:40 · 主 CLI

**Decision**:
- 坑 1 → 单独 RFC `docs/contracts/rfc/20260418-evaluation-runner.md`，跨 Agent 形态（base_evaluator + per-agent adapter），不占 v16 Phase 1
- 坑 2 → 选 C（放宽 DoD 至骨架型），对公 matched 推 Phase 2 由业务方提供材料

**Rationale**: 评估 runner 是共享基础设施，让 v16 单独写会跟 Agent2 回测重复实现；对公材料不在 CC 边界。

**新 v16 Phase 1 DoD**：
- [ ] 骨架型样本 QC ≥ 75 的完整输出
- [x] prompt 治本 commit（`b1c4d13`）
- [ ] work tree clean

---

## [Q-003] 2026-04-18 23:45 · report(v16) · RESCUE-COMMIT 迁移前后续

**CLI**: report
**Priority**: P0
**Blocking**: no
**Related**: `fa01e89` `b1c4d13`

rescue commit landed on chore/l0-infra 尾部。请示：
1. 留在 chore/l0-infra OK 还是 cherry-pick 到 feat/agent6-v16？
2. demo-agent6 的 samples/ / customer/ 空，如何同步？

### [A-003] 2026-04-18 23:55 · 主 CLI

**Decision**:
1. 留在 `chore/l0-infra` ✅ 不 cherry-pick。等 `feat/tiered-search` 合并或 rebase `feat/agent6-v16` 时自然带过去。
2. samples/ 由主 CLI 的 Pre-Phase-0 assets commit 承载，落到 `chore/l0-infra` 后 `demo-agent6` pull 即可取到。`customer/` 是客户真实材料（合规不入 repo），走 .env 外部挂载。

**Rationale**: 避免分支分裂造成轨迹混乱；samples 属于主 CLI Pre-Phase-0 资产，跨 Agent 共用。
**Follow-up**: 主 CLI 跑完 §P1 5 commit 后发 migration signal 给 v16 CLI。

---
