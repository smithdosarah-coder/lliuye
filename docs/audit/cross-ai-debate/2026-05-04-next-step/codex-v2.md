# Codex Round 2 · v2 · "下一步 1-3 周 plan" · Cross-Critique

> 作者: Codex Round 2 · 2026-05-04 · 已读 `main-cli-v1.md` + `codex-v1.md`；未读并行 `main-cli-v2.md`。R1 fire 基线 `6393249`；本轮 spot-check 发现新 HEAD `b63c308` (`chore(debate): R2-START · main-cli-v2 + codex-R2-prompt fire bg`)。

## 1. R1 双方共识 (v2 不动)

- **时间窗一致**: 都把 1-3 周界定为 2026-05-04 到约 2026-05-25、覆盖 Sprint 2 启动/进展/收尾与 Sprint 3 prep；见 `docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:8`、`docs/audit/cross-ai-debate/2026-05-04-next-step/codex-v1.md:4`。
- **Sprint 2 三 worker 是真主线**: 都主张 B4-alert、B4-compliance、B2 启动，不启 B3；见 `docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:22`、`docs/audit/cross-ai-debate/2026-05-04-next-step/codex-v1.md:7`。外部证据是 Q-046 `docs/handoff/decisions-log.md:2664` 和 HANDOFF v3 `docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-05-02.md:7`。
- **视觉冻结不碰**: 双方均排除视觉路线，除非 PM 显式 unfreeze；见 `docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:10`、`docs/audit/cross-ai-debate/2026-05-04-next-step/codex-v1.md:37`。Q-047 来源 `f3dc86c`，决策 entry 在 `docs/handoff/decisions-log.md:2707`。
- **Codex review 要 sequential + medium + trailer**: 双方都接受 Q-043 v2 作为 review 规则；见 `docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:24`、`docs/audit/cross-ai-debate/2026-05-04-next-step/codex-v1.md:18`。规范证据 `CLAUDE.md:128`、`CLAUDE.md:130`。
- **Phase A partial 要证据化复核**: 双方都点名 #5/#6/#7，尤其 handoff schema 与 PRD master；见 `docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:23`、`docs/audit/cross-ai-debate/2026-05-04-next-step/codex-v1.md:20`。spot-check 证实 PRD master 仍 `pending PM ratification`，见 `docs/prd/master-2026-04-29.md:3`。
- **B2 是 doc-only，不做 multi-tenant 代码**: 双方一致禁止 B2 扩成实现；见 `docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:23`、`docs/audit/cross-ai-debate/2026-05-04-next-step/codex-v1.md:37`。onboarding 红线是 `docs/onboarding/B2-biz.md:35`。
- **Sprint 3 要吸收 BE7 提前完成事实**: 双方都要求 B7 工作量减半/改 BE13-only；见 `docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:26`、`docs/audit/cross-ai-debate/2026-05-04-next-step/codex-v1.md:21`。charter 旧排程仍写 B7 包 BE7+BE13，见 `docs/reset/phase-b-charter.md:103`、`docs/reset/phase-b-charter.md:106`。
- **cron / state-snapshot 纪律必须守**: 双方都要 5 min patrol 与留痕；见 `docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:21`、`docs/audit/cross-ai-debate/2026-05-04-next-step/codex-v1.md:14`。HANDOFF SOP 在 `docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-05-02.md:60`。

## 2. 改 (你 v1 错了 / 不够好 · R2 改)

