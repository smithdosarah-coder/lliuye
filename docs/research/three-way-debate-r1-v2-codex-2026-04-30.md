# 三方辩论 R1 v2 · Codex 全扫 web/src 后独立前端方案

> Codex high reasoning · sandbox read-only · 主 CLI 落盘代写 · 任务 ID blo0yym6g
> 完工 ~5 min (高效 · per protocol v2 SLA OK)

## Step 1 Inventory (真扫 156 文件)

全扫 `web/src`:
- **103 个 .tsx**
- **53 个 .ts**
- **合计 156 文件**

每个文件 `--- READ path (lines)` 已输出 (sandbox shell)。重点大文件 (≥ 200 行) 全读: 6 个 archive workspace + dispatch store/components + customer + warroom + audit + lib/api + lib/auth + shell/shared。

## Step 2 R1 v2 (基于真全扫 · 上轮全错位)

### 真痛点 (6 个 · 全是产品深层 bug · 不是 UI 视觉)

#### 1. 客户上下文断链 (P0 critical)
- `CustomerPage` 链 `${a.path}?customer=${customerId}` (`web/src/app/customer/[id]/_components/AgentTileStrip.tsx:89`)
- `dispatch` 也 push `?customer=` (`web/src/app/dispatch/_components/ComposerBar.tsx:273`)
- 但 **archive workspace 不读 query**
- Credit/Report 有 `CustomerSelector` 但未传 value/onChange (`CreditWorkspace.tsx:859` · `ReportWorkspace.tsx:603`)
- Selector 自述 "实际数据切换由上层处理" 但上层不传 (`web/src/components/shared/CustomerSelector.tsx:7`)
- **影响**: RM 从 customer 360 / IM 调 agent · workspace 仍是默认样本 → 工作流断

#### 2. Evidence-First 多处挂 fixture (P0 critical)
- 6 workspace 都用固定 evidence fixture:
  - `ChannelWorkspace.tsx:379`
  - `CreditWorkspace.tsx:485`
  - `ReportWorkspace.tsx:452`
  - `AlertWorkspace.tsx:552`
  - `ComplianceWorkspace.tsx:439`
  - `RiskctrlWorkspace.tsx:357`
- fixture 自述 "真后端 SSE 接入后替换" (`web/src/components/evidence/fixtures.ts:7`)
- **影响**: 审贷员/合规官看到的是演示证据 · 不一定对应当前 live output (反 north star §3.3 Evidence-First)

#### 3. Dispatch 发消息双路径 (P1 真 bug)
- submit 后先 `sendMessageRest` 到 `/api/im/messages` (`web/src/app/dispatch/_components/ComposerBar.tsx:177` · `web/src/lib/api/im.ts:210`)
- 随后**无条件**再 fetch `/api/im/send` (`ComposerBar.tsx:216`) · 失败 silent fallback (`ComposerBar.tsx:240`)
- **影响**: RM 可能收重复回复 · 审计事件不可信

#### 4. Warroom 拒绝工单消失 (P1)
- 看板列只含 `requested/accepted/in_progress/completed` (`web/src/app/warroom/_store/ticket-store.ts:30`)
- 但 drawer 可 `updateStatus(..., "rejected")` (`web/src/app/warroom/_components/TicketDrawer.tsx:139`)
- **影响**: 风险经理/合规官退回交接后 · 主看板不可追踪

#### 5. Audit 不是可靠审计 (P1)
- AuditView 读内存 event-bus `history` (`web/src/app/audit/AuditView.tsx:57`) · 只切前 50 (`AuditView.tsx:65`)
- event-bus cap 200 且不持久 (`web/src/lib/store/event-bus.ts:14, 41`)
- 客户页还会 seed 演示事件 (`web/src/app/customer/[id]/CustomerPageClient.tsx:93`)
- **影响**: 合规官无法把它当审计账本

#### 6. ScanCTA 仍是老式假进度/幽灵 API (P2)
- fetch `/api/run/{agent}` · 失败只 warn · 始终 `onDone` (`web/src/components/shared/ScanCTA.tsx:78, 83, 102`)
- Riskctrl 用它触发 backtest (`RiskctrlWorkspace.tsx:477`) · 但 backtest 又可能因无 DSL 报错 (`RiskctrlWorkspace.tsx:277`)
- **影响**: 风险经理看到"完成"后才失败

### 推荐 Action (7 个 · 全是补真 bug · 不是 UI polish)

