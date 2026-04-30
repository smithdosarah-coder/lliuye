verdict: DISAGREE

issue-1-fixed: partial  
issue-2-fixed: yes  
issue-3-fixed: yes  
issue-4-fixed: yes

remaining concerns:
- `web/src/app/archive/channel/_components/ChannelWorkspace.tsx:212`, `:463`, `:752`: `ConversationPanel` still renders from separate `messages` state, not directly from `sessionData.conversation`. V2 does call `setMessages(live.conversation)` after `setLiveData(live)`, which fixes the worst stale-state path from V1, but `normalizeBackendDone()` still returns `{ ...tplFallback, ... }` and does not read any backend/demo `conversation` field. So the conversation panel is reset to the current mock template conversation, not truly derived from the done result.
- `web/src/app/archive/channel/_components/ChannelWorkspace.tsx:1373`: `normalizeBackendDone()` hydrates candidates/radar/signals/funnel, but not conversation. If “5 panels derived from result” is still the bar, this remains partial.
- Minor test limitation: `web/tests/regression/channel-pilot-4gate.spec.ts` T5 wires and hits `/api/channel/demo/run` and injects `data_source: "mock_forced"`, but it does not independently assert a rendered `data_source` value. This is acceptable for issue 2 because endpoint wiring and panel hydration are now covered.

Confirmed fixed:
- Issue 2: demo UI buttons exist and call `/api/channel/demo/run`; Playwright T5 verifies endpoint hit, `scenario_id="medium"`, live-mode hydration, 5 visible panels, candidate replacement, and no fallback banner.
- Issue 3: live Tavily is normalized to `DATA_SOURCE_LIVE` with `provider_source="tavily"` on stage and done events. `make_done(..., data_source=data_source, **done_extras)` no longer emits `"tavily"` as `data_source`.
- Issue 4: drawer smoke is now mandatory via `[data-testid="channel-candidate-card"]` click, `[data-testid="channel-candidate-drawer"]` visible, Escape hidden. No conditional skip remains.

Net: V2 resolves 3 of 4 prior blockers. The remaining gap is narrower than V1, but the conversation panel is still not a true result-derived/sessionData-derived panel.