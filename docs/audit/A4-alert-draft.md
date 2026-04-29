---
title: Worker-A4-alert · Pre-dispatch draft (§0.5 wait gate)
date: 2026-04-29
worker: A4-alert
worktree: D:\claude code\work-A4-alert
branch: feat/phase-a4-alert-adapter
gate: §0.5 wait · A3 not yet cherry-picked into chore/l0-infra
go_signal_expected: A4-ALERT-GO-AFTER-A3
done_signal: WORKER-A4-ALERT-ADAPTER-DONE
sources:
  - docs/onboarding/A4-alert.md (主 CLI dispatch · 9114633)
  - docs/contracts/workspace-state-protocol.md (4 gate canon)
  - docs/contracts/live-fallback-banner-spec.md
  - docs/audit/conflict-register-v1.md (Cat 2/4/5/6/7/11 alert)
  - docs/reset/north-star.md §1.2/§2.2
  - feat/phase-a3-channel-pilot:web/src/app/archive/channel/_components/ChannelWorkspace.tsx (template)
  - web/src/app/archive/alert/_components/AlertWorkspace.tsx (current · 200+ lines read)
  - agent_alert/api.py (current · 318 lines)
  - agent_alert/word_export.py (risk_level/level/tier fallback)
  - agent_alert/runtime_dump.py (grade serialize · RiskLevel.value)
  - web/src/lib/mock/agent-alert-session.ts (TopCase.tier / ReachRate.tier / HeatCell.level)
  - docs/contracts/agent-alert-spec.md
  - docs/features-inventory.md (F-020/021/022/023/049/055/061/064 alert)
status: pre-dispatch · 等 A3 cherry-pick + A4-ALERT-GO-AFTER-A3
---

# Worker-A4-alert · Pre-dispatch Draft

> **目的**: §0.5 wait gate 内把 alert 全栈现状盘清 + 4 gate 复用 A3 计划 + Cat 4/5/11/6/7 alert entries 处理预案 + grade 三命名 Q-NNN 草拟好。GO 信号一到照搬执行 · 不再二次思考。
>
> **不是**: 不写实现代码 · 不动 AlertWorkspace.tsx · 不动 agent_alert/api.py。

---

## 1. Alert 全栈现状盘点

### 1.1 前端 `web/src/app/archive/alert/_components/AlertWorkspace.tsx`

