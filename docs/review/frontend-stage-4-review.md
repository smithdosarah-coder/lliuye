# Frontend Stage 4 · Review (APPROVED)

**Worker**: feat/platform-shell
**HEAD**: 0d7feb0 (FRONTEND-STAGE-4-DONE)
**Review 时间**: 2026-04-20
**Review by**: 主 CLI
**决议**: APPROVED · 可合 chore/l0-infra

---

## 一 Commit 链盘点（10 个 Task + 1 个 Task D 文档 fix-up）

| Task | 内容 | commit | Signal |
|---|---|---|---|
| Spec Landed | v2 spec + onboarding + mockup lock（sha256 `84a5e0ef...` · 3748 行） | `e869a72` | `FRONTEND-STAGE-4-SPEC-LANDED` |
| A | `tokens.css` 整包重写 + next/font 迁移 | `6dae0ad` | `FRONTEND-STAGE-4-TASK-A-DONE` |
| B | Masthead / FloatBadge / ThemeSwitcher 1:1 | `94db10e` | `FRONTEND-STAGE-4-TASK-B-DONE` |
| C | Desk 抽屉 ⌘K + mousemove 16ms throttle | `bf79aff` | `FRONTEND-STAGE-4-TASK-C-DONE` |
| D | `/today` hero (glyph-rise + 3 kv + LIVE pill) | `dd438e2` | `FRONTEND-STAGE-4-TASK-D-DONE` |
| D-docfix | onboarding §D 追平 mockup（3 kv + 无 lede） | `ff052c9` | （无，归 Task D 收尾） |
| E | `/today` FeedCard 15 行 + mask fade | `eda88f0` | `FRONTEND-STAGE-4-TASK-E-DONE` |
| F | `/today` BoardCard 7 pin-board 纸条 | `a6894af` | `FRONTEND-STAGE-4-TASK-F-DONE` |
| G | `/dispatch` 3 列 IM（频道 + 会话 + 卷宗） | `b7cc870` | `FRONTEND-STAGE-4-TASK-G-DONE` |
| H | `/archive` 6 tile 聚合 | `aa61124` | `FRONTEND-STAGE-4-TASK-H-DONE` |
| I | `/warroom` 4 列 kanban + 10 priority 变体 | `a6f45a5` | `FRONTEND-STAGE-4-TASK-I-DONE` |
| J | 20 PNG 截图 + Playwright 5 断言 + 全量回归 | `0d7feb0` | `FRONTEND-STAGE-4-TASK-J-DONE` + `FRONTEND-STAGE-4-DONE` |

共 12 个 commit（含 SPEC-LANDED + Task D docfix），其中 10 个携带阶段 Signal trailer。

---

## 二 Red Zone Gate 验收（R-0..R-6）

规则出处：`D:/claude code/demo-frontend/docs/onboarding/frontend-stage-4-rmassistant.md` §〇 前置约束。

### R-0 视觉 1:1（CSS class / DOM / keyframe / SVG / stagger 参数对齐 mockup）

- Task D commit `dd438e2`：「onboarding 原 DoD 提及 hero-meta 4 pill + lede，但 mockup L2791-2809 实为 3 kv + 1 pill 且无 lede，按 R-0 mockup 为准」
- Task E commit `eda88f0`：onboarding 的 type=info 一项 mockup 无，砍；保留 urgent/unread/sys/warn 4 真实变体
- Task F commit `a6894af`：onboarding 的 `.pk-bullet` 6 变体 / `.pk-bar` 进度条 / `blip` 脉冲均不在 mockup 实际 board-card DOM，按 mockup 实作 `.pv-board .note` 4 变体（p0/p1/p2/done）
- Task G commit `b7cc870`：memo 着色 `.memo.urgent` / `.memo.system` 在 mockup 不存在，按 mockup 只一种 `.memo` 样式
- Task H commit `aa61124`：onboarding tile 顺序「报告/预警/合规/授信/风控/获客」与 mockup L3270-3351「获客/风控/授信/预警/合规/报告」相反，按 mockup（AGENT · 01-06）实作
- Task I commit `a6f45a5`：onboarding 列名「待分配/进行中/等待回复/已完成」，mockup 实「待处理/进行中/冒出/已归档」，按 mockup