1. **我 v1**: 把 Sprint 1 B1/B4-credit/B4-report 各自 post-DONE review 列成 D1-D4 独立工作，见 `docs/audit/cross-ai-debate/2026-05-04-next-step/codex-v1.md:18`。**Main CLI v1**: 合进一次 pre-Sprint-2 periodic audit，见 `docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:24`。**Main CLI 论点**: 4 次 fire cost 高，集中回答 Sprint 1 BE drift 更高 ROI，见 `docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:96`。**我 R2 改**: 接受“先集中 audit、发现 P0/P1 再拆 review”。原因是 Q-043 明确 sequential 1 bg at a time (`CLAUDE.md:130`)，而 Sprint 2 启动不能被审查队列反向卡死。
2. **我 v1**: Phase A 复核只列 #5/#6/#7，见 `docs/audit/cross-ai-debate/2026-05-04-next-step/codex-v1.md:20`。**Main CLI v1**: 要 8 硬线逐条 yes/partial/no，见 `docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:23`。**Main CLI 论点**: Q-046 跑偏本质是“凭印象认为已 OK”，必须全量证据化。**我 R2 改**: 接受全 8 项状态 doc；我原方案会漏掉非 #5/#6/#7 的 latent partial，治理颗粒度不够。
3. **我 v1**: 把 observability gate 直接列为 Week 1 deliverable，见 `docs/audit/cross-ai-debate/2026-05-04-next-step/codex-v1.md:19`。**Main CLI v1**: 赞同必要性但反对 timing，倾向 Sprint 4，见 `docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:100`。**Main CLI 论点**: Sprint 2 onboarding 已要求 baseline，先别给 worker 增加横向 gate。**我 R2 改**: 降级为“观测设计 + audit checklist”，不要求 Week 1 改代码；但仍保留 ledger/flywheel 最小观测项进入 periodic audit。
4. **我 v1**: 用 `WORKER-B2-BIZ-DOC-DONE`，见 `docs/audit/cross-ai-debate/2026-05-04-next-step/codex-v1.md:15`。**Main CLI v1**: 用 `WORKER-B2-BIZ-DONE`，见 `docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:23`。**Main CLI 论点**: 与自身 flow 简化一致。**我 R2 改**: 坚持以实际 onboarding 为准，即 `WORKER-B2-BIZ-DOC-DONE` (`docs/onboarding/B2-biz.md:42`)，但 v2 plan 会显式兼容 alias，避免 cron 漏信号。

## 3. 坚持 (你 v1 对的 · R2 坚持)

1. **坚持 ledger/flywheel 可观测不能等到 Sprint 4 才第一次出现**。Main CLI v1 把 observability timing 后置到 Sprint 4 (`docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:100`)，但 Phase B charter 把数据飞轮 gate 列为验收硬线 #1 (`docs/reset/phase-b-charter.md:23`)，CLAUDE 已把 cross-agent decision ledger defaults 固化 (`CLAUDE.md:137`)。v2 不要求 Week 1 改代码，但要求 Week 1 audit checklist 有 `feedback jsonl / baseline run / ledger persisted ratio / silent-fail count`，否则 Sprint 5 demo 只能说“能跑”，不能说“可审计”。
2. **坚持 B2 doc-only DONE signal 以 onboarding 为准**。Main CLI v1 的 `WORKER-B2-BIZ-DONE` (`docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:23`) 与 worker doc 不一致；真实要求是 `WORKER-B2-BIZ-DOC-DONE` + `DOC-FILES` trailer (`docs/onboarding/B2-biz.md:42`、`docs/onboarding/B2-biz.md:46`)。Q-046 类跑偏经常从信号名“差不多”开始，cron 必须匹配真实 worker 输出。
3. **坚持 review 不能只等 worker DONE 后才看 Sprint 1 drift**。Main CLI v1 的 periodic audit方向对，但其 closeout DoD 没明确 P0/P1 fix-forward gate；我 v1 写了 “P0/P1 已 fix-forward 或纳入 Sprint 3/4”，见 `docs/audit/cross-ai-debate/2026-05-04-next-step/codex-v1.md:34`。v2 继续坚持：集中 audit 可以，但 P0/P1 不能被“成本高”吞掉。
4. **坚持文件状态不能被 commit exit 盖过**。Phase B charter 说 Phase A 全过 (`docs/reset/phase-b-charter.md:5`)，但 contract 自述 v1.1 fixture 仍是 placeholder (`docs/contracts/agent-handoff-schemas.md:17`)，PRD master 仍 pending PM ratification (`docs/prd/master-2026-04-29.md:3`)。我的 v1 对 #6/#7 的怀疑成立，只是 v2 改成全 8 项复核。

