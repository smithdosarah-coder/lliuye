# IM Protocol v1.0

**目的**: 定义 dispatch view (`/dispatch`) 与 archive ConversationPanel 共用的 IM 系统架构 · 含 thread 持久化 / WebSocket 实时 / LLM tool calling / @agent routing / drop-from-canvas / 微信气泡 (`wc-msg`) 渲染。覆盖 master plan gap #11 (WebSocket + thread persistence) 与 D.4 (tool calling)。

**适用范围**: `web/src/app/dispatch/` · `web/src/app/archive/<agent>/_components/<Agent>Workspace.tsx` 内的 ConversationPanel · `api_server.py` IM 段 · 后续新增 `im_service/` 后端模块。  
**Owner**: 主 CLI · 修改本协议走红区 RFC。  
**生效**: Stage D.2/D.3/D.4 · 与 auth-protocol.md 协同 (5 user 真 login + IM 1:1)。

---

## 1. 现状 (master plan gap #11 + D.2/D.3/D.4)

| Gap | 现状 | 文件位置 |
|---|---|---|
| 单 turn · 无 thread persistence | `/api/im/send` 每次新 LLM call · 无 history · 无 DB | `api_server.py:228-258` |
| 无 SSE / WebSocket 实时 | 前端 fetch POST · response 等到才显 · 多 user 无同步 | `ChannelWorkspace.tsx:113-170` `submit()` |
| Thread 数据全 mock 在前端 | `seedThreads` hardcoded · 5 group + N dm · 重启丢上下文 | `web/src/app/dispatch/_store/dispatch-store.ts:21-80` |
| Tool calling 缺 | LLM 说"找 / 搜 / 扫" 无法触发对应 agent run | `_AGENT_SYSTEMS` map 仅切 system prompt · 不调 agent endpoint |
| `target_agent` 仅由前端硬指定 | composer 没解析 `@agent` token · 不能让 user 灵活选 | `MessageBubble.tsx` + `ComposerBar.tsx` |

本协议把以上系统化为强制 IM 架构。

---

## 2. 5 User 固定账号 (passwords in PASSWORD_MAP)

IM 用户 = auth 用户 (一处声明 · 两域共用)。当前 5 user 与硬编 password:

```ts
// web/src/lib/store/auth-store.ts:14-50 · DEMO_USERS 5 个
// web/src/app/login/_components/LoginForm.tsx:35-41 · PASSWORD_MAP
{
  u_wangzhe:  "wangzhe",   // 客户经理 · 王哲   · 华东·上海第一支行
  u_lihua:    "lihua",     // 审贷官  · 李华   · 华东·授信审查部
  u_zhoumin:  "zhoumin",   // 合规官  · 周敏   · 总部·合规管理部
  u_chenkai:  "chenkai",   // 风险经理 · 陈凯   · 总部·风险管理部
  u_liuye:    "liuye",     // admin   · 刘野   · AI 中台
}
```

Stage D.1 后 PASSWORD_MAP 移到 backend (bcrypt hash) · 见 `auth-protocol.md §3`。本协议消费"已登录"事实 · 不重复声明 password 来源。

---

## 3. Thread 持久化 (gap #11 · D.3)

### 3.1 后端 schema (sqlite 优先 · jsonl 备选)

```sql
-- data/im.sqlite · alembic 不需要 (5-table demo 级)
CREATE TABLE threads (
  id TEXT PRIMARY KEY,                    -- "thr_zrgs" / "dm_lihua_wangzhe"
  title TEXT NOT NULL,
  customer_id TEXT,                       -- nullable · dm 不挂 customer
  kind TEXT NOT NULL DEFAULT 'group',     -- "group" | "dm"
  participants TEXT NOT NULL,             -- JSON array of user_id
  last_message_at TEXT NOT NULL,          -- ISO 8601
  unread_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  thread_id TEXT NOT NULL REFERENCES threads(id),
  from_id TEXT NOT NULL,                  -- user_id | "system" | agent_id
  kind TEXT NOT NULL,                     -- "text" | "system_event" | "handoff_card" | "file" | "agent_output" | "pin_ref"
  content TEXT NOT NULL,                  -- 文本正文 or JSON 序列化
  refs TEXT,                              -- JSON {eventId? ticketId? fileUrl? agentRunId?}
  created_at TEXT NOT NULL
);

CREATE INDEX idx_messages_thread_at ON messages(thread_id, created_at);
```

