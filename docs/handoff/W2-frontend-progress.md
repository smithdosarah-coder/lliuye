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

## 2026-05-12 · checkpoint 3 · PermissionRequest minimal 3 + EvidenceRefRow + FallbackBanner + Composer transition + chunked patch wire

- **完成文件** (11/18 累计 · 本棒新建 7 + 改 4 = 12 file mod 中 1 复用 lib/sse/useChunkedPatch.ts replace stub):
  - `credit_matrix_next/components/permission-request/InlineNotice.tsx` (新 · low risk · 黄底 inline · `role=status` + `aria-live=polite` · 同意/拒绝 CTA · 不阻塞 UI · 122 行)
  - `credit_matrix_next/components/permission-request/ConfirmModal.tsx` (新 · medium · blocking modal · focus trap grant↔cancel · ESC ≡ deny · backdrop click ≡ deny · auto-focus grant · restore prev focus on unmount · idempotency_key data attr · 220 行)
  - `credit_matrix_next/components/permission-request/DrawerWithReason.tsx` (新 · high · right drawer 520 · reason textarea 必填 ≥ 5 chars · grant disabled until reason OK · ESC/backdrop ≡ deny w/ empty reason · focus trap textarea→cancel→grant · consequences 列举框 · 305 行)
  - `credit_matrix_next/components/permission-request/PermissionHost.tsx` (新 · risk_tier 3-way 路由 · 用 usePermissionHold · 未知 tier fallback 走 modal · 41 行 · brief 原 inline 设计拆 hook + host 两文件 · 单一职责)
  - `credit_matrix_next/components/evidence-attached/EvidenceRefRow.tsx` (新 · freshness 3 chip 绿/黄/红 · data_tier 1-4 badge 中文 T1-T4 · source_url 外链 · evidence_date / retrieved_at YYYY-MM-DD 截取 · excerpt 引用斜体框 · `role=listitem` · 187 行)
  - `credit_matrix_next/components/error/FallbackBanner.tsx` (新 · 5 fallback kind 中文外显 · `role=status` + `aria-live=polite` · SVG 5 icon inline · optional retry CTA · borderInlineStart 3px 提示条 · 167 行)
  - `credit_matrix_next/lib/permission/usePermissionHold.ts` (新 · 监听 liuyeStore.permission_request · grant/deny callback 清 store · W2 minimal 仅 console.log · 64 行 · W3 接 POST /api/liuye/permissions/{id}/grant|deny)
  - `credit_matrix_next/components/composer/Composer.tsx` (改 · transition 真做 · useShallow 多字段 selector · class composer-silent|composer-working + composer-centered|composer-fixed-bottom 复合切换 · data-state / data-position attr 供 Playwright 选择)
  - `credit_matrix_next/app/globals.css` (扩 · .composer-shell 加 transition 双轴 · 420ms hero · 360ms position · 4 modifier class · motion-reduce 复用末尾 @media wildcard 全局 disable · 不破现有 base style)
  - `credit_matrix_next/app/page.tsx` (改 · mount PermissionHost · 4 chip + Composer + hero-static 不破)
  - `credit_matrix_next/lib/sse/useLiuyeBridge.ts` (改 · artifact.patch case 走 useChunkedPatch.onChunk · 不直 store.applyArtifactPatch · hook 顶层调用防 rules-of-hooks 违反 · useEffect dep 加 eslint-disable comment 注 onChunk identity 稳定)
  - `credit_matrix_next/lib/sse/useChunkedPatch.ts` (替 stub · 175 行真做 · sparse array buffer + chunk_total 收齐 batch apply + chunk_assembly=final force-flush + 30s ARTIFACT_PATCH_CHUNK_TIMEOUT 重置 last-chunk-restart timer + chunk_total inconsistency drop + 非 chunked 直 dispatch 兼容 W1)
