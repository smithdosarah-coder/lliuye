# Features Inventory · 已交付前端 feature 清单

> **目的**：防回档。worker 派活前必读·改动后必须在 commit trailer 列 `PRESERVES: F-XXX` 声明保留。
> **约束**：本清单是 worker 改 `web/` 的 contract——任何改动都不能破坏已列 feature·破坏视作 regression。
> **生成于**：2026-04-27·基于 6 个回档 bug 反推首批 entries。后续每修一个 bug / 上线一个新 feature 必须 enrich。

## 模板

```yaml
F-XXX · <短标题>
location: <主文件路径> + 引用点
selector: <DOM data-testid 或类名>
interaction: <一句话描述用户操作 → 系统响应>
introduce: <commit_hash>  <YYYY-MM-DD>  <commit subject 摘要>
lost_at: <commit_hash 或 N/A>
restored: <commit_hash 或 pending>
smoke_test: <web/tests/regression/*.spec.ts 路径·没写就标 pending>
```

---

## F-001 · 退出登录按钮

- **location**: `web/src/components/shell/LogoutButton.tsx` + 引用于 `Masthead.tsx` / `PersonaSwitcher.tsx`
- **selector**: `[data-testid="logout-button"]`（待 cherry-pick 后确认）
- **interaction**: click → `store.logout()` → redirect `/login`
- **introduce**: `05fafcd` 2026-04-23「退出登录 pill · 画布/主题双 pill 对齐」
- **lost_at**: `63107fb` 2026-04-26「Stage 1 · file-snapshot 8 文件」LogoutButton.tsx 文件被删
- **restored**: pending（Phase C.1 cherry-pick `05fafcd`）
- **smoke_test**: `web/tests/regression/logout.spec.ts` pending

## F-002 · 画布开关 pill（CanvasModeToggle）

- **location**: `web/src/components/shell/CanvasModeToggle.tsx`·引用于 `AppShell.tsx`
- **selector**: `[data-testid="canvas-mode-toggle"]`
- **interaction**: click → 切换 `panel-canvas` ↔ `free-drag` mode
- **introduce**: `63107fb` 2026-04-26（毛玻璃）+ `05fafcd` 2026-04-23（双 pill 对齐）
- **lost_at**: `315de1e` 2026-04-22 revert 把 motion tokens 删了·样式降级
- **restored**: pending（Phase C.2）
- **smoke_test**: `web/tests/regression/canvas-toggle.spec.ts` pending

## F-003 · 主题切换 pill（ThemeSwitch · 4 主题）

- **location**: `web/src/components/shell/ThemeSwitch.tsx`
- **selector**: `[data-testid="theme-switch-{canvas|matcha|dusk|ink}"]` × 4
- **interaction**: click theme → set `data-theme` on `<html>` → 切换 4 主题渐变（**不含已下架的 Letterpress / Nebula**）
- **introduce**: 同 F-002（双 pill 升级）
- **lost_at**: 同 F-002（token 降级）
- **restored**: pending（Phase C.2）
- **smoke_test**: `web/tests/regression/theme-switch.spec.ts` pending

## F-004 · Forge（Agent2 风控）Workspace · ScanCTA 触发按钮

- **location**: `web/src/components/shared/ScanCTA.tsx` + `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx`
- **selector**: ScanCTA 内的 `<button>` 触发回测
- **interaction**: click → POST `/api/run/riskctrl`（multiplexer endpoint）→ SSE 流式更新进度
- **introduce**: `ffc60ca` 2026-04-23「5 agent workspace 共享 ScanCTA · 补齐过程感演示」
- **lost_at**: `95437b6` 2026-04-26「Stage 3 微信气泡 + dispatch group/dm split」改了 ScanCTA `onDone` callback
- **restored**: pending（Phase C.3 对比版本 + 小修）
- **smoke_test**: `web/tests/regression/forge-trigger.spec.ts` pending

## F-005 · Scout（Agent1 获客）· 自由搜索标签

