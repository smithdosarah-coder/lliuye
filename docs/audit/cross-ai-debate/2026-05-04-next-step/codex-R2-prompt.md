# Codex Round 2 · v2 · "下一步 1-3 周 plan" · Cross-Critique

You are Codex (gpt-5.5-codex). In Round 1 you wrote `codex-v1.md` independently. Main CLI (Claude) wrote `main-cli-v1.md` IN PARALLEL — they couldn't see your v1.

Now Round 2: you read main CLI's v1 + your own v1 · write v2 with schema "改 / 坚持 / 对方弱点 / 吸收对方 / v2 final".

## Anti-bias rules

- 看双方 v1 后写 R2 · NOT 抄 main CLI v2 (you don't see it · they're parallel)
- ≤ 4000 词
- file:line / commit sha 必备
- 强 dissent 留到 §7 (R3 用 · 不强行收敛)
- 不站队 R1 立场 · 真改要承认 · 真坚持要论证

## Required reading (R1 时已读 · 此次仅 spot-check 变化)

- HEAD = `6393249` (R1 fire 时) · check `git log --oneline -5` 看本次有无新 commit
- `RESET_MASTER_PLAN.md` / `docs/reset/north-star.md` / `docs/reset/phase-a-charter.md` / `docs/reset/phase-b-charter.md`
- `docs/reset/state-snapshot.md` 末 200 行
- `docs/handoff/decisions-log.md` 末 250 行 (Q-043 to Q-047)
- `docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-05-02.md` (v3)
- `CLAUDE.md` (root · §3.7 / §13 / §14 / §15)
- spot-check `docs/onboarding/{B4-alert,B4-compliance,B2-biz}.md`
- spot-check `docs/contracts/agent-handoff-schemas.md` (你 R1 引 v1.1 · 验证字段是否真完整 · 别假设 64KB 就 done)
- spot-check `docs/prd/master-2026-04-29.md:1-30` (你 R1 引 :1-6 pending PM ratification · 验证状态)

## Inputs (verbatim · 完整 v1 双方文本)

### Main CLI v1 (verbatim · 你 R1 时未见)

# Main CLI Round 1 · v1 · "下一步 1-3 周 plan" · Independent

> 作者: 主 CLI Claude Opus 4.7 (1M context) · 2026-05-04 · 独立 v1 · 不见 Codex v1 (anti-bias rule 1)
> Round 1 fire 时 Codex bg 在并行跑 · 双方 R1 完成后进 R2 互评

## 1. Scope 界定

"下一步 1-3 周" = 2026-05-04 (今天 · post-Q-047 reset session day 1) 起 · 至 ~2026-05-25 · Phase B Sprint 2 启动 + 第一/第二 worker 进展期。

含: Sprint 2 三 worker 派单 prep + worker DONE 序列处理 + Phase A 8 硬线现状梳理 + critical path 风险暴露 + Sprint 3 charter prep (BE7 提前调整)。

不含: 视觉路线 (Q-047 冻结 · PM 显式 unfreeze 才动) · Sprint 3 三 worker 实际派单 (~5/25 后) · Sprint 4 整合 · Sprint 5 demo。

## 2. TL;DR

