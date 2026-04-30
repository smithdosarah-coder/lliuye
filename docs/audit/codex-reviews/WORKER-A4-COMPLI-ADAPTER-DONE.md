verdict: DISAGREE

4-gate-state: yes  
done-envelope: yes  
llm-caller-migrated: no  
agent-id-compliance: no  
demo-3-scenarios: yes  
smoke-pass: partial  
live-fail-banner-preserved: yes

**Issues**

1. `llm-caller-migrated` is not done.  
   `agent_compliance/scan_engine.py:78-106` still builds local callers via `from llm import LLMClient` for both text and JSON paths. The Phase A hardline explicitly required `agent_compliance/scan_engine.py` to move to A2 `shared/llm_caller`. This is a direct miss.

2. `agent-id-compliance` is not done.  
   The commit message defers it, but the DONE schema asks for it. Evidence:
   `auth_service/rbac.py:10-14`, `:23-37`, `:42` still use `compli`.
   `web/src/components/shell/AuthGate.tsx:21` still matches `/archive/.../compli/...`, not `compliance`.
   `web/src/lib/auth/agent-id.ts:16` still maps `compliance: "compli"`.
   So the full-stack canonical id remains split.

3. Smoke is only partial against the claimed contract.  
   The new Playwright spec validates synthetic SSE and demo wiring, but it does not catch the two contract misses above. It also doesn’t assert the linked revision sentinel in T3; it only checks `第十九条` in the detail panel, so the “修订意见联动” assertion is weaker than the comment claims.

**Strengths**

The backend SSE envelope work is materially good: `agent_compliance/api.py:182-230` intercepts the persisted scan event, loads the full result, and emits `make_done(...)` with compliance panels and metrics. `/api/compliance/demo/run` plus the three scenario JSON files are present and shaped consistently.

The frontend does implement the 4 gate state model and wires live/demo done envelopes into `liveData`, with auto-select for the first violation. The live-fail banner path appears preserved.

Bottom line: good adapter progress, but not DONE against the submitted acceptance schema because two explicit Phase A requirements remain unimplemented.