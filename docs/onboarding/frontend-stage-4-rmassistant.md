# Frontend Stage 4 · RM Assistant 视觉 1:1 复刻

**目标**：把 `design_mockups/rm-assistant-final-2026-04-19.html` 全量翻译为 Next.js 实现，视觉 1:1（CSS / DOM / 动画 / SVG / JS 交互），端口·路由·实时时钟·mock 数据 shape 按现有前端实际对应。

**规范源**：`docs/design/platform-shell-v2.md`（Stage 4 task overview 见 §七）
**Mockup**：`design_mockups/rm-assistant-final-2026-04-19.html`（sha256 `84a5e0ef...` · 3748 行 · 161KB）
**分支**：`feat/platform-shell`（Worker CLI，不走 main）
**信号约定**：每个 Task 完成 commit trailer `Signal: FRONTEND-STAGE-4-TASK-<X>-DONE`；阶段收尾 `FRONTEND-STAGE-4-DONE`

---

## 〇 前置约束（Red Zone · 违反即返工）

| # | 约束 | 解释 |
|---|---|---|
| R-0 | **视觉 1:1**：CSS class 名 / DOM 层级 / keyframe name / SVG viewBox / stagger 参数必须与 mockup 对齐 | 重命名 / 改层级 / 合并样式全部拒收 |
| R-1 | **实际对应**：端口走 `localhost:3000`，路由走 `/today /dispatch /archive /warroom`，时钟走 `new Date()` 20s tick，不硬编 mockup 的字面时间 | mockup 里写 `14:32` 的地方要变动态 |
| R-2 | **不动既有 workspace**：`/archive/[agent]` Stage 3 ext 落地的 A-015/016 workspace 保留，Task H 只替换 `/archive` landing 为 6-tile，tile click 跳转既有 workspace 路由 | 删 workspace 子路由直接 revert |
| R-3 | **tokens.css 整包替换**：Task A 一次性把 5 主题 tokens / 动画 / cursor / noise overlay 落齐，不要分多次改 | 分多次 ≈ 多次破坏基线 |
| R-4 | **浏览器基线**：Chrome/Edge 111+ / Safari 16.4+（`color-mix` 依赖），不给 fallback | 银行内网兼容在 Stage 5 决策 |
| R-5 | **mock 数据在 `web/src/lib/mock/`**，不内嵌 component；结构向 mockup 对齐但字段名英文 | 内嵌 mock 直接 revert |
| R-6 | **Signal 每 task 一次**：一次 commit 一个 Signal trailer，不攒堆；阶段收尾额外一次 `FRONTEND-STAGE-4-DONE` | 攒堆导致 main CLI 定位回滚点成本爆炸 |

---

## 一 Task 清单（A–J · 10 Task）

### Task A · tokens.css 全量重写

**Goal**：5 主题 tokens + 5 keyframes + cursor SVG + noise overlay + font stack + 圆角 / 阴影 token 全部就位
**Input**：mockup L11–220
**Output**：`web/src/styles/tokens.css`（整包重写）
**DoD**：
- [ ] 5 个 `[data-theme="..."]` 块（canvas / matcha / dusk / letterpress / ink）各有 `--g0..--g7 --g0b --ink-1..3 --chalk-1..3 --accent` 完整
- [ ] 6 Agent 功能色 tokens：`--t-report --t-alert --t-compli --t-credit --t-riskctrl --t-channel`
- [ ] keyframes：`bodyBreath 22s / drift 38s / breathe 8.5s / glyph-rise / rise / card-rise / bar-in / case-in / bar-flow / wait-slide / blip`
- [ ] Custom cursor：`--cursor-default` 内嵌 SVG data URI
- [ ] `body::after` SVG turbulence noise overlay（feTurbulence baseFrequency / mix-blend-mode multiply）
- [ ] Font stack：Funnel Display / Instrument Sans+Serif / Noto Sans+Serif SC / JetBrains Mono（next/font 加载）
- [ ] 圆角：`--r-md: 18px / --r-lg: 26px`
- [ ] `npm run lint` 0 err · `tsc --noEmit` 0 err
**Signal**：`FRONTEND-STAGE-4-TASK-A-DONE`

### Task B · Masthead + Float-badge + Theme switcher 复刻

