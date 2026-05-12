# W1-frontend Progress (append-only)

> 接力 sub-agent 必读 · main session 监控源 · sub-agent checkpoint 每次 append 一段

<!-- 第一棒 sub-agent 在此 append 第一段 -->

## 2026-05-12 04:42 · checkpoint 2 · infra 4 文件 + 静默 hero 骨架

- **完成文件** (4/24):
  - `credit_matrix_next/next.config.ts` (Next 16 + turbopack + reactStrictMode + typedRoutes)
  - `credit_matrix_next/app/layout.tsx` (字体栈 6 字体 + theme provider 占位 + lang zh-CN + suppressHydrationWarning)
  - `credit_matrix_next/app/page.tsx` (静默 hero 360×280 占位球 + 4 Agent chip + composer 840×72 + send 42 + data-testid 全暴露)
  - `credit_matrix_next/app/globals.css` (token v3 §10 + 附录 D verbatim · light + projection 双 set · WCAG AA 4.5:1)
- **关键决策**:
  - **typedRoutes**: Next 16.2.6 启动时警告 `experimental.typedRoutes` 已 promote 顶层 · 移出 experimental 块直放 `nextConfig.typedRoutes = true` · brief 模板写 experimental.typedRoutes 已过时
  - **tsconfig.json revert**: Next dev 启动自动改了 jsx (preserve→react-jsx) + 加 plugins next + 加 .next/dev/types include · 这是 W1-contract 已 commit 文件 · brief 硬线"不动 W1-contract 已 commit 文件" · 我 `git checkout --` 还原 · tsc 在原 jsx:preserve 下仍 0 error (下次跑 dev Next 会再改一次 · 留主 session 决策是否在 W1-contract 棒改 tsconfig 还是接受 Next 自动行为)
  - **dev port 3210**: localhost:3000 被旧 next-server 进程占且 EADDRINUSE · 我换 port 3210 验启动 (`npx next dev --port 3210`) · 不影响产物
  - **curl 走 proxy 假 502**: 测试时 curl 默认走 http_proxy 127.0.0.1:7897 · 第一次拿 502 · 加 `--noproxy '*'` 后 HTTP 200 / 13.3 KB · 后续 sub-agent 验 dev 用 `curl --noproxy '*'`
  - **字体加载**: next/font/google 装载 Funnel_Display + Instrument_Sans + Instrument_Serif + Noto_Sans_SC + Noto_Serif_SC + JetBrains_Mono · 全部 display: swap · CSS variable 注入 (--font-display / --font-body / --font-italic / --font-zh / --font-zh-serif / --font-mono) · 中文字体 Noto_Sans_SC 需要 subsets:['latin'] 否则 next-font 报错 (Noto SC 用 latin subset 触发字体文件下载 · 实际中文字符走 fallback 'PingFang SC' / 'Microsoft YaHei')
  - **静默 hero sphere**: Phase 1 静态 CSS radial-gradient 占位球 220×220 · Phase 2 Three.js GLB · 不引 PNG (减少首次加载)
  - **composer readOnly**: W1 skeleton 不接 ImeGuard / submit 逻辑 · textarea 设 readOnly · 留下一棒接 components/composer/Composer.tsx + ImeGuard.tsx
  - **agent chip testid**: brief 规定 `agent-chip-{credit/report/channel/alert}` 4 个 id · 我按 命名 SSOT v1.1 mapping (客户经理助理→channel · 授信助理→credit · 报告助理→report · 预警助理→alert) · DOM verified