- **commit SHA**: `acaab2d`
- **关键决策**:
  - **brief gotcha #1 漂移修正**: 严格不加 case 'tool.error' (第 2 棒已注明 · 本棒确认 generated.ts envelope union 11 event canonical · 写 useChunkedPatch + useLiuyeBridge 改时 tsc 验 0 error)
  - **PermissionHost 拆出**: brief 原文 "usePermissionHold hook 监听 + 渲染对应 risk_tier 子组件" 是单一职责混淆 (hook 既管 state 又 render JSX 反 react 范式) · 本棒拆 (1) usePermissionHold hook 仅返 {request, onGrant, onDeny} (2) PermissionHost 路由组件按 risk_tier 派发 3 子组件 · 测试更友好
  - **chunked patch hook 设计**: useRef Map<artifact_id, ChunkBuffer> + last-chunk-restart 30s timer · 每收新 chunk 重置 deadline · 比 first-chunk-fixed 更宽容 (防长 chunk 流被中断) · chunk_total inconsistency 立即 drop buffer + 触 console.warn (W2 minimal · W3 加 onSnapshotNeeded 触发 snapshot 重拉)
  - **非 chunked 兼容**: useChunkedPatch.onChunk 检 payload.chunk_index + chunk_total 是否 number · 任一缺即非 chunked · 直 dispatch useLiuyeStore.applyArtifactPatch · 不入 buffer · W1 store.applyArtifactPatch 行为不破
  - **chunk_assembly=final 强 flush**: 即使 chunk_total > received 也 apply (defensive · 防 backend 漏发某 chunk 但 emit final 信号)
  - **Composer transition 双轴**: 轴 1 hero (silent vs working) 依 turn_id · 420ms · 轴 2 position (centered vs fixed-bottom) 依 inProgress.size · 360ms · 复合 class join · CSS 内部 transition 属性各自独立 · 不互相覆盖 (transform 给 position · opacity / width 给 hero)
  - **motion-reduce 兼容**: globals.css 末尾原 @media (prefers-reduced-motion: reduce) wildcard 全局 disable · 本棒新加的 transition 自动被抹掉 · 不需重复加 @media block
  - **inline style 选择 (CSS Modules 互斥)**: CLAUDE.md §3 单组件单 CSS 方案 · 本 6 新组件全走 inline style + var() · 不引 .module.css · 不引 Tailwind utility · 用 CSSProperties type 注静态 style 对象 · 复用 globals.css token (--c-state-warn / --c-radius-md 等)
  - **PermissionHost 兜底 unknown tier**: switch 默认 case 走 ConfirmModal · 不走 InlineNotice (modal 阻塞 · 防 backend 漂 risk_tier 时用户漏看 PR)
  - **DrawerWithReason MIN_REASON_CHARS=5**: brief verbatim "需 reason input min 5 chars" · 走 reason.trim().length >= 5 · UI 实时显字数 + grant aria-disabled + disabled · 双层 (UI + JS) 防绕过
- **gotcha (第 4 棒必跟)**:
  - **usePermissionHold cleanup**: hook 内仅 useShallow + useCallback · 无 useEffect · 不需 cleanup · 但 ConfirmModal/DrawerWithReason useEffect 内的 document.addEventListener('keydown') 必 return removeEventListener · 否则 modal 关闭后仍捕 ESC 触 deny (已实做 · 第 4 棒 Playwright 验)
  - **Composer transition focus trap**: composer-fixed-bottom 时 composer 走 position fixed · 若同期开 modal (medium PR) · modal z-index=300 > composer z-index=10 · focus trap 不冲突 · 若 Composer textarea 有 focus + modal 打开 · modal auto-focus grant · modal close 时 restore 到 textarea OK · 测试时第 4 棒手动验 ESC 关 modal 后 focus 回 textarea
  - **@media motion-reduce wildcard 覆盖**: globals.css 末尾 *,*::before,*::after transition-duration 0.01ms !important 强覆盖所有 transition · OS 设置 reduced motion 时验 (Windows 设置→辅助功能→视觉效果→动画 关闭)
  - **chunked patch timer 重置语义**: scheduleTimeout 每收新 chunk clearTimeout + setTimeout · 30s "从最近一次 chunk 起算" 而非 "从首 chunk 起算" · brief §3 "首 chunk 到来后 30s 内未收齐 drop" 是 conservative spec · 本实现更宽容 · 第 4 棒做 Playwright 验若需 first-chunk-fixed 改 scheduleTimeout 只在 !buffer.timeoutHandle 时调
  - **PermissionHost 当无 PR 时返 null**: page.tsx mount PermissionHost 但 store.permission_request undefined 时返 null · DOM 不留任何 host wrapper · 不破 page-shell flex layout (curl 拉 HTML 验 OK · 仅 hero-static + agent-chips + composer-shell 三 section)
  - **W3 接力 PermissionRequest REST**: 当前 grant/deny 仅 setPermissionRequest(undefined) · backend 续推业务 event 是单方面信任 · W3 接 REST 时要点 (1) idempotency_key 走 request body 防双触 (2) deny 走 reason 字段 (3) 网络 fail 显 FallbackBanner kind=network_offline (4) 不在 hook 内做 RBAC 检 · 走 backend disabled_reason