**Goal**：共享 layout 壳 1:1
**Input**：mockup L2770–2787（Masthead） + L3483–3558（Float-badge 5 SVG） + L3562–3569（Theme switcher）
**Output**：`web/src/components/shell/Masthead.tsx` / `FloatBadge.tsx` / `ThemeSwitcher.tsx` + `web/src/app/layout.tsx` 组合
**DoD**：
- [ ] Masthead：logo + 4 tab（今日 / 对话 / AI 助手 / 任务）+ persona `王哲 · 客户经理 · 华东`（mock 可配） + live clock（`setInterval(20s)`，hydration-safe）
- [ ] 4 tab active 态跟随 `usePathname()`（`/today /dispatch /archive /warroom`）
- [ ] Float-badge：5 个 SVG 符号（落日 / 禅圆 / 桃花 / 铅字印章 / 太极）按 `data-theme` 切换显隐
- [ ] Theme switcher：4 个按钮（Canvas / Matcha / Dusk / Letterpress），Ink 按钮不渲染；点击 `document.body.dataset.theme = ...`；首次载入从 localStorage 读偏好
- [ ] 4 view 切换 tab 时 Masthead 不重渲染（React Layout / Suspense 保持）
**Signal**：`FRONTEND-STAGE-4-TASK-B-DONE`

### Task C · Desk 抽屉 1:1

**Goal**：左抽屉 hover-from-edge + pin + Esc + dr-sec × 4
**Input**：mockup L2643–2768
**Output**：`web/src/components/shell/Desk.tsx` + `web/src/lib/mock/desk.ts`
**DoD**：
- [ ] hover-from-edge：`mousemove` 事件 `clientX < 22` 触发展开，离开收起（throttle 16ms）
- [ ] Pin 按钮锁定展开态；Esc 键收起并解锁
- [ ] 4 个 `.dr-sec`：我的客户 / 进行中 / 最近 / 新建；dot 变体（`.dot.live / .dot.due / .dot.idle`）
- [ ] `⌘K` 快捷键聚焦顶部搜索框（`dr-qc`）
- [ ] mock 数据 5–8 条每 section（来自 `desk.ts`）
- [ ] 与 Masthead 同层级，不被 view 切换销毁
**Signal**：`FRONTEND-STAGE-4-TASK-C-DONE`

### Task D · /today hero 区

**Goal**：单 word `今日看板` + glyph-rise stagger + 4-pill hero-meta（单位拆分）+ hero lede
**Input**：mockup L223–356 + L2791–2850
**Output**：`web/src/app/today/page.tsx`（替换现有 hero） + `web/src/components/today/Hero.tsx`
**DoD**：
- [ ] `<h1>` 里每个字符拆 `<span>` 带 `--i` index，React `useEffect` 触发 `.glyph-rise` animation
- [ ] hero-meta 4 pill：如 `7:12 事件`、`3 红`、`5 黄` 等，每 pill 数字 + 单位分别渲染（`.nbr` + `em`）便于字体精调
- [ ] lede 段落：mockup L257 原文案移植
- [ ] `data-theme` 切换时 hero bg 跟随渐变
**Signal**：`FRONTEND-STAGE-4-TASK-D-DONE`

### Task E · /today feed-card

**Goal**：今日事件流卡片 + urgent/unread/sys 标签 + 底部 mask fade
**Input**：mockup L2850–2960
**Output**：`web/src/components/today/FeedCard.tsx` + 扩充 `web/src/lib/mock/today.ts` `TODAY_FEED` 5 → 15 条
**DoD**：
- [ ] 15 条 mock feed，每条含 `time / type (urgent/unread/sys/info) / title / excerpt / source`
- [ ] 底部 `mask-image: linear-gradient(...)` fade 效果
- [ ] `.tag.urgent` 红 / `.tag.unread` 琥珀 / `.tag.sys` 灰（走 accent token）
- [ ] 滚动区高度固定 + overflow-y scroll
**Signal**：`FRONTEND-STAGE-4-TASK-E-DONE`

### Task F · /today board-card（深色）