- **下一棒 file checklist** (第 3 棒 · 5 组件域 skeleton · 13 文件 30-45 min):
  - `components/floating/StatusPill.tsx` (32h pill placeholder)
  - `components/floating/PersonaPill.tsx` (32h pill placeholder)
  - `components/floating/TopIcons.tsx` (36 icon placeholder)
  - `components/composer/Composer.tsx` (840×72 + useImeGuard 接入)
  - `components/composer/ImeGuard.tsx` (useImeGuard hook · v3 §4.15 verbatim · PascalCase)
  - `components/composer/Suggestions.tsx` (composer suggestion 列表 placeholder)
  - `components/messages-shell/MessageList.tsx` (skeleton · W2-W4 扩 38 子类)
  - `components/messages-shell/MessageRow.tsx` (skeleton · 单消息 row 占位)
  - `components/toolcall-card/ToolCallCard.tsx` (skeleton · stage_label 中文外显)
  - `components/toolcall-card/ProgressBar.tsx` (stage_label + percent)
  - `components/artifact-card/ArtifactCard.tsx` (skeleton · visible actions ≤ 3)
  - `components/artifact-card/ArtifactActions.tsx` (action button · aria-label 中文)
  - `components/artifact-card/PinHandle.tsx` (拖拽 placeholder · W2-W4 真实做)
- **blocker** (or "无"):
  - 无 (硬 blocker) · 但有一个 PM-decision 待决: tsconfig.json 在 dev 启动时被 Next 自动修改 (jsx + plugins + include) · 当前 revert 后下次再改 · 长期路径: (a) 在 W1-contract 棒 commit 时直接采用 Next 期望值 (jsx: react-jsx + plugins + .next/dev/types) 或 (b) 接受 Next 自动行为视作 git 脏度 · 我倾向 (a) 因 jsx:react-jsx 是 React 19 + Next 16 mandatory
- **ELAPSED min**: 约 40 min
- **commit SHA**: 见 git log 本次 commit
- **tsc --noEmit**: 0 error (双验 · 一次 Next 自动改后 · 一次 revert 还原后)
- **npm run dev**: ok · Ready in 503ms · localhost:3210 HTTP 200 / 13.3 KB · DOM verified (data-testid hero-static / composer-submit / agent-chip-{channel,credit,report,alert} 全命中 · 4 chip 中文文案对 · html lang zh-CN data-theme light 对)
- **token lock**: v3 §10 + 附录 D verbatim (composer 840×72 / radius 36 / send 42 / silent hero 360×280 / work hero 96×96 / trans 420ms hero / 360ms composer / chip 28-32h / pill 32h / icon 36 / modal 480-840 / drawer 420-520 / popover 280-440)
- **PRESERVES**: LY-007 (composer A 静默 hero) · LY-018 (Channel 信号搜索 4 字段 candidate metadata · W1 skeleton 留 W2 接 SSE)
- **NEW-DOM**: data-testid="hero-static" + data-testid="composer-submit" + data-testid="agent-chip-{channel,credit,report,alert}"

## 2026-05-12 05:30 · checkpoint 3 · 5 组件域 skeleton 13 文件 + page.tsx 接 Composer

