# Batch 2 · 4 Worker Kickoff Prompts

> **定位**：Batch 2 正式派发。4 轨并行——code-urgent（证据链前端化）/ code-arch（Agent1/5 外部搜索补全）/ evaluation（真基线重跑 + EV-12）/ data-foundation（Agent4 预警 mock）。每个 worker 先 ACK → 读 onboarding → 按 Task 顺序独立 commit 带 Signal trailer → 收尾 `READY-FOR-<X>-B2-REVIEW`。
>
> **Batch 2 启动前提**：Batch 1 全 APPROVED 已合流 main（含 data-foundation v2 APPROVED + 3 Holding task APPROVED）+ Product Hardening Phase 1 全部落地。当前 4 worker 分支已具备 Batch 2 基座（Batch 1 merge tips 可见）。
>
> **粘发时机**：各 worker 只在主 CLI 发 `Signal: BATCH-2-DISPATCHED` 的 commit 落 main **之后**才粘对应 kickoff；提前粘会撞 Batch 1 review 尾流。worker 先 `git fetch origin main` 确认 dispatch commit sha 可见，再 ACK。
>
> **生效前提**：4 条 Batch 1 分支（feat/code-urgent / feat/code-arch / feat/evaluation / feat/data-foundation）均已合流 main，`b412656` / `a42f432` / `50cdbb1` / `e4f23b5` 等 merge tip 可 `git log origin/main --grep` 查到。4 worker Batch 2 期间并行推进，无跨 worker 串行依赖（code-arch B2 Task C oracle 对 evaluation Task C 是软依赖，走 stub 分支不卡流）。

---

## ① code-urgent · Batch 2 · 证据链前端化

```
你是 code-urgent worker CLI · Batch 2。先 ACK 再动手。

【Step 0 · ACK】
1) git fetch origin chore/l0-infra && git log origin/chore/l0-infra -10
2) 读 docs/handoff/decisions-log.md 中 Q-029(Batch 2 派发决策)
3) 读 docs/onboarding/batch-2-code-urgent-evidence-frontend.md 全文
4) 读 shared/evidence/protocol.py 确认 AuditReport.to_dict() shape(source/snippet/ref_id/confidence/meta + unfilled_fields)
5) commit 一条 doc-only(空改动或补一行 ACK 备注),trailer `Signal: BATCH-2-CU-ACK`

【Step 1 · Task A · archive evidence UI 组件】
- 新建 web/src/components/evidence/ 下 EvidenceTrail.tsx / EvidencePopover.tsx / types.ts / EvidenceContext.tsx
- 6 archive workspace 挂 <EvidenceTrail>;web/src/lib/api.ts SSE type 扩 evidence_trail + unfilled_fields
- tests/evidence-trail.spec.ts 5 case(空/多源/低置信/popover 开关/pdf 跳页)
- cd web && npx tsc --noEmit 0 error && npm run build 0 error
- 独立 commit · `Signal: ARCHIVE-EVIDENCE-UI-DONE`

【Step 2 · Task B · 高亮卡系统】
- 新建 HighlightCard.tsx / claimParser.ts / evidence.css;复用 EvidenceContext
- 6 workspace 正文 render pass 改 claimParser.renderWithHighlights;后端无 [ref:] 锚点要降级不报错
- 扩 spec 3 case(有锚点 / 无锚点 / ref_id 缺失降级)
- 独立 commit · `Signal: HIGHLIGHT-CARD-UI-DONE`

【Step 3 · Task C · 未填标记 UI】
- 新建 UnfilledMarker.tsx / unfilled.css;6 workspace 字段 render check unfilled_fields
- fallback.ts audit 去掉 "未知字段填 0/空" 兜底
- tests/unfilled-marker.spec.ts 4 case
- 独立 commit · `Signal: UNFILLED-MARKER-UI-DONE`

【红线】
只动 web/src/app/archive/*/_components/ + web/src/components/evidence/(新) + web/src/lib/api.ts + web/src/lib/fallback.ts。
不动 backend(agent_*/api_server.py/shared/*.py/v16_*.py);不动 Agent6;不动 data/mock/ + evaluation/;不动 store/ + shell/;不动 legacy 顶层路由 /channel /credit /alert /compliance /report /riskctrl。
每 Task 独立 commit。blocker 立即喊停,不绕过。

【Final】
三 Task 全绿 → commit trailer `Signal: READY-FOR-CODE-URGENT-B2-REVIEW`。

开干。
```

---

## ② code-arch · Batch 2 · Agent1/5 外部搜索能力补全

```
你是 code-arch worker。Batch 2 · Agent1/5 外部搜索能力补全。

[ACK step]
先用一句话 ACK 你已进入 Batch 2 + 理解你要做的事,禁止直接写代码。

[强制前置]
1. cd 到 worktree root (`D:/claude code/demo-code-arch`)
2. git fetch upstream && git status(确认干净 + 在 feat/code-arch 上)
3. 读决策:git log --all --oneline --grep='Q-029' — 读完 Q-029/A-029 全文
4. 读 onboarding:docs/onboarding/batch-2-code-arch-external-search.md(整篇)
5. 读 §3.5 环境边界:git show 40f653f -- CLAUDE.md 或 grep '§3\.5\|env-boundary' CLAUDE.md
6. 读现状:ls shared/sources/impls/ && ls agent_channel/domains/ && ls agent_compliance/domains/ && ls data/mock/channel-kb/ && ls data/mock/compliance-kb/
7. 跑 test_sources_smoke.py 确认环境 OK

[执行顺序]
严格 Task A → B → C 顺序,不并行,每 Task 独立 commit:
- Task A: Agent1 SearchProvider 接 Tavily + look-alike → commit → trailer `Signal: AGENT1-EXTERNAL-SEARCH-DONE`
- Task B: Agent5 SearchProvider 接银保监/央行 + 冲突比对 → commit → trailer `Signal: AGENT5-POLICY-COMPARE-DONE`
- Task C: integration test + evaluation adapter plug-in → commit → trailer `Signal: BATCH-2-INTEGRATION-TEST-DONE`

每 Task 完成前必须:
(a) `pytest tests/<agent>/<test>.py -v` 绿
(b) `git diff --name-only b412656..HEAD` 自查 scope 收敛(红线第 1 条)
(c) commit message 用英文,简洁说明 why + 影响面

[红线]
- 只动 agent_channel/ + agent_compliance/ + shared/sources/impls/ + tests/ + evaluation/runner/adapters/{agent1_channel,agent5_compliance}.py + evaluation/{agent1_channel,agent5_compliance}.yaml
- 不动 web/ / agent_report/ / agent_credit/ / financial_analyzer* / quality_scorer* / truth_fill* / v16_* / data/mock/
- 不动 evaluation/runner/base_evaluator.py / cli.py
- CompanyProfile / ConflictItem 对外 schema 只加字段不删改

[中途不请示]
Blocker 定义:环境不可达(Tavily key 缺 + gov_cn 双路全挂)/ 数据契约冲突 / 红线真被逼触碰。非 blocker 一律不请示,一口气跑到底。

[最终]
3 Task Signal 都打完之后,在 feat/code-arch 顶 HEAD 加一个 review-ready commit:
  Signal: READY-FOR-CODE-ARCH-B2-REVIEW
  body 附 3 commit SHA + git diff --name-only b412656..HEAD + 硬指标自检结论

开干.
```

---

## ③ evaluation · Batch 2 · 真基线重跑 + EV-12 跨 Agent 一致性

```
你是 evaluation worker CLI。worktree 在 D:/claude code/demo-evaluation,分支 feat/evaluation。
请读 AGENT_IDENTITY.md 和里面列的所有文件(onboarding / decisions-log / contracts / 最近
signal commit)resume 状态。本批次进 Batch 2,onboarding 单是:
docs/onboarding/batch-2-evaluation-real-baseline.md

总目标:用 data-foundation v2 真脏数据(data/mock/deep-pillar/DP001-005 + channel-kb/
+ compliance-kb/)重跑 6 Agent 基线 + 解锁 EV-12 跨 Agent 财务比率一致性 + Agent1/5 精
确度召回指标。3 个 Task 顺序跑,每 Task 独立 commit 带 Signal trailer。

红线:只动 evaluation/ 和 evaluation/baselines/,不动 v16_* / agent_*/ / data/mock/ / rubric
schema。EV-12 跨 Agent 是消费 financial_analyzer 只读不改。依赖 code-arch Batch 2
oracle 若未到位,Task C 走 stub 分支推进,不卡 Task A/B。

全部 Task 完成后 commit Signal: READY-FOR-EVALUATION-B2-REVIEW。

Resume 完汇报:当前 phase / 已理解的 3 Task 范围 / 准备先跑哪个 Task / 有无 blocker,
然后停下等我 GO。
```

---

## ④ data-foundation · Batch 2 · Phase 2 Agent4 预警 mock

