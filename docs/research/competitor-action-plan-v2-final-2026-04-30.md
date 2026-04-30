# 竞品借鉴最终融合方案 v2 · 2026-04-30

> Main CLI ultrathink + Codex independent review + 辩论融合 · PM 反硬改 mindset 严守
> v1 原稿 `competitor-action-plan-2026-04-30.md` 保留 · 本 v2 是辩论后融合

## 0. 辩论方法论 (PM 要求)

PM mindset:
- 不要硬改
- 所有优化必须有理有据有可行性
- 如果我们已是最优方案就完全不改
- 核心保持产品特色 (RM workbench + 6 Agent + Evidence-First + 中文金融场景)
- 这是优化的可能性 · 不是必须有优化方案

辩论参与者:
- **Main CLI v1**: 6 action 排序 + 5 PM 拍板项 (起初 Phase B-3 + B-1 + B 末 三档)
- **Main CLI self-review**: 6 → 4 action 自检 (砍 Action 4+6 · 推 Phase C)
- **Codex independent review**: 4 必做 + 3 撤回 + 3 改 scope (比 main CLI 更严)

## 1. 辩论对位 (6 Action 逐条 verdict)

### Action 1: `/today` modal-driven 改造

| 参与者 | Verdict | 理由 |
|---|---|---|
| Main CLI v1 | 🔴 P0 · 全 6 Agent modal · 3 周 | north star §3.1 RM workbench 主角 |
| Main CLI self | 保留 · 工程量 1 周 PoC 可 | 重新评估 6 workspace refactor 风险 |
| Codex | **改进建议** · 先 Agent6→Agent3 单链路 · 1 周 · `/archive` 保留 deep-link | 6 Agent 全 modal 一步到位会拖垮 Phase B · 单链路是核心闭环 |
| **融合** | ✅ **保留 · scope 改** | 接 Codex: 先单链路 1 周 · Agent4/5 推 Phase C |

**v2 verdict**: 🔴 P0 · 改 scope 为 **Agent6→Agent3 单链路 modal** · 1 周 · `/archive/[agent]` 全保留作为 deep-link/历史归档。

### Action 2: Agent3 评分按客群分模板 (科创六维)

| 参与者 | Verdict | 理由 |
|---|---|---|
| Main CLI v1 | 🔴 P0 · 1.5 周 · 3 segment yaml | 银行客户痛点 · "懂科创"卖点 |
| Main CLI self | 保留 · 工程量合理 | 通用四维 = Phase A 简化版 |
| Codex | **同意** · 但 rubric 先于 mock · segment 必须可 override · 不让 LLM 现场判生命周期 | 业务含金量最高 |
| **融合** | ✅ **保留 + 加约束** | rubric 先 · mock 后 · segment user-overridable · 生命周期用 truth_fill 确定性推断 (非 LLM) |

**v2 verdict**: 🔴 P0 · 1-1.5 周 · 加 3 约束 (rubric 先 / segment override / truth_fill 推断生命周期)。

### Action 3: 任务看板真接 handoff

| 参与者 | Verdict | 理由 |
|---|---|---|
| Main CLI v1 | 🟡 P1 · Phase B-1 顺带 · 1 周 | handoff schema 已就绪 |
| Main CLI self | 保留 P1 | A6 contract 已落 |
| Codex | **同意但提级 P0** · 不是顺带 · 是闭环证据 | Agent6 done 自动生成"待授信"卡带 ReportJSON · 风险=只做假 kanban |
| **融合** | ✅ **提级 P0 · 与 Action 1 配套** | handoff 任务卡是闭环证据 · 验证 Agent6→Agent3 单链路真通 |

**v2 verdict**: 🔴 P0 (从 P1 提级) · 1 周 · 与 Action 1 同 sprint · Agent6→Agent3 单链路 + handoff 任务卡 = 演示闭环 minimum 单元。

### Action 4: `/today` Hero 实时指标 strip

| 参与者 | Verdict | 理由 |
|---|---|---|
| Main CLI v1 | 🟡 P1 · 0.5 周 · 3-5 数字 chip (今日处理 / 红线命中 / 报告生成) | RM 反馈循环 |
| Main CLI self | 撤 · 推 Phase C | 弱痛 · 无用户反馈说要 |
| Codex | **反对当前 scope** · 无真实事件口径会变 KPI 装饰 · 只保留待办数/SLA | 反 Evidence-First (假数据装饰) |
| **融合** | ⚠️ **改 scope · 仅保留 minimum** | 撤"今日效率提升 35.8%" 装饰指标 · 保留待办数 + SLA (真数据) |

