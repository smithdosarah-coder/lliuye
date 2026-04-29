---
sub-agent: production-shape
cat: [0, 13, 14, 15]
date: 2026-04-29
round: 1
---

| Cat | file:line | 证据 (≤80 char) | Keep / Revert / Rewrite |
|---|---|---|---|
| 0 | web/src/app/today/_components/TodayContent.tsx:21-91 | 今日是 KPI dashboard (FeedCard / BoardCard / EventTimeline) · 无客户管线 · 无跨 agent 调度入口 | Rewrite |
| 0 | web/src/app/today/_components/MorningBrief.tsx:28 | HERO_WORD="今日看板" · 定性是 dashboard · 非 RM workbench ("客户经理工作台") | Rewrite |
| 0 | web/src/app/archive/page.tsx:28-38 | archive 是 6 agent portal grid · lede "每一位助手是一间独立工作区" · 无 workbench 概念 | Rewrite |
| 0 | web/src/app/archive/credit/_components/CreditWorkspace.tsx:88-115 | CreditWorkspace 独立 state machine · runDecision POST 直调 /api/credit/decision · 不消费 Agent6 ReportJSON upstream handoff | Rewrite |
| 0 | web/src/app/archive/credit/_components/CreditWorkspace.tsx:1568-1635 | EmptyState CTA §6 注释说"来自 Agent6 handoff" · 但实际 onClick onPrimary 只走 runDecision · 无 handoff data flow | Rewrite |
| 0 | web/src/app/today/_components/PriorityQueue.tsx:9 | click 注释"→ /archive/<agent>?customer=<id>" · 跳 6 独立 workspace · 无 cross-agent 任务串联 | Rewrite |
| 13 | agent_riskctrl/api.py:1-39 | riskctrl 后端无 export_docx / export_xlsx 端点 · 但 RiskctrlWorkspace 前端已调 exportDocxApi · 404 on prod | Rewrite |
| 13 | web/src/app/archive/channel/_components/ChannelWorkspace.tsx:1717-1724 | 导出按钮 OUTPUT_ACTIONS 全 4 个均无 onClick handler · 纯 UI dead button · 后端有 /api/channel/export_xlsx + export_docx | Rewrite |
| 13 | web/src/app/archive/credit/_components/CreditWorkspace.tsx:1784-1786 | credit export_docx 失败只 console.error · 无 recordLiveFail / fallback banner · 不一致于 compliance/alert/riskctrl | Rewrite |
| 14 | web/src/lib/agents.ts:47 | `accent: "var(--color-ink)"` (report agent) · 旧 Letterpress token · 违 §7 红线 | Revert |
| 14 | web/src/lib/agents.ts:60 | `accent: "var(--color-brass)"` (channel agent) · 旧 Letterpress token · 违 §7 红线 | Revert |
| 14 | web/src/lib/agents.ts:114 | `accent: "var(--color-brass-dim)"` (compliance agent) · 旧 Letterpress token · 违 §7 红线 | Revert |
| 14 | web/src/components/viz/VerdictBadge.tsx:12 | `bg: "var(--color-brass)"` + L27 `--color-ink` + L45 `--color-brass-glow` · 3 legacy token 消费 | Revert |
| 14 | web/src/app/globals.css:12-13 | 注释明言"旧 6 Agent 页面继续消费 --color-ink / --color-brass" · legacy 段未标 TODO-remove | Keep (暂) |
| 14 | web/src/components/viz/PipelineRail.tsx:42-44 | `--color-ink` / `--color-ink-muted` 3 处 · 非 Ink 主题品牌用途 · Letterpress 残留 | Revert |
| 15 | git log main..chore/l0-infra | 1 commit ahead (STEP-2-FIRE-DISPATCHED) · 未 merge 到 main · ECS 未取 | Keep (待 Step 2 完成后 merge) |
| 15 | git log chore/l0-infra..main | 10 commits ahead in main · chore/l0-infra 落后 main 10 commit · branch 严重分叉 | Rewrite |
| 15 | git (inferred ECS state) | ECS 跑 main · main 含 10 commits chore/l0-infra 没有 · dev 分支未同步 morning sync 规范 (CLAUDE.md §13.4) | Rewrite |

---

## Cat 0 · 产品形态 verdict (≤200 词)

**当前形态**: 6 showroom。今日页 (`/today`) 是 KPI dashboard（FeedCard + BoardCard + EventTimeline），Archive 页是 6 agent 独立入口 portal，6 个 workspace 是互不联通的单页应用——这是典型 6 showroom 形态，距 north-star RM workbench 有根本性差距。

**走歪表征 5 处**:
1. `/today` 标题硬编"今日看板"，无客户管线视图，无跨 agent 调度入口（north-star §3.1 要求"客户管线 + 今日待办 + 跨 agent 调用入口"）
2. Archive portal lede："每一位助手是一间独立工作区"——产品自我定性为孤岛
3. Agent6 → Agent3 handoff 数据流未串：CreditWorkspace EmptyState 注释声称"来自 Agent6 handoff"，实际 onClick 直调独立 /api/credit/decision，不消费 ReportJSON
4. PriorityQueue click 跳 6 个独立 workspace URL，无任务上下文传递
5. Archive 页无 workbench 二级导航逻辑，6 tile 全平铺等权，无业务流程串联感（Agent1→6→3→4→5 的 RM 工作流不可见）

**修正方向 (引用 north-star §3.1)**: `/today` 必须重写为"客户管线 + 今日待办 + 跨 agent 调用入口"三区布局；Agent6 → Agent3 需定义 ReportJSON schema 并让 CreditWorkspace EmptyState 真消费，两步串联才算 handoff 到位。