- **完成文件** (13/24 · 累计 17/24):
  - `components/floating/StatusPill.tsx` (32h pill · 3 态 online/busy/offline · role=status + aria-live=polite · inline style 引 globals.css token)
  - `components/floating/PersonaPill.tsx` (32h pill · 默认 王哲 · 客户经理 · 华东 · avatar 取首字 + name + role + region · role=group)
  - `components/floating/TopIcons.tsx` (36 icon row · 3 button search/theme/settings · role=toolbar · 各 button 中文 aria-label · 自带 svg inline)
  - `components/composer/Composer.tsx` (840×72 复用 globals.css `.composer-shell*` class · 接 useImeGuard(textareaRef, handleSubmit) · useState text + setText · Suggestions 上方插入 · `composer-textarea` testid · 移除 readOnly)
  - `components/composer/ImeGuard.tsx` (PascalCase · `useImeGuard(textareaRef, submit)` hook 名 verbatim · v3 §4.15 verbatim · onCompositionStart/End + onKeyDown + captureFocus + restoreFocus · 兜底 e.nativeEvent.isComposing 跨浏览器)
  - `components/composer/Suggestions.tsx` (0 建议 return null · 1-3 建议 chip 列表 · onPick 父注入 textarea insertText · 默认 console.log)
  - `components/messages-shell/MessageList.tsx` (skeleton · role=log + aria-busy={streaming} · 空数组显 "暂无对话消息" · selector 纪律 doc 注释 reminder · W2-W4 接 VirtualMessageList + 38 子类)
  - `components/messages-shell/MessageRow.tsx` (skeleton · MessageRole 4 enum: user/assistant/system/tool · 各 role 中文 label + 颜色 token · article role + aria-label · content placeholder + children slot 留 W2-W4 inline tool_call/artifact_ref)
  - `components/toolcall-card/ToolCallCard.tsx` (region role + aria-labelledby · 8 status 完整 mapping + 中文 label + STATUS_TONE color + 6 agent label + token · ProgressBar 仅 running/streaming 时显 · data-status/data-agent/data-boundary 暴露)
  - `components/toolcall-card/ProgressBar.tsx` (接 ProgressMessage subset · percent 0-100 int 强校验 Math.max/min/round · stage_label 中文 + 5 enum STATUS_COLOR · role=progressbar + aria-valuenow/min/max/text · WCAG AA via globals.css token)
  - `components/artifact-card/ArtifactCard.tsx` (article role + aria-labelledby title · 5 type 中文 label + 4 status chip + verdict chip (PASS/PARTIAL/FAIL) · header 含 PinHandle · placeholder body · footer 含 ArtifactActions · data-artifact-type/status/owner-agent 暴露)
  - `components/artifact-card/ArtifactActions.tsx` (硬线 visible actions ≤ 3 slice + overflow menu W2-W4 · ActionRiskTier 3 分级 low/medium/high · 3 button style mapping · disabled 状态 cursor:not-allowed + aria-disabled + 中文 disabledReason via aria-describedby)
  - `components/artifact-card/PinHandle.tsx` (role=button + tabIndex=0 keyboard focusable · Space/Enter 触发 · cursor:grab · svg 6 dot drag handle 视觉 · W2-W4 接 HTML5 drag API)
- **page.tsx 改动**:
  - import `Composer` from `@/components/composer/Composer` (line 23)
  - 移除 inline `<section className="composer-shell">` block (原 line 81-129 · 49 line)
  - 替换 `<Composer placeholder="说出你的诉求…" onSubmit={(text) => console.log(...)} />` (line 73-79)
  - 移除 `CSSProperties` import (Composer 内部已封 inline style · page.tsx 不再消费)
  - 总体 diff: -62 line / +1663 line (13 新组件)
- **关键决策**:
  - **ImeGuard hook 兜底**: e.nativeEvent.isComposing 加为第二道防线 · Chrome IME `isComposing` flag · 防 isComposing.current 在 keydown 微秒级 race (老仓踩过类似坑 · 与 v3 §4.15 spec 兼容 · 不冲突)
  - **inline style vs CSS class · floating + toolcall + artifact 域用 inline style 引 var()**: 单组件只用一种 CSS 方案 (CLAUDE.md §3) · floating 3 文件 + messages-shell 2 文件 + toolcall 2 文件 + artifact 3 文件 全 inline style 引 globals.css var() · composer 3 文件复用 globals.css `.composer-shell*` class · 各组件域内部一致
  - **Composer state**: useState 内置 · onSubmit 父注入 · W2-W4 替成 liuyeStore action (selector 纪律预留 · 暂用本地 state 走通 IME flow)
  - **Suggestions 上方插入**: composer-shell wrap 改 flex column · Suggestions 在 composer-shell__inner 之前 · 不破 v3 附录 D.5 锁的 840×72 inner box
  - **ProgressBar percent 强校验**: Number.isFinite check · 防 NaN/Infinity · Math.round 整数化 (per matrix Q1 决议 int) · clamp 0-100
  - **artifact verdict chip**: ArtifactCard 在 status chip 旁加 verdict chip (PASS/PARTIAL/FAIL) · v3 §2.2 verdict 字段 surfaced · W2-W4 接 quality_scorer.py 9-dim 结果
  - **PinHandle 留 cursor:grab + tabIndex=0**: HTML5 drag API W2-W4 接 · keyboard 路径已就位 (Space/Enter activate · 与 drag-and-drop 双轨 per a11y)
