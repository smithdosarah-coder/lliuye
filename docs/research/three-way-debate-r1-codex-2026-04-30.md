# 三方辩论 R1 · Codex 独立前端优化方案

> Codex high reasoning · sandbox read-only · 主 CLI 落盘代写
> 任务 ID: b5xrnwaq9 · 完工 ~25 min

## 1. 真痛点

1. **P0 `/today` 还不是闭环工作台**
   - 证据: north-star 要 `/today` 整合客户管线/待办/跨 agent 调用入口 (docs/reset/north-star.md:85)
   - 但 AI 助手卡整卡跳 `/dispatch` (web/src/app/today/_components/TodayContent.tsx:29)
   - 设计源是 AI 助手区承接 Agent6/Agent3 状态 (design_mockups/rm-assistant-final-2026-04-19.html:2934,2945,2981)
   - 影响: RM 离开上下文找能力

2. **P0 Agent6→Agent3 能力已有 · 但未成为 `/today` 主路径**
   - 证据: Credit workspace 已有 `runDecisionWithAgent6Handoff` · 拉报告 / POST `/api/credit/handoff/from_report` / 注入 `report_json` 决策 (web/src/app/archive/credit/_components/CreditWorkspace.tsx:237,257,279,322,500)
   - v2 方案目标是在 `/today` modal 跑通单链路 (docs/research/competitor-action-plan-v2-final-2026-04-30.md:92,96)
   - 影响: RM/审贷员看不到最核心 Evidence-First 闭环

3. **P0 任务数与 handoff 任务卡割裂**
   - 证据: MorningBrief 仍用 `TICKET_FALLBACK_COUNT = 4` (web/src/app/today/_components/MorningBrief.tsx:37,146)
   - 但 warroom store 已能订阅 `handoff.requested` 建 ticket (web/src/app/warroom/_store/ticket-store.ts:271,274)
   - `report_to_credit` recipe 已定义 (web/src/lib/store/handoff-catalog.ts:38-48)
   - 影响: RM/审贷员无法从今日页信任待办优先级

4. **P1 Agent3 评分缺分客群表达**
   - 证据: north-star 仍写 Agent3 四维评分 (docs/reset/north-star.md:19) · 竞品研究指出科创六维/三主看三辅看是真银行方法论 (docs/research/competitor-borrow-2026-04-30.md:72-75)
   - 影响: 审贷员/风险经理觉得"不懂科创"

5. **P1 `/today` 局部仍是静态 mock · 生产可信度不足**
   - 证据: today fixture 标 Stage 3+ 才切 API (web/src/lib/mock/today.ts:2-4) · TodayContent 直接消费 `TODAY_RUNNING_SHEETS/TODAY_IDLE_SHEETS` (web/src/app/today/_components/TodayContent.tsx:9-11)
   - 影响: RM/合规官/风险经理难区分实时状态与演示状态

## 2. 推荐 action

| # | Action | 工程量 | DoD | 风险 | Phase |
|---|---|---|---|---|---|
| C1 | Today 单链路工作台入口 | 1 周 | `/today` 可继续/启动 Agent6→Agent3 · 复用现有 credit handoff API · `/archive/[agent]` 保留 deep-link | 复制 workspace 状态 | B-3 |
| C2 | Handoff 任务卡真接入 | 0.5-1 周 | `report.completed` 自动生成 `report_to_credit` 待授信卡 · 带 `report_id/ReportJSON ref` · today/warroom 数字一致 | 只做假 kanban | B-3 |
| C3 | 修正 Today AI 助手卡路由 | 0.5 天 | AI 助手卡进 `/archive` 或具体 agent/session · 消息卡继续 `/dispatch` | 低 · 需保留 mockup 视觉 | B-1 |
| C4 | Hero minimum 真指标 | 0.3 周 | 待办数来自 ticket-store · 预警数来自 event-bus · 无源时显 fallback 标识 · 不显示效率提升/转化率 | hydration/localStorage | B-1 |
| C5 | Agent3 segment-aware 入口 | 1-1.5 周 | 科创/对公/普惠 selector + yaml rubric + RM override · 生命周期由确定性字段推断 (非 LLM 现场判) | rubric 变展示 mock | B-3 |
| C6 | Agent1 explainable similarity 前端露出 | 1 周 | 候选卡显示 industry/geo/scale/similarity 四维证据与内源相似客户 · 不扩 12 场景 | 数据源不足 | B 末 |

## 3. 反对借鉴 / 不做

1. **不做全 6 Agent 一步 modal 化**: v2 已拍单链路优先 (docs/research/competitor-action-plan-v2-final-2026-04-30.md:147) · 全量会拖垮 Phase B · `/archive/[agent]` 不应删除 (docs/reset/north-star.md:117)
2. **不做装饰 KPI**: 无真实事件口径的"效率提升/转化率"反 Evidence-First · v2 已限定只做待办数/SLA (docs/research/competitor-action-plan-v2-final-2026-04-30.md:64,117)
3. **不抄竞品单页 HTML / 5 角色 / 五融产品**: 竞品技术栈和角色边界不适配 · 我们的核心是 RM workbench + 6 Agent + 中文信贷证据链 (docs/research/competitor-borrow-2026-04-30.md:108-121)

## 4. Codex R1 verdict (≤ 200 字)

不硬改全站 · 只补真痛: 把已存在的 Agent6→Agent3 handoff 收进 `/today` 单链路工作台 · 接通 handoff 任务卡与真待办数 · 修正 AI 助手卡路由; Agent3 做分客群 rubric · Agent1 只露出可解释 similarity。不做全 6 modal · 装饰 KPI · 竞品角色/技术栈照搬。
