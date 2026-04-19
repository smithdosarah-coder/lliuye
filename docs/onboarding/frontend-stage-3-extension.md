# Frontend Platform Shell v1 · Stage 3 Extension Onboarding（Task D/E/F）

**对应 worktree**：`D:/claude code/demo-frontend`（branch `feat/platform-shell`）
**发布日期**：2026-04-19
**前置**：已读 `AGENT_IDENTITY.md` + `CLAUDE.md` §7 + 本文 + `docs/review/frontend-stage-3-regression-diagnosis.md` + `docs/handoff/decisions-log.md`（尤其 A-014~017）
**当前 HEAD**：`290ede2`（Task C 已合）
**目标**：Stage 3 收尾批次——让用户再次打开网页时 O1/O2/O3 全部消除，同时完成原定的双层顶栏排查。Stage 3 最终 APPROVED 判定口径 = Task A/B/C（已合）+ D/E/F 全绿。

---

## 0. 背景（3 行速读）

用户打开网页后反馈"少了细节 / 改了字段 / 中间气泡框变早期设计版本"。主 CLI subagent 诊断归因：**O1/O2 是 Task A 数据契约错位**（AGENTS.tagline 当 description 用）、**O3 是 Stage 2 遗留**（Today `.sheet-card` 从未按 spec 实装）。主 CLI 已落 A-014~A-017 决策，本 Onboarding 把三条决策打包成 **Task D / E / F** 派给本窗口。

---

## 1. 范围 & 不做什么

### 本批 3 Task（打包一批，顺序由你）

| Task | 目标 | 依赖决策 | 工时预算 |
|---|---|---|---|
| **D** | `usePathname` 双层顶栏排查 | 原 Stage 3 onboarding 遗留条款 | 0.5 天 |
| **E** | AgentDef 加 `description` + `eyebrowLabel` 字段 + credit 动态 `<HeaderSlot>` | A-015 + A-016 | 1 天 |
| **F** | Today `.sheet-card` / `.pv-sheets` / `.pv-foot` 完整实装 | A-017 | 0.5-1 天 |

### 不做什么（明确排除，防 scope creep）

- ❌ **不动红区 `tokens.css`**：A-014 已拍板接受 `--ink-14 / --ink-28` 为 canonical，不补 12/24
- ❌ **不删旧 `app/<agent>/page.tsx` 6 文件**：已 307 redirect，本批只从其中**迁文案**；删除另起 commit 等 Stage 4
- ❌ **不动后端 API / SSE / workspace 业务组件**：6 个 workspace client 内部逻辑不改，只改 props 契约（承载新 slot）
- ❌ **不做 Stage 4 的 Archive spec gap**：`.archive-h` 44px vs spec `hero-h1` clamp 不一致是 spec gap，主 CLI 另起 spec 修订，本 Task E 不负责收敛
- ❌ **不改主题切换逻辑**：Crimson 主题 playwright 视觉回归是**验证**动作，不是修改动作

---

## 2. Task D · `usePathname` 双层顶栏排查

### 问题（来自原 Stage 3 onboarding）
`AppShell` 渲染 `Masthead`；但 6 个 `app/<agent>/page.tsx` 文件仍保留旧完整 `<header>` 代码（虽已通过 `next.config.ts` 307 redirect 到 `/archive/<agent>`）。如果 redirect 某种情况失效或 prefetch 命中，会出现双层顶栏。

### DoD
1. 起 dev server 后用 Playwright（或手动）实测以下链路：
   - `http://localhost:3000/credit` → 预期 307 → `/archive/credit`，稳态无双层顶栏
   - 从 Desk `"新建"` 菜单点击某 agent 跳转
   - 从 Archive index tile 点击跳转
   - `router.push` / `<Link>` prefetch 是否在中间态暴露旧 header
