# W2 Frontend Worker · Onboarding Brief

> **worker 代号**: `claude-W2-frontend`
> **任务**: W2 Phase 1 端到端 demo path · `lib/api/sse.ts` connectStream live + 11 event UI 真渲 + Composer transition + page.tsx 接 store + SSE consumer + PermissionRequest minimal 3 子组件 + 5 应急 frontend UI + Playwright live SSE (18 文件改 + 新)
> **依据**: `_temp/w2-plan.md` §3.2 + v3 spec §4 (CC 15 pattern) + §6.3 (demo path) + §10 (视觉硬线) + 附录 C (5 fallback UI) + 附录 D (5 layout token)
> **估时**: ~12-14 工时 (W2 D6 ~ D10 · 16-20 sub-agent 棒 30-45 min/棒)
> **版本**: v1.0 (W2 brief writer 写 · 2026-05-12)

---

## 1. 身份 + 起手

**你是**: W2 frontend worker · 3 worker 并行第二棒 · 你把 W1 frontend skeleton 升级为 11 event 真渲 + live SSE 接通.

**依赖**:
- W1 frontend 24/24 DONE (Next 16 app + ground truth 首页 + 5 组件域 skeleton + 2 store + API + codegen 协议 · `aa1e1ab` + `39e597b`)
- W1 contract 14/14 DONE (`lib/protocols/generated.ts` 9 export interface/type 已在新仓 · schema_hash `d79ddfdcf6d3b381...`)
- W2 backend 同 W2 并行 (你消费 live SSE 11 event 真流 · 走 BFF :8000 `/api/liuye/sessions/{turn_id}/stream`)
- W2 mock-test 同 W2 并行 (Playwright spec 跑你的真渲组件 · 3 mock SSE :8001/:8002/:8003 起停由 mock-test 控)

**第一件事 (开工前必做)**:
1. 读 `D:\claude code\_temp\w2-plan.md` (W2 plan 全 · 8 章 + 12 必修 + D6-D10)
2. 读 `D:\claude code\credit_report_agent_work\docs\onboarding\W1-frontend-worker.md` (W1 brief 模板源)
3. 读 `D:\claude code\credit_report_agent_work\docs\handoff\W1-frontend-progress.md` (W1 frontend 4 棒累积 hidden gotcha · 重点第 3 棒 + 第 4 棒)
4. 读 `D:\claude code\_temp\liuye-final-spec-v3.md` §4 (CC 15 pattern) + §6.3 (demo path) + §10 (视觉硬线) + 附录 C (5 fallback UI) + 附录 D (5 layout token) + §2.1 (11 event)
5. 读 `D:\claude code\credit_matrix_next\CLAUDE.md` (前端 scoped · §3 CSS Modules / §4 Selector / §5 Stream store / §8 IME / §9 a11y)
6. 读 老仓 root `CLAUDE.md` "前端反复踩过的具体坑" + §7 (前端设计系统 platform shell v2 · 注意区别老仓 vs 新仓)
7. **读 `docs/onboarding/W1-worker-handoff-protocol.md` §2 + §5** · W2 沿用 · 你不是 12-14h 单 session · 是接力赛 · 每 30 min 必 checkpoint + 写 `docs/handoff/W2-frontend-progress.md`
8. 写 "我理解 W2 frontend scope" 一段 (≤ 200 字) 给 main session verify · 没漂再开干

## 2. 输入文件清单

