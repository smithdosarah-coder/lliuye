# code-urgent (Batch 2 · 证据链前端化) Onboarding

**状态**：APPROVED
**发布日期**：2026-04-24
**Signal 入口**：`BATCH-2-DISPATCHED`
**前置**：
- Batch 1 已合流（archive 6 workspace 归位 + Agent3 financial_analyzer 接入 + 占位符 QC + Agent2/4 api + Agent2/4 /health + BLE001 清零）
- code-arch Batch 1 已落 `shared/evidence/protocol.py`，5 Agent evidence_pipeline 产出 `evidence_trail: [{source, snippet, ref_id, confidence, meta}]` + `unfilled_fields: string[]`（`AuditReport.to_dict()`）
- archive 6 workspace 已挂在 `web/src/app/archive/{channel,credit,alert,compliance,report,riskctrl}/_components/*Workspace.tsx`（canon 路由，非 legacy 顶层）

**Verdict**：后端齐、前端空。客户 demo 看不到"这句话出自哪"——演示效果 -50%。Batch 2 最高 ROI。

---

## 1. 背景与目标

### 现状

- **后端已出 `evidence_trail`**：`shared/evidence/protocol.py` `AuditReport.to_dict()` 统一 shape `{evidence_trail: [{source, snippet, ref_id, confidence, meta}], unfilled_fields: string[], findings, blocked}`。5 Agent 的 `evidence_pipeline.py` 全部继承，SSE 最终事件里已经带这些字段。
- **前端没消费**：archive 6 workspace 只把 LLM 正文段落渲染出来，`evidence_trail` 被丢掉，`unfilled_fields` 被 fallback 成空字符串 / 0。客户点开一条结论，拿不到"出处文件 + 第几段 + 置信度"的证据链。`ChannelWorkspace.tsx:540` 有个本地 `st.evidences` 的临时渲染，shape 和新 `evidence_trail` 不统一，需要归一。
- **QC Blocker 拦截字段**：Batch 1 code-urgent Task B 落了 `shared/qc/placeholder_guard.py`，后端把命中的字段标记为"未能自动填写"（或进 `unfilled_fields`），前端当前没差异化渲染——用户看不出是"还没生成"还是"被 QC 拦掉了"。

### 目标

让审贷员 / 客户经理在 demo 时**点一下**能看到"这句话出自材料第几页 / 哪条流水 / 哪份政策"；**低置信度**和**未能自动填写**在视觉上不能跟正常字段混。后端不动，只把已经吐出来的结构化证据在前端消费好。

**产品硬边界**：Evidence UI 是 demo 的主卖点之一（第 1 次有"可追溯 AI"），比"多一个 Agent workspace"优先级更高。

---

## 2. 你是谁

你是 **code-urgent** worker CLI · **Batch 2**，负责把 evidence UI 从 0 到 1 在 6 Agent archive workspace 全量上线。你是产品化手术台，不做架构重构（那是 code-arch 的事），不碰后端契约（那是 data-foundation/evaluation 的事）。

- Worktree：`D:/claude code/demo-code-urgent`
- 分支：`feat/code-urgent`（续 Batch 1 分支，无需新建）
- Upstream remote：`D:/claude code/credit_report_agent_work`

---

## 3. 本批次任务

### 🔴 Task A · archive evidence UI 组件（`ARCHIVE-EVIDENCE-UI-DONE`）

**目标**：新建统一的 `EvidenceTrail` 组件，消费后端 SSE 的 `evidence_trail` 字段；6 Agent archive workspace 全部挂载。审贷员点一条结论，弹 popover 看原文 + 出处。

**模块路径**：
- 新建：`web/src/components/evidence/EvidenceTrail.tsx`（TreeView / 折叠列表；props `{items: EvidenceItem[], onSourceClick?}`）
- 新建：`web/src/components/evidence/EvidencePopover.tsx`（点击 / hover 弹原文片段 + 出处链接；若 `source` 是 pdf，加 `#page=N` 跳页）
- 新建：`web/src/components/evidence/types.ts`（`EvidenceItem` / `EvidenceTrailResponse` 与后端 `AuditReport` 对齐，去掉 `meta` 里非渲染字段）
- 新建：`web/src/components/evidence/EvidenceContext.tsx`（React context provider，整 workspace 共享一份 evidence · 与 Task B HighlightCard 共用）
- 修改：`web/src/app/archive/{channel,credit,alert,compliance,report,riskctrl}/_components/*Workspace.tsx`（在"结论/输出"区域下方挂 `<EvidenceTrail>`；ChannelWorkspace 已有的 `st.evidences` 临时结构要迁到统一 shape，不要保留两套）
- 修改：`web/src/lib/api.ts`（SSE 消息类型扩 `evidence_trail?: EvidenceItem[]` + `unfilled_fields?: string[]`；ND / JSON 解包逻辑把这两个字段透传给 workspace）
- 新建：`tests/evidence-trail.spec.ts`（5 case 见下）

