verdict: PENDING (V3 fix landed · codex re-review 触发中)

context: V2 commit (b56b361 · 2026-04-30 morning) 后 PM 注意到 issue 1 (ConversationPanel) 在 V2 是 partial fix · V3 走 option 1 完整版: backend 显式 emit `conversation` 字段 · 前端真 hydrate.

## V2 vs V3 在 issue 1 上的差距

| 维度 | V2 | V3 |
|---|---|---|
| `setMessages(live.conversation)` 调用 | ✓ (V2 加) | ✓ (V2 patch 保留 · 不破) |
| `live.conversation` 来源 | `tplFallback.conversation` (mock 模板 · 不动) | `evt.conversation` (backend) · 空时 fallback tplFallback |
| Backend 透传 conversation | ✗ (envelope 缺字段) | ✓ (`make_done(panels={..., "conversation": []})`) |
| `CHANNEL_PANEL_KEYS` 含 conversation | ✗ (7 keys) | ✓ (8 keys) |
| ConversationPanel 真从 sessionData 派生 | ✗ (走前端 mock state) | ✓ (`normalizeBackendDone` hydrate) |
| codex 原意 "render ConversationPanel from sessionData.conversation directly" | partial | 满足 |

V2 的 `setMessages(live.conversation)` 在 V3 仍保留作 defensive 同步 · 但来源真实化: live.conversation 现在直接来自 `evt.conversation` (backend canonical) · 而非 tplFallback 兜底.

## V3 触面 (单 commit · 6 文件)

### 1. `shared/sse_envelope.py`
- `CHANNEL_PANEL_KEYS` 7 → 8 keys · 加 `"conversation"`
- 注释更新: "V3 fix · ConversationPanel 显式从 done envelope 派生 · A4-channel AI 复盘 turn 落地后真填"

### 2. `tests/shared/test_sse_envelope.py`
- `test_channel_panel_keys_canonical` expected 8 keys (加 "conversation")
- 31/31 PASS

### 3. `agent_channel/realtime_stream.py`
- `make_done(panels={...})` 加 `"conversation": []` (live 路径默认空 · 不调 LLM 时 ConversationPanel 走 tplFallback fallback)

### 4. `agent_channel/api.py` `/api/channel/demo/run`
- panels 加 `"conversation": data.get("conversation", [])` · scenario JSON 可在 easy/medium/hard 各自填 demo conversation turns (当前 3 scenario JSON 不填 · 默认空)

### 5. `web/src/app/archive/channel/_components/ChannelWorkspace.tsx`
- `normalizeBackendDone` 加 conversation hydration 块 (与 radar/signals/funnel 同 pattern):
  ```ts
  const conversation =
    Array.isArray(evt.conversation) && (evt.conversation as unknown[]).length > 0
      ? (evt.conversation as ConversationMessage[])
      : tplFallback.conversation;
  ```
- 返回的 ChannelSession 含 `conversation` 字段 · 注入 setLiveData 后 V2 的 setMessages(live.conversation) 真获得 backend 数据

### 6. `web/tests/regression/channel-pilot-4gate.spec.ts`
- T2 + T5 mock SSE done payload 加 `conversation: []` (lock 8th key shape)
- **新增 T6** · V3 contract lock · backend done event 注入 `conversation: [{id, content: SENTINEL, ...}]` · 验 `[data-testid="channel-pilot-conversation"]` toContainText(SENTINEL) · backend conversation 非空时 ConversationPanel 必须显 backend 注入消息 · 不再 stale mock

## Verification

- `pytest tests/shared/test_sse_envelope.py` 31/31 PASS
- `pytest tests/agent_channel --ignore test_external_search` 191/191 PASS (跳 1 Tavily 401 integration · pre-existing · 与 V3 无关)
- `npx tsc --noEmit` PASS
- `npx playwright test channel-pilot-4gate.spec.ts --project=chromium` 6/6 PASS (18.2s)
  - T1 mock session select (不变)
  - T2 live mock SSE (加 conversation: [] · 仍 PASS)
  - T3 drawer mandatory (V2 加固 · 不变)
  - T4 mock_fallback banner (不变)
  - T5 demo run (V2 加 · 加 conversation: [] · 仍 PASS)
  - T6 V3 conversation hydration (新增)

## Tier 1 contract 修订 (workspace-state-protocol.md)

- §4 done event JSON 加 `"conversation": [...]` 行 + V3 fix 注释段
- **不破旧 V1/V2 envelope**: 缺 `conversation` 字段时前端 fallback `tplFallback.conversation` · 等于 V2 行为
- A4 worker 复用 channel pilot 模板时按 8 key 处理 · A4-channel 必跟 · 其他 5 子按需扩

## 不变 (V2 已 land · V3 不动)

- `data_source` envelope enum normalize (V2 issue 3) · 不动
- UI demo button 3 档 + Playwright T5 endpoint hit (V2 issue 2) · 不动
- T3 drawer mandatory (V2 issue 4) · 不动
- V2 patch `setMessages(live.conversation)` + `setSelectedCandidate(null)` 保留作 defensive · 数据来源升级到 backend
