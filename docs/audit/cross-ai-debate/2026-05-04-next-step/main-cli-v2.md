# Main CLI Round 2 · v2 · "下一步 1-3 周 plan" · Cross-Critique

> 作者: 主 CLI Claude Opus 4.7 · 2026-05-04 · 看完 main-cli-v1 + codex-v1 后写
> Schema: 改 / 坚持 / 对方弱点 / 吸收对方 / v2 final (per codex-mesh-protocol §4.1)
> Round 1 v1 双方独立 · Round 2 我看 codex v1 + 自己 v1 写 v2 · Codex 也并行写 R2 v2

---

## 1. R1 双方共识 (v2 不动)

| # | 共识项 |
|---|---|
| 1 | Sprint 2 三 worker 照原计划启 (B4-alert + B4-compliance + B2 · 不动 B3) |
| 2 | Q-046 5 跑偏 root cause 硬规守住 |
| 3 | Q-047 视觉冻结守住 · 不动 B3 · 任何视觉变更 PM 显式 unfreeze |
| 4 | cron 5 min 巡逻 · 扫 3 worker branch · state-snapshot 每 tick 写 |
| 5 | 不主动加 Sprint 3 worker · 不接 BE7 提前的 worker-B7 |
| 6 | Sprint 3 prep · BE7 提前 · worker-B7 减半 (BE13 POC glue · 0.75-1 周) |
| 7 | sprint-end tag (`phase-b-sprint2-end-YYYY-MM-DD`) |
| 8 | reasoning effort medium default · sequential bg · 90 min monitor fallback manual (Q-043 v2) |

---

## 2. 改 (我 v1 的错 / 不够好 · R2 改)

### 改 #1 · Observability gate 时机错了

- **我 v1**: 留 Sprint 4 整合时做 (Sprint 2 worker 已要求 baseline 跑 · 够 first-line)
- **Codex v1**: Week 1 内做 · `docs/runbook/phase-b-observability-gate.md` · 记 feedback jsonl 写入 + baseline run + ledger persisted ratio + silent-fail count
- **Codex 论点 (强)**: "BE2 graph、BE3 material gap、BE7 ledger、BE10 feedback 如果不可观测 · demo 只能'能跑' · 不能证明'可审计、可复盘、可持续改进'"
- **我 R2 改**: 接受 Codex 的 timing。理由: banking demo 客户审贷员 / 合规官就是要看 audit trail · 没 observability gate · ledger silent-fail (`shared/decision_ledger/store.py:124-201` 的 `persisted=false` 路径) 可能掩盖审计断链。Sprint 2 worker baseline 是 per-worker first-line · observability gate 是 cross-Sprint-1 全 4 worker (B1+B4-credit+B4-report) 的 second-line · 不冲突 · 都做。

### 改 #2 · Sprint 1 后端 post-DONE review 粒度

- **我 v1**: 集成 1 次 periodic audit (Q1 question · 4 worker 一起 · cost 1 fire bg)
- **Codex v1**: sequential 3 次 (B1 + B4-credit + B4-report) · D1-D4 · 不阻塞 Sprint 2 启动 · 重点查 file:line:
  - B4-credit BE2 graph wrapper `agent_credit/decision_engine.py:130-157`
  - B4-credit BE7 ledger wrapper `agent_credit/decision_engine.py:159-196`
  - B4-report SSE audit/key fail-fast `agent_report/api.py:604-658`
- **我 R2 改**: 折中接受 Codex 但加 cost 控制。Sequential 3 次 review 比 1 次 periodic 更聚焦 · file:line specificity 高 · review verdict trailer 三份独立。但 cost 3x · 加 medium reasoning + 30 min budget per review 控制 (3 × 30 min = 1.5h wall-clock 而非 3×90)。
- B3 视觉撤了不需 review (Codex 也同意 · 4 worker 中只 review 3)。

### 改 #3 · B2 doc-only 4 份具体清单缺失

