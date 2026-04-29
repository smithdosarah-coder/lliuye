# Worker-A4-compli Onboarding · Compliance thin adapter (Phase A Week 4-5)

> 依赖 A3 cherry-pick 后真动 · Dispatch signal: `PHASE-A-A4-COMPLI-DISPATCHED`

## 0. worktree
- `D:\claude code\work-A4-compli` · branch `feat/phase-a4-compli-adapter`
- resume: cd worktree · git status clean · 干 §0.5

## 0.5. 前置 wait gate (硬)
A3 cherry-pick 进 chore/l0-infra 之前 · 不真动 ComplianceWorkspace.tsx。
- `git log chore/l0-infra | grep "A3-CHANNEL-PILOT\|A3-MERGED"` 检查
- 没 cherry-pick → read A3 模板 + draft `docs/audit/A4-compli-draft.md` · 等 GO
- cherry-pick → rebase + 照搬

主 CLI GO: `A4-COMPLI-GO-AFTER-A3`

## 1. 任务

| # | 交付 |
|---|---|
| 1 | `web/src/app/archive/compliance/_components/ComplianceWorkspace.tsx` 重构 4 gate (复用 A3 · compliance 5 panel = 政策矩阵 + 违规榜单 + 修订意见 + 业务单号 + 政策事件) |
| 2 | `agent_compliance/api.py` done event 加完整 envelope (现 done 空 · audit cat 4) |
| 3 | SSE reader 改 streamSse |
| 4 | `data/mock/workspace/compliance/scenarios/*.json` + `/api/compliance/demo/run` 端点 |
| 5 | `web/tests/regression/compliance-pilot-4gate.spec.ts` smoke |
| 6 | agent_id 用 `compliance` (PM 拍板 · A1 SSOT 8 列单 id) · `compli` 别名 (RBAC backend) 保留兼容 — 等 A1 V2 SSOT + A4-compli 同步 |

## 2. 必读
- RESET_MASTER_PLAN / north-star / phase-a-charter §3 worker-A4
- conflict-register-v1.md cat 2 compliance + cat 4 compliance + cat 8 compli/compliance + cat 11 compliance (cat 11-5 Codex 标 Keep · live fail banner 已实装)
- A3 模板
- agent_compliance/api.py + scan_engine.py
- ComplianceWorkspace.tsx 现状
- A1 docs/contracts/agent-naming-ssot.md (PM 拍板 compliance 单 id)

## 3. 红线
- ❌ 不跨 worktree / commit 缺 Signal / web 缺 PRESERVES
- ❌ A3 cherry-pick 前真动
- ❌ live fail banner 已实装 (cat 11-5 · 不要破坏)

## 4. ACK
- DONE: `WORKER-A4-COMPLI-ADAPTER-DONE` · trailer 含 4 gate / done envelope / agent-id 统一为 compliance / SMOKE-PASS / PRESERVES / NEW-DOM

## 5. Codex
Pre-dispatch draft 落 `docs/audit/codex-drafts/A4-compli.md`

---
**主 CLI · 2026-04-29 · A4-compli (3 of 5)**