**Goal**：`.card.deep` 深色看板 + peek-list + pk-bullet 6 变体 + pk-bar 进度
**Input**：mockup L2960–3144
**Output**：`web/src/components/today/BoardCard.tsx` + 扩充 `today.ts` board mock
**DoD**：
- [ ] `.card.deep` 深色渐变（`--g6 → --g7` + ink 叠加）
- [ ] peek-list 3–5 条，每条 `.pk-bullet` 六种变体（running / waiting / blocked / done / due / signal）对应不同 accent
- [ ] waiting 项有 `.pk-bar` 进度条（`bar-flow` animation）
- [ ] `.pk-bullet.signal` 伴随 `blip` 脉冲动画
**Signal**：`FRONTEND-STAGE-4-TASK-F-DONE`

### Task G · /dispatch 3 列布局

**Goal**：Slack 风 IM + memo block + 卷宗侧栏
**Input**：mockup L3145–3268
**Output**：`web/src/app/dispatch/page.tsx`（替换现有） + `web/src/components/dispatch/*.tsx` + 扩充 `web/src/lib/mock/dispatch.ts`
**DoD**：
- [ ] 3 列 grid：左 thread list（频道/DM） / 中 memo block（会话主区） / 右 卷宗 sidebar（客户档案 + agent 工单快照）
- [ ] memo 支持 `.memo.urgent` / `.memo.system` 两种标注
- [ ] mock：5 个 thread + 每 thread 8–12 memo + 3 个卷宗卡片
- [ ] 未读红点 + 最近活跃时间（实时 20s 刷新）
**Signal**：`FRONTEND-STAGE-4-TASK-G-DONE`

### Task H · /archive 6 tile 聚合

**Goal**：替换当前 placeholder → 6 Agent tile landing；tile click 跳 `/archive/[agent]` 既有 workspace
**Input**：mockup L3270–3351
**Output**：`web/src/app/archive/page.tsx`（整页重写） + `web/src/components/archive/AgentTile.tsx`
**DoD**：
- [ ] 6 tile（报告 / 预警 / 合规 / 授信 / 风控 / 获客），每 tile 用对应 `--t-*` 功能色做 accent 边框 + icon 底纹
- [ ] tile 显示：agent 名 + 一句话定位 + 本周使用次数 + 最近一次活跃时间
- [ ] tile 点击跳转 `/archive/${agentSlug}`（既有 Stage 3 ext workspace，不动 children 实现）
- [ ] tile hover `card-rise` 微位移
**Signal**：`FRONTEND-STAGE-4-TASK-H-DONE`

### Task I · /warroom 4 列 kanban

**Goal**：作战室看板 + 7 种优先级 pill
**Input**：mockup L3353–3478
**Output**：`web/src/app/warroom/page.tsx`（替换） + `web/src/components/warroom/KanbanColumn.tsx` + `KCard.tsx` + 扩充 `web/src/lib/mock/warroom.ts`
**DoD**：
- [ ] 4 列：待分配 / 进行中 / 等待回复 / 已完成；每列 heading + count pill
- [ ] 每列 10–14 张 `.kcard` mock，总 ~50 张
- [ ] 7 种 `.priority-pill` 变体（P0/P1/P2/P3/合规/法务/风险），每个颜色 token 对齐 mockup
- [ ] kcard 拖拽**不做**（Stage 5 再议），视觉态齐全即可
- [ ] `case-in` 首屏进场动画
**Signal**：`FRONTEND-STAGE-4-TASK-I-DONE`

### Task J · 5 主题 × 4 view = 20 截图基线 + 最终回归

**Goal**：全量视觉回归，Letterpress 主题也要通过（Q-C 默认保留）
**Input**：Task A–I 全部落地
**Output**：`web/__snapshots__/stage-4-final/{canvas,matcha,dusk,letterpress,ink}-{today,dispatch,archive,warroom}.png` 共 20 张
**DoD**：
- [ ] 20 张截图全部与 mockup 对应区域像素对齐（允许 ±2% anti-alias 差异）
- [ ] Playwright 断言：4 view 均可加载（HTTP 200） + Masthead 存在 + Desk hover 能展开 + 主题切换器切换后 `data-theme` 真的变了
- [ ] 跨主题 hero glyph-rise stagger 均正常播放（不是 CSS freeze）
- [ ] `tsc --noEmit` 0 err · `npm run lint` 0 err · `npm run build` 成功
- [ ] 若 Letterpress 在回归中视觉对比度失败（Q-C 重拍条件），在本 Task 内 retake tokens 并补 commit
**Signal**：`FRONTEND-STAGE-4-TASK-J-DONE` + `FRONTEND-STAGE-4-DONE`

