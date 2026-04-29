# Worker-A4-alert Onboarding · Alert thin adapter (Phase A Week 4-5)

> 依赖 A3 cherry-pick 后真动 · Dispatch signal: `PHASE-A-A4-ALERT-DISPATCHED`

## 0. worktree
- `D:\claude code\work-A4-alert` · branch `feat/phase-a4-alert-adapter`
- resume: cd worktree · `git status` clean · 干 §0.5

## 0.5. 前置 wait gate (硬)
A3 cherry-pick 进 chore/l0-infra 之前 · 不真动 AlertWorkspace.tsx。
- `git log chore/l0-infra | grep "A3-CHANNEL-PILOT\|A3-MERGED"` 检查
- 没 cherry-pick → read A3 模板 (work-A3-channel-pilot) + draft `docs/audit/A4-alert-draft.md` · 等 GO
- cherry-pick → `git rebase chore/l0-infra` + 照搬

主 CLI GO 信号: `A4-ALERT-GO-AFTER-A3`

## 1. 任务

| # | 交付 |
|---|---|
| 1 | `web/src/app/archive/alert/_components/AlertWorkspace.tsx` 重构 4 gate (复用 A3 模板 · alert 5 panel 是红/黄/绿榜单 + 雷达图 + 处置建议) |
| 2 | `agent_alert/api.py` done event 加完整 envelope (现 done 空 + stage event 无 stage 名 · 见 audit cat 4) |
| 3 | SSE reader 改 streamSse |
| 4 | `data/mock/workspace/alert/scenarios/*.json` + `/api/alert/demo/run` 端点 |
| 5 | `web/tests/regression/alert-pilot-4gate.spec.ts` smoke |
| 6 | grade 命名统一 (mock `tier` vs word_export `risk_level/level/tier` vs runtime_dump `grade` 三命名 → A6 handoff schema 选一个 · 你按 schema 改 alert 全栈) |

## 2. 必读

- RESET_MASTER_PLAN.md / north-star.md / phase-a-charter §3 worker-A4
- conflict-register-v1.md cat 2 alert + cat 4 alert + cat 5 grade 三命名 + cat 11 alert
- A3 ChannelWorkspace.tsx (模板)
- agent_alert/api.py + word_export.py + runtime_dump.py (grade 三处)
- `web/src/app/archive/alert/_components/AlertWorkspace.tsx` 现状
- `docs/contracts/agent-handoff-schemas.md` (A6 · grade schema 选项)

## 3. 红线
- ❌ 不跨 worktree / commit 缺 Signal / web 缺 PRESERVES
- ❌ A3 cherry-pick 前真动
- ❌ grade 命名你自己定 (等 A6 handoff schema · 没决就 raise Q-NNN)

## 4. ACK
- DONE: `WORKER-A4-ALERT-ADAPTER-DONE` · trailer 含 4 gate / done envelope / SMOKE-PASS / PRESERVES F-XXX / NEW-DOM / GRADE-FIELD-UNIFIED-AS=<name>

## 5. Codex
Pre-dispatch draft 落 `docs/audit/codex-drafts/A4-alert.md`

---
**主 CLI · 2026-04-29 · A4-alert (2 of 5)**