## 4. Main CLI v1 弱点

1. **信号名与 worker doc 不一致**: Main CLI v1 写 `WORKER-B2-BIZ-DONE` (`docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:23`)，真实 onboarding 是 `WORKER-B2-BIZ-DOC-DONE` (`docs/onboarding/B2-biz.md:42`)。这是 Q-046 同类风险：用“印象信号”巡逻，worker DONE 后可能扫不到。
2. **把 old worker branch 完全不扫，可能漏 Sprint 1 post-ship fix-forward**: Main CLI v1 说“4 旧 worker branch 已 release 不扫” (`docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:21`)。如果 pre-Sprint-2 audit 发现 B1/B4-credit/B4-report P0/P1，需要临时扫相关 fix-forward branch；否则“release”会变成免审护身符。
3. **observability timing 过晚**: Main CLI v1 明确反对 Sprint 2 observability gate (`docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:100`)；但 BE10 data flywheel 已是 Phase B gate (`docs/reset/phase-b-charter.md:23`)，BE7 ledger 是痛点底座 (`CLAUDE.md:152`)。这不是加功能，是避免 silent regression 的最小仪表盘。
4. **ECS deploy 说法过粗**: Main CLI v1 对 B4-compliance/B4-alert 都写 “ECS deploy --skip-build” (`docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:28`、`docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:30`)。HANDOFF 只说明后端 deploy 路径 (`docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-05-02.md:127`)，但具体服务 restart/healthcheck 要按 touched service 决定，不能在计划里默认“restart compliance service”就覆盖 Agent4。
5. **对 handoff schema 的“partial 但不阻 Sprint 2”判断需要条件化**: Main CLI v1 说若 partial 留 Sprint 3 补 (`docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:42`)。我同意一般情况，但若 #6 缺的是 Agent4/Agent5 与 demo链路字段，而 Sprint 2 正在改这两个 agent，就应追加 contract reference 到 onboarding/trailer，不等 Sprint 3。

## 5. 吸收 main CLI (R2 真接受)

| # | main CLI v1 项 | 吸收方式 |
|---|---|---|
| 1 | 三 onboarding trailer `manual` → `codex`，见 `docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:18` | 纳入 D0 preflight；但同时修正 DONE signal alias，避免只改 trailer 不改巡逻规则。 |
| 2 | Phase A 8 硬线状态 doc，见 `docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:23` | 从我 v1 的 #5/#6/#7 扩为全 8 项 yes/partial/no + evidence + commit sha。 |
| 3 | Pre-Sprint-2 Codex periodic audit，见 `docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:24` | 替代我 v1 的三次 Sprint 1 单独补审；仅对 P0/P1 再拆 post-DONE review。 |
| 4 | 不补完 Phase A 再启 Sprint 2，见 `docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:88` | 接受；Phase A status doc 只阻塞重大 contract 误派，不作为 Sprint 2 全停条件。 |
| 5 | Sprint 3 charter v2.2 prep，见 `docs/audit/cross-ai-debate/2026-05-04-next-step/main-cli-v1.md:26` | 纳入 Week 2 起草；B7 改 BE13-only，PM verify 后才派 Sprint 3。 |

## 6. v2 Final Plan

### 6.1 Concrete Deliverable (融合 v1 双方 + R2 改)