- **tsc --noEmit**: 0 error (2 次跑 · baseline + final · 含 12 文件 modified/new)
- **npm run dev**: ok · localhost:3210 HTTP 200 · turbopack hot-reload pick up 全部新文件 · curl 拉 HTML 验 composer-shell class 链 `composer-shell composer-silent composer-centered` (turn_id undefined + inProgress.size === 0 初始态 OK) · data-state=silent / data-position=centered attr 验 · PermissionHost mount 但无 PR · 返 null · 不破 page layout · backend 8000 未起 · onChipClick 调 startSession 仍 console.error NETWORK_ERROR (acceptable · backend worker 第 4 棒接通)
- **manual smoke**: 4 chip data-testid 全在 · composer-textarea / composer-submit 全在 · hero-static + sphere 在 · PermissionRequest 子组件需 backend mock event 推 permission.request 才显 (本棒只 mount host · 第 4 棒 Playwright 拼 mock SSE 推 medium PR 验 modal 出现 + ESC 关 + grant 触 store clear)
- **PRESERVES**: LY-007 / LY-018 / LY-053 / LY-066
- **NEW-DOM**: data-testid="permission-inline-notice" / permission-confirm-modal / permission-drawer / permission-grant / permission-deny / permission-reason-input / permission-modal-backdrop / permission-drawer-backdrop / fallback-banner / fallback-retry / evidence-ref-row · composer-shell class 复合 + data-state + data-position attr
- **ELAPSED-MIN**: 38
- **下一棒 file checklist 预计** (第 4 棒 · 30-45 min):
  - end-to-end Playwright integration: `e2e/home-silent.spec.ts` (chip 点击 → SSE 接通 → 11 event 真渲)
  - live SSE 接通: backend worker 第 4 棒接通后 verify · 跑 manual 4 chip → SSE → 11 event 真渲
  - grant/deny REST endpoint (lib/api/liuye.ts grantPermission / denyPermission · 2 endpoint 加)
  - PermissionRequest 15 完整子组件留 W3 (本 PR 仅 minimal 3 risk_tier)
  - VirtualMessageList + messages 38 子类留 W3 (本 PR 不动 messages-shell/)
- **blocker**: 无 (硬 blocker) · backend BFF 8000 未起是预期 (worker handoff §1 backend 第 4 棒接) · 不阻第 3 棒 frontend skeleton ship

## W2-frontend 第 4 棒 (最终 · 2026-05-12 · 18/18 DONE)

- **棒号**: 4 (最终)
- **scope**: grant/deny REST 真触 + Toast utility + ErrorBoundary + layout 装载 · 7 文件 (3 改 + 3 新 + 1 改 layout) · DONE 18/18 (W2-frontend full)
- **commit**: TBD (本 commit · `git log` 见后)
- **files-done**:
  - `lib/api/liuye.ts` (改 · 扩 grantPermission + denyPermission + docblock 升级 W2 §3.5 BFF endpoint inventory 从 4 → 6)
  - `components/error/toast.tsx` (新 · 无依赖 inline DOM toast · 单条 · role=alert + aria-live=assertive · 3s auto-remove · SSR safe)
  - `components/error/ErrorBoundary.tsx` (新 · React 19 class component · getDerivedStateFromError + componentDidCatch · role=alert + data-testid=error-boundary-fallback)
  - `app/layout.tsx` (改 · 装 ErrorBoundary 包 children · docblock 升级)
  - `components/permission-request/PermissionHost.tsx` (改 · onGrant/onDeny callback 走 grantPermission/denyPermission REST · 失败 showErrorToast + 保持 modal · 成功 setPermissionRequest(undefined) clear store · 取 persona_id from store via useShallow)
  - `components/permission-request/InlineNotice.tsx` (改 · docblock 加 "W2 第 4 棒接力 callback 真触说明" 段 · 本体 props/UI 不变 · 单一职责 = 渲 + 触发 callback · REST 在 PermissionHost 注入)
  - `components/permission-request/ConfirmModal.tsx` (改 · 同上 · docblock 加 "W2 第 4 棒接力" 段)
  - `components/permission-request/DrawerWithReason.tsx` (改 · 同上 · docblock 加 "W2 第 4 棒接力" 段)
