# 三方辩论 R2 v2 · 主 CLI 综合 Codex R2 v2 + Gemini R2 v2

> 主 CLI 看 Codex R2 v2 (byo5w849m) + Gemini R2 v2 (主 CLI 直接控浏览器抓 · 第 4-5 turn) 后综合
> 2026-05-01 · PM 反硬改 mindset 严守

## 1. 看 Codex R2 v2 verdict

### Codex 接受主 CLI 90% / Gemini 80%
- Codex 6 bug + 7 action 全 reaffirm · 主 CLI 100% 接受 (R1 v2 doc 已写)
- Codex 反对 Gemini 一刀切删 selector / IM 降级到边缘 / Phase B 大改 Report+Riskctrl 布局 — **主 CLI agree** (这些 Phase C 推 OK)

### Codex R2 v2 game-changer 加补: C14 Evaluation Baseline Gate
- **三方都漏的真痛**: Phase B-1 数据飞轮要做 live evidence adapter (Codex C8) · 但 6 Agent baseline 多个"待首跑" · 没 evidence_rate / hallucination_rate 红线
- **影响**: 没 baseline · 接 live evidence 后无法证明"fixture → live"没让 hallucination 退化 · Evidence-First 只是 UI 口号
- **主 CLI verdict**: ✅ 接受 C14 — Phase B-1 必做 (跑 6 Agent baseline · 接入 CI 或 release checklist · 时间 ~3-5 天)

### Codex 唯一反对 (A5 完整 vs spike)
- Codex R2 v2: A5 必须降级到 Phase B-3 spike (冲突来源/影响客户/推荐 owner/可跳 Warroom · 0.3 周) + 完整仲裁推 Phase C
- 理由: 当前 audit 还只是内存 history (event-bus.ts:14) · 没可靠账本 · 完整仲裁会变成"漂亮但不可追责"
- **主 CLI verdict**: 接受 Codex 降级 (PM 反硬改 + Codex evidence 强 · audit 没接后端前完整仲裁不可追责)

## 2. 看 Gemini R2 v2 verdict (7 决断 verbatim)

### Gemini 接受三方共识 5/7 决断 (1+2+3+5+7)
- 1 黑洞撤 / 2 全屏渐变折中 / 3 /today 单链路 / 5 Kanban 拒件+红牌 / 7 千分位+Tabular: 三方完全一致
- **主 CLI verdict**: ✅ 全接 (R3 final)

### Gemini 决断 4 (Customer ID 全局 + /archive 降级历史/后台)
- 与 Codex C7 + Gemini Customer Ribbon 互补 · 主 CLI A3 (弱化 /archive) 升级
- **主 CLI verdict**: ✅ 接受 + 折中 (per Codex R2 v2 · "Phase B-1 做 CustomerContextGateway + 顶部只读 Customer Ribbon · 不删除所有 selector 保留 demo/异常切换入口")

### Gemini 决断 6 (A5 完整 + Actionable)
- Gemini 站 A5 完整 (审贷官一键裁定) · 但 Codex R2 v2 反对 (没 audit 账本 · 不可追责 · 降级 spike)
- **主 CLI 裁决**: **分阶段** (Codex 路径)
  - Phase B-3 做 spike (0.3 周): 冲突显性化 (来源/影响客户/推荐 owner/可跳 Warroom)
  - Phase C 做完整 (含 audit 账本接 /api/audit + 审贷官一键裁定 + 跨 Agent 冲突 schema)
  - 理由: 三方权重 PM 反硬改 (主 CLI · Codex · Gemini 都反硬改 · 这是核心)
  - 但**Gemini 视觉权重高** · Phase B-3 spike 也要做出 "⚠️ 冲突待仲裁" 视觉提示 (per Gemini · 不只 backend 数据)

## 3. 主 CLI R2 v2 加补 (Codex + Gemini 都没提)

### 加补 1: 关于 v3 → v4 演进的 PM 视角排期

