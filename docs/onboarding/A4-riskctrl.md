# Worker-A4-riskctrl Onboarding · Riskctrl thin adapter (Phase A Week 4-5)

> 依赖 A3 cherry-pick 后真动 · Dispatch signal: `PHASE-A-A4-RISKCTRL-DISPATCHED`

## 0. worktree
- `D:\claude code\work-A4-riskctrl` · branch `feat/phase-a4-riskctrl-adapter`
- resume: cd · git status clean · 干 §0.5

## 0.5. 前置 wait gate (硬)
A3 cherry-pick 之前 · 不真动 RiskctrlWorkspace.tsx。检查 `git log chore/l0-infra | grep "A3-CHANNEL-PILOT\|A3-MERGED"`。
没 cherry-pick → read A3 + draft `docs/audit/A4-riskctrl-draft.md` · 等 GO `A4-RISKCTRL-GO-AFTER-A3`。

## 1. 任务

| # | 交付 |
|---|---|
| 1 | `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx` 重构 4 gate (复用 A3 · riskctrl 5 panel = DSL editor + KS + 通过率 + 坏账率 + 案例诊断) |
| 2 | `agent_riskctrl/api.py` 改 SSE (charter 写"非 SSE" · 但前端 riskctrl.ts:44 期待 SSE · 看 audit cat 3 + cat 4 镜像) — 决定: 加 SSE done envelope · 跟 6 agent 共形 |
| 3 | `agent_riskctrl/llm_judge.py` (现独立 LLMJudge 基类 · audit cat 7 caller 3) 改用 A2 shared/llm_caller |
| 4 | `agent_riskctrl/api.py` 不暴露 provider 给前端 (现 line 141 LLMClient(provider=req.provider) · audit cat 7) |
| 5 | `data/mock/workspace/riskctrl/scenarios/*.json` + `/api/riskctrl/demo/run` 端点 |
| 6 | `web/tests/regression/riskctrl-pilot-4gate.spec.ts` smoke |
| 7 | export_docx + export_xlsx endpoint (audit cat 13 · 现后端 0 · 前端调 404) |

## 2. 必读
- RESET_MASTER_PLAN / north-star / phase-a-charter §3 worker-A4
- conflict-register-v1.md cat 2 riskctrl + cat 3 riskctrl + cat 4 riskctrl + cat 7 (caller 3 + 5) + cat 13 riskctrl export
- A3 模板
- agent_riskctrl/api.py + llm_judge.py
- A2 shared/llm_caller (你 import 替代 llm_judge)
- RiskctrlWorkspace.tsx 现状

## 3. 红线
- ❌ 不跨 worktree / commit 缺 Signal / web 缺 PRESERVES
- ❌ A3 cherry-pick 前真动
- ❌ provider 选择不暴露给前端 (audit cat 7)
- ❌ 角色文案对齐 "风险经理" (不是"策略经理" · audit cat 16 · 你 prompt / UI 改)

## 4. ACK
- DONE: `WORKER-A4-RISKCTRL-ADAPTER-DONE` · trailer 含 4 gate / SSE done / llm_judge 迁 A2 / export endpoints / SMOKE-PASS / PRESERVES / NEW-DOM / 角色文案"风险经理"

## 5. Codex
Pre-dispatch draft 落 `docs/audit/codex-drafts/A4-riskctrl.md`

---
**主 CLI · 2026-04-29 · A4-riskctrl (4 of 5)**
