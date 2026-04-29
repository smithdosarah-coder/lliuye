# Phase A Charter · "全新出发" 验收硬线

> Phase A 是 reset 工程的核心 · 完成才算"轻装上阵"。Phase A 验收过 · 才进 Phase B (商业化推进)。

---

## 1. Phase A 验收硬线 (8 项 · 全 yes 才算 done)

| # | 验收项 | 怎么算 done |
|---|---|---|
| 1 | **5 份契约存在** | `docs/contracts/{workspace-state-protocol, agent-naming-ssot, sse-envelope, llm-prompt-contract, instruction-source-of-truth}.md` 5 文件 commit |
| 2 | **shared infra 抽出** | `shared/llm_caller/` core 写完 · `shared/sse_envelope.py` 写完 · `shared/prompts/contract.py` 8 段 template 写完 · 配 pytest 通过 |
| 3 | **Channel pilot 4 gate 真实装** | `ChannelWorkspace.tsx` 用 4 gate state · 5 panel 全派生自 `result` · Playwright 5 panel 同步亮 smoke 通过 |
| 4 | **5 agent thin adapter 完** | Credit / Alert / Compliance / Riskctrl / Report 都迁 4 gate + result-driven · 各 Playwright smoke 通过 |
| 5 | **Letterpress 真清** | `globals.css` legacy 段 (line 25-50/65-70/153-160/205-210/388 · 之前确认的) 删 · 12 consumer 全迁 shell-v2 token · grep `--color-brass` `--color-ink` 0 命中 |
| 6 | **6 Agent handoff data contract** | `docs/contracts/agent-handoff-schemas.md` 定义清楚: Agent1.candidate → Agent6.input · Agent6.report → Agent3.input · etc. (不要求自动跑通 · 仅 schema 定) |
| 7 | **PRD master + 6 sub v1** | `docs/prd/master-2026-XX-XX.md` + 6 sub-PRD 写完 · 双写飞书 |
| 8 | **命名 SSOT 单表落地** | `docs/contracts/agent-naming-ssot.md` 8 列单表 · CI lint 加(任何 agent_*/api.py mount 路径必须在词典 route 列里) |

---

## 2. 7 worker 拆分 + 依赖图

```
Week 1 · 并行 2 worker
├ worker-A1 · 写 5 契约
└ worker-A2 · shared infra (llm_caller core / sse envelope / prompt template)

Week 2-3 · 并行 4 worker (A3 依赖 A1+A2 完)
├ worker-A3 · Channel pilot (4 gate workspace migration)
├ worker-A5 · 设计 (Letterpress 真清 · 12 consumer 迁)
├ worker-A6 · 6 Agent handoff data contract
└ worker-A7 · PRD 取证 + master + 6 sub draft (与 PM 飞书协作)

Week 4-5 · 5 子 worker 并行 (依赖 A3 完)
└ worker-A4 · {credit / alert / compliance / riskctrl / report} 各 thin adapter

Week 6 · 主 CLI 整合
└ integration · Playwright cross-agent smoke · verify
```

---

## 3. 每 worker 详细 charter

### worker-A1 · 写 / 完善 5 契约

- **worktree**: `D:\claude code\work-A1-contracts` (新建 · 派生自 chore/l0-infra)
- **branch**: `feat/phase-a1-contracts`
- **onboarding doc**: `docs/onboarding/A1-contracts.md` (主 CLI 写)
- **交付** (3 完善 + 2 新建):
  - `docs/contracts/workspace-state-protocol.md` ✅ **v1.0 已存在** (Stage B 时建) · worker-A1 任务 = review v1.0 完整性 + 6 spec 同步引用 (6 spec 都标"待 A2 worker 产出" stale · 改为 "v1.0 已 ratified · 见 §X")
  - `docs/contracts/agent-naming-ssot.md` 🆕 新建 (8 列单表 · 6 agent 全列)
  - `docs/contracts/sse-envelope.md` 🆕 新建 (event 名 + done payload 共形)
  - `docs/contracts/llm-prompt-contract.md` 🆕 新建 (8 段: safety/evidence-first/agent-role/tool-use/output-schema/self-check/few-shot/evaluation-hook)
  - `docs/arch/instruction-source-of-truth.md` 🆕 新建 (优先级: contracts > root CLAUDE.md > scoped child > worker onboarding > decisions-log)
- **DONE signal**: `WORKER-A1-CONTRACTS-DONE`
- **Codex 介入**: 插入点 1 (pre-dispatch independent draft) + 插入点 2 (post-DONE peer review)

### worker-A2 · shared infra

- **worktree**: `D:\claude code\work-A2-shared`
- **branch**: `feat/phase-a2-shared`
- **交付**:
  - `shared/llm_caller/{client,prompts,audit,retry,provider}.py` (含 deepseek/qwen/moonshot provider abstraction)
  - `shared/sse_envelope.py` (helper for backend SSE event 共形)
  - `shared/prompts/contract.py` (8 段 template)
  - `tests/shared/test_llm_caller.py` + `test_sse_envelope.py`
- **DONE signal**: `WORKER-A2-SHARED-INFRA-DONE`

### worker-A3 · Channel pilot