- **gotcha (sub-agent 第 4 棒必跟)**:
  - **8 status (ToolCall) ≠ 5 status (ProgressMessage)** 命名漂移点 · 我已在 ProgressBar + ToolCallCard 文件注释里明示 · 第 4 棒做 lib/api/sse.ts SSE consumer 时区分 tool.started → ToolCall.status / tool.progress → ProgressMessage.status
  - **selector 纪律预备**: MessageList.tsx 注释里 reminder 父组件取 messages 时必用 EMPTY sentinel · 第 4 棒做 store/liuyeStore.ts 时**必**创建 `lib/empty.ts` 模块级 `EMPTY_ARRAY` 等 (CLAUDE.md §4 硬线)
  - **useSyncExternalStore stream 路径**: ToolCallCard 当前消费 ToolCall.progress[-1] · 第 4 棒做 store/streamStore.ts 走 35 行 createStore + useSyncExternalStore · 不要在 ToolCallCard 内做 useEffect 监听 progress 数组
  - **PermissionRequest 15 子组件**: ArtifactActions 现仅 3 button style mapping placeholder · risk_tier 3 分级真实 UI form factor (inline confirm / modal / drawer + reason input) 留 W2-W4 完整做
  - **字体加载顺序**: layout.tsx 6 字体 next/font/google preload · globals.css 引用 `var(--font-display)` etc · 我所有组件 inline style 用 `var(--c-font-body)` / `var(--c-font-mono)` 间接引 · 不直接 hardcode 字体名 · 主题切换无影响
- **下一棒 file checklist** (第 4 棒 · 5 文件 30-40 min · 累计 22/24):
  - `store/liuyeStore.ts` (Zustand 5 store · persona/messages/turn state · 无 persist middleware 主 store · CLAUDE.md §2 硬线)
  - `store/streamStore.ts` (35 行 createStore + useSyncExternalStore 范式 · v3 §4 #5 + #11)
  - `lib/api/liuye.ts` (BFF endpoints client · GET /api/liuye/turns · POST /api/liuye/messages · GET /api/liuye/artifacts · v3 §5)
  - `lib/api/sse.ts` (LiuyeChatEvent 11 event consumer · Last-Event-ID + seq gap reconnect · v3 §2.1)
  - `lib/empty.ts` (EMPTY_ARRAY / EMPTY_MAP / EMPTY_SET 模块级 Object.freeze · CLAUDE.md §4 selector 纪律 SSOT)
- **blocker**: 无 (硬 blocker) · checkpoint 2 提的 tsconfig.json PM-decision main session 已 amend (cd28826) · jsx:react-jsx + plugins next + .next/dev/types include · 我未动 tsconfig 完全遵守 brief 硬线
- **ELAPSED min**: 约 35 min
- **commit SHA**: `aa1e1ab` (W1-frontend checkpoint 17/24)
- **tsc --noEmit**: 0 error (13 新组件 + page.tsx 改动后 · strict + noUncheckedIndexedAccess + plugins next 全过)
- **npm run dev**: ok · Ready in 586ms · localhost:3210 HTTP 200 / 13.5 KB · DOM verified (7 data-testid 全命中: hero-static / composer-textarea / composer-submit / agent-chip-{channel,credit,report,alert})
- **IME manual test**: 结构性验证完成 — Composer 内 useImeGuard 已 wire textareaRef + onCompositionStart/End/onKeyDown + e.nativeEvent.isComposing 兜底 · textarea 不再 readOnly (page.tsx 改动确认 DOM) · 真实 keypress E2E 验证留 W2-W4 Playwright smoke (浏览器侧 IME 行为难以脚本化 · CLI subagent 限制)
- **PRESERVES**: LY-007 (composer A 静默 hero · Composer 组件接入) · LY-018 (Channel 信号搜索 4 字段 candidate metadata · W2 接 SSE)
- **NEW-DOM**: data-testid="composer-textarea" (新增 · Composer 内部) · 保留 hero-static / composer-submit / agent-chip-{channel,credit,report,alert}
- **IME-GUARD-VERBATIM**: v3 §4.15 + useImeGuard hook 名 + ImeGuard.tsx PascalCase 文件名 全合规