| # | item | owner | 时间 | DoD |
|---|---|---|---|---|
| 1 | R2 后 resume baseline 固化 | 主 CLI | D0 | 记录 HEAD `b63c308` 已发生；后续任何行动基于 `6393249` R1 fire + `b63c308` R2 start 双基线，不读并行 main-cli v2。 |
| 2 | 三 onboarding trailer + signal 修正 | 主 CLI | D0 30 min | `docs/onboarding/B4-alert.md:33`、`docs/onboarding/B4-compliance.md:50`、`docs/onboarding/B2-biz.md:43` 的 `REVIEW-MODE: manual` 改为 `codex` 或加“codex resumed”；cron 同时识别 `WORKER-B2-BIZ-DOC-DONE` (`docs/onboarding/B2-biz.md:42`) 与旧 alias。commit signal `ONBOARDING-TRAILER-UPDATE-CODEX-RESUMED`。 |
| 3 | Phase A 8 硬线状态 doc | 主 CLI | D0 1-2 hr | 新建 `docs/audit/phase-a-status-2026-05-04.md`：8 项 yes/partial/no + evidence file:line + commit sha；重点 #5 visual after Q-047、#6 handoff schema v1.1 placeholder (`docs/contracts/agent-handoff-schemas.md:17`)、#7 PRD pending (`docs/prd/master-2026-04-29.md:3`)。 |
| 4 | Pre-Sprint-2 Codex periodic audit | 主 CLI fire Codex | D0 60-90 min | `docs/audit/codex-periodic/2026-05-04-phase-b-pre-sprint2.md` + commit `CODEX-PERIODIC-AUDIT-2026-05-04-DONE`；回答 Sprint 1 BE drift、Sprint 2 onboarding clarity、Sprint 3 BE7 adjustment、Phase A 8 status、ledger/flywheel min-observability checklist。 |
| 5 | 启 5 min cron / patrol | 主 CLI | D0 起 | 每 tick 扫 3 active branch：`feat/phase-b4-alert`、`feat/phase-b4-compliance`、`feat/phase-b2-biz`；不常规扫旧 release branch，但 audit P0/P1 出现时临时加入 fix-forward branch；按 HANDOFF SOP `docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-05-02.md:60`。 |
| 6 | PM 启 Sprint 2 三 worker | PM + 主 CLI | D0 audit 后 | 只启 B4-alert、B4-compliance、B2；不启 B3。三 resume signal：`WORKER-B4-ALERT-RESUMED`、`WORKER-B4-COMPLIANCE-RESUMED`、`WORKER-B2-RESUMED`。 |
| 7 | B2 BE11 doc-only 收口 | worker-B2 + 主 CLI | Week 1 | 交付 `docs/biz/pricing-assumptions.md`、`multi-tenant-assumptions.md`、`trial-flow-assumptions.md`、`sales-playbook-v1.md`；不动代码 (`docs/onboarding/B2-biz.md:35`)；DONE `WORKER-B2-BIZ-DOC-DONE` + `DOC-FILES` trailer。 |
| 8 | B2 post-DONE Codex review + merge | 主 CLI + Codex | Week 1 | `docs/audit/codex-reviews/WORKER-B2-BIZ-DOC-DONE.md`；verdict `AGREE/DISAGREE/NEED-MORE-INFO`；AGREE 后 cherry-pick main；doc-only 不 ECS deploy。 |
| 9 | B4-compliance BE4 | worker-B4-compliance | Week 1-2.5 | Policy registry + version diff + reason schema；baseline `policy_coverage >=0.85` + `conflict_recall >=0.85` (`docs/onboarding/B4-compliance.md:45`)；DONE `WORKER-B4-COMPLIANCE-POLICY-REGISTRY-DONE`。 |
| 10 | B4-alert BE5+BE9 | worker-B4-alert | Week 1-3 | Signal quality + source confidence + fallback banner + replay + batch analytics + deterministic clustering；baseline `signal_diversity >=0.85` (`docs/onboarding/B4-alert.md:27`)；DONE `WORKER-B4-ALERT-SIGNAL-QUALITY-DONE`. |
| 11 | Worker DONE review / merge / backend deploy | 主 CLI + Codex | 各 DONE 后 | 每 worker 按 Q-043 medium sequential review (`CLAUDE.md:130`)；P0/P1 fix-forward 后 merge；B4 后端改动按 touched service deploy + healthcheck，不对 B2 deploy。 |
| 12 | Ledger/flywheel min-observability design | 主 CLI | Week 1-2 | 不强制新代码；在 audit/runbook 记录 `/api/feedback` jsonl、6-agent baseline、ledger persisted ratio、silent-fail count；若 Sprint 1 audit 已有现成指标则接入 `docs/runbook/phase-b-observability-gate.md`。 |
| 13 | Sprint 3 charter v2.2 + onboarding 草稿 | 主 CLI | Week 2-3 | 更新 `docs/reset/phase-b-charter.md`：BE7 已提前、B7 改 BE13-only 0.75-1w、B4-channel/B4-riskctrl/B7-final onboarding 草稿；PM verify 后才派 Sprint 3。 |
| 14 | Sprint 2 closeout tag + handoff | 主 CLI | Week 3 末 | 三 worker reviewed/merged/deployed as applicable；`phase-b-sprint2-end-YYYY-MM-DD` tag（tag 规范 `docs/reset/phase-b-charter.md:156`）；decisions-log Q-048+ 与 state-snapshot Day 3-21 完整。 |