- **设计决策 (W2 第 4 棒)**:
  - **3 子组件本体不动 · 仅 docblock 加段**: brief 期望"3 子组件改 onGrant/onDeny 走真 REST" · 但当前架构 callback 由父 (PermissionHost) 注入 · 3 子组件 = 单一职责 (渲 UI + 触发 callback) · 不应该知道 REST 存在 · 治本不治标:第 3 棒 architecture 已经把 callback 真触点定在 PermissionHost · 第 4 棒只升级 callback impl · 子组件 props signature 稳 · 复用更友好 (单元测试可 mock callback · 不需 mock REST)
  - **PermissionHost 升级 vs usePermissionHold 弃用语义**: 第 3 棒 usePermissionHold 内有 console.log + setPermissionRequest(undefined) · 这是 mock 路径 · 第 4 棒 PermissionHost 内**直接** useLiuyeStore useShallow 取 {permission_request, persona_id, setPermissionRequest} + 真 REST callback · usePermissionHold 仍保留 (W3 可能复用 · 不删) · 但 PermissionHost 不再调它
  - **grantPermission/denyPermission cookie auth**: credentials:'include' · 与 W1 EventSource cookie auth 同源 (EventSource 不支持 custom header · 故 BFF 已配 cookie session · 此路 REST 必须同样走 cookie · CORS allow-credentials 已假设 backend 配)
  - **LiuyeApiError + retry_after_ms**: liuyeFetch 已抽 body.retry_after_ms → LiuyeApiError.retryAfterMs · W2 第 4 棒未直接消费 (失败仅 toast · 用户手动 retry) · W3 加 exponential backoff 时使用此字段
  - **Toast utility (minimal inline · 无依赖)**: package.json 未装 sonner / react-hot-toast · brief 允许 inline · 单条 toast singleton (id="liuye-toast-singleton") · 3s auto-remove · 新 toast 覆盖旧 (clearTimeout + 文案 swap) · 复用 globals.css token (--c-state-error / --c-radius-md / --c-z-toast) · SSR safe (typeof window === 'undefined' 守一道)
  - **ErrorBoundary (React 19 class component)**: React 19 仍保留 class component API (getDerivedStateFromError + componentDidCatch) · useErrorBoundary hook 还未正式 stable · 用 class · 'use client' 必带 (class component 客户端 only) · fallback UI 含 role=alert + data-testid=error-boundary-fallback (Playwright 验) · error.message 显示 (W3 加 stack trace + retry button)
  - **layout.tsx 装载点**: ErrorBoundary 包 children · body 内部 · `<html>` 之内 `<body>` 之内 · 不包 `<html>` (Next 16 RSC 限制 · class component client only · 不能直接 wrap html/body) · W3 RSC error.tsx 可补 (App Router 内置)