**绿**。6 处偏离均以「mockup 为源头，onboarding 是草拟 DoD，R-0 为最高优先」说明，无擅自剪裁。

### R-1 实际对应（路由 + 时钟 + 端口）

- Task B commit `94db10e`：Masthead「live clock `setInterval` 20s, hydration-safe（time="" 空字符串 fallback）」；「4 tab match (`/today /dispatch /archive+6legacy /warroom`)」
- Task D commit `dd438e2`：「eyebrow 日期 + live 时间 SSR 占位『—』/『--:--』，20s tick」
- Task J commit `0d7feb0`：Playwright `baseURL 127.0.0.1:3000`，20 test 跑 4 view 各 5 主题

**绿**。

### R-2 不动既有 workspace

- Task H commit `aa61124`：「`<Link href="/archive/<key>"> `包整个 `.agent` article, 点击跳既有 workspace」
- Task H commit `aa61124` DoD 验证：「/archive/{report,channel,credit,riskctrl,alert,compliance} 全 200;/archive/bogus HTTP 404」——Stage 3 ext 落地的 6 workspace 路由保留
- Task H 只替换 `page.tsx` landing 为 6-tile grid

**绿**。

### R-3 tokens.css 整包替换（单次完成）

- Task A commit `6dae0ad` 单次 commit 覆盖：5 主题 tokens + 6 Agent 功能色 + 11 keyframes + cursor SVG data URI + `--r-md 18 / --r-lg 26` + 字体栈变量
- 后续 Task B..I 无人修 `tokens.css`（Task J commit `0d7feb0` 说明 Letterpress 对比度 ≥15:1 WCAG AAA 通过，Q-C 未触发 retake）

**绿**。

### R-4 浏览器基线（Chrome/Edge 111+ / Safari 16.4+）

- `D:/claude code/credit_report_agent_work/CLAUDE.md §7` 第 98 行：「浏览器基线：`color-mix()` 要求 Chrome/Edge 111+ / Safari 16.4+（银行内网兼容待产品决策）」
- Stage 4 无 fallback 条件分支写入，与 spec 一致；银行内网兼容 defer Stage 5

**绿**。

### R-5 mock 在 `web/src/lib/mock/`

真实 diff（`git diff --stat chore/l0-infra..feat/platform-shell`）命中：

- `web/src/lib/mock/desk.ts`（Task C）
- `web/src/lib/mock/today.ts`（+135 行，Task D/E/F 累计）
- `web/src/lib/mock/dispatch.ts`（+283 行，Task G）
- `web/src/lib/mock/archive.ts`（Task H）
- `web/src/lib/mock/warroom.ts`（+399 行，Task I）

5 份 mock 全部在对目录。无内嵌 component。

**绿**。

### R-6 Signal 每 Task 一次

- 10 个 Task 对应 10 个 Signal trailer（见 §一 表格）
- Task D 文档 fix-up commit `ff052c9` 未新 Signal（明言「不发新 Signal, 算 Task D 收尾」）——符合「Signal 每 task 一次」约束
- 阶段收尾 Task J commit `0d7feb0` 同时携带 `TASK-J-DONE` + `STAGE-4-DONE` 两条 trailer（onboarding §五规定）

**绿**。

**7 Red Zone 全绿。**

---

## 三 Task 级 DoD 采样（D / G / J 重点）

### Task D — `/today` hero 区

- `dd438e2` commit message：「HERO_WORD『今日看板』按字拆 `.glyph.cn`, baseDelay 0.8s + i*0.045s」「useEffect 清 animation→reflow→回填 保证导航回来 stagger 重放」
- hero-meta 3 kv big：管道总额 ¥28.5亿 / 在队项 14项 / 风险等级 黄色III + LIVE pill（与 mockup L2791-2809 一致）
- 偏离点：onboarding 原 DoD 4 pill + lede → 实作 3 kv + 无 lede，`ff052c9` 追平 onboarding 文字
- DoD 验证：「tsc 0 err / /today HTTP 200 / html 含 `.glyph.cn` + `hero-meta--row` + 3 个 kv 中文 label」

### Task G — `/dispatch` 3 列 IM