- **我 v1**: 只说 "B2 BE11 商业化 doc only" · 没列具体 4 份
- **Codex v1**: 列 4 docs 引 `docs/onboarding/B2-biz.md:12-31` (pricing / multi-tenant / trial-flow / sales-playbook)
- **我 R2 改**: 验证后吸收。`docs/onboarding/B2-biz.md` :12-31 真有 4 份具体 spec (pricing-assumptions / multi-tenant-assumptions / trial-flow-assumptions / sales-playbook-v1) · `:33-39` 红线 "绝不动代码 · 只写 docs/biz/*.md · 不实装 multi-tenant 数据模型"。我 v1 漏了 spot-check onboarding · 改之。

### 改 #4 · Phase A 复核 file:line 不够具体

- **我 v1**: #2 `docs/audit/phase-a-status-2026-05-04.md` 8 项逐条 yes/partial/no
- **Codex v1**: 给具体 file:line:
  - #5: `rg "--color-brass|--color-ink|letterpress|ink-brush-hr" web/src` 0 命中
  - #6: `docs/contracts/agent-handoff-schemas.md:1-18` (验证 v1.1 真存在 · 64KB)
  - #7: `docs/prd/master-2026-04-29.md:1-6` (验证 status 🟡 v1 draft · pending PM ratification)
