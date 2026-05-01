# 三方辩论 R2 v2 · Codex 互检主 CLI R1 v2 + Gemini R1 v2

> Codex high reasoning · sandbox read-only · 主 CLI 落盘代写 · 任务 ID byo5w849m
> 2026-05-01 · PM 反硬改 mindset: 不硬改 / 有证据 / 已最优不改 / 保持产品特色

## 1. 对主 CLI R1 v2 verdict

**接受 90%。** 主 CLI 接受 Codex R1 v2 6 bug + 7 action + 4 不做是正确的: 这些不是审美偏好 · 而是工作流断链 / 证据假消费 / 状态丢失 / 审计不可靠。主 CLI 已明确"接受 Codex R1 v2 100%" (`docs/research/three-way-debate-r1-v2-mainCLI-2026-04-30.md:15`)。

**唯一 dissent: A5 不应 Phase B 完整做。** 6 Agent 跨冲突 UI 有价值 · 但主 CLI 自己也记录"spike + Phase C 完整" (`docs/research/three-way-debate-r1-v2-mainCLI-2026-04-30.md:57`)。Codex 仍坚持: Phase B-3 只做冲突显性化 spike (冲突来源 / 影响客户 / 推荐 owner / 可跳 Warroom) · 完整仲裁器推 Phase C。理由: 当前 `handoff.requested` 已经是 event-bus + warroom 协作骨架 (`web/src/app/dispatch/_components/ComposerBar.tsx:267` · `web/src/app/warroom/_store/ticket-store.ts:274`) · 但 audit 还只是内存 history (`web/src/app/audit/AuditView.tsx:57`)。**没有可靠账本前做"完整仲裁"会变成漂亮但不可追责**。

## 2. 对 Gemini R1 v2 verdict

### 视觉

**agree 80%。** 全屏渐变退到 `#F7F9FC` / 中文优先字体栈 / 删装饰斜体 / 圆角收敛到 ≤8px · Codex 同意。现有 CSS 渐变密度确实高 (`views.css` 多处 linear-gradient · `web/src/app/views.css:111, 481, 628`) · 字体 token 也把 display/sans 放在英文字体变量前 (`web/src/app/tokens.css:25, 26`) · 且保留 `--italic` (`web/src/app/tokens.css:27`)。这不是"跟竞品" · 是金融专业场景降噪。

**保留 dissent**: 不做全站去特色化。panel/canvas/whiteboard 是产品特色 · 不应被 BI dashboard 化。

### IA

**Customer Ribbon: agree · 但折中。** Gemini "Agent 沦计算插件" 方向对 · Bug 1 证据强: customer 360 和 dispatch 都传 `?customer=` (`AgentTileStrip.tsx:89` · `ComposerBar.tsx:273`) · 但 workspace 内 `CustomerSelector` 未接 value/onChange (`CreditWorkspace.tsx:859` · `ReportWorkspace.tsx:603`) · 组件还声明"实际数据切换由上层处理" (`CustomerSelector.tsx:7`)。

**折中方案**: Phase B-1 做 CustomerContextGateway + 顶部只读 Customer Ribbon · 但**不删除所有 selector** · 保留 demo/异常切换入口 · 避免硬改现有演示能力。

**IM 降级: partial dissent。** Gemini 说 `/today + Kanban` 做唯一真理源 · IM 降级旁路 (`gemini-r1-v2:86`) · 方向对 · 但**不能砍 dispatch**。现有 dispatch 已承载 `/handoff` 和 `handoff_card` (`ComposerBar.tsx:276, 282`)。Codex 建议: 任务真理源归 `/today + warroom` · dispatch 保留为协作会话 + command surface · 用 `⌘K` 汇总 `/run /handoff /assign` · 而不是从 IA 上废掉。

### UX

**Stage-aware Primary Action: agree · 与 Action Card 互补。** Gemini 指客户 360 缺 Primary Action 是新真痛。它**不冲突** v3 Action Card · 反而应作为 Action Card 组件族的"顶部主卡": stage 决定 CTA · 如"提交授信审查 / 打回补件 / 发起合规复核"。

**Report Document + Riskctrl IDE: Phase C。** Gemini 对空间分配的判断对: Report 空 / Riskctrl 挤。但 Riskctrl 已是复杂三栏 workspace · 右侧承载 DSL/KS/Sample (`RiskctrlWorkspace.tsx:7, 1299`)。Phase B 做局部扩容和默认 tab 优化 · **全屏 Document/IDE 大改推 Phase C** · 避免把 B 的 P0 bug 资源挤掉。

### 中文金融

**agree · 工程量小。** 金额千分位 / Tabular Figures / 右对齐已在 v3 action 内 · v4 应加 **"大白话结论"**。Riskctrl 当前大量暴露 KS/AUC (`RiskctrlWorkspace.tsx:690, 724, 1522`) · Gemini 的"审贷官非算法师"判断成立。实现只需在 metrics adapter 增加 `plainDecisionSummary` · UI 显示"建议通过 / 需补充抵押 / 违约概率 < x%" · 不动底层模型。

## 3. Codex R2 加补: 三方都漏的真痛

**Evaluation 飞轮未闭环。** R1 都在谈 UI/IA · 但 Phase B-1 数据飞轮还有发布闸门风险。`evaluation/README.md` 规定改 prompt/逻辑前先跑基线 · 并定义 `baseline_target` / `blocker_threshold` (`evaluation/README.md:5, 11`)。但文件清单显示**多个 Agent "待首跑"** · 只有 riskctrl/report/alert 有部分基线 (`evaluation/README.md:37`)。

这会直接影响 C8 live evidence adapter: **没有评估基线 · 无法证明 "fixture → live evidence" 没有让 hallucination/evidence_rate 退化**。

**新增 action: C14 Evaluation Baseline Gate。** Phase B-1 前置跑 6 Agent baseline · 若 agent1/3/5 仍待首跑 · 至少补 smoke baseline + evidence_rate/hallucination_rate 红线 · 接入 CI 或 release checklist。否则 Evidence-First 只是 UI 口号。

## 4. 对 Codex R1 v2 6 bug 的降级建议

**不降级 Bug 1/2/3/4/6。** 客户上下文 / fixture evidence / dispatch 双发 / rejected 消失 / ScanCTA 幽灵 API 都必须 Phase B 修。证据分别见 `AgentTileStrip.tsx:89` · `fixtures.ts:7` · `ComposerBar.tsx:178+216` · `TicketDrawer.tsx:139` · `ScanCTA.tsx:78+102`。

**Bug 5 audit 分阶段。** B-3 明示 "session-only demo" · Phase C 接 `/api/audit`。原因是 event-bus 注释已说明 history 只做前端实时协调 · 完整审计由后端 `/api/audit` 提供 (`event-bus.ts:14`)。

## 5. R2 verdict

接受主 CLI R1 v2 **90%**: 6 bug + 7 action 全接 · A5 只反对 Phase B 完整做 · 坚持 B-3 spike + Phase C 完整。

接受 Gemini R1 v2 **80%**: 视觉降噪 / Customer Ribbon / Primary Action / 大白话结论全接 · 反对"一刀切删 selector / IM 降级到边缘 / Phase B 大改 Report+Riskctrl 布局"。

新增 **C14 Evaluation Baseline Gate**: Phase B-1 必须补 6 Agent baseline 红线 · 否则 live evidence 接入后无法证明 Evidence-First 真的成立。
