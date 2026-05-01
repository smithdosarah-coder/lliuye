# Worker-B1 Onboarding · 数据飞轮 Phase B gate (Phase B Sprint 1)

> Phase B-1 (Week 1-3) sprint 1 · Codex R2 缩 scope (vs 主 CLI 原 3 周 · 不重 A/B 平台)
>
> Dispatch signal: `PHASE-B-SPRINT-1-DISPATCHED`

## 0. worktree

- `D:\claude code\work-B1-flywheel` · branch `feat/phase-b1-flywheel` (新建 · 已 checkout)
- resume: cd worktree · `git status` (clean) · 直接干 §1

## 1. 任务 (per `docs/reset/phase-b-charter.md` v2 worker-B1 + `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE10)

| # | 交付 |
|---|---|
| 1 | `/api/feedback` endpoint 真接 audit modify (vs 现 PoC) · 写 `data/feedback/YYYY-MM-DD.jsonl` |
| 2 | `evaluation/runner/cli.py` 跑 6 agent baseline · 输出 `evaluation/baselines/agent_{n}_2026-XX-XX.json` (含 evidence_rate / hallucination_rate / field_completeness 红线指标) |
| 3 | blocker_threshold 阻断发布 (per `evaluation/README.md:7-10, 32-39` 规则) |
| 4 | `scripts/inject_fewshot_to_prompts.py` 真跑通 · 把高质量 feedback 注入 `agent_*/prompts.py` few-shot (PoC 级 · 不重 A/B framework) |
| 5 | `docs/runbook/feedback-flywheel.md` runbook |

## 2. 必读

- `RESET_MASTER_PLAN.md`
- `docs/reset/phase-b-charter.md` v2 (Stream 3 worker-B1)
- `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE10 (Codex R2 缩 scope 决议)
- `docs/research/two-way-debate-backend-r2-codex-2026-05-01.md` §1.6 (反对重 A/B 平台理由)
- `evaluation/README.md` (baseline + blocker_threshold 现规则)
- CLAUDE.md §6 (数据飞轮四环)

## 3. 红线 (per Codex R2)

- ❌ **不要做重 A/B test 平台** (Phase B 缩成 thin gate · 未来真 production 走 Phase C)
- ❌ 不跨 worktree
- ❌ commit 不带 `Signal:` trailer (per Q-043 codex protocol v2 · 必含 `REVIEW-MODE` + `REASONING-EFFORT` + `ELAPSED`)
- ❌ 改 backend code 不跑 evaluation baseline 验 (per evaluation/README.md 硬规)

## 4. ACK

DONE commit `Signal: WORKER-B1-FLYWHEEL-DONE` · trailer:
```
BE-DELIVERED: BE10 (数据飞轮 Phase B gate)
FEEDBACK-ENDPOINT: /api/feedback 真接
BASELINE-AGENTS: 6/6 跑通
BLOCKER-THRESHOLD-ACTIVE: yes
FEW-SHOT-INJECT-POC: yes
RUNBOOK: docs/runbook/feedback-flywheel.md
PRESERVES: F-XXX (worker-B1 不动现有 feature · 仅加 endpoint)
HARDLINE-PHASE-B-#1: met
```

## 5. Codex (插入点 1+2 per Q-043 protocol v2)

Pre-dispatch draft 落 `docs/audit/codex-drafts/B1-flywheel.md` (worker 启动后立即 fire codex pre-dispatch · medium reasoning · ~10 min)

Post-DONE Codex review (主 CLI fire · 等 verdict cherry-pick to main)

---

**Author**: 主 CLI · 2026-05-01 · Worker-B1 (Phase B Sprint 1 · 1 of 4)