2. 若发现双层顶栏**真实发生**：
   - **方案 a**（推荐）：Masthead 的 active tab `match` 逻辑用 `usePathname()` 收敛（见 `Masthead.tsx:17`），对 `/archive/<agent>` 路径高亮 "AI 助手" tab，对 `/credit /channel /report ...` 旧路径也同 tab
   - **方案 b**：若是 redirect 中间态问题，改 `next.config.ts` 用 `permanent: true` 301（浏览器缓存跳转，减少闪现）
   - 不要删旧 `app/<agent>/page.tsx`（本批不做）
3. 若未发现双层顶栏 → commit body 写"未发现双层顶栏，Playwright 截图 4 链路稳态均单层"，附截图路径
4. Signal trailer: `Signal: FRONTEND-TASK-D-DONE` 或 `Signal: FRONTEND-TASK-D-NO-REGRESSION`

### 红区边界
- 不动 `AppShell.tsx` 的结构布局
- 不动 `Masthead.tsx` 除 active tab `match` 逻辑外的代码
- `next.config.ts` 改 redirect 配置需在 commit body 标出前后差异

---

## 3. Task E · AgentDef 加 description + eyebrowLabel + credit HeaderSlot

### 依据
- **A-015**: AgentDef 加 `description: string` 字段（A 默认）+ credit 走 `<HeaderSlot>`（B 特例）
- **A-016**: 回退 eyebrow "A06 · Report Generation" 长版，加 `eyebrowLabel: string` 字段

### DoD

#### 3.1 · `lib/agents.ts` schema 升级
从 6 个旧 `app/<agent>/page.tsx` 提取原文案，填入 `AgentDef`：

```ts
export type AgentDef = {
  code: string;           // A01-A06
  key: string;            // channel/credit/report/...
  title: string;          // CJK 标题
  tagline: string;        // archive index tile 用（保留原用途）
  description: string;    // 新增 · page-level 描述（archive/[agent] lede 用）
  eyebrowLabel: string;   // 新增 · "Report Generation" / "Credit Decision Assistant" 等
};
```

**文案提取来源**（严禁编造，从旧 page 复刻原文）：
- `app/report/page.tsx:239-248` → description + eyebrowLabel
- `app/credit/page.tsx:307-320`（包含 SEGMENT_META 默认态文案）
- `app/channel/page.tsx`
- `app/alert/page.tsx`
- `app/compliance/page.tsx`
- `app/riskctrl/page.tsx`

若某 agent 旧 page 描述是**动态的**（如 credit 的 SEGMENT_META），静态 `description` 取"默认态"（如 credit 默认 segment = "corporate"），动态切换走 3.3 slot。

#### 3.2 · `archive/[agent]/page.tsx` 渲染升级
```tsx
<div className="eyebrow">
  <span style={{ width: 32, height: 1, background: "var(--ink-28)" }} />
  {def.code} · {def.eyebrowLabel}   {/* A-016: 不再 key.toUpperCase() */}
  <Link href="/archive">← 返回助手目录</Link>
</div>
<h1 className="archive-h">
  <span style={{ fontFamily: "var(--cjk)", fontWeight: 700 }}>{def.title}</span>
</h1>
<p className="archive-lede">
  {slotDescription ?? def.description}   {/* A-015: slot 覆盖静态 */}
</p>
```

#### 3.3 · credit `<HeaderSlot>` 机制
实装跨 client 的 slot 传递：
- **推荐方案**：React Context `HeaderSlotContext` 挂在 `archive/[agent]/page.tsx`，Credit workspace client 通过 `useContext(HeaderSlotContext).setDescription(segmentDesc)` 在 segment 变化时注入
- **Fallback**：若 Context 无值，`archive/[agent]` 渲染 `def.description` 默认态
- 其他 5 个 agent workspace **不需要** 挂 slot（静态 description 已够用）

**验收**：
- 打开 `/archive/credit` → 默认 segment=对公 → lede 显示 SEGMENT_META.corporate.description
- 切换 segment 到普惠 → lede 更新为 SEGMENT_META.inclusive.description
- 切到对私 → lede 更新为 SEGMENT_META.retail.description
- 打开 `/archive/report` → lede 显示 `def.description`（静态，slot 无值）

