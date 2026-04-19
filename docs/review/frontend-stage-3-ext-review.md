# Frontend Platform Shell v1 · Stage 3 Extension Review (Task D/E/F)

**日期**：2026-04-19
**reviewer**：主 CLI（via subagent，credit_report_agent_work 主工树）
**onboarding**：`docs/onboarding/frontend-stage-3-extension.md`
**worktree**：`D:/claude code/demo-frontend` · branch `feat/platform-shell`
**HEAD**：`9486d00`
**Signal**：`FRONTEND-TASK-F-DONE`
**Range**：`deeecb9..9486d00`（5 commits：deeecb9 merge onboarding / f6f4ba1 ACK / a7ff006 Task D / 71e13f4 Task E / 9486d00 Task F）

## Verdict

**APPROVED**

## DoD 对账（逐条）

### Task D · usePathname 双层顶栏 4 链路核验（evidence SHA: `a7ff006`）

| 条目 | 状态 | 证据 |
|---|---|---|
| 4 链路 Playwright 稳态截图（1440×900） | OK | `__snapshots__/stage-3-ext/taskD-link{1..4}-*.png` 4 张齐全；commit body L17-30 列每条链路的 `mastheadCount=1` 明证 |
| 直链 `/credit` → 307 → `/archive/credit` 单层 | OK | link1 截图 `mastheadCount=1, anyHeaderCount=3 (1 Masthead + 2 card-internal)`，card-internal 属内容区 `<header>`（非 page-level） |
| `/archive` index tile 点击跳转 | OK | link2 `mastheadCount=1, mastheadTabOn="AI 助手"` |
| Desk "新建" 菜单点击跳转 | OK | link3 `mastheadCount=1, anyHeaderCount=7`（1 Masthead + 6 workspace card-internal，仍全一层 Masthead） |
| `/today` Link prefetch 扫描（legacy route 暴露） | OK | link4 `22 anchors, 0 legacy-route links, 0 Next.js prefetch <link> to legacy paths`（vacuously safe） |
| src 静态分析：0 legacy hrefs | OK | commit body L33 "src/ 内 0 legacy hrefs (/credit\|/channel\|/alert\|/compliance\|/report\|/riskctrl)" |
| Masthead.tsx 结构未改（红区尊重） | OK | `git diff deeecb9..a7ff006 -- web/src/components/Masthead.tsx` empty |
| Signal trailer | OK | `Signal: FRONTEND-TASK-D-NO-REGRESSION`（onboarding §2.4 允许的两种之一） |

**结论**：Task D 无需修改任何代码，纯 verification commit。Masthead.tsx:17 的 `startsWith("/archive") \|\| LEGACY_ROUTES.some((r) => p.startsWith(r))` 已覆盖两类路径，无需 `usePathname` 重写。

### Task E · A-015 + A-016 landing（evidence SHA: `71e13f4`）

