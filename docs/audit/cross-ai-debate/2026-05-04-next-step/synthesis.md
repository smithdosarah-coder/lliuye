# Synthesis · "下一步 1-3 周 plan" · Final · 给 PM 拍板

> 作者: 主 CLI · 2026-05-04 · 综合 main-cli-v1 / codex-v1 / main-cli-v2 / codex-v2 (R1 + R2 双 AI 辩论)
> R3 跳过 (实质 dissent 0 · 双方 v2 实际收敛 · 详 §3)
> 等 PM 拍板 GO / NOGO 一句话

---

## 1. 一段话 verdict

**1-3 周 (2026-05-04 → ~2026-05-25) 下一步**: Today 4 件并行 (onboarding trailer + Phase A 8 status doc + pre-Sprint-2 Codex periodic audit fire + cron 启) → PM 双击 launch.bat 启 3 后端 worker (B4-alert + B4-compliance + B2 · Q-046 Sprint 2 真主线) → Week 1 内最小 observability checklist + B2 BE11 doc-only DONE → Week 2-3 等 B4-compliance + B4-alert DONE 序列 + Sprint 3 charter v2.2 prep → Week 3 末 sprint-end tag。**关键发现 (Codex R2 catch · 我 R1+R2 漏)**: `docs/contracts/agent-handoff-schemas.md:17` 自述 "v1.1 仅 placeholder · v1.2 实装" · 而 placeholder 的 6 反向链 + Agent2 链**正是 B4-alert/B4-compliance 要碰的字段** · 必须在 onboarding 加 contract reference 警告 (不等 Sprint 3 补)。

---

## 2. R1 → R2 双方收敛过程

### R1 双 AI 独立 v1 (anti-bias rule 1 · 互不见对方)

- **Main CLI v1**: 14 deliverable + 5 风险 + critical path 反推 + 6 dissent 预期 (commit `6393249`)
- **Codex v1**: 11 deliverable + 5 风险 + critical path + 自己 dissent (commit `b63c308` 含)
- 双方 R1 共识 (8 项): Sprint 2 三 worker 真主线 / Q-047 视觉冻结 / Q-043 codex protocol v2 / cron 5 min / Sprint 3 BE7 提前 + B7 减半 / Phase A partial 复核 / B2 doc-only 红线 / state-snapshot 纪律

### R2 双方互评 v2 (各看对方 v1)

**双方 R2 各自接受对方的事**:

