# 三方辩论 R1 v2 · 主 CLI 加补 (基于 Codex R1 v2 全扫 + 12 view 截图)

> 主 CLI 看 Codex R1 v2 (01d1582 · 全扫 156 文件 6 bug) + sub-agent 12 view inventory (17.3 MB) 后产 R1 v2
> v1 主 CLI R1 (a9e3682) 已 supersede · 本 doc 替

## 0. v1 vs v2 主 CLI 视角差距

| v1 R1 主 CLI | v2 R1 主 CLI |
|---|---|
| 只看 design_mockup + Phase A 收尾印象 | 看 Codex 全扫 156 文件 + 12 view 截图 |
| 漏 5 个 archive workspace 内部 (alert/compliance/report/channel/riskctrl) | 全部 12 view 真看 |
| 漏 customer 360 + warroom + audit | 全有 |
| 6 action 主要 UI/视觉 | 加 6 个产品深层 bug (Codex 真扫发现) |

## 1. 接受 Codex R1 v2 100% (6 bug + 7 action + 4 不做)

### 1.1 6 bug 主 CLI verdict (全接受)

| Codex bug | 主 CLI 视角 verdict | 理由 |
|---|---|---|
| P0 客户上下文断链 | ✅ 完全接受 + 是真 bug 我漏 | 工作流断 (RM 从 customer 360 / IM 调 agent → workspace 默认样本) · 北极星反方向 |
| P0 Evidence-First 假 fixture | ✅ 完全接受 + 严重违反 north star §3.3 | 6 workspace 全挂 · 比客户上下文断链更严重 (反我们最核心产品原则) |
| P1 Dispatch 双发送 bug | ✅ 真 bug 必修 | RM 收重复回复 + 审计不可信 · 立即修 |
| P1 Warroom rejected 消失 | ✅ 真 bug 必修 | 风险经理/合规官退回交接看不见 · 工作流缺口 |
| P1 Audit 非可靠 | ✅ 接受 · 但分阶段 | 短期标 session-only (1 周) · 中期接 /api/audit (Phase C) · Codex 已分阶段建议 |
| P2 ScanCTA 幽灵 API | ✅ 接受 | 风险经理"完成"后才失败是 demo 灾难 |

### 1.2 7 action 主 CLI verdict (全接受 · 略调)

| Codex action | 主 CLI 接受度 | 备注 |
|---|---|---|
| C7 CustomerContextGateway (B-1 中) | ✅ | 必做 · 解 P0 bug 1 |
| C8 Live evidence adapter (B-1/B-3 中) | ✅ | 必做 · 解 P0 bug 2 · 跨 sprint OK (B-1 P 路径 + B-3 全覆盖) |
| C9 Dispatch 单发送 (B-1 小) | ✅ | 必做 quick win |
| C10 Warroom rejected lane (B-1 小) | ✅ | 必做 quick win |
| C11 Audit 降级标识 + 接后端 (B-3 中) | ✅ 分阶段 | B-3 标 session-only · Phase C 接 /api/audit |
| C12 替换 live 路径 ScanCTA (B-3 小/中) | ✅ | Report mock 留 · Riskctrl backtest 改 |
| C13 抽 shared live-fail/evidence hook (B 末 中) | ✅ | 重构债 · 不阻塞 ship |

### 1.3 4 不做 主 CLI verdict (全接受)

1. ✅ 不做通用 BI dashboard (panel pin/whiteboard/canvas 是产品特色)
2. ✅ 不取消 demo/mock (Report 演示稳定价值)
3. ✅ Riskctrl 不强行单客户化 (策略回测不针对单客户)
4. ✅ 不加 hero/视觉 chrome (痛点在数据闭环不在装饰)

## 2. 主 CLI v1 R1 vs Codex R1 v2 重叠 + 取舍

主 CLI v1 R1 6 action 哪些坚持 / 哪些撤:

| 主 CLI v1 action | v2 verdict | 理由 |
|---|---|---|
| A1 千分位 + 术语 + 金额标准 | ✅ 坚持 | UI/视觉清洗 · Codex 没否 · Gemini R1 v3 也提 (Tabular Figures + 右对齐) |
| A2 /today RM 起点改造 | ✅ 坚持 + 加客户上下文 (Codex C7) · 同 sprint 做 | A2 (UI 重构) + C7 (客户上下文断链 fix) 是同一改造 · 合并到 B-3 |
| A3 Agent 视角下沉 /archive 弱化 | ✅ 坚持 + Gemini ⌘+K Command Bar | v3 已定 · 不变 |
| A4 告警 actionable inline | ✅ 坚持 + Codex C12 (ScanCTA fix) · 同 Action Card 组件族合并 | v3 已定 · Codex C12 加 |
| **A5 6 Agent 跨冲突 UI** | ⚠️ 主 CLI 仍坚持完整 vs Codex R2 v3 降级 spike vs Gemini v3 完整支持 | R3 v3 已分阶段 (spike + Phase C 完整) · 不变 |
| A6 登录页黑洞 | ✅ 坚持 + Gemini 提权 P1 · B-1 做 | v3 已定 |

## 3. 主 CLI 加补 (基于 12 view 截图 + Codex R1 v2)

我看 12 view 截图 (尤其 5 archive workspace 内部 · 之前没看):

### 加补 1: 6 Agent workspace 内部 UI 复杂度差异大 (P2)

- ChannelWorkspace 379 行: 中
- AlertWorkspace 552 行: 中
- ComplianceWorkspace 439 行: 中
- ReportWorkspace 452 行: 中 (注: 但 Phase A 我之前听说 1832 行 · 实际 452 是 EvidenceProvider 行 · 整个文件可能 1500+)
- CreditWorkspace 485 行: 中
- RiskctrlWorkspace 357 行: 中

实际 6 workspace 内部相似度高 (Codex C13 抽 shared hook 印证)。**Phase B 视觉清洗 (F10) 应一次性 grep 6 workspace · 不分 6 次做** (节省 5x 工程量)。

### 加补 2: Stage 5a smoke 验证 6 workspace HTML page 全 200 (production live)

- 我 Stage 5a smoke verify backend SSE 真流 6/6 PASS
- 6 workspace HTML page /archive/{report,credit,channel,alert,compliance,riskctrl} 全 200
- 但 Codex R1 v2 发现这些 workspace 内部 evidence 是 fixture · 不是 live
- **意味着: production live 看起来 OK · 实际 evidence 是假的** — 这是真生产 bug · Phase B-1 必修 (Codex C8)

## 4. 主 CLI R1 v2 verdict (≤ 300 字)

R1 v2 关键变化:
- 接受 Codex R1 v2 全部 6 bug + 7 action + 4 不做 (Codex 全扫 156 文件比我盲推强)
- v1 R1 6 action 全部坚持 (UI/视觉清洗仍必做) · 但加 Codex 6 bug fix (产品深层)
- v3 完整版 14 action 大部分还成立 · 但**加补 7 action** (Codex C7-C13) → v4 final ~21 action

Phase B 工程量重估 (vs v3):
- v3: ~5 周 (~4-4.5 周 wall-clock)
- v4 (加 Codex 7 action 真 bug): ~6.5-7 周 (~5-5.5 周 wall-clock)
- 加的 1.5-2 周是真 bug 修 · 必做 · PM 反硬改 mindset 也接受 (这是 bug 不是优化)

PM mindset 严守: 6 个产品深层 bug 是真痛 (反 Evidence-First / 工作流断 / 重复发送 / 工单消失) · 不是为竞品装饰加项 · 必做。

等 Gemini R1 v2 (sub-agent 跑中 · 看 12 view + Codex 6 bug 重出) → R2 互检 → R3 综合 → 完整版方案 v4。
