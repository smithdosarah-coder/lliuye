verdict: AGREE

issue-1-fixed: yes  
`agent_compliance/scan_engine.py` at `183486c` now uses `shared.llm_caller.make_text_caller` and `make_json_caller` for both paths, with `_LLM_CALLER_AGENT_ID = "compliance"` and endpoint `/api/compliance/policy_scan`. I found no remaining direct `from llm import LLMClient` / `LLMClient` usage under `agent_compliance`.

issue-2-fixed-internal-only: yes  
Within the narrowed scope, the internal LLM caller agent id is now canonical `compliance`. The remaining `compli` occurrences I saw inside `agent_compliance/*` are legacy names/prefixes/tool labels such as `build_compli_provider`, `compli-{uuid}`, `compli_provider`, or data-dir naming, not the scoped caller `agent_id`.

Consumer cleanup remains out of V2 scope as裁决 said: `auth_service/rbac.py`, `web/src/components/shell/AuthGate.tsx`, and `web/src/lib/auth/agent-id.ts` still use `compli`.

issue-3-fixed: yes  
The Playwright T3 assertion now checks the revision linkage sentinel in `[data-testid="compli-violation-detail-revisions"]`, requires `sentinel-VIO-002-rev`, and negatively asserts `sentinel-VIO-001-rev` is absent. That validates filtered revision linkage, not just the article text.

remaining concerns:
- `auth_service/rbac.py`, `web/src/components/shell/AuthGate.tsx`, `web/src/lib/auth/agent-id.ts`: still `compli`, but accepted as Stage 4 cleanup.
- `agent_compliance/scan_engine.py:600`: persisted scan id prefix remains `compli-...`; not blocking under the narrowed internal-agent-id scope, but worth deciding during canonical-id cleanup if external artifacts should also move.