# 完整版前端优化方案 · 2026-04-30 (FINAL)

> 三方辩论 R1+R2+R3 融合 + 综合竞品分析 v2 · 主 CLI ultrathink · PM mindset 严守
> R1 doc: three-way-debate-r1-{mainCLI,codex,gemini}-2026-04-30.md
> R2 doc: three-way-debate-r2-{mainCLI,codex,gemini}-2026-04-30.md
> R3 = 主 CLI 综合 (本 doc)
> 竞品 v2: competitor-action-plan-v2-final-2026-04-30.md
> Gemini 真截图反馈: gemini-frontend-feedback-v3-2026-04-30.md

## 0. 辩论过程

3 方:
- **主 CLI** = 产品 PM 视角 (4 角色 + 银行金融场景 + Evidence-First)
- **Codex** = 技术/逻辑视角 (file:line 证据 + 工程量精准)
- **Gemini Pro** = 审美/IA 视角 (真截图 · 5045 字 R1 + 1708 字 R2 verbatim · **审美权重重**)

3 轮:
- R1 独立草案 (各方独立看竞品 + 当前前端 · 出真痛 + action + 不做)
- R2 互检 (各方看其他两方 R1 · 出 dissent + agree + 加补)
- R3 主 CLI 综合 (本 doc · 含 3 真冲突 verdict + Phase B 完整 action 清单)

## 1. 三方辩论收敛点 (5 维度 unanimously approved)

### 1.1 视觉

| 议题 | 三方 verdict |
|---|---|
| 弃登录页黑洞 | ✅ unanimously (Gargantua/Interstellar 复刻 · 金融语义负面 · 资金黑洞触风控潜意识) |
| **全屏渐变折中** | ✅ 三方 lock: 主工作区背景纯净灰/白 #F7F9FC + 4 主题渐变只作点缀 (Masthead 底色 / 选中导航高亮条 / 指标卡顶边框 / 主按钮 Hover 态) |
| 删手写斜体 (pinged/running/open) | ✅ unanimously (字体 token --italic + login multi-place 用 · 金融工作台无衬线中文优先) |
| 字体栈中文优先 (PingFang SC / MiSans / Inter) | ✅ unanimously (Gemini Tailwind 路径 · 全局 grep search-replace) |

### 1.2 IA

| 议题 | 三方 verdict |
|---|---|
| /today 头重脚轻 (顶部 KPI 压横向 · 队列拉升 10-15 行) | ✅ unanimously (Gemini 视觉看出 · Codex agree · 主 CLI R2 接受) |
| /archive 弱化 + Today 主路径 | ✅ unanimously |

### 1.3 UX

| 议题 | 三方 verdict |
|---|---|
| 收敛圆角 (外层 ≤12px · 数据列表 4-8px · 状态标签全圆角) | ✅ unanimously |
| **Action Card 组件族合并** (告警/交接/补材料/通过/驳回 共享 · 复用 HandoffCard.tsx + ComposerBar.tsx) | ✅ Codex 提议 · 三方接受 |

### 1.4 中文金融

| 议题 | 三方 verdict |
|---|---|
| 金额标准 ¥50,000,000.00 + Tabular Figures + 严格右对齐 | ✅ unanimously (Gemini 升级主 CLI A1 · Codex 同意 · 当前 ¥amount.toLocaleString() 万 不够) |
| 术语纯中文 (待办工单/今日预警/活跃客户/流转中任务/风险拦截) | ✅ unanimously (Gemini 给具体词 · Codex 同意 · MorningBrief.tsx:184-201 中英混排 fix) |

### 1.5 产品深问题

| 议题 | 三方 verdict |
|---|---|
| Hero minimum 真指标 (替 TICKET_FALLBACK_COUNT=4 mock · 不显效率/转化率装饰 KPI) | ✅ unanimously (反 Evidence-First) |
| Agent6→Agent3 单链路 Today 工作台 (复用 CreditWorkspace.tsx:237 runDecisionWithAgent6Handoff) | ✅ unanimously (1 周 · 不是 1.5 周高估) |
| Handoff 任务卡真接入 (`report.completed` 自动生成"待授信"卡 + 带 ReportJSON ref) | ✅ unanimously |
| Agent3 segment-aware 评分 (科创/对公/普惠 yaml + RM override + truth_fill 推断生命周期不让 LLM 现场判) | ✅ unanimously |