1-3 周做 5 件 · 第一周内 4 件并行 + 后续 2 周 worker DONE 序列被动跟。**核心判断**: Sprint 2 三 worker 照原计划启 (charter v2 真主线 · Q-046 验证) · 但启之前必做 critical path 风险暴露 (Phase A 8 硬线现状 doc · 尤其 #6 handoff schema · 这是 demo 闭环前提) · 启之后用 codex post-DONE peer review 双闸 (插入点 2 · codex 已恢复)。

## 3. Concrete deliverable

| # | item | owner | 时间 | DoD (file:line / signal) |
|---|---|---|---|---|
| 1 | 三 onboarding trailer update | 主 CLI | 30 min · today | `docs/onboarding/B{4-alert,4-compliance,2-biz}.md` `REVIEW-MODE: manual` → `codex` (codex 已恢复) · commit signal `ONBOARDING-TRAILER-UPDATE-CODEX-RESUMED` |
| 2 | Phase A 8 硬线现状 doc | 主 CLI | 1-2 hr · today | `docs/audit/phase-a-status-2026-05-04.md` · 8 项逐条 yes/partial/no + evidence (file:line / commit sha) · 暴露 #5 Letterpress Q-047 后 / #6 handoff schema / #7 PRD master 真状态 |
| 3 | Phase B pre-Sprint-2 audit (Codex periodic 插入点 4 提前) | 主 CLI fire codex bg | 60 min wall · today | `docs/audit/codex-periodic/2026-05-04-phase-b-pre-sprint2.md` + commit signal `CODEX-PERIODIC-AUDIT-2026-05-04-DONE` · 4 questions 答 (Q1 Sprint 1 BE drift / Q2 Sprint 2 onboarding 清晰度 / Q3 Sprint 3 BE7 提前调整 / Q4 Phase A 8 硬线完成度) |
| 4 | cron 5 min 巡逻启 | 主 CLI ScheduleWakeup | 5 min · today | cron alive · git log -50 --since=10min · 扫 3 worker branch (`feat/phase-b4-alert` + `feat/phase-b4-compliance` + `feat/phase-b2-biz` · 4 旧 worker branch 已 release 不扫) |
| 5 | PM 双击 launch.bat 启 3 后端 worker | PM | 5 min · today (audit 后) | 3 cmd window 启 (B4-alert + B4-compliance + B2 · 不含 B3) |
| 6 | 等 B2 BE11 DONE | worker-B2 | ~1 week (~5/11) | `WORKER-B2-BIZ-DONE` signal commit |
| 7 | B2 post-DONE codex review (插入点 2) | 主 CLI fire codex bg | 60 min wall | `docs/audit/codex-reviews/WORKER-B2-BIZ-DONE.md` + commit signal `CODEX-REVIEW-WORKER-B2-BIZ-DONE-VERDICT` · trailer `CODEX-VERDICT: AGREE/DISAGREE/NEED-MORE-INFO` |
| 8 | B2 cherry-pick + push (codex AGREE 后) | 主 CLI | 15 min | main 含 B2 · ECS deploy 不需 (doc only) |
| 9 | Sprint 3 charter v2.2 prep | 主 CLI | 2-3 hr · 5/14 起 | `docs/reset/phase-b-charter.md` v2.2 段 (BE7 提前 + worker-B7 减半 1-1.5w → 0.75-1w + 减半时间分配建议) · PM verify |
| 10 | 等 B4-compliance DONE | worker | ~2-2.5 weeks (~5/18-5/21) | `WORKER-B4-COMPLIANCE-POLICY-REGISTRY-DONE` |
| 11 | B4-compliance review + ECS deploy --skip-build | 主 CLI | ~1 hr | codex review verdict + cherry-pick + ECS pull + restart compliance service |
| 12 | 等 B4-alert DONE (~3w · 5/25 周) | worker | week 3 末 | `WORKER-B4-ALERT-SIGNAL-QUALITY-DONE` |
| 13 | B4-alert review + ECS deploy --skip-build | 主 CLI | ~1 hr | 同 #11 |
| 14 | Sprint 3 派单 prep (3 onboarding 写) | 主 CLI | week 3 末 (5/22-5/25) | `docs/onboarding/B4-{channel,riskctrl}.md` + `B7-final.md` 草稿 · 等 PM verify |

## 4. 风险

| # | 风险 | 触发条件 | 缓解 | 缓解 owner |
|---|---|---|---|---|
| 1 | worker 派偏 charter (Q-046 5 跑偏) | onboarding 模糊 / worker 自跳 sprint | 三 onboarding 已严格写 + #3 audit Q2 加固 + 启后 codex post-DONE review 双闸 | 主 CLI |
| 2 | Phase A 8 硬线 #6 handoff schema partial → Sprint 2/3 stuck | #2 现状 doc 暴露后才知 | #2 现状 doc today 必出 · 若 partial 则 Sprint 3 减半的 1-1.5 周补 · 不留到 Sprint 4 | 主 CLI |
| 3 | Codex 第二次用尽 (token / quota) | 频繁 fire bg / 高 reasoning | medium reasoning default · sequential 1 bg at a time · 90 min monitor fallback manual (Q-043 v2) | 主 CLI |
| 4 | ECS 部署失败 (build / restart / healthcheck) | code 改 break / config 漂 | `scripts/deploy_to_ecs.sh` 含 healthcheck · 失败 abort · `--skip-build` for backend-only | 主 CLI |
| 5 | 数据飞轮 BE10 + decision ledger BE7 没 monitoring → silent regression | Sprint 2 worker 改后端无 baseline 比对 | #3 audit 包含 evaluation runner baseline check · Sprint 2 worker onboarding 已要求跑 baseline (B4-alert `signal_diversity ≥ 0.85`) | 主 CLI + worker |

## 5. DoD (整体 3 周后)

3 周后 PM 看到:
- Sprint 2 三 worker (B4-alert + B4-compliance + B2) 全 DONE · cherry-pick 进 main · ECS 部署 (--skip-build for backend / B2 不需)
- Phase A 8 硬线现状 doc + Codex periodic audit doc 留底 (`docs/audit/`)
- Sprint 3 charter v2.2 (含 BE7 提前调整 + worker-B7 减半时间分配 + 三 worker onboarding 草稿)
- decisions-log Q-048..Q-051 (本期决策追加)
- state-snapshot Day 3..Day 21 完整段 (CLAUDE.md §14.1 硬规守住)
- cron scoreboard 显 "Sprint 2 done · Sprint 3 ready"
- 5 跑偏 root cause 硬规 0 violation (任何派单前 grep charter / PM idle 先读 charter / Sprint 边界 mental switch / P0 写死优先级 / PM 高频提醒 STOP 5s)

## 6. 不做的事 (反 Q-046 5 跑偏)

- ❌ 不派 Sprint 3 worker (charter 真主线说 Sprint 3 是 ~5/25 后启 · 不提前)
- ❌ 不接 BE7 提前的 worker-B7 (Sprint 3 worker · 不主动加 worker)
- ❌ 不动视觉 (Q-047 PM ratify 冻结 · 任何视觉变更 PM 显式 unfreeze 才启)
- ❌ 不 codex 并发 (Q-043 v2 sequential 1 bg at a time · 哪怕 R1 R2 也是各自一次)
- ❌ 不省 onboarding update (codex 恢复后 trailer 改 codex · 0 cost · 防 worker 误以为 manual review)
- ❌ 不省 audit / 现状 doc (Q-046 5 跑偏硬规 · 启动前必 verify · 不允许"看着像 OK"就启)
- ❌ 不在 PM 高频提醒时立即响应 (STOP 5s · 想 charter 真主线 vs 印象)
- ❌ 不对 B3 视觉撤回的 worker 做 post-DONE review (Q-047 后 B3 release · 视觉成果已撤 · review 无意义)

## 7. 替代方案 evaluated rejected

- A. **不 audit · 直接派 Sprint 2** — 拒. Q-046 5 跑偏硬规 #1 要求 charter verify · audit 是显式 verify · 省 60 min audit 换 3 周 worker 派偏风险不值得
- B. **Phase A 8 硬线全补完再启 Sprint 2** — 拒. Phase A 已 declared exit (commit fb4cead + Codex re-audit GO) · 补 Phase A 走 Sprint 3 worker-B7 减半的 1-1.5 周更合理 · 不阻 Sprint 2 启动
- C. **完全 reset Phase B charter v2** — 拒. v2 已 PM ratify (Q-045) + Q-046 接受 Sprint 2 真主线既成事实 · 不再翻 · 避免决策 thrashing
- D. **Sprint 2 + Sprint 3 合并启 (6 worker 同时跑)** — 拒. 反 Q-046 跑偏硬规 #3 (Sprint 边界 mental switch) · 6 worker 主 CLI cron 巡逻 + post-DONE review 容量超载 · cost / 风险 / collision 都不划算
- E. **post-DONE review 4 worker (B1+B4-credit+B4-report+B3) 各 fire 1 次 codex** — 拒. 4 次 fire bg cost 高 · 集成进 1 次 periodic audit (item #3 Q1) 更高 ROI · B3 视觉撤了不需 review

## 8. Critical path 反推 (Sprint 5 demo 4 维 → 现在 1-3 周)

Phase B 验收硬线 #5 (charter line 28): "RM 工作台 1 客户全流程跑通 + 1 个完整 video 录 + 个人画像 POC 跑通 4 维度评价 + 银行客户演示 ready"

Critical path:
1. **RM 工作台 1 客户全流程** = 6 Agent handoff 真串 (Agent6→Agent3→Agent4→Agent5) · **依赖 Phase A 8 硬线 #6 handoff schema** (worker-A6) — 这是 1-3 周必暴露的关键风险
2. **个人画像 POC** = BE12 (Agent1 personal_insight 子域) + BE13 (B7 final POC) · **Sprint 3 才做 · 1-3 周不在 critical path**
3. **video 录 + 银行客户演示** = Sprint 5 主 CLI 自己 + PM · **5 周后 · 不在 1-3 周 critical path**

1-3 周 critical path verdict:
- Sprint 2 B4-alert BE5+BE9 = Agent4 信号质量 + batch — **YES** (RM 工作台需要 Agent4)
- Sprint 2 B4-compliance BE4 = Agent5 policy registry — **YES** (RM 工作台需要 Agent5)
- Sprint 2 B2 BE11 商业化 doc only — **NO 直接 critical path** · 但 Phase B 验收硬线 #2 要求 (`pricing/multi-tenant/trial-flow`-assumptions doc + tenant_id 数据模型 spec)
- **Phase A 8 硬线 #6 handoff schema 真状态** — **真 critical path · 必须 today 暴露**

结论: 1-3 周 plan 在 critical path 上的 ~70% (Sprint 2 三 worker 中 2 个 + #2 现状 doc 暴露 #6 handoff schema 状态) · ~30% 是 enabler 工作 (商业化 doc / audit / cron / onboarding update) · 这个比例合理。

## 9. Dissent appendix

预期 Codex R1 v1 可能推荐 + 我不同意:

1. **Codex 可能推荐 Sprint 2 启动前先做 6 Agent handoff schema (worker-A6 补)** — 我**部分反对**: 启动前应该 *暴露* (item #2 现状 doc) 但 *不补* · 补留 Sprint 3 减半时间。理由: handoff schema 不阻 Sprint 2 三 worker (alert / compliance / biz doc 三个不依赖 handoff schema 完整)。但若 audit verdict 显示 schema 完全空白 (而非 partial) · 可能改主意。
2. **Codex 可能推荐 4 worker (B1+B4-credit+B4-report+B3) 各 fire post-DONE review** — 我反对: cost 4x · 集成 1 次 periodic audit 更高 ROI (item #3)
3. **Codex 可能推荐 monitoring/observability gate 加 Sprint 2** — 我**赞同必要性 · 反对 timing**: 留 Sprint 4 整合时做更合理 · Sprint 2 worker onboarding 已要求 evaluation baseline 跑 (够 first-line)
4. **Codex 可能推荐 Sprint 2 + Sprint 3 合并启 (BE7 提前后腾出 worker capacity)** — 我反对: 反 Q-046 跑偏硬规 #3 · cron + review capacity 超载 · 不值
5. **Codex 可能推荐 R3 codex 仲裁 (插入点 3) 替代 PM 拍** — 我反对: PM 才是 final 拍板 · codex 只产 audit doc 不仲裁产品决策 (codex-mesh-protocol §7 红线)
6. **Codex 可能推荐三 onboarding trailer 不只是 codex 改 manual · 还要加更多 contract reference** — 我可能赞同 · 看 Codex 给的具体 file:line + 哪个 contract

End Round 1 v1.

---

### Your own v1 (codex-v1.md · 你 R1 输出)

# Codex Round 1 · v1 · "下一步 1-3 周 plan" · Independent

## 1. Scope 界定 (≤200 词)
我把“下一步 1-3 周”界定为 Phase B Sprint 2 从启动到收尾，并提前做 Sprint 3 准备。包含：Sprint 2 三 worker 启动、巡检、post-DONE review、合并/deploy；Sprint 1 已 ship 后端的补审；Phase A 可能 partial 项做一次证据化复核；数据飞轮和 decision ledger 加观测 gate；Q-046/Q-047 约束持续执行。不包含：任何视觉/前端审美路线重启，除非 PM 显式 unfreeze；不新建 Agent7 后端；不做真实 multi-tenant 代码实现。证据基线为当前 HEAD `6393249`，历史关键点包括 Phase A exit `fb4cead`、visual reset `413a9ab`、Q-046 `412f516`、Q-047 `f3dc86c`。

## 2. TL;DR (≤150 词)
主 CLI 应先启动 Sprint 2 真主线三 worker：B4-alert、B4-compliance、B2，不再触碰 B3 视觉。并行做三件轻量但必须的治理：对 Sprint 1 已 ship 的 B1/B4-credit/B4-report 做 Codex 恢复后的 sequential post-DONE review；给 `/api/feedback` + decision ledger 加运行观测 gate；把 Phase A #5/#6/#7 用 grep 和文件证据复核，避免“已 exit”里埋 partial。Sprint 2 不应被补审卡死，但 P0/P1 审查发现要 fix-forward 后再打 sprint-end tag。Week 3 预备 Sprint 3：B7 改成 BE13-only，B4-channel/B4-riskctrl 按 charter 原排启动。

## 3. Concrete deliverable (table)
| # | item | owner | 时间 | DoD (file:line / signal) |
|---|---|---|---|---|
| 1 | Sprint 2 启动 preflight：主 CLI 写 resume signal、核对 Q-046/Q-047、确认 launcher 只含 3 后端 worker | 主 CLI | D0 半天 | `NEW-MAIN-CLI-RESUMED` commit；handoff 要求见 `docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-05-02.md:86-126`；Q-047 不启 B3 见 `docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-05-02.md:4-11` |
| 2 | 启动 Sprint 2 三 worker：B4-alert / B4-compliance / B2 | PM 双击 + 主 CLI patrol | D0-D1 | 三个 resume signal：`WORKER-B4-ALERT-RESUMED`、`WORKER-B4-COMPLIANCE-RESUMED`、`WORKER-B2-RESUMED`；真主线来自 `docs/reset/phase-b-charter.md:120-124` 与 Q-046 `docs/handoff/decisions-log.md:2676-2683` |
| 3 | 5 分钟 cron + state-snapshot 纪律 | 主 CLI | D0 起持续 | 每 tick 查 3 worker branch，不扫已 release worker；SOP 见 `docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-05-02.md:59-64`；每 tick 写 state-snapshot 约束见 `docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-05-02.md:221-225` |
| 4 | B2 商业化 doc-only 先收，释放 worker | worker-B2，主 CLI review | Week 1 | 4 docs：pricing / multi-tenant / trial-flow / sales-playbook，见 `docs/onboarding/B2-biz.md:12-31`；绝不动代码见 `docs/onboarding/B2-biz.md:33-39`；DONE `WORKER-B2-BIZ-DOC-DONE` + `DOC-FILES` trailer `docs/onboarding/B2-biz.md:40-47` |
| 5 | B4-compliance BE4：policy registry + diff + reason schema | worker-B4-compliance | Week 1-2.5 | 交付项见 `docs/onboarding/B4-compliance.md:11-36`；red line：不黑名单兜底、不让 LLM 现场 diff、baseline `policy_coverage >=0.85` + `conflict_recall >=0.85`，见 `docs/onboarding/B4-compliance.md:38-45`；DONE `WORKER-B4-COMPLIANCE-POLICY-REGISTRY-DONE` |
| 6 | B4-alert BE5+BE9：signal quality + batch analytics | worker-B4-alert | Week 1-3 | `agent_alert/signal_quality.py`、source confidence、fallback banner、replay、batch scan、clustering，见 `docs/onboarding/B4-alert.md:13-20`；red line：不破 4 步 pipeline、不引入 ML、`signal_diversity >=0.85`，见 `docs/onboarding/B4-alert.md:22-29`；DONE `WORKER-B4-ALERT-SIGNAL-QUALITY-DONE` |
| 7 | Sprint 1 已 ship 后端 post-DONE peer review：B1 / B4-credit / B4-report，sequential | Codex + 主 CLI | D1-D4，不阻塞 Sprint 2 启动 | Review verdict commit/doc 各 1 份；Q-043 要 medium + sequential + trailer，见 `CLAUDE.md:128-135`；B4-credit 重点查 BE2 graph wrapper `agent_credit/decision_engine.py:130-157`；BE7 ledger wrapper `agent_credit/decision_engine.py:159-196`；B4-report SSE audit/key fail-fast `agent_report/api.py:604-658` |
| 8 | 数据飞轮 + decision ledger observability gate | 主 CLI | Week 1 内 | 新增/更新 `docs/runbook/phase-b-observability-gate.md`：记录 feedback jsonl 写入、baseline run、ledger persisted ratio、silent-fail count；ledger 失败隔离与 persisted flag 依据 `shared/decision_ledger/store.py:124-201`；CLAUDE ledger 默认见 `CLAUDE.md:137-155` |
| 9 | Phase A 8 硬线 partial 复核，不阻塞 Sprint 2，但阻塞 Sprint 4 final audit | 主 CLI + Codex | D0-D3 | #5：`rg "--color-brass|--color-ink|letterpress|ink-brush-hr" web/src` 0 命中；硬线定义 `docs/reset/phase-a-charter.md:15`。#6：handoff schema v1.1 存在 `docs/contracts/agent-handoff-schemas.md:1-18`。#7：master + 6 sub PRD 存在，但 master 状态仍 pending PM ratification，见 `docs/prd/master-2026-04-29.md:1-6`，需 PM 标注 done/partial |
| 10 | Sprint 3 prep：更新 onboarding/mesh，B7 改 BE13-only | 主 CLI | Week 3 | Sprint 3 原排见 `docs/reset/phase-b-charter.md:125-128`；BE7 已提前 ship，Q-046 决议“B7 工作量减半”见 `docs/handoff/decisions-log.md:2676-2681`；B7 onboarding 明确只做 BE13 POC glue，估 0.75-1 周 |
| 11 | Sprint 2 closeout：merge、ECS backend deploy、tag、handoff | 主 CLI | Week 3 末 | 三 worker DONE review 后 cherry-pick/merge；backend deploy `--skip-build` 路径见 `docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-05-02.md:128-135`；打 `phase-b-sprint2-end-YYYY-MM-DD`，tag 机制见 `docs/reset/phase-b-charter.md:140-148` |

## 4. 风险 (≤5 个 · 缓解措施)
| # | 风险 | 触发条件 | 缓解 | 缓解 owner |
|---|---|---|---|---|
| 1 | 再次跑偏到非 Sprint 2 worker 或视觉 | PM/worker 提 idle、主 CLI 凭印象派活 | 每次派单前 grep charter；执行 Q-046 五条，见 `docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-05-02.md:34-42` | 主 CLI |
| 2 | Codex review 拖慢 | 单 review >90min 且 CPU=0 | Q-043 fallback manual；但仍保留 review verdict trailer，见 `CLAUDE.md:128-135` | 主 CLI |
| 3 | Ledger silent-fail 掩盖审计断链 | `persisted=false` 或 sqlite error 多次出现 | Week 1 加 observability gate，统计 `ledger_done.persisted`；写入失败不阻塞业务但必须告警 | 主 CLI |
| 4 | Phase A “exit”里 #7 未 ratify | master PRD 仍 pending | Sprint 2 不中断；Sprint 4 final audit 前 PM 明确 done/partial，必要时补一条 decision log | PM + 主 CLI |
| 5 | B4-alert/B4-compliance 为冲指标写规则兜底 | baseline 突升但 fixture 结构不符合 §3.5 | review 强查 fixture 盲测、真实来源、无答案字段；规则见 `CLAUDE.md:52-77` | 主 CLI + Codex |

## 5. DoD (整体 3 周后 PM 看到什么) (≤200 词)
三周后 PM 应看到：Sprint 2 三 worker 全部 DONE、reviewed、merged、backend deployed；B2 四份商业化文档落地且无代码改动；Agent5 policy registry/diff/reason schema 达到 `policy_coverage/conflict_recall >=0.85`；Agent4 signal quality/batch/clustering 达到 `signal_diversity >=0.85`；B1/B4-credit/B4-report 已有 Codex 恢复后的 post-DONE review 结论，P0/P1 已 fix-forward 或明确纳入 Sprint 3/4；`phase-b-sprint2-end-YYYY-MM-DD` tag 存在；state-snapshot 和 decisions-log 记录 Sprint 2 过程；Sprint 3 onboarding 已按 BE7 提前完成事实更新。

## 6. 不做的事 (反 Q-046 5 跑偏) (≤200 词)
不启 B3，不改视觉，不问 F4 v2 verdict；Q-047 已冻结视觉，见 `docs/handoff/decisions-log.md:2703-2730`。不把 B1/B4-credit/B4-report release worker 拉回来加新功能，只做审查和必要 fix-forward。不把 B2 doc-only 扩成 multi-tenant 代码实现，red line 见 `docs/onboarding/B2-biz.md:33-39`。不做 ML/embedding clustering，B4-alert 明确用 deterministic jaccard，见 `docs/onboarding/B4-alert.md:24-25`。不为 baseline 指标写黑名单/关键词兜底，CLAUDE 反模式见 `CLAUDE.md:27`。不把 Phase A partial 复核变成阻塞 Sprint 2 的大返工。

## 7. 替代方案 evaluated rejected (≥3 个 · 理由) (≤300 词)
1. **先停 Sprint 2，补完 Sprint 1 全量审查再启动**：拒绝。Sprint 2 三 worker 是 charter 真主线，且 B2/B4-alert/B4-compliance 不依赖 Sprint 1 review 全完成；补审只应阻塞发现的 P0/P1 merge/deploy。

2. **继续做视觉或恢复 B3 B-3 phase**：拒绝。Q-047 明确 visual freeze，launcher 已删 B3，见 `docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-05-02.md:6-10`。

3. **把 B2 升级为真实多租户实现**：拒绝。BE11 的价值是商业化假设和 architecture spec，真实隔离进 Phase C；现在改 DB/RBAC 会扩大风险且偏离 `docs/onboarding/B2-biz.md:35-38`。

4. **等 Sprint 4 再看 Phase A partial**：拒绝。#5/#6/#7 复核只需半天级别，早发现不早返工，特别是 master PRD 当前仍写 pending PM ratification `docs/prd/master-2026-04-29.md:3`。

## 8. Critical path 反推 (Sprint 5 demo 4 维 → 现在 1-3 周) (≤300 词)
Sprint 5 demo 要的是 6 Agent 端到端链路 + POC 4 维评价，Phase B exit 写明画像 35%、产品适配 25%、经营策略 20%、性能 20%，见 `docs/reset/phase-b-charter.md:160-165`。现在 1-3 周在 critical path 上的是 B4-alert、B4-compliance、B2 和 observability gate。

B4-alert 支撑贷中监控、批量扫描、模式聚类，是经营策略和产品适配的证据来源；没有它，Agent4 仍像单点 showroom。B4-compliance 支撑政策事件驱动和可复核 violation reason，是银行客户“不敢追责”的关键。B2 不直接跑 demo 链路，但给 Sprint 5 POC 话术、pricing、trial flow、multi-tenant 边界提供 sales-ready 外壳。Sprint 1 补审和 ledger/flywheel monitoring 是 demo 的可信度底座：BE2 graph、BE3 material gap、BE7 ledger、BE10 feedback 如果不可观测，demo 只能“能跑”，不能证明“可审计、可复盘、可持续改进”。

Phase A #5/#6/#7 复核是平行治理，不是 Sprint 2 功能 critical path，但会阻塞 Sprint 4 final audit 和 Sprint 5 对外可信度。

## 9. Dissent appendix (≤300 词)
我预期 main CLI 会推荐“立即启动三 worker + cron + 等 DONE 后 manual/Codex review + Sprint 3 接着干”，并可能把 Sprint 1 补审、Phase A partial 复核、observability gate 放到 Sprint 2 之后。我不同意把这三项后置到 Week 3 末：它们都很轻，但能防止 Q-046 类跑偏再次发生。尤其 B1 flywheel 和 BE7 ledger 都已经 ship，若没有 persisted/feedback 可观测信号，后面 Sprint 5 demo 会在“可信审计”上补洞。

我也预期 main CLI 会更强调“不阻塞速度”。我同意不阻塞启动，但不同意“不阻塞”被解释成“不审”。我的方案是：Sprint 2 照启，review sequential 插空跑；只让 P0/P1 阻塞 merge/deploy，不让审查阻塞 worker 开工。

最后，我不会建议视觉路线任何复活。即使主 CLI 认为前端 0% 会影响 demo，也应等 PM 明确 unfreeze 后重开独立视觉 plan，而不是在本 1-3 周偷改 UI。
---

## Output schema (verbatim)

```markdown
# Codex Round 2 · v2 · "下一步 1-3 周 plan" · Cross-Critique

## 1. R1 双方共识 (v2 不动)
<list >5 个 main CLI v1 + 你 v1 都同意的项 · 直引 v1 file:line>

## 2. 改 (你 v1 错了 / 不够好 · R2 改)
<≥3 项 · 每项: 我 v1 / Main CLI v1 / Main CLI 论点 / 我 R2 改的理由>

## 3. 坚持 (你 v1 对的 · R2 坚持)
<≥3 项 · 每项: 论证 main CLI v1 没 catch 但你坚持的不让步项>

## 4. Main CLI v1 弱点
<≥3 项 · file:line / 推理漏洞 / Q-046 跑偏类比>

## 5. 吸收 main CLI (R2 真接受)
<table: # / main CLI v1 项 / 吸收方式>

## 6. v2 Final Plan
### 6.1 Concrete Deliverable (融合 v1 双方 + R2 改)
| # | item | owner | 时间 | DoD |
### 6.2 风险
### 6.3 DoD (3 周后 PM 看到)
### 6.4 不做的事 (反 Q-046)
### 6.5 替代方案 rejected
### 6.6 Critical path 反推

## 7. v2 Dissent (R3 用 · 不强行收敛)
<≥3 项你预期 main CLI v2 持不同立场的点 · R3 仲裁 input>
```

≤ 4000 词。Begin.
