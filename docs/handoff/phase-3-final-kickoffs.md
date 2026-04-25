# Phase 3-Final · 8 轨 Kickoffs

**版本**：v1.0 · 2026-04-25
**主 CLI commit**：`PHASE-3-FINAL-DISPATCHED`（dispatch 锚 · 见 git log）
**前置文档**：
- `docs/handoff/session-2026-04-25-phase-3-final-handoff.md`（PRD 级 8 轨 scope）
- `docs/handoff/decisions-log.md` Q-032（Phase 3-F 总规划 · 推翻 Q-031 档 2/3）
- `docs/scorecard/dod-current-status-2026-04-24.md`（DoD 倒推依据）
- `docs/onboarding/p3f-*.md` × 7（轨 1-7 onboarding）
- `docs/onboarding/batch-3-*.md` × 3（轨 8 复用 · 不重写）

**用户操作模型**：
1. 读本文找你要 dispatch 的 Wave
2. 找该 Wave 下的 worker 段
3. 复制对应 kickoff prompt（**整段** · 含开场指令 + 必读清单 + 红线快报 + ACK signal）
4. 粘到该 worker 的 CLI 窗口
5. Worker 自动 resume + ACK · 然后等 worker emit Final Signal · 主 CLI 自动 patrol 5min /loop 扫到 → subagent pre-review → APPROVE / REJECT-V2

---

## §0. 8 轨 + Wave 拓扑

| 轨 | 内容 | onboarding | Wave | worker / 主 CLI 代理 | Final Signal |
|---|---|---|---|---|---|
| 1 | agent6 解冻 + rebase + merge | `p3f-agent6-unfreeze.md` | **Wave 1** | worker（用现有 demo-agent6） | READY-FOR-AGENT6-UNFREEZE-REVIEW |
| 2 | agent3 解冻 + rebase + merge | `p3f-agent3-unfreeze.md` | **Wave 1** | worker（用现有 demo-agent3） | READY-FOR-AGENT3-UNFREEZE-REVIEW |
| 3 | agent1 cherry-pick | `p3f-agent1-cherry.md` | **Wave 1** | worker（**新 worktree** code-agent1-cherry） | READY-FOR-AGENT1-CHERRY-PICK-REVIEW |
| 8a | Agent2 data-foundation | `batch-3-data-foundation-agent2-samples.md` | **Wave 1** | worker（**新 worktree** data-agent2-foundation） | READY-FOR-DATA-FOUNDATION-AGENT2-REVIEW |
| 5 | reason_codes 字典 | `p3f-reason-codes.md` | 与 Wave 1 并行 | **主 CLI 代理** | READY-FOR-REASON-CODES-REVIEW |
| 7 | 合规文档 + 模型卡 + Agent1 SignalTimeline | `p3f-docs-compliance.md` | 与 Wave 1 并行 | **主 CLI 代理** | READY-FOR-DOCS-COMPLIANCE-REVIEW |
| 4 | 7 frozen branch 整合 | `p3f-frontend-integration.md` | **Wave 2**（等 Wave 1 三轨合）| worker（新 worktree code-frontend-integration · Codex 辅助）| READY-FOR-FRONTEND-INTEGRATION-REVIEW |
| 8b | Agent2 code-arch | `batch-3-code-arch-agent2-hardening.md` | **Wave 2**（等 Wave 1 8a 数据出）| worker（新 worktree code-agent2-hardening）| READY-FOR-CODE-ARCH-AGENT2-REVIEW |
| 8c | Agent2 evaluation 真 baseline | `batch-3-evaluation-agent2-metrics.md` | **Wave 3**（等 Wave 2 8b 合）| worker（新 worktree eval-agent2）| READY-FOR-EVALUATION-AGENT2-REVIEW |
| 6 | L3 POC 证据链 | `p3f-poc-evidence.md` | **Wave 3**（等 Wave 2 4 合）| worker（新 worktree code-poc-evidence）| READY-FOR-POC-EVIDENCE-REVIEW |

**Wave 1 = 4 个外包 kickoff（本批次粘）** + 主 CLI 并行干轨 5/7
**Wave 2 = 2 个外包 kickoff** + 收 Wave 1 review
**Wave 3 = 2 个外包 kickoff** + 收 Wave 2 review

---

## §1. 万能 Worker 开场指令（所有 worker 通用）

每段 kickoff 第一句必复制以下万能指令（已嵌入各 worker 段）：