---

## 二 依赖图

```
Task A (tokens)
  ├─▶ Task B (Masthead/Float/Switcher 依赖 tokens + keyframes)
  ├─▶ Task C (Desk 依赖 tokens)
  └─▶ Task D..I (所有 view 依赖 tokens + B + C 壳已就位)
          └─▶ Task J (全量回归，最后)
```

**强串行边**：A → B → (C 可并 D..I)；C 与 D..I 可并，但 D..I 内部互相不依赖（4 个 view 独立）；J 必须最后。

---

## 三 Worker 派发 2 方案

### 方案甲：单 Worker 串行（~3 天）

主 CLI 派单给当前 `feat/platform-shell` Worker，A → B → C → D → E → F → G → H → I → J 顺序做。每 Task 一次 commit + Signal，主 CLI APPROVE 后派下一个。

**优点**：上下文连续，风格一致，Worker 自己的 mock / token 判断不会分叉。
**缺点**：D..I 有 6 个 view 任务本可并行，串行浪费。

### 方案乙：多 Worker 并行（~1 天）

- Worker-shell（`feat/platform-shell`）：Task A + B + C + J（壳 + 回归）
- Worker-today（`feat/platform-shell-today` 分叉）：Task D + E + F
- Worker-dispatch（`feat/platform-shell-dispatch` 分叉）：Task G
- Worker-archive（`feat/platform-shell-archive` 分叉）：Task H
- Worker-warroom（`feat/platform-shell-warroom` 分叉）：Task I

A + B + C 完成后其他 Worker 从该 commit rebase 开始并行；各自完成后主 CLI 负责合回 `feat/platform-shell`，最后 Worker-shell 跑 J。

**优点**：总时长压缩 60%+。
**缺点**：tokens / component 命名不一致风险高；合并冲突 mock 文件可能重复写；主 CLI 要做 4 路合并裁决。

**Dispatcher's call**（Q-D）——**建议方案乙**，前提是主 CLI 在 A 完成后立即 freeze tokens.css，其余 Worker 只 consume 不动。

---

## 四 验收（Stage 4 整体）

- [ ] 20 张截图落入 `__snapshots__/stage-4-final/`
- [ ] `docs/review/frontend-stage-4-review.md`（主 CLI 产出）
- [ ] `docs/scorecard/definition-of-done.md` Stage 3 ext → Stage 4 状态位推进
- [ ] 5 主题在生产 build 下 flash-of-unstyled 为 0（首屏 body data-theme 已定）
- [ ] Q-A / Q-B（后端对接 / 监控埋点）**不在 Stage 4 范围**，Stage 5 再议
- [ ] Q-C Letterpress 若重拍发生，在 Task J commit 内说明
- [ ] `feat/platform-shell` HEAD 合入 `main` 前保留 Worker 分支快照

---

## 五 Signal 总览

| Task | Signal trailer |
|---|---|
| A tokens | `FRONTEND-STAGE-4-TASK-A-DONE` |
| B Masthead+Float+Switcher | `FRONTEND-STAGE-4-TASK-B-DONE` |
| C Desk | `FRONTEND-STAGE-4-TASK-C-DONE` |
| D Today hero | `FRONTEND-STAGE-4-TASK-D-DONE` |
| E Today feed | `FRONTEND-STAGE-4-TASK-E-DONE` |
| F Today board | `FRONTEND-STAGE-4-TASK-F-DONE` |
| G Dispatch | `FRONTEND-STAGE-4-TASK-G-DONE` |
| H Archive 6-tile | `FRONTEND-STAGE-4-TASK-H-DONE` |
| I Warroom kanban | `FRONTEND-STAGE-4-TASK-I-DONE` |
| J 20 screenshot 回归 | `FRONTEND-STAGE-4-TASK-J-DONE` + `FRONTEND-STAGE-4-DONE` |

阶段启动 spec 落盘：`FRONTEND-STAGE-4-SPEC-LANDED`（本次提交）
