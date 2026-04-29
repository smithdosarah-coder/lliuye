# Worker-A4-report Onboarding · Report thin adapter (Phase A Week 4-5)

> 依赖 A3 cherry-pick 后真动 · Dispatch signal: `PHASE-A-A4-REPORT-DISPATCHED`

## 0. worktree
- `D:\claude code\work-A4-report` · branch `feat/phase-a4-report-adapter`
- resume: cd · git status clean · 干 §0.5

## 0.5. 前置 wait gate (硬)
A3 cherry-pick 之前 · 不真动 ReportWorkspace.tsx。检查 `git log chore/l0-infra | grep "A3-CHANNEL-PILOT\|A3-MERGED"`。
没 cherry-pick → read A3 + draft `docs/audit/A4-report-draft.md` · 等 GO `A4-REPORT-GO-AFTER-A3`。

## 1. 任务

| # | 交付 |
|---|---|
| 1 | `web/src/app/archive/report/_components/ReportWorkspace.tsx` 重构 4 gate (复用 A3 · report 5 panel = 材料 grid + 时间流 + A4 预览 + FieldChip 3 态 + 工具栏) — 现有 livePayload/liveFailErr 不是 liveData contract · 改 |
| 2 | `agent_report/api.py` event 名注释 V14-B → v16 align (audit cat 4) |
| 3 | `agent_report/api.py:264-301 _build_llm_caller` 删 (硬编 OpenAI · 第 4 套 caller) · 改用 A2 shared/llm_caller (audit cat 7-5) |
| 4 | `data/mock/workspace/report/scenarios/*.json` + `/api/report/demo/run` 端点 (报告生成 demo) |
| 5 | `web/tests/regression/report-pilot-4gate.spec.ts` smoke |
| 6 | export_pdf + 分享链接 + 版本时光机 真接后端 (现是 mock hook · prd-evidence-frozen G-10) — 至少 export_pdf 接通 · 后两个标 Phase B |
| 7 | `agent_report/mock_fixtures.py` disk fixture else embedded stub fallback 决议 (audit cat 5 · 跟 A2 shared 商) |

## 2. 必读
- RESET_MASTER_PLAN / north-star / phase-a-charter §3 worker-A4
- conflict-register-v1.md cat 2 report + cat 4 report (event 名漂) + cat 7-5 _build_llm_caller + cat 13 report export
- A3 模板
- agent_report/api.py (~600 行) + mock_fixtures.py
- A2 shared/llm_caller
- ReportWorkspace.tsx 现状
- v16_pipeline.py 主管线 (你 backend 改对接)
- prd-evidence-frozen.md G-10

## 3. 红线
- ❌ 不跨 worktree / commit 缺 Signal / web 缺 PRESERVES
- ❌ A3 cherry-pick 前真动
- ❌ 不破坏 v16 主管线 (PM 用真实材料跑过 · 但 wrapper unreleased · 你改 wrapper 不改主管线)
- ❌ legacy_gradio 默认 ImportError (A7 干 import guard · 你不动 · 但你 commit 改 agent_report wrapper 时 verify 没破坏 ALLOW_LEGACY_GRADIO emergency 路径)

## 4. ACK
- DONE: `WORKER-A4-REPORT-ADAPTER-DONE` · trailer 含 4 gate / event 名 v16 align / _build_llm_caller deleted / export_pdf 真接 / SMOKE-PASS / PRESERVES F-009..F-014 / NEW-DOM / wrapper-released-via-A2

## 5. Codex
Pre-dispatch draft 落 `docs/audit/codex-drafts/A4-report.md`

---
**主 CLI · 2026-04-29 · A4-report (5 of 5)**
