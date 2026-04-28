# Workspace State Protocol v1.0

**目的**: 定义 6 Agent archive Workspace (Channel / Report / Credit / Alert / Compli / Riskctrl) 必须遵循的 state 架构 · 避免 Stage B+ worker 各自实现一套 · 让"切下拉切全 panel + 候选 click 详情 drawer + live SSE hydrate"成为跨 Workspace 一致行为。

**适用范围**: `web/src/app/archive/<agent>/_components/<Agent>Workspace.tsx` 全 6 个。  
**Owner**: 主 CLI (本 doc 是红区契约 · 修改走 RFC · 见 `shared-change-protocol.md`)。  
**生效**: Stage B Channel 重写完成即生效 · Stage C 5 Agent 复用此 pattern。

---

## 1. 现状 (master plan gap #2/#3/#4/#5)

`web/src/app/archive/channel/_components/ChannelWorkspace.tsx:67-254` 已部分实装 · 但存在以下 gap:

| Gap | 表现 | 根因 |
|---|---|---|
| #2 mock 不切 session | 选下拉无效 | `import { CHANNEL_SESSION } from ...mock` 单 const · panel 永远读这一个 |
| #3 panel 不接 props | radar/timeline/funnel 永远 mock | `function RadarPanel() { const s = CHANNEL_SESSION; ... }` 直接 import · 无 props |
| #4 SSE done 字段不全 | 前端无法 hydrate radar/signals/funnel | 后端 `/api/channel/run` done event 只返 `candidates` |
| #5 候选不可点 detail | 体验残缺 | candidate map 渲染 card · 无 onClick · 无 drawer |

本协议把以上 gap 系统化为强制 state 架构。

---

## 2. 必须实现的 4 个 useState gate

每 Workspace 顶层 component (e.g. `ChannelWorkspace`) 必须含以下 4 个 useState:

```tsx
// web/src/app/archive/<agent>/_components/<Agent>Workspace.tsx

import { useState } from "react";
import { MOCK_SESSIONS, type AgentSession } from "@/lib/mock/agent-<agent>-sessions";

export default function AgentXWorkspace() {
  // (1) started gate · 默认 false → 仅渲 Hero + QueryBar + 空白等待提示
  //     选下拉 / submit textbox / upload file 任一即 setStarted(true)
  const [started, setStarted] = useState<boolean>(false);

  // (2) selectedSession · 当前选中的 mock session id (默认取第一个)
  //     QueryBar 下拉 onChange / live SSE done 后由 setSelectedSession 切换
  const [selectedSession, setSelectedSession] = useState<string>(
    MOCK_SESSIONS[0].id,
  );

  // (3) liveData · live mode SSE done event 注入的真实数据
  //     null = 当前是 mock 模式 · 非 null = live 模式 (panel 优先消费)
  const [liveData, setLiveData] = useState<AgentSession | null>(null);

  // (4) selectedCandidate · 候选 click 后 drawer 显示的目标 (null = 关 drawer)
  const [selectedCandidate, setSelectedCandidate] = useState<string | null>(
    null,
  );

  // 推导 sessionData · panel 全部消费这一个 (live 优先 · 否则按 id 取 mock)
  const sessionData =
    liveData ??
    MOCK_SESSIONS.find((s) => s.id === selectedSession) ??
    MOCK_SESSIONS[0];

  // ... 渲染
}
```

### 2.1 触发源 (state 哪里被 set)