## 2. 三方 dissent + R3 主 CLI 裁决 (3 议题)

### 2.1 议题 A: 6 Agent 跨冲突 UI 仲裁 (主 CLI A5)

| 三方 verdict |
|---|
| 主 CLI R2: 保留完整 1 周 |
| Codex R2: **降级 P1 spike** "冲突提示 + 人工裁决记录" 0.3 周 (理由: 当前没跨 Agent 冲突 schema · 完整仲裁引擎是产品深问题不是 Phase B 工程量) |
| Gemini R2: **"神来之笔"** 完整支持 (审美/产品视角) |

**R3 主 CLI 裁决: 分阶段** (折中 · 兼顾 Codex 务实 + Gemini 审美 + PM mindset):
- **Phase B-3 (~0.3 周)**: 做 Codex 提议的 spike — "冲突提示 + 人工裁决记录" 最小可演示形态
- **Phase C (1 周 + schema 设计 ~0.5 周)**: 做 Gemini "神来之笔" 完整版 — 跨 Agent 冲突 schema + 完整仲裁 UI
- **理由**: PM 反硬改 + Codex 没 schema 反对成立 + Gemini 审美方向对但需 schema 先 · spike 验产品 + Phase C 完整版

### 2.2 议题 B: AI 助手卡路由 (Codex C3)

| 三方 verdict |
|---|
| 主 CLI R1: (没提 · 漏看 TodayContent.tsx:29) |
| Codex R2: **C3 修路由** 0.5 天 quick win (AI 助手卡进 /archive 或具体 agent/session · 消息卡仍 /dispatch) |
| Gemini R2: **直接移除 AI 助手卡 + 改 ⌘+K Command Bar 或工作流侧边栏** (Agent 必须隐形于工作流之下) |

**R3 主 CLI 裁决: 分阶段** (二者都对 · 不冲突):
- **Phase B-1 (0.5 天)**: 做 Codex C3 修补 — quick win 避免立即破 (用户体验立即改善 · 不等 B-3)
- **Phase B-3 (~0.5-1 周)**: 做 Gemini ⌘+K Command Bar — Agent 隐形入口 · 慢迁移 (修补完后逐步迁到 Command Bar)
- **B-3 末**: 移除 AI 助手卡入口 (与 ⌘+K 同期 · 慢迁完后才移)
- **理由**: 修补先 (避免立即空白) + Command Bar 后 (IA 重构 · 不一步到位) · Codex 务实 + Gemini IA 重构 · 分阶段融合

### 2.3 议题 C: 登录页黑洞优先级 (主 CLI A6)

| 三方 verdict |
|---|
| 主 CLI R1: P2 (Phase B 末 · 0.3 周) |
| Codex R2: 默认接受 P2 (没异议) |
| Gemini R2: **必提权 P0/P1** (B2B 决策者第一印象 · 资金黑洞触碰风控红线潜意识) |

**R3 主 CLI 裁决: 接受 Gemini 提权 P1** (Phase B-1 做 · 不等 B 末):
- 工程量小 (0.3 周) · 与 A1 千分位 + C3 修路由 + C4 Hero 一起 B-1 sprint
- Gemini 审美权重重 · 银行客户第一印象关键
- 改: 3D 几何粒子网络 OR 极简磨砂玻璃企业级登录台 + 微弱品牌色深灰/深蓝
- **待 PM 校验**: 此前定 Interstellar 是品牌实验 · 是否接受 Gemini 替换方案

## 3. 完整版 Action 清单 (R1+R2+R3 融合 + 综合竞品 v2)

### Phase B-1 sprint (~1 周 · quick win 立做)