- `b7cc870` commit message：「3 列 grid: 左 thread list（频道/DM）/ 中 memo block（会话主区）/ 右 卷宗 sidebar」
- 6 组件：`DispatchShell / ChannelList / MessageThread / CaseSidebar / MemoCallout / Segs`
- CSS 移植点：「追加新 `.v-dispatch .dispatch` 3 列 grid (260 / 1fr / 320) + `.dp-col/.ch/.msg/.memo/.composer/.dp-info` 全套规则, 移植 mockup L1331-1405 1:1」
- 偏离点（onboarding 草拟 vs mockup 实）：
  - onboarding「5 thread × 每 thread 8-12 memo」→ mockup 6 channels，memo 是会话内罕见 callout
  - onboarding「3 个卷宗卡片」→ mockup 1 张卷宗 × 5 row
  - onboarding「`.memo.urgent` / `.memo.system` 两种着色」→ mockup 只一种 `.memo`
- DoD 验证：「3 列 `.dp-col` + `.dp-col.dp-main` + `.dp-col.dp-info` 各 1 实例 / 6 `.ch` button（只 1 `.ch.on`）/ 1 `.msg.me` / 1 `.memo` callout / 1 `.composer` input / 5 `.row` 卷宗行 / 8 `.glyph`」

### Task J — 20 截图 + Playwright 回归

- 20 PNG 落盘 `web/__snapshots__/stage-4-final/` 已核实存在（`canvas/matcha/dusk/letterpress/ink` × `today/dispatch/archive/warroom`）
- Playwright 5 断言（`0d7feb0` commit message 原文）：
  - a) 4 view HTTP 200
  - b) Masthead `.shell-op .name="王哲"` · `.role="客户经理 · 华东"`
  - c) Desk hover `clientX<22` → `aside.drawer.open` 出现（仅 today 验一次避免污染其他 view 截图）
  - d) `body[data-theme]` 切换后真变（ink 走 `setAttribute`，switcher 隐藏）
  - e) hero `.hero-h1 .word .glyph` count > 0（glyph-rise stagger 在位）
- Letterpress 对比度：`--g0 #F0EBE0 / --ink #14120F` 对比度 ≥15:1，WCAG AAA 通过，**Q-C 未触发 retake**
- 构建：`npx tsc --noEmit` 0 err；`npm run build` 20 路由全 static/SSG 成功
- 工程约定：`web/.gitignore` 追加 `/test-results/` + `/playwright-report/`；`package.json` 新增 `"test:snap": "playwright test"`；devDep `+@playwright/test ^1.59.1`

---

## 四 偏离集合（onboarding 文字 DoD vs mockup 实际）

每条从 commit message 原文摘，末尾附裁定。

| # | Task | commit | onboarding 草拟 | mockup 实际 | 裁定 |
|---|---|---|---|---|---|
| 1 | D | `dd438e2` | hero-meta 4 pill + lede | 3 kv big + 1 LIVE pill，无 lede | 合规（R-0 优先，且 `ff052c9` 回追 onboarding） |
| 2 | E | `eda88f0` | feed type 含 `info` 一项 | 仅 urgent/unread/sys/warn 4 真实变体 | 合规 |
| 3 | F | `a6894af` | `.pk-bullet` 6 变体 + `.pk-bar` + `blip` 脉冲 | `.pv-board .note` 4 变体 p0/p1/p2/done | 合规（bar-flow/blip keyframes 仍在 tokens.css 备用） |
| 4 | F | `a6894af` | 渐变 `--g6 → --g7 + ink 叠加` | `--g1 78% → --g4 84% → --g6 90%`（mockup L383） | 合规 |
| 5 | G | `b7cc870` | 5 thread × 8-12 memo | 6 channels，memo 是 agent 消息内 callout | 合规 |
| 6 | G | `b7cc870` | `.memo.urgent` / `.memo.system` 2 着色 | 仅一种 `.memo` 样式 | 合规 |
| 7 | G | `b7cc870` | 3 个卷宗卡片 | 1 张卷宗 × 5 row | 合规 |
| 8 | G | `b7cc870` | 未读红点 + 20s 刷新 | `.ch .meta` 静态时间串无红点 UI | 合规（`unread` 字段保留供未来扩展） |
| 9 | H | `aa61124` | tile 顺序 报告/预警/合规/授信/风控/获客 | 获客/风控/授信/预警/合规/报告（AGENT · 01-06） | 合规 |
| 10 | H | `aa61124` | 本周使用次数 + 最近活跃时间 2 行 stat | 单行 stat（活跃线索/在用规则/...） | 合规（mockup 无两行空间） |
| 11 | H | `aa61124` | accent 边框 + icon 底纹（mockup 无 `--t-*`） | 叠加在 mockup 之上（border-left 3px + `.circle bg`） | 合规（onboarding 附加，不破坏 mockup g2-g6） |
| 12 | I | `a6f45a5` | 列名 待分配/进行中/等待回复/已完成 | 待处理/进行中/冒出/已归档 | 合规 |
| 13 | I | `a6f45a5` | 7 priority pill | mockup 只 4 样 + onboarding 加 7 variants = 10 合集（P0-P3/compli/law/risk + urg/wait/cn） | 合规（对 mockup 取超集） |
| 14 | I | `a6f45a5` | 每列 10-14 张 ~50 张总 | mockup 原 14 张 → 扩至 51 张填满 4 列（种子 1:1 保留，其余按风格扩展） | 合规 |
| 15 | I | `a6f45a5` | case-in 首屏进场 | mockup `.kcol` rise 逐列；保留 mockup + 附加 `.kcard` case-in 逐卡 stagger | 合规（叠加不替换） |