- **status**: 🔴 NEVER CORRECTLY DELIVERED·产品定位错·待重做
- **location**: `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` QueryBar 区 + `web/src/lib/mock/agent-channel-session.ts` query 部分
- **interaction (期望)**: 客户经理输入 / 组合 tag → 自由搜索企业·候选基于 tag 命中·**不是** look-alike 找相似
- **introduce (错版)**: `19b6d72` 2026-04-24 实现成 look-alike KB matcher（worker 误解产品定位）
- **regress**: `95437b6` 2026-04-26 placeholder 改为「标杆客户名 / 描述画像」·**仍是错的方向**
- **fix_path**: 重写 QueryBar + ScoutQuery 类型·spec 由 PM 提供后 implement·**不能 cherry-pick · 必须新做**
- **smoke_test**: `web/tests/regression/scout-tag-search.spec.ts`（重写后写）

## F-006 · ScoreRadar 8 维评分雷达图 · 毛玻璃样式

- **location**: `web/src/components/viz/ScoreRadar.tsx` + 各 Workspace 内引用（Scout / Forge / Credit）
- **interaction**: render 8 维 radar（该企业 vs 行业 P50）
- **introduce**: `3a20bdf` v14-v5 baseline 毛玻璃风格首次落地
- **lost_at**: 全局 token 降级（`315de1e` revert）间接波及·CSS 看起来是默认样式
- **restored**: pending（Phase C.5 手动 CSS 恢复）
- **smoke_test**: visual snapshot regression（pending）

## F-007 · Today 页 · 空白状态（不含 worker hallucinate 的 4 块）

- **location**: `web/src/app/today/page.tsx` + `web/src/components/today/Hero.tsx`
- **MUST NOT contain**:
  - PriorityQueue（今日队列 · Priority 5 客户清单）
  - EventTimeline（事件流 · Timeline）
  - 4 KPI 大数字（本月已放款 / 待签卷宗 / 观察名单 / 本周新政）
- **MUST contain**: 空白 hero + 「开始演示」CTA（PM 愿景·worker 自由发挥多了 4 块）
- **introduce (错版)**: `bc70e65` + `a82efe5` 2026-04-20 worker 加 PriorityQueue + EventTimeline
- **fixed_at**: `f1acf66` 2026-04-21 删除 import 和渲染（但 user 截图显示当前 production 还有这些 block·**ECS 跑的可能不是 chore/l0-infra**·待 verify）
- **fix_path**: verify `f1acf66` 是否在 ECS production·不在则 cherry-pick（Phase C.6）
- **smoke_test**: `web/tests/regression/today-empty.spec.ts` 验 DOM **不含** `[data-testid="today-priority-queue"]` / `today-event-timeline` / `today-kpi-belt`

## F-008 · 气泡拖拽到画布 → 缩略图卡片

- **location**: `web/src/components/dispatch/MessageBubble.tsx` + `web/src/components/shell/MessagePinHandle.tsx` + `web/src/app/dispatch/_store/dispatch-store.ts`
- **selector**: `[data-pin-handle="message"]` drag source · drop target Whiteboard
- **interaction**: dispatch 消息气泡 drag handle → 拖到 Whiteboard 区域 → 缩略图卡片渲染（thumbnail·**不是** url 链接）
- **MIME**: `PANEL_PIN_MIME` 双 MIME 拖柄（缩略图 logic 依赖此 MIME）
- **introduce**: `a5572b9` 2026-04-22「任务2 · MessagePinHandle · 双 MIME 拖柄」
- **lost_at**: `95437b6` 2026-04-26 dispatch-store.updateMessage 改·`refs` 字段移除·拖柄 onDragStart 逻辑改
- **restored**: pending（Phase C.7 cherry-pick `a5572b9` + verify dispatch-store 兼容）
- **smoke_test**: `web/tests/regression/bubble-drag-thumbnail.spec.ts` pending

---

## F-050 · Compli Workspace · 空白启动 + 3 CTA 分级

- **location**: `web/src/app/archive/compliance/_components/ComplianceWorkspace.tsx`（`started` state + `TriggerBar` + `EmptyStateSkeleton`）+ `compliance-workspace.css` 末尾 Stage CF 段
- **selector**: `[data-testid="compli-workspace"][data-started="no"]` · `[data-testid="compli-empty-skeleton"]` · `[data-testid="compli-history-dropdown"]` · `[data-testid="compli-template-check-cta"]` · `[data-testid="compli-policy-scan-cta"]`
- **interaction**:
  - default `started=false` · 仅 Hero + UploadRail + TriggerBar + 空骨架
  - Primary 上传 + 「开始政策比对」 → `setStarted(true)` + POST `/api/compliance/policy_scan` (SSE) → 落 `scanId`
  - Secondary 「用模板快速比对」 → POST `/api/compliance/matrix_check` 同步 demo
  - Tertiary 历史 dropdown 标 `(示例)` → demo banner 显示
