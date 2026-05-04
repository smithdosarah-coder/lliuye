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