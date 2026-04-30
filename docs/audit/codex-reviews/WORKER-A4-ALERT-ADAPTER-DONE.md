verdict: DISAGREE

4-gate-state: partial  
done-envelope-cat-4: yes  
llm-caller-migrated: yes  
grade-unified: no  
demo-endpoint-3-scenarios: yes  
smoke-pass: partial

specific issues:

1. `grade-unified` does not follow A6 schema. `docs/contracts/agent-handoff-schemas.md:430` says Agent4 maps into its hitlist `tier` field, and `docs/contracts/agent-handoff-schemas.md:720` defines alert filters as `{session_id, tier?, client_ids?}`. Worker instead rewrote frontend alert objects to `risk_level` in `web/src/lib/mock/agent-alert-sessions.ts` and normalizes to `risk_level` in `web/src/app/archive/alert/_components/AlertWorkspace.tsx:155` / `:169`. That violates onboarding §1 #6 “per A6 handoff schema”. Fix: either update A6 schema first, or revert Agent4 public/internal alert grade field to `tier` and only keep `risk_level` as backend/export compatibility input.

2. Live done envelope is not actually propagated to all 5 alert panels. `normalizeAlertSession()` only updates `totals`, `distribution`, `signalHeatmap`, `reach`, and `topCases` (`AlertWorkspace.tsx:138-178`). But the main hitlist/queue shown after scan is derived from `sessionData.scanSnapshotAfter.queue` via `currentQueue = phase === "after" ? after.queue : sessionData.scanQueueCases` (`AlertWorkspace.tsx:240-244`). Since `scanSnapshotAfter` is never rebuilt from backend `hit_list`, live scan can show live totals/topCases while the queue/hitlist remains fallback mock. Fix: derive `scanQueueCases` and `scanSnapshotAfter.queue/heat/sources/kbState/summary` from done payload, especially `hit_list.red/yellow/green`.

3. Live `session_id` is dropped by the frontend scan client. Backend `make_done()` puts `session_id` at top level, but `runAlertScan()` only reads `evt.data.payload.type === "session"` (`web/src/lib/api/alert.ts:53-59`). The UI then passes `scanSessionId` into live drill (`AlertWorkspace.tsx:742-743`), but that state is never set from the done event. Fix: in `runAlertScan`, read top-level `evt.data.session_id` when `evt.type/event === "done"`.

4. Smoke coverage is overstated. `alert-pilot-4gate.spec.ts` skips the `/api/alert/demo/run` integration unless `ALERT_BACKEND_URL` is set (`web/tests/regression/alert-pilot-4gate.spec.ts:285-287`), so the claimed 8-spec smoke is not hermetic by default. The live-data test also only checks `data-live-mode`/disabled select and does not assert that the live totals, hitlist, or visible top case changed, so issue #2 would pass.

strengths:

- The 4 gate state variables are present and wired at the root level.
- Backend `/api/alert/scan` now emits stage and non-empty done events via `shared.sse_envelope`.
- `/api/alert/demo/run` and 3 scenario fixtures are present.
- `/api/alert/drill` caller was moved to `shared.llm_caller.make_text_caller`.

Bottom line: substantial work landed, but onboarding §1 is not fully met because grade naming contradicts the A6 schema and live done data does not drive all alert panels.