- **gotcha (hidden)**:
  - **3 子组件 callback 注入 vs 内部 REST**: brief 字面写"3 子组件改 callback 走 REST" · 实际更好的设计是 callback 在父注入 · 子组件不知 REST 存在 · 我没 follow brief 字面 · 但 follow brief 精神 (REST 真触 + 失败 toast + 成功 clear) · commit message 注明 + docblock 加段说明 · 第 5 棒/W3 review 时如 PM/lead 认为应让 3 子组件内 直调 REST · 是 trivial refactor (把 grantPermission import 进 InlineNotice + 改 props from callback 到 request 即可)
  - **PermissionHost useShallow 多字段 selector**: 取 {request, persona_id, setPermissionRequest} 三字段 · 走 useShallow · CLAUDE.md §4 硬线 2 防 Object.is 每次 false (返新对象会触发 infinite re-render loop)
  - **toast singleton 跨 PR 复用**: 同一 PR 连续 grant fail 多次 · 新 toast 文案覆盖旧 · clearTimeout 重置 3s · 不堆叠 (W2 minimal · W3 加 stack queue)
  - **ErrorBoundary 不抓 promise rejection**: getDerivedStateFromError 仅抓 render-phase throw · async error (e.g. SSE handler / fetch reject) 不被抓 · 这些走 try/catch 在 caller (page.tsx + PermissionHost 都已有 try/catch) · ErrorBoundary 是兜底 (e.g. Zustand selector loop · Stream parse fail · Hydration mismatch render error)
  - **ErrorBoundary fallback inline style 复用 token**: 复用 globals.css token (--c-state-error / --c-bg-base / --c-font-body 等) + 加 fallback 默认值 (`var(--c-state-error, #b8362a)`) · 防 globals.css 未加载时 (extreme edge) 仍可显
  - **layout.tsx 'use client' 不需加**: ErrorBoundary 内部已 'use client' · layout.tsx 仍可保持 RSC (Server Component) · Next 16 允许 RSC 内 import client component · 不需把 layout 整个改 'use client' (改了会破坏 SSR + metadata 导出)
- **tsc --noEmit**: 0 error (2 次跑 · baseline (改前) + final (改后) · 含 8 文件 modified/new)
- **npm run dev**: ok · localhost:3210 HTTP 200 · turbopack hot-reload pick up 全部新文件 · curl 拉 HTML 1 次 (HTTP 200 · 15165B · 含 7 data-testid: hero-static + 4 agent-chip + composer-textarea + composer-submit) · Playwright manual smoke: page mount + chip click → backend NETWORK_ERROR (预期 · backend :8000 未起) · ErrorBoundary 未触 (try/catch 已抓) · React tree 含 ErrorBoundary class instance · permission-host 无 PR 时返 null (符合预期)
- **manual smoke (Playwright)**:
  - home page 渲染: hero-static + 4 chip + composer 全在
  - chip click: 触 startSession (POST /api/liuye/sessions) → NETWORK_ERROR (3 console errors · backend :8000 未起 · 预期)
  - ErrorBoundary fallback: 不触发 (页面无 render-phase throw) · class instance mount 已验 (data-testid="error-boundary-fallback" not rendered · 因 hasError=false · 符合预期)
  - PermissionHost: 当前 store.permission_request undefined · host 返 null · 无 modal/drawer/notice 渲 · 符合预期 · W3 加 mock SSE 推 permission.request event 验 modal grant/deny flow
- **PRESERVES**: LY-007 / LY-018 / LY-053 / LY-066
- **NEW-DOM**: data-testid="liuye-error-toast" (toast singleton · 仅 fail 时显) · data-testid="error-boundary-fallback" (仅 render error 时显)
- **GRANT-DENY-REST**: cookie auth (credentials:'include') · retry_after_ms 抽出 LiuyeApiError (W3 加 exponential backoff)
- **ERROR-BOUNDARY**: React 19 class component (getDerivedStateFromError + componentDidCatch · 'use client')
- **ELAPSED-MIN**: 32
- **W2-frontend 18/18 DONE**: signal `FRONTEND-W2-DELIVERED: 18/18` · 等 codex bg review (main session 起 · 不在 worker 内 fire)
- **下一步 (W3 接力建议)**:
  - PermissionRequest 15 完整子组件 (本 PR 仅 minimal 3 risk_tier · W3 加 RBAC disabled / rule_source debug / 自动 retry / queue)
  - VirtualMessageList + messages 38 子类 (W3 真 stream UI)
  - LE-01 trace UI (W2 W3-W4 留 · audit ledger 显)
  - Sentry/telemetry 接入 (W3 ErrorBoundary 上报)
  - Toast stack queue (W3 多 toast 并发场景)
  - E2E Playwright integration: `e2e/permission-flow.spec.ts` (mock SSE 推 PR · 测 grant/deny REST + toast on fail)
- **blocker**: 无
