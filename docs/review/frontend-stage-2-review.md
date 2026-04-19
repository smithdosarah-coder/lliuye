# Frontend Platform Shell v1 · Stage 2 Review

**日期**：2026-04-19
**reviewer**：主 CLI
**onboarding**：docs/onboarding/frontend-shell-phase-1.md
**HEAD**：`e5dad4b`
**Signal**：FRONTEND-STAGE-2-READY-FOR-REVIEW

## Verdict
**CONDITIONAL-APPROVE** — 3 Task 冒烟实测 + DoD 基本全覆盖，但 Task B "老 AppShell 弃用标记" 和 Task C "动态路由复用策略变更未走 Q/A" 两条需本窗收口。不阻塞 Stage 3 但不合并到 `main`。

## Task 对账

### Task A · token 层 (`a4e609e`)
| DoD | 状态 | 证据 |
|---|---|---|
| 4 主题 `[data-theme]` + canvas 默认 | PASS | tokens.css L12-117，canvas 在 `:root`，matcha/dusk/crimson 选择器齐 |
| `--g0..--g7` / accent / ink / chalk / safe | PASS | L13-25 齐，4 主题各自 override |
| 32 档透明度 | **PARTIAL** | 实得 9 档 `--ink-*` + 20 档 `--ch-*` = 29 档；spec §3.3 原本就 "10+22"，onboarding "32 档" 表述偏差 |
| 字体栈 6 变量 | PASS | L27-32 display/sans/italic/mono/cjk/cjkserif |
| `--r-md 18px / --r-lg 26px` | PASS | L34-35 |
| `@import './tokens.css'` | PASS | globals.css L14 |

### Task B · AppShell 骨架 (`1cee58b`)
| DoD | 状态 | 证据 |
|---|---|---|
| AppShell 组装 Desk + Masthead + stage | PASS | AppShell.tsx L7-17 |
| Desk 4 节 + mock 驱动 | PASS | Desk.tsx 消费 `DESK_SECTIONS` + `DESK_QUICK_CREATE`；edge-hover 22px + 钉住 + Esc 全有 |
| Masthead logo + 4 tab + persona + 时钟 | PASS | Masthead.tsx L14-19；persona 显示"王哲·客户经理·华东"+ 20s 自更新 |
| ThemeSwitch 4 主题 + localStorage | PASS | ThemeSwitch.tsx `platform-shell-theme`，canvas 清 attr |
| layout.tsx 挂 `<AppShell>` | PASS | layout.tsx L12,76 |
| 老 AppShell 弃用标记 | **FAIL** | `web/src/components/layout/AppShell.tsx` 文件仍存在、无 deprecated 注释、无 JSDoc；onboarding DoD 明说"删除或注释标记" |

### Task C · 4 view + 路由迁移 (`e5dad4b`)
| DoD | 状态 | 证据 |
|---|---|---|
| 4 个 view page.tsx | PASS | today/dispatch/archive/warroom 全在 |
| `/archive/[agent]` 动态路由 | PASS | archive/[agent]/page.tsx + generateStaticParams 6 项 |
| `/` → `/today` | PASS | page.tsx `redirect('/today')`；冒烟 307 |
| 6 旧路由 → `/archive/[agent]` | PASS | next.config.ts redirects + 冒烟 6 条 307 全绿 |
| 4 mock fixture 齐全 | PASS | desk/today/dispatch/warroom 共 186 行 |
| 动态路由复用 6 现有 page 组件 | **DEVIATION** | onboarding L78 写"直接 import 现有 page 组件"；实装换成了 placeholder（明示 Stage 3 迁）。方向合理——现有页面有 `"use client"` + 顶栏耦合，直塞会破壳。但**未走 Q/A 入 decisions-log**，违反 onboarding §红区边界"发现问题 → 写 Q-NNN"约定 |

## 硬规则 & 红区

| 项 | 状态 | 说明 |
|---|---|---|
| R-A smoke-must-test | PASS | Task C commit 列 11 条 curl verbatim（含 tsc 0 err），Task A/B 标"无冒烟"并给出无下游消费方的合理理由 |
| R-B 一 commit 一 Signal | PASS | 三 commit 各一 trailer |
| 红区零触碰 | PASS | diff 全在 web/ + design_mockups/ + docs/，shared/ / agent_*/ / api_server.py 零动 |
| Google Fonts CDN→`<link>` 决策 | **MISSING LOG** | layout.tsx L66-73 + commit body 有说明，但未进 decisions-log；onboarding §七规定 spec/实装偏离必须走 Q-NNN |

