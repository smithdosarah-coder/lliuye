# Frontend Stage 3 Visual Regression Diagnosis

- 日期: 2026-04-19
- reviewer: 主 CLI 调查 subagent
- worktree: `D:/claude code/demo-frontend`
- branch: `feat/platform-shell`
- HEAD: `290ede2` (Task C) · tree 含 Task A (dc63f42) + B (f5ca52e) + C (290ede2)
- spec 基线: `design_mockups/shell.html` (2026-04-18 lock) + `docs/design/platform-shell-v1.md`

---

## 1 · 用户观察（原文）

> "刚刚看到前端 CLI 弹出了网页，和我们之前的方案有一定出入，少了一些细节，改了些字段，中间的气泡框也变成早期设计版本了"

拆 3 条特征：

- **O1** "少了一些细节" —— 页面元素 / 文案精度下降
- **O2** "改了些字段" —— 可见字段文案变了
- **O3** "中间的气泡框变成早期设计版本" —— 中间 card 的 UI 回退

---

## 2 · 代码变更清单（Task A/B/C 合并）

### 2.1 Task A (`dc63f42`) —— 6 workspace 抽离

新增 12 文件（6 server wrapper + 6 client），从 `app/<agent>/page.tsx` 搬业务体到 `components/workspace/<agent>/<Agent>WorkspaceClient.tsx`。**commit message 原文承认的 3 项手术**：

1. 外层 `<div className="px-8 py-8 max-w-[1400px] mx-auto">` **删**
2. 页面级 `<header>`（eyebrow + h1 + description）**整块删** —— 因 "archive 顶部已从 AGENTS 常量渲染同结构 header"
3. 原 header 右侧按钮 **搬进内容区**

按钮搬迁验证（挑 2 个代表性页）：

- **report**: `LLMStatusIndicator + MockToggle` → 根顶 `flex justify-end gap-4 mb-4`，见 `web/src/components/workspace/report/ReportWorkspaceClient.tsx:237-241`。搬迁正确，功能等价 ✓
- **credit**: `handoffSource banner + SegmentedControl` → 右栏顶 `flex items-center justify-end gap-3 flex-wrap`，见 `web/src/components/workspace/credit/CreditWorkspaceClient.tsx:429-457`。搬迁正确，功能等价 ✓

**Task A 唯一的有害副作用不在代码，而在数据**：页面级 description 被删后，由 `archive/[agent]/page.tsx` 渲染 `def.tagline` 取代——但 `AGENTS[].tagline` 是静态短语（如 report 的 tagline 是 "材料 → 授信申报书"），远不如原 page header 的动态完整描述丰富。见 §3.2 O2 证据链。

### 2.2 Task B (`f5ca52e`) —— archive/[agent] 挂载

唯一改动文件: `web/src/app/archive/[agent]/page.tsx`（+35/-33）。

当前渲染结构（见 `page.tsx:34-67`）:

```
<div className="v-archive px-8 py-8 max-w-[1400px] mx-auto">
  <div className="eyebrow" style=...>
    <span style={{ width:32, height:1, background:"var(--ink-28)" }} />
    {def.code} · {def.key.toUpperCase()}         ← 如 "A06 · REPORT"
    <Link href="/archive">← 返回助手目录</Link>
  </div>
  <h1 className="archive-h" style={{ marginTop: 12 }}>
    <span style={{ fontFamily:"var(--cjk)", fontWeight:700 }}>{def.title}</span>
  </h1>
  <p className="archive-lede">{def.tagline}</p>    ← 这里信息量骤降
  <div style={{ marginTop: 24 }}><Workspace /></div>
</div>
```

字号: `.archive-h` 定义在 `views.css:125-128` = `44px` 固定。spec `hero-h1` (shell.html L2373-2376) 是 `clamp(42px,5vw,82px)`，Archive view 里的视觉锚。两者不一致但 spec 里没有 Archive **子路由** 的单独章节，此处是 spec gap，archive/[agent] 的 header 规格**未被定义过**。

### 2.3 Task C (`290ede2`) —— 色系 migration

332 legacy token → 291 new token + 23 ember literal `#c8463a`。映射表 workspace-only，不触碰 `ui/* viz/* layout/* app/<agent>/page.tsx globals.css`。

**自承的 spec deviation**（commit body 明写）:

> Onboarding mapping table cites `var(--ink-12)` for `--color-line` and `var(--ink-24)` for `--color-line-strong`, but tokens.css does not define `--ink-12` or `--ink-24` (defined: 04/08/14/18/28/32/48/65/80). Used nearest existing tokens (`--ink-14 / --ink-28`). Visual delta: ≤4% opacity, imperceptible. Recommend Q-012...