- **我 R2 改**: 加具体 file:line + grep 命令。我 v1 漏了 spot-check `docs/prd/master-2026-04-29.md` 状态 (它真存在 · 但 pending PM ratification · 这是 #7 partial 而非 done)。

### 改 #5 · Sprint 3 减半时间分配论点不够

- **我 v1**: 风险 #2 提了减半 1-1.5w 应该用来补 #6 handoff schema (但 #6 未必 partial · 待 audit verdict 决定)
- **Codex v1**: 没明确减半时间分配 · 只说 "BE13 POC glue · 0.75-1 周"
- **我 R2 改**: 接受 audit-driven 决定 · 不预设。R2 final: Sprint 3 减半时间分配规则 = Phase A 复核 (改 #4) verdict 决定:
  - 若 #6 handoff schema 在 v1.1 已完整 (`docs/contracts/agent-handoff-schemas.md` 64KB 看起来够) · 减半时间留作 buffer 或 enabler 工作
  - 若 #6 实际 partial (字段不全 / fixture 缺) · 减半时间补
  - 若 #7 PRD master pending PM ratification · 减半时间不补 (那是 PM 拍板事 · 不是 worker 工作)

---

## 3. 坚持 (我 v1 对的 · R2 坚持)

### 坚持 #1 · 三 onboarding trailer update (codex 已恢复 · `REVIEW-MODE: manual` → `codex`)

Codex v1 漏了这件 0 cost / 30 min 的 hygiene。三 onboarding (`B4-alert.md:36-39` + `B4-compliance.md:36-39` + `B2-biz.md:46-49`) trailer 当前写 `REVIEW-MODE: manual (codex 用尽 until 2026-05-08 · 主 CLI 自接 review)` · 现 codex 已恢复 (本 R1 R2 就是证据 · 2026-05-04 medium PONG OK 4 秒) · 不改 trailer · worker DONE 后会按 manual 走 · 浪费 codex post-DONE peer review 双闸能力。**坚持改**。

### 坚持 #2 · Phase A #6 handoff schema 是 RM 工作台 demo 闭环前提的 critical path 反推

我 v1 §8 Critical path 反推: Sprint 5 demo 4 维 → 1-3 周 → "RM 工作台 1 客户全流程跑通" 依赖 Agent6→Agent3→Agent4→Agent5 真串 → 依赖 Phase A 8 硬线 #6 handoff schema 真完整。

Codex v1 §8 也提 critical path 但没明确 #6 是 RM 工作台前提 · 只说 "Sprint 4 final audit 阻塞"。**我坚持**: #6 不只是 audit 闸 · 是 demo 能跑闸。Sprint 5 演 RM 工作台需要 ReportJSON → DecisionInput schema 字段 · 没 schema 就不能 demo 1 客户全流程。

但 audit verdict 显示 #6 在 v1.1 看起来够 (64KB doc 不像空架子) · 这个 critical path 风险**可能**已经 mitigated · 不要变成新焦虑。我 R2 final 列为 "audit verify · 若 partial 立即报警 · 若 done 不动"。

### 坚持 #3 · Q-046 5 跑偏 root cause 硬规中"PM 高频提醒诱反应"风险 (#5)

Codex v1 风险 #1 "再次跑偏到非 Sprint 2 worker 或视觉" 触发条件只列 "PM/worker 提 idle、主 CLI 凭印象派活" · 漏了 Q-046 #5 PM 高频提醒诱反应 (STOP 5s 想 charter vs 印象)。

PM 5/2 已经发生过 (前主 CLI 派 B1 enrich + B4-credit BE7 都是 PM 提"worker idle"诱反应 · 没 STOP 5s)。**我坚持** v2 final 风险表加 #5 PM 高频提醒诱反应 · 缓解 = "STOP 5s · 想 charter 真主线 vs 印象 · 不立即响应"。

### 坚持 #4 · 不集成 Phase A 8 硬线复核 + Sprint 1 review 进 Sprint 2 启动 gate

我 v1 是不阻塞: 复核 today 同步做 · audit fire bg · PM 双击 launch.bat 启 worker · 不互锁。Codex v1 §4 风险 #1/#3/#4 + §5 DoD 也持同观点。**双方共识 · 坚持**。

---

## 4. Codex v1 弱点

### 弱点 #1 · 漏 onboarding trailer update (改 #1 + 坚持 #1 已论)

30 min / 0 cost / 100% 高 ROI 的 hygiene 没列 deliverable。

### 弱点 #2 · Sprint 3 减半时间分配模糊

Codex item #10 "B7 onboarding 明确只做 BE13 POC glue · 估 0.75-1 周" 但没说省下的 1 周 worker capacity 分配给谁 / 做啥。Sprint 3 三 worker (B4-channel + B4-riskctrl + B7) 加上 B7 减半省的 1 周 = 实际 capacity 比预算多。建议明确分配规则 (Phase A 漏的补 / Sprint 4 整合 buffer / 啥也不加 让 Sprint 4 提前 1 周)。

### 弱点 #3 · cron 5 min 巡逻 SOP specificity 不够

Codex item #3 "5 分钟 cron + state-snapshot 纪律" 但没列具体扫的 branch 名 / 扫完 fallback 行为 / monitor 90 min CPU=0 fallback 等。我 v1 列了 `feat/phase-b{4-alert,4-compliance,2-biz}` + state-snapshot 每 tick 写 + scoreboard.py 状态 (虽然 scoreboard.py 我之前发现不存在 · 这点 Codex 也没 catch) · 比 Codex specificity 高。

### 弱点 #4 · 没明确 PRD master `🟡 v1 draft` 状态 → PM 拍板事

Codex item #9 提到 "master 状态仍 pending PM ratification · 需 PM 标注 done/partial" · 但没明确这是 PM 工作 · 不是 worker 工作。R2 v2 final 应明确: PRD master ratification 是 PM 在合适时点 (Sprint 4 整合时) 显式批 · 1-3 周不主动推 PM 批 · 暴露状态 doc 即可。

### 弱点 #5 · Sprint 1 review 没明确 review verdict 流程

Codex item #7 sequential review 但没说 verdict (AGREE/DISAGREE/NEED-MORE-INFO) 流程 · 也没说 DISAGREE 时主 CLI 走插入点 3 仲裁还是 PM 拍。codex-mesh-protocol §6 已写 · 但 R2 v2 final 应 inline 提醒。

---

## 5. 吸收 Codex (R2 final 真接受)

| # | Codex v1 项 | 吸收方式 |
|---|---|---|
| 1 | Sequential 3 次 post-DONE review (B1+B4-credit+B4-report) | 替代我 1 次 periodic · 加 30 min budget 控制 cost |
| 2 | Observability gate Week 1 内 + `docs/runbook/phase-b-observability-gate.md` | 替代我 Sprint 4 timing |
| 3 | B2 doc-only 4 份具体 (pricing / multi-tenant / trial-flow / sales-playbook) | 列 R2 final deliverable 表 |
| 4 | Phase A 复核 file:line specificity | 加 grep 命令 + `docs/prd/master-2026-04-29.md:1-6` 状态 |
| 5 | `phase-b-sprint2-end-YYYY-MM-DD` tag 机制 | 加 R2 final DoD 末项 |
| 6 | "不阻塞 ≠ 不审" 原则 (Codex Dissent appendix) | R2 final 不写做硬规 · 但 v2 verbal 接受 |
| 7 | review P0/P1 阻塞 merge/deploy 但不阻塞 worker 开工 | R2 final 风险表 + verdict 流程 |
| 8 | BE2 / BE7 / BE3 具体 file:line 引用 | review onboarding-style brief 时引用 |

---

## 6. v2 Final Plan

### 6.1 Concrete Deliverable (融合后 16 件 · v1 14 + Codex 加 2)

| # | item | owner | 时间 | DoD (file:line / signal) |
|---|---|---|---|---|
| 1 | 三 onboarding trailer update (`REVIEW-MODE: manual` → `codex`) | 主 CLI | 30 min · today | `docs/onboarding/{B4-alert,B4-compliance,B2-biz}.md` 第 36-49 行 trailer 改 · commit signal `ONBOARDING-TRAILER-CODEX-RESUMED` |
| 2 | Phase A 8 硬线现状 doc | 主 CLI | 1-2 hr · today | `docs/audit/phase-a-status-2026-05-04.md` · 8 项逐条 yes/partial/no + evidence (含 `rg "--color-brass\|--color-ink\|letterpress\|ink-brush-hr" web/src` 0 命中验证 #5 / `docs/contracts/agent-handoff-schemas.md` 64KB 验证 #6 / `docs/prd/master-2026-04-29.md:1-6` 🟡 v1 draft pending 验证 #7) |
| 3 | Phase B pre-Sprint-2 audit (Codex periodic 插入点 4) fire bg | 主 CLI | 60 min wall · today | `docs/audit/codex-periodic/2026-05-04-phase-b-pre-sprint2.md` + commit signal `CODEX-PERIODIC-AUDIT-2026-05-04-DONE` · 4 questions (Sprint 1 BE drift / Sprint 2 onboarding 清晰 / Sprint 3 BE7 调整 / Phase A 8 硬线) |
| 4 | cron 5 min 巡逻启 (扫 3 worker branch) | 主 CLI ScheduleWakeup | 5 min · today | cron alive · `git log --all --oneline -50 --since="10 minutes ago"` · 扫 `feat/phase-b4-alert` + `feat/phase-b4-compliance` + `feat/phase-b2-biz` (4 旧 branch 已 release 不扫) · 每 tick 写 state-snapshot 段 (CLAUDE.md §14.1) |
| 5 | PM 双击 launch-all-LIUYE.bat 启 3 后端 worker | PM | 5 min · today (audit 不阻 · 启即可) | 4 cmd window 启 (MAIN-CLI + B4-alert + B4-compliance + B2 · 不含 B3) |
| 6 | Sprint 1 已 ship sequential post-DONE review #1: B1-flywheel | 主 CLI fire codex bg | 30 min budget · D1 | `docs/audit/codex-reviews/WORKER-B1-FLYWHEEL-DONE.md` + commit signal `CODEX-REVIEW-WORKER-B1-FLYWHEEL-DONE-VERDICT` + trailer `CODEX-VERDICT: AGREE/DISAGREE/NEED-MORE-INFO` · 重点查 BE10 feedback jsonl + Sprint 2 enrich 误派 6 commit drift |
| 7 | Sprint 1 sequential post-DONE review #2: B4-credit | 主 CLI fire codex bg | 30 min budget · D2 | `docs/audit/codex-reviews/WORKER-B4-CREDIT-DECISION-GRAPH-DONE.md` + verdict trailer · 重点查 `agent_credit/decision_engine.py:130-157` BE2 graph wrapper + `:159-196` BE7 ledger wrapper + `shared/decision_ledger/store.py:124-201` retention default + jurisdiction enum + subject_id hash |
| 8 | Sprint 1 sequential post-DONE review #3: B4-report | 主 CLI fire codex bg | 30 min budget · D3 | `docs/audit/codex-reviews/WORKER-B4-REPORT-MATERIAL-GAP-DONE.md` + verdict trailer · 重点查 `agent_report/api.py:604-658` SSE audit/key fail-fast · BE3 material gap graph + section impact |
| 9 | 数据飞轮 + decision ledger observability gate runbook | 主 CLI | 1 hr · D2-D3 | `docs/runbook/phase-b-observability-gate.md` 新建 · 记 feedback jsonl 写入率 + baseline run pass/fail + ledger `persisted=true` ratio + silent-fail count · 与 `shared/decision_ledger/store.py:124-201` 失败隔离对齐 |
| 10 | 等 B2 BE11 DONE | worker-B2 | ~1 week (~5/11) | `WORKER-B2-BIZ-DOC-DONE` signal commit · trailer `DOC-FILES: docs/biz/*.md (4 file)` |
| 11 | B2 post-DONE codex review (插入点 2) | 主 CLI fire codex bg | 30 min budget | verdict + trailer · DISAGREE 时走插入点 3 仲裁 or PM 拍 (codex-mesh-protocol §6) |
| 12 | B2 cherry-pick + push (codex AGREE 后) | 主 CLI | 15 min | main 含 B2 · ECS deploy 不需 (doc only) |
| 13 | Sprint 3 charter v2.2 prep (BE7 提前调整) | 主 CLI | 2-3 hr · 5/14 起 | `docs/reset/phase-b-charter.md` v2.2 段 · BE7 提前 ship 既成事实 + worker-B7 减半 (1.5-2w → 0.75-1w) + 减半时间分配规则 (audit verdict 决定 · 不预设) · PM verify |
| 14 | 等 B4-compliance DONE | worker | ~2-2.5 weeks (~5/18-5/21) | `WORKER-B4-COMPLIANCE-POLICY-REGISTRY-DONE` signal · baseline `policy_coverage >= 0.85` + `conflict_recall >= 0.85` |
| 15 | B4-compliance review + ECS deploy `--skip-build` | 主 CLI | ~1 hr | codex review verdict + cherry-pick + ECS pull + restart compliance service |
| 16 | 等 B4-alert DONE + review + deploy | worker + 主 CLI | ~3w · week 3 末 | `WORKER-B4-ALERT-SIGNAL-QUALITY-DONE` signal · baseline `signal_diversity >= 0.85` (从 0.0 → ≥ 0.85) + codex review + cherry-pick + ECS deploy --skip-build · 打 `phase-b-sprint2-end-2026-05-25` tag |

### 6.2 风险 (5 + 1 = 6 个)

| # | 风险 | 触发条件 | 缓解 | owner |
|---|---|---|---|---|
| 1 | worker 派偏 charter (Q-046 5 跑偏) | onboarding 模糊 / worker 自跳 sprint | 三 onboarding 已严格写 + #3 audit Q2 加固 + #6/#7/#8 sequential review 双闸 + #2 现状 doc 早暴露 | 主 CLI |
| 2 | Phase A 8 硬线 #6 handoff schema partial → demo 闭环 stuck | #2 现状 doc audit 后才知 | #2 today 必出 · audit verdict 显 partial 则 Sprint 3 减半的 1 周补 · audit verdict 显 done 则 buffer | 主 CLI |
| 3 | Codex 第二次用尽 / 高 reasoning latency | 频繁 fire bg / 高 reasoning | medium reasoning default · sequential 1 bg at a time · 30 min budget per review · 90 min monitor fallback manual (Q-043 v2) | 主 CLI |
| 4 | ECS 部署失败 (build / restart / healthcheck) | code 改 break / config 漂 | `scripts/deploy_to_ecs.sh` 含 healthcheck 失败 abort · `--skip-build` for backend-only · B2 不需 deploy (doc only) | 主 CLI |
| 5 | Ledger silent-fail 掩盖审计断链 (Codex 论点) | `shared/decision_ledger/store.py:124-201` `persisted=false` 多次 | #9 observability gate runbook · 统计 `persisted` ratio · 失败不阻业务但 alert · Sprint 4 整合时 Codex periodic audit 二次审 | 主 CLI |
| 6 | PM 高频提醒诱反应 (Q-046 跑偏 #5 specific trigger · Codex v1 漏列) | PM 提"worker idle"/"加点啥"/"还有什么" | STOP 5s · 想 charter 真主线 vs 印象 · 不立即响应 · 派单前 grep charter verify | 主 CLI |

### 6.3 DoD (整体 3 周后 PM 看到)

3 周后 (~2026-05-25) PM 看到:
- Sprint 2 三 worker 全 DONE · cherry-pick · ECS 部署 (B2 不需 / B4-compliance + B4-alert `--skip-build`)
- B2 4 份商业化 doc 落地 (`docs/biz/{pricing,multi-tenant,trial-flow}-assumptions.md` + `sales-playbook-v1.md`) · 0 代码改动
- Agent5 baseline `policy_coverage >= 0.85` + `conflict_recall >= 0.85` (B4-compliance DoD)
- Agent4 baseline `signal_diversity >= 0.85` (从 0.0 升 · B4-alert DoD)
- Sprint 1 已 ship 后端 3 review (B1 + B4-credit + B4-report) verdict 留底 (`docs/audit/codex-reviews/`) · P0/P1 fix-forward 或纳入 Sprint 3/4
- `docs/audit/phase-a-status-2026-05-04.md` Phase A 8 硬线现状 doc + `docs/audit/codex-periodic/2026-05-04-phase-b-pre-sprint2.md` audit doc 留底
- `docs/runbook/phase-b-observability-gate.md` runbook + observability metrics dashboard 雏形
- `phase-b-sprint2-end-2026-05-25` tag 在 `main`
- decisions-log Q-048..Q-052 (本期决策追加 · 至少含 Sprint 1 review verdict 入册 + Sprint 3 charter v2.2 ratify + observability gate runbook)
- state-snapshot 完整 Day 3..Day 21 段 (CLAUDE.md §14.1 硬规 0 violation)
- cron scoreboard 显 "Sprint 2 done · Sprint 3 ready"
- Q-046 5 跑偏 root cause 硬规 + Q-047 视觉冻结 0 violation

### 6.4 不做的事 (反 Q-046 5 跑偏 · v1 8 + Codex 加 1 = 9 条)

- ❌ 不派 Sprint 3 worker (charter 真主线 ~5/25 后启 · 不提前)
- ❌ 不接 BE7 提前的 worker-B7 (Sprint 3 worker · 不主动加 worker)
- ❌ 不动视觉 (Q-047 PM ratify 冻结 · PM 显式 unfreeze 才启)
- ❌ 不 codex 并发 (Q-043 v2 sequential 1 bg at a time · R1/R2/review 各自一次)
- ❌ 不省 onboarding update (改 #1 列 0 cost · 防 worker 误以为 manual review)
- ❌ 不省 audit / 现状 doc / observability gate (Q-046 5 跑偏硬规 + Codex "不阻塞 ≠ 不审" 原则)
- ❌ 不在 PM 高频提醒时立即响应 (STOP 5s · 想 charter 真主线 vs 印象)
- ❌ 不对 B3 视觉撤回的 worker 做 post-DONE review (Q-047 后 B3 release · 视觉成果已撤 · review 无意义)
- ❌ 不主动推 PM ratify PRD master (Codex 弱点 #4 · 是 PM 在合适时点显式批 · Sprint 4 整合时再问 · 1-3 周不主动推)

### 6.5 替代方案 evaluated rejected (v1 5 + R2 加 1 = 6)

- A. 不 audit · 直接派 Sprint 2 — 拒. Q-046 5 跑偏硬规 #1 要求 charter verify
- B. Phase A 8 硬线全补完再启 Sprint 2 — 拒. Phase A 已 declared exit · 补走 Sprint 3 减半 (audit verdict 决定)
- C. 完全 reset Phase B charter v2 — 拒. v2 已 PM ratify (Q-045 + Q-046)
- D. Sprint 2 + Sprint 3 合并启 (6 worker 同时跑) — 拒. 反 Q-046 跑偏 #3
- E. post-DONE review 4 worker (B1+B4-credit+B4-report+B3) 各 fire 1 次 — 改 #2 后部分接受 (3 sequential 替代 4 各自 fire · B3 视觉撤不 review)
- **F (R2 加)**. Sprint 3 减半时间预设补 #6 handoff schema — 拒. audit verdict 决定 · 若 #6 done 不补 · 若 partial 补 · 若 #7 PRD pending 不补 (PM 拍板事)

### 6.6 Critical path 反推 (v1 unchanged · v2 不动)

Sprint 5 demo 4 维 → 1-3 周:
- B4-alert / B4-compliance: **YES** (RM 工作台 Agent4/Agent5 真业务能力)
- B2 商业化 doc: **NO 直接 critical** · Phase B 验收硬线 #2 要求 (sales-ready 外壳)
- Phase A #6 handoff schema: **真 critical** (RM 工作台 demo 闭环前提) · 但 audit verdict 暴露后才知 · #2 现状 doc today 必出
- Sprint 1 已 ship 后端可观测性: **YES** (Codex 论点 · demo 可信审计底座) · #9 observability gate Week 1 内做

1-3 周 plan ~70% 在 critical path · ~30% 是 enabler (商业化 doc / audit / cron / onboarding update / observability gate runbook) · 比例合理。

---

## 7. v2 Dissent (R3 用)

我 v2 vs Codex 预期 v2 的可能 dissent:

1. **Sprint 1 review 的 30 min budget per review 是否够** — 我 v2 加 budget 控制 cost · Codex 可能反对说 30 min 太短 · 看 file:line 不够细。R3 可能争 budget 长度 (30 / 45 / 60 min)。
2. **Observability gate runbook 是否包含 alert/notification 机制** — 我 v2 只说 "失败不阻业务但 alert" · Codex 可能要求具体 alert 路径 (lark-im 飞书通知 · 还是 email · 还是 just runbook 记)。R3 可能争 alert 实装 vs only runbook spec。
3. **PRD master `🟡 v1 draft pending` 是否 1-3 周内推 PM 批** — 我 v2 不主动推 · Codex 可能推 Sprint 2 末同步推。R3 可能争 PM 工作流程 (PM 拍板事 vs 主 CLI 主动 nudge)。
4. **Sprint 2 + Sprint 3 间是否需要 1 周 buffer 防 Sprint 2 延期** — 我 v2 没明确 · 假设 Sprint 2 按时 ~5/25。Codex 可能推 buffer。R3 可能争 schedule risk。
5. **B1 review 是否包含 Sprint 2 enrich 误派 6 commit 的"是否撤回"决策** — 我 v2 R2 没说撤回 (Q-046 接受既成事实) · Codex 可能在 R2 推 review 时要求二次评估是否撤。R3 可能争 "误派但 ship · 撤还是不撤"。

如果以上任何 dissent 在 R2 后 codex v2 持不同立场 · R3 仲裁 (codex 插入点 3 中立 · 或 PM 拍)。

---

End Round 2 v2.
