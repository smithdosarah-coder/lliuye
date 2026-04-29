# Worker-A3 Onboarding · Channel pilot (4 gate workspace · Phase A Week 2-3)

> 依赖 A1 + A2 (V2 中) · 等 A1/A2 V2 cherry-pick 后真动 · 之前先 read + draft
>
> Dispatch signal: `PHASE-A-A3-DISPATCHED`

---

## 0. worktree

- worktree: `D:\claude code\work-A3-channel-pilot` (新建 · 已 `git worktree add`)
- branch: `feat/phase-a3-channel-pilot` (派生 chore/l0-infra)
- resume 第一步: `cd D:/claude code/work-A3-channel-pilot && git status` (clean) · 直接干

## 0.5. 前置 wait gate (软)

A3 是 A4 5 子 worker 的 channel 4 gate 模板源。但 A3 自己依赖 A1 (5 contracts · workspace-state-protocol + sse-envelope + llm-prompt) + A2 (shared/llm_caller + shared/sse_envelope helper)。

A1+A2 都 V2 改中。你 resume 后:
1. `git log chore/l0-infra` 看 A1 V2 + A2 V2 是否 cherry-pick 进来 (commit signal `WORKER-A1-CONTRACTS-V2-DONE` + `WORKER-A2-SHARED-INFRA-V2-DONE`)
2. 没 cherry-pick → 你先 read 5 contracts (V1) + shared/llm_caller (V1) · 写 design draft (不真动 ChannelWorkspace.tsx) · 等主 CLI GO 信号
3. cherry-pick 进 → 你 `git rebase chore/l0-infra` 拉新 V2 contract/shared · 然后真动

主 CLI GO 信号 commit (chore/l0-infra): `A3-GO-AFTER-A1-A2-V2` · trailer 含 V2 cherry-pick hash。

## 1. 任务 (verbatim from `phase-a-charter.md` §3 worker-A3)

| # | 交付 |
|---|---|
| 1 | `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` 重构 = 4 gate state model (`started / selectedSession / liveData / selectedCandidate`) · 5 panel 全派生自 result · 不再各 panel 独立 state |
| 2 | `agent_channel/realtime_stream.py` (现 `done` event 缺 `radar/signals/funnel`) 改 = done 加完整 envelope per A1 sse-envelope contract + A2 sse_envelope helper |
| 3 | `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` SSE reader 改 = 用 `web/src/lib/api/_live.ts streamSse` (现内联 `res.body.getReader()`) |
| 4 | `data/mock/workspace/channel/scenarios/*.json` + `/api/channel/demo/run` 单独端点 (channel demo 模式 · 跟 live 路分开) |
| 5 | `web/tests/regression/channel-pilot-4gate.spec.ts` Playwright smoke (5 panel 同步亮 + demo run + live run) |
| 6 | banner-spec 规则 2 实装 (mock fallback 必显 banner · 不静默 · 见 `realtime_stream.py:339` Tavily key 缺 silent fallback 修) |

**Phase A 验收硬线 #3** (`phase-a-charter.md` §1): "Channel pilot 4 gate 真实装 · ChannelWorkspace.tsx 用 4 gate state · 5 panel 全派生 result · Playwright 5 panel 同步亮 smoke 通过"

## 2. 必读

- `RESET_MASTER_PLAN.md`
- `docs/reset/north-star.md` §2.2 + §3.2
- `docs/reset/phase-a-charter.md` §3 worker-A3 + §1 硬线 #3
- `docs/audit/conflict-register-v1.md` (你 owner: cat 2 channel · cat 3 channel · cat 4 channel · cat 11 channel banner + Tavily fallback)
- `docs/audit/sub-agent-step2-round1/architecture.md` (cat 2/3/4/11 verbatim findings)
- `docs/contracts/workspace-state-protocol.md` (A1 V1 · 等 V2 修)
- `docs/contracts/sse-envelope.md` (A1 V1 · V2 加 event 名 table)
- `shared/llm_caller/` + `shared/sse_envelope.py` (A2 · V2 修中)
- `agent_channel/realtime_stream.py` 当前 (你改)
- `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` 当前 (~1700 行 · 你重构)
- `web/src/lib/api/_live.ts streamSse` (你 import)
- `design_mockups/rm-assistant-final-2026-04-19.html` (视觉源 · 不偏离)

## 3. 不在范围

- ❌ 5 子 agent (credit/alert/compli/riskctrl/report) workspace 重构 — A4 干 · 你只 channel
- ❌ /today RM workbench 重写 — Phase B-3
- ❌ Agent6→Agent3 handoff data flow — A6 干 schema · A4-credit 真接

## 4. 红线 (red lines)

- ❌ 不跨 worktree
- ❌ commit 不带 `Signal:` trailer
- ❌ 改 `web/*` 必带 `PRESERVES: F-XXX` + `NEW-DOM: data-testid="..."` + `SMOKE-PASS: <spec>.spec.ts` (per features-inventory + CLAUDE.md §13)
- ❌ A1+A2 V2 cherry-pick 之前真动 ChannelWorkspace.tsx (规模重构 · 拉到 V2 才动 · 否则 rebase 巨 conflict)
- ❌ 直接 push origin

## 5. ACK

- 每 panel migration commit 一次 · trailer `Signal: WORKER-A3-PANEL-<N>-MIGRATED`
- backend done envelope commit 单独 `Signal: WORKER-A3-DONE-ENVELOPE-LANDED`
- 全完 + smoke pass 最后 commit `Signal: WORKER-A3-CHANNEL-PILOT-DONE` · trailer:
  ```
  CHANNELWORKSPACE-LINES: <approx · 重构后 line count>
  GATES-IMPLEMENTED: started/selectedSession/liveData/selectedCandidate (4/4)
  PANELS-DERIVED-FROM-RESULT: 5/5
  DONE-ENVELOPE-FIELDS: candidates/metrics/data_source/radar/signals/funnel/profile_brief/hero_summary
  SMOKE-PASS: web/tests/regression/channel-pilot-4gate.spec.ts
  HARDLINE-3-MET: yes
  PRESERVES: F-XXX (列 channel 相关 features-inventory ID)
  NEW-DOM: data-testid="channel-pilot-..."
  BANNER-SPEC-2: implemented (Tavily key 缺 mock fallback 显 banner)
  ```

## 6. Codex

主 CLI 已 fire codex pre-dispatch draft · 你不见。落 `docs/audit/codex-drafts/A3-channel-pilot.md`。
DONE 后主 CLI fire codex post-DONE peer review。

---

**Author**: 主 CLI · 2026-04-29
**Phase A Week 2-3 · 与 A5/A6/A7 并行 · A4 5 子等 A3 完**