| Action | 来源 | 工程量 | 验收 (DoD) |
|---|---|---|---|
| **F1** 千分位 + 术语 + 金额标准 (¥50,000,000.00 + Tabular Figures + 严格右对齐 + 纯中文术语) | 主 CLI A1 + Gemini 升级 + Codex 同意 | 0.5-1 周 | 4 角色 view 全数字达金融规范 · 0 中英混排 |
| **F2** Today AI 助手卡路由修补 (TodayContent.tsx:29 修) | Codex C3 | 0.5 天 | 助手卡进 /archive 或具体 agent · 消息卡仍 /dispatch |
| **F3** Hero minimum 真指标 (替 TICKET_FALLBACK_COUNT 真 ticket-store · 不显效率/转化率) | Codex C4 + Gemini 反对装饰 | 0.3 周 | Hero 待办数 + SLA 全真数据 · 无源时显 fallback 标识 |
| **F4** 登录页黑洞重设计 (3D 几何粒子 OR 极简磨砂玻璃 + 中性深灰/蓝) | 主 CLI A6 + Gemini 提权 P1 | 0.3 周 | 银行客户首屏不联想"资金被吞" · 待 PM 校验品牌实验 |

### Phase B-3 sprint (~3 周 · RM workbench 闭环 · 含并行)