| 条目 | 状态 | 证据 |
|---|---|---|
| 3.1 `lib/agents.ts` AgentDef 加 `description` + `eyebrowLabel` | OK | `web/src/lib/agents.ts:28-29` 字段新增；L22-33 schema 升级 |
| 3.1 · 6 agent description/eyebrowLabel 从旧 page **verbatim** 迁移 | OK | spot-check：report `lib/agents.ts:42-44` vs 旧 `app/report/page.tsx:240,245-246` → description 64 字符**完全一致**"读入企业材料包,按「普惠授信申报及审查审批意见表」节段自动撰写,未能填写字段显式标注。" + eyebrow "Report Generation"。channel `lib/agents.ts:54-57` vs `app/channel/page.tsx:151,156-157` 同样 verbatim。无 paraphrase |
| 3.2 `archive/[agent]/page.tsx` 渲染 `{def.code} · {def.eyebrowLabel}` | OK | 实装走 `ArchiveAgentShell`（间接渲染）；见 `archive/[agent]/page.tsx:35-42` 把 `eyebrowLabel` 作 props 传入；`ArchiveAgentShell.tsx:35` 渲染 `{code} · {eyebrowLabel}` |
| 3.2 lede 来自 `def.description` | OK | `ArchiveAgentShell.tsx:17` `const lede = slot?.description ?? description;`；L46 `<p className="archive-lede">{lede}</p>` |
| 3.3 HeaderSlot Context（推荐方案 A：Context + Provider） | OK | `web/src/lib/header-slot.tsx` 31 行，`HeaderSlotContext / HeaderSlotProvider / useHeaderSlot` 完整三件套；`ArchiveAgentShell.tsx:52-57` Provider 包 children |
| 3.3 Credit workspace `useEffect` `setDescription(SEGMENT_META[segment].description)` | OK | `CreditWorkspaceClient.tsx:144` `const headerSlot = useHeaderSlot();` + L147-150 useEffect 随 `segment` 变化推 description，cleanup `setDescription(null)` |
| 3.3 Playwright 三段 segment 切换 lede 证据 | OK | commit body L48-55 列对公/普惠/对私 3 文案对比；`taskE-credit-retail-lede.png`（retail 态） + `taskE-report-static-lede.png`（static fallback） |
| 3.4 旧 `app/<agent>/page.tsx` 6 文件保留 | OK | Stage 4 scope，`next.config.ts` 307 redirect 继续生效；`git diff deeecb9..71e13f4 -- web/src/app/{channel,credit,report,alert,compliance,riskctrl}/page.tsx` empty |
| 3.5 Signal trailer | OK | `Signal: FRONTEND-TASK-E-DONE` |
| tsc 0 err | OK | commit body L72 `tsc: 0 err`，reviewer 在 HEAD 重跑 `cd web && npx tsc --noEmit` → 零输出（pass） |
| R-A smoke-must-test | OK | commit body L38-46 列 6 路由 curl 返回 200 及 SSR lede 文本对 AgentDef.description 等值核对（verbatim 贴输出） |

### Task F · A-017 Today .card.warm.sheet-card 实装（evidence SHA: `9486d00`）

| 条目 | 状态 | 证据 |
|---|---|---|
| 1. Today 中栏 Link 改 `.card.warm.sheet-card` | OK | `web/src/app/today/page.tsx:82` `<Link href="/dispatch" className="card warm sheet-card">` |
| 1. `.tag` + `.dash` + `.label` + `.sum` | OK | `today/page.tsx:83-89` 结构完整对 shell.html 规格 |
| 1. `<h3><span className="nbr">03</span><em>running.</em></h3>` 大数字 | OK | `today/page.tsx:90-93` 零填充 running count |
| 1. `.pv-sheets .sheet.running` 每条含 sheet-tag/sheet-state/sheet-title/sheet-sub/eta/sheet-bar | OK | `today/page.tsx:94-112` 完整 6 字段；`style={{ "--p": ${s.pct}% }}` 渐进条 CSS var 驱动 |
| 1. `.pv-sheets .sheet.idle` 独立灰态视觉 | OK | `today/page.tsx:113-125` idle sheet 无 sheet-bar；`views.css:254 .v-today .sheet.idle .sheet-tag { color: var(--ink-48); }` + L268 `.sheet.idle .sheet-title` italic 弱化 |
| 1. `.pv-foot.sheet-foot` + `.badge` | OK | `today/page.tsx:127-134` 尾栏 + `<div className="badge">02.</div>` |
| 2. tokens.css 零触碰 | OK | `git diff deeecb9..9486d00 -- web/src/app/tokens.css` empty |
| 2. 新 CSS scope 到 `.v-today` | OK | `views.css:240-319` 新增 class 全部前缀 `.v-today`（计数：15 条 `.v-today .sheet-*` + `.v-today .card` 等） |
| 3. taskF-today-sheet-cards.png | OK | `__snapshots__/stage-3-ext/taskF-today-sheet-cards.png` 存在（Canvas 默认态） |
| 4. 4 主题 sweep（sheet-card 渐变跟 --g6 切换） | OK | `taskF-today-sheet-cards.png`（Canvas） + `taskF-today-matcha.png` + `taskF-today-dusk.png` + `taskF-today-crimson.png` 全齐；额外一张 `taskF-preview-today-canvas.png` 预览 |
| 5. tsc 0 err | OK | commit body L23 `tsc 0 err`，reviewer 在 HEAD 重跑 `cd web && npx tsc --noEmit` → 零输出（pass） |
| 6. Signal trailer | OK | `Signal: FRONTEND-TASK-F-DONE` |
| shell.html lock spec 关键 class 对齐 | OK | spot-check 5 class：`.sheet-tag / .sheet-state / .sheet-title / .sheet-sub / .sheet-bar / .pv-foot.sheet-foot` 全部字面出现在 `today/page.tsx` 与 `views.css`，命名与 shell.html 2026-04-18 lock 一致 |
| RunningSheet / IdleSheet types | OK | `web/src/lib/mock/today.ts:64-80` 类型完整；`TODAY_RUNNING_SHEETS × 3` + `TODAY_IDLE_SHEETS × 3` |