- **worktree**: `D:\claude code\work-A3-channel-pilot`
- **branch**: `feat/phase-a3-channel-pilot`
- **依赖**: A1 + A2 都 DONE 才启
- **交付**:
  - `ChannelWorkspace.tsx` 重构: 4 gate state + 5 panel 全派生 result
  - `agent_channel/api.py` done event 加完整 envelope (含 candidates / signal_timeline / radar / profile_brief / hero_summary)
  - Demo 走 `/api/channel/demo/run` 单独端点 + `data/mock/workspace/channel/scenarios/*.json`
  - `web/tests/regression/channel-pilot-4gate.spec.ts` Playwright smoke (5 panel 同步亮)
- **DONE signal**: `WORKER-A3-CHANNEL-PILOT-DONE`

### worker-A4 · 5 agent thin adapter (5 子 worker)

- **5 子 worker** 并行 (依赖 A3 完)
- **worktree**: `work-A4-{credit, alert, compli, riskctrl, report}`
- **branch**: `feat/phase-a4-{agent}-adapter`
- **交付** (per 子 worker):
  - 该 agent workspace.tsx 重构 4 gate · 复用 A3 模式
  - `agent_*/api.py` done event 加 envelope
  - Demo `/api/{agent}/demo/run` 端点
  - Playwright smoke
  - 抽出共享 hook: `web/src/app/archive/_shared/useWorkspaceRun.ts` + `WorkspaceBanner.tsx` + `EmptyWorkspace.tsx` + `sseWorkspaceClient.ts` (其中一个子 worker 兼任)
- **DONE signal**: `WORKER-A4-{AGENT}-ADAPTER-DONE`

### worker-A5 · Letterpress 真清

- **worktree**: `D:\claude code\work-A5-design`
- **branch**: `feat/phase-a5-design`
- **可与 A3-A7 并行 · 不依赖**
- **交付**:
  - `globals.css` legacy 段 (--color-brass / --color-ink-* / .letterpress-* / ink-brush-hr 等) 全删
  - 12 consumer 迁 shell-v2 token (`--g0..--g7` / `--ink` / `--chalk` / `--accent` / `--t-{agent}` 功能色)
  - 4 themes (canvas/matcha/dusk/ink) 视觉一致 · 主题切换无穿帮
  - Playwright visual regression smoke
- **DONE signal**: `WORKER-A5-DESIGN-LETTERPRESS-DONE`

### worker-A6 · 6 Agent handoff contract

- **worktree**: `D:\claude code\work-A6-handoff`
- **branch**: `feat/phase-a6-handoff`
- **可与 A3-A7 并行**
- **交付**:
  - `docs/contracts/agent-handoff-schemas.md` 含:
    - Agent1.candidate_company → Agent6.upload_intent (字段 schema)
    - Agent6.report_json → Agent3.decision_input (schema)
    - Agent3.decision → Agent4.client_pool_signal (schema)
    - Agent5.policy_event → Agent4/Agent6 schema
  - Sample fixture in `data/mock/handoff/*.json` 每条链路 1 个真实形态
- **DONE signal**: `WORKER-A6-HANDOFF-CONTRACT-DONE`

### worker-A7 · PRD 取证 + draft

- **worktree**: `D:\claude code\work-A7-prd`
- **branch**: `feat/phase-a7-prd`
- **可与 A3-A7 并行**
- **依赖 PM**: 飞书旧 PRD 抓取 (PM 主动)
- **交付**:
  - 飞书旧 PRD 截图归档 + intent extraction
  - repo current state inventory (基于 features-inventory.md + CLAUDE.md §7 + contracts)
  - drift table 5 列 (Original Intent / Current Repo State / Keep-Revert-Rewrite / Evidence / Owner+Deadline+Acceptance)
  - PM 逐条裁决 cycle
  - master PRD v1 + 6 sub-PRD v1 (双写飞书 + `docs/prd/`)
- **DONE signal**: `WORKER-A7-PRD-MASTER-DONE`

---

## 4. 跨 worker 红线 (mesh discipline)

- ❌ Worker 不可跨 worktree 改文件 · 走 decisions-log Q-NNN
- ❌ Worker commit 必带 `Signal:` trailer · 否则 validator 拒绝
- ❌ Worker 改 `web/` 必带 `PRESERVES: F-XXX` + `NEW-DOM:` + `SMOKE-PASS:` trailer
- ❌ A4 5 子 worker 必须先等 A3 完 (依赖 channel 4 gate 模板)
- ❌ A1 + A2 不允许串行 · 必须并行 · 否则 Phase A 时间线塌

---

## 5. PM 周一 30 min checkpoint

每周一 PM (你) 30 min review:
- 上周完成 worker DONE list (从 `git log --grep "Signal: WORKER-"` 抓)
- 当前 mesh state (`scoreboard.py`)
- 卡点 (Q-NNN-RAISED · 无 A 答的)
- 本周 worker 排期

PM checkpoint commit (主 CLI 写): `chore(checkpoint): Week N · PM review` · `Signal: WEEKLY-CHECKPOINT-WEEK-<N>`。

---

## 6. Codex 4 插入点 (per worker)

详 `docs/reset/codex-mesh-protocol.md`。每 worker 至少触发:
- 插入点 1 · pre-dispatch independent draft (主 CLI 写 onboarding 同时 fire)
- 插入点 2 · post-DONE peer review (worker DONE 后主 CLI fire)

可选触发 (按需):
- 插入点 3 · arbitration (有 dissent)
- 插入点 4 · periodic audit (Phase A 中段 + 末)

---

## 7. Phase A 退出标准

8 项验收硬线全 yes (本文 §1) + PM 周一 checkpoint 至少 4 周连续无 BLOCKER + Codex periodic audit 通过 → Phase A 完毕 → 进 Phase B。