- **contract**: `docs/contracts/empty-state-design-protocol.md` v1.0 · production / mock 路径分离 · mock 不 default load
- **introduce**: pending Stage CF 第 1 批 cherry-pick
- **lost_at**: N/A（新 feature · 此前 ComplianceWorkspace 默认 load mock 数据 · 无 empty state）
- **smoke_test**: `web/tests/regression/compli-empty-state.spec.ts`（5 case · 默认空 + dropdown 标 + 3 CTA 分级 + tertiary trigger + primary CTA mock SSE）

## F-054 · Compli Workspace · 完整 production-grade pipeline (3 endpoints + Word 导出)

- **location**: `web/src/app/archive/compliance/_components/ComplianceWorkspace.tsx`（`triggerPolicyScan` / `triggerTemplateCheck` / `triggerExportDocx` handlers · `RevisionPanel` 接 `scanId/exportInfo/onExportDocx` props）· `web/src/lib/api/compliance.ts` (W-FIX2-A3 加 · runPolicyScan / runMatrixCheck / exportDocx)
- **selector**: `[data-testid="compli-policy-upload-cta"]` · `[data-testid="compli-business-upload-cta"]` · `[data-testid="compli-matrix-cell"]` · `[data-testid="compli-conflict-chip"]` · `[data-testid="compli-revision-draft"]` · `[data-testid="compli-export-docx-btn"]` · `[data-testid="compli-live-fail-banner"]`（W-FIX2-A3 加） · `[data-testid="compli-live-fail-retry"]`（W-FIX2-A3 加）
- **interaction**:
  - 上传政策 + 业务制度 → SSE 抽规则 → 抽事件 → N×M 矩阵 → 改/补/强 LLM 修订
  - 矩阵 cell click 展开左右对照纸 + 条款映射
  - RevisionPanel 改/补/强 三 chip + 展开建议列表
  - 「导出修订意见 Word」 → POST `/api/compliance/export_docx` → blob → a.click() 触发下载
- **backend wire**: Stage C.4 `agent_compliance/api.py` 3 endpoints (`a76cea2`)
- **introduce**: pending Stage CF 第 1 批 cherry-pick
- **lost_at**: N/A（新增 backend wiring · ComplianceWorkspace 既有 mock viz 转为 SSE 真接 + Word 导出）
- **smoke_test**: `web/tests/regression/compli-empty-state.spec.ts`（部分覆盖 · 完整 SSE 解析跑通待 Stage D playwright）
- **W-FIX2-A3 fix (2026-04-29)**: bug #5 修复 · 之前 primary CTA 路径 hardcode `force_mock: true` (line 113) 静默走 mock policy corpus · UI 标 live · 用户欺骗 (违反 live-fallback-banner-spec.md §1.5 production / demo 路径分离)。
  - **fix**: primary path 现 `force_mock: false` · 真接后端 SSE · 失败 → live-fail banner（per spec §2 规则 1）· `mock` 仍只在 tertiary `(示例)` dropdown 路径
  - **新 selector**: `compli-live-fail-banner` + `compli-live-fail-retry` (status / endpoint data-attrs)
  - **新 client**: `web/src/lib/api/compliance.ts` 复用 `_live.ts` LiveFailError + streamSse · Pattern 与 riskctrl/alert client 一致

---

## F-051 · Riskctrl/Forge Workspace · 空白启动 + 3 CTA 分级