## 硬规则对账

| 规则 | 状态 | 说明 |
|---|---|---|
| R-A smoke-must-test | OK | Task E commit body verbatim 贴 6 路由 curl + SSR 断言；Task F commit body L30 列启停命令 verbatim；Task D commit body 列 4 链路 Playwright `mastheadCount` 具体数字。reviewer 在 HEAD `9486d00` 重跑 `cd web && npx tsc --noEmit` → 0 err（Task E/F 均声明的一致） |
| R-B 一 commit 一 signal | OK | 5 commit 逐个 grep trailer：`deeecb9`(merge 无 signal，onboarding 类允许) / `f6f4ba1` `Signal: FRONTEND-STAGE-3-EXT-ACK` / `a7ff006` `Signal: FRONTEND-TASK-D-NO-REGRESSION` / `71e13f4` `Signal: FRONTEND-TASK-E-DONE` / `9486d00` `Signal: FRONTEND-TASK-F-DONE`。每非 merge commit 恰一 trailer |
| A-012.D SHA 不可变 | OK | `git reflog feat/platform-shell @{0..15}` 无任何 `rebase` / `amend` 条目；5 commit 全部 `commit:` 类型（deeecb9 单条 `commit (merge):`），零重写。从 `4e493f7 branch: Created` 以降全部线性新增 |
| Signal await semantics | OK | commit body 自陈每 Task 完成后 "停等 GO 再进下一 Task"，符合 A-011 / MEMORY signal await |

## 红区审计

**命令**：`git diff deeecb9..9486d00 --first-parent --no-merges -- web/src/app/tokens.css web/src/components/AppShell.tsx web/src/components/Masthead.tsx next.config.ts`

**结果**：**empty**（零 hunk）。四红区文件在本 5 commit 窗口内零触碰，worker 严格遵守 onboarding §1 "不动什么"。

额外审计：

- `web/src/app/tokens.css` ink scale `{04, 08, 14, 18, 28, 32, 48, 65, 80}` 保持 A-014 canonical，`--ink-12 / --ink-24` 在全 `web/src/**` 下 grep 命中数 `0`（reviewer 实测），A-014 严格贯彻
- 旧 `app/<agent>/page.tsx` 6 文件保留（Stage 4 cleanup），本批只做文案 verbatim 迁移，未触发 A-012.D SHA 重写问题
- `docs/handoff/decisions-log.md` / `docs/scorecard/GLOBAL.md` / `shared/**` / `api_server.py` / `agent_*/api/**` 均未被 worker 触碰（主 CLI 独占）

## A-014/015/016/017 landing check（本 review 特有）

