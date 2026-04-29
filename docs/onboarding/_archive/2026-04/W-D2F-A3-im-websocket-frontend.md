# Worker A3 (Stage D.2 frontend) · IM WebSocket frontend wire (替换 polling) · Onboarding

> Worker CLI 在 `D:/claude code/work-A3-prd` (branch `feat/prd-summaries-A3`) ·
> 复用 worktree。
> 上批 Stage D.2 + D.3 backend (`ab59186`) 已 cherry-pick MERGED (`7c2afaf`) ·
> 本批 Stage D.2 frontend 启动 · 配对收尾 gap #11 全 stack。

## Goal

实装 master plan §D.2 frontend — IM dispatch 替换 polling 用 WebSocket 实时 ·
配套 thread DB REST endpoint。
**gap #11 (WebSocket 实时 IM) frontend 闭环 · 全 stack production-grade**。

## Acceptance

- [ ] **必读** `docs/contracts/im-protocol.md` v1.0 + 自己上批 backend `im_service/`
      (cherry-pick 7c2afaf)
- [ ] **WebSocket client** `web/src/lib/im/websocket.ts`:
  - 连 `/ws/im` (cookie auto-bring JWT)
  - 重连 backoff (exponential · max 30s)
  - 心跳 ping/pong (30s · 防 60s timeout)
  - message types parse (chat/pin_ref/agent_output/system)
- [ ] **dispatch-store.ts 改造**:
  - 移除 polling fetch (现 setInterval call /api/im/messages)
  - 改用 WebSocket onMessage 推送
  - thread list 改 GET `/api/im/threads` (REST)
  - 历史消息 GET `/api/im/threads/{tid}/messages` (REST · paginated)
  - 发消息 POST `/api/im/messages` (REST · backend 同步 broadcast 到 WS)
- [ ] **ConversationPanel 改造**:
  - 实时收消息 (WebSocket → store → re-render · 不再 polling)
  - typing indicator (其他用户在打字 · WS message kind="typing")
  - 已读标记 POST `/api/im/threads/{tid}/read`
  - pin_ref kind 渲染 thumbnail card (复用 F-008 pattern)
- [ ] **Thread switch** 改用 GET `/api/im/threads/{tid}/messages` 拉历史
- [ ] tsc 0 error · `cd web && npx playwright test web/tests/regression/im-websocket.spec.ts` 跑通
- [ ] features-inventory.md 加 F-058 (IM WebSocket 实时 + thread persistence)
- [ ] commit trailer:
  ```
  Signal: WORKER-A3-STAGE-D2F-IM-WEBSOCKET-FRONTEND-DONE
  RECOVER-FROM: ab59186 (D.2 backend done · 本批接续)
  PRESERVES: F-001~F-057 (列全)
  RESPECTS: docs/contracts/im-protocol.md
  NEW-DOM: data-testid="im-typing-indicator", data-testid="im-thread-history-load"
  SMOKE-PASS: web/tests/regression/im-websocket.spec.ts
  INVENTORY-ADDED: F-058
  ```

## Boundary

- **改**: `web/src/app/dispatch/_store/dispatch-store.ts` (移 polling · 加 WebSocket) ·
  `web/src/app/dispatch/_components/ConversationPanel.tsx` (实时 re-render · typing) ·
  `web/src/app/dispatch/_components/ThreadList.tsx` (改 fetch 真 backend)
- **加**: `web/src/lib/im/websocket.ts` (WS client · reconnect · heartbeat) ·
  `web/src/lib/api/im.ts` (REST client · threads/messages/read) ·
  `web/tests/regression/im-websocket.spec.ts` ·
  `docs/features-inventory.md` F-058
- **不动**: backend `im_service/` (上批 7c2afaf 已 deliver) · auth_service/ ·
  agent_*/api.py · CLAUDE.md · RFC

## Dependencies

- master plan §D.2 frontend (gap #11 frontend)
- 自己上批 backend `im_service/` (7c2afaf · WS /ws/im + 6 REST endpoint)
- D.1 frontend AuthGate (Worker A2 现批 1f67866 · 复用 cookie · 必须 D.1F merge 后)
- `web/AGENTS.md` (Next 16 警告 · use client · WebSocket browser API)

## Method

1. Read 上批 `im_service/{websocket,threads,schemas}.py` (验 message type / event)
2. WebSocket client `web/src/lib/im/websocket.ts`:
   - constructor · open · close · onmessage handler
   - reconnect: exponential backoff (1s/2s/4s/8s/...30s)
   - heartbeat: setInterval(30s) send ping
3. dispatch-store 改 reducer · WebSocket message → action
4. ConversationPanel useEffect mount WS · cleanup unmount
5. typing indicator (debounce 1s send · receive show 3s)
6. tsc + playwright smoke (5 case · WS connect · receive · send · reconnect · typing)
7. inventory F-058 + trailer

## Trailer protocol

```
Signal: WORKER-A3-STAGE-D2F-IM-WEBSOCKET-FRONTEND-DONE
RECOVER-FROM: ab59186
PRESERVES: F-001~F-057 (列全 57 id)
RESPECTS: docs/contracts/im-protocol.md
NEW-DOM: ...
SMOKE-PASS: web/tests/regression/im-websocket.spec.ts
INVENTORY-ADDED: F-058
```

## On completion

1. `git add web/` + commit + push origin
2. main CLI auto-patrol → review (tsc + playwright + WS connect verify) →
   cherry-pick → push origin

## Estim

5-7 hr (WebSocket client + reconnect + heartbeat + typing + 5 case smoke)

## NB

- backend WS 60s timeout · frontend 30s heartbeat 安全 buffer
- 重连后历史消息: 走 REST GET `/api/im/threads/{tid}/messages?since=<ts>` · 不
  期望 WS replay (避免大流量)
- 消息 ordering: backend sqlite created_at ASC · frontend trust backend order
- typing indicator 是 D.2 frontend nice-to-have · 但 production demo 必备
- D.1 frontend AuthGate 必须先 cherry-pick 进 main (依赖 cookie 共享) ·
  本批 dispatch 时假设 D.1F 已 in (主 CLI 顺序 cherry-pick 会保证)