> **读 `AGENT_IDENTITY.md` 和里面列的所有文件，resume 状态后等我指令。**

worker CLI 收到后会自动跑 `resume-agent` skill · 读 worktree 本地 AGENT_IDENTITY.md → 顺着 identity 拉 onboarding / decisions-log / contract / 最近 signal → 汇报状态 → 等 ACK 指令。

**用户视角**：粘完整 kickoff block 后，worker 会先 resume 然后 ACK。等 ACK 出现再让它正式开干（一般直接说"按 onboarding 干"或"go"即可）。

---

### §1.1 ⚠️ Askout 红线（2026-04-25 加 · Q-035 教训）

任何 worker 遇到 blocker / spec gap / red-line conflict / 等裁决 · **必走 commit trailer · 禁止 chat 输出**：

```
git commit -m "ask(<worker>): <主题>" -m "<background + data + 候选方案 + 推荐>" \
  --trailer "Signal: Q-NNN-RAISED"
```

详见 `docs/process/worker-askout-protocol.md`（含 commit body 模板 + 编号约定 + main CLI 响应周转）。

**反例**：agent6 worker 在 chat 输出 "Q-033 candidate" + 等用户截图转发主 CLI · 60min+ 阻塞 · main CLI patrol 看不见。

**正例**：worker `git commit ... --trailer "Signal: Q-035-RAISED"` · main CLI patrol ≤ 5min 内 surface · 立即裁决。

---

## §2. Wave 1 Kickoffs（4 个 · 现在粘）

### §2.1 · 轨 1 · agent6-unfreeze 

**用 worktree**：`D:/claude code/demo-agent6`（现有 · 用户重开窗口即可 · 无需新建）
**Branch**：`feat/agent6-v16`（现状 · rebase 到 chore/l0-infra）
**预计工期**：2-3 天 + 允许 REJECT-V2 一轮

**==== 复制以下整段粘到 demo-agent6 worker 窗口 ====**

```
读 AGENT_IDENTITY.md 和里面列的所有文件，resume 状态后等我指令。

你的本任 dispatch 是 Phase 3-Final 轨 1 · agent6 解冻 + rebase + 合流。

强制必读（onboarding 已落盘）：
- docs/onboarding/p3f-agent6-unfreeze.md（本任 scope · Task A-D · 验收 12 项 · 红线 6 条）
- docs/handoff/session-2026-04-25-phase-3-final-handoff.md §2.1 + §4.1（20 commit 价值归类 + rebase 风险）
- docs/handoff/decisions-log.md Q-032（Phase 3-F 推翻 Q-031 冻结 · 激活本 branch）
- docs/scorecard/dod-current-status-2026-04-24.md（解 DoD 6 条目：L2-12/13/14 + L3-8/11/12）

关键纪律：
- ❌ 红区禁动：financial_analyzer.py / quality_scorer.py / truth_fill.py（任何 import 错误也算违规）
- ❌ rebase 冲突 > 4 文件 → 立即 Q-033 askout · 不硬解
- ❌ v16 跑分漂移 > 1% → 立即 git rebase --abort · 报告漂移 + 怀疑 commit
- ❌ 不在原 demo-agent6 worktree 之外开新 worktree（git 不允许同 branch 双 worktree）
- ❌ 不 git push
- ✅ rebase tip 已备份在 docs/handoff/agent6-pre-rebase-tip.txt（4bf8361）· 失败一行回滚
- ✅ 4 段 signal trailer：AGENT6-REBASE-CLEAN → AGENT6-V16-REGRESSION-OK → AGENT6-PYTEST-GREEN → READY-FOR-AGENT6-UNFREEZE-REVIEW
- ✅ Final commit body 含：20 commit SHA 分组 + diff --name-only + 解 DoD 6 项自检 + 红区 0 漂移声明 + v16 跑分对比

ACK 第一个 trailer：Signal: AGENT6-UNFREEZE-ACK
ACK 后等我说 "按 onboarding 干" 再正式 rebase。
```

---

### §2.2 · 轨 2 · agent3-unfreeze

**用 worktree**：`D:/claude code/demo-agent3`（现有 · 用户重开窗口即可）
**Branch**：`feat/agent3-productize`
**预计工期**：1-2 天

**==== 复制以下整段粘到 demo-agent3 worker 窗口 ====**