| 决策 | 预期落点 | 实际状态 | 证据 |
|---|---|---|---|
| A-014 ink-14/28 canonical（不补 ink-12/24） | `tokens.css` 保留 `--ink-14 / --ink-28`；全 src 下 0 处 ink-12/24 引用 | **LANDED** | `tokens.css:39` `--ink-14:` + `tokens.css:41` `--ink-28:`；grep `--ink-12\|--ink-24` over `web/src/` 命中数 **0** |
| A-015 AgentDef 加 `description` + credit `<HeaderSlot>` | `AgentDef.description` + Context Provider + credit useEffect | **LANDED** | `lib/agents.ts:28` `description: string` 字段；`lib/header-slot.tsx` 31 行 Context 实装；`CreditWorkspaceClient.tsx:147-150` useEffect 驱动 slot；Playwright 三段 segment 切换文案实证 |
| A-016 eyebrow 长版 "A06 · Report Generation" 回退 | `AgentDef.eyebrowLabel` 字段 + 6 agent 长版英文 | **LANDED** | `lib/agents.ts:29` `eyebrowLabel: string`；6 agent 分别填 "Report Generation / Signal-Driven Prospecting / Credit Decision Assistant / Strategy Operations / Portfolio Early Warning / Policy Compliance Audit"，与旧 page 字面一致；`ArchiveAgentShell.tsx:35` 渲染 `{code} · {eyebrowLabel}`（去掉旧 `{key.toUpperCase()}` 短版） |
| A-017 Today .card.warm.sheet-card Stage 3 必做 | 完整 sheet-card 结构 + 4 主题 sweep | **LANDED** | `today/page.tsx:82-135` 完整实装；`views.css:240-319` scoped 新 CSS；4 主题 Playwright 截图齐全 |

4 条决策本批全部落地，映射一一对应，无遗漏。

## Top 3 Gap（Stage 4 锚点）

1. **旧 `app/<agent>/page.tsx` 6 文件仍在（按 onboarding §3.4 刻意保留）** — 307 redirect 虽生效，但文件体积浪费 + 构建双路径风险持续累积。Stage 4 需单独 cleanup commit 批删，同时更新 `next.config.ts` 删除 legacy redirect。onboarding 起草须显式列该 cleanup 为 Task 并明述 A-012.D SHA 合规路径（新 commit 批删，不 rebase）。

2. **Task E runtime console error `fetchPresets ECONNREFUSED 127.0.0.1:8000`**（commit body L74 worker 自承 "pre-existing, unrelated"，因 backend 未起）— 体验层默读：客户打开页时若后端未就绪，console 有红字 + `fetchPresets` 失败可能污染用户感知。Stage 4 需把 `fetchPresets` 外加 try/catch + 友好 degraded state UI，或在无 backend 时注入 mock preset。非 blocker 但属"证据支撑"纪律要求（CLAUDE.md §1 "字段填不了标未填"）。

3. **Archive `.archive-h` 44px vs spec `hero-h1` `clamp(42px,5vw,82px)` 不一致（diagnosis §2.2 指出的 spec gap）** — 本批 Task E 仅动 eyebrow/lede 文案，`.archive-h` 44px 固定值未收敛到 spec `clamp()`。Stage 4 需由主 CLI 亲操补 `platform-shell-v1.md` Archive 子路由 header 规格章节，确认 44px 是 canonical 还是回归 spec。worker 不越权改 spec。

## 亮点

- **6-agent verbatim 文案迁移**：description + eyebrowLabel 从旧 6 page 字面复刻，reviewer spot-check report（`"读入企业材料包,按「普惠授信申报及审查审批意见表」节段自动撰写,未能填写字段显式标注。"` 完全一致）+ channel（`"从细微信号（中标/专利/扩产/获奖/认证）中挖出小而美的公司 — 5 路并行信号搜索 + 信号密度排序"` 完全一致）均无 paraphrase。commit body 标 "no paraphrasing" 诚实达标。严格执行 CLAUDE.md §1 "证据支撑，禁止编造"。

- **HeaderSlot Context 做 cross-client 解耦**：archive/[agent]/page.tsx（**server** component）持静态 `def.description`，传入 `ArchiveAgentShell`（**client** component）挂 Provider；credit workspace client 通过 `useHeaderSlot()` 注入动态 SEGMENT_META description，cleanup 清理 slot；其余 5 agent 不消费 slot 自然 fallback 到静态。设计小而完美，既不把 5 agent 强行 dynamic 化，也保留 credit 动态 segment 的独特需求。A-015 "A 默认 + B 特例" 决策精确落地。

- **Task D 诚实 NO-REGRESSION**：未发现双层顶栏即如实标 `FRONTEND-TASK-D-NO-REGRESSION`（非 `-DONE`），commit body 列 4 链路 `mastheadCount=1` 明证 + src 静态分析 0 legacy hrefs。不为了"完成 Task D"而造工作量，也不为了过 review 而虚报修复。A-011 + CLAUDE.md "不要谄媚" 纪律达标。