**消费契约**（与后端 `AuditReport.to_dict()` 对齐 · 见 `shared/evidence/protocol.py`）：
```ts
type EvidenceItem = {
  source: string;      // 文件名 / URL / 数据表名
  snippet: string;     // 原文摘录
  ref_id: string;      // 稳定 ID，正文可 [ref:xxx] 反查
  confidence: number;  // 0-1，< 0.5 视为低置信
  meta?: Record<string, unknown>; // 只渲染已知 key：page / paragraph_id / year / entity
};
```

**测试**（`tests/evidence-trail.spec.ts` · playwright 或 vitest + RTL · 5 case）：
1. 空 `evidence_trail` → 组件渲染"暂无证据"空态，不报错
2. 多源（≥3 source，含重复）→ 按 source 分组展开，折叠默认收起
3. 低置信度（`confidence < 0.5`）→ 项样式加 `.is-low-confidence`（灰 + 斜体），title 提示"置信度偏低"
4. popover 打开 / 关闭 → 点击条目弹出 popover，点外部 / Esc 关闭
5. 跳页 → `meta.page` 有值且 `source` 是 pdf → popover 链接 `href` 带 `#page=N`

**指标/验证**：
- 6 Agent workspace 都能看到 `<EvidenceTrail>` 区块（mock SSE 喂样本数据可见）
- `cd web && npx tsc --noEmit` 0 error
- `cd web && npm run build` 0 error
- `tests/evidence-trail.spec.ts` 5 case 全绿

**工作量**：M（1.5 天）
**完成信号**：`Signal: ARCHIVE-EVIDENCE-UI-DONE`

---

### 🔴 Task B · 高亮卡系统（`HIGHLIGHT-CARD-UI-DONE`）

**目标**：Agent 输出段落里每个关键 claim（"营收 5800 万 / 毛利率 32%"）用浅色块包裹，hover 弹 mini popover 显示 1 行出处 + 置信度条。与 Task A 共享 `EvidenceContext`，不重复拉数据。

**模块路径**：
- 新建：`web/src/components/evidence/HighlightCard.tsx`（props `{refId: string, children: ReactNode}`；从 `EvidenceContext` 按 `ref_id` 取证据，hover 弹 popover）
- 新建：`web/src/components/evidence/claimParser.ts`（工具函数：文本含 `[ref:xxx]` 标记时，把标记段切出来包 `<HighlightCard refId={xxx}>`；不含标记则原样渲染——不做 NLP 启发式识别，靠后端正文插 `[ref:ref_id]` 锚点）
- 新建：`web/src/components/evidence/evidence.css`（高亮浅色块 + mini popover + 置信度条；不要 inline style · 复用 `--t-*` Agent 功能色）
- 修改：`web/src/app/archive/{channel,credit,alert,compliance,report,riskctrl}/_components/*Workspace.tsx`（把 Agent 输出正文的 render pass 换成 `claimParser.renderWithHighlights(text, context)`；ReportWorkspace 段落多，注意 React key 稳定性）

**注意**：后端正文里的 `[ref:xxx]` 锚点由 `shared/evidence/protocol.py` Phase 2 grounded 生成时注入——**前端只消费，不回写后端**。如某 Agent 正文里没有 `[ref:]` 锚点（5 Agent 中可能有几个 evidence_pipeline 还没串到 prompt 层），前端正常渲染原文、不报错、不编造高亮。

**测试**（扩 `tests/evidence-trail.spec.ts` 或新增 `tests/highlight-card.spec.ts` · 3 case）：
1. 正文含 `[ref:ev_001]` → 渲染 `<HighlightCard>`，hover 弹 popover
2. 正文无 `[ref:]` 锚点 → 原样渲染，无高亮
3. `ref_id` 在 `evidence_trail` 里找不到 → 降级为普通 `<span>`，不报错（防后端契约漂移）

**指标/验证**：
- 6 Agent workspace 正文段落凡有 `[ref:]` 锚点都能看到浅色高亮
- hover popover 显示 1 行出处 + 置信度条
- `tsc --noEmit` / `build` 0 error

