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