### 6.2 风险

| # | 风险 | 触发条件 | 缓解 |
|---|---|---|---|
| 1 | Q-046 式跑偏复发 | 启 B3/视觉/非 Sprint 2 worker | 每次派单前 grep charter；Q-047 freeze (`docs/handoff/decisions-log.md:2707`)；STOP 5s。 |
| 2 | DONE signal 漏扫 | B2 输出 doc signal、cron 等旧 alias | 以 onboarding `WORKER-B2-BIZ-DOC-DONE` 为主，兼容 `WORKER-B2-BIZ-DONE`。 |
| 3 | Codex quota/卡死 | review >90min CPU=0 | Q-043: medium、sequential、manual fallback + trailer (`CLAUDE.md:130`)。 |
| 4 | Handoff schema partial 影响 Sprint 2 | Agent4/Agent5 字段缺失但 worker 已改实现 | D0 status doc 条件化：若缺 Sprint 2 直接相关字段，补 contract reference 到 onboarding，不等 Sprint 3。 |
| 5 | Silent regression | feedback/ledger 写入失败但 demo 继续 | Week 1-2 min-observability checklist；P0/P1 才阻塞 merge/deploy。 |

### 6.3 DoD (3 周后 PM 看到)

- Sprint 2 三 worker DONE、Codex reviewed、merged；B4-alert/B4-compliance 按服务 healthcheck 部署，B2 doc-only 不部署。
- `docs/audit/phase-a-status-2026-05-04.md` 与 `docs/audit/codex-periodic/2026-05-04-phase-b-pre-sprint2.md` 留底，所有 yes/partial/no 有 file:line + commit sha。
- B2 四份商业化 doc 完成且无代码改动；B4-compliance 达 `policy_coverage/conflict_recall >=0.85`；B4-alert 达 `signal_diversity >=0.85`。
- Sprint 1 BE drift 已集中审；P0/P1 已 fix-forward 或明确写入 Sprint 3/4。
- Sprint 3 charter v2.2 + onboarding 草稿 ready；B7 已改 BE13-only；`phase-b-sprint2-end-YYYY-MM-DD` tag、state-snapshot、decisions-log Q-048+ 完整。

### 6.4 不做的事 (反 Q-046)