```
读 AGENT_IDENTITY.md 和里面列的所有文件，resume 状态后等我指令。

你的本任 dispatch 是 Phase 3-Final 轨 2 · agent3 解冻 + rebase + 合流。

强制必读：
- docs/onboarding/p3f-agent3-unfreeze.md（本任 scope · Task A-D · 验收 12 项）
- docs/handoff/session-2026-04-25-phase-3-final-handoff.md §2.2 + §4.2（11 commit 价值归类）
- docs/handoff/decisions-log.md Q-032
- docs/scorecard/dod-current-status-2026-04-24.md（解 DoD 5 条目：L2-7/L2-8 + L1-3/L1-4 + L1-11）

关键纪律：
- ❌ 红区禁动：financial_analyzer.py / quality_scorer.py / truth_fill.py
- ❌ 不覆盖 Batch 2 evaluation：agent3 branch 的 14a4a34 / d221115 优先 git checkout --ours（保 chore/l0-infra 版本）
- ❌ Batch 1 code-urgent 的 financial_analyzer 注入必须保留（在 scoring_model_corporate.py + advisor_formatter.py）
- ❌ rebase 冲突 > 4 文件 → Q-033 askout
- ❌ 不在原 demo-agent3 worktree 之外开新 worktree
- ❌ 不 git push · 不 squash commit（保 11 commit SHA 串行）
- ✅ rebase tip 已备份在 docs/handoff/agent3-pre-rebase-tip.txt（6c5820a）· 失败一行回滚
- ✅ Signal trailer 链：AGENT3-UNFREEZE-ACK → AGENT3-REBASE-CLEAN → READY-FOR-AGENT3-UNFREEZE-REVIEW
- ✅ Final commit body 含：11 commit 新旧 SHA 对照 + diff --name-only + 解 DoD 5 项自检 + Batch 1 注入保留自检

ACK 第一个 trailer：Signal: AGENT3-UNFREEZE-ACK
ACK 后等我说 "按 onboarding 干" 再正式 rebase。
```

---

### §2.3 · 轨 3 · agent1-cherry

**用 worktree**：`D:/claude code/code-agent1-cherry`（**新建** · 主 CLI 已 git worktree add · 用户开新窗口）
**Branch**：`feat/agent1-cherry-pick`（fork chore/l0-infra · 新分支）
**预计工期**：0.5-1 天

**==== 复制以下整段粘到 code-agent1-cherry worker 窗口 ====**

```
读 AGENT_IDENTITY.md 和里面列的所有文件，resume 状态后等我指令。

你的本任 dispatch 是 Phase 3-Final 轨 3 · agent1 cherry-pick（**不整体 rebase** · 30 commit 大部分过期 · 只 cherry-pick 3-5 条价值的）。

强制必读：
- docs/onboarding/p3f-agent1-cherry.md（本任 scope · Task A-E · 验收 8 项）
- docs/handoff/session-2026-04-25-phase-3-final-handoff.md §2.3 + §4.3（30 commit 归类 · 1 极高 + 4 中价值）
- docs/handoff/decisions-log.md Q-032
- docs/scorecard/dod-current-status-2026-04-24.md（解 DoD 3 条目：L3-8 + L1-4 + L1-11）

关键纪律：
- ❌ 不整体 rebase agent1 branch（30 commit 大部分过期 · 必 pick 3 + 选 0-2）
- ❌ 红区禁动：financial_analyzer.py / quality_scorer.py / truth_fill.py / web/src/lib/store/*
- ❌ 不动其他 5 Agent 代码（Agent2/3/4/5/6 各专轨 · 本轨只 Agent1）
- ❌ 不 git push · 不删 / 不 amend f950b40 / 4f2132e / d84619f / 1aef58d / 0a531dd / 4f2132e 既有 commit
- ✅ 必 pick 3 条：c408b3a 飞轮 / dc4c148 export_xlsx / 0b6eca4 handoff button + UI
- ✅ 选择性 pick：f3bd9b5 信号多样性 + f430e7f data classification（先读 diff 判断是否被 Batch 2 code-arch / 轨 1 agent6 覆盖）
- ✅ Signal trailer：AGENT1-CHERRY-PICK-START → 3 个 cherry-pick commit → READY-FOR-AGENT1-CHERRY-PICK-REVIEW
- ✅ Final commit body 含：3 必 pick SHA + 选择性 pick 决策（PICK/SKIP + 1 句理由）+ 显式 SKIP 列表（≥ 13 条）+ pytest 全绿 + 解 DoD 3 项

ACK 第一个 trailer：Signal: AGENT1-CHERRY-PICK-ACK
ACK 后等我说 "按 onboarding 干" 再正式 cherry-pick。
```