| # | Action | Phase | 工程量 | DoD | 风险 | 证据 |
|---|---|---|---|---|---|---|
| **C7** | CustomerContextGateway (读 ?customer · focus customer-store · 传入 4 workspace) | B-1 | 中 | 从 customer/dispatch/today 进入后 hero/query/默认 scan 一致 | demo id 需映射 | AgentTileStrip.tsx:89 · ComposerBar.tsx:273 · CustomerSelector.tsx:18 |
| **C8** | Live evidence adapter (EvidenceProvider 优先吃 liveData · fixture 只 mock/demo) | B-1/B-3 | 中 | live SSE 后 ClaimText/EvidenceTrail 同源 | 后端字段不齐 | 6 workspace EvidenceProvider 行 · fixtures.ts:7 |
| **C9** | Dispatch 单发送路径 (删 /api/im/send 或并入 sendMessageRest) | B-1 | 小 | 一次 submit 仅一个 POST · 失败可见 banner | - | ComposerBar.tsx:177, 216, 240 |
| **C10** | Warroom rejected lane (加列 OR 显式"已退回/归档"过滤) | B-1 | 小 | 拒绝后卡片仍可查 · source event/payload 保留 | - | ticket-store.ts:30 · TicketDrawer.tsx:139 |
| **C11** | Audit 降级标识或接后端 (短期标 "session-only demo" · 中期接 /api/audit) | B-3 | 中 | 刷新不丢关键事件 · 演示 seed 不混成审计 | - | AuditView.tsx:57 · event-bus.ts:14 |
| **C12** | 替换 live 路径 ScanCTA (Report mock CTA 留 · Riskctrl backtest 改直接 live action + 真 running/error) | B-3 | 小/中 | 无 /api/run/riskctrl 幽灵调用 | - | ScanCTA.tsx:78 · RiskctrlWorkspace.tsx:477 |
| **C13** | 抽 shared live-fail/evidence hook (6 workspace 已重复 liveFail/retry/banner) | B 末 | 中 | 统一 status/bodyExcerpt/retry API · 不改视觉 | - | ComplianceWorkspace.tsx:251 · RiskctrlWorkspace.tsx:189 · AlertWorkspace.tsx:363 |

### 反对借鉴 / 不做

1. **不做通用 BI dashboard 化**: 当前产品特色是 panel pin/whiteboard/canvas (`AppShell.tsx:86` · `PanelCanvas.tsx:85` · `Whiteboard.tsx:88`) · 应保留
2. **不取消 demo/mock**: Report 已明确 demo 难度分层且"不调 LLM" (`ReportWorkspace.tsx:1738`) · 价值是稳定客户走访
3. **不把 Riskctrl 强行单客户化**: 代码注释已说明策略回测不针对单客户 (`RiskctrlWorkspace.tsx:660`)
4. **不继续加 hero/视觉 chrome**: 痛点在状态与证据闭环 · 不在首屏装饰

## Step 3 对比上轮 R1 (game-changer)

### 上轮漏了
- archive 五个大 workspace 内部 (alert/compliance/report/channel/riskctrl)
- customer 360
- warroom
- audit
- lib/api/auth
- shell/shared

### 本轮补出 (跨模块产品深问题)
- 客户上下文断链
- fixture evidence (反 Evidence-First)
- dispatch 双发送
- rejected 工单消失
- audit 非持久

### 关键 verdict 变化
> 上轮若把重点放在统一 UI/视觉 polish · **需要降级**
> 现在 verdict 改为先补数据与状态闭环

### 坚持项
live fallback banner 不应再大改 · 代码已在 Alert/Compliance/Riskctrl/Report 多处落地。

## Step 4 Verdict (≤ 200 字)

**必做**: CustomerContextGateway · live evidence adapter · dispatch 单发送 · warroom rejected lane (4 个真 bug · 全 P0/P1)

**撤回**: 为竞品样式而改首页/看板 · 强行把 Riskctrl 单客户化 · 取消 demo/mock

**改 scope**: ScanCTA 只从 live 风险路径撤出 · Report mock 演示保留 · audit 先标 session-only · 再接后端

## Step 5 vs v3 完整版方案对比 (主 CLI 视角加补)

v3 完整版方案 v3 14 action 主要 UI/视觉 (Gemini 主导) + 部分产品 (主 CLI A5 / Codex C5) · 本 R1 v2 加补**6 个产品深 bug**:

| v3 没覆盖 | R1 v2 必加 |
|---|---|
| ❌ 客户上下文断链 | C7 CustomerContextGateway (P0) |
| ❌ Evidence fixture 假 | C8 Live evidence adapter (P0 · 反 Evidence-First) |
| ❌ Dispatch 双发送 bug | C9 单发送路径 |
| ❌ Warroom rejected 消失 | C10 rejected lane |
| ❌ Audit 不可靠 | C11 降级标识 + 接后端 |
| ❌ ScanCTA 幽灵 API | C12 替换 live 路径 |

**Phase B 工程量重估**:
- v3: ~5 周 (~4-4.5 周 wall-clock)
- v3 + R1 v2 加补 7 action (3 B-1 + 3 B-3 + 1 B 末): +1.5-2 周
- **v4 final**: ~6.5-7 周 (~5-5.5 周 wall-clock)

但这些都是真 bug 修 · 不是优化 · 必做。
