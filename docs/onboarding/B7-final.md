# worker-B7-final · Sprint 3 (BE13 个人画像 POC · 减半)

## 你是谁

worker-B7-final · Phase B Sprint 3 · branch `feat/phase-b7-final` · worktree `D:\claude code\work-B7-final`

## 你的任务

按 `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE13 实施个人画像 POC + ledger integration verify (减半 · BE7 已被 B4-credit Sprint 2 提前 ship per Q-046)。

### BE13 个人画像 POC (0.75-1 周 · 减半)

> ⚠️ **写集修正 (per Codex Sprint 3 onboarding pre-dispatch review NEEDS-FIX)**: BE13 跑 BE12 (Agent1 `personal_insight` 子域 · 客户/候选个人画像 POC) 的 4 维度评价 · 不是 RM 业绩。

**B7 写集 (write files)**:
- `docs/runbook/be13-personal-insight-poc.md` (POC report 主输出)
- `evaluation/runner/adapters/agent1_personal_insight.py` (新 evaluation adapter · 不是 agent_riskctrl yaml)
- `evaluation/agent1_personal_insight.yaml` (新 baseline config · 4 维度 metric)

**B7 read-only verify (不改 · 仅 verify)**:
- `agent_channel/personal_insight*` (B4-channel BE12 ship 后 · 你接 payload)
- `shared/decision_ledger/` (BE7 ship · verify integration)

**4 维度评价** (per Phase B 验收硬线 #5):
1. **个人画像 35%** — Agent1 候选客户个人画像准确度 (per BE12 person_features schema)
2. **产品适配 25%** — 候选客户与推荐产品 fit 度 (per BE12 product_fit)
3. **合规 + 话术 20%** — pep / sanction / talking_points (per BE12 compliance_check + talking_points · 替代之前 "经营策略" 维度)
4. **PII + latency 20%** — pii_redacted bool + latency_ms (per BE12 性能维度)

**ledger integration verify** — 验 BE7 decision_ledger (B4-credit Sprint 2 ship) 在 BE12 个人画像决策时真上链 (含 `subject_id` PII hash · `evidence_chain` 含 BE12 payload 引)。

**POC report** 必含: 4 维度真值 (跑 evaluation runner) · ledger 上链 evidence · 可信度评分。

## 红线 (硬 · 违 = REJECT V2)

- 不破现有 BE7 decision_ledger 4 角色 retention (per CLAUDE.md §3.7.5)
- LLM 调用走 `shared/llm_caller/` · **禁止新增 `from llm import LLMClient` OR `LLMClient(...)` 直连** (per Q-052 P2.6 grep guard 修正版 · BASELINE=30 hits / 14 file at dispatch HEAD `269aba1` · DIFF guard `git diff origin/main...HEAD` 必 0 新增 · 不 touch 已知残留 14 file)
- 不动 shell / today / auth / dispatch (B5 owns) · 不动 Agent1 workspace (B4-channel owns)
- 4 维度评价确定性 · 不让 LLM 现场算 (per CLAUDE.md §3.1)
- evaluation runner baseline 不退化 (vs `evaluation/baselines/2026-05-04-sprint2-end.md`)
- 反 5 原则 §3.5 (POC 数据 · gold 不预埋 runtime · 难度分层 · 真实来源锚定 · 脱敏再造 · 环境边界)

## ⚠️ Sprint 3 关键警告 (per Q-052)

1. **依赖 B4-channel BE12 ship**: 你 Week 7-8 启 (Day 1-3 + Day 4-5 是 B5 + B4-channel + B4-riskctrl 主战) · B4-channel BE12 ship 后 (~Week 7 初) 你接 personal_insight payload + endpoint 跑评价
2. **legacy LLMClient grep guard 修正版** (per Codex Sprint 3 onboarding pre-dispatch review NEEDS-FIX): BASELINE=30 hits / 14 file at dispatch HEAD `269aba1` · 你**不 touch 已知残留 14 file** + **不增加新残留** · DIFF guard `git diff origin/main...HEAD` 必 0 新增
3. **POC 不演销售/价格 / multi-tenant 叙事** (per Q-052 #6 charter v2 #5 改验收口径): 4 维度评价是产品能力评估 · 不是商业化 demo

## DONE signal

`WORKER-B7-FINAL-BE13-POC-DONE` · trailer 必含:
- `REVIEW-MODE: codex`
- `REASONING-EFFORT: medium`
- `ELAPSED: <min>`
- `POC-4-DIMS: <画像 / 产品适配 / 经营策略 / 性能 各 dimension 得分>`
- `LEDGER-INTEGRATION-VERIFY: <yes/no · 含 evidence>`
- `GREP-GUARD-LEGACY-LLM: BASELINE=30; NEW=0` (per Q-052 P2.6 修正版)

## 工程量

BE13 减半 = **0.75-1 周** (BE7 已被 B4-credit Sprint 2 提前 ship per Q-046 · 原 charter v2 BE13 包 BE7+BE13 = 1.5-2 周 · 现 BE13 only)

## 必读文件

1. `docs/onboarding/B7-final.md` (本文)
2. `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE13 章节
3. `docs/reset/phase-b-charter.md` v2.2 段 (Sprint 3 排期 · B7 减半)
4. `docs/handoff/decisions-log.md` Q-046 (BE7 提前 ship · B7 减半) + Q-052
5. `shared/decision_ledger/` (BE7 ship · 你 verify integration)
6. `agent_channel/personal_insight*` (B4-channel BE12 ship 后 · 你接)
7. `shared/llm_caller/`
8. `evaluation/baselines/2026-05-04-sprint2-end.md`
9. CLAUDE.md §3.1 + §3.5 + §3.7.5 (decision ledger)

## 起手第一步

```bash
cd "D:/claude code/work-B7-final"
git fetch origin && git rebase origin/main  # per Q-050
# read 上面 9 文件
git commit --allow-empty -m "chore(resume): WORKER-B7-FINAL-RESUMED · 我理解 Sprint 3 BE13 减半 task

任务: BE13 个人画像 POC + 跑通 4 维度评价 (画像 35% + 产品适配 25% + 经营策略 20% + 性能 20%) + ledger integration verify
工程量: 0.75-1 周 (减半 · BE7 已 B4-credit 提前 ship per Q-046)
DONE signal: WORKER-B7-FINAL-BE13-POC-DONE
红线: 不破 BE7 ledger 4 retention · LLM 走 shared/llm_caller · 4 维度评价确定性 · 反 5 原则

Signal: WORKER-B7-FINAL-RESUMED"
```

完了等主 CLI verify · 等 B4-channel BE12 ship 后接 personal_insight 跑评价。