实测验证：
- `web/src/app/tokens.css:37-45` ink scale = {04, 08, 14, 18, 28, 32, 48, 65, 80}。**ink-12 / ink-24 确实不存在。**
- `web/src/components/workspace/**` 中 `ink-12 / ink-24` 命中数 = 0；`ink-14 / ink-28 / ...` 命中数 = 163。替代执行到位。

视觉影响：2-3% alpha 差，单独看几乎不可感知，但多条 border/line 叠加后整体灰度偏深 1 档。归类 §3.3 O1 边缘证据，单独不成立。

---

## 3 · spec 视觉元素核对 + 归因

### 3.1 核对表 · 工作区（archive/[agent]）

| 元素 | shell.html spec | 旧 app/<agent>/page.tsx | 新 archive/[agent] + workspace client | 结论 |
|---|---|---|---|---|
| 外层 padding | n/a（spec 无子路由条款） | `px-8 py-8 max-w-[1400px]` | `px-8 py-8 max-w-[1400px]` via archive 壳 | ✓ 等价 |
| 页面 eyebrow | n/a | "A06 · Report Generation" etc. | `{code} · {KEY}` + "← 返回助手目录" | ≈ 等价，加了返回链接 |
| 页面 h1 | n/a | 36px display font，如"信贷报告助手" | 44px `.archive-h` + CJK | **改了视觉规格**（更大） |
| 页面 description | n/a | 多行动态描述（如 credit 随 segment 变） | `def.tagline` 单句静态 | **信息量骤降** |
| 顶部状态按钮 | n/a | page-header 右侧 | 搬到内容区右对齐 | ✓ 搬迁正确 |
| 内容区 12-col grid | n/a | 12-col | 12-col（workspace client 内部） | ✓ 保留 |
| Card 色系 | var(--g0..7) / --ink / --accent / --safe | legacy --color-* | new token + ember literal | ✓ 迁完，14/28 替代有 spec gap |
| error banner | n/a | `border-l-4 --color-ember` | `border-l-4 #c8463a` + 注释 | ✓ 语义保留 |

### 3.2 核对表 · 4 view 壳（未被 Task A/B/C 修改）

**关键发现**：Today / Dispatch / Warroom / Archive-index 都由更早的 Stage 2 `e5dad4b` 产出，本次 3 个 Task 未触碰。但用户"气泡框"观察指向 **Today 中间 card**，所以仍需诊断。

| 元素 | shell.html L2047-2170 (Today 中间 card) | 当前 `web/src/app/today/page.tsx:79-101` | 差距 |
|---|---|---|---|
| 容器 class | `.card.warm.sheet-card` + tag/h3/pv-sheets/pv-foot/badge/open | `.v-card`（普通 linear-gradient） | **样式降级** |
| `<div class="tag">` | dash + label "agent · 正在跑" + sum "共 06 位" | `.v-card-tag` 简化版 | ≈ 等价结构 |
| `<h3><span class="nbr">03</span><em>running.</em></h3>` | 大号数字 + 斜体英文尾 | `.v-card-h` 用 `{count}<em>running</em>` | ≈ 等价 |
| `.pv-sheets .sheet.running` | 每条含: sheet-tag + sheet-state + sheet-title + sheet-sub + **eta** + **sheet-bar 进度条** | 仅 `<ul><li>` 标题 + status 副标 + 百分比文字 | **少了进度条、ETA、tag pill、分隔排版** |
| `.pv-sheets .sheet.idle` | idle 条带有独立视觉（灰态） | 同上 `<li>` | **无 idle 视觉区分** |
| `.pv-foot + .badge "02." + .open "打开调度台 ↘"` | 卡底统一尾栏 + 编号 + 打开链接 | 整张 card 包在 Link，无尾栏 | **缺尾栏** |

→ **这就是 O3 "早期设计版本" 的实锤**。Today view 中间 card 从未按 shell.html 的 `sheet-card` / `pv-sheets` 规格实装，一直停在 Stage 2 的 `.v-card` stub 版本。Task A/B/C 无涉。

### 3.3 归因（对 3 条 observation 逐条）

#### O1 "少了一些细节" → **(b) Task A 副作用** + **(d) Stage 2 未实装遗留**

主因: Task A 把 `<header>` 整块删掉后，改由 `archive/[agent]/page.tsx` 用 `AGENTS[].tagline` 渲染 lede。tagline 是设计给 Archive index tile 的**短标语**（如 `材料 → 授信申报书` · `报告 → 评分 → 额度建议`），不是 page-level description。原页面描述（如 report 的 "读入企业材料包,按「普惠授信申报及审查审批意见表」节段自动撰写,未能填写字段显式标注。"）**直接丢失**，未在任何地方接续。

