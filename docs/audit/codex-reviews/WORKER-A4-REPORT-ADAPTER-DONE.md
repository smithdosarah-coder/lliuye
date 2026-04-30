verdict: DISAGREE

4-gate-state: partial  
done-envelope-v16-align: partial  
build_llm_caller-deleted: yes  
demo-endpoint-3-scenarios: yes  
export_pdf-real: partial  
smoke-pass: partial  
v16-pipeline-not-broken: yes, but live/export contract still incomplete

**specific issues**

1. `ReportWorkspace.tsx:1352-1359`, `855-856`, `941-943` still render the core panels from static `REPORT_SESSION`, not from a `sessionData = liveData ?? selectedSession` contract. `liveSections` only toggles `data-mode`; A4 preview, material grid, timeline, FieldChip counts/content do not hydrate from demo/live data.  
   替代: introduce report mock session list + normalized live session shape, then derive all five panels from one `sessionData`.

2. `agent_report/api.py:1010-1025` creates `session_id = demo_report_*` in the done payload, but calls `store.create(...)` and ignores the returned UUID. Later `/api/report/refine_section` using the emitted `session_id` will 404.  
   替代: assign `session_id = store.create(...)` before building `done_payload`, or extend the store to accept caller-provided IDs.

3. `agent_report/v16_runner.py:268-288` real v16 `done` still lacks top-level `sections` and `profile`, despite the documented v16 envelope in `agent_report/api.py:21-22`. Frontend export/refine paths assume `liveData.sections` exists (`ReportWorkspace.tsx:323-329`, `404-410`).  
   替代: normalize/stash real v16 output into `{session_id, report_id, pipeline, sections, profile, qc, stats, pending_questions}` and persist `done_payload` in `SessionStore`.

4. `agent_report/api.py:1052-1053` implements `/api/report/export_pdf`, but share/version are only disabled Phase B buttons (`ReportWorkspace.tsx:1452-1469`) and no `/api/report/share` or `/api/report/version` endpoints exist. This is acceptable only under the onboarding’s “至少 export_pdf” carve-out, not full G-10 completion.

5. `agent_report/mock_fixtures.py:154-181` appears unchanged for cat 5. The disk-fixture-else-embedded-stub behavior is still present, but there is no visible “决议” beyond keeping it. If the expected outcome was “documented decision to preserve fallback,” this is under-evidenced.

6. `web/tests/regression/report-pilot-4gate.spec.ts` is useful, but it mainly checks testids/mode flags and endpoint hits. It would not catch issue #1 because it never asserts panel content switches to the demo scenario. No test run output was provided, so `smoke-pass` cannot be marked yes from the diff alone.

**strengths**

- `_build_llm_caller` is correctly moved to `shared.llm_caller.make_text_caller` (`agent_report/api.py:267-280`).
- `/api/report/demo/run` plus easy/medium/hard scenario fixtures are present.
- PDF export is a real backend route using `reportlab`, with frontend toolbar wiring.
- The live-mode DeepSeek guard in `report_v16_fill` is retained, so the v16 runner path is not obviously broken by this patch.