**工作量**：S-M（1 天）
**完成信号**：`Signal: HIGHLIGHT-CARD-UI-DONE`

---

### 🔴 Task C · 占位符未填标记 UI（`UNFILLED-MARKER-UI-DONE`）

**目标**：后端 QC Blocker 拦截的字段（进 `unfilled_fields: string[]` 或正文留 `未能自动填写` 标记）前端明确渲染为 `<UnfilledMarker>`，不 fallback 成 "0" / 空字符串 / "-"——这是 CLAUDE.md §12 硬红线。

**模块路径**：
- 新建：`web/src/components/evidence/UnfilledMarker.tsx`（props `{fieldName: string, reason?: "qc_blocked" | "no_evidence" | "conflict" | "unknown"}`；渲染灰色占位条 + "未能自动填写" + 小问号 icon hover 显示原因）
- 新建：`web/src/components/evidence/unfilled.css`（灰色占位条样式；与字段值区分度要明显）
- 修改：`web/src/app/archive/{channel,credit,alert,compliance,report,riskctrl}/_components/*Workspace.tsx`（渲染字段时 check `unfilled_fields.includes(fieldName)`，命中则挂 `<UnfilledMarker>`；正文出现字面值 `未能自动填写` 也替换）
- 修改：`web/src/lib/fallback.ts`（如有 fallback 逻辑，**禁用**把未知字段填 0 / "" 的路径；改为让调用方走 `<UnfilledMarker>` 分支 · 该文件 Batch 1 已存在，需 audit 有无"假数据"fallback）

**测试**（新增 `tests/unfilled-marker.spec.ts` · 4 case）：
1. `unfilled_fields` 含字段名 → 渲染 `<UnfilledMarker>`，文案"未能自动填写"
2. 正文含字面值 `未能自动填写` → 替换为组件（不是纯文本）
3. `reason="qc_blocked"` → hover tooltip 显示"QC 拦截"
4. `reason="no_evidence"` → hover tooltip 显示"证据不足"

**指标/验证**：
- 6 Agent workspace 任何字段被后端标 unfilled → 前端明确渲染 `<UnfilledMarker>`，无 "0" / "" / "-" fallback
- `fallback.ts` grep 不到 `return 0` / `return ''` 兜底未知字段的路径（有则移除）
- 3 Task 合计 `npm run build` + `tsc --noEmit` 全绿；3 个 spec 文件合计 ≥ 5 case

**工作量**：S（0.5-1 天）
**完成信号**：`Signal: UNFILLED-MARKER-UI-DONE`

---

## 4. 完成后

所有 Task 做完：`Signal: READY-FOR-CODE-URGENT-B2-REVIEW`

---

## 5. 红线

- ❌ **不动 backend**：`agent_*/` / `api_server.py` / `shared/*.py` / `v16_*.py` / `financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py` 一行不改
- ❌ **不动 Agent6 主管线**（`v16_pipeline.py` + 其他 `v16_*.py`，status 🟢，不许动坏）
- ❌ **不动 `data/mock/` / `evaluation/`**（data-foundation / evaluation worker 地盘）
- ❌ **不动 `web/src/lib/store/*`**（红区 · 主 CLI 保留）
- ❌ **不动 `web/src/components/shell/*`**（主 CLI 保留）
- ❌ **不动 legacy 顶层路由** `/channel` `/credit` `/alert` `/compliance` `/report` `/riskctrl`（shell v1 遗留，有独立清理 task，不在本批次）
- ❌ 不碰 code-arch / data-foundation / evaluation worker 的地盘
- ✅ 只动 `web/src/app/archive/*/_components/` + `web/src/components/evidence/`（新目录）+ `web/src/lib/api.ts`（SSE type 扩字段）+ `web/src/lib/fallback.ts`（audit 去 fallback）
- ✅ 新增 `tests/evidence-trail.spec.ts` / `tests/highlight-card.spec.ts` / `tests/unfilled-marker.spec.ts`
- ✅ 每 Task 独立 commit 带对应 Signal

---

## 6. 硬指标（Review 闸门预告）