证据:
- 旧 `web/src/app/report/page.tsx:244-248` 描述 64 字
- 新 `web/src/app/archive/[agent]/page.tsx:62` = `{def.tagline}` 仅引用短语
- `web/src/lib/agents.ts:39` report.tagline = `"材料 → 授信申报书"`（11 字）

次因: Today 中间 card 缺进度条 / ETA / idle 分层，见 §3.2 表 —— 与 3 个 Task 无关。

#### O2 "改了些字段" → **(b) Task A 副作用**

`AGENTS[].code` 在 `lib/agents.ts:33-94` 给 Agent 分配了 "A06 / A01 / A03 / A02 / A04 / A05" —— 这不是旧 page header 里的命名（旧 report page 叫 "A06 · Report Generation"，credit 叫 "A03 · Credit Decision Assistant"）。新 archive/[agent] eyebrow 渲染 `{code} · {KEY}` = "A06 · REPORT"（upper case key），和旧的 "A06 · Report Generation" 风格字面不一致——大小写、短语、tagline 均不同。

证据:
- 旧 `web/src/app/report/page.tsx:239-241` eyebrow = "A06 · Report Generation"
- 新 `web/src/app/archive/[agent]/page.tsx:50` eyebrow = `{def.code} · {def.key.toUpperCase()}` = "A06 · REPORT"
- h1 差: 旧 "信贷报告助手" (36px) vs 新 同名但 44px + CJK class

credit 页更惨：旧 description 随 `SEGMENT_META[segment].description` 动态切换（对公 / 普惠 / 对私 3 套文案），新 archive/[agent] 只显示 `"报告 → 评分 → 额度建议"` 一句静态。用户切 segment 时不再看到说明文字变化 → 直观感受"字段改了"。

证据: `web/src/components/workspace/credit/CreditWorkspaceClient.tsx:307-500` 无 `SEGMENT_META[segment].description` 使用；旧 `web/src/app/credit/page.tsx:318-320` 有。

#### O3 "中间的气泡框变成早期设计版本" → **(d) Stage 2 未实装遗留（非本次 3 Task 的锅）**

见 §3.2 表。Today 中间 "agent · 正在跑" card 在 Stage 2 Task C (`e5dad4b`) 就是简版 `<ul><li>`，本次 3 个 Task 未触碰 `web/src/app/today/page.tsx`。用户说"变成早期版本"是准确感知：spec 的 `sheet-card` 丰富形态**从未实装过**，一直是早期 stub。

| 情况 | 归类 |
|---|---|
| 视觉降级是 Task A/B/C 的 regression | ❌ 否 |
| 视觉降级是 Stage 2 未完成实装 | ✅ 是 |

---

## 4 · Task D 影响预测

Task D = `usePathname` 双层顶栏修正。当前我未观察到"双层顶栏"现象:
- `AppShell.tsx` 只渲染 1 个 `Masthead`
- `workspace/*/` client 内**已无** page-level header（Task A 删了）
- archive/[agent] 页只有 eyebrow + h1 + lede + workspace，无第二个 Masthead

**推测** Task D 的实际工作可能是:
1. 6 个 `app/<agent>/page.tsx` 仍保留旧完整 page 代码（如 `web/src/app/credit/page.tsx:307-516`，旧 `<header>` 完整在那），但已通过 `next.config.ts:25-31` 307 redirect 到 `/archive/<agent>`。如果 redirect 某种情况失效（如 Link 拦截、prefetch 命中），会显示旧页的 header + Masthead 双层。
2. 或者 Masthead 当前标签的 `match` 逻辑里 `/credit /channel ...` 的老路径仍高亮 "AI 助手" tab（见 `Masthead.tsx:17`），即便 301 会把 URL 扶正，中间态短促闪一下可能被看到。

两种猜测都无法仅凭静态分析确认，**无法定论，需要 playwright 实跑 1440 viewport 截图核** `/credit` → `/archive/credit` 跳转瞬间、以及挂载完成稳态。

**推测 Task D 是否能解决 O1/O2/O3**:
- O1 少了细节: **不能** —— 描述丢失是 AGENTS tagline vs 页级 description 的数据层问题，不是顶栏。
- O2 改了字段: **不能** —— 同理。
- O3 中间气泡框: **不能** —— Today card 简化与 Task D 无关。

---

## 5 · 建议下一步（不自行执行）

### 5.1 REJECT 的 Task：无

