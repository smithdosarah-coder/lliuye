# W2-frontend Progress (append-only)

> 接力 sub-agent 必读 · main session 监控源 · sub-agent checkpoint 每次 append 一段
>
> 对应 brief: `docs/onboarding/W2-frontend-worker.md`
> 仓库: `credit_matrix_next/` (新仓 · 物理隔离 · 不动老仓 web/)
> handoff protocol: `docs/onboarding/W1-worker-handoff-protocol.md` v1.0 (沿用)

## 2026-05-12 · checkpoint 2 · SSE bridge + page.tsx 真接 + store 扩

- **完成文件** (4/18):
  - `credit_matrix_next/lib/sse/useLiuyeBridge.ts` (新 · 254 行 · 11 event 全分流 + heartbeat keepalive · 共 11 named case + default fall-through)
  - `credit_matrix_next/store/liuyeStore.ts` (扩 · W1 137 行 → W2 273 行 · 加 6 action: appendMessage / addToolCall / updateToolCall / applyArtifactPatch / attachEvidence / attachToolProgress)
  - `credit_matrix_next/app/page.tsx` (改 · 4 chip onClick console.log → 真触 startSession + setAgent + startTurn · useShallow 多字段 selector · 接 useLiuyeBridge SSE consumer)
  - `credit_matrix_next/lib/sse/useChunkedPatch.ts` (新 stub · 28 行 · W3 第 3 棒实做 chunk buffer + 30s timeout)
- **commit SHA**: `99874ce` (`99874ce W2-frontend checkpoint 4/18 · SSE bridge + page.tsx 真接 + store 扩`)
- **关键决策**:
  - **brief 'tool.error' 漂移修正**: brief §3 文件 1 列 12 case handler 含 `tool.error` · 但 v3 spec §2.1 + `generated.ts` envelope union canonical 仅 11 event · **不含 tool.error**. canonical 是 turn.error · tool 级 error 走 `tool.completed` payload.status='failed' + payload.error · 或 backend emit `turn.error` · 已在 `useLiuyeBridge.ts` 文件头注释明示 `(NOTE: brief 列 'tool.error' 是漂移 · canonical 是 turn.error · tool 级 error 走 tool.completed payload.error 或 ToolCall.error)` · 第 3 棒接力时**不可凭 brief 加 tool.error case** (tsc 会 reject: `Type '"tool.error"' is not comparable to type ...`)
  - **case 编号**: 11 named event + heartbeat keepalive + default = 11 case + 1 default · brief "12 case handler" 把 default 算入即 12 · 我的注释编号 1-11 · 与 generated.ts envelope union 一一对应
  - **8 vs 5 status 分流** (per W1 progress gotcha): tool.started → addToolCall (ToolCall.status 8 enum · 默认 'queued') · tool.progress → attachToolProgress (ProgressMessage.status 5 enum · 不动 ToolCall.status) · tool.completed → updateToolCall (final_status 走 payload.status ?? 'completed' · 支持 failed/aborted/idle_timeout/completed) · 三 case 各走独立 store action · 不共享 ToolCall.status mutation 路径
  - **chunked artifact patch W2 minimal**: `liuyeStore.applyArtifactPatch` push patch 到 artifact.patches[] + 维护 version · 非 chunked 或 chunk_assembly='final' 时 merge snapshot + 标 status='resolved' · 真 chunk_index 0..n-1 buffer + 30s ARTIFACT_PATCH_CHUNK_TIMEOUT 留 W3 `useChunkedPatch` (lib/sse/useChunkedPatch.ts 已建 stub · 占位 file path + `CHUNK_ASSEMBLY_TIMEOUT_MS = 30_000` 常量)
  - **首次见 artifact_id 兜底**: applyArtifactPatch 首次见 artifact_id 时若 store.artifacts.get() 返 undefined · 用最小骨架占位 (type='credit_decision' / owner_agent='channel' / title='' fallback) · 等 backend 后续 emit artifact full snapshot 覆盖 · 不抛错 (defensive · backend 应先 emit 完整 artifact 再 patch · 但 SSE 顺序无保证)
  - **applyArtifactPatch payload cast**: envelope.payload 是 open schema `{ [k: string]: unknown | undefined }` · 走类型化 cast `payload as { id?: string; base_version?: number; ... }` · 不强 ArtifactPatch 类型 (避免 generated.ts envelope union 与 ArtifactPatch 完整 schema 之间的 type assertion friction)
  - **attachEvidence 去重**: evidence_refs.includes(evidence_id) 检 · 重复 SSE event 不 push 重 (idempotent · per W1 backend gotcha dedup_key)
  - **updateToolCall 防半残**: 若 tool_call_id 未见过 · updateToolCall 返 `{}` 不创建 (避免 partial ToolCall 半残对象) · 必须先走 addToolCall (tool.started) 才能 update (tool.progress/completed)
  - **page.tsx useShallow**: 4 字段 selector (turn_id, persona_id, setAgent, startTurn) 走 useShallow (CLAUDE.md §4 硬线 2 · 返新对象 → Object.is 每次 false → infinite re-render loop) · 实测页面 hot-reload 无 loop · 4 chip 全渲
  - **page.tsx onChipClick try/catch**: backend 未起或 network error 时 startSession throws LiuyeApiError · console.error 兜底 (W3 加 FallbackBanner UI 真渲) · 不破 chip 点击行为
  - **page.tsx onComposerSubmit 留 W3**: composer submit 真触 sendMessage 留 W3 (依 turn_id · 若 turn_id 缺先 startSession) · 本棒 page.tsx scope 仅 chip 4 个
  - **useEffect cleanup**: useLiuyeBridge 内 useEffect 返 connectStream 的 cleanup function · turn_id 变化时 React 自动调 cleanup · sse.ts 内 cleanup 关 EventSource + clearInterval (dead check timer)