**v2 verdict**: 🟡 P2 · 0.3 周 · 只做 (a) 今日待办数 (b) 任务 SLA · 不做"效率提升 / 转化率 / 处理时长" 装饰指标 (无真数据来源 = KPI 装饰 = 反 Evidence-First)。

### Action 5: Agent1 Look-alike 增强 (F-005 fix)

| 参与者 | Verdict | 理由 |
|---|---|---|
| Main CLI v1 | 🟢 P2 · 1 周 · 内源 + 外源 + 12 场景预设 | F-005 fix-forward |
| Main CLI self | 保留 (是 F-005 fix · 不是为竞品) | F-005 NEVER CORRECTLY DELIVERED |
| Codex | **改进建议** · 先做内源 + explainable similarity · 不扩 LBS/12 场景 | 先修 F-005 真痛 · 12 场景 Phase C |
| **融合** | ✅ **保留 · scope 砍** | 只做内源已成交客户库 + 4 维度 explainable similarity · 12 场景预设推 Phase C |

**v2 verdict**: 🟡 P1 (从 P2 提级因是 F-005 fix) · 1 周 · scope 砍到内源 + similarity 解释化 · 不扩场景库。

### Action 6: 全局 Ctrl+K 命令面板

| 参与者 | Verdict | 理由 |
|---|---|---|
| Main CLI v1 | 🟢 P2 · 0.5 周 · cmdk 风 + 3 段聚合 | Cursor 模式核心 |
| Main CLI self | 撤 · 推 Phase C | 弱痛 · 无用户要 |
| Codex | **反对 Phase B 必做** · 放 Phase C 或 demo polish | workbench/handoff 更急 |
| **融合** | ❌ **撤 · 推 Phase C** | 三方一致 |

**v2 verdict**: ⚫ Phase C / demo polish · Phase B 不做。

## 2. 融合后路线图 (4 必做 + 1 改 scope + 1 撤)

### 🔴 P0 · Phase B-3 闭环单链路 (~3 周 · 含并行)

**目标**: Agent6→Agent3 单链路在 `/today` modal 内跑通 + handoff 任务卡自动流转 + Agent3 评分按客群分。这是**演示闭环 minimum 单元**。

| Action | 工程量 | 验收 (DoD) |
|---|---|---|
| 1. `/today` Agent6→Agent3 单链路 modal | 1 周 | 同页跑 Agent6 报告→Agent3 评分 · `/archive` 保留 deep-link · ESC + click outside 关 modal |
| 2. handoff 任务卡 (Agent6→Agent3 优先) | 1 周 | Agent6 done 自动生成"待授信"卡 · 带 ReportJSON · 状态机 4 列 |
| 3. Agent3 segment rubric (3 segment yaml) | 1-1.5 周 | rubric 先 mock 后 · segment user-overridable · truth_fill 推断生命周期 (非 LLM) |

**关键约束** (per Codex):
- 不全量 6 Agent modal 一步到位 — 单链路验通后 Phase C 加 Agent4/5
- handoff 不是顺带 UI · 是闭环证据
- segment 必须可 override · 不让 LLM 现场判

### 🟡 P1 · Phase B-1 真痛 fix (~1 周)

| Action | 工程量 | 验收 |
|---|---|---|
| 5. Agent1 F-005 内源 + explainable similarity | 1 周 | 内源已成交客户库 + 4 维度 explainable similarity (industry/geo/scale/similarity 含证据链) |

**砍 scope**: 不扩 LBS/12 场景预设 (推 Phase C)。

### 🟡 P2 · Hero minimum (~0.3 周 · 可不做)

| Action | 工程量 | 验收 |
|---|---|---|
| 4. `/today` Hero 待办数 + SLA | 0.3 周 | 只显真数据 (任务卡待办数 · 任务 SLA) · **不做装饰 KPI** |

**条件**: PM 确认要 · 否则 Phase C 再说。

### ⚫ Phase C / demo polish (不在 Phase B)