Task A/B/C 本身的手术都按 onboarding 完成，**无代码层面 REJECT 理由**。用户观察的真正 root cause 是:

- **数据层缺失**（AGENTS tagline 不是页级 description 的替代）—— 需要补契约
- **Stage 2 Today card 未按 spec 实装** —— 需要新 Task

### 5.2 建议主 CLI 发的 decisions-log 事项

- **Q-012 (Task C 已建议)** —— `--ink-12 / --ink-24` tokens 是否加入 `tokens.css`？建议选 **B. 接受 14/28 为 canonical**（视觉差 2-3% alpha，不值得动红区）。若选 A 则需更新 onboarding 里所有引用 ink-12/24 的地方。
- **Q-013 (新建议)** —— `AGENTS[].tagline` 被 archive/[agent] 当 lede 使用，但 tagline 原始用途是 archive index tile 短标语。需决策: 
  - **方案 A**: 给 AgentDef 新增 `description: string` 字段，archive/[agent] 渲染 description，archive index 继续用 tagline
  - **方案 B**: 由 Workspace client 自行暴露一个 "slot" 把旧 page 级 description 吐出，archive/[agent] 渲染 slot
  - **方案 C**: 接受短 tagline 作为子路由 lede（承认信息量降级）
  推荐 A——最小侵入，保留 dynamic description（credit 的 segment 切换描述需要动态时再用 slot，走 B）。

- **Q-014 (新建议)** —— `eyebrow` 文案规格: 旧 "A06 · Report Generation" vs 新 "A06 · REPORT"。哪个是 canonical？shell.html L2369 Archive view 用的是 `"ARCHIVE · 频道 03"` 格式（全 CJK/数字），spec 没定义子路由 eyebrow 规格。主 CLI 需拍板 tx 文案，可能再补一个 AgentDef 字段 `eyebrow: string`。

- **Q-015 (新建议·最重要)** —— Today view `sheet-card` / `pv-sheets` 丰富形态是否在 Stage 3 之前必须实装？用户已经感知到"早期版本"，这是体验层 regression（即便非 Task A/B/C 引入）。建议列为 Stage 3 Task E 或 Stage 4 阻断项。

### 5.3 GO Task D 能解决什么

- Task D (`usePathname` 双层顶栏) **大概率不能**消除 O1/O2/O3 中的任何一条观察。
- Task D 该跑完，但完成后用户仍会看到 O1/O2/O3 的 residual。
- 在派 Task D 之前，**建议主 CLI 先回答 Q-013 / Q-014 / Q-015**，Q-013 决策完才能派 Task E 补 description。否则 Task D 做完用户观察不会改善，会被误读为 Task D 无效。

### 5.4 需要实跑验证的盲区

- 实跑 `pnpm dev` + Playwright 截图 `/archive/credit` 与旧版 `/credit`（redirect 前）对比，确认"双层顶栏"是否真的发生过、在什么交互路径下发生。当前静态分析**无法定论**。
- 实跑 4 主题切换，确认 Task C 的 14/28 替代在 Crimson 主题（色阶对比最强）下是否仍 imperceptible。

---

## 6 · 附录: 核心文件锚点

- `D:/claude code/demo-frontend/web/src/app/archive/[agent]/page.tsx` (新 Task B)
- `D:/claude code/demo-frontend/web/src/app/today/page.tsx` (Stage 2 未升级)
- `D:/claude code/demo-frontend/web/src/app/views.css:123-160` (v-archive / v-tile)
- `D:/claude code/demo-frontend/web/src/app/tokens.css:37-45` (ink scale 无 12/24)
- `D:/claude code/demo-frontend/web/src/lib/agents.ts:33-94` (AGENTS 常量)
- `D:/claude code/demo-frontend/web/src/components/workspace/report/ReportWorkspaceClient.tsx:235-517` (抽离后)
- `D:/claude code/demo-frontend/web/src/components/workspace/credit/CreditWorkspaceClient.tsx:307-502` (抽离后)
- `D:/claude code/demo-frontend/web/src/app/report/page.tsx:236-253` (旧 header · 已 redirect 但文件还在)
- `D:/claude code/demo-frontend/web/src/app/credit/page.tsx:307-350` (同上)
- `D:/claude code/demo-frontend/web/next.config.ts:25-31` (6 条 legacy redirect)
- `D:/claude code/credit_report_agent_work/design_mockups/shell.html:1882-2240` (Today spec)
- `D:/claude code/credit_report_agent_work/design_mockups/shell.html:2367-2447` (Archive spec)
- `D:/claude code/credit_report_agent_work/docs/design/platform-shell-v1.md` (spec 文本 v1)