- **location**: `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx`（`started` state + `RiskTriggerBar` + `RiskEmptySkeleton`）+ `riskctrl-workspace.css` 末尾 Stage CF2 段
- **selector**: `[data-testid="riskctrl-workspace"][data-started="no"]` · `[data-testid="riskctrl-empty-skeleton"]` · `[data-testid="riskctrl-history-dropdown"]` · `[data-testid="riskctrl-preset-dropdown"]` · `[data-testid="riskctrl-dsl-gen-cta"]`
- **interaction**:
  - default `started=false` · 仅 Hero + RiskTriggerBar + 空骨架（4 panel placeholder）
  - Primary 「选样本 + 写策略 · 生成 DSL」按钮 → `setStarted(true)` + POST `/api/riskctrl/dsl_gen` (SSE) → 落 `rulesetId`
  - Secondary 预置规则集 dropdown → `setStarted(true)` + 直接展示
  - Tertiary 历史回测 dropdown 标 `(示例)` → demo banner 显示
- **contract**: `docs/contracts/empty-state-design-protocol.md` v1.0 · production / mock 路径分离
- **introduce**: pending Stage CF2 第 2 批 cherry-pick
- **lost_at**: N/A（新 feature · 此前 RiskctrlWorkspace 默认 load mock 数据 · 无 empty state）
- **smoke_test**: `web/tests/regression/riskctrl-empty-state.spec.ts`（6 case · 默认空 + dropdown 标 + 3 CTA 分级 + tertiary trigger + secondary trigger + primary mock SSE）

## F-056 · Riskctrl Workspace · 完整 production-grade pipeline (3 endpoints + Word 导出)

- **location**: `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx`（`triggerDslGen` / `triggerBacktest` / `triggerExportDocx` handlers · `RiskOutputPanel` 接 `rulesetId/exportInfo/onExportDocx` props）
- **selector**: `[data-testid="riskctrl-dsl-editor"]` · `[data-testid="riskctrl-ks-chart"]` · `[data-testid="riskctrl-sample-dist"]` · `[data-testid="riskctrl-backtest-cta"]` · `[data-testid="riskctrl-export-docx-btn"]`
- **interaction**:
  - 写策略文本 → POST `/api/riskctrl/dsl_gen` SSE → 真 LLM 生成 DSL 树 → 落 ruleset_id
  - 「样本回测」CTA → POST `/api/riskctrl/backtest` SSE → KS / AUC / 通过率 / 样本分布刷新
  - DSL 树展示 4 op (IF / AND / OR / THEN) · KS 双线图 · sample stacked bars
  - 「导出回测报告 Word」 → POST `/api/riskctrl/export_docx` (后端 stub · 404 时 fallback banner) → blob → a.click() 下载
- **backend wire**: Stage C.5 backend (cb8bff1 · `agent_riskctrl/api.py` `/dsl_gen` + `/backtest`)
- **introduce**: pending Stage CF2 第 2 批 cherry-pick
- **lost_at**: N/A（新增 backend wiring · DSL editor / KS chart 转为 SSE 真接 + Word 导出 placeholder）
- **smoke_test**: `web/tests/regression/riskctrl-empty-state.spec.ts`（部分覆盖 · 完整 SSE + 导出待 Stage D playwright）

---

## F-058 · IM WebSocket 实时 + Thread 持久化 + 6 kind 渲染 (Stage D.2F frontend)

- **location**:
  - `web/src/lib/im/websocket.ts` (ImWebSocketClient · reconnect exponential backoff · heartbeat 30s)
  - `web/src/lib/api/im.ts` (REST: listThreads / listMessages / sendMessage / markThreadRead / createThread)
  - `web/src/app/dispatch/_components/ImLiveBridge.tsx` (mount-once side-effect · fetch threads + connect ws + subscribe currentThreadId + pruneTyping)
  - `web/src/app/dispatch/_components/MessageStream.tsx` (WS state pill + typing indicator + history-load button + mark-read on switch)
  - `web/src/app/dispatch/_components/MessageBubble.tsx` (PinRefThumbnail · pin_ref kind 渲染缩略图卡 · 不显 url)
  - `web/src/app/dispatch/_components/ComposerBar.tsx` (typing debounce 1s + sendMessage REST 持久化)
  - `web/src/app/dispatch/_store/dispatch-store.ts` (ingestRemoteMessage / setRemoteThreads / noteTyping / pruneTyping / liveMode + wsState)
  - `web/src/lib/store/types.ts` (ImMessage.kind 加 "pin_ref" · refs 加 agentId/href/fullText/thumbDataUrl/agentRunId · additive · Q-037 precedent)