| Codex R2 接受 main CLI v1 | Main CLI R2 接受 Codex v1 |
|---|---|
| Phase A 全 8 项 yes/partial/no (Codex R1 只 #5/#6/#7) | Sprint 1 sequential review file:line specificity 高 (`agent_credit/decision_engine.py:130-157` BE2 graph wrapper / `:159-196` BE7 ledger · `agent_report/api.py:604-658` SSE) |
| 集中 pre-Sprint-2 periodic audit 替代 sequential 3 review (cost 控制) | Observability gate Week 1 内 + `docs/runbook/phase-b-observability-gate.md` 替代 Sprint 4 timing |
| Sprint 3 charter v2.2 prep + B7 改 BE13-only | B2 doc-only 4 份具体 (`docs/onboarding/B2-biz.md:12-31`) |
| 不补完 Phase A 再启 Sprint 2 (Codex 接受不互锁) | Phase A 复核 file:line specificity (`docs/prd/master-2026-04-29.md:1-6` 🟡 v1 draft pending) |
| 三 onboarding trailer update | sprint-end tag 机制 |

**Codex R2 catch 我 R2 漏的 2 项**:

1. **B2 DONE signal**: 我 v1 写错 `WORKER-B2-BIZ-DONE` · 真 onboarding `B2-biz.md:42` 是 `WORKER-B2-BIZ-DOC-DONE` (我 v2 已 catch · 但 Codex 不知 anti-bias)
2. **`docs/contracts/agent-handoff-schemas.md:17` 自述 "v1.1 仅 placeholder · v1.2 实装"**: 我 v2 critical path 反推假设 "64KB 看起来够" 错了 · v1.0 4 主链真 done · v1.1 加补的 6 反向链 + 2 Agent2 链是 placeholder 待 v1.2 实装 · **而 B4-alert (Agent4↔Agent5 反向链) + B4-compliance (Agent5→Agent4/Agent6 反向链) 正是 placeholder 部分**

### R2 后真实状态

Codex R2 §7 列 5 项 dissent (R3 用) · 实际收敛后:

| # | Codex R2 dissent | 真实状态 |
|---|---|---|
| 1 | Observability timing (Codex 主 Week 1-2 · 预期我反对) | 已收敛 · 我 R2 已接受 Week 1 内 (Codex 不知 anti-bias) |
| 2 | Sprint 1 review granularity (Codex 主 periodic 先行 + P0/P1 拆 · 预期我只主张 Q1 汇总) | 我接受 Codex 这版 · 比我 v2 sequential 3 with budget 更高明 (cost 更低 · audit 是先行闸 · sequential 仅 P0/P1) |
| 3 | Handoff schema partial 处理 (Codex 主立即给 onboarding 加 reference if 缺 Sprint 2 字段) | 现在已 verify partial · placeholder 正是 Sprint 2 字段 · 立即加 reference (不等 Sprint 3) |
| 4 | DONE signal 正名 | 已收敛 (我 v2 已 catch) |
| 5 | ECS deploy phrasing (Codex 主 "按 touched service healthcheck" · 反对一律 specific service 名) | 我接受 Codex 这版 (更通用不出错) |

**R3 真实 dissent: 0** · skip。

---

## 3. v2 Final Plan (融合 main-cli-v2 + codex-v2 · synthesis)

### 3.1 Concrete Deliverable (15 件)

| # | item | owner | 时间 | DoD (file:line / signal) |
|---|---|---|---|---|
| 1 | 三 onboarding trailer + DONE signal alias 修正 | 主 CLI | 30 min · D0 | `B4-alert.md:36-39` + `B4-compliance.md:36-39` + `B2-biz.md:46-49` `REVIEW-MODE: manual` → `codex (resumed 2026-05-04)`; cron 兼容 `WORKER-B2-BIZ-DOC-DONE` (canonical) + `WORKER-B2-BIZ-DONE` (alias 防漏扫); commit signal `ONBOARDING-TRAILER-CODEX-RESUMED` |
| 2 | **Sprint 2 worker onboarding 加 handoff schema v1.1 placeholder 警告** (Codex R2 catch) | 主 CLI | 30 min · D0 | `B4-alert.md` + `B4-compliance.md` 加段: "`docs/contracts/agent-handoff-schemas.md:17` v1.1 反向链 fixture placeholder · 你的 worker 触及 Agent4↔Agent5/Agent6 反向链请自写 fixture + 在 v1.2 spec section 标记 file:line · 不等 Sprint 3 补" |
| 3 | Phase A 8 硬线全状态 doc (8 项 yes/partial/no + evidence) | 主 CLI | 1-2 hr · D0 | `docs/audit/phase-a-status-2026-05-04.md` · 8 项 + commit sha · 重点: #5 `rg "--color-brass\|--color-ink\|letterpress\|ink-brush-hr" web/src` 0 命中 / #6 `agent-handoff-schemas.md:17` v1.1 placeholder 状态 / #7 `prd/master-2026-04-29.md:3` 🟡 pending PM ratification |
| 4 | Pre-Sprint-2 Codex periodic audit fire bg (插入点 4 提前) | 主 CLI fire codex | 60-90 min wall · D0 | `docs/audit/codex-periodic/2026-05-04-phase-b-pre-sprint2.md` + commit signal `CODEX-PERIODIC-AUDIT-2026-05-04-DONE` · 5 questions (Sprint 1 BE drift / Sprint 2 onboarding clarity / Sprint 3 BE7 调整 / Phase A 8 status / ledger+flywheel min-observability checklist) |
| 5 | cron 5 min 巡逻启 | 主 CLI ScheduleWakeup | 5 min · D0 | 扫 `feat/phase-b4-alert` + `feat/phase-b4-compliance` + `feat/phase-b2-biz` (4 旧 release branch 不常规扫 · audit P0/P1 出现时临时加 fix-forward branch); 每 tick 写 state-snapshot 段 (CLAUDE.md §14.1) |
| 6 | PM 双击 launch-all-LIUYE.bat 启 3 后端 worker | PM | 5 min · D0 (audit 不阻 · 启即可) | 4 cmd window 启 (MAIN-CLI + B4-alert + B4-compliance + B2 · 不含 B3); resume signal `WORKER-B4-ALERT-RESUMED` + `WORKER-B4-COMPLIANCE-RESUMED` + `WORKER-B2-RESUMED` |
| 7 | Sprint 1 已 ship periodic audit follow-up (P0/P1 才拆 sequential review) | 主 CLI fire codex | sequential after #4 verdict · D1-D4 budget | `docs/audit/codex-reviews/WORKER-{B1-FLYWHEEL\|B4-CREDIT-DECISION-GRAPH\|B4-REPORT-MATERIAL-GAP}-DONE.md` per audit verdict · 每 P0/P1 case 30 min budget · trailer `CODEX-VERDICT: AGREE/DISAGREE/NEED-MORE-INFO` · DISAGREE 走插入点 3 仲裁 or PM 拍 (codex-mesh-protocol §6) |
| 8 | Ledger / flywheel min-observability checklist (Codex R2 折中 · 不改代码) | 主 CLI | 1 hr · D2-D3 | `docs/runbook/phase-b-observability-gate.md` · 4 项 checklist: `/api/feedback` jsonl 写入率 + 6-agent baseline run pass/fail + ledger `persisted=true` ratio + silent-fail count; align `shared/decision_ledger/store.py:124-201` · 接 Sprint 1 audit 已有指标 (无需 worker 改代码) |
| 9 | 等 B2 BE11 DONE | worker-B2 | ~1 week (~5/11) | `WORKER-B2-BIZ-DOC-DONE` (canonical) + trailer `DOC-FILES: docs/biz/*.md (4 file)` · 4 docs: `pricing-assumptions.md` + `multi-tenant-assumptions.md` + `trial-flow-assumptions.md` + `sales-playbook-v1.md` |
| 10 | B2 post-DONE Codex review + cherry-pick (doc-only 不 ECS) | 主 CLI fire codex | 30 min budget · ~5/11 | `docs/audit/codex-reviews/WORKER-B2-BIZ-DOC-DONE.md` + verdict; AGREE 后 cherry-pick main; doc-only 不 ECS deploy |
| 11 | 等 B4-compliance DONE | worker | ~2-2.5 weeks (~5/18-5/21) | `WORKER-B4-COMPLIANCE-POLICY-REGISTRY-DONE` · baseline `policy_coverage >= 0.85` + `conflict_recall >= 0.85` (`B4-compliance.md:45`) |
| 12 | B4-compliance review + ECS deploy (按 touched service healthcheck · Codex R2 修正) | 主 CLI | ~1 hr | codex review verdict + cherry-pick + ECS pull + restart **affected backend service only** (per `scripts/deploy_to_ecs.sh --skip-build` · service name 按 touched module · 不预写 specific name); healthcheck pass abort-on-fail |
| 13 | Sprint 3 charter v2.2 + onboarding 草稿 prep | 主 CLI | 2-3 hr · ~5/14 起 | `docs/reset/phase-b-charter.md` v2.2 段: BE7 提前 ship 既成事实 + worker-B7 改 BE13-only (1.5-2w → 0.75-1w) + 减半时间分配规则 (audit verdict + handoff schema v1.1 实际 partial 决定) + B4-channel/B4-riskctrl/B7-final onboarding 草稿; PM verify 后才派 |
| 14 | 等 B4-alert DONE + review + deploy | worker + 主 CLI | ~3 weeks (~5/22-5/25) | `WORKER-B4-ALERT-SIGNAL-QUALITY-DONE` · baseline `signal_diversity >= 0.85` (从 0.0 升 · `B4-alert.md:27`) + codex review + cherry-pick + ECS deploy 按 touched service healthcheck |
| 15 | Sprint 2 closeout sprint-end tag + handoff | 主 CLI | week 3 末 · ~5/25 | `phase-b-sprint2-end-2026-05-25` tag in main; decisions-log Q-048..Q-052 entry (Sprint 1 review verdict 入册 + Sprint 3 charter v2.2 ratify + observability checklist + handoff schema v1.2 决定); state-snapshot Day 3-21 完整 (CLAUDE.md §14.1 0 violation) |

### 3.2 风险

| # | 风险 | 缓解 |
|---|---|---|
| 1 | Q-046 式跑偏复发 (派非 Sprint 2 worker / 视觉) | 每次派单前 grep charter; STOP 5s; PM 高频提醒不立即响应; Q-047 freeze 守住 |
| 2 | DONE signal 漏扫 (B2 BIZ-DONE vs BIZ-DOC-DONE) | cron 同时识别 canonical + alias |
| 3 | Codex quota / 卡死 | medium reasoning · sequential 1 bg at a time · 90 min CPU=0 fallback manual (Q-043 v2) |
| 4 | Handoff schema v1.1 placeholder 撞 Sprint 2 worker | #2 onboarding 警告 + worker 自写 fixture + v1.2 spec file:line 标记 |
| 5 | Silent regression (feedback/ledger 写入失败但 demo 继续) | #8 min-observability checklist; P0/P1 才阻塞 merge/deploy |
| 6 | PM 高频提醒诱反应 (Q-046 跑偏 #5 specific trigger) | STOP 5s · 想 charter 真主线 vs 印象 · 不立即响应 |

### 3.3 DoD (3 周后 PM 看到 · ~2026-05-25)

- Sprint 2 三 worker 全 DONE · Codex reviewed · merged · ECS deploy (B4-alert/B4-compliance 按 touched service healthcheck · B2 doc-only 不 deploy)
- B2 4 份商业化 doc 落地 · 0 代码改动
- Agent5 baseline `policy_coverage/conflict_recall >= 0.85` · Agent4 baseline `signal_diversity >= 0.85`
- `docs/audit/phase-a-status-2026-05-04.md` (8 硬线全状态) + `docs/audit/codex-periodic/2026-05-04-phase-b-pre-sprint2.md` (audit) 留底
- `docs/runbook/phase-b-observability-gate.md` (min-observability checklist · 不改代码)
- Sprint 1 BE drift 已集中审 · P0/P1 fix-forward 或纳入 Sprint 3/4
- Sprint 3 charter v2.2 + onboarding 草稿 ready · B7 改 BE13-only · PM verify 后才派
- handoff schema v1.1 placeholder 部分: Sprint 2 worker 自写 fixture · v1.2 实装路径决定 (Sprint 3 减半时间补 vs PM 拍板)
- `phase-b-sprint2-end-2026-05-25` tag · decisions-log Q-048+ · state-snapshot Day 3-21 (CLAUDE.md §14.1 0 violation)
- Q-046 5 跑偏 root cause 硬规 + Q-047 视觉冻结 0 violation

### 3.4 不做的事 (反 Q-046 · 9 条)

- ❌ 不启 B3 / 不改视觉 / 不问 F4 v2
- ❌ 不接 BE7 提前的 worker-B7 (Sprint 3 worker)
- ❌ 不并发 Codex (Q-043 v2)
- ❌ 不省 onboarding update / audit / 现状 doc / observability checklist
- ❌ 不在 PM 高频提醒时立即响应 (STOP 5s)
- ❌ 不对 B3 视觉撤回的 worker 做 post-DONE review
- ❌ 不主动推 PM ratify PRD master (Sprint 4 整合再问)
- ❌ 不把 Phase A status doc 变成大返工借口
- ❌ 不预写 ECS specific service 名 (按 touched service healthcheck · Codex R2)

---

## 4. PM 拍板项 (1 个真问题 · 其他自动)

PM 一句话决定:

**"GO / NOGO 立即执行 D0 4 件 + 双击 launch.bat 启 3 后端 worker?"**

GO 后我立即 fire (sequence in §5)。NOGO 我等 PM 进一步指令。

**Sub-question (PM 不答默认我推荐)**:

| Sub-Q | 我推荐 | 备选 |
|---|---|---|
| Sprint 1 review = periodic audit 先行 + P0/P1 拆 (Codex R2) vs sequential 3 with budget (我 v2)? | **Codex R2 版** (cost 更低 · audit 是先行闸 · sequential 仅 P0/P1 才拆) | sequential 3 with budget |
| Observability = Week 1 checklist/runbook 不改代码 (双方 R2 共识) vs Week 1 改代码 (Codex R1) vs Sprint 4 (我 v1)? | **双方 R2 共识 (checklist + runbook · 不改代码)** | 改代码 / 后置 |
| Handoff schema v1.1 placeholder Sprint 2 worker 处理? | **onboarding 加警告 + worker 自写 fixture + v1.2 决定 Sprint 3 减半时间补 (Codex R2)** | 留 Sprint 3 才碰 |
| ECS deploy 表述? | **按 touched service healthcheck (Codex R2)** | 预写 specific service 名 |
| R3 仲裁? | **跳过** (实质 dissent 0) | fire R3 codex 仲裁 |

---

## 5. PM GO 后立即执行 sequence

```
T+0   commit synthesis.md (本文) + push origin main (留 PM 看)
T+1m  并行: 三 onboarding trailer + signal alias 修正 (item 1+2)
T+5m  Phase A 8 status doc 写 (item 3)
T+30m fire Codex periodic audit bg (item 4 · medium reasoning · sequential)
T+30m cron 5 min 巡逻启 (item 5 · ScheduleWakeup)
T+30m PM 双击 launch.bat (item 6 · 不阻 audit · 直接启)
T+90m Codex audit verdict 回 · 看 P0/P1 → 决定 item 7 sequential review 触发与否
T+1d  observability checklist runbook 起草 (item 8)
T+1w  B2 DONE → review → cherry-pick (item 9-10)
T+10d Sprint 3 charter v2.2 prep (item 13 起草)
T+18d B4-compliance DONE → review → deploy (item 11-12)
T+21d B4-alert DONE → review → deploy + sprint-end tag (item 14-15)
```

---

## 6. 文件清单 (所有 git 留底)

- `docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md` (commit `6393249`)
- `docs/audit/cross-ai-debate/2026-05-04-next-step/codex-R1-prompt.md` (`6393249`)
- `docs/audit/cross-ai-debate/2026-05-04-next-step/codex-v1.md` (`b63c308`)
- `docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v2.md` (`b63c308`)
- `docs/audit/cross-ai-debate/2026-05-04-next-step/codex-R2-prompt.md` (`b63c308`)
- `docs/audit/cross-ai-debate/2026-05-04-next-step/codex-v2.md` (本 commit 加)
- `docs/audit/cross-ai-debate/2026-05-04-next-step/synthesis.md` (本文 · 待 commit)

PM 任意打开看 · 全文皆可。

---

End synthesis. 等 PM "GO" / "NOGO" / 调整。