## Top 3 Gap（Stage 3+ 锚点）

1. **Archive workspace 实际挂载策略**：Stage 3 需决定"现有 6 页直接 import vs 抽 business component 再塞"——后者干净但工作量大，前者快但 `"use client"` 与新壳兼容要验
2. **Font loading 统一方案**：当前 5 路字体并存（next/font × 5 + Funnel/Instrument via `<link>` + Noto/JetBrains via next/font），Stage 6 自托管时需收敛
3. **Theme scope 错位**：ThemeSwitch `setAttribute` 到 `body`，tokens.css 选择器用 `[data-theme=...]`；但 `globals.css [data-theme="ink"]` 老主题也挂 body——两套 data-theme 可能撞（canvas 切到 ink 行为未定义）

## 亮点 / 视觉吻合度

- 4 主题渐变值 1:1 来自 `design_mockups/tokens.css` L12-117，未走样
- Desk edge-hover 22px + pin + Esc 三态在 shell.html L1735-1831 有对应，实装完整
- Today view eyebrow + hero + 3 KV + 3 preview 五段结构与 shell-today-1440.png 骨架一致
- 1440 viewport 吻合度未经人眼复核；建议 Stage 2.1 补一次 `shell-today-1440.png` 对拍

## Required Actions（CONDITIONAL 解封条件）

1. `web/src/components/layout/AppShell.tsx` 顶部加 `/** @deprecated use @/components/shell/AppShell – platform-shell-v1 */` 或直接删除（无引用）
2. `docs/handoff/decisions-log.md` 补 Q-NNN/A-NNN：记录 "archive 动态路由 Stage 2 用 placeholder 而非直 import 现有 page 组件" 的理由
3. `docs/handoff/decisions-log.md` 再追一条：Google Fonts `@import url` 与 Tailwind v4 顺序冲突 → 改 layout.tsx `<link>`，字体策略 §3.2 不变
4. 可选：Stage 2.1 window 关闭前做 1440 viewport 视觉对拍（shell-today-1440.png vs 实际 /today），结果写 `docs/ui-snapshot-2026-04-19.md`

完成 1-3 后抛 `Signal: FRONTEND-STAGE-2-CONDITIONAL-RESOLVED`，我复核后升 APPROVED。

---

## Update 2026-04-19 14:52 · APPROVED

**Verdict**: APPROVED（升级自 CONDITIONAL-APPROVE）
**Resolver commit**: `b2b48fe chore(shell): resolve Stage 2 CONDITIONAL`
**Signal**: `FRONTEND-STAGE-2-CONDITIONAL-RESOLVED`

### Required Actions 对账
| # | 方案 | 状态 | 证据 |
|---|---|---|---|
| 1 | 老 AppShell.tsx @deprecated 或删 | PASS | b2b48fe 删 150 行整文件；走 CLAUDE.md 全局"可完全删除"而非 @deprecated；tsc --noEmit 0 err |
| 2 | archive placeholder 策略 Q/A | PASS | decisions-log Q-010/A-010：三阻理由（use client + 老顶栏嵌套 / legacy ink 主题撞色 / usePathname 语义错位）；副作用坦白"Stage 2→3 过渡期老页面离线" |
| 3 | Google Fonts @import→`<link>` Q/A | PASS | decisions-log Q-011/A-011：Tailwind v4 inline 展开触发 CSS "@import must precede all rules" 硬约束；试过 C 方案仍 500；字体策略 §3.2 不动 |
| 4 | 1440 viewport 视觉对拍（可选） | SKIP | Stage 2.1 或 Stage 3 前补 |

### Stage 3 入口锚
- **首批任务**：六 agent workspace C 方案解耦（workspace 业务组件抽离，页面解 `"use client"` 依赖 / 色系迁移）——A-010 Follow-up 已约束
- **过渡期风险**：/credit /channel 等 6 路 307 → placeholder 生效，老页面离线；客户 demo 前若暴露则回退 redirect 或挪到 `/archive-legacy/*`
- **字体收敛**：Stage 6 私有化自托管 woff2 时 Q-011 作废（`<link>` 与 `@import url` 都不再需要）