- 不启 B3、不改视觉、不问 F4 v2、不做任何 visual route，除非 PM 明确 unfreeze。
- 不把 B2 doc-only 扩成 tenant_id/RBAC/DB 代码实现。
- 不把 Sprint 1 release worker 拉回做新功能；只在 audit P0/P1 时做 fix-forward。
- 不并发 Codex review；不 xhigh；不省 verdict trailer。
- 不提前派 Sprint 3 worker；只写 charter/onboarding 草稿。
- 不把 Phase A status doc 变成大返工借口；只对 Sprint 2 直接字段缺失做小补。

### 6.5 替代方案 rejected

1. **直接启 Sprint 2、不做任何 audit** — 拒绝。Q-046 已证明“凭印象”会跑偏；D0 audit 是 1-2 小时换 3 周风险下降。
2. **Phase A 全补完再启 Sprint 2** — 拒绝。Phase A exit 已有 `fb4cead`，多数 partial 不阻 B2/B4；只对 Sprint 2 直接 contract 缺口做小补。
3. **三次 Sprint 1 单独 post-DONE review 先跑完** — 拒绝。Q-043 sequential 限制下成本太高；先 periodic audit，P0/P1 再拆。
4. **observability 完全等 Sprint 4** — 拒绝。可以不改代码，但不能不定义 checklist；BE10/BE7 是 demo 可信底座。
5. **Sprint 2 + Sprint 3 合并启** — 拒绝。违反 Sprint 边界 mental switch，cron/review capacity 超载。

### 6.6 Critical path 反推

Sprint 5 demo 需要 RM workbench 的 6 Agent 闭环、可审计证据链、个人画像 POC、银行客户演示 ready。North star 明确 RM→Agent1→Agent6→Agent3→Agent4→Agent5 闭环 (`docs/reset/north-star.md:35`、`docs/reset/north-star.md:52`)；Phase B 要求数据飞轮、商业化 doc、6 Agent 后端能力、decision ledger、个人画像 POC (`docs/reset/phase-b-charter.md:23`、`docs/reset/phase-b-charter.md:24`、`docs/reset/phase-b-charter.md:26`、`docs/reset/phase-b-charter.md:163`)。

因此 1-3 周最关键的是：B4-alert 让 Agent4 从单点 showroom 变成贷中监控/批量扫描能力；B4-compliance 让 Agent5 产生可复核 policy diff/reason；Phase A #6 handoff schema 状态必须曝光，因为 contract 自述 fixture placeholder (`docs/contracts/agent-handoff-schemas.md:17`)；B2 虽不直接串链路，但提供 trial/pricing/tenant 边界和 sales playbook；ledger/flywheel 最小观测保证 demo 可复盘。视觉继续为 0 不是本周期问题，Q-047 已冻结。

## 7. v2 Dissent (R3 用 · 不强行收敛)

1. **Observability timing**: 我坚持 Week 1-2 至少形成 checklist/runbook；预期 Main CLI v2 仍会主张留 Sprint 4。R3 需裁定“设计级 gate 是否算偏离 Sprint 2”。
2. **Sprint 1 review granularity**: 我接受 periodic audit 先行，但坚持 P0/P1 必须拆 review/fix-forward；预期 Main CLI v2 可能仍认为只需 Q1 汇总。R3 需裁定 P0/P1 gate 表述强度。
3. **Handoff schema partial 的处理条件**: 我主张若缺 Agent4/Agent5 相关字段，应立即给 Sprint 2 onboarding 加 contract reference；Main CLI v1 倾向留 Sprint 3。R3 需按 Phase A status doc 的真实结果裁定。
4. **DONE signal 正名**: 我坚持 `WORKER-B2-BIZ-DOC-DONE` 为主信号；若 Main CLI v2 为统一口径继续用 `WORKER-B2-BIZ-DONE`，R3 应以 `docs/onboarding/B2-biz.md:42` 为 source of truth。
5. **ECS deploy phrasing**: 我反对“一律 --skip-build + restart compliance service”这种计划级简化；R3 需确认按 touched service healthcheck 写入 handoff，避免 Agent4/Agent5 部署命令混淆。