- **4 主题 playwright sweep 作为 design token isolation proof**：Canvas / Matcha / Dusk / Crimson 4 截图齐全，sheet-card gradient 跟 `--g6` 主题 token 切换，未写死 hex。A-014 ink-14/28 替代方案在 Crimson（色阶对比最强）下的 imperceptibility 被 playwright 证据链覆盖，而非仅靠 commit 自白。

- **`views.css +197` 全 scope `.v-today`**：新 CSS 零外泄到其他 view；`.card` / `.warm` / `.sheet-card` 等通用 class 未污染 tokens.css 或 globals.css。CSS modularization 纪律模范。

- **Signal 链路完整**：D → E → F 每 Task 单 signal，与 onboarding §2.4 / §3.5 / §4.5 一一对应；主 CLI 可按 ACK 每 Task GO，mesh await semantics 精确落地。

## Scorecard 预估

**前端 Shell**：`Stage 2 APPROVED 2026-04-19` → **`Stage 3 ext APPROVED 2026-04-19`**

comprehensive % 维持 `—`（前端表无百分比列）；state cell 升级从 "Stage 2 APPROVED" 推进到 "Stage 3 ext APPROVED"。

Stage 3 extension 定义 = Task A/B/C（Stage 3 首批，290ede2 已合）+ Task D/E/F（本批 9486d00）= Stage 3 整体 APPROVED 完成。原 `docs/scorecard/GLOBAL.md:34` 备注 "Stage 3 首批 = workspace C 方案解耦" 可更新为 "Stage 3 ext APPROVED；Stage 4 聚焦 legacy cleanup + spec gap 收敛"。

## Required Actions

无（APPROVED）。

## 下一阶段 onboarding 起草时采纳

- **Stage 4 legacy cleanup**（Top Gap #1）：单 Task 批删旧 `app/<agent>/page.tsx` 6 文件 + 同步改 `next.config.ts` 去 legacy redirect；commit body 必须 Playwright 回归 `/credit → 404 or /archive/credit` 一条验证路径完整性
- **fetchPresets degraded UX**（Top Gap #2）：backend 未起时 console 静默 + UI 不退化，不依赖外部服务首屏可用
- **Archive 子路由 header spec 收敛**（Top Gap #3）：主 CLI 补 `docs/design/platform-shell-v1.md` Archive 子路由条款，明确 `.archive-h` 是 44px canonical 还是回归 `clamp(42px,5vw,82px)`；然后 Stage 4 按最终 spec 对齐
- **无障碍审计（accessibility）**：sheet-bar 仅色彩 + 宽度表达进度，屏幕阅读器需 `aria-valuenow` / role="progressbar"；Stage 4 补 a11y pass
- **窄屏响应式 sheet-card**：当前 `.v-grid-3` 未在 `@media (max-width: X)` 下重排 sheet-card，窄屏 iPad 横屏观察验证待补（非银行主场景但对外 demo 有风险）
- **4 主题 × 3 view 12 截图视觉回归 CI 化**：本批 Task F 手动跑 playwright 脚本获 4 截图，Stage 4 可考虑 `@playwright/test` 快照做 CI baseline diff，避免后续迭代手工

## 主 CLI 落地动作

1. **升级 scorecard**：`docs/scorecard/GLOBAL.md:34` 前端行 "Stage 2 APPROVED 2026-04-19" → "Stage 3 ext APPROVED 2026-04-19"；附注从 "Stage 3 首批 = workspace C 方案解耦" 更新为 "Stage 3 ext 全绿：Task D/E/F 2026-04-19"
2. **发 APPROVED signal**：`Signal: FRONTEND-STAGE-3-EXT-APPROVED` 告知 worker，授权 `WINDOW-CLOSED-CLEAN`
3. **起草 Stage 4 onboarding**（可选 / 与用户确认优先级）：按 "下一阶段 onboarding 起草时采纳" 5 项整合为 Task 清单
4. **decisions-log.md 追加 A-014~017 status "LANDED at 9486d00"**（可选 / 作为决策闭环追踪）