**已有 state** (line 75-106):
- ✅ `started: boolean` (default false → empty state · F-049 · W-CF2-A2 实装)
- ✅ `phase: "before" | "scanning" | "after"` · `stepIdx` · `timerRef` (扫描进度推进)
- ✅ `tab: "dist" | "heat" | "reach"` · `rangeId` (右栏 3 切换)
- ✅ `drillCustomer: string | null` (drill drawer 半实装 · 但**用 customer name 而非 client_id**)
- ✅ `liveFail / retryHandler` (W-FIX-A3 · live-fallback-banner-spec §2 规则 1)
- ✅ `scanError / demoBanner` (training-mode 显式 banner state)
- ✅ `exportError / exporting` (W-FIX2 bug #6 · F-064)
- ✅ `scanSessionId: string` (post-scan 持久化 id)

**4 gate 缺什么** (vs `workspace-state-protocol.md` §2):
- ❌ `selectedSession: string` — 现状 `const session = ALERT_SESSION` 单 const · 不切 mock
- ❌ `liveData: AlertSession | null` — 现状 SSE done 不回完整 envelope · 前端无法 hydrate
- ⚠️ `selectedCandidate` — 有 `drillCustomer` 但语义/命名不对齐 (协议 §2 要求 client_id key)

**当前 panel 反模式** (per `workspace-state-protocol.md:78-83`):
```tsx
const session = ALERT_SESSION;  // line 76 · 单 const · 不接 props
```

5 panel 全部直读 `session` 闭包变量 · 切 session 不会跟着切 (gap #2 镜像)。

### 1.2 后端 `agent_alert/api.py`

**SSE done payload 漂** (line 107-112 · Cat 4):
```py
wrap = {"event": "stage", "payload": cleaned}    # ❌ 无 stage 名
...
yield sse_encode({"event": "done"})              # ❌ done 空 · 无 envelope
```

**LLM caller 反模式** (line 306-318 · Cat 7):
```py
def _build_simple_llm_caller():
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return None
    from llm import LLMClient                     # ❌ 跳 shared/llm fallback
    client = LLMClient(provider="deepseek", api_key=api_key)
```

**已实装 OK 的端点** (本 worker 不动):
- `POST /api/alert/export_docx` (W-FIX2 bug #6 · F-064)
- `GET /api/alert/hitlist` (Stage C · 持久化)
- `GET /api/alert/drill/{client_id}` (Stage C · LLM disposition fallback)
- `GET /api/alert/health`

### 1.3 SSE 客户端 (`web/src/lib/api/alert.ts → runAlertScan`)

现状: `LiveFailError` + `runAlertScan` 已存在 · `AlertWorkspace.tsx:38` `import { LiveFailError, runAlertScan } from "@/lib/api/alert"`。

**反模式 (Cat 3)**: 推断 `runAlertScan` 内 inline `res.body.getReader()` SSE 解析 · 未走 `web/src/lib/api/_live.ts` 的 `streamSse` helper (Channel/Credit/Report 同问题 · A3 在 pilot 里改)。GO 后 verify 实际实现并迁。

### 1.4 Mock & Schema 三命名漂移 (Cat 5)

| 文件 / 行 | 字段 | 类型 / 取值 | 用途 |
|---|---|---|---|
| `web/src/lib/mock/agent-alert-session.ts:74` | `TopCase.tier` | `"red" \| "yellow" \| "green"` | 命中清单 risk grade |
| `web/src/lib/mock/agent-alert-session.ts:62` | `ReachRate.tier` | `"red" \| "yellow" \| "green"` | 触达率分档同 grade |
| `web/src/lib/mock/agent-alert-session.ts:58` | `HeatCell.level` | `0..4` (number) | **热力 intensity ramp** · 非 risk grade · 不动 |
| `agent_alert/word_export.py:22` (注释) | fallback `risk_level / level / tier` | str (snake/camel) | 后端兼容三键 · 优先 snake_case |
| `agent_alert/word_export.py:51-55` | `_TIER_LABEL` dict key | `"red"/"yellow"/"green"` | 等价 grade enum |
| `agent_alert/runtime_dump.py:88` (`_serialize_hit`) | `grade: hit.level.value` | `RiskLevel.value` (str) | 写 `evaluation/manual/4_*.yaml` · adapter 消费 |
| `shared/kb_scan/models.py:RiskLevel` | enum source | enum (`.value` = str) | 真正源头 |

**根因**: alert 历史 `tier` 留自 channel scout · runtime_dump 跑 `RiskLevel.value` 直序列化为 `grade` · word_export 三键兼容兜底 · 三命名并行未统一。`HeatCell.level` 是热力强度 ramp · 与 grade 同名不同义 · **不应卷入归一**。

### 1.5 demo / live boundary (Cat 11 alert · onboarding §2 必读)

| Entry | 现状 | 处理 |
|---|---|---|
| `triggerTertiaryDemo` (line 214-224) `setDemoBanner(true)` · phase=after | training-mode state 已 set · 但顶部 banner UI 未必显眼 (Cat 11-6 Codex Keep 模式) | Keep · GO 后 verify banner 真显 |
| `liveFail` banner (line 387+) | 已实装 W-FIX-A3 · live-fallback-banner-spec 规则 1 | Keep |
| `AlertEmptyState onPrimary/onSecondary/onTertiary` | 已 wire | Keep |
| **mock dropdown banner (规则 2)** | 现状无 mock dropdown (单 session) · `selectedSession` gate 加之后才有 | Stage 2.7 加 banner · **per live-fallback-banner-spec §2 规则 2** |

无 silent mock fallback 路径 · alert 此项相对干净。

### 1.6 Cat 6 alert · prompt 漂

`agent_alert/prompts.py:13-37 SYSTEM_RISK_SCAN` 含"事实数据"措辞 · 但**无三阶段 evidence-first 结构** · 与 root `_DATA_CITATION_RULES` 脱轨。需迁 `shared/prompts/contract.py` 8 段 template (A2 worker DONE · `cf9623b` 已交)。

### 1.7 Cat 7 alert · LLM caller

`agent_alert/api.py:312-313` 直 init `LLMClient(provider="deepseek", api_key=api_key)` · 跳 `shared/llm` fallback chain。需改 `from shared.llm import chat_with_fallback` · per `shared/kb_scan/impls/channel_signal.py:311` 现成模板。

---

## 2. 4 gate 复用 A3 模板计划 (照搬 ChannelWorkspace.tsx 模式)

**原则**: 严格按 `workspace-state-protocol.md` §7 七步路径 · 不另设计。A3 ChannelWorkspace.tsx 是参考实装 (line 1392-1432 SSE done envelope 注入 · line 1059-1065 dropdown onChange) · GO 后 cross-ref 行号迁。

### 2.1 状态层 (4 useState)

```tsx
// AlertWorkspace.tsx (post-A4)

import { ALERT_MOCK_SESSIONS, DEFAULT_SESSION_ID, type AlertSession } from "@/lib/mock/agent-alert-sessions";

// (1) started — 已有 · 不动
const [started, setStarted] = useState<boolean>(false);

// (2) selectedSessionId — 新加 · default = ALERT_MOCK_SESSIONS[0].id
const [selectedSessionId, setSelectedSessionId] = useState<string>(DEFAULT_SESSION_ID);

// (3) liveData — 新加 · live mode SSE done 注入完整 AlertSession (不只 hit_list)
const [liveData, setLiveData] = useState<AlertSession | null>(null);

// (4) selectedClientId — 改名 (drillCustomer → selectedClientId)
//     语义切到 client_id (与 backend /api/alert/drill/{client_id} 端点一致)
const [selectedClientId, setSelectedClientId] = useState<string | null>(null);

// 推导 sessionData (5 panel 全消费这一个)
const sessionData: AlertSession =
  liveData ??
  ALERT_MOCK_SESSIONS.find((s) => s.id === selectedSessionId) ??
  ALERT_MOCK_SESSIONS[0];
```

### 2.2 mock-sessions 拆分 (≥ 3 sessions · 反 5 原则 #2 难度分层)

新建 `web/src/lib/mock/agent-alert-sessions.ts` (复数 · 取代单 const `ALERT_SESSION`):

| session id | benchmark | 难度 | 红/黄/绿分布 | 触发源 |
|---|---|---|---|---|
| `sess_baseline_100` | 在贷 100 家 (常态) | 简单 | 5 / 15 / 80 | 内部规则 + 外部舆情 |
| `sess_manuf_policy_event` | 制造业 · 国务院政策升级 | 中等 | 12 / 38 / 50 | Agent5 政策事件交叉触发 |
| `sess_judicial_news_dual` | 司法+舆情双路命中 | 困难 | 25+ / 35 / 40 | 外部信号流 + 内部交易异常 |

每 session 之间 industry / heatmap / topCases 实质不同 · 不许 deep-copy 改名。

### 2.3 5 Panel props 化

当前 alert 5 panel (per onboarding §1):
1. **TrafficLightWall** (红/黄/绿榜单 · phase=after · `currentQueue`)
2. **OutputPanel** (3 tab 切 dist/heat/reach · industry stacked / heatmap / reach rate)
3. **ScanProgress** (`steps` / `stepIdx` / phase=scanning)
4. **DrillDrawer / TopCases** (drill drawer · disposition advice)
5. **AlertConversation / Composer** (中栏对话)

5 panel 全改签名:
```tsx
function TrafficLightWall({ sessionData }: { sessionData: AlertSession }) { ... }
// 删 const session = ALERT_SESSION
```

### 2.4 SSE done envelope 注入 (前端)

A3 模板 (line 1392-1432) 同 pattern:
```tsx
const reader = res.body.getReader();  // 改用 streamSse
for await (const evt of streamSse(reader)) {
  if (evt.event === "stage") {
    setStepIdx(/* derive from evt.stage */);
  }
  if (evt.event === "done") {
    const liveSession: AlertSession = normalizeAlert(evt.payload);
    setLiveData(liveSession);
    setPhase("after");
  }
  if (evt.event === "error") {
    recordLiveFail("alert scan", evt, () => startScan());
  }
}
```

`normalizeAlert` 兼容 backend snake_case ↔ frontend camelCase。

### 2.5 streamSse 迁

`runAlertScan` 内 inline `res.body.getReader()` → 改用 `web/src/lib/api/_live.ts` 的 `streamSse(...)`。Cat 3 修。

### 2.6 候选 click → drawer

`<TopCaseRow onClick={() => setSelectedClientId(c.id)} />` · drawer 接 `selectedClientId` · 调 `GET /api/alert/drill/{client_id}` · ESC / backdrop 关。`drillCustomer` (按 name) 全栈替换 `selectedClientId` (按 id)。

### 2.7 mock dropdown banner (live-fallback-banner-spec §2 规则 2)

`selectedSession` 切到非 default (mock) session → 顶部 banner:
```
示例数据 (training mode) · 切真实输入 → [按钮]
```
`liveData != null` 时不显 (live 优先)。`demoBanner` state 半实装 · 这一步把 banner UI 真显 + 与 `selectedSession` 联动。

---

## A3 模板抄段清单

> **基线**: `feat/phase-a3-channel-pilot` HEAD = `4c54cf2` (A3 worker 尚未 commit 任何 web/ 改动 · sibling worktree `D:\claude code\work-A3-channel-pilot` 也只加了 onboarding doc)。所以"模板"= 当前 disk 上的 `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` (2730 行 · workspace-state-protocol §1 标"部分实装")。
>
> **行号注**: 以下行号锚定**当前 HEAD**。A3 worker 真 cherry-pick 后 ChannelWorkspace.tsx 行号会漂 · GO 后第一步 `git rebase chore/l0-infra` · 然后**按 anchor 字符串重新 grep 行号** · 不锁死。
>
> **共 12 段 · 每段标 alert 改名 / alert 改造点 / 用法 / 抄入 §11 step**。

### 段 1 · 4 useState declarations 块

| 项 | 值 |
|---|---|
| **A3 锚点** | `ChannelWorkspace.tsx:87-130` (`selectedSessionId` / `liveCandidates` / `started` / `selectedCandidateId` 顺序声明 + 注释) |
| **抄什么** | 4 useState 声明结构 + JSDoc 注释 (含 `F-041` / `F-005 Phase 2` / `F-042` 引用风格) |
| **alert 改名** | `liveCandidates` → `liveData` (整 `AlertSession` 不只 candidates · per workspace-state-protocol §2 第 3 gate)。`selectedCandidateId` → `selectedClientId` (与 backend `/api/alert/drill/{client_id}` 端点一致) |
| **alert 改造** | `started` 已存在不动 (line 86)。`drillCustomer: string \| null` 改 `selectedClientId` 同时把所有下游 customer-name display 接 `drillablePool[selectedClientId].customer` (UI 文案不丢) |
| **抄入 step** | §11 step 2 |

### 段 2 · ESC 关 drawer useEffect

| 项 | 值 |
|---|---|
| **A3 锚点** | `ChannelWorkspace.tsx:134-144` (`useEffect` 监听 `globalThis.KeyboardEvent` · `selectedCandidateId` truthy 时 Escape clear) |
| **抄什么** | useEffect 整段 + cleanup return |
| **alert 改名** | `selectedCandidateId` → `selectedClientId` |
| **alert 改造** | 一比一 · alert 现状没有 ESC 关 drawer 代码 (drillCustomer 半实装) · 直接抄入 |
| **抄入 step** | §11 step 6 |

### 段 3 · handleSelectSession callback

| 项 | 值 |
|---|---|
| **A3 锚点** | `ChannelWorkspace.tsx:147-158` (useCallback · 切 session id · reset messages · setLive(null) · 关 drawer) |
| **抄什么** | useCallback 整段结构 (按 id lookup MAP + 4 个 setter 顺序) |
| **alert 改名** | `setMessages` reset alert conversation (alert 现状是 ScanQueueCase / TopCase 数据 · 不是 messages · 改成 reset `phase` / `stepIdx` / `tab` / `selectedClientId` · 同时 setLiveData(null)) |
| **alert 改造** | alert 没有 conversation in same shape · reset target = `phase="before"` + `setStepIdx(0)` + `setTab("dist")` + `setSelectedClientId(null)` + `setLiveData(null)` (清 live · 切回 mock) |
| **抄入 step** | §11 step 2 (与 4 useState 同 commit) |

### 段 4 · sessionData 推导块

| 项 | 值 |
|---|---|
| **A3 锚点** | `ChannelWorkspace.tsx:102-104` (`s = MOCK_SESSIONS_MAP[selectedSessionId] ?? MOCK_SESSIONS_MAP[DEFAULT_SESSION_ID]`) + line 117 (`candidatesPool: Candidate[] = liveCandidates ?? s.candidates`) |
| **抄什么** | 双层 fallback derive 模式: `liveX ?? mockX ?? defaultX` |
| **alert 改名** | `s` → `sessionData`。`candidatesPool` 概念在 alert 不存在 · alert 直接全 session 切: `sessionData = liveData ?? ALERT_MOCK_SESSIONS_MAP[selectedSessionId] ?? ALERT_MOCK_SESSIONS_MAP[DEFAULT_SESSION_ID]` |
| **alert 改造** | 一处 derive 同时 cover 5 panel · 不分 candidatesPool / radarPool / heatmapPool (alert 全是同 sessionData 派生) |
| **抄入 step** | §11 step 2 |

### 段 5 · normalizeBackendCandidate (snake↔camel 桥)

| 项 | 值 |
|---|---|
| **A3 锚点** | `ChannelWorkspace.tsx:1200-1346` (146 行长函数 · 把 backend SSE done event 单 candidate dict normalize 成前端 `Candidate` type · 含 timeline / match_dimensions / product_recommendations / pitch_scripts / similarity\|\|match_score fallback / industry/geo/scale 字段) |
| **抄什么** | 整体结构 + Q-041 fix 模式 (`String(c.industry ?? "—")` / 多键 fallback / Array.isArray 守门) |
| **alert 改名** | `normalizeBackendCandidate` → `normalizeAlertSession` · 输入是**整个 done envelope payload** 而不是单 candidate dict · 输出 `AlertSession` |
| **alert 改造** | 字段映射 (per §3 done envelope schema): backend `hit_list` / `industry_distribution` / `signal_heatmap` / `reach_rate` / `top_cases` / `dispositions` / `kb_state` → 前端 `AlertSession.{topCases, scanQueueCases, signalHeatmap, industryDistribution, reachRate, ...}`。**关键**: cat 5 grade 命名 (`risk_level` / `tier` / `grade` 三选一 · 等 Q-NNN A) 在此处统一兜底 (用 selected name 优先 · fallback 兼容旧字段) |
| **抄入 step** | §11 step 5 |

### 段 6 · runRealSearch SSE 主循环

| 项 | 值 |
|---|---|
| **A3 锚点** | `ChannelWorkspace.tsx:1379-1446` (QueryBar 内 · `runRealSearch(queryOverride?: string)` async function · POST /api/channel/run · `res.body.getReader()` · 累积 buf · `\n\n` block split · 解析 `data:` line · evt.event === "done" 时 normalize + setLive · catch 写 streamError) |
| **抄什么** | 错误处理结构 (try/catch/finally + `setStreaming(false)`) + SSE block 累积 / split 模式 |
| **alert 改名** | `runRealSearch` → `runAlertScan` (alert 已有同名 helper 在 `web/src/lib/api/alert.ts` · 改造它) · `setLive` → `setLiveData` · `setStreamEvents` → 推进 stage 步骤 (`setStepIdx`) |
| **alert 改造** | **不抄 inline `res.body.getReader()`** (Cat 3 反模式) · 改用 `web/src/lib/api/_live.ts` 的 `streamSse` helper:<br/>`for await (const evt of streamSse(reader)) { ... }`<br/>endpoint `/api/channel/run` → `/api/alert/scan` · payload 改 `{scenario_key, force_mock: false}` · evt.event 三态: `stage` (推 stepIdx + 显示 stage 名) / `done` (normalize 整 session + setLiveData + setPhase("after")) / `error` (调 `recordLiveFail("alert scan", e, () => startScan())`) |
| **抄入 step** | §11 step 5 (兼 step 4 后端 done envelope · 前后端同批联调) |

### 段 7 · dropdown click-to-fire (B-2 pattern)

| 项 | 值 |
|---|---|
| **A3 锚点** | `ChannelWorkspace.tsx:1448-1499` (pendingSessionId state + onSessionSelectChange + onApplySessionSwitch button click · `<select data-testid="channel-session-select" value={pendingSessionId} onChange={...}>` + MOCK_SESSIONS_LIST.map render options) |
| **抄什么** | dropdown 双阶段: select onChange 仅 set pending · 显式 button 点击触发 parent setter · 防止 select 误触切走 live state |
| **alert 改名** | `data-testid` → `alert-session-select`。MOCK_SESSIONS_LIST → ALERT_MOCK_SESSIONS_LIST (导自 `agent-alert-sessions.ts`) |
| **alert 改造** | alert 现状**无 dropdown** (只有 scanRange dropdown 选扫描范围 · 不是 mock session) · 在 hero 下加新 dropdown · 与 scanRange 不冲突 (两 dropdown 独立) |
| **抄入 step** | §11 step 8 (mock dropdown banner 同批 · 选下拉触发 banner 显) |

### 段 8 · external trigger useEffect (skip)

| 项 | 值 |
|---|---|
| **A3 锚点** | `ChannelWorkspace.tsx:1470-1480` (`externalTrigger?: { input: string; nonce: number }` · IdealProfile "开始扫描" 触发 auto-run) |
| **抄什么** | (none) |
| **alert 改名** | — |
| **alert 改造** | **skip · alert 无 IdealProfile pre-step** · 三个 CTA (primary/secondary/tertiary) 已经直接调 `triggerPrimaryScan()` / `triggerSecondaryScan()` / `triggerTertiaryDemo()` · 不需 external trigger 间接层 |
| **抄入 step** | (none · 显式不抄) |

### 段 9 · 顶部 banner aggregation

| 项 | 值 |
|---|---|
| **A3 锚点** | `ChannelWorkspace.tsx:140-144` (`streamErrorTop` / `aggregatedKbError` / `topBannerMessage` derive · `dismissTopBanner` callback) + JSX line 268-285 (banner render) |
| **抄什么** | 多源 error 统一聚合到顶部 banner 单 entry · 支持 dismiss + retry |
| **alert 改名** | streamErrorTop → scanErrorTop。aggregatedKbError → (alert 无 KB upload · skip) |
| **alert 改造** | alert 现状有**多个分散 banner** (`liveFail` line 387+ / `scanError` line 358+ / `exportError` 推断) · 改造时合并: 顶部统一 `topBannerMessage` derive `liveFail \|\| scanError \|\| exportError \|\| trainingModeBanner (mock dropdown · 段 7 联动)` · 单 dismiss 路径 |
| **抄入 step** | §11 step 8 (与 mock dropdown banner 同批) |

### 段 10 · 4 gate root render branch

| 项 | 值 |
|---|---|
| **A3 锚点** | `ChannelWorkspace.tsx:264-339` (data-started 顶层 + EvidenceProvider wrap + topBanner + Hero + KbUploadStrip + IdealProfileCard + QueryBar + `started ? <full workspace 5 panel> : <empty state>` ternary + CandidateDetailDrawer 始终在 root) |
| **抄什么** | started ternary 分支 + EvidenceProvider 双层包 + 顶层 data-attr (`data-view` / `data-started` / `data-phase` / `data-session-id`) |
| **alert 改名** | `data-view="archive-channel"` → `data-view="archive-alert"`。EvidenceProvider items: `CHANNEL_EVIDENCE` → `ALERT_EVIDENCE` (已存在 · line 37) |
| **alert 改造** | alert 现状已有**两份 return** (line 295 empty / line 346 full) · 合并到 single return + ternary · 与 A3 一致。data-attr 加 `data-session-id={sessionData.id}` + `data-live-mode={liveData ? "yes" : "no"}` (NEW-DOM trailer) |
| **抄入 step** | §11 step 2 (与 4 useState 同 commit · 因为 ternary 依赖 sessionData derive) |

### 段 11 · CandidateDetailDrawer 模板

| 项 | 值 |
|---|---|
| **A3 锚点** | `ChannelWorkspace.tsx:2149+` (`function CandidateDetailDrawer({ candidate, sessionData, onClose })` · 接 selectedCandidate 渲染 derived radar + signals timeline + match dim + products + pitch) |
| **抄什么** | drawer 4 区结构 (header / radar+signals / 匹配明细 / 产品+话术) + onClose backdrop click + 关闭 button |
| **alert 改名** | `CandidateDetailDrawer` → `AlertDrillDrawer` · `candidate: Candidate \| null` → `clientId: string \| null` |
| **alert 改造** | drawer **不消费 sessionData 本地数据** · 改成 `useEffect` fetch `GET /api/alert/drill/{client_id}` (已有端点 `agent_alert/api.py:260`) · 渲染 backend 返回的 `{client_id, company_name, level, score, matched_rules, reasons, signal_timeline, disposition, disposition_source}` · 4 区: header (company_name + level + score) / signal_timeline (per A3 timeline 模式) / matched_rules + reasons / disposition (LLM 优先 / 模板兜底) |
| **抄入 step** | §11 step 6 |

### 段 12 · MOCK_SESSIONS array + MAP + LIST + DEFAULT_SESSION_ID 导出

| 项 | 值 |
|---|---|
| **A3 锚点** | `web/src/lib/mock/agent-channel-sessions.ts` (整文件结构 · ≥ 3 sessions array + `MOCK_SESSIONS_MAP: Record<id, ChannelSession>` + `MOCK_SESSIONS_LIST: RecentScoutSession[]` summary list + `DEFAULT_SESSION_ID` const) |
| **抄什么** | 文件骨架 + 多 export 命名 + 难度分层注释 (反 5 原则 §3.5) |
| **alert 改名** | 新建 `web/src/lib/mock/agent-alert-sessions.ts` · 类型 `ChannelSession` → `AlertSession` · `MOCK_SESSIONS_MAP` → `ALERT_MOCK_SESSIONS_MAP` · `MOCK_SESSIONS_LIST` → `ALERT_MOCK_SESSIONS_LIST` · `RecentScoutSession` → `AlertRecentSession` (类型已存在 in `agent-alert-session.ts:80`) |
| **alert 改造** | ≥ 3 sessions (per §2.2 难度分层 · `sess_baseline_100` / `sess_manuf_policy_event` / `sess_judicial_news_dual`) · 每 session 之间 hit_list / industry / heatmap / topCases 实质不同 · 不许 deep-copy 改名。**反 5 原则 #5 环境边界**: fixture 不含 difficulty / risk_level 答案字段 · Agent 自己算。 |
| **抄入 step** | §11 step 1 |

### 段映射 → §11 step 总结

| §11 step | 抄哪些段 |
|---|---|
| step 1 (mock-sessions 拆) | 段 12 |
| step 2 (4 gate + sessionData derive + ternary render) | 段 1 + 段 3 + 段 4 + 段 10 |
| step 3 (5 panel props) | (无 A3 锚点 · 自己改 · workspace-state-protocol §2.2 模式) |
| step 4 (backend done envelope) | (无 A3 锚点 · 后端独立 · 但 §3 schema 与 A3 done event 共形) |
| step 5 (frontend SSE done 注入 + streamSse 迁) | 段 5 + 段 6 |
| step 6 (drill drawer + ESC) | 段 2 + 段 11 |
| step 7 (grade 三命名归一) | (cat 5 · 与段 5 normalize 桥联动 · 等 Q-NNN A) |
| step 8 (mock dropdown banner) | 段 7 + 段 9 |
| step 9 (demo/run 端点 + fixture) | (后端独立 · 模式参考 A3 fixture 形态 + agent_channel/api.py demo 路) |
| step 10 (Cat 6/7 prompt + LLM caller · 若范围内) | (无 A3 锚点 · A2 shared infra 为模板) |
| step 11 (Playwright smoke) | 段 7/9/10/11 的 data-testid 都是 selector 入口 |

### 风险 (与 §10 R4 / R5 联动)

- **行号锁死**: 本清单行号锚 HEAD `4c54cf2` · A3 worker 真 cherry-pick 时若 ChannelWorkspace.tsx 已被 A3 worker 改 (新加 result-driven 派生逻辑 · 删 inline reader 改 streamSse · 重写 panel props) → 行号全漂。**对策**: GO 后第一步 grep anchor 字符串 (e.g. `function CandidateDetailDrawer` / `runRealSearch` / `pendingSessionId`) 重定位 · 不锁死本清单行号
- **段 6 inline reader 反模式**: 本清单显式标"不抄 inline reader · 改用 streamSse" · A3 worker 也会做这个迁 (per onboarding 任务 #2 "SSE reader 改 streamSse") · 真 cherry-pick 后 A3 ChannelWorkspace 应已是 streamSse 版本 · 直接抄成型版本就好
- **段 5 normalize 函数大小**: 当前 ChannelWorkspace `normalizeBackendCandidate` 146 行 · alert 的 `normalizeAlertSession` 估计同量级 (整 session 不只 candidate 但 alert 字段更少) · **不抽 hook**: 跟 A3 一样在 component 内 · workspace-state-protocol §7 step 1-7 都没要求抽 hook · 简单优先 (per A4 子 worker onboarding §2 charter `web/src/app/archive/_shared/useWorkspaceRun.ts` 那个 task 主 CLI 派给 5 子 worker 中**一个**兼任 · 不绑 alert)

---

## 3. Cat 4 alert · Backend SSE schema 修法

`agent_alert/api.py:107-112` 改:

```py
# stage event 加 stage 名 (per A2 sse_envelope 共形 + workspace-state-protocol.md §4)
wrap = {
    "event": "stage",
    "stage": evt.get("stage_name", "scan"),  # e.g. "kb_load" / "external_scan" / "internal_match" / "cross" / "summary"
    "payload": cleaned,
}

# done event 加完整 envelope (注入 frontend liveData)
yield sse_encode({
    "event": "done",
    "session_id": session_id,
    "scenario_key": req.scenario_key,
    "mode": "live",                                    # "live" | "mock"
    "summary": "扫描 N 家 · 红 X / 黄 Y / 绿 Z",
    "totals": {"red": int, "yellow": int, "green": int},
    "hit_list": {"red": [...], "yellow": [...], "green": [...]},  # HitList shape (cat 5 grade 字段统一后)
    "industry_distribution": [...],                    # IndustryDistribution[]
    "signal_heatmap": [...],                           # HeatCell[]
    "reach_rate": [...],                               # ReachRate[]
    "top_cases": [...],                                # TopCase[]
    "dispositions": {client_id: advice_text},          # 处置建议 map
    "kb_state": "...",
})
```

字段 shape 派生 `agent-alert-sessions.ts` `AlertSession` type · 与 frontend liveData 注入方式逐字段对齐。

A2 worker DONE 后 import `shared.sse_envelope.AlertDoneEnvelope` · 走 dataclass-from。

---

## 4. Cat 5 alert · grade 三命名统一 (Q-NNN raise)

### 4.1 事实再述

| 来源 | 命名 | 形态 |
|---|---|---|
| frontend mock `TopCase.tier` / `ReachRate.tier` | `tier` | `"red"/"yellow"/"green"` |
| backend `RiskLevel.value` (`shared/kb_scan/models.py`) | `.value` 字符串 | 等价取值 |
| `runtime_dump.py:88` 写 yaml | `grade` | enum.value |
| `word_export.py:22` 注释 | 三键 fallback | snake-priority |
| `agent_credit/*` (推断) | `risk_level` (snake) | 跨 agent 已用 |

**`HeatCell.level` 不动** (热力 intensity ramp 0-4 · 非 grade)。

### 4.2 三选项 + 影响面

| 选项 | 含义 | 改面 |
|---|---|---|
| **A · `risk_level`** (snake) | 跟 agent_credit 趋同 · A6 schema 大概率走 snake | frontend mock + `AlertWorkspace.tsx` ~12 处 + `runtime_dump.py:88` 1 行 + `evaluation/manual/4_*.yaml` schema · word_export 注释清理 |
| **B · `tier`** (frontend 现状) | 改面最小 (前端) · 但 backend `RiskLevel` enum + runtime_dump + evaluation fixture 全改 | backend ~5 处 · evaluation fixture 大改 · word_export 注释清理 |
| **C · `grade`** (runtime_dump 现状) | evaluation adapter / `phase0_scan_sample.json` 已锁 | frontend mock + `AlertWorkspace.tsx` ~12 处 · word_export 注释清理 · 跨 agent 不一致 |

### 4.3 推荐: **A · `risk_level`** (snake_case)

理由:
1. 跟 agent_credit `risk_level` 趋同 · 跨 agent handoff schema 一致
2. backend python 主流 snake · A6 handoff schema 大概率 snake
3. `word_export.py:22` 注释已把 `risk_level` 列首选 · 改面最匹配后端兼容现状
4. frontend mock 改面虽 ~12 处但都是机械替换

但**不自决** (per onboarding §3 红线 #3): 需 A6 worker DONE 给出 `agent-handoff-schemas.md` 中 alert handoff schema 的最终命名 · OR PM 直接拍板。

### 4.4 Q-NNN 草稿 (raise 时填实际编号)

```
Q-NNN: alert 全栈 grade 字段命名统一 (cat 5)

背景:
  - frontend mock: TopCase.tier / ReachRate.tier ("red"/"yellow"/"green")
  - backend runtime_dump: grade (RiskLevel.value)
  - word_export 注释 fallback: risk_level / level / tier
  - HeatCell.level 是热力强度 ramp · 不卷入

三选项:
  A · risk_level (snake · 跟 agent_credit 趋同 · 推荐)
  B · tier (frontend 现状 · 改面前端最小)
  C · grade (runtime_dump 现状 · evaluation adapter 已锁)

推荐 A 理由: 跨 agent 一致 + A6 schema 大概率 snake + word_export 注释优先
等 A6 worker DONE 看其 schema 选项 OR PM 直接拍板

worker-A4-alert 拍板后照单全栈到位 (HeatCell.level 不动) ·
trailer GRADE-FIELD-UNIFIED-AS=<name> attached
```

---

## 5. Cat 11 alert · demo / live boundary (维持 Codex Keep)

| Entry | 现状 | A4-alert 动作 |
|---|---|---|
| `triggerTertiaryDemo` setDemoBanner | training-mode state 已 set | Keep · 加顶部 banner UI 真显 (规则 2) |
| `liveFail` banner | 已实装 (W-FIX-A3) | Keep |
| `runAlertScan` `forceMock: false` 默认真扫 (line 178) | live 优先 · 失败 record banner 不 silent swap | Keep |
| `triggerSecondaryScan` (规则集) line 206-211 | 同 primary 走 mock startScan | verify · 不 silent swap (live-fallback-banner-spec 规则 1) |

无 silent fallback · alert 此项相对干净 · 仅补 mock dropdown banner (规则 2)。

---

## 6. Cat 6 / Cat 7 alert · 范围界定 (Q-NNN 提前 raise)

**A2 worker DONE 状态**: `WORKER-A2-SHARED-INFRA-DONE` (commit `cf9623b` · 含 `shared/llm_caller/` + `shared/sse_envelope.py` + `shared/prompts/contract.py`) → 已可用。

**Cat 6 alert** (prompts.py 迁 8 段 contract template · evidence-first 三阶段):
- 改面: `agent_alert/prompts.py` 全文重写 · `agent_alert/scan_engine.py` LLM 调用点替换
- **建议**: 范围内 · 跟 4 gate 同批 · 一次到位

**Cat 7 alert** (api.py:312-313 LLMClient 直 init → shared/llm.chat_with_fallback):
- 改面: `agent_alert/api.py:_build_simple_llm_caller` + `agent_alert/scan_engine.py` LLM 调用点 (推断同模式)
- **建议**: 范围内 · 与 Cat 6 同批

**预期 Q-NNN-2 (若主 CLI 决定收窄 scope)**:
> Q: A4-alert worker 范围是否含 Cat 6 / Cat 7 (prompt + LLM caller 迁)?
> 选项 A: 含 · 4 gate + cat 4/5/6/7 一次到位
> 选项 B: 不含 · 只 4 gate + cat 4/5/11 · 6/7 推 Phase B 独立批
> 推荐 A: 5 子 worker (credit/alert/compli/riskctrl/report) 都有同问题 · 各自一次到位 cleanest · 否则 Phase B 还要再起 5 worker

---

## 7. `/api/alert/demo/run` 端点 + scenarios fixture

新建:
- `data/mock/workspace/alert/scenarios/baseline_100.json`
- `data/mock/workspace/alert/scenarios/manuf_policy_event.json`
- `data/mock/workspace/alert/scenarios/judicial_news_dual.json`

每 fixture shape = §3 done envelope (含 hit_list + industry_distribution + signal_heatmap + reach_rate + top_cases + dispositions)。**反 5 原则 #5 环境边界**: fixture 不含 difficulty / risk_level 等"答案字段" · Agent 自己算 (HitList + RiskLevel mapping)。

`agent_alert/api.py` 加:
```py
@app.post("/api/alert/demo/run")
async def alert_demo_run(req: AlertScanRequest):
    """Demo 路 · 不读 KB / 不调 LLM · load fixture · stream stage event · 输出 done envelope。
    与 /api/alert/scan 同 envelope shape · mode="mock"。
    """
    def gen():
        fixture = load_alert_scenario(req.scenario_key or "baseline_100")
        for stage_name in ["kb_load", "external_scan", "internal_match", "cross", "summary"]:
            yield sse_encode({"event": "stage", "stage": stage_name, "payload": {...}})
            time.sleep(0.4)  # 推进视觉
        yield sse_encode({**fixture, "event": "done", "mode": "mock"})
    return StreamingResponse(gen(), media_type="text/event-stream", headers={...})
```

---

## 8. Playwright smoke · `web/tests/regression/alert-pilot-4gate.spec.ts`

| # | 场景 | DOM 验证 |
|---|---|---|
| 1 | 默认 empty state | `data-alert-started="no"` · `data-testid="alert-empty-state"` |
| 2 | 选 mock dropdown 切 session | `data-alert-started="yes"` · 顶部 banner training-mode 显 · 5 panel 全切数据 |
| 3 | 切第二个 mock session | radar / hit_list / heatmap 全跟着切 (gap #2 修验) |
| 4 | textbox submit → SSE live | `event=stage` 推进 · `event=done` liveData 注入 · 5 panel 切 live · banner training-mode 隐 |
| 5 | live failed (mock 502 fixture) | `data-testid="alert-live-fail-banner"` 显 · retry button wire |
| 6 | TopCase 行 click → drawer | `data-testid="alert-drill-drawer"` 显 · `data-client-id="..."` · ESC 关 |
| 7 | export_docx button click | blob download (regression · 不破 F-064) |
| 8 | `/api/alert/demo/run` 端点 (curl mock) | done envelope 字段全 (totals + hit_list + industry + heatmap + reach_rate + top_cases + dispositions) |

---

## 9. ACK trailer 模板 (per onboarding §4)

DONE commit message:
```
feat(alert): WORKER-A4-ALERT-ADAPTER-DONE · 4 gate + done envelope + grade unified

4-GATE-INSTALLED: started + selectedSessionId + liveData + selectedClientId
DONE-ENVELOPE: hit_list + totals + industry_distribution + signal_heatmap + reach_rate + top_cases + dispositions + kb_state
STREAM-SSE-MIGRATED: yes (web/src/lib/api/_live.ts:streamSse 接入)
DEMO-RUN-ENDPOINT: POST /api/alert/demo/run + 3 scenarios fixture
SMOKE-PASS: web/tests/regression/alert-pilot-4gate.spec.ts (8 spec)
PRESERVES: F-020 + F-021 + F-022 + F-023 + F-049 + F-055 + F-061 + F-064
NEW-DOM: data-testid="alert-drill-drawer" + data-client-id + data-live-mode + data-session-id
GRADE-FIELD-UNIFIED-AS=<等 A6 / PM 决>
PRD-CAT-4-ALERT: stage/done envelope 共形 (引 sse-envelope.md)
PRD-CAT-5-ALERT-GRADE: 三命名归一 (引 Q-NNN-A)
PRD-CAT-6-ALERT-PROMPT: shared/prompts/contract.py 8 段迁 (若范围内)
PRD-CAT-7-ALERT-LLM: shared.llm.chat_with_fallback 接入 (若范围内)
PRD-CAT-11-ALERT-BANNER: mock dropdown banner 加 (live-fallback-banner-spec §2 规则 2)

Signal: WORKER-A4-ALERT-ADAPTER-DONE
```

---

## 10. 风险 / 待 PM-or-主 CLI 拍板

| # | 风险 | 收敛路径 |
|---|---|---|
| R1 | grade 三命名 · A6 schema 未 ratify | Q-NNN raise · 等 A6 DONE 或 PM 直接拍 · 默认 risk_level (snake) |
| R2 | `HeatCell.level` 与 grade 同名不同义 · 易卷入归一 | draft 已显式标"不动" · DONE 时 trailer 注明 |
| R3 | A4-alert scope 是否含 Cat 6/7 | Q-NNN-2 提前 raise · 推 A (含 · 一次到位) |
| R4 | A3 cherry-pick 时 ChannelWorkspace.tsx 行号变化 | GO 后第一步 = `git rebase chore/l0-infra` · 拿到最新 A3 后再读行号 cross-ref · 不锁死本 draft 引行号 |
| R5 | `runAlertScan` 内 SSE 实装细节本 draft 未读 (推断 inline · 未 verify) | GO 后第一步 = 读 `web/src/lib/api/alert.ts` 实装 + `_live.ts streamSse` · cross-ref 迁 |
| R6 | `drillCustomer` → `selectedClientId` 改名牵连 backend `/api/alert/drill/{client_id}` 调用方 (现已用 client_id) · 但 frontend 闭包内一些下游 derive 用 customer name | GO 后 grep 全栈 `drillCustomer` · 替换时保留 customer name 显示 (UI 文案) · state 用 client_id |

---

## 11. GO 后 step-by-step (照搬 workspace-state-protocol §7 + onboarding §1)

| # | 文件 | 动作 | 验证 | commit signal |
|---|---|---|---|---|
| 0 | (worktree) | `git rebase chore/l0-infra` 拿 A3 | git log clean | (无 commit) |
| 1 | `web/src/lib/mock/agent-alert-sessions.ts` (新建) | 拷 `agent-alert-session.ts` · 包成 array · 写 ≥ 3 sessions (难度分层) | tsc 0 error | `WORKER-A4-ALERT-MOCK-SESSIONS` |
| 2 | `AlertWorkspace.tsx` | 加 4 useState (started 已有 · 加 selectedSessionId / liveData / selectedClientId) · 改 import · sessionData derive | tsc 0 error · 默认渲 empty state · 选下拉切 mock | `WORKER-A4-ALERT-4GATE` |
| 3 | 5 panel function | 加 `sessionData` props · 删 const session 闭包 | 切下拉 panel 全跟 | `WORKER-A4-ALERT-PANELS-PROPS` |
| 4 | `agent_alert/api.py` SSE handler | done event 加完整 envelope (§3) · stage event 加 stage 名 · LLM caller 改 shared/llm | curl `/api/alert/scan` 看字段全 | `WORKER-A4-ALERT-DONE-ENVELOPE` |
| 5 | `runAlertScan` SSE 解析 | 切 streamSse · done 时 setLiveData(整 session) | live mode panel 全切 live | `WORKER-A4-ALERT-STREAMSSE` |
| 6 | DrillDrawer | TopCase onClick → setSelectedClientId · drawer 调 `/api/alert/drill/{client_id}` · ESC 关 | drawer smoke pass | `WORKER-A4-ALERT-DRILL-DRAWER` |
| 7 | grade 三命名归一 | 全栈替换 (per Q-NNN A 决 · default risk_level) | grep 0 残留 (HeatCell.level 不动) | `WORKER-A4-ALERT-GRADE-UNIFIED` |
| 8 | mock dropdown banner | training-mode banner 加 · `selectedSessionId` 联动 | spec 规则 2 验 | `WORKER-A4-ALERT-MOCK-BANNER` |
| 9 | demo/run 端点 + 3 fixture | 新建 + scenarios | curl smoke pass | `WORKER-A4-ALERT-DEMO-RUN` |
| 10 | (Cat 6/7 范围内时) prompts/contract + chat_with_fallback 接入 | 改 prompts.py + api.py LLM caller | unit test pass | `WORKER-A4-ALERT-PROMPT-LLM` |
| 11 | Playwright smoke | 8 spec 写 + 跑 | 全绿 | `WORKER-A4-ALERT-SMOKE` |
| 12 | features-inventory.md | F-020/021/022/023/049/055/061/064 PRESERVES verify · 新加必要 entry | inventory 全引用 | (含 12 之内 commit) |
| 13 | 删 `agent-alert-session.ts` 单 const | 全 import 已迁 | grep 0 残留 | `WORKER-A4-ALERT-LEGACY-MOCK-PURGED` |
| 14 | 最终 DONE | 收尾 | 全 trailer fill | `WORKER-A4-ALERT-ADAPTER-DONE` |

---

**Author**: worker-A4-alert (Claude · 主 CLI 派的 worker CLI)
**Date**: 2026-04-29
**Status**: §0.5 wait gate · A3 未 cherry-pick · 等 GO `A4-ALERT-GO-AFTER-A3`
**Next**: commit 本 draft · 等主 CLI A3 cherry-pick + GO signal · 不再二次思考 · 照搬 §11 顺序执行
