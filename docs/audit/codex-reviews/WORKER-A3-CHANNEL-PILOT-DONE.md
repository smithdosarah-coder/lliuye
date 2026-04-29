verdict: DISAGREE

reasoning: The core 4-gate refactor is mostly present, but DONE overclaims the acceptance bar. The demo path is not wired or covered by Playwright, one of the “5 panels” still uses separate state rather than `sessionData`, and live backend `data_source` still emits `"tavily"` instead of the envelope enum.

4-gate-state-implemented: yes (`started/selectedSession/liveData/selectedCandidate` present)

5-panel-derived-from-result: partial

streamSse-used: yes

done-envelope-fields: candidates, metrics, data_source, radar, signals, funnel, match_dimensions, product_recommendations, pitch_scripts

banner-spec-rule-2-implemented: yes

smoke-pass: partial. A Playwright spec exists and is reported pass, but it does not exercise `/api/channel/demo/run`, and the drawer assertion is conditional.

a4-template-readiness: usable as a partial template for A4. Best parts to copy: `sessionData = liveData ?? mock[selectedSession]`, `streamSse` integration, backend `make_done(panels=...)`, and warning-to-banner flow. Do not copy the conversation-state pattern or the weak smoke assertions.

specific issues:
- `web/src/app/archive/channel/_components/ChannelWorkspace.tsx:212`, `:461`, `:1465`: `ConversationPanel` is not derived from `sessionData`; it renders separate `messages` state initialized from the initial mock session and only reset on mock session switch. Live `setLiveData(live)` does not update `messages`, so the “conversation” panel can stay on stale mock data while the other panels swap to live. Alternative: either render `ConversationPanel` from `sessionData.conversation` directly, or set live conversation together with `setLiveData`, e.g. `setMessages(live.conversation)` after `normalizeBackendDone`.
- `web/tests/regression/channel-pilot-4gate.spec.ts:70-71`, `docs/features-inventory.md:1000-1002`: onboarding required demo run smoke, but the Playwright test mocks `/api/channel/run`; `/api/channel/demo/run` is not wired in the UI and the inventory explicitly says the demo button is deferred. Alternative: add a UI control for easy/medium/hard that calls `/api/channel/demo/run` through the same `streamSse` path, then add a Playwright case that intercepts or hits that endpoint and asserts `data_source="mock_forced"` plus 5 panels.
- `agent_channel/realtime_stream.py:190`, `:249-253`, `:269`, `:491`: successful live Tavily results still produce `data_source="tavily"` because the enum normalization is a no-op for non-enum values. That breaks the shared `DATA_SOURCE_LIVE/mock_forced/mock_fallback` contract and makes A4 copy a bad pattern. Alternative: map provider source to the envelope enum: `ds_for_envelope = DATA_SOURCE_LIVE if data_source == "tavily" else data_source`; if the UI needs provider detail, add `provider_source="tavily"` separately.
- `web/tests/regression/channel-pilot-4gate.spec.ts:159-169`: gate-4 smoke does not fail if the drawer never opens. It explicitly treats missing drawer visibility as acceptable, so it cannot prove `selectedCandidate` is functional. Alternative: click `[data-testid="channel-candidate-card"]`, require `[data-testid="channel-candidate-drawer"]` visible, then press Escape and require it hidden.

strengths:
- The 4 gate variables and `sessionData` single derivation are present and clear.
- Backend `make_done(panels=...)` now emits the 7 Channel panel keys.
- Tavily fallback warnings are surfaced through stage warning and `done.warnings`.
- The new scenario JSON endpoint is useful once wired into the UI/test path.