**所有偏离均为合规**。Frontend worker 守 R-0 视觉 1:1 优先，onboarding 文字 DoD 作草拟稿在冲突处让位于 mockup。

---

## 五 验收数字

- **Commit 数**：12（10 Task Signal + 1 SPEC-LANDED + 1 Task D onboarding docfix）
- **PNG 截图**：20（`web/__snapshots__/stage-4-final/` · 5 主题 × 4 view）
- **Playwright 断言**：5 条（HTTP 200 / Masthead persona / Desk hover / `data-theme` 切换 / glyph-rise count>0）
- **Red Zone**：7 条（R-0..R-6）全绿
- **tsc 结果**：`npx tsc --noEmit` 0 err
- **build 结果**：`npm run build` 20 路由全 SSG 成功，0 err
- **diff 规模**（`git diff --stat chore/l0-infra..feat/platform-shell` 真实值）：
  - 133 files changed
  - 12496 insertions(+)
  - 8325 deletions(-)
- **新增 mock 体量**：
  - `web/src/lib/mock/dispatch.ts` +283 行
  - `web/src/lib/mock/warroom.ts` +399 行
  - `web/src/lib/mock/today.ts` +135 行
  - 另 `desk.ts` / `archive.ts` 两份新文件
- **Letterpress 对比度**：`--g0 #F0EBE0` / `--ink #14120F` ≥15:1，WCAG AAA 通过，**Q-C 未触发 retake**

---

## 六 决议

**APPROVED**。可 `--no-ff` merge 回 `chore/l0-infra`（保留 worker 分支历史）。

- 7 Red Zone 全绿
- 15 条 onboarding → mockup 偏离全数「合规」判定（R-0 优先执行正确）
- Letterpress 主题 WCAG AAA 通过（≥15:1），Q-C 无需 retake
- Q-A（后端对接）/ Q-B（监控埋点）**defer Stage 5**
- 无遗留红区触碰、无擅自剪裁、无跨 Task Signal 乱序

---

## 七 后续

1. 主 CLI 执行：`git merge --no-ff feat/platform-shell` → `chore/l0-infra`（保留 worker 分支历史作为 audit trail）
2. 更 `docs/scorecard/GLOBAL.md` 前端行为 **APPROVED · Stage 4 · 2026-04-20**
3. 更 `docs/scorecard/definition-of-done.md` Stage 3 ext → Stage 4 状态位推进
4. Stage 5 立项决断（待用户）：
   - **Q-A** 后端对接（6 Agent API 真实 wiring，替换 mock）
   - **Q-B** 监控埋点（交互事件 / 主题切换 / Desk 使用频次）
   - **Q-C** Letterpress retake（当前 AAA 通过，不立案）
   - **Q-D** 银行内网浏览器兼容（`color-mix` fallback 或 PostCSS 预处理）
   - **Q-D'** kcard 拖拽（Stage 4 视觉态已齐，交互 defer）