#### 3.4 · 删除清单（不做）
旧 `app/<agent>/page.tsx` 6 文件**保留**，本批只从其中迁文案。删除动作推 Stage 4 专项 cleanup，不要在本 Task 里触发 A-012.D 语义问题（SHA-immutable）。

#### 3.5 · Signal
`Signal: FRONTEND-TASK-E-DONE`

---

## 4. Task F · Today `.sheet-card` 完整实装

### 依据
**A-017**: User 明确感知 regression，Stage 3 必做。

### 参考 spec
- `D:/claude code/credit_report_agent_work/design_mockups/shell.html:1882-2240` Today 规格
- `.card.warm.sheet-card` + `.tag` + `h3 .nbr + em` + `.pv-sheets .sheet.running + .sheet.idle` + `.pv-foot .badge + .open`
- 色系用 `var(--g0..g7)` / `var(--ink-*)` / `var(--accent)` / `var(--safe)`（A-014 canonical）

### DoD

#### 4.1 · `web/src/app/today/page.tsx:79-101` 容器升级
从当前简版 `<ul><li>` 升级到 `.card.warm.sheet-card` 结构：

```tsx
<article className="card warm sheet-card">
  <div className="tag">
    <span className="dash" />
    <span className="label">agent · 正在跑</span>
    <span className="sum">共 {totalCount} 位</span>
  </div>
  <h3>
    <span className="nbr">{String(runningCount).padStart(2, "0")}</span>
    <em>running.</em>
  </h3>
  <div className="pv-sheets">
    {runningSheets.map(s => (
      <div className="sheet running" key={s.id}>
        <span className="sheet-tag">{s.tag}</span>
        <span className="sheet-state">{s.state}</span>
        <span className="sheet-title">{s.title}</span>
        <span className="sheet-sub">{s.sub}</span>
        <span className="sheet-eta">ETA {s.eta}</span>
        <div className="sheet-bar" style={{ "--pct": `${s.pct}%` }} />
      </div>
    ))}
    {idleSheets.map(s => (
      <div className="sheet idle" key={s.id}>
        <span className="sheet-tag">{s.tag}</span>
        <span className="sheet-state">idle</span>
        <span className="sheet-title">{s.title}</span>
      </div>
    ))}
  </div>
  <footer className="pv-foot">
    <span className="badge">02.</span>
    <Link href="/dispatch" className="open">打开调度台 ↘</Link>
  </footer>
</article>
```

#### 4.2 · CSS 补齐（`web/src/app/views.css` 或新 `today.css`）
从 shell.html 迁移相关 class 定义，对齐 `--ink-14 / --ink-28`（A-014 canonical）：

- `.card.warm.sheet-card` 容器（背景 gradient / border / radius）
- `.tag` 布局 + `.dash` + `.label` + `.sum`
- `h3 .nbr` 大号数字（display font）+ `em` 斜体英文尾
- `.pv-sheets .sheet.running` 行布局（网格或 flex）
- `.pv-sheets .sheet.idle` 灰态独立视觉（opacity / color 下降一档）
- `.sheet-bar` 进度条用 `::after` + `width: var(--pct)` 渐变
- `.pv-foot` 尾栏 + `.badge` + `.open` 链接

#### 4.3 · Mock 数据扩展
当前 `web/src/mocks/today.ts`（若存在）可能只挂简版字段。新增字段：
```ts
type RunningSheet = {
  id: string;
  tag: string;        // e.g. "A06"
  state: string;      // e.g. "running"
  title: string;      // agent 名
  sub: string;        // 客户/材料简述
  eta: string;        // e.g. "2min"
  pct: number;        // 0-100 进度
};
type IdleSheet = {
  id: string;
  tag: string;
  title: string;
};
```

