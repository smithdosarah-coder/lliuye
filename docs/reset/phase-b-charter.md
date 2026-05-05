# Phase B Charter v2 · 商业化推进 + 真产品力大提升

> **v2 (2026-05-01)** · 主 CLI + Codex 后端方案 v2.1 final 三轮辩论后 + Gemini 前端方案 v4 final 三方辩论后 · 痛点驱动 (PM ultrathink "深度考虑产品到底解决了什么痛点")
> v1 (2026-04-29) 已 supersede · git history 留底 · v1 仅含 worker-B1 + worker-B2 (轻量) · v2 加 Stream 1 v4 前端 + Stream 2 BE1-BE13 后端 deep work + Stream 3 enabler
> Phase A 验收硬线全过 (commit fb4cead + Codex re-audit GO) · 退回点 git tag `phase-a-exit-bugfix-2026-05-01`

---

## 0. v1 → v2 演进

| 维度 | v1 (2026-04-29) | v2 (2026-05-01) |
|---|---|---|
| 工程量 | ~5 周 (B1 + B2 thin) | ~14-18 周 wall-clock (含 v4 前端 + 后端 v2.1 BE1-BE13 + enabler) |
| Worker 数 | 2 (B1 + B2) | 9 (B1 + B2 + B3 + B4-{credit/report/alert/compliance/channel/riskctrl}) |
| Scope | 数据飞轮 thin MVP + 商业化 doc | + RM workbench v4 前端 17 action + 13 BE 后端 deep work + 跨 Agent decision ledger + 个人画像 POC |
| 痛点驱动 | 无 (主 CLI 凭印象) | 4 角色 10+ 痛点对照 + Codex 全扫 175 .py file:line evidence (~85% evidence 强度) |

---

## 1. Phase B v2 验收硬线 (5 项 · 全 yes 才算 reset 工程完毕)