| Action | 来源 | 工程量 | 验收 (DoD) |
|---|---|---|---|
| **F5** Today 单链路 Agent6→Agent3 工作台 (复用 CreditWorkspace.tsx:237) | Codex C1 + 主 CLI A2 (Codex 砍 0.5 周) | 1 周 | RM 同页跑 Agent6 报告→Agent3 评分 · /archive/[agent] 保留 deep-link |
| **F6** Handoff 任务卡真接入 (report.completed → 自动"待授信"卡 + ReportJSON ref) | Codex C2 + 竞品 v2 Action 3 | 0.5-1 周 | today/warroom 数字一致 · 不假 kanban |
| **F7** Agent3 segment-aware 评分 (科创/对公/普惠 yaml + RM override + truth_fill 推断生命周期) | Codex C5 + 竞品 v2 Action 2 | 1-1.5 周 | 输入科创企业出六维画像 · 输入小微出团队+还款评分 · segment 可 override |
| **F8** Action Card 组件族合并 (告警/交接/补材料/通过/驳回 共享 · 复用 HandoffCard.tsx + ComposerBar.tsx) | Codex 提议 + 主 CLI A4 + Gemini Action Card | 0.5-1 周 | 合规告警 + 任务交接 + 审批 全 inline 可处置 · 一键 button |
| **F9** A5 spike 冲突提示 + 人工裁决记录 | Codex R2 降级 + 主 CLI R3 裁决分阶段 | 0.3 周 | Agent3+Agent5 冲突时 /dispatch 显式 ⚠️ + 审贷员手动裁决 (无完整 schema) |
| **F10** 视觉清洗 (字体栈 PingFang/MiSans/Inter + 删手写斜体 + 收敛圆角 4-12px) | Gemini R1 + R2 + Codex 同意 | 0.5 周 | 全局 grep search-replace + Tailwind config 改 · 0 手写斜体残留 |
| **F11** /today 头重脚轻改造 (顶部 KPI 横向数据看板 · 队列拉升 10-15 行) | Gemini R1 | 0.5 周 | RM 进 /today 一屏看 10-15 客户 · KPI 不抢屏 |
| **F12** 全屏渐变折中 (主区 #F7F9FC + 装饰区保留 4 主题) | 三方 R2 lock | 0.5 周 | shell.css:21-29 .shell-root 主区改中性 · Masthead/选中/指标卡顶边/Hover 保留主题 · 待 PM 校验 |
| **F13** ⌘+K Command Bar (Agent 隐形入口 · 慢迁) | Gemini R2 | 0.5-1 周 | Cmd+K → 输入 → 客户 + Agent 调用 + 历史会话 3 段 suggestion |

### Phase B 末 sprint (~1 周)

| Action | 来源 | 工程量 | 验收 (DoD) |
|---|---|---|---|
| **F14** Agent1 explainable similarity (内源 + industry/geo/scale/similarity 四维证据) | Codex C6 + 竞品 v2 Action 5 | 1 周 | 候选卡显内源相似客户证据 · 不扩 12 场景 |

### Phase C (不在 Phase B)

- **F15** A5 完整跨 Agent 冲突 UI (Phase C · schema 设计先 + UI 后) — Gemini "神来之笔" 完整版
- **F16** Agent1 12 场景预设 (Phase C · 不扩) — 借鉴南京银行 LBS
- **F17** 全 6 Agent modal 一步到位 (Phase C · 单链路验通后加 Agent4/5)
- **F18** 5 角色权限矩阵单表化 (治理债 · Phase C 顺带)

### 不做 (产品特色保护红线 · 三方一致 + CLAUDE.md §3)

| 不做 | 理由 |
|---|---|
| 装饰 KPI ("效率提升 35.8%" 类无真数据指标) | 反 Evidence-First |
| 单页 Vue inline HTML 架构 | 技术倒退 · 不可维护 |
| 5 角色含产品经理 + 部门领导 | 营销偏 · 不贴信贷场景 |
| 投贷联动 / 五融生态 | 银行业务创新 · 不是 AI 工具 · 模糊产品边界 |
| 全屏渐变全撤 (per Gemini R1) | 破 platform shell-v2 lock 定稿品牌特色 · 三方 R2 折中即可 |
| 全 6 Agent 一步 modal 化 (per 主 CLI v1) | 工程量与价值不匹配 · 单链路先 |
| 直接移除 AI 助手卡 (per Gemini R2 一口吃下) | IA 重构需慢迁 · 修补先 + Command Bar 后 |

## 4. 总工程量 + 排期

```
Phase B (假设 4-6 周 · 现 Phase A 收尾中)
├── B-1 (~1 周 quick win sprint):
│   ├── F1 千分位+术语+金额标准 (0.5-1 周)
│   ├── F2 Today AI 助手卡路由修补 (0.5 天)
│   ├── F3 Hero minimum 真指标 (0.3 周)
│   └── F4 登录页黑洞重设计 (0.3 周 · 待 PM 校验)
├── B-3 (~3 周 RM workbench 闭环 sprint · 含并行):
│   ├── F5 Today 单链路 Agent6→Agent3 (1 周)
│   ├── F6 Handoff 任务卡真接入 (0.5-1 周)
│   ├── F7 Agent3 segment-aware (1-1.5 周)
│   ├── F8 Action Card 组件族合并 (0.5-1 周)
│   ├── F9 A5 spike (0.3 周)
│   ├── F10 视觉清洗 (0.5 周)
│   ├── F11 /today 头重脚轻改造 (0.5 周)
│   ├── F12 全屏渐变折中 (0.5 周 · 待 PM 校验)
│   └── F13 ⌘+K Command Bar (0.5-1 周)
└── B 末 (~1 周):
    └── F14 Agent1 explainable similarity (1 周)
```

**总工程量**: ~5 周 (含并行 ~4-4.5 周 wall-clock)

**对比 v1 → v3 演进**:
- v1 (主 CLI 6 action): ~6 周
- self-review (4 必做 + 2 撤): ~4.5 周
- v2 融合 (Codex 砍): ~4-4.3 周
- v3 完整版 (含 Gemini 14 action 含视觉清洗): ~5 周 (含并行 ~4-4.5 周)

v3 比 v2 多了视觉清洗 + ⌘+K + Action Card 合并 + 头重脚轻改造 等真痛 fix · 但单项 ROI 都高 · 总工程量基本平。

## 5. PM 拍板项 (≤ 5)

| # | 提案 | 选项 | 推荐 | 理由 |
|---|---|---|---|---|
| 1 | **全屏渐变折中** (主区 #F7F9FC + 装饰区保留 4 主题) | A) 接受折中 · B) 全保留 4 主题 · C) 全撤为中性 | **A** | 三方 R2 unanimously lock · 兼顾品牌 + WCAG · 唯一破点是 platform shell-v2 lock 定稿微调 |
| 2 | **登录页黑洞替换** (3D 几何粒子 OR 极简磨砂玻璃) | A) 接受替换 (Gemini 提权 P1 · B-1 做) · B) 保留 Interstellar 黑洞作品牌实验 · C) 推 Phase C | **A** | Gemini 审美权重重 · B2B 第一印象 · 工程量 0.3 周 · 待 PM 校验是否舍弃 Interstellar 品牌实验 |
| 3 | **A5 跨冲突 UI 分阶段** (B-3 spike + Phase C 完整) | A) 接受分阶段 · B) B-3 完整 (1 周 · 主 CLI R2) · C) 全推 Phase C (Codex spike 都不做) | **A** | 折中: Codex 务实 (没 schema 不强行) + Gemini 审美 (神来之笔 必做) + PM 反硬改 |
| 4 | **AI 助手卡路由分阶段** (B-1 修补 + B-3 ⌘+K 慢迁) | A) 接受分阶段 · B) 一步移除 (Gemini 激进) · C) 仅修补 (Codex 务实) | **A** | 修补先避免空白 + Command Bar 后慢迁 · 二者都对 |
| 5 | **Action Card 组件族合并** (告警 + 交接 + 补材料 + 通过 + 驳回) | A) 接受合并 · B) 各自独立组件 | **A** | 复用现有 HandoffCard.tsx + ComposerBar.tsx · Codex 提议三方接受 |