保持 mock 驱动，与现有 `DESK_QUICK_CREATE` 风格对齐。不要引入真实后端 poll。

#### 4.4 · 验收
- 打开 `/today` 中间 card 显示：tag pill + 大号数字 + 英文尾 + ≥3 running sheets（含进度条）+ ≥1 idle sheet（灰态）+ 尾栏链接
- 视觉对拍 `design_mockups/shell-today-1440.png`（若存在）或 shell.html 预览
- 点击 "打开调度台 ↘" 跳转 `/dispatch`

#### 4.5 · Signal
`Signal: FRONTEND-TASK-F-DONE`

---

## 5. 收尾动作（3 Task 全完成后）

### 5.1 · Playwright 1440 viewport 视觉回归
跑 4 主题 × 3 view（today / archive/credit / archive/report）= 12 截图，对比 shell.html / mockup：

```bash
# 自由选实装方式：Playwright codegen / 手写脚本 / webapp-testing skill
pnpm playwright ... # 或 mcp browser_* 裸调
```

截图落 `web/__snapshots__/stage-3-final/` 或 `docs/ui-snapshot-stage-3.md` 附录。

关键核对项：
- Crimson 主题下 ink-14/28 替代 vs onboarding 原 ink-12/24 是否仍 imperceptible（A-014 Follow-up #3）
- archive/credit segment 切换 lede 动态更新
- today sheet-card 4 主题下色彩协调

### 5.2 · READY-FOR-REVIEW commit
所有 3 Task 完成后，emit:
```
Signal: FRONTEND-STAGE-3-READY-FOR-REVIEW
```

commit body 列 D/E/F 各自完成状态 + Playwright 回归截图路径 + `curl`/启停命令 verbatim（R-A smoke-must-test）。

### 5.3 · 主 CLI 侧动作（本窗不做）
收到 READY signal 后，主 CLI 触发 Stage 3 最终 review → APPROVED → 升级 scorecard → 解封 agent2/4 Phase 1。

---

## 6. 硬规则快照（每轮必过）

- **R-A smoke-must-test**: 每 commit 必须在 commit body 列 verbatim 运行命令 + 输出摘要；未 smoke 的 commit 一律 `Signal: TASK-*-NO-SMOKE` 注明原因
- **R-B 一 commit 一 Signal**: 每 commit trailer 只 1 个 `Signal:` 行
- **A-012.D SHA 不可变**: 本 worktree feat/platform-shell 已有 commits 不准 rebase / amend / force-push，纠错用新 commit
- **红区零触碰**: `shared/` / `docs/contracts/` / `api_server.py` / `agent_*/api/` / `evaluation/runner/base_evaluator.py`（ink-12/24 补充归此红区）/ `docs/handoff/decisions-log.md` / `docs/scorecard/GLOBAL.md`
- **无方案停下**: 遇到 onboarding 未覆盖的 spec 缺口 → `Signal: NEED-DECISION-Q-NNN` 停下，不要自造解法
- **onboarding 与实装偏离**: 按 onboarding 开工前 diff 一遍；若发现 spec 不 consistent 先 Q/A 再动

---

## 7. 开工前的 git fetch

```bash
cd "D:/claude code/demo-frontend"
git fetch upstream chore/l0-infra
git log --oneline upstream/chore/l0-infra -5
# 应见: ef80943 docs(review+handoff): frontend Stage 3 regression diagnosis + Q-014~017
# 应见: 7fa19ef docs(onboarding): Agent2 + Agent4 Phase 1 + Agent6 Phase 2 drafts
# 应见: 9312f26 docs(review): Agent1 Phase 1 APPROVED
```

读 `docs/review/frontend-stage-3-regression-diagnosis.md`（subagent 诊断）+ `docs/handoff/decisions-log.md` 尾部 Q-014~017 + 本 onboarding 对齐后开工。

完成 Task D/E/F 后**不要自己升级 scorecard**（红区，主 CLI 亲操），`READY-FOR-REVIEW` 即可。
