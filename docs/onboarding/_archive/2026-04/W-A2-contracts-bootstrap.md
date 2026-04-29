# Worker A2 · Contracts Bootstrap · Onboarding

> Task spec for worker CLI in worktree `work-A2-contracts` (branch
> `feat/contracts-bootstrap-A2`). Read this + `AGENT_IDENTITY.md` on
> resume, then start work.

## Goal

Write 3 protocol contract docs that define the cross-cutting architecture
patterns Stage B+ workers (Channel/Report/etc PRD-grade implementation)
will follow. These contracts make worker dispatch deterministic — each
Stage B worker reads its agent-spec + these protocols and knows exactly
what shape state/IM/auth must take.

## Deliverables

### 1. `docs/contracts/workspace-state-protocol.md`

Defines the architecture every archive Workspace MUST follow:
- `useState started` gate (default false → 空白等待 · only render Hero + QueryBar + empty hint)
- `useState selectedSession` (mock_sessions map · 切下拉切到该 session 的全 panel data)
- `useState liveData` (SSE done event injects · panels prefer live, fallback selectedSession.mock)
- `useState selectedCandidate` (click candidate → drawer detail · 8-axis radar / signal timeline derived per candidate)
- All panel functions take `props sessionData` instead of `import CHANNEL_SESSION` (delete static import)
- Mock_sessions shape: `{ [sessionId]: { radar, signals, candidates, funnel, conversation, query, ... } }` — at least 3 sessions per Workspace
- Backend SSE done event MUST emit `radar` / `signals` / `funnel` (not just `candidates`) — frontend can hydrate full state
- Trigger sources for `setStarted(true)` and `setSelectedSession(id)`:
  - select 历史 session dropdown
  - submit textbox (live mode)
  - upload file (KB mode · per PRD v2)
- Reference current Channel implementation as template (`web/src/app/archive/channel/_components/ChannelWorkspace.tsx` post-2026-04-27)

### 2. `docs/contracts/im-protocol.md`

Defines the IM system architecture:
- 5 user fixed accounts (passwords in PASSWORD_MAP) · login backend `/api/auth/login` (JWT later)
- Thread persistence: lightweight DB (sqlite or jsonl) backend `/api/im/threads` `/api/im/messages/{thread_id}`
- WebSocket upgrade path: `/ws/im` for realtime push (replaces polling fetch)
- Tool calling: `/api/im/send` upgraded with LLM intent detection — when user says "找/搜/扫", LLM emits tool call
  invoking the corresponding agent SSE (e.g. `/api/channel/run`) — result injected back into thread as `kind="agent_output"` message
- @agent routing: composer parses `@报告/获客/...` → target_agent → backend selects agent system prompt
- Multi-user 1:1 chat: thread = pair of user IDs (or group thread)
- Drop-from-canvas: composer onDrop accepts PANEL_PIN_MIME / CARD_PIN_MIME · message rendered as thumbnail card (kind="pin_ref"), not URL link
- Frontend MessageBubble uses `wc-msg` wechat bubble style (not `dpx-msg` legacy grid)

### 3. `docs/contracts/auth-protocol.md`

Defines auth + RBAC architecture:
- Login: `POST /api/auth/login` · accept `{user_id, password}` · return `{token, user, roles}`
- 5 fixed accounts (preserve current PASSWORD_MAP shape) · backend hash + verify
- JWT token stored in httpOnly cookie · frontend reads via `/api/auth/me`
- RBAC: ACCESS matrix (auth-store.ts already defined) — frontend AuthGate enforces
  - rm: 6 agent all
  - credit_officer: credit + report + alert
  - compliance_officer: compli + report + alert
  - risk_manager: riskctrl + alert + credit
  - admin: all
- Frontend redirect to /403 if user accesses unpermitted /archive/*
- Logout: POST /api/auth/logout · clears cookie · redirect /login

## Acceptance

- 3 doc files created under `docs/contracts/`
- Each doc ≥ 80 lines · clear sections · code examples for key data shapes
- Cross-references to current code (file paths · line numbers · existing types)
- Each doc lists "Migration path" for refactor (which files change · in what order)
- Commit on `feat/contracts-bootstrap-A2` with trailer:
  ```
  Signal: WORKER-A2-CONTRACTS-BOOTSTRAP-DONE
  ```

## Boundary

- Write ONLY: 3 new files under `docs/contracts/`
- Read-only: existing code under `web/src/`, `agent_*/`, `api_server.py`
- DO NOT modify: code · CLAUDE.md · other docs · existing contracts in `docs/contracts/rfc/`

## Dependencies

- Master plan: `docs/contracts/master-execution-plan-2026-04-27.md` § Stage A.4
- Existing Channel implementation as state-protocol reference template
- Existing api_server.py `/api/im/send` as IM-protocol baseline
- Existing auth-store.ts ACCESS matrix as RBAC reference

## Trailer protocol

```
Signal: WORKER-A2-CONTRACTS-BOOTSTRAP-DONE
```

## On completion

1. `git add docs/contracts/ && git commit -m "..."` with trailer
2. `git push origin feat/contracts-bootstrap-A2`
3. Main CLI reviews 3 docs · checks shape clarity + migration path completeness
4. Main CLI cherry-pick / merge to `chore/l0-infra`

## Estimated effort

3-4 hr — careful spec writing · examples · cross-refs.