```
你是 data-foundation worker · Batch 2 · Phase 2 Agent4 mock。

【第一步】Resume doc-only commit,trailer `Signal: PRODUCT-HARDENING-BATCH-2-DF-P2-ACK`,仅记录"已接收 Phase 2 onboarding,准备开工"即可。

【第二步】强制 onboarding:
1. git fetch origin chore/l0-infra
2. git log origin/chore/l0-infra --format='%h %s' -15
3. 读 docs/handoff/decisions-log.md Q-028/A-028(环境边界反 5 原则)+ Q-029/A-029(Batch 2 四轨 + 测试豁免)
4. 读 docs/onboarding/batch-2-data-foundation-phase-2.md 全文
5. 读 docs/onboarding/data-foundation-phase-1-v2.md(Phase 1 反 5 原则范本)
6. 读 项目 CLAUDE.md §3.5 环境边界表(确认 Agent4 全 mock 豁免)
7. ls data/mock/deep-pillar/DP001_龙峰精工/4、银行流水/ 感受流水形态
8. 读 data/mock/channel-kb/historical-clients/ 1-2 份 md 感受企业名风格

【第三步】按 §2 顺序 Task A → B → C:
- A · clients.csv · 100-200 行薄画像 · 零答案 · 难度 20/100/40/20 · Signal: ALERT-POOL-CLIENTS-DONE
- B · transactions/AP<id>.csv · ≥12 月 · hard/extreme 埋行为变化不标注 · Signal: ALERT-POOL-TRANSACTIONS-DONE
- C · external-signals/AP<id>.md · 3-10 条 · 混合矛盾 · 零答案 · Signal: ALERT-POOL-SIGNALS-DONE

【红线】
- 只动 data/mock/alert-pool/ · 不动 deep-pillar/channel-kb/compliance-kb/agent_*/web/evaluation/shared
- 零答案:产物不得出现 risk_level/alert_flag/red_flag/risk_score/difficulty/expected_color
- 合理矛盾:红档不要信号流水全红,至少 10 家混淆交叉样本
- 数字脱敏再造保量级 · 测试阶段重名 OK(Q-029.D)
- 每 Task 独立 commit 带对应 Signal

【最终】三 Task 全过 + 7 条硬指标自检通过 → commit trailer `Signal: READY-FOR-DATA-FOUNDATION-B2-REVIEW`,停下等 main CLI 复核。

开干。
```

---

## 尾部说明

- **签名**：Batch 2 kickoff 2026-04-24 · 主 CLI
- **粘发顺序**：4 worker 无串行依赖,同一 commit `BATCH-2-DISPATCHED` 后并行粘;Evaluation Task C 对 code-arch Task C oracle 是软依赖(未到位走 stub 分支,不卡流)
- **预计工时**：
  - code-urgent：3 Task 合计 3-3.5 天（A=M 1.5d / B=S-M 1d / C=S 0.5-1d）
  - code-arch：3 Task 合计 2.5-4 天（A=M 1-1.5d / B=M 1-1.5d / C=S-M 0.5-1d）
  - evaluation：3 Task 合计 4 天（A=L 2d / B=M 1.5d / C=S 0.5d 实做 + 等 code-arch）
  - data-foundation：3 Task 合计 2-3 天（100-200 家 × clients/transactions/signals）

- **Signal 索引**：
  - **ACK × 4**：`BATCH-2-CU-ACK` / `BATCH-2-CA-ACK`（code-arch 用一句话 ACK，无独立 trailer；对齐规则 commit 打 `Signal: BATCH-2-CA-ACK` 可补） / `BATCH-2-ACK`（evaluation） / `PRODUCT-HARDENING-BATCH-2-DF-P2-ACK`
  - **Task done**:
    - code-urgent：`ARCHIVE-EVIDENCE-UI-DONE` / `HIGHLIGHT-CARD-UI-DONE` / `UNFILLED-MARKER-UI-DONE`
    - code-arch：`AGENT1-EXTERNAL-SEARCH-DONE` / `AGENT5-POLICY-COMPARE-DONE` / `BATCH-2-INTEGRATION-TEST-DONE`
    - evaluation：`BASELINE-REAL-DONE` / `EV-12-RATIO-CONSISTENCY-DONE` / `AGENT1-5-METRICS-DONE`
    - data-foundation：`ALERT-POOL-CLIENTS-DONE` / `ALERT-POOL-TRANSACTIONS-DONE` / `ALERT-POOL-SIGNALS-DONE`
  - **收尾 READY × 4**：`READY-FOR-CODE-URGENT-B2-REVIEW` / `READY-FOR-CODE-ARCH-B2-REVIEW` / `READY-FOR-EVALUATION-B2-REVIEW` / `READY-FOR-DATA-FOUNDATION-B2-REVIEW`

- **Batch 2 合流前提**：4 个 `READY-FOR-<X>-B2-REVIEW` trailer 齐 + 对应 ACK signal 收齐（`BATCH-2-CU-ACK` / `BATCH-2-CA-ACK` / `BATCH-2-ACK` / `PRODUCT-HARDENING-BATCH-2-DF-P2-ACK`），主 CLI review 通过后合流 main;任一 REJECT 走 V2 返工
- **Batch 3 冷冻期**：4 worker 领完各自 `READY-FOR-<X>-B2-REVIEW` 后原地待命,**不得**自行启动 Batch 3 scope——等主 CLI 在 Batch 2 全 APPROVE 后统一派 Batch 3 kickoffs