- 全 6 Agent modal 化 (Phase C 加 Agent4/5)
- Agent1 12 场景预设 (Phase C 增量)
- 全局 Ctrl+K 命令面板 (demo polish)
- 5 角色权限矩阵单表化 (治理债)

## 3. 总工程量对比

| 版本 | 总工程量 | 必做 action 数 | Phase B-3 scope |
|---|---|---|---|
| Main CLI v1 | ~6 周 | 6 | 全 6 Agent modal + segment + handoff |
| Main CLI self-review | ~4.5 周 | 4 | 全 6 Agent modal + segment |
| Codex independent | ~4 周 | 4 | 单链路 modal + segment + handoff |
| **v2 融合** | **~4-4.3 周** | **4 必做 + 1 可选** | 单链路 modal + segment + handoff (3 配套) |

砍掉:
- 全 6 Agent modal (1.5 周) · 改单链路 (1 周)
- Hero 装饰 KPI (0.5 周) · 改 minimum 待办+SLA (0.3 周可选)
- Ctrl+K (0.5 周) · 推 Phase C
- Look-alike 12 场景 (0.5 周) · 推 Phase C

## 4. 5 PM 拍板项 (修订版)

| # | 提案 | 选项 | 推荐 verdict | 理由变化 |
|---|---|---|---|---|
| 1 | Phase B-3 charter scope | A) 单链路 modal+handoff+segment 3 配套 (4 周) · B) 全 6 Agent modal 一步 (6+ 周) | **A** (codex 反对一步到位) | 演示能讲 Agent6→Agent3 故事 · 不为大而大 |
| 2 | Agent3 segment 命名 | A) 科创/对公/普惠 (与南京银行术语对齐) · B) 科创/对公/小微 · C) 行业自定义 | **A** | 城商行术语统一 |
| 3 | Action 3 (handoff) 与 Action 1 同 sprint? | A) 同 (Phase B-3 配套) · B) 推 Phase B-1 顺带 | **A** (codex 提级) | handoff 是闭环证据 · 不是顺带 |
| 4 | Hero 指标做不做? | A) 只做 minimum (待办+SLA) · B) 全做 · C) 全不做 (推 Phase C) | **A 或 C 都行** | 反 Evidence-First 装饰必撤 · minimum 看 PM 是否要 |
| 5 | Look-alike scope | A) 内源 + similarity (1 周) · B) + 12 场景预设 (1.5 周) | **A** (codex 反对 scope creep) | F-005 真痛先修 · 场景库 Phase C |

## 5. 不做的 (产品特色保护红线 per CLAUDE.md §3)

- ❌ 全 6 Agent 一步 modal (Codex 反对 · 单链路先验)
- ❌ Hero 装饰 KPI ("效率提升 35.8%" 类无真数据指标 · 反 Evidence-First)
- ❌ 单页 Vue inline HTML 架构 (技术倒退)
- ❌ 5 角色含产品经理 + 部门领导 (营销偏 · 不贴信贷)
- ❌ 投贷联动 / 五融生态 (银行业务创新 · 不是 AI 工具)
- ❌ 12 场景预设 (Phase B scope creep)
- ❌ 全局 Ctrl+K Phase B 必做 (Phase C / demo polish)

## 6. 总结 (3 句以内)

- **Verdict**: 三方独立审 (Main CLI v1 / self / Codex) 一致 → 6 action 砍到 4 必做 + 1 可选 (4-4.3 周 vs 6 周 v1) · 砍掉 30% 不必做的工作。
- **真核心**: Phase B-3 = Agent6→Agent3 单链路 modal + handoff 任务卡 + Agent3 segment rubric (3 配套 = 演示闭环 minimum 单元) · 不为竞品大而大。
- **PM mindset 严守**: 撤掉所有"为竞品补 UI"的硬改 (Hero 装饰 / 全 6 Agent modal / Ctrl+K) · 保留所有"修我们已知缺陷"的真痛 (F-005 / 通用四维 / 假任务卡) · north-star 没漂。

## 7. Sign-off

- 起草: Main CLI ultrathink + Codex independent review (high reasoning · sandbox read-only · main CLI 落 doc 代写)
- 待 PM 拍板: §4 表 5 项 (修订版)
- 落地后回写: `docs/reset/phase-b-charter.md` 加 worker-B3 (Action 1+2+3 配套) + worker-B1 (Action 5) + decisions-log Q-NNN entry "Codex peer-review on competitor borrow plan ratified"