| state | 触发源 | 文件位置 (Channel 模板) |
|---|---|---|
| `setStarted(true)` | (a) 选下拉历史 session, (b) submit textbox 触发 live SSE, (c) upload file (KB mode · per PRD v2 B.6) | `ChannelWorkspace.tsx:919-940` `QueryBar.runRealSearch` + `:1033-1039` `onSelectSession` |
| `setSelectedSession(id)` | 下拉 `<select onChange>` 切到该 session id | `ChannelWorkspace.tsx:1059-1065` `<select onChange={onSelectSession}>` |
| `setLiveData(data)` | SSE `event === "done"` 时 normalize payload + setLiveData | `ChannelWorkspace.tsx:979-1019` `liveCandidates` 注入 (Stage B 扩为 full session) |
| `setSelectedCandidate(id)` | candidate card `onClick` (Stage B 加 · gap #5) | (待加 · `CandidateCard onClick={() => setSelectedCandidate(c.id)}`) |

### 2.2 panel 必须接 props · 禁止 inline import const

**反模式** (Channel 现状 `RadarPanel`):
```tsx
function RadarPanel() {
  const s = CHANNEL_SESSION; // ❌ 永远 mock · 不切 session
  return <RadarView radar={s.radar} />;
}
```

**正确**:
```tsx
function RadarPanel({ sessionData }: { sessionData: AgentSession }) {
  return <RadarView radar={sessionData.radar} />;
}
```

5 panel 全部按此改: `RadarPanel` / `FunnelStrip` / `CandidatesPanel` / `SignalTimelinePanel` / `ConversationPanel`。

---

## 3. mock_sessions shape · 至少 3 sessions/Workspace

每 Workspace 必须有 ≥ 3 个 mock session (反 5 原则 · 难度分层 §3.5 CLAUDE.md). 单 const 改为 array 导出:

```tsx
// web/src/lib/mock/agent-channel-sessions.ts (Stage B 新建 · 取代 agent-channel-session.ts 单 const)

export type ChannelSession = {
  id: string;                    // "sess_zrgs" / "sess_dingchuan" / "sess_haiyuan" ...
  benchmark: string;             // "中锐工商" / "鼎川精密" / "海元供应链"
  benchmarkName: string;
  query: ScoutQuery;             // 标杆画像 (industry / geo / scaleRange / featureTags / kbRefs)
  signals: SignalSource[];       // 8 信号源状态
  candidates: Candidate[];       // Top N 候选 (含 timeline / matchDimensions / products / pitchScripts)
  funnel: FunnelStage[];         // 5 阶段扫描漏斗
  radar: RadarDimension[];       // 8 维 P50 对标
  conversation: ConversationMessage[];
  match: MatchSetting;
  qcCounts: { block: number; warn: number; info: number };
  candidateCount: number;
  stage: string;                 // "已扫描" / "扫描中" / "草稿"
  recentSessions: RecentScoutSession[];
};

export const CHANNEL_MOCK_SESSIONS: ChannelSession[] = [
  { id: "sess_zrgs",      benchmark: "中锐工商",   /* ... */ },
  { id: "sess_dingchuan", benchmark: "鼎川精密",   /* ... */ },
  { id: "sess_haiyuan",   benchmark: "海元供应链", /* ... */ },
  // ≥ 3 个 · 反 5 原则 #2 难度分层覆盖 (简单 / 中等 / 困难)
];
```

每 session 之间 radar/signals/funnel/candidates 必须**实质不同** · 不许 deep-copy 改名。

---

## 4. 后端 SSE done event · 必须返完整 panel 数据

`/api/<agent>/run` SSE done event 当前 (Channel) 只返 `candidates` (`api_server.py` mounted via `agent_channel.api`)。Stage B.5 升级到:

```json
{
  "event": "done",
  "candidates": [...],
  "radar": [...],         // 8 维 RadarDimension[]
  "signals": [...],       // 8 信号源 SignalSource[] (status + hits + coverage)
  "funnel": [...],        // 5 阶段 FunnelStage[]
  "match_dimensions": [...],         // B.4b 候选 vs IdealProfile 维度匹配
  "product_recommendations": [...],  // B.4c Top3 产品 + 评分
  "pitch_scripts": [...],            // B.4c 切入话术
  "metrics": { "signalTotal": 0, "companiesFound": 0, "final": 0 }
}
```

前端 `setLiveData` 时把整个 payload 注入 (而非只 candidates):

```tsx
if (evt.event === "done") {
  const liveSession: AgentSession = {
    id: "live",
    benchmark: "(实时搜索)",
    candidates: normalize(evt.candidates),
    radar: evt.radar ?? [],
    signals: evt.signals ?? [],
    funnel: evt.funnel ?? [],
    matchDimensions: evt.match_dimensions ?? [],
    productRecommendations: evt.product_recommendations ?? [],
    pitchScripts: evt.pitch_scripts ?? [],
    /* ... */
  };
  setLiveData(liveSession);
}
```

`normalize` 函数兼容 backend snake_case 与前端 camelCase · 见 `ChannelWorkspace.tsx:979-1019` 现成模板。

---

## 5. 候选 detail drawer (gap #5 · master plan B.4)

candidate card `onClick` 触发 drawer · drawer 组件接 `selectedCandidate` 渲染:

```tsx
function CandidateCard({ rank, c, onSelect }: {
  rank: number; c: Candidate; onSelect: (id: string) => void;
}) {
  return <li onClick={() => onSelect(c.id)} /* ... */ />;
}

function CandidateDrawer({
  candidate, onClose,
}: {
  candidate: Candidate | null;
  onClose: () => void;
}) {
  if (!candidate) return null;
  return (
    <aside className="candidate-drawer">
      {/* B.4   8-axis derived radar (该候选 vs P50) */}
      {/* B.4   该候选 signal timeline */}
      {/* B.4b  匹配维度明细 chip 列表 (vs IdealProfile) */}
      {/* B.4c  Top3 产品推荐 + 切入话术 */}
      <button onClick={onClose}>×</button>
    </aside>
  );
}
```

drawer 状态走顶层 `selectedCandidate` · 不在 panel 内部 useState (点候选与切 session / 切 mode 互不干扰)。

---

## 6. Channel reference template (post Stage B 重写)

Stage B 完成后 `ChannelWorkspace.tsx` 是其他 5 Agent 复用的标准模板。Stage C 5 Agent worker 派活时 onboarding 必须 cross-ref Channel impl 行号。Stage B 完工 commit signal: `B-CHANNEL-WORKSPACE-REWRITE-DONE`。

---

## 7. Migration path (Channel · 然后 5 Agent 复制)

按以下顺序改 · 每步独立 commit · 每步完跑 `cd web && npx tsc --noEmit` + Playwright smoke 验:

| # | 文件 | 动作 | 验证 |
|---|---|---|---|
| 1 | `web/src/lib/mock/agent-channel-sessions.ts` (新建) | 拷 `agent-channel-session.ts` 内容 · 包成 array · 写 ≥ 3 sessions | tsc 0 error |
| 2 | `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` | 加 4 useState (started / selectedSession / liveData / selectedCandidate) · 删 `import { CHANNEL_SESSION }` 改 `MOCK_SESSIONS` array import | 默认渲染等待提示 · 选下拉切 mock · 视觉无回归 |
| 3 | 5 panel function (`RadarPanel` / `FunnelStrip` / `CandidatesPanel` / `SignalTimelinePanel` / `ConversationPanel`) | 改签名加 `sessionData` props · 删 `const s = CHANNEL_SESSION` | tsc 0 error · 切下拉 panel 全跟着切 |
| 4 | `agent_channel/api.py` SSE handler | done event 加 `radar` / `signals` / `funnel` / `match_dimensions` / `product_recommendations` / `pitch_scripts` 字段 (mock 也填 · live 时真生成) | curl `/api/channel/run` 看 done event 字段全 |
| 5 | `ChannelWorkspace.tsx` `runRealSearch` SSE 解析 | done 时构 `liveSession` 整体 setLiveData (而非只 candidates) | live mode panel 全切真数据 |
| 6 | `CandidateCard` / `CandidateDrawer` (新增) | onClick → setSelectedCandidate · drawer 渲染 derived radar + timeline + match dim + products + pitch | Playwright smoke `candidate-detail-drawer.spec.ts` |
| 7 | 删 `web/src/lib/mock/agent-channel-session.ts` 旧单 const | 全 import 已迁到 `-sessions` | grep 项目无残留 import · build 通 |

5 Agent 复制 (Stage C): 重复 1-7 步 · file 名换 `agent-<agent>-sessions.ts` + `<Agent>Workspace.tsx`。

---

## 8. Acceptance gate (每 Workspace 必跑)

Workspace 改完 commit 前必跑:
- `cd web && npx tsc --noEmit` 0 error
- `cd web && npm run build` 0 error  
- Playwright smoke ≥ 3 spec: `<agent>-mock-switch.spec.ts` (切下拉 panel 切) / `<agent>-live-search.spec.ts` (textbox submit 触发 live + panel 切) / `<agent>-candidate-detail-drawer.spec.ts` (click 候选 drawer 出现)
- features-inventory.md 加 F-`<agent>`-* entries

不达 gate 视作 regression · 阻断 merge。

---

## 9. 与其他契约的关系

- `im-protocol.md` · ConversationPanel 内消息走 IM · 但 IM thread 持久化是另一域 · 本协议只管 archive Workspace state shape
- `auth-protocol.md` · Workspace 入口由 AuthGate enforce · ACCESS matrix 不在本协议范围
- `shared-change-protocol.md` · 修本协议走红区 RFC · 修单个 Workspace 实现不走 (绿区)
