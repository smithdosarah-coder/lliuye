verdict: DISAGREE

4-gate-state: partial  
done-envelope-symmetric: yes  
streamSse: yes  
demo-6-scenarios: partial  
agent6-handoff-real: partial/no  
smoke-pass: partial

Specific issues:

1. Live normalization reintroduces stale mock red lines when backend returns zero hits. In `web/src/app/archive/credit/_components/_normalize.ts:170`, `if (!hits || hits.length === 0) return fallback;` means an approved live/demo result with `rule_hits: []` keeps the fallback session’s red lines. This directly breaks “done envelope hydrate → panel single source” and will show false risk warnings/fails for clean cases. Same pattern exists for `case_matches: []` at `_normalize.ts:189`.

2. Agent6 handoff is not really discoverable from Agent6 output. `agent_credit/api.py:323-339` lists only `demo_data/agent_credit/*.json` and always returns `source: "phase_a_demo_data"`. The real archive path exists only in `handoff_from_report` for manually supplied non-demo IDs (`agent_credit/api.py:371-379`), but the frontend only chooses from the demo list. So EmptyState primary consumes a ReportJSON-shaped fixture, not real Agent6 sessions.

3. The frontend same-origin `/api/credit/*` calls have no Next rewrite. `web/next.config.ts:22-33` proxies `/api/report/*` and `/api/auth/*`, but not `/api/credit/*`. Unless `NEXT_PUBLIC_API_BASE` is set externally, `/api/credit/reports/sessions`, `/handoff/from_report`, `/decision`, `/demo/run`, and `/export_docx` hit the Next app and 404. The tests mask this by route interception.

4. Smoke tests contain silent no-op branches. `web/tests/regression/credit-pilot-4gate.spec.ts:306-316` lets the drawer test pass if no case row appears, and `:376-385` lets export-error pass if no export button appears. Those are the two new UI fixes with the highest regression risk; they should fail if the feature is absent.

Strengths:

- The backend done envelope is materially improved for mock/live paths.
- The inline SSE reader is replaced with the shared `streamSse`.
- Six scenario JSON files exist and `/api/credit/demo/run` is a reasonable fixture-backed path.
- The 4 gate structure is present, but the stale-fallback normalization weakens the liveData contract.

I would not cherry-pick this as DONE until the stale fallback behavior, real handoff discovery/proxy path, and non-skipping Playwright assertions are fixed.