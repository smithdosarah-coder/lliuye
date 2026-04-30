verdict: DISAGREE

4-gate-state: partial  
sse-done-envelope: yes  
llm-caller-migrated: yes  
provider-not-exposed: no  
export-endpoints: partial  
role-风险经理: no  
demo-3-fixture: yes  
smoke-pass: partial/no

**Issues**

1. **Hard-line violation: provider is still exposed through the riskctrl API/client.**  
   At `13c7fb7:agent_riskctrl/api.py:98-99`, `DslGenRequest` still accepts `provider` and `api_key`; at `api.py:190-200`, request provider mutates the fallback chain. The frontend type/body also exposes and sends these fields at `web/src/lib/api/riskctrl.ts:39-40` and `:83-88`. This conflicts with onboarding §1/#4 and §3: “provider 选择不暴露给前端.”

2. **Hard-line violation: “策略经理” remains in runtime/user-facing paths.**  
   `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx:10` still documents the workflow as “策略经理协同 AI”, and message UI still uses “策略经理” around `:1012-1032` in the submitted diff context. Export PDF approval uses `agent_riskctrl/exports.py:350` `"策略经理"`. Onboarding requires role wording to align to “风险经理”.

3. **Live backtest path is effectively not functional by default.**  
   Frontend sets `lastSampleCsvPath` to `"samples/sample.csv"` at `RiskctrlWorkspace.tsx:211-212`, but that file does not exist in the submitted tree. Backend rejects missing CSV with `CSV_NOT_FOUND` before backtest. So DSL generation may work, but the live “run backtest → liveData” flow fails unless a hidden/nonexistent path is supplied.

4. **Export delivery is incomplete from the UI side and still carries stale fallback behavior.**  
   Backend adds docx/xlsx/pdf endpoints, but `RiskctrlWorkspace.tsx:299-327` still says backend export is not delivered and treats 404 as “Stage D pending”. The UI only wires docx; `exportXlsx` and `exportPdf` exist only in `web/src/lib/api/riskctrl.ts:196-201` and are unused. If the acceptance is endpoint-only this is partial, but the workspace does not expose the promised trio.

5. **Smoke evidence is weak and likely not hermetic.**  
   The riskctrl specs use `page.goto(..., { waitUntil: "networkidle" })` (`riskctrl-mock-switch.spec.ts:47`, `riskctrl-sample-segment-detail.spec.ts:45`), while the same commit comments elsewhere say Next dev long polling means not to use `networkidle`. Also `playwright.config.ts:49-59` runs both Chromium and Edge, but the new screenshot baselines are Chromium-only. That makes “SMOKE-PASS” hard to trust without actual command output.

6. **Scope bleed: A4-riskctrl includes A5/global styling work.**  
   The branch changes `globals.css`, shared UI/viz components, Playwright global config, and adds 24 letterpress screenshot baselines. That is outside the Riskctrl thin adapter scope and increases cherry-pick/merge risk with A5.

**Strengths**

- Backend `dsl_gen` and `backtest` now use `StreamingResponse` plus `shared.sse_envelope.make_done`, which matches the flat done envelope pattern.
- `llm_judge.py` no longer imports root `LLMClient`; it binds `LLMCaller(agent_id="riskctrl", endpoint="judge")`.
- Three riskctrl demo fixtures and `/api/riskctrl/demo/run` are present.
- Mock session array and selected-session wiring are a real improvement over the prior single const.

I would not cherry-pick as DONE until provider exposure and “风险经理” wording are fixed, and the smoke claim is backed by a clean run on the submitted branch.