### 3.2 后端 endpoints

```
GET  /api/im/threads
       Query:   ?user_id=u_wangzhe (auth 取 currentUser · 不接受 query string 传 user_id 防越权)
       Returns: ImThread[]  (按 lastMessageAt desc · 仅含 currentUser 在 participants 里的 thread)

GET  /api/im/threads/{thread_id}/messages
       Query:   ?before=<created_at>&limit=50
       Returns: ImMessage[]
       403:     currentUser 不在 thread.participants

POST /api/im/threads
       Body:    { title, kind: "group"|"dm", participants: string[], customer_id? }
       Returns: ImThread

POST /api/im/threads/{thread_id}/read
       Action:  set unread_count=0 for currentUser

POST /api/im/messages       (replace 当前 /api/im/send 单 turn)
       Body:    { thread_id, content, target_agent?, kind?: "text"|"pin_ref", refs? }
       Behavior: 写 messages 表 · update threads.last_message_at · 触发 LLM (若 target_agent 或 @agent token) · WebSocket broadcast 新 message + LLM 异步 reply
       Returns: { message: ImMessage, ack: "queued" }
```

frontend types 复用 `web/src/lib/store/types.ts:126-150` `ImMessage` / `ImThread` (`kind?: "group" | "dm"` 已在 · Q-037 例外允许)。

---

## 4. WebSocket /ws/im (gap #11 · D.2)

### 4.1 协议

```
URL:     wss://demo.liuye.me/ws/im?token=<jwt>
         (本地 dev: ws://localhost:8000/ws/im?token=...)

Connect: 后端从 query token 解 JWT → currentUser · 注册 socket 到 user_sockets[user_id]

Inbound (client → server) JSON line:
  { "type": "subscribe", "thread_id": "thr_zrgs" }
  { "type": "typing",    "thread_id": "thr_zrgs" }
  { "type": "ack_read",  "thread_id": "thr_zrgs", "up_to": "<msg_id>" }

Outbound (server → client) JSON line:
  { "type": "message",        "thread_id": "...", "message": ImMessage }
  { "type": "typing",         "thread_id": "...", "user_id": "u_lihua" }
  { "type": "agent_progress", "thread_id": "...", "stage": "signal_scan", "pct": 40 }   // tool call 进度
  { "type": "agent_output",   "thread_id": "...", "message": ImMessage }                // LLM 异步 reply 落表后回推
```

### 4.2 前端连接

```tsx
// web/src/app/dispatch/_store/dispatch-store.ts (Stage D.2 改)
const ws = new WebSocket(`${WS_BASE}/ws/im?token=${getJwt()}`);
ws.onmessage = (ev) => {
  const evt = JSON.parse(ev.data);
  if (evt.type === "message")     pushMessage(evt.thread_id, evt.message);
  if (evt.type === "agent_output") pushMessage(evt.thread_id, evt.message);
  if (evt.type === "agent_progress") setAgentStage(evt.thread_id, evt.stage, evt.pct);
};
```

### 4.3 重连策略

- 连接断: exponential backoff (1s → 2s → 5s → 10s → cap 30s)
- 重连后: 客户端发 `{ type: "resync", since: "<last_msg_id>" }` 拉缺失消息 (后端 SELECT WHERE created_at > since)

---

## 5. Tool Calling (gap D.4)

### 5.1 触发条件

LLM system prompt 注入工具列表 · 当用户消息含 "找 / 搜 / 扫 / 看一下" 等意图词时 · LLM 输出 tool_call · 后端拦截执行:

```python
# api_server.py (Stage D.4)
TOOLS = [
    {
        "name": "agent_channel_run",
        "description": "触发 Agent1 获客 SSE · 输入查询语句 · 返候选企业",
        "endpoint": "/api/channel/run",
        "params": {"query": "string", "top_n": "int"},
    },
    {
        "name": "agent_credit_score",
        "description": "触发 Agent3 授信评分",
        "endpoint": "/api/credit/score",
        "params": {"customer_id": "string"},
    },
    # ... 6 Agent 各 1 tool
]
```

### 5.2 流程

```
用户在 dispatch composer 发 "找做工业软件的 SaaS 公司"
  → POST /api/im/messages {content: "...", thread_id: "thr_x"}
    → 后端写 user message (kind="text")
    → LLM call with TOOLS
      → LLM 返 tool_call {name: "agent_channel_run", args: {query: "..."}}
        → 后端 invoke agent_channel.run(query=...) (内部 SSE 消费完)
          → 后端写 system_event "Agent1 已启动"  → WebSocket broadcast
          → 后端写 agent_output (kind="agent_output", content=JSON.stringify(candidates), refs={agentRunId})
            → WebSocket broadcast 给 thread.participants 全部 client
            → 前端 MessageBubble kind=agent_output 渲染 candidate 卡片 (非纯 text)
```

### 5.3 message kind 扩展

`ImMessage.kind` (已在 `types.ts:130`) 含 5 种 · IM tool calling 后必用全:

| kind | 渲染 |
|---|---|
| `text` | wc-msg-bubble 文本气泡 |
| `system_event` | dpx-row-system 系统事件 chip (Agent1 已启动 / 切换扫描范围 ...) |
| `handoff_card` | HandoffCard 跳转下游 Agent (用 `web/src/app/dispatch/_components/HandoffCard.tsx`) |
| `file` | 附件卡片 (KB 上传) |
| `agent_output` | candidate 列表 / 评分卡 / 政策矩阵 (按 refs.agentId 分形态) |
| `pin_ref` | 画布 → composer drop 形成的缩略图卡 (§7) |

`MessageBubble.tsx:18-22` 当前 `KIND_TO_WC` 只 map user/agent/system 三类 · Stage D.4 必须扩。

---

## 6. @agent Routing

### 6.1 composer 解析

```tsx
// web/src/app/dispatch/_components/ComposerBar.tsx (Stage D.4 改)
function parseTargetAgent(text: string): AgentId | null {
  const m = text.match(/@(报告|获客|授信|预警|合规|风控)\b/);
  if (!m) return null;
  return ({
    "报告": "report", "获客": "channel", "授信": "credit",
    "预警": "alert", "合规": "compli", "风控": "riskctrl",
  } as Record<string, AgentId>)[m[1]];
}
```

提交时把 `target_agent` 与 `content` 一起 POST `/api/im/messages` · 后端 `_AGENT_SYSTEMS[target_agent]` 选 system prompt (`api_server.py:204-211` 已有 map)。

### 6.2 archive ConversationPanel

archive 内 (e.g. `ChannelWorkspace.tsx:113-170`) 也走 `/api/im/messages` · 但 `target_agent` 由 archive 路由硬指定 (`/archive/channel` → `target_agent="channel"`) · 不解析 @ token (用户不需在 archive 内切 agent · 已在该 agent 的 workspace)。

---

## 7. Drop-from-canvas (Pin → Composer)

### 7.1 MIME 协议 (已在 · 复用)

```ts
// web/src/lib/store/whiteboard-store.ts
export const CARD_PIN_MIME = "application/x-zhongan-card-pin";
// web/src/lib/store/panel-canvas-store.ts
export const PANEL_PIN_MIME = "application/x-zhongan-panel-pin";

// payload shape (stringify into dataTransfer)
type PinPayload = {
  id: string;            // "channel:radar" | "report:section:..."
  title: string;
  subtitle?: string;
  agentKey: AgentId;
  href: string;          // jump-back 链接 "/archive/channel"
  fullText?: string;     // for message pin
  thumbDataUrl?: string; // 可选缩略图 base64
};
```

### 7.2 dispatch composer 接 drop

参考 `ChannelWorkspace.tsx:721-779` 现成实装:

```tsx
function onDrop(e: DragEvent<HTMLDivElement>) {
  const rawPanel = e.dataTransfer.getData(PANEL_PIN_MIME);
  const rawCard = e.dataTransfer.getData(CARD_PIN_MIME);
  const payload = rawPanel ? JSON.parse(rawPanel) : rawCard ? JSON.parse(rawCard) : null;
  if (!payload) return;
  // 提交 message kind="pin_ref" · 不显 URL · 显缩略图卡
  submitMessage({
    kind: "pin_ref",
    content: payload.title,
    refs: { agentId: payload.agentKey, href: payload.href, fullText: payload.fullText },
  });
}
```

后端 `messages.kind="pin_ref"` · WebSocket broadcast · `MessageBubble.tsx` 见 kind=pin_ref 渲染 thumbnail card · 不显 url 链接 (master plan gap E13beec 已 fix · 本协议 forward declare)。

---

## 8. wc-msg 微信气泡 (统一渲染)

### 8.1 Class 命名

| Class | 用法 |
|---|---|
| `.wc-msg`           | 行容器 (li) |
| `.wc-msg--user`     | 用户消息 (右侧) |
| `.wc-msg--ai`       | AI/agent 消息 (左侧) |
| `.wc-msg--system`   | 系统事件 (居中 chip) |
| `.wc-msg-avatar`    | 头像 |
| `.wc-msg-bubble`    | 气泡本体 |
| `.wc-msg-bubble--user` / `--ai` | 颜色区分 |
| `.wc-msg-bubble--ask` / `--think` | special variants |
| `.wc-msg-foot`      | 底部 meta (作者名 / role / 时间) |
| `.wc-msg-typing`    | 三点 typing 指示 |
| `.wc-msg-fieldref`  | 字段引用 chip |

### 8.2 vs `dpx-msg` legacy

`dispatch` view 之前用 `dpx-msg` grid layout · 与 archive ConversationPanel 不一致。Stage D 起统一走 `wc-msg` (archive 已用 · 见 `ChannelWorkspace.tsx:546-672`)。`MessageBubble.tsx:24-60` 已切换。**禁止新增 `dpx-msg` class** · legacy 渐进清理。

---

## 9. ImMessage / ImThread 类型契约

types.ts (`web/src/lib/store/types.ts:126-150`) 是前后端共享 source of truth。新增字段必须:
- 走 RFC (本协议是红区契约)
- additive optional (Q-037 例外允许)
- 后端 `messages.refs` JSON 列承载 (无需 schema migration)

---

## 10. Migration path (Stage D.2/D.3/D.4)

| # | 文件 | 动作 |
|---|---|---|
| 1 | `im_service/db.py` (新建) | sqlite schema + CRUD (threads + messages + read marker) |
| 2 | `api_server.py` | 加 `/api/im/threads` GET / `/api/im/threads/{id}/messages` GET / POST `/api/im/threads` / POST `/api/im/threads/{id}/read` |
| 3 | `api_server.py` | `/api/im/send` rename `/api/im/messages` · 接 DB · 异步触发 LLM · 写 user msg 立 ack 返 message_id |
| 4 | `im_service/ws.py` (新建) | FastAPI WebSocket `/ws/im` · 注册 `user_sockets` dict · broadcast on new message |
| 5 | `web/src/app/dispatch/_store/dispatch-store.ts` | 删 `seedThreads` · 改 useEffect fetch `/api/im/threads` · 加 ws connection |
| 6 | `web/src/app/dispatch/_components/MessageBubble.tsx` | 扩 KIND_TO_WC 含 `handoff_card` / `file` / `agent_output` / `pin_ref` 各自渲染分支 |
| 7 | `web/src/app/dispatch/_components/ComposerBar.tsx` | 加 `parseTargetAgent` · drop handler · POST `/api/im/messages` |
| 8 | `api_server.py` | TOOLS 列表 + LLM tool_call 拦截 · invoke agent endpoint · 写 agent_output message · ws broadcast |
| 9 | `web/src/app/archive/<agent>/_components/<Agent>Workspace.tsx` ×6 | ConversationPanel 改走 `/api/im/messages` (thread_id=`archive:<agent>:<sessionId>`) · 删本地 mock canned-replies |

每步独立 commit · 每步跑 Playwright smoke (`im-thread-load.spec.ts` / `im-ws-realtime.spec.ts` / `im-tool-calling.spec.ts` / `im-pin-drop.spec.ts`)。

---

## 11. Acceptance gate

Stage D.2/D.3/D.4 完成判定:
- 重启 backend · thread + message 不丢 (sqlite 持久)
- 两个 user 同时登录 · A 发消息 · B 即时收 (WebSocket)
- 用户在 dispatch 发 "找做 SaaS 的公司" · LLM 返 tool_call · candidates 卡片落入 thread (kind=agent_output)
- 画布 panel 拖到 composer · 落成 thumbnail (kind=pin_ref) · 不是 URL 链接
- @报告 / @获客 解析正确 · backend system prompt 切换正确

---

## 12. 与其他契约的关系

- `auth-protocol.md` · IM 消费"已登录"事实 · 取 JWT 校验 ws connect · 取 currentUser 限 thread visibility
- `workspace-state-protocol.md` · archive ConversationPanel 是 IM 的一种宿主 · 但 thread shape 由本协议定义
- `shared-change-protocol.md` · `types.ts` `ImMessage`/`ImThread` 修改走红区 RFC (Q-037 已立 additive optional 例外先例)
