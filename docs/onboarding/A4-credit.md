# Worker-A4-credit Onboarding · Credit thin adapter (Phase A Week 4-5)

> 依赖 A3 channel pilot 完 · cherry-pick 到 chore/l0-infra 后才真动 · 之前先 read + draft
>
> Dispatch signal: `PHASE-A-A4-CREDIT-DISPATCHED`

## 0. worktree

- `D:\claude code\work-A4-credit` · branch `feat/phase-a4-credit-adapter` (新建 · 已 checkout)
- resume: cd worktree · `git status` (clean) · 直接干 §0.5

## 0.5. 前置 wait gate (硬)

A3 channel pilot 是你的 4 gate 模板源。**A3 cherry-pick 进 chore/l0-infra 之前 · 你不真动 CreditWorkspace.tsx**。

resume 后:
1. `git log chore/l0-infra | grep "A3-CHANNEL-PILOT-DONE\|A3-MERGED"` 看 A3 是否 cherry-pick
2. 没 cherry-pick → 你 read A3 ChannelWorkspace.tsx (在 work-A3-channel-pilot worktree) + draft 你 credit 4 gate 改造方案 (写 `docs/audit/A4-credit-draft.md` · 不动真代码) · 等 main CLI GO 信号
3. cherry-pick 进 → `git rebase chore/l0-infra` 拉新 ChannelWorkspace 模板 · 然后照搬到 CreditWorkspace

主 CLI GO 信号 commit: `A4-CREDIT-GO-AFTER-A3` · trailer 含 A3 cherry-pick hash。

## 1. 任务 (per phase-a-charter §3 worker-A4)

| # | 交付 |
|---|---|
| 1 | `web/src/app/archive/credit/_components/CreditWorkspace.tsx` 重构 4 gate (复用 A3 ChannelWorkspace 模板 · 但 credit 5 panel 是 corp/small/retail 三 segment + radar + score · 不是 channel 5 panel) |
| 2 | `agent_credit/api.py` done event 加完整 envelope (mock 路 + live 路对称 · 不再 live 路 done payload 空 · 见 audit cat 4) |
| 3 | `agent_credit/api.py` SSE reader 改 streamSse · 删内联 fetch reader |
| 4 | `data/mock/workspace/credit/scenarios/*.json` + `/api/credit/demo/run` 单独端点 |
| 5 | `web/tests/regression/credit-pilot-4gate.spec.ts` Playwright smoke |
| 6 | Agent6→Agent3 handoff input 真消费 (per A6 ReportJSON schema · CreditWorkspace EmptyState onPrimary 改成"等 Agent6 ReportJSON" · 不再独立 runDecision) — 这是 cat 0 北极星修正核心 |

## 2. 必读

- `RESET_MASTER_PLAN.md`
- `docs/reset/north-star.md` §3.1 (Agent6→Agent3 handoff)
- `docs/reset/phase-a-charter.md` §3 worker-A4 + §1 硬线 #4
- `docs/audit/conflict-register-v1.md` cat 2 credit + cat 3 credit + cat 4 credit + cat 11 credit + cat 0 credit (Agent6 handoff 部分)
- `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` (A3 模板 · 你抄)
- `agent_channel/realtime_stream.py` (A3 done envelope · 你抄)
- `docs/contracts/agent-handoff-schemas.md` (A6 干中 · ReportJSON schema · 你 EmptyState 真消费的契约)
- `agent_credit/api.py` 当前
- `web/src/app/archive/credit/_components/CreditWorkspace.tsx` 当前 (~1800 行)

## 3. 红线

- ❌ 不跨 worktree
- ❌ commit 不带 `Signal:` trailer
- ❌ 改 `web/*` 必带 `PRESERVES: F-XXX + NEW-DOM + SMOKE-PASS`
- ❌ A3 cherry-pick 之前真动 CreditWorkspace.tsx (硬规)
- ❌ 重新发明 4 gate (用 A3 模板 · 复用)

## 4. ACK

- DONE commit `Signal: WORKER-A4-CREDIT-ADAPTER-DONE` · trailer:
  ```
  GATES-IMPLEMENTED: 4/4
  PANELS: corp/small/retail × radar/score (5 panel)
  DONE-ENVELOPE-SYMMETRIC: mock + live (cat 4 修)
  AGENT6-HANDOFF-CONSUMED: yes (EmptyState 真接 ReportJSON · 不再 runDecision)
  SMOKE-PASS: web/tests/regression/credit-pilot-4gate.spec.ts
  HARDLINE-4-MET: yes (credit 部分)
  PRESERVES: F-015..F-019
  NEW-DOM: data-testid="credit-pilot-..."
  ```

## 5. Codex

Pre-dispatch draft 落 `docs/audit/codex-drafts/A4-credit.md`。

---

**Author**: 主 CLI · 2026-04-29 · A4-credit (1 of 5 子 worker)
