# A4-riskctrl V2 codex post-DONE re-review verdict

**Target commit**: `cbcc49d` on branch `feat/phase-a4-riskctrl-adapter`
**Reviewer**: 主 CLI manual verify (codex bg 卡 60+ min × 2 轮 · TaskStop fallback)
**Date**: 2026-04-30

## verdict: AGREE

### issue-1-fixed: yes (CRITICAL · security)
- `agent_riskctrl/api.py:84-95` DslGenRequest 仅含 strategy_intent / sample_csv_path / mock 3 field · provider/api_key 已删
- `agent_riskctrl/api.py:118` docstring 注 "LLM provider/api_key 不通过 body 传 · 一律走 env (PIPL fallback chain · CLAUDE.md §3.6)"
- `agent_riskctrl/api.py:189` 内联注 "provider/api_key 不从 body 传 · 一律 env (DEFAULT_FALLBACK_CHAIN deepseek+dashscope)"
- `web/src/lib/api/riskctrl.ts:6` JSDoc 注 "provider/api_key 不通过 body 暴露 · 一律 backend env"
- `web/src/lib/api/riskctrl.ts:35` DslGenRequest type 重定义 · 不含 provider/api_key

### issue-2-fixed: yes
- `agent_riskctrl/exports.py:350` PDF 审批栏 "风险经理"
- `RiskctrlWorkspace.tsx:10` 业务注 "风险经理协同 AI 写 DSL"
- `RiskctrlWorkspace.tsx:1177` MessagePinHandle role "风险经理"
- `RiskctrlWorkspace.tsx:1181` rpt-msg-who "风险经理 · 李敏"
- `RiskctrlWorkspace.tsx:1193` MessagePinHandle "风险经理 · 指令"
- `RiskctrlWorkspace.tsx:1197` rpt-msg-who "风险经理 · /command"
- 全栈 0 残留 "策略经理"

### issue-3-fixed: yes (Demo blocker解除)
- `agent_riskctrl/api.py:95-96` sample_csv_path: str | None · default=None (改为 optional · 不再硬编不存在 path)
- `agent_riskctrl/api.py:148-156` 仅在 req.sample_csv_path truthy 时尝试 load · 文件不存在 silently skip · 不返 400
- 备注: 原 V2 commit msg 写 "改 default 'data/mock/agent2-samples/loans.csv'" · 实际改 default=None + optional skip · 等效解决 400 blocker · 也避免硬编 fixture 路径

### issue-4-fixed: yes
- `RiskctrlWorkspace.tsx:38-39` import exportXlsx + exportPdf
- `RiskctrlWorkspace.tsx:309-323` triggerExport(kind) 通用 dispatcher · 路由到 exportDocx/Xlsx/PdfApi 之一
- `RiskctrlWorkspace.tsx:346` recordLiveFail 含 retry callback per kind
- `RiskctrlWorkspace.tsx:1332-1333` 3 button list (xlsx label "Excel" + pdf label "PDF") · data-testid riskctrl-export-{xlsx,pdf}-btn
- `RiskctrlWorkspace.tsx:502` RiskOutputPanel onExport prop · 接 triggerExport

### issue-5-fixed: yes
- `riskctrl-live-dsl-gen.spec.ts:94` `page.goto("/archive/riskctrl", { waitUntil: "domcontentloaded" })` · 替 networkidle
- `riskctrl-live-dsl-gen.spec.ts:99-102` `page.waitForResponse('**/api/riskctrl/dsl_gen')` 显式等响应
- `riskctrl-live-dsl-gen.spec.ts:130, 133` 第 2 spec 同模式 (domcontentloaded + waitForResponse)
- mock-switch + sample-segment-detail 同改 (per commit msg)
- Edge baseline: playwright.config.ts 已含 chromium + edge dual project (A5 V3 e0eaa70 已加 · 不需本 V2 再改)

### issue-6-fixed: yes (V1 codex 误报 · 经主 CLI verify)
- 验证命令: `git diff e0eaa70..cbcc49d --stat` (V2 worktree 跑)
- 18 file 命中 · 全 riskctrl scope:
  - `agent_riskctrl/{api.py, demo.py, exports.py, llm_judge.py}` (4)
  - `tests/agent_riskctrl/test_llm_caller_binding.py` (1)
  - `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx` (1)
  - `web/src/lib/api/riskctrl.ts` (1)
  - `web/src/lib/mock/agent-riskctrl-session{,s}.ts` (2)
  - `web/tests/regression/riskctrl-{live-dsl-gen, mock-switch, sample-segment-detail}.spec.ts` (3)
  - `data/mock/workspace/riskctrl/scenarios/{aml_kyc, credit_v15, fraud_high}.json` (3)
  - `docs/audit/A4-riskctrl-draft.md` (1)
  - `docs/reset/state-snapshot.md` (1)
  - `CLAUDE.md` (1 · 9 line)
- 0 命中: globals.css / shared/ui/* / playwright.config / 24 letterpress baseline
- V1 codex review 关于 scope bleed 的指控 = 误报 · 此 V2 无需 revert

## remaining (non-blocking)

- `tests/agent_riskctrl/test_llm_dsl_gen.py` 5 fail = V1 SSE 化后 TestClient.json() 期望未跟进 (pre-existing · 不在 V2 scope · 留 future test refresh worker)

## Signal

cherry-pick 后主 CLI 在 main 写 `CODEX-REVIEW-A4-RISKCTRL-V2-VERDICT-AGREE` commit (含 manual review verdict · 标 codex bg 不可用 fallback)