- **selector**:
  - `[data-testid="dispatch-view"]` · `[data-testid="im-ws-state"]` · `[data-testid="im-typing-indicator"]`
  - `[data-testid="im-thread-history-load"]` · `[data-testid="im-pin-ref-thumbnail"]`
- **interaction**:
  - mount: ImLiveBridge listThreads → setRemoteThreads + connect ws · fallback "live_with_seed_fallback" 兜底
  - switch thread: 自动 listMessages + ws.subscribe(tid) + markThreadRead
  - send message: addMessage 本地 optimistic + sendMessage REST 持久化 · WebSocket broadcast 给其他 user · ingest 时按 id dedup
  - typing: ComposerBar input change debounce 1s emit ws.sendTyping · 其他 user 收 typing event → noteTyping → MessageStream 渲染 indicator (3s expire · pruneTyping 1s 周期清)
  - 重连: ImWebSocketClient exponential backoff (1s → 2s → 4s → 8s → 16s → cap 30s) · re-subscribe 历史 thread
  - heartbeat: 30s 内发 typing-self · backend 60s timeout 安全 buffer
- **backend wire**: Stage D.2 backend (ab59186 · 7c2afaf MERGED)
- **contract**: `docs/contracts/im-protocol.md` v1.0 (§3 schema · §4 ws · §5 6 kind · §7 pin_ref · §10 migration)
- **introduce**: pending Stage D.2F cherry-pick
- **lost_at**: N/A (新 feature · 此前 dispatch 走 polling fetch + seed only · 无 WebSocket / 无持久化)
- **smoke_test**: `web/tests/regression/im-websocket.spec.ts` (5 case · route load + WS state + history-load + pin_ref thumbnail + typing indicator container)
- **NB**:
  - seed 数据保留作 `liveMode="live_with_seed_fallback"` UI · 后端 unreachable 时演示不崩
  - 真客户端双 user realtime 验证留 Stage D 主 CLI 用 websocat 跑
  - D.1 frontend AuthGate (Worker A2 同期) 提供 cookie auth_token · 本批 fallback `getImToken()` 取 cookie / localStorage / demo-u_wangzhe

---

## F-061 · Riskctrl + Alert live-fallback banner (W-FIX-A3 · live-fallback-banner-spec v1.0)

- **location**:
  - `web/src/lib/api/_live.ts` (LiveFailError class · postLive · streamSse helper)
  - `web/src/lib/api/riskctrl.ts` (runDslGen / runBacktest / exportDocx · 不 silent swap)
  - `web/src/lib/api/alert.ts` (runAlertScan / fetchHitlist / fetchDrill · 4xx/5xx 抛 LiveFailError)
  - `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx` (`liveFail` state + banner JSX)
  - `web/src/app/archive/alert/_components/AlertWorkspace.tsx` (`startScan` 真接 SSE + banner JSX + scanSessionId state)
  - `web/src/app/archive/riskctrl/riskctrl-workspace.css` (+60 LOC · `.riskctrl-live-fail-banner*`)
  - `web/src/app/archive/alert/alert-workspace.css` (+60 LOC · `.alert-live-fail-banner*`)
- **selector**:
  - `[data-testid="riskctrl-live-fail-banner"]` · `[data-testid="riskctrl-live-fail-retry"]`
  - `[data-testid="alert-live-fail-banner"]` · `[data-testid="alert-live-fail-retry"]`
  - `[data-testid="alert-workspace"][data-scan-session-id]` (scan 通时落 sessionId)
- **interaction**:
  - Riskctrl backtest: HTTP 422 root cause = backend 必填 instruction + uploaded_files (Pydantic 默认无 default factory) · frontend `runBacktest({uploadedFiles: []})` 已显式传 [] 防 422 · 失败时 banner 显 "后端 X 调用失败 (HTTP 422) · 当前显 fallback 演示数据" + retry button + body excerpt detail
  - Riskctrl dsl_gen / export_docx: 同处理 · 5xx / network / SSE error → banner
  - Alert startScan: 不再纯本地 mock toggle · `runAlertScan({forceMock: true})` 真 POST /api/alert/scan SSE · 失败 banner · 成功 setScanSessionId
  - 失败时仍渲染 fallback mock viz · 但 banner 显式标 "fallback 演示数据" · 不静默
  - retry button 重跑同一调用 · dismiss × 关 banner