| # | 验收项 | 怎么算 done |
|---|---|---|
| 1 | **数据飞轮 Phase B gate** | `/api/feedback` 接 audit modify + 写 jsonl + 6 agent baseline 跑通 + blocker_threshold 阻断发布 + few-shot 注入 PoC |
| ~~2~~ | ⚠️ **OBSOLETE (Q-052 · 2026-05-04 PM ratify)** — ~~商业化 doc + 多租户 architecture~~ | 商业化交众安信科商务团队 · 客户全本地化部署 = 永不 multi-tenant 实装 · B2 4 doc 已 ship 标 REFERENCE-ONLY · 不再是 PM 验收项 · 详 Q-052 |
| 3 | **4+1 角色定位工作台** (Q-052 · 改名自 ~~RM workbench v4 闭环~~) | 5 角色 (RM / credit_officer / compliance_officer / risk_manager / admin) 各 home view + ACCESS matrix + 后端 row-level/action gate + 前端 F5/F7/F8/F9/F10/F15 工作台逻辑 (注: F11-F14/F16/F17 视觉打磨 Q-047 冻结 · 不在 #3 内) · 详 Q-052 |
| 4 | **6 Agent 后端真业务能力** | 13 BE 全 done (BE1-BE13 · 含 Agent1 候选证据/Agent3 decision graph/Agent6 material gap/Agent5 policy registry/Agent4 信号质量+batch/Agent2 DSL+回测+业务指标/跨 Agent decision ledger/个人画像 POC) |
| 5 | **6 Agent 端到端 demo + 银行客户 POC ready** (Q-052 · 改验收口径) | 按 4+1 角色跑通同一客户闭环 (5 账号登录 · 各看到角色专属 home + handoff 串通) + 1 个完整 video 录 + 个人画像 POC 跑通 4 维度评价 + 银行客户演示 ready (注: 不是销售/价格/multi-tenant 叙事 · 详 Q-052) |

---

## 2. 9 Worker 拆分 (3 Stream 并行)

### Stream 1 · v4 前端 (worker-B3 · ~5-6 周 · 含并行 ~4-5 周 wall-clock)

#### worker-B3 · RM workbench v4 (前端 17 action)
- **worktree**: `D:\claude code\work-B3-rm-workbench`
- **branch**: `feat/phase-b3-rm-workbench`
- **依据**: `docs/research/FINAL-FRONTEND-OPTIMIZATION-PLAN-V4-2026-05-01.md` (Gemini + Codex + 主 CLI 三方辩论 R1+R2+R3 ratify · 5 turn Gemini conversation 真发生)
- **交付**: 17 action (B-1 quick win + B-3 RM workbench 闭环 + B 末)
  - B-1 (~1 周): F1 千分位 + F2 路由修补 + F3 Hero 真指标 + F4 登录黑洞 + F5 CustomerContextGateway + F6 baseline gate (与 worker-B1 配套)
  - B-3 (~3 周): F7 Today 单链路 + F8 handoff 任务卡 + F9 segment-aware + F10 Action Card 组件族 + F11 A5 spike + F12 视觉清洗 + F13 /today 头重脚轻 + F14 全屏渐变折中 + F15 Live evidence + F16 dispatch 单发送 + F17 warroom rejected lane
  - B 末 (~1 周): C11 audit 降级 + C12 ScanCTA + C13 抽 hook + C18 Agent1 similarity (前端部分)
- **DONE signal**: `WORKER-B3-RM-WORKBENCH-V4-DONE`

### Stream 2 · 后端 6 Agent deep work (worker-B4 系列 · ~10-12.5 周 · 含并行 ~7-9 周 wall-clock)

#### worker-B4-credit · Agent3 decision graph + peer_gap (BE2)
- **worktree**: `D:\claude code\work-B4-credit`
- **branch**: `feat/phase-b4-credit`
- **依据**: `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE2
- **交付**: decision graph (feature snapshot + rule hit + 阈值 + 来源段落 + 版本) + peer_gap (同业对标 fixture · scoring_model_corporate.py:215-240 已有字段未纳入可复核链)
- **工程量**: 2 周
- **DONE signal**: `WORKER-B4-CREDIT-DECISION-GRAPH-DONE`

#### worker-B4-report · Agent6 material gap + cross-section coherence (BE3)
- **worktree**: `D:\claude code\work-B4-report`
- **branch**: `feat/phase-b4-report`
- **交付**: material gap graph + section impact + handoff Agent3 + cross-section coherence (跨章节语义/历史一致性 · 现有 financial_consistency 只比 anchor)
- **工程量**: 1.5-2 周
- **DONE signal**: `WORKER-B4-REPORT-MATERIAL-GAP-DONE`

#### worker-B4-alert · Agent4 信号质量 + batch analytics (BE5 + BE9)
- **worktree**: `D:\claude code\work-B4-alert`
- **branch**: `feat/phase-b4-alert`
- **交付**: BE5 信号质量 (freshness + source confidence + fallback banner + scan replay) + BE9 跨客户 batch analytics + alert clustering (per handoff schema §6.4)
- **工程量**: 1 + 2 = 3 周
- **DONE signal**: `WORKER-B4-ALERT-SIGNAL-QUALITY-DONE`

#### worker-B4-compliance · Agent5 policy registry + version diff + reason schema (BE4)
- **worktree**: `D:\claude code\work-B4-compliance`
- **branch**: `feat/phase-b4-compliance`
- **交付**: policy registry + rule version diff + violation reason schema (字段/原文/置信度/复核原因)
- **工程量**: 2-2.5 周
- **DONE signal**: `WORKER-B4-COMPLIANCE-POLICY-REGISTRY-DONE`

#### worker-B4-channel · Agent1 候选证据 + 内源 + conversion + personal_insight 子域 (BE1 + BE12)
- **worktree**: `D:\claude code\work-B4-channel`
- **branch**: `feat/phase-b4-channel`
- **交付**: BE1 候选证据评分 + 数据源状态 + 内源已成交客户库 + conversion tracking + BE12 Agent1 `personal_insight` 子域 (复用 shared/personal_profile.py · 前端可叫 Agent7 后端不复制)
- **工程量**: 1.5-2 + 2.5 = 4-4.5 周
- **DONE signal**: `WORKER-B4-CHANNEL-PERSONAL-INSIGHT-DONE`

#### worker-B4-riskctrl · Agent2 DSL + 回测 + 业务指标双轨 (BE6 + BE8)
- **worktree**: `D:\claude code\work-B4-riskctrl`
- **branch**: `feat/phase-b4-riskctrl`
- **交付**: BE6 DSL 上线性 (字段字典 + 单位归一 + 互斥/遮蔽) + 业务指标双轨 (KS/AUC + 通过率/坏账率/利润影响) + BE8 回测可信度 (champion/challenger + PSI + 分月 + 误杀解释)
- **工程量**: 2-2.5 + 2 = 4-4.5 周
- **DONE signal**: `WORKER-B4-RISKCTRL-BACKTEST-DONE`

### Stream 3 · 数据飞轮 + 商业化 + decision ledger (worker-B1 + worker-B2 + worker-B7 · ~6-7 周)

#### worker-B1 · 数据飞轮 Phase B gate (BE10 · Codex 缩 scope)
- **worktree**: `D:\claude code\work-B1-flywheel`
- **branch**: `feat/phase-b1-flywheel`
- **交付**: `/api/feedback` 接 audit modify + 写 `data/feedback/YYYY-MM-DD.jsonl` + 6 agent baseline 跑通 + blocker_threshold 阻断发布 + few-shot 注入 PoC + `docs/runbook/feedback-flywheel.md` runbook
- **工程量**: 1.5 周 (Codex 缩 vs 主 CLI 原 3 周 · 不重 A/B 平台)
- **DONE signal**: `WORKER-B1-FLYWHEEL-DONE`

#### worker-B2 · 商业化 doc + 多租户 architecture only (BE11 · Codex 反对实装)
- **worktree**: `D:\claude code\work-B2-biz`
- **branch**: `feat/phase-b2-biz`
- **交付**:
  - `docs/biz/{pricing, multi-tenant, trial-flow}-assumptions.md`
  - `docs/biz/sales-playbook-v1.md`
  - tenant_id/org_id 数据模型 spec (不实装)
- **工程量**: 1 周 (Codex 缩 vs 主 CLI 原 3-4 周 · 真 isolation 推 Phase C)
- **DONE signal**: `WORKER-B2-BIZ-DOC-DONE`

#### worker-B7 · 跨 Agent decision ledger + POC 跨 Agent 拼 (BE7 + BE13)
- **worktree**: `D:\claude code\work-B7-decision-ledger`
- **branch**: `feat/phase-b7-decision-ledger`
- **交付**: BE7 跨 Agent decision ledger (统一结论账本 · 候选/报告/授信/合规/预警串成同客户可审计链) + BE13 POC 跨 Agent 拼 (Agent1 画像 + Agent5 合规 + Agent4 触达后预警 · 不造 orchestrator 重平台)
- **工程量**: 2 + 1.5-2 = 3.5-4 周
- **DONE signal**: `WORKER-B7-DECISION-LEDGER-DONE`

---

## 3. Sprint 排期 (含并行)

```
Phase B (~14-18 周 wall-clock):
├── Sprint 1 (Week 1-3 · 4 worker 并行):
│   ├── worker-B1 数据飞轮 gate (1.5 周)
│   ├── worker-B3 v4 前端 B-1 (1 周)
│   ├── worker-B4-credit Agent3 decision graph (2 周)
│   └── worker-B4-report Agent6 material gap (1.5-2 周)
├── Sprint 2 (Week 3-6 · 4 worker 并行):
│   ├── worker-B3 v4 前端 B-3 (3 周 · 含 F5 CustomerContextGateway 与 BE2 配套)
│   ├── worker-B4-alert Agent4 信号质量 + batch (3 周)
│   ├── worker-B4-compliance policy registry (2-2.5 周)
│   └── worker-B2 商业化 doc + multi-tenant arch (1 周 · 完后释放)
├── Sprint 3 (Week 6-10 · 3 worker 并行):
│   ├── worker-B4-channel Agent1 候选证据 + personal_insight (4-4.5 周)
│   ├── worker-B4-riskctrl DSL + 回测 (4-4.5 周)
│   └── worker-B7 decision ledger + POC 跨 Agent 拼 (3.5-4 周)
├── Sprint 4 (Week 10-14 · worker-B3 收尾 + 整合):
│   ├── worker-B3 v4 前端 B 末 (1 周 · C11/C12/C13/C18)
│   ├── 跨 worker 整合 (decision ledger 串通 6 Agent · BE7 验)
│   └── Codex periodic final audit Phase B (插入点 4)
└── Sprint 5 (Week 14-18 · 客户演示 ready · POC 4 维评价跑通):
    ├── 6 Agent 端到端 demo chain (1 客户全流程)
    ├── POC 个人画像 4 维评价跑通
    ├── video 录
    └── 银行客户演示 ready
```

---

## 4. 回档节点 (per PM 2026-05-01 ratify "留好一个回档节点")

| Tag | 含义 | 退回命令 |
|---|---|---|
| `phase-a-exit-bugfix-2026-05-01` | Phase A 真 exit (8 硬线全通 + 4 BUG 修完) · 已落 | `git reset --hard phase-a-exit-bugfix-2026-05-01` |
| `phase-b-start-2026-05-01` | Phase B 启动前 (本 commit + tag) · 含 Phase B charter v2 + 三方辩论 v4 + 后端 v2.1 doc · 但 worker 还没动手 | `git reset --hard phase-b-start-2026-05-01` |
| `phase-b-sprint{N}-end-YYYY-MM-DD` | 每 Sprint 结束打 tag (5 个 sprint 5 个 tag · per PM "做好每一步的记录") | `git reset --hard phase-b-sprint{N}-end-YYYY-MM-DD` |

⚠️ **`git push --force-with-lease` 是 destructive · PM 必须明确同意才执行**。

---

## 5. Codex + 三方辩论介入

- **插入点 1**: Pre-dispatch (每 worker 启动前 · Codex 看 onboarding doc 给 dissent)
- **插入点 2**: Post-DONE (每 worker DONE 后 Codex review · per Q-043 codex protocol v2)
- **插入点 4**: Periodic final (Phase B 末跑全仓 audit · 确认无新 drift)
- **三方辩论**: Phase B 期间任何重大方案改动必走 R1+R2+R3 (主 CLI + Codex + 必要时 Gemini · per Q-044 三方辩论 ratify)

---

## 6. Phase B 退出 = reset 工程完毕

5 项 v2 验收 + Phase A 8 项验收 · 共 13 项硬线全过 → 产品"全新出发" · 可拿出去给银行客户**真卖**:
- 真产品力差异 (vs Phase A 收尾 thin demo): 4 角色全有可信 evidence + 跨 Agent decision ledger + 个人画像 POC + 数据飞轮 gate + 多租户 architecture
- POC 4 维评价跑通 (画像 35% + 产品适配 25% + 经营策略 20% + 性能 20%)
- 6 Agent 端到端 demo chain + video

---

## 7. Sign-off

- v1 author: 主 CLI 2026-04-29 (B1 + B2 thin)
- v2 author: 主 CLI 2026-05-01 (基于真三方辩论 v4 + 后端 v2.1 final)
- ratify: PM 2026-05-01 ultrathink "前端后端任务一起推进 · 做好每一步的记录 · 留好一个回档节点 · 剩下的直接干"

---

**Author**: 主 CLI · 2026-05-01
**v2 supersede v1**: ✓
**git tag baseline**: phase-b-start-2026-05-01 (本 commit + tag)

---

## v2.2 · Sprint 3 排期 + 4 worker 阶梯启 (2026-05-04 PM ratify · post-Q-052 audit dispose synthesis)

### 触发

- Codex Phase B periodic audit (`bx2wmkcwp` · 2026-05-04) verdict NEEDS-FIX · 4 P1 + 4 P2 + 2 P3 finding
- R1/R2 audit dispose 双辩论 synthesis (主 CLI v1+v2 · Codex `btx6e1616` + `b23cpqfz5` · R3 跳 dissent ≤ 1)
- PM 2026-05-04 GO 拍板 + Codex R2 catch 2 项: B5 V2-issue-3 endpoint DoD 明确 + P2.6 grep guard 防复制污染

### Sprint 3 4 worker 阶梯启 (Week 6-8)

| Week | Day | worker | 任务 |
|---|---|---|---|
| Week 6 | Day 1-3 (~5/14-5/16) | **B5-role-workbench-logic** (新加) | **contract-first sub-PR**: ACCESS v2 + row-level Depends schema (action enum `invoke/read/export/handoff/approve`) + RM 权限收窄 contract (主调 Agent1/Agent6 · 看 Agent3/Agent4 read-only · 不可调 Agent2/Agent5) + V2-issue-3 policy_diff endpoint contract (POST /api/compliance/policy_diff + sse_envelope) |
| Week 6 | Day 1-3 同启 | **B4-channel** (BE1+BE12) | backend-only · 不碰 shell/today/auth/dispatch 公共区 · approve/export/action 集成等 B5 schema freeze |
| Week 6 | Day 1-3 同启 | **B4-riskctrl** (BE6+BE8) | backend-only · DSL/backtest/business metrics · approve/export 集成等 B5 schema freeze |
| Week 6 | Day 4-5 (~5/17-5/18) | **B5 implementation sub-PR** | atomic 跨前后端: rbac.py + auth-store.ts + AuthGate.tsx + 5 role home view (F5/F7/F8/F9/F10/F15) + policy_diff endpoint consumer + frontend listener + endpoint test |
| Week 6 | Day 4-5 同启 | B4-channel | 接 Agent1 workspace + personal_insight payload (不改 today layout) |
| Week 6 | Day 4-5 同启 | B4-riskctrl | 接 Agent2 DSL/backtest + Agent2→4/3 链路 fixture |
| Week 7-8 (~5/19-6/15) | 插空 | **B7-BE13** | BE13 个人画像 POC (减半 · 0.75-1 周 · BE7 已被 B4-credit Sprint 2 提前 ship) |

### 4 worker 边界 ownership (per Codex audit dispose R2 synthesis)

| worker | owns | 不 owns |
|---|---|---|
| **B5-role-workbench-logic** | `auth_service/rbac.py` · `auth_service/dependencies.py` · `web/src/lib/store/auth-store.ts` · `web/src/components/shell/AuthGate.tsx` · `/today` role shell (5 角色 differentiation) · `/dispatch` handoff task card frame/action gate · handoff/action schema · V2-issue-3 endpoint (POST /api/compliance/policy_diff + sse_envelope + endpoint test) | Agent1/2/3/4/5/6 业务 BE · workspace 内容 |
| **B4-channel** | `agent_channel/` · channel API/types · `/archive/channel` workspace · Agent1 candidate evidence card · `personal_insight` payload (BE12 后端 + payload schema) | `/today` layout · auth · dispatch · shell |
| **B4-riskctrl** | `agent_riskctrl/` · DSL/backtest/business metrics (BE6+BE8) · Agent2→4/3 链路 fixture (写真业务深度 · per Q-052 P2.5) | shell/today/auth/dispatch |
| **B7** | `docs/runbook/be13-personal-insight-poc.md` (POC report) + `evaluation/runner/adapters/agent1_personal_insight.py` + `evaluation/agent1_personal_insight.yaml` (新 BE13 evaluation adapter · per Codex Sprint 3 onboarding pre-dispatch review NEEDS-FIX 修正 · 不是 agent_riskctrl yaml) + `agent_channel/personal_insight*` 和 `shared/decision_ledger/` read-only verify | 其他 |

### Sprint 3 启动前 DoD (~5/14 ratify before)

主 CLI 自决执行 (~3 hr 总 · per Q-052 audit dispose synthesis):

1. ✅ P2.7 Sprint 2 baseline regen 跑 + commit (~30 min) — `evaluation/baselines/2026-05-04-sprint2-end.md`
2. ⏳ P2.6 legacy LLMClient (3 file `shared/base_agent.py:16,30` + `enterprise_info.py:294-295` + `rule_extractor.py:53-54`) 主 CLI pre-Sprint 小 PR 迁 (~30-45 min if testable) OR Sprint 4 waiver + grep guard `rg "from llm import LLMClient|LLMClient\("`
3. ✅ P2.5 主 CLI 修 stale + schema-valid 最小 fixture × 5 (`agent5-to-3-block.json` · `agent3-to-6-gap.json` · `agent4-to-5-escalate.json` · `agent2-to-4-dsl-deploy.json` · `agent2-to-3-rubric.json`) — 业务深度 worker 触链路时扩展 (per §3.5 #5 mock 边界)
4. ✅ P3.9 contract stale 改 (6 line · §6.1-6.6 fixture status update · §6.4 标 done with commit f9cfcc9)
5. ✅ PRD master v1.1 update (post-Q-052 reframe · 8 active rule + Sprint 3 排期)
6. ✅ charter v2.2 段写 (本段)
7. ⏳ 4 worker onboarding 起草 (B5 + B4-channel + B4-riskctrl + B7 · ~1 hr)
8. ⏳ Codex pre-dispatch review **一次批量 4 onboarding** (per Q-049 双辩论 + Codex R2 audit dispose 建议 · ~30-60 min · 验跨 worker 写集 + DoD 含 P1/P2 + Q-048/Q-049/Q-050/Q-052 + B5 V2-issue-3 endpoint DoD 明确 + 禁止新增 legacy LLMClient grep guard)

完了 PM:
- ratify charter v2.2 (本段 · ~10 min)
- ratify 4 worker onboarding (~10 min)
- ratify PRD master v1.1 (~30 sec · 已 status ✅)
- ~5/14 双击 launch-all-LIUYE.bat 启 4 sub CLI (B5 + B4-channel + B4-riskctrl + B7)

### Sprint 3 风险 (5 项 · post-Codex R2 audit dispose)

| # | 风险 | 缓解 |
|---|---|---|
| 1 | B5 scope 膨胀 (权限 + home + dispatch + endpoint + UI overhaul) | contract-first sub-PR + implementation sub-PR 分两段 atomic commit chain · 每段跨前后端 · 守 PM 5/4 "禁止先改一端" |
| 2 | B4-channel + B5 同改 `/today`/`dispatch` merge conflict | 边界严格 ownership (上表) · review block 跨 worker file edit |
| 3 | row-level schema 没真实 customer assignment 数据 | 先 skeleton + demo fixture · Sprint 3 中 B4-channel BE12 / B4-credit history 真数据接入 · `web/src/lib/store/types.ts:49-60` `Customer.assignedTo/sharedWith` shape |
| 4 | policy_diff endpoint 再次只 ship lib (类 V2-issue-3 历史) | B5 DoD 必含 `POST /api/compliance/policy_diff` route + sse_envelope · `tests/agent_compliance/test_policy_diff_endpoint.py` 真 ship · 不只 lib |
| 5 | Codex review file:line 幻觉 (5/4 V2-issue-3 教训) | R2 + Codex review 必人工 verify file:line · 不盲信 AGREE |

### 替代方案 rejected (post-Codex R2 audit dispose)

| # | 替代 | 拒理由 |
|---|---|---|
| A | 主 CLI 现在直接 fix P1.1 RM 权限 | break 当前 RM 前端 view · 必跟 row-level schema atomic · 留 B5 |
| B | Sprint 4 整合时改 P2.6 legacy LLMClient | Codex catch · 越拖 Sprint 3 worker 复用 shared 会再加一份 · 改 Sprint 3 启前 OR waiver + grep guard |
| C | 4 worker 不阶梯启 (Sprint 3 全 4 worker 同时启) | cron + review capacity 超载 · 反 Q-046 5 跑偏硬规 #3 |
| D | B5 单巨 PR | Review cost 过高 (跨 5+ file 全前后端 + endpoint + 5 home view) |
| E | 4 worker onboarding 4 sequential bg 双辩论 | Codex catch · cost 4× · 一次包 4 看跨 worker 冲突更全 |
| F | 反向链 fixture worker 触到时全自写 (没主 CLI 修 stale) | Codex catch · contract `:855` 仍 placeholder 但本地 fixture 已存在 = SSOT 漂移 · 主 CLI 必修 stale + 写 schema-valid 最小 (业务深度 worker 扩展) |
| G | 直接 ratify PRD v1 (不 v1.1) | 内容跟 Q-052 reframe 不一致 · 误导后续 worker |

### Sign-off

- v2 author: 主 CLI 2026-05-01 (5 项验收硬线 · 9 worker · BE1-BE13)
- v2.2 author: 主 CLI 2026-05-04 (Sprint 3 排期 + 4 worker 阶梯启 + B5 contract-first + 4 worker 边界 ownership · post-Q-052 audit dispose synthesis)
- ratify: PM 2026-05-04 GO

