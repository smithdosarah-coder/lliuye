# Worker A3 (Stage D 第 1 批) · IM WebSocket + Thread DB backend · Onboarding

> Worker CLI 在 `D:/claude code/work-A3-prd` (branch `feat/prd-summaries-A3`) ·
> 复用 worktree。
> 上批 Stage CF2 Riskctrl frontend (`2e0f49f`) 已 cherry-pick MERGED (`a9e12af`) ·
> 本批 Stage D.2 + D.3 启动 (合并)。

## Goal

实装 master plan §D.2 + §D.3 — IM WebSocket 实时 + Thread/Messages 持久化 sqlite ·
按 `docs/contracts/im-protocol.md` v1.0 spec 落地。
**gap #11 (WebSocket 实时 IM) backend 闭环** · production 必修 (现 polling fetch
单 turn · 不真实时 · 多 user 1:1 不可信)。

## Acceptance

- [ ] **必读** `docs/contracts/im-protocol.md` v1.0 全文 (cherry-pick a660019)
- [ ] **WebSocket `/ws/im`** FastAPI WebSocket endpoint:
  - 连 require JWT cookie (复用 D.1 auth-protocol)
  - message types: `chat` / `pin_ref` / `agent_output` / `system`
  - 重连 backoff (frontend 处理 · backend 配合 ping/pong · 60s timeout)
  - 1:1 thread 用 user_id pair · group thread 用 thread_id
- [ ] **Thread persistence sqlite** · `data/im/threads.db`:
  - tables: `threads (id, type, user_a, user_b, group_id, created_at)` ·
    `messages (id, thread_id, sender_id, kind, body, refs_json, created_at)`
- [ ] **REST endpoints**:
  - GET `/api/im/threads` · 当前 user 所有 thread (cookie auth)
  - GET `/api/im/messages/{thread_id}` · 历史消息 paginated
  - POST `/api/im/send` 升级支持 `pin_ref` kind (参考 dispatch-store)
- [ ] curl 测 REST + websocat (WebSocket client) 测 /ws/im 连 + 收发 · sample 进 commit
- [ ] pytest `im_service/tests/` ≥ 6 case (REST · WebSocket · thread 持久化 · 消息
      kind · 重连 · auth fail)
- [ ] commit trailer:
  ```
  Signal: WORKER-A3-STAGE-D2-IM-WEBSOCKET-DONE
  RECOVER-FROM: 2e0f49f (Stage CF2 Riskctrl done · 本批接续)
  NEW-ENDPOINT: WS /ws/im, GET /api/im/threads, GET /api/im/messages/{tid}
  DEPENDS-ON: D.1 auth-protocol (Worker A2 同批 · cookie auth 共享)
  ```

## Boundary

- **改**: `api_server.py` (mount /ws/im + REST endpoints)
- **加**: `im_service/threads.py` (sqlite store) · `im_service/websocket.py`
  (FastAPI WebSocket handler) · `im_service/schemas.py` (Pydantic message types) ·
  `im_service/tests/test_*.py` · `data/im/.gitkeep`
- **不动**: `web/*` (frontend dispatch UI 后续 worker 改 polling → ws) ·
  agent_*/api.py · auth_service/ (D.1 worker 在改 · 复用) · CLAUDE.md · RFC

## Dependencies

- master plan §D.2 + §D.3 (gap #11 · IM 系统级)
- `docs/contracts/im-protocol.md` v1.0 (cherry-pick a660019 · spec 9-step migration)
- D.1 auth-protocol (Worker A2 同批 · 共享 JWT cookie 验证 · 你 import auth_service)
- sqlite (Python stdlib) · websockets (uvicorn 自带支持 FastAPI WebSocket)

## Method

1. Read im-protocol.md (D.2 D.3 D.4 9-step migration)
2. 设计 sqlite schema · DDL 在 `im_service/threads.py`
3. WebSocket handler `im_service/websocket.py`:
   - on_connect: verify JWT cookie · attach to user_id
   - on_message: parse + dispatch to thread + persist + broadcast to thread members
   - on_disconnect: cleanup connection
4. REST endpoints `/api/im/threads` + `/messages/{tid}` · 复用 sqlite store
5. POST `/api/im/send` 升级 `pin_ref` kind (现支持 `chat` 单 type)
6. pytest mock JWT + sqlite + WebSocket client · 6+ case

## Trailer protocol

```
Signal: WORKER-A3-STAGE-D2-IM-WEBSOCKET-DONE
RECOVER-FROM: 2e0f49f
NEW-ENDPOINT: WS /ws/im, GET /api/im/threads, GET /api/im/messages/{tid}
DEPENDS-ON: D.1 auth-protocol (Worker A2 同批)
```

## On completion

1. `git add im_service/ api_server.py data/im/.gitkeep` + commit + push origin
2. main CLI auto-patrol → review (curl + websocat + pytest + sqlite schema verify)
   → cherry-pick → push origin

## Estim

5-7 hr (sqlite schema + WebSocket handler + REST + 6+ test · careful concurrent
connection handling)

## NB

- 同批 D.1 auth-protocol (Worker A2 在改 auth_service/) · 你 import auth_service
  时假设它存在 · 你 commit 后主 CLI cherry-pick 顺序: D.1 先 (A2) · D.2 后 (A3)
- LLM tool calling (Stage D.4) 是后续 worker · 本批 only WebSocket + thread DB
- 重连机制: backend 60s ping timeout · frontend 走 exponential backoff
- 消息 ordering: 用 sqlite created_at ASC · WebSocket broadcast 顺序保证 (asyncio.Lock)