---

### §2.4 · 轨 8a · Agent2 data-foundation

**用 worktree**：`D:/claude code/data-agent2-foundation`（**新建** · 主 CLI 已 git worktree add · 用户开新窗口）
**Branch**：`feat/data-agent2-foundation`（新分支 · fork chore/l0-infra）
**预计工期**：2.5 天

**==== 复制以下整段粘到 data-agent2-foundation worker 窗口 ====**

```
读 AGENT_IDENTITY.md 和里面列的所有文件，resume 状态后等我指令。

你的本任 dispatch 是 Phase 3-Final 轨 8a · Agent2 风控历史贷款样本 CSV 产数据底座。
（原 Batch 3 设计 · Q-032 升级为 P3F 轨 8a · onboarding 内容不变 · 仅 commit message 带 P3F 标签）

强制必读：
- docs/onboarding/batch-3-data-foundation-agent2-samples.md（本任 scope · Task A-X · 反 5 原则 + 环境边界硬线）
- CLAUDE.md §3.5（反结果导向 5 原则 · 形态硬线 · 绝不含答案字段）
- docs/handoff/decisions-log.md Q-028（反 5 原则触发场景）+ Q-029（测试豁免）+ Q-032（P3F 总规划）
- docs/scorecard/dod-current-status-2026-04-24.md（Agent2 5 pending 指标背景）

关键纪律：
- ❌ 不动 agent_riskctrl/ / shared/ / evaluation/ / web/（代码硬化是轨 8b 范围）
- ❌ 不产 labels.json / optimal_dsl.yaml / difficulty_tags 任何答案字段（反 5 原则第 1 条 · Q-028 触发过 REJECT-V2）
- ❌ 不抄真实存续企业数据（脱敏再造 · 第 4 条原则）
- ❌ mock 形态必须真实（单表 CSV 5000-10000 行 · 12-36 字段 · 结果列只能是 days_past_due）
- ❌ 不 git push
- ✅ 反 5 原则全守：盲测 · 难度分层 60/20/20 · 真实来源锚定 A 股年报 / 央行模板 · 脱敏再造 · 环境边界（Agent2 全内部建模 · 外部不 mock）
- ✅ 字段字典 md 1 份 + README.md（不含答案字段）
- ✅ Signal trailer：DATA-FOUNDATION-AGENT2-ACK → AGENT2-CSV-DRAFT-DONE → AGENT2-FIELD-DICT-DONE → READY-FOR-DATA-FOUNDATION-AGENT2-REVIEW
- ✅ commit message 带 P3F 标签（不是 BATCH-3）· trailer 用 P3F-* 系列

ACK 第一个 trailer：Signal: DATA-FOUNDATION-AGENT2-ACK
ACK 后等我说 "按 onboarding 干" 再正式产数据。
```

---

## §3. Wave 2 Kickoffs（**等 Wave 1 三轨合流后再粘 · 现在不动**）

### §3.1 · 轨 4 · frontend-integration

**用 worktree**：`D:/claude code/code-frontend-integration`（**新建 · Wave 2 dispatch 时由主 CLI 创建**）
**Branch**：`feat/frontend-integration`（新分支 · fork chore/l0-infra · 含 Wave 1 三轨已合流的 tip）
**预计工期**：7-8 天 + 允许 REJECT-V2 一轮

**Wave 1 完成条件**：轨 1 / 轨 2 / 轨 3 全 APPROVED merged 到 chore/l0-infra（带 agent6 + agent3 + agent1 cherry-pick 三方资产）。

**前置主 CLI 操作**：
1. 三轨 merge 完
2. `git worktree add ../code-frontend-integration -b feat/frontend-integration chore/l0-infra`
3. 写新 worktree 的 AGENT_IDENTITY.md（指向 p3f-frontend-integration.md + handoff §3 + §4.4）
4. mesh.json 加 entry
5. 通知用户开新窗口 + 粘 §3.1 kickoff

**==== 此 kickoff 等 Wave 1 完后启用 · 不要现在粘 ====**

```
读 AGENT_IDENTITY.md 和里面列的所有文件，resume 状态后等我指令。

你的本任 dispatch 是 Phase 3-Final 轨 4 · 7 frozen branch 融合（Stage 1-5）+ 严格保 Batch 2 EvidenceTrail。

强制必读：
- docs/onboarding/p3f-frontend-integration.md（本任 scope · Stage 1-5 · 验收 15 项）
- CLAUDE.md §7（platform shell v2 spec · 4 view canon vs legacy / 4 主题 / 6 functional color / Float-badge SVG / 字体栈 / 圆角 / 动画 token / Desk hover<22px）
- docs/design/platform-shell-v2.md（spec 详写）
- design_mockups/rm-assistant-final-2026-04-19.html（视觉 1:1 复刻源 · sha256 25155e74...）
- docs/handoff/session-2026-04-25-phase-3-final-handoff.md §3（7 branch 详 + Stage 顺序 + EvidenceTrail 兼容策略）
- docs/handoff/decisions-log.md Q-031 / Q-032

关键纪律：
- ❌ legacy 顶层 6 页 0 改动（chore route 收敛是单独 task）
- ❌ 后端 0 改动（agent_*/ / shared/ / api_server.py / v16_*.py / evaluation/）
- ❌ 红区 0 改动（financial_analyzer.py / quality_scorer.py / truth_fill.py / web/src/lib/store/* 仅 panel-layout-store.clearAgent 扩展）
- ❌ Letterpress / crimson / 老 tokens（--color-brass / --color-ink / ink-brush-hr）一律 REJECT
- ❌ Stage 顺序硬性：1 → 2 → 3 → 4 → 5 · 每 stage 编译闸门通过才进下一 stage
- ❌ Batch 2 EvidenceTrail 挂载点丢失立即 REJECT-V2
- ❌ 不 git push · 不删既有 spec
- ✅ Codex 辅助大批量 tsx 改动 · 决策走 Claude 主力
- ✅ 每 stage 独立 commit · 单行 trailer · 5 stage signal + READY = 6 段
- ✅ Final body 含：7 branch 处理结果 + 5 stage SHA + 32 张截屏路径 + 解 DoD + 红区漂移自检

ACK 第一个 trailer：Signal: FRONTEND-INTEGRATION-ACK
ACK 后等我说 "按 onboarding 干" 再正式 Stage 1。
```

---

### §3.2 · 轨 8b · Agent2 code-arch

**用 worktree**：`D:/claude code/code-agent2-hardening`（**新建 · Wave 2 dispatch 时主 CLI 创建**）
**Branch**：`feat/agent2-hardening`
**预计工期**：3 天

**Wave 1 完成条件**：轨 8a data-foundation APPROVED merged（Agent2 mock CSV 落地）+ 轨 1 agent6 / 轨 2 agent3 完成（red zone 释放）。

**==== 此 kickoff 等 Wave 1 完后启用 · 不要现在粘 ====**

```
读 AGENT_IDENTITY.md 和里面列的所有文件，resume 状态后等我指令。

你的本任 dispatch 是 Phase 3-Final 轨 8b · Agent2 adapter 探针 + baseline_ruleset 对照组 + LLM-judge 实装。
（原 Batch 3 设计 · Q-032 升级为 P3F 轨 8b）

强制必读：
- docs/onboarding/batch-3-code-arch-agent2-hardening.md（本任 scope · Task A-D · adapter 探针 / baseline / judge）
- docs/handoff/decisions-log.md Q-024（evaluation 路径规范）+ Q-032
- docs/onboarding/batch-3-data-foundation-agent2-samples.md（轨 8a 产物 ref · 你消费它）

关键纪律：
- ❌ 不动 financial_analyzer.py / quality_scorer.py / truth_fill.py / web/ / v16_*.py / data/mock/ / evaluation/runner/{base_evaluator,cli}.py（A-024 路径规范）
- ❌ 不重写 Agent2 引擎（agent_riskctrl/ 1283 行 production 骨架已在 · 只补探针 + 对照组 + judge）
- ❌ 不 git push
- ✅ Signal trailer：CODE-ARCH-AGENT2-ACK → AGENT2-ADAPTER-PROBES-DONE → AGENT2-BASELINE-RULESET-DONE → AGENT2-LLM-JUDGE-DONE → READY-FOR-CODE-ARCH-AGENT2-REVIEW
- ✅ commit message 带 P3F 标签

ACK 第一个 trailer：Signal: CODE-ARCH-AGENT2-ACK
```

---

## §4. Wave 3 Kickoffs（**等 Wave 2 合流后再粘 · 现在不动**）

### §4.1 · 轨 6 · poc-evidence

**用 worktree**：`D:/claude code/code-poc-evidence`（**新建 · Wave 3 dispatch**）
**Branch**：`feat/poc-evidence`
**预计工期**：2-3 天

**Wave 2 完成条件**：轨 4 frontend-integration APPROVED merged（前端齐才能跑 E2E）。

**==== 等 Wave 2 完后启用 ====**

```
读 AGENT_IDENTITY.md 和里面列的所有文件，resume 状态后等我指令。

你的本任 dispatch 是 Phase 3-Final 轨 6 · L3 POC 证据链（Playwright E2E×3 + 9 张截屏 + P95 load test + 4 份 ops 文档）。

强制必读：
- docs/onboarding/p3f-poc-evidence.md（本任 scope · Task A-E · 验收 12 项）
- docs/handoff/session-2026-04-25-phase-3-final-handoff.md §4.6
- docs/scorecard/dod-current-status-2026-04-24.md §2.4 L3 + §2.1 L0-12/L0-13

关键纪律：
- ❌ 不动业务代码（agent_*/ / shared/ / web/src/）· bug 走 Q-NNN askout
- ❌ 不动红区
- ❌ 不依赖真 LLM key（Tavily / DeepSeek 缺时仍跑 · 走 mock）
- ❌ 不并发压测（单线程顺序采样）
- ❌ 不 git push
- ✅ 用 webapp-testing skill 跑 Playwright
- ✅ 截屏 ≥ 1440×900 全屏
- ✅ ops md 双平台命令（bash + cmd）
- ✅ Signal trailer 5 段：POC-EVIDENCE-ACK → E2E-3-PATHS-DONE → SCREENSHOT-3-PATHS-DONE → P95-LOAD-TEST-DONE → OPS-DOCS-DONE → READY-FOR-POC-EVIDENCE-REVIEW

ACK 第一个 trailer：Signal: POC-EVIDENCE-ACK
```

---

### §4.2 · 轨 8c · Agent2 evaluation

**用 worktree**：`D:/claude code/eval-agent2`（**新建 · Wave 3 dispatch**）
**Branch**：`feat/eval-agent2`
**预计工期**：2 天

**Wave 2 完成条件**：轨 8b code-arch APPROVED merged（adapter 探针 + baseline 已实装）。

**==== 等 Wave 2 完后启用 ====**

```
读 AGENT_IDENTITY.md 和里面列的所有文件，resume 状态后等我指令。

你的本任 dispatch 是 Phase 3-Final 轨 8c · Agent2 5 pending 指标跑真 baseline + rubric 精修 + 6 Agent 总览。
（原 Batch 3 设计 · Q-032 升级为 P3F 轨 8c）

强制必读：
- docs/onboarding/batch-3-evaluation-agent2-metrics.md（本任 scope · Task A-D）
- docs/handoff/decisions-log.md Q-024（evaluation 路径）+ Q-025（rubric schema）+ Q-032
- evaluation/baselines/2026-04-26-real-run.md（Batch 2 baseline 现状）

关键纪律：
- ❌ 不动 agent_*/ / shared/ / data/mock/ / web/ / v16_*.py / evaluation/runner/{base_evaluator,cli}.py
- ❌ 不臆造数值（5 pending 跑真 · 不行就标 pending 不写虚高）
- ❌ 不 git push
- ✅ Signal trailer：EVALUATION-AGENT2-ACK → AGENT2-REAL-BASELINE-DONE → AGENT2-RUBRIC-REFINE-DONE → READY-FOR-EVALUATION-AGENT2-REVIEW

ACK 第一个 trailer：Signal: EVALUATION-AGENT2-ACK
```

---

## §5. 主 CLI 本地代理（与 Wave 1 并行 · 不开新窗口）

### §5.1 · 轨 5 · reason_codes 字典

**onboarding**：`docs/onboarding/p3f-reason-codes.md`
**主 CLI scope**：4 yaml 落 docs/reason_codes/agent{4,5,1,2}.yaml + Agent3 字典等轨 2 合后自检
**最终 commit signal**：`READY-FOR-REASON-CODES-REVIEW`
**工期**：~1 天 · 与 Wave 1 并行 · 不阻塞

### §5.2 · 轨 7 · 合规文档 + 模型卡 + Agent1 SignalTimeline

**onboarding**：`docs/onboarding/p3f-docs-compliance.md`
**主 CLI scope**：L2-15 doc + 5 模型卡 + 5 演示脚本 + Agent1 SignalTimeline UI（如 7 branch 不含）
**最终 commit signal**：`READY-FOR-DOCS-COMPLIANCE-REVIEW`
**工期**：2-3 天 · Task A 等轨 1 合后启 · Task B/C/D 立即可启

---

## §6. 用户 dispatch 操作手册

### §6.1 · Wave 1 dispatch 步骤

1. **打开 4 个 CLI 窗口**：
   - 窗口 1：`cd D:/claude code/demo-agent6` + 启 claude（用 `start_claude.bat` 或手开）
   - 窗口 2：`cd D:/claude code/demo-agent3` + 启 claude
   - 窗口 3：`cd D:/claude code/code-agent1-cherry` + 启 claude（**新 worktree** · 主 CLI 已建）
   - 窗口 4：`cd D:/claude code/data-agent2-foundation` + 启 claude（**新 worktree** · 主 CLI 已建）
2. **粘 kickoff**：在每个窗口分别复制本文 §2.1 / §2.2 / §2.3 / §2.4 整段
3. **等 ACK**：每个 worker resume 后会 commit `Signal: <NAME>-ACK`（主 CLI patrol 5min /loop 自动扫到 · 提示主 CLI 检查）
4. **批 GO**：主 CLI 检查 ACK 后告诉用户哪些 worker 可以开干 · 用户回 worker 窗口说"按 onboarding 干"
5. **等 Final Signal**：worker 工期完后 commit `Signal: READY-FOR-<X>-REVIEW` · 主 CLI 起 subagent pre-review · APPROVE 后 merge / REJECT-V2 返工

### §6.2 · 主 CLI 与 worker 通信纪律

- ACK 走 commit trailer · 不走 chat（CLAUDE.md 信号纪律）
- 主 CLI 决策走 decisions-log + signal commit · 不绕路
- worker blocker → Q-NNN-RAISED commit · 主 CLI 写 A-NNN-RESOLVED commit · 不口头
- 红区改动必走 RFC（worker raise RFC-<topic>-RAISED · 主 CLI 决 + commit A-NNN-RESOLVED）

### §6.3 · 主 CLI patrol

主 CLI 在 dispatch commit 后 fire `multi-cli-mesh §7 /loop 5min` 一次性 patrol。每 5min 扫 mesh-status.json + git log -20 · 仅当下列任一新出现时主 CLI 主动 surface：
- READY-FOR-<X>-REVIEW signal
- Q-NNN-RAISED
- RFC-<topic>-RAISED
- stuck_event 触发

无新事件保持沉默。停 patrol：用户说 `/loop kill`。

---

## §7. 进度跟踪（实时）

| Wave | 轨 | 状态 | 最近 Signal | 备注 |
|---|---|---|---|---|
| 1 | 1 agent6 | 🔵 待 dispatch | - | 用 demo-agent6 现窗口 |
| 1 | 2 agent3 | 🔵 待 dispatch | - | 用 demo-agent3 现窗口 |
| 1 | 3 agent1-cherry | 🔵 待 dispatch | - | 新 worktree code-agent1-cherry |
| 1 | 8a data-foundation | 🔵 待 dispatch | - | 新 worktree data-agent2-foundation |
| 1 | 5 reason_codes | 🟢 主 CLI 进行中 | - | 与 Wave 1 并行 |
| 1 | 7 docs-compliance | 🟢 主 CLI 进行中 | - | 与 Wave 1 并行 |
| 2 | 4 frontend-integration | ⚪ 等 Wave 1 合 | - | 等 1/2/3 merged |
| 2 | 8b code-arch | ⚪ 等 Wave 1 合 | - | 等 8a merged + 1/2 merged |
| 3 | 6 poc-evidence | ⚪ 等 Wave 2 合 | - | 等 4 merged |
| 3 | 8c evaluation | ⚪ 等 Wave 2 合 | - | 等 8b merged |

---

## §8. END-OF-PHASE 标记

Phase 3-F 最终完结预期 commit：`Signal: PHASE-3-FINAL-COMPLETED-DOD-85`（按 Q-032 锁）· DoD 实测 L3 ≥ 85% / L2 ≥ 95% / L1 ≥ 90% / L0 ≥ 90% 时 close。