| # | 指标 | 验证方式 |
|---|---|---|
| 1 | archive 6 workspace 点击可见 evidence_trail | `npm run dev` → 开 6 路由 → 发起 mock 查询 → 底部 `<EvidenceTrail>` 可展开 |
| 2 | 6 Agent 的 SSE 端点返回 payload 的 evidence_trail 被前端正确消费 | `curl -N http://127.0.0.1:8000/api/<agent>/...` 拿到 json 含 `evidence_trail`，前端渲染条数一致 |
| 3 | placeholder_guard 拦住的字段显示"未能自动填写" | mock SSE 带 `unfilled_fields: ["revenue_2024"]`，前端字段渲染为 `<UnfilledMarker>` 不是 "0" / "" |
| 4 | `npm run build` + `npx tsc --noEmit` 0 error | workspace 根 `cd web` 跑 |
| 5 | evidence UI 组件测试覆盖 ≥ 5 case | `cd web && npm test` 对 3 个 spec 全绿，case 合计 ≥ 5（实际 5 + 3 + 4 = 12） |
| 6 | `fallback.ts` 无"未知字段兜底 0/空"路径 | grep `return 0` / `return ''` 在 fallback.ts 0 命中 |

**Review 时 main CLI 会核对**：6 个 workspace 是否都挂了组件、SSE type 是否统一、fallback.ts 是否清洁、legacy 顶层路由是否 0 改动。任一不满足 → REJECT。

---

## 7. ACK 协议

1. Resume 读本文件 + decisions-log Q-029（Batch 2 派发决策） → commit doc-only，trailer `Signal: BATCH-2-CU-ACK`
2. Task A → B → C 顺序，每 Task 独立 commit 带对应 Signal（`ARCHIVE-EVIDENCE-UI-DONE` / `HIGHLIGHT-CARD-UI-DONE` / `UNFILLED-MARKER-UI-DONE`）
3. 全 Task 完成 → `READY-FOR-CODE-URGENT-B2-REVIEW`

**维护者**：主 CLI
**下次更新触发**：主 CLI APPROVE 或 REJECT

---

## 附录 · Kickoff Prompt（可粘贴）

```
你是 code-urgent worker CLI · Batch 2。先 ACK 再动手。

【Step 0 · ACK】
1) git fetch origin chore/l0-infra && git log origin/chore/l0-infra -10
2) 读 docs/handoff/decisions-log.md 中 Q-029（Batch 2 派发决策）
3) 读 docs/onboarding/batch-2-code-urgent-evidence-frontend.md 全文
4) 读 shared/evidence/protocol.py 确认 AuditReport.to_dict() shape（source/snippet/ref_id/confidence/meta + unfilled_fields）
5) commit 一条 doc-only（空改动或补一行 ACK 备注），trailer `Signal: BATCH-2-CU-ACK`

【Step 1 · Task A · archive evidence UI 组件】
- 新建 web/src/components/evidence/ 下 EvidenceTrail.tsx / EvidencePopover.tsx / types.ts / EvidenceContext.tsx
- 6 archive workspace 挂 <EvidenceTrail>；web/src/lib/api.ts SSE type 扩 evidence_trail + unfilled_fields
- tests/evidence-trail.spec.ts 5 case（空/多源/低置信/popover 开关/pdf 跳页）
- cd web && npx tsc --noEmit 0 error && npm run build 0 error
- 独立 commit · `Signal: ARCHIVE-EVIDENCE-UI-DONE`

【Step 2 · Task B · 高亮卡系统】
- 新建 HighlightCard.tsx / claimParser.ts / evidence.css；复用 EvidenceContext
- 6 workspace 正文 render pass 改 claimParser.renderWithHighlights；后端无 [ref:] 锚点要降级不报错
- 扩 spec 3 case（有锚点 / 无锚点 / ref_id 缺失降级）
- 独立 commit · `Signal: HIGHLIGHT-CARD-UI-DONE`

【Step 3 · Task C · 未填标记 UI】
- 新建 UnfilledMarker.tsx / unfilled.css；6 workspace 字段 render check unfilled_fields
- fallback.ts audit 去掉 "未知字段填 0/空" 兜底
- tests/unfilled-marker.spec.ts 4 case
- 独立 commit · `Signal: UNFILLED-MARKER-UI-DONE`

【红线】
只动 web/src/app/archive/*/_components/ + web/src/components/evidence/（新） + web/src/lib/api.ts + web/src/lib/fallback.ts。
不动 backend（agent_*/api_server.py/shared/*.py/v16_*.py）；不动 Agent6；不动 data/mock/ + evaluation/；不动 store/ + shell/；不动 legacy 顶层路由 /channel /credit /alert /compliance /report /riskctrl。
每 Task 独立 commit。blocker 立即喊停，不绕过。

【Final】
三 Task 全绿 → commit trailer `Signal: READY-FOR-CODE-URGENT-B2-REVIEW`。

开干。
```