v3 14 action + Codex R1 v2 7 action + Gemini R1 v2 3 新点 + Codex R2 v2 加补 C14 = **总 22-25 action**

- **必做** (PM 反硬改 + 三方 unanimous): 13 action
  - Codex 6 bug 修 (C7-C12) + C13 抽 hook + C14 baseline gate
  - 主 CLI A1 (千分位 Tabular) + A2 (single link modal · 与 C1 合并) + A3 (Agent 下沉 · 与 Customer Ribbon 合并) + A4 (Action Card) + A6 (登录黑洞)
  - Gemini Customer Ribbon (与 A3 + C7 合并)
- **分阶段** (PM 反硬改 · spike + Phase C 完整): 1 action
  - A5 (跨冲突 UI 仲裁): B-3 spike + Phase C 完整
- **可选 / 可推 Phase C** (主 CLI + Codex 不强推 · Gemini 推但 Phase B 资源紧): 3 action
  - Stage-aware Primary Action 巨型按钮 (Gemini · 与 Action Card 互补 · 可 B-3 顺带做 OR Phase C)
  - Report 全屏 Document + Riskctrl IDE 三列 (Gemini 视觉重构 · Phase C 推)
  - 大白话结论 (Gemini · "违约概率 < 2.8%" 替 KS/AUC · plainDecisionSummary metrics adapter · B-3 顺带做)
- **撤** (Codex R2 v2 反对 + 主 CLI 同意): 3 action
  - 一刀切删 CustomerSelector (Codex 反对 · 保留 demo/异常切换入口)
  - IM 降级到边缘 (Codex 反对 · IM 保留为协作会话 + command surface)
  - Phase B 大改 Report+Riskctrl 布局 (Codex 反对 · Phase B 局部扩容 + 默认 tab 优化 · 全屏 Document/IDE 推 Phase C)

总 必做 13 + 分阶段 1 + 可选 3 = **17 action** (撤 3 个 v3/Gemini 提的 vs Codex 反对)

## 4. 主 CLI R2 v2 verdict

### 接受度
- 接受 Codex R2 v2 100% (含 C14 加补 + A5 降级 spike)
- 接受 Gemini R2 v2 7 决断 6/7 (决断 6 A5 完整 → 改 spike + Phase C 完整 · 但 spike 必含 Gemini 视觉提示)
- 接受主 CLI R1 v2 加补 A5 → 改分阶段 (vs R1 v2 完整 1 周 · 现 spike 0.3 周 + Phase C 完整 1.5 周)

### 关键变化 vs R1 v2 + 之前 v3
- **加 C14 Evaluation Baseline Gate** (三方都漏 · 必做)
- **A5 降级 spike + Phase C 完整** (Codex evidence 强 · audit 没接后端前完整仲裁不可追责)
- **Customer Ribbon 折中** (顶部只读 + 不删 selector · 保留 demo/异常切换)
- **撤 3 个 Codex 反对项** (一刀切删 selector / IM 边缘化 / Phase B 大改 Report+Riskctrl)

### 总 Phase B 工程量重估
- v3 ~5 周 (14 action)
- v4 ~6.5-7 周 (21 action) — R3 v3 主 CLI 估
- v4 final 17 必做+分阶段+可选 action = **~5.5-6 周** (含并行 ~4.5-5 周 wall-clock) — 比 v3 R3 估 short (因为撤 3 + 分阶段 A5)

## 5. R3 next step

主 CLI R3 综合 R1 v2 + R2 v2 三方 → 出 **完整版方案 v4 final** (`docs/research/FINAL-FRONTEND-OPTIMIZATION-PLAN-V4-2026-05-01.md`):
- 17 action 详细排期 (B-1 / B-3 / B 末)
- Phase C action 列出 (3 个推 Phase C 项)
- PM 拍板项 (8-10 项)
- 退回命令引用 git tag `phase-a-exit-bugfix-2026-05-01`