| 文件 | 用途 | 必读章节 |
|---|---|---|
| `_temp/w2-plan.md` | W2 plan SSOT | §3.2 W2-frontend worker scope + §5 risk + §6 DoD |
| `docs/onboarding/W1-frontend-worker.md` | W1 brief 模板源 | 全 (你的 brief 是它的 W2 延伸) |
| `docs/handoff/W1-frontend-progress.md` | W1 frontend 4 棒累积 gotcha | 第 3 棒 (5 组件域) + 第 4 棒 (2 store + 2 API · SHA `39e597b`) |
| `_temp/liuye-final-spec-v3.md` | v3 spec | §4 (CC 15 pattern · line 385-456) + §6.3 (demo path 70s) + §10 (视觉) + 附录 C (5 fallback) + 附录 D (5 layout token) + §2.1 (11 event) |
| `credit_matrix_next/CLAUDE.md` | 前端 scoped | §3 CSS Modules + §4 Selector + §5 Stream store + §8 IME + §9 a11y |
| `docs/contracts/liuye-architecture.md` | Tier 1 SSOT | 全 |
| `docs/contracts/liuye-sse-event-matrix.md` v1.1 | 11 event × 6 Agent matrix | §3 Q1/Q2/Q3 + §4 mapping table |
| 老仓 root `CLAUDE.md` | 全局工程纪律 | "前端反复踩过的具体坑" + §7 (注意区别新老前端) |
| `shared/contracts/liuye/schemas/*.json` | 5 协议 (codegen 源) | 全 5 文件 |
| `credit_matrix_next/lib/protocols/generated.ts` | codegen 9 export | W1 contract 已 ship · 不动 |
| 视觉锚 `localhost:8765/` | ground truth 首页 (v3 §10) | 已锁 W1 · W2 加 work hero 96×96 + composer transition |

## 3. W2 file checklist (18 文件 · 改 10 + 新 8)

### 3.1 改 10 W1 文件 (live 真渲实做)

```
credit_matrix_next/app/page.tsx                                  (静默 → dynamic · 接 liuyeStore + SSE consumer)
credit_matrix_next/app/globals.css                               (加 composer transition + work hero 96×96 token + 5 fallback chip token)
credit_matrix_next/components/composer/Composer.tsx              (onSubmit → store action · transition center → bottom)
credit_matrix_next/components/messages-shell/MessageList.tsx     (真消费 messages array · streaming state)
credit_matrix_next/components/messages-shell/MessageRow.tsx      (4 role 完整 · message.delta 实时拼接)
credit_matrix_next/components/toolcall-card/ToolCallCard.tsx     (8 status 完整 mapping · queued → connecting → running → streaming → completed/failed/aborted)
credit_matrix_next/components/toolcall-card/ProgressBar.tsx      (stage_label live · percent 实时更新)
credit_matrix_next/components/artifact-card/ArtifactCard.tsx     (chunked apply · chunk_index 0..n-1 buffer + final apply)
credit_matrix_next/lib/api/sse.ts                                (live consumer · 真触发 connectStream + onEvent dispatch)
credit_matrix_next/store/liuyeStore.ts                           (扩 11 event handler action · upsertArtifact / appendMessage / setPermissionRequest)
```

### 3.2 新 8 文件 (PermissionRequest minimal 3 + EvidenceRef + FallbackBanner + 2 SSE hook)

```
credit_matrix_next/components/permission-request/InlineNotice.tsx     (low risk · F-001 logout / LE-04a 下载)
credit_matrix_next/components/permission-request/ConfirmModal.tsx     (medium · A3-NEW Decision submit / F-053 上链 / F-052-export 导出)
credit_matrix_next/components/permission-request/DrawerWithReason.tsx (high · LE-05 签字 / LE-04b 生成 ZIP · reason_required)
credit_matrix_next/components/evidence-attached/EvidenceRefRow.tsx    (freshness 3 enum chip + data_tier 1-4 badge · root §3.5.1)
credit_matrix_next/components/error/FallbackBanner.tsx                (5 fallback UI · Tavily mock / LLM fallback / ledger silent / SSE fail / offline)
credit_matrix_next/lib/sse/useLiuyeBridge.ts                          (SSE event → store dispatch routing hook · per W1 gotcha)
credit_matrix_next/lib/sse/useChunkedPatch.ts                         (chunk_index 0..n-1 buffer + final apply hook)
credit_matrix_next/lib/sse/usePermissionHold.ts                       (permission.request 收到后 hold business event 渲染 · grant/deny callback)
```

## 4. 关键纪律

### 4.1 11 event 真渲完整 mapping (v3 §2.1 + matrix §4)

每 event 渲染策略 (W2 必全实做):