## 6. 风险 + 不做的边界

### 6.1 主要风险

| 风险 | 缓解 |
|---|---|
| F12 全屏渐变折中破 PM lock 定稿品牌特色 | PM 重新校验 (拍板项 1) · feature flag 双轨过渡 |
| F4 登录页改 Interstellar 是品牌核心 | PM 重新校验 (拍板项 2) · 不撤的话 F4 推 Phase C |
| F9 A5 spike 不够真 | 接受 spike 是验证形态 · Phase C 加完整 schema + UI |
| F13 ⌘+K Command Bar IA 重构破现有跳转 | 慢迁 · B-3 末才移除 AI 助手卡入口 (与 ⌘+K 同期) |
| Phase B 总工程量超 5 周 | F13/F14 推 Phase C · F1-F12 优先 ship |

### 6.2 不做的边界 (per CLAUDE.md §3 + 三方 R3 共识)

见 §3 不做表 (7 条)。

## 7. Sign-off

- **R1 主 CLI** (a9e3682): 产品 PM 视角 6 action 草案
- **R1 Codex** (e8099e8): 技术/逻辑视角 6 action + file:line 证据
- **R1 Gemini** (faefbfe): 审美视角 5 verdict + 4 维度详细 (真截图 5045 字)
- **R2 主 CLI** (9d387d9): 接受 Codex 100% / Gemini 80% · dissent 1 (全屏渐变折中)
- **R2 Codex** (6eb6059): 接受 Gemini 80% / 主 CLI 75% · dissent 1 (A5 降级 spike)
- **R2 Gemini** (本 commit 前一): 1708 字 verdict · 反对 A6 P2 (提权 P1) · 反对 C3 (要 ⌘+K)
- **R3 主 CLI 综合** (本 doc): 14 action + 3 真冲突分阶段裁决 + 5 PM 拍板项
- **竞品 v2** (81c112d): 4 必做 + 1 可选 · 已 ratify
- **完整版方案** = 三方辩论 R3 + 竞品 v2 = 14 action 排期

**待 PM 5 拍板项 (§5) 通过后**:
- 落 Phase B charter: `docs/reset/phase-b-charter.md` 加 worker-B1 (F1-F4) + worker-B3 (F5-F13) + worker-B 末 (F14)
- decisions-log Q-NNN entry: "Three-way debate (Main CLI ↔ Codex ↔ Gemini) ratified · 14 action + 3 真冲突分阶段裁决"
- CLAUDE.md §7 platform shell-v2 段加 "F12 全屏渐变折中 · 主区 #F7F9FC · 装饰区保留主题" (per PM 拍板 1 后)