- **contract**: `docs/contracts/live-fallback-banner-spec.md` v1.0 §2 规则 1-4
- **introduce**: pending W-FIX-A3 cherry-pick
- **lost_at**: N/A (新 feature · 此前 silent swap mock · 用户怒"左右脑互博")
- **smoke_test**: `web/tests/regression/riskctrl-alert-fix.spec.ts` (4 case · riskctrl 422 + dsl_gen 500 + alert scan 503 + alert scan 200)
- **NB**:
  - 422 root cause 已 verify (TestClient 真打 backend) · backend Pydantic schema 严格 · 缺 uploaded_files / instruction 都返 422
  - LiveFailError 含 status / endpoint / bodyExcerpt 三字段 · banner 渲染 detail · 帮 ops 一眼看根因
  - export_docx 404 (后端未上线) 显式视为 pending · 不弹 banner · 走原 exportInfo error 状态

---

## F-062 · Compli ForceMock Hardcode 删除 + Live-fallback banner (W-FIX2-A3 · live-fallback-banner-spec v1.0)

- **location**:
  - `web/src/lib/api/compliance.ts` (新 · runPolicyScan / runMatrixCheck / exportDocx · 复用 `_live.ts` LiveFailError + streamSse pattern)
  - `web/src/app/archive/compliance/_components/ComplianceWorkspace.tsx` (`liveFail` state + recordLiveFail/clearLiveFail + banner JSX · 删 hardcode `force_mock: true`)
  - `web/src/app/archive/compliance/compliance-workspace.css` (+62 LOC · `.compliance-live-fail-banner*`)
- **selector**:
  - `[data-testid="compli-live-fail-banner"]` (status / endpoint data-attrs)
  - `[data-testid="compli-live-fail-retry"]` (retry button)
- **interaction**:
  - **bug #5 (修)**: primary CTA「开始政策比对」之前 (Stage CF · `c75488f`) hardcode `force_mock: true` · 用户点 → 实际跑 mock policy corpus · UI 仍标 live · 静默欺骗（左右脑互博）
  - **fix**: primary path 现 `force_mock: false` · 真接后端 SSE · 失败 → live-fail banner（per spec §2 规则 1）· mock 仅 tertiary `(示例)` dropdown 显式 demo banner
  - secondary template_check 同处理: 4xx/5xx/network → liveFail banner · 不再 silent
  - export_docx 404 (Stage 未上线) 仍走 exportInfo pending error · 不弹 banner（与 riskctrl 同 fallback pattern）
- **contract**: `docs/contracts/live-fallback-banner-spec.md` v1.0 §1.5 (production / demo 路径必须显式分开) · §2 规则 1 (live failed → 显式 banner)
- **introduce**: pending W-FIX2-A3 cherry-pick
- **lost_at**: N/A (修 Stage CF `c75488f` 引入的 hardcode bug · 之前 user 投诉「左右脑互博」)
- **smoke_test**: `web/tests/regression/compli-empty-state.spec.ts` (新加 2 case · primary force_mock:false body verify + primary 503 → live-fail banner)
- **NB**:
  - 与 F-061 (Riskctrl + Alert) 同 pattern · 复用 `_live.ts` LiveFailError + streamSse
  - tertiary mock dropdown 路径 `compli-demo-banner` 已 wire (Stage CF) · 本 fix 不动
  - test runner 见 `web/tests/regression/compli-empty-state.spec.ts` · 加 case 「force_mock:false body verify」 + 「primary path 失败 → live-fail banner 显」

---

## 待补（用户暗示"还有很多其他的"）

F-009 ~ pending · 等用户继续指出 → enrich 此清单

---

## 维护规则

1. **新 feature 落地必须加 entry**·worker 在 commit message 内 trailer `INVENTORY-ADDED: F-XXX`
2. **修复回档必须更新 entry**·trailer `RESTORED: F-XXX <commit_hash>`
3. **改 web/ 不动 inventory feature**·trailer `PRESERVES: F-001, F-005, ...` 列保留 id
4. **smoke test 写完后**·把 `pending` 替换为实际路径
5. **每周巡检**：grep `web/` 找未列入 inventory 的 critical interaction（按钮 / 拖拽 / 跳转）补 entry