| event | 渲染目标 | store action | 关键点 |
|---|---|---|---|
| `turn.started` | loading state · 静默 hero → 工作 hero transition | `liuyeStore.startTurn(turn_id, trace_id)` | composer center → bottom 360ms |
| `message.created` | MessageList push · MessageRow append | `liuyeStore.appendMessage(message)` | 4 role 中文 label + 颜色 token |
| `tool.started` | ToolCallCard mount · 显 8 status `queued/connecting` | `liuyeStore.addToolCall(tool_call)` + `streamStore.addInProgress(tool_call_id)` | ToolCall.status 8 enum |
| `tool.progress` | ProgressBar percent + stage_label 中文外显 | `streamStore.updateProgress(tool_call_id, progress_message)` | ProgressMessage.status 5 enum (与 ToolCall 8 enum 不重叠 · per W1 contract 第 3 棒 gotcha #3) · percent 0-100 int |
| `tool.completed` | ToolCallCard status=completed · 收尾 artifact | `liuyeStore.updateToolCall(tool_call_id, status='completed')` + `streamStore.removeInProgress(tool_call_id)` | 触发 artifact 出现 |
| `tool.error` | ToolCallCard error + retry option | `liuyeStore.updateToolCall(tool_call_id, status='failed', error)` | TurnErrorPayload 9 字段都 surface |
| `artifact.patch` | ArtifactCard upsertArtifact + chunked apply | `liuyeStore.applyArtifactPatch(patch)` (W2 加 chunked buffer 逻辑) | chunk_index 0..n-1 全到才 apply final · 走 `useChunkedPatch` hook |
| `evidence.attached` | ArtifactCard 显示 EvidenceRef 列 | `liuyeStore.attachEvidence(artifact_id, evidence)` | freshness 3 enum chip + data_tier 1-4 badge |
| `permission.request` | 3 风险分级 inline (low) / modal (medium) / drawer (high) | `liuyeStore.setPermissionRequest(req)` + `usePermissionHold` hook | risk_tier 决定 UI 形态 · reason_required (high) 必输入 |
| `turn.completed` | loading dismiss + final snapshot + cleanup | `liuyeStore.endTurn(turn_id)` (W1 已实做) | 清 inProgress Set · clear active turn_id |
| `turn.error` | error toast + retry option | `liuyeStore.endTurn(turn_id, error)` | TurnErrorPayload 9 字段 |
| `heartbeat` | 不渲染 (静默 keepalive) | 仅 `lib/api/sse.ts` 更新 `lastEventTs` (W1 已实做) | dead 30s detection trigger |

### 4.2 chunked patch apply 真路径 (v3 §2.2 + 必修 #14)

W1 frontend ArtifactCard 是 skeleton · W2 加 chunked buffer:

```tsx
// useChunkedPatch.ts
const useChunkedPatch = (artifactId: string) => {
  const buffer = useRef<Map<number, ArtifactPatch>>(new Map());
  const expectedTotal = useRef<number | null>(null);

  return useCallback((patch: ArtifactPatch) => {
    if (patch.chunk_index === undefined) {
      // 非分片 patch · 直接 apply
      liuyeStore.applyArtifactPatch(patch);
      return;
    }
    buffer.current.set(patch.chunk_index, patch);
    if (expectedTotal.current === null) expectedTotal.current = patch.chunk_total ?? null;
    // chunk_index 0..n-1 全到才 apply final
    if (buffer.current.size === expectedTotal.current && patch.chunk_assembly === 'final') {
      const merged = mergeChunkedPatches(buffer.current);
      liuyeStore.applyArtifactPatch(merged);
      buffer.current.clear();
      expectedTotal.current = null;
    }
  }, [artifactId]);
};
```

**硬规** (per W1 mock-test 第 4 棒 gotcha #1):
- chunk_index 存在 → chunk_total + chunk_assembly 必同存 (cross-field validation)
- chunk_index < chunk_total
- chunk_assembly 序列 streaming → streaming → final (per W1 mock-test report fixture 实做)
- 不全到的 chunked patch 不渲染 (避免 UI 闪烁)

### 4.3 Composer transition (v3 §10 + 附录 D.5 + 必修 #2)

W1 实做静默 hero 360×280 + composer 840×72 center · W2 加 transition:

**static 状态** (静默页):
- composer center fixed (top: 50% · transform translateY)
- 静默 hero 360×280 圆形 sphere · 浅蓝 radial-gradient
- 4 Agent chip 在 composer 下方

**dynamic 状态** (turn.started 后):
- composer bottom fixed (bottom: 24px · 360ms transition)
- 工作 hero 96×96 圆形 sphere · 同位置 · transition 420ms (per v3 §10)
- MessageList 在 composer 上方占主区
- 4 Agent chip 隐藏 (transition fade 300ms)

**实做**:
- `app/page.tsx` 用 `useLiuyeStore(s => s.turn_id !== null ? 'dynamic' : 'static')` 取状态
- CSS class `body[data-state="static"]` vs `body[data-state="dynamic"]` · 用 CSS `@property` + transition
- 兼容 `prefers-reduced-motion: reduce` · transition 改 0ms (per a11y)

### 4.4 PermissionRequest minimal 3 子组件 (v3 §2.5 + matrix §3 Q2)

W2 minimal 3 风险分级 placeholder (W3-W4 扩 15 子组件):

| 风险 | 组件 | UI 形态 | 关键字段 |
|---|---|---|---|
| low | `InlineNotice.tsx` | composer 内嵌 inline notice (1 行 · 黄色 highlight) · 用户点 "知道" 即 grant | action / explanation |
| medium | `ConfirmModal.tsx` | blocking modal (380×220) · 2 button "取消" / "确认" · idempotency_key 防重 | action / consequences / idempotency_key / required_persona |
| high | `DrawerWithReason.tsx` | side drawer (420×520) · reason textarea (必填 · reason_required=true) · 2 button | 同 medium + reason 必输 + reason_min_length 验 |

**`usePermissionHold` hook**:
```tsx
const usePermissionHold = () => {
  const permissionRequest = useLiuyeStore(s => s.permissionRequest);
  const grant = useCallback((idempotencyKey: string, reason?: string) => {
    return fetch(`/api/liuye/permissions/${permissionRequest.id}/grant`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({idempotency_key: idempotencyKey, reason}),
    });
  }, [permissionRequest]);
  const deny = useCallback((idempotencyKey: string, reason: string) => {
    return fetch(`/api/liuye/permissions/${permissionRequest.id}/deny`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({idempotency_key: idempotencyKey, reason}),
    });
  }, [permissionRequest]);
  return {permissionRequest, grant, deny};
};
```

### 4.5 5 应急流程 frontend UI (附录 C.2)

W2 实做 `FallbackBanner.tsx` (5 fallback 中文外显):

| 触发 | UI 文案 | 类型 |
|---|---|---|
| Tavily quota mock | 「Demo 模式 · 数据来自预录候选」 | chip 灰 badge |
| LLM provider fallback | 「LLM 暂时不可用 · 已切换备用模型」 | banner 顶部 5s 自动消失 |
| ledger silent-fail | 「已提交 · 上链中」 | confirm modal 乐观更新 |
| SSE conversion failed | 「事件流转换失败 · 已切换完整快照模式」 | banner 顶部 + 触发 snapshot 重拉 |
| network offline | 「网络中断 · 显示最近快照 · 重连中」 | banner 顶部 + cached snapshot 提示 |

### 4.6 SSE consumer live 接通 (lib/api/sse.ts · 必修 #12)

W1 frontend 第 4 棒 `lib/api/sse.ts` 实做了 connectStream signature · W2 真接 BFF + 真触发:

**关键加固**:
- 真 `EventSource(`/api/liuye/sessions/${turnId}/stream`, {withCredentials: true})` 连 BFF :8000
- Last-Event-ID 自动 carry (浏览器内置 · 不手动 set header · per W1 第 4 棒 gotcha #2)
- seq gap ≥ 10 触发 `onSnapshotNeeded('seq_gap')` → 调 `GET /api/liuye/sessions/{turn_id}/snapshot` 重拉全 state · W2 minimal 实做 (W3-W4 完整 snapshot store)
- dead 30s detection 真触: 内部 setInterval 5s 查 `Date.now() - lastEventTs > 30000` → onSnapshotNeeded('dead_threshold') + close + reconnect
- heartbeat seq 不递增 (per W2 plan §5.2 decision · 与 backend 对齐)

### 4.7 useLiuyeBridge hook (SSE → store routing)

新加 `lib/sse/useLiuyeBridge.ts` (per W1 第 4 棒 gotcha):

```tsx
const useLiuyeBridge = (turnId: string | null) => {
  useEffect(() => {
    if (!turnId) return;
    const handle = connectStream(turnId, {
      onEvent: (evt: LiuyeChatEvent) => {
        switch (evt.event) {
          case 'turn.started': liuyeStore.startTurn(evt.turn_id, evt.trace_id); break;
          case 'message.created': liuyeStore.appendMessage(evt.payload); break;
          case 'tool.started': liuyeStore.addToolCall(evt.payload); streamStore.addInProgress(evt.tool_call_id!); break;
          case 'tool.progress': streamStore.updateProgress(evt.tool_call_id!, evt.payload); break;
          case 'tool.completed': liuyeStore.updateToolCall(evt.tool_call_id!, {status: 'completed'}); streamStore.removeInProgress(evt.tool_call_id!); break;
          case 'tool.error': liuyeStore.updateToolCall(evt.tool_call_id!, {status: 'failed', error: evt.payload}); break;
          case 'artifact.patch': chunkedPatchApply(evt.artifact_id!, evt.payload); break;
          case 'evidence.attached': liuyeStore.attachEvidence(evt.artifact_id!, evt.payload); break;
          case 'permission.request': liuyeStore.setPermissionRequest(evt.payload); break;
          case 'turn.completed': liuyeStore.endTurn(evt.turn_id); break;
          case 'turn.error': liuyeStore.endTurn(evt.turn_id, evt.payload); break;
          case 'heartbeat': /* nothing · sse.ts 内部已更 lastEventTs */ break;
        }
      },
      onSnapshotNeeded: (reason) => { /* W3-W4 fetch snapshot */ console.warn('snapshot needed', reason); },
      onError: (err) => { liuyeStore.setError(err); },
    });
    return () => handle.close();
  }, [turnId]);
};
```

### 4.8 selector 纪律 (CLAUDE.md §4 + 必修 #19)

W1 frontend 第 4 棒 lib/empty.ts 已建 · W2 沿用:
- 任何 `useLiuyeStore(s => s.xs ?? [])` → 改 `useLiuyeStore(s => s.xs ?? EMPTY_ARRAY)`
- 多字段 selector 用 `useShallow` (zustand v5 内置)
- streamStore 多字段 selector 同
- inProgress 双重维护 (liuyeStore UI 感知 + streamStore 高频内部) · 不互写 (per W1 第 4 棒 gotcha)

### 4.9 视觉硬线沿用 W1 (v3 §10 + 附录 D)

W2 不动 ground truth (浅蓝渐变 + floating layer + 大圆角 + 黑色 send + 4 Agent chip) · 仅加:
- composer center → bottom transition (360ms)
- 静默 hero → 工作 hero transition (96×96 · 420ms)
- FallbackBanner 顶部 banner (44h · WCAG AA 4.5:1)
- 3 PermissionRequest UI form factor (modal 380×220 / drawer 420×520 / inline 1 行)

**禁** (任一 = reject · W1 已锁):
- masthead 横条
- table grid 6 column
- 米色 / 奶油色
- AI 味重紫蓝渐变
- 复活老仓 Letterpress / crimson / ink-brush-hr
- 添加新主题 / dark mode (Phase 1 lockdown)

## 5. 输出 DoD (Definition of Done)

- ✓ 18 文件全 Write/Edit 完成 · path 与 §3 1:1 一致
- ✓ `cd credit_matrix_next && npm run dev` 跑通 (localhost:3210)
- ✓ `npx tsc --noEmit` 0 error
- ✓ 11 event UI 真渲 (`useLiuyeBridge` hook + 11 event + heartbeat keepalive · 共 12 case handler · perfect-check fix #3 术语清理)
- ✓ chunked patch apply 真路径 (chunk_index 0..n-1 buffer + final apply · `useChunkedPatch` hook)
- ✓ Composer transition 实做 (center → bottom 360ms · 静默 hero → 工作 hero 420ms · `motion-reduce` 兼容)
- ✓ page.tsx 接 store + SSE consumer (4 Agent chip onClick 真触 startSession + connectStream)
- ✓ PermissionRequest minimal 3 子组件 (InlineNotice low / ConfirmModal medium / DrawerWithReason high · usePermissionHold hook)
- ✓ EvidenceRefRow 显 freshness 3 enum chip + data_tier 1-4 badge
- ✓ FallbackBanner 5 fallback UI 中文外显
- ✓ Playwright live SSE 跑通 (W2 mock-test 写 `demo-path-step4-9.spec.ts` · 你的组件被它跑)
- ✓ selector 纪律 0 inline `?? []` (npm run typecheck 跑过)
- ✓ commit trailer 含 `FRONTEND-W2-DELIVERED: 18/18` + `ELEVEN-EVENT-UI: ok` + `COMPOSER-TRANSITION: 360ms+420ms` + `PERMISSION-MINIMAL: 3/3` + `FALLBACK-BANNER: 5/5` + `PRESERVES: LY-007, LY-018` + `NEW-DOM: data-testid="permission-modal" ...`
- ✓ codex independent review 通过 (root §3.7.4 protocol v2)

## 6. W2 末 sign-off 流程

1. **PR 创建**: `credit_matrix_next` 仓 `feat/liuye-W2-frontend` 分支 → PR to `main` (新仓) · title `[W2-frontend] 11 event UI 真渲 + Composer transition + PermissionRequest minimal 3 + 5 fallback UI + live SSE`
2. **codex review** (root §3.7.4):
   ```
   codex exec -c 'model_reasoning_effort="medium"' \
     --search \
     "Review W2 frontend worker PR for credit_matrix_next. Check 1) 11 event UI 真渲 (useLiuyeBridge hook routing + 11 event + heartbeat 共 12 case handler) 2) chunked patch apply chunk_index 0..n-1 buffer + final 3) Composer transition center → bottom 360ms + 静默 hero → 工作 hero 420ms + motion-reduce 4) PermissionRequest minimal 3 子组件 (inline/modal/drawer · idempotency_key) 5) EvidenceRefRow freshness 3 enum + data_tier 1-4 6) selector 纪律 0 inline ?? [] 7) live SSE Last-Event-ID + seq gap 10 snapshot + dead 30s. Verdict: GO / NO-GO."
   ```
3. **commit trailer** (老仓 root §13.5 类比):
   ```
   FRONTEND-W2-DELIVERED: 18/18
   ELEVEN-EVENT-UI: ok
   COMPOSER-TRANSITION: 360ms+420ms
   PERMISSION-MINIMAL: 3/3
   FALLBACK-BANNER: 5/5
   PRESERVES: LY-007, LY-018, LY-053, LY-066
   NEW-DOM: data-testid="permission-modal" data-testid="permission-drawer" data-testid="fallback-banner" data-testid="evidence-ref-row"
   SMOKE-PASS: demo-path-step4-9.spec.ts (by mock-test worker)
   REVIEW-MODE: codex
   REASONING-EFFORT: medium
   ELAPSED: <min>
   ```
4. **PM ack**: PM 视觉 verify (composer transition · PermissionRequest 3 子组件 · FallbackBanner 中文文案) + codex verdict · ack 后 W3 才能开工

## 7. 估时 + 风险点 (file-level)

| 文件 | 估时 | 风险点 |
|---|---|---|
| `app/page.tsx` 接 store + SSE | 1.5h | static → dynamic 切换 · 4 chip onClick 真触 startSession · turn_id 生命周期管理 |
| `app/globals.css` 加 transition + token | 1h | composer center → bottom 真 transition · `prefers-reduced-motion` 兼容 |
| `components/composer/Composer.tsx` 改 | 1h | onSubmit 真接 liuyeStore action · transition state 同步 page.tsx · IME guard 沿用 |
| `messages-shell/*` + `toolcall-card/*` + `artifact-card/*` 真渲 | 3h | 11 event 真渲 · message.delta 拼接 · ToolCall 8 status vs ProgressMessage 5 status 不混 · ArtifactCard chunked apply |
| `lib/api/sse.ts` live consumer | 1h | EventSource 真连 BFF :8000 · cookie 鉴权 · Last-Event-ID carry verify |
| `store/liuyeStore.ts` 扩 11 event action | 1.5h | upsertArtifact + applyArtifactPatch + attachEvidence + setPermissionRequest action · immutable 更新 |
| 3 PermissionRequest 子组件 | 1.5h | risk_tier 3 form factor · idempotency_key 防重 · reason_required (high) 必输 · focus trap (modal/drawer) |
| `EvidenceRefRow` + `FallbackBanner` | 1h | freshness chip 颜色 token (fresh 绿 / critical 黄 / expired 灰) · data_tier badge · 5 fallback 中文 |
| `useLiuyeBridge` + `useChunkedPatch` + `usePermissionHold` 3 hook | 1.5h | 12 event handle switch · chunked buffer Map + final apply · permission grant/deny fetch + idempotency_key |
| Playwright spec (mock-test 写 · 你的组件被它跑) | 0.5h | 你的组件 data-testid 暴露完整 · mock-test 才能 selector 抓 |

**风险 mitigation**:
- D6 第一件事: `cd credit_matrix_next && npm run dev` 起 :3210 · curl `/` 200 verify · 确认 W1 baseline 稳
- live SSE 真连 BFF: 先用 W1 mock SSE :8001 起 + DEMO_MODE=0 + BFF live mode → 跑通 11 event UI → 再切真 backend (per W2-backend D6 plan)
- composer transition 真测: prefers-reduced-motion media query 必兼容 · D7 PM 视觉 verify (浅蓝渐变 + work hero 96×96 + 360ms 真感觉)
- chunked patch: 先写 unit test `useChunkedPatch` (jest or vitest) · 跑通边界 (chunk_total=1 单 chunk · chunk_total=3 真分片) · 再上 Playwright e2e

## 8. 不准做 / 别越界

- ❌ 不准复活老仓 archive/ 任何 import / token (Letterpress / crimson / canvas / matcha / dusk / ink)
- ❌ 不准用 Pages Router · React 18 · Zustand persist (主 store)
- ❌ 不准 inline `?? []` (selector 纪律 · 用 EMPTY_ARRAY/MAP/SET sentinel)
- ❌ 不准混用 Tailwind + CSS Modules 控同 property
- ❌ 不准跳 IME guard hook (用 `e.key === 'Enter'` 不查 composition · 必用 `useImeGuard`)
- ❌ 不准把 SSE 直接 dispatch 到 Zustand store (用 streamStore + useSyncExternalStore + useLiuyeBridge routing)
- ❌ 不准添加新主题 / dark mode (Phase 1 lockdown · 只 light + projection)
- ❌ 不准做完整 messages 38 子类 / VirtualMessageList + 30 cap / 完整 PermissionRequest 15 子组件 / 3 compact (这是 W3-W4)
- ❌ 不准动 5 schema (W1 contract 已 lock · schema_hash `d79ddfdcf6d3b381...`)
- ❌ 不准跳 codex review (root §3.7.4)
- ❌ 不准动 `lib/protocols/generated.ts` (W1 contract codegen 输出 · 走 sync-contracts.ts 重跑)

## 9. 引用 SSOT

| Tier | 文件 |
|---|---|
| 1 | `docs/contracts/liuye-architecture.md` |
| 1 | `_temp/liuye-final-spec-v3.md` (§4 + §6.3 + §10 + 附录 C + 附录 D + §2.1) |
| 1 | `docs/contracts/liuye-sse-event-matrix.md` v1.1 |
| 2 | 老仓 root `CLAUDE.md` (前端踩坑 + §7 注意区别新老) |
| 3 | `credit_matrix_next/CLAUDE.md` (前端 scoped) |
| 4 | W1-frontend-worker brief (模板源) |
| 4 | **本文件** (W2-frontend brief) |
| 5 | `docs/handoff/W1-frontend-progress.md` (W1 4 棒累积 hidden gotcha · 重点第 3-4 棒) |
| 5 | `_temp/w2-plan.md` §3.2 (W2-frontend scope SSOT) |
| 上游 input | W1 contract 14/14 DONE · W1 frontend 24/24 DONE (`39e597b`) · W2 backend 同 W2 并行 (live SSE 源) · W2 mock-test 同 W2 并行 (Playwright spec 跑你的组件) |