- **gotcha (第 3 棒必跟)**:
  - **brief 漂移 tool.error**: 见上 (第 3 棒不可凭 brief 加 case 'tool.error': · tsc 会 reject)
  - **W2 minimal vs W3 真做边界 (chunked patch)**: 当前 W2 minimal · liuyeStore.applyArtifactPatch 直 push patch · 不 buffer · 不 30s timeout · 第 3 棒做 useChunkedPatch 时**改 useLiuyeBridge.ts artifact.patch case** 走 useChunkedPatch.onChunk 而非直 store.applyArtifactPatch · 真 buffer 收齐才触 store · 否则 30s 后 emit ARTIFACT_PATCH_CHUNK_TIMEOUT (turn.error 走 onError callback 或 store.setPermissionRequest)
  - **PermissionRequest minimal 3 vs 完整 15**: W2 minimal 仅 `setPermissionRequest(evt.payload)` 写 store 状态 · 真渲 3 风险分级子组件 (InlineNotice low / ConfirmModal medium / DrawerWithReason high) 留第 3 棒 · 完整 15 子组件 W4
  - **Composer transition W3**: brief §3 文件 3 指明 "本棒先 skeleton wire" · transition 真做 (center → bottom 360ms · 静默 hero → 工作 hero 420ms · motion-reduce 兼容) 留第 3 棒 · 依 inProgress / turn_id 状态切 CSS class · 当前 hero-static / agent-chips / composer 三层位置不变 · transition 需改 globals.css + Composer.tsx 内部 wrapper class
  - **useLiuyeBridge.ts onSnapshotNeeded**: sse.ts seq gap ≥ 10 或 dead 30s 触发 · 当前 W2 minimal console.warn · W3 加 lib/api/liuye.ts `getTurnSnapshot(turn_id)` endpoint + dispatch · 真路径靠 backend BFF /api/liuye/turns/{turn_id}/snapshot 提供
  - **turn.error W2 minimal**: 仅 console.warn + endTurn · W3 加 FallbackBanner toast + retry button (依 retryable + retry_after_ms + human_hint 9 字段全 surface)
- **tsc --noEmit**: 0 error (双验 · 一次 console.error 修后 · 一次 case 'tool.error' 修后)
- **npm run dev**: ok · localhost:3210 HTTP 200 / 13.5 KB · DOM verified (4 chip testid + composer-submit/textarea + hero-static + 4 中文 label "客户经理助理/授信助理/报告助理/预警助理" + placeholder "说出你的诉求…") · 旧 W1 dev 进程 turbopack hot-reload pick W2 改动 · backend 未起 → onChipClick console.error (acceptable · W2-backend D7 才真跑 backend)
- **PRESERVES**: LY-007 (composer A 静默 hero) · LY-018 (Channel 信号搜索 4 字段 candidate metadata) · LY-053 (decision_ledger 跨 mode parent_turn_id) · LY-066 (5 应急流程 fallback chain)
- **NEW-DOM**: useLiuyeBridge hook 集成 (lib/sse/useLiuyeBridge.ts) · 4 chip onClick → startSession + SSE consumer (page.tsx)
- **ELAPSED-MIN**: 约 35 min (read 8 W1 文件 + brief + spec 路径 + tsc 2 次跑 + 4 文件改 + commit + progress · 不含读 root CLAUDE.md 上下文加载时间)
- **下一棒 file checklist 预计** (第 3 棒 · 30-45 min · 5-6 文件):
  - `components/permission-request/InlineNotice.tsx` (low risk · inline 行内提示 · ARIA role=alert)
  - `components/permission-request/ConfirmModal.tsx` (medium · modal + idempotency_key 防双触)
  - `components/permission-request/DrawerWithReason.tsx` (high · drawer + reason_required textarea + 中文 a11y)
  - `components/evidence-attached/EvidenceRefRow.tsx` (freshness chip 3 enum + data_tier badge 1-4)
  - `components/error/FallbackBanner.tsx` (turn.error + 5 fallback 类型 UI · TurnErrorPayload 9 字段全 surface)
  - `components/composer/Composer.tsx` (transition 真做 · center → bottom 360ms · 静默 hero → 工作 hero 420ms · motion-reduce 兼容 · 依 turn_id 状态切 CSS class)
- **blocker**: 无 (硬 blocker) · 但有 1 个 next-棒 必跟决策点: chunked patch buffer 的 fallback 路径 (chunk_total 不一致 vs gap 触 snapshot 重拉 vs 30s timeout drop · 三种走不同 store action / SSE 端 onSnapshotNeeded · 需第 3 棒做 useChunkedPatch 时统一)
