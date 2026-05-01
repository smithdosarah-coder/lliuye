# 完整版前端优化方案 v4 final · 2026-05-01

> 真三方辩论 R1 v2 + R2 v2 + R3 主 CLI 综合 (Gemini conversation 5 turn 真发生 · PM 可 chrome verify)
> 替代 v3 (820e64e · 14 action) · v4 包含 Codex R1 v2 找的 6 真 bug + Gemini 3 新点 + Codex R2 v2 加补 C14 - 共识精简后 17 action
> 历史 milestone: git tag `phase-a-exit-bugfix-2026-05-01` (4 BUG 修完后稳定版 · 退回点)

## 0. 三方辩论真实性 verify (PM 可手动验)

| 轮次 | 主 CLI | Codex | Gemini |
|---|---|---|---|
| R1 v2 | a3a7adc (产品 PM) | 01d1582 (高 reasoning · 全扫 156 文件 · 6 bug) | Gemini conversation turn 4 (12 view 真截图 · 5 verdict + 3 新点 · 1239+ 字 verbatim) |
| R2 v2 | 本 commit (本 doc 含) | byo5w849m (高 reasoning · 加补 C14) | Gemini conversation turn 5 (主 CLI 直接控浏览器抓 · 7 决断 verbatim) |
| R3 综合 | 本 doc (主 CLI 综合三方齐 verdict) | n/a | n/a |

**Gemini conversation URL** (PM verify 用): https://gemini.google.com/app/0da5b5fe5b4aecdd
- 应该能看到 5 个 turn (R1 v3 + R1 v2 + R2 v3 + R2 v2 第 1 反问 + R2 v2 第 2 follow-up 7 决断)
- Sub-agent v3 上轮 fail · 主 CLI 直接控浏览器接手成功 · 截图 `docs/research/screenshots-2026-04-30/v2/15-gemini-reply-r2-v2.png`

## 1. 17 Action 排期 (R3 final)

### Phase B-1 sprint (~1 周 · quick win)

| # | Action | 来源 | 工程量 | 验收 (DoD) |
|---|---|---|---|---|
| **F1** | 千分位 + 术语 + 金额标准 (`¥50,000,000.00` + Tabular Figures + 严格右对齐 + 纯中文术语) | 主 CLI A1 + Gemini 升级 + Codex 同意 | 0.5-1 周 | 4 角色 view 全数字达金融规范 · 0 中英混排 · Tabular Figures CSS 接 |
| **F2** | Today AI 助手卡路由修补 (TodayContent.tsx:29 修) | Codex C3 | 0.5 天 | 助手卡进 /archive 或具体 agent · 消息卡仍 /dispatch |
| **F3** | Hero minimum 真指标 (替 TICKET_FALLBACK_COUNT 真 ticket-store · 不显效率/转化率装饰) | Codex C4 + Gemini 反对装饰 | 0.3 周 | Hero 待办数 + SLA 全真数据 · 无源时显 fallback 标识 |
| **F4** | 登录页黑洞重设计 (3D 几何粒子 OR 极简磨砂玻璃 + 中性深灰/蓝) | 主 CLI A6 + Gemini 提权 P1 + R2 v2 三方一致 | 0.3 周 | 银行客户首屏不联想"资金被吞" · Interstellar 实验撤 |
| **F5** | **CustomerContextGateway** (读 ?customer query · focus customer-store · 传入 4 workspace) | Codex C7 + Gemini Customer Ribbon (折中) | 0.5-1 周 | RM 从 customer/dispatch/today 进 workspace 后 hero/query/默认 scan 一致 · 不删 CustomerSelector 保留 demo 切换 |
| **F6** | **C14 Evaluation Baseline Gate** (Phase B-1 必跑 6 Agent baseline · 接入 CI release checklist) | Codex R2 v2 加补 (三方都漏) | 3-5 天 | 6 Agent evidence_rate / hallucination_rate / field_completeness baseline 跑通 · 红线接 CI |

### Phase B-3 sprint (~3 周 · RM workbench 闭环 · 含并行)

| # | Action | 来源 | 工程量 | 验收 (DoD) |
|---|---|---|---|---|
| **F7** | Today 单链路 Agent6→Agent3 (复用 CreditWorkspace.tsx:237 runDecisionWithAgent6Handoff) | Codex C1 + 主 CLI A2 (Codex 砍 0.5 周) | 1 周 | RM 同页跑 Agent6 报告→Agent3 评分 · /archive/[agent] 保留 deep-link |
| **F8** | Handoff 任务卡真接入 (report.completed → 自动"待授信"卡 + ReportJSON ref) | Codex C2 + 竞品 v2 Action 3 | 0.5-1 周 | today/warroom 数字一致 · 不假 kanban |
| **F9** | Agent3 segment-aware 评分 (科创/对公/普惠 yaml + RM override + truth_fill 推断生命周期) | Codex C5 + 竞品 v2 Action 2 | 1-1.5 周 | 输入科创企业出六维画像 · 小微出团队+还款评分 · segment 可 override |
| **F10** | **Action Card 组件族合并** (告警/交接/补材料/通过/驳回 共享 · 复用 HandoffCard + ComposerBar · 含 Stage-aware 顶部主卡) | Codex 提议 + 主 CLI A4 + Gemini Action Card + Stage-aware (合并) | 0.5-1 周 | 合规告警 + 任务交接 + 审批 全 inline 可处置 · stage 决定 CTA "提交授信审查/打回补件/发起合规复核" |
| **F11** | **A5 spike 冲突显性化** (冲突来源/影响客户/推荐 owner/可跳 Warroom · ⚠️ 视觉提示 per Gemini) | Codex R2 v2 降级 + 主 CLI R3 接受 + Gemini 视觉提示 | 0.3 周 | Agent3+Agent5 冲突时 /dispatch 显式 ⚠️ + 显冲突点 · 不做完整仲裁引擎 |
| **F12** | 视觉清洗 (字体栈 PingFang/MiSans/Inter + 删手写斜体 + 收敛圆角 ≤ 8px) | Gemini R1 + R2 + Codex 同意 | 0.5 周 | 全局 grep search-replace · Tailwind config 改 · 0 手写斜体残留 |
| **F13** | /today 头重脚轻改造 (顶部 KPI 横向数据看板 + 队列拉升 10-15 行 + 左侧客户列表 + 右侧 Agent 建议) | Gemini R1 v2 + R2 v2 决断 3 | 0.5 周 | RM 进 /today 一屏看 10-15 客户 + 单链路工作中心 |
| **F14** | **全屏渐变折中** (主区 #F7F9FC + 装饰区 4 主题 仅 Masthead 底色 + 选中导航高亮条 + 主按钮 Hover 态) | 三方 R2 lock | 0.5 周 | shell.css:21-29 .shell-root 主区改中性 · 装饰区保留主题 · WCAG 2.1 达标 |
| **F15** | **Live evidence adapter** (EvidenceProvider 优先吃 liveData · fixture 只 mock/demo) | Codex C8 (P0 critical) | 1 周 | 6 workspace evidence 接 SSE done · fixture 仅 demo 路径 · 反 Evidence-First 假 fixture 修 |
| **F16** | Dispatch 单发送 (删 /api/im/send 重复 OR 并入 sendMessageRest) | Codex C9 (P1) | 0.5 天 | 一次 submit 仅一个 POST · 失败可见 banner |
| **F17** | Warroom rejected lane (加 rejected 列 OR "已退回/归档"过滤) | Codex C10 (P1) + Gemini 决断 5 | 0.5 天 | 拒绝后卡片仍可查 · source event/payload 保留 |

### Phase B 末 sprint (~1 周)

| # | Action | 来源 | 工程量 | 验收 (DoD) |
|---|---|---|---|---|
| C11 | Audit 降级标识 (短期 "session-only demo" · 中期 Phase C 接 /api/audit) | Codex C11 (P1 · Codex R2 v2 分阶段) | 0.3 周 | AuditView 加 banner 说明 · event-bus 显 cap 200 · CustomerPage seed 标注 |
| C12 | 替换 live 路径 ScanCTA (Report mock 留 · Riskctrl backtest 改 live action + 真 running/error) | Codex C12 (P2) | 0.5-1 周 | 无 /api/run/riskctrl 幽灵调用 · 真失败红卡阻断 |
| C13 | 抽 shared live-fail/evidence hook (6 workspace 已重复 liveFail/retry/banner) | Codex C13 (B 末 中) | 1 周 | 统一 status/bodyExcerpt/retry API · 不改视觉 |
| **C18** | Agent1 explainable similarity (内源 + 4 维度证据) | Codex C6 + 竞品 v2 Action 5 | 1 周 | 候选卡显内源相似客户证据 · 不扩 12 场景 |

### Phase C (不在 Phase B · 推后)

- **Phase C1**: A5 完整跨 Agent 冲突 schema + UI · 含 audit 账本接 /api/audit + 审贷官一键裁决 (~1.5 周 · 等 audit 后端 ready)
- **Phase C2**: Report 全屏 Document + Riskctrl IDE 三列 (~2 周 · 视觉重构 · Phase B 资源紧推后)
- **Phase C3**: 大白话结论 (`plainDecisionSummary` metrics adapter · "违约概率 < 2.8%" 替 KS/AUC) — Gemini 提的可 B-3 顺带 OR Phase C
- **Phase C4**: Agent1 12 场景预设 (Phase B 不扩)
- **Phase C5**: 全 6 Agent modal 一步到位 (Phase B 单链路 Agent6→Agent3 验通后才扩 Agent4/5)
- **Phase C6**: 5 角色 RBAC 权限矩阵单表化 (治理债 · Phase C 顺带)

## 2. 不做的边界 (产品特色保护红线 · 三方共识)

| 不做 | 理由 |
|---|---|
| 装饰 KPI ("效率提升 35.8%" 类无真数据指标) | 反 Evidence-First |
| 单页 Vue inline HTML 架构 | 技术倒退 · 不可维护 |
| 5 角色含产品经理 + 部门领导 | 营销偏 · 不贴信贷场景 |
| 投贷联动 / 五融生态 | 银行业务创新 · 不是 AI 工具 · 模糊产品边界 |
| 全屏渐变全撤 (per Gemini R1) | 破 platform shell-v2 lock 定稿品牌特色 · R2 v2 三方 lock 折中 |
| 全 6 Agent 一步 modal 化 | 工程量与价值不匹配 · 单链路先 |
| 一刀切删 CustomerSelector (per Codex R2 v2) | 保留 demo / 异常切换入口 |
| IM 降级到边缘 (per Codex R2 v2) | dispatch 保留为协作会话 + command surface · ⌘+K 汇总 /run /handoff /assign · 不从 IA 上废掉 |
| Phase B 大改 Report+Riskctrl 布局 (per Codex R2 v2) | Phase B 局部扩容 + 默认 tab 优化 · 全屏 Document/IDE 推 Phase C |

## 3. 总工程量 + 排期

```
Phase B (~5.5-6 周 · 含并行 ~4.5-5 周 wall-clock):
├── B-1 (~1 周 quick win sprint):
│   ├── F1 千分位+术语+金额 (0.5-1 周)
│   ├── F2 Today AI 助手卡路由修补 (0.5 天)
│   ├── F3 Hero minimum 真指标 (0.3 周)
│   ├── F4 登录页黑洞重设 (0.3 周)
│   ├── F5 CustomerContextGateway (0.5-1 周)
│   └── F6 C14 Evaluation Baseline Gate (3-5 天)
├── B-3 (~3 周 RM workbench 闭环 · 含并行):
│   ├── F7 Today 单链路 Agent6→Agent3 (1 周)
│   ├── F8 Handoff 任务卡 (0.5-1 周)
│   ├── F9 Agent3 segment-aware (1-1.5 周)
│   ├── F10 Action Card 组件族 (0.5-1 周)
│   ├── F11 A5 spike (0.3 周)
│   ├── F12 视觉清洗 (0.5 周)
│   ├── F13 /today 头重脚轻 (0.5 周)
│   ├── F14 全屏渐变折中 (0.5 周)
│   ├── F15 Live evidence adapter (1 周)
│   ├── F16 Dispatch 单发送 (0.5 天)
│   └── F17 Warroom rejected lane (0.5 天)
└── B 末 (~1 周):
    ├── C11 Audit 降级标识 (0.3 周)
    ├── C12 ScanCTA fix (0.5-1 周)
    ├── C13 抽 shared hook (1 周)
    └── C18 Agent1 similarity (1 周)
```

## 4. PM 拍板项 (10 项 · 推荐都 A)

| # | 提案 | 选项 | 推荐 | 理由 |
|---|---|---|---|---|
| 1 | 全屏渐变折中 (主区 #F7F9FC + 装饰区保留 4 主题 Masthead/选中/Hover) | A 接受 / B 全保 / C 全撤 | **A** | 三方 R2 v2 lock · 唯一破点是 platform shell-v2 lock 定稿微调 |
| 2 | 登录页黑洞替换 (3D 几何粒子 OR 极简磨砂玻璃) | A 接受 / B 推 Phase C / C 完全保留 | **A** | Gemini 提权 P1 · B2B 第一印象 · 0.3 周 · 待校验 Interstellar 实验是否舍弃 |
| 3 | A5 跨冲突 UI 分阶段 (B-3 spike 0.3 周 + Phase C 完整 1.5 周) | A 接受 / B 完整 1 周 B-3 / C 全推 Phase C | **A** | Codex 反对没 audit 账本完整不可追责 · Gemini 视觉提示 spike 已含 |
| 4 | Customer Ribbon 折中 (顶部只读 + CustomerContextGateway + 不删 selector) | A 接受 / B Gemini 一刀切 / C 不做 | **A** | Codex 反对一刀切 · 保留 demo/异常切换入口 |
| 5 | Action Card 组件族合并 (含 Stage-aware Primary Action 顶部主卡) | A 接受 / B 拆 | **A** | 复用 HandoffCard + ComposerBar · Codex 提议三方接受 |
| 6 | C14 Evaluation Baseline Gate (Phase B-1 必跑 6 Agent baseline) | A 接受 / B 推 Phase C | **A** | Codex 加补 · 三方都漏的真痛 · 没 baseline live evidence 不可证 Evidence-First · 3-5 天工程量 |
| 7 | F15 Live evidence adapter (P0 critical) | A 接受 / B 推 Phase C | **A** | 6 workspace 全挂 fixture · 反 north-star §3.3 · 必修 |
| 8 | dispatch 不降级到边缘 (per Codex R2 v2 反对 Gemini IM 边缘化) | A 接受 / B Gemini 一刀切 | **A** | dispatch 保留为协作 + command surface · ⌘+K 汇总 |
| 9 | Phase B 不大改 Report+Riskctrl 布局 (Phase C 推) | A 接受 / B Phase B 大改 | **A** | Phase B 资源给 P0 bug · 大改推 Phase C |
| 10 | Codex 6 bug 是否全接 (Bug 1/2/3/4/5/6 · 含 audit 分阶段) | A 全接 / B 部分推 Phase C | **A** | 真 bug 必修 · 已 commit 计划 (F5/F15/F16/F17/C11/C12) |

## 5. 退回命令 (后续优化方案 ship 后 PM 不满意时)

```bash
cd "D:/claude code/credit_report_agent_work"
git fetch --all --tags
git reset --hard phase-a-exit-bugfix-2026-05-01
git push origin main --force-with-lease  # ⚠️ destructive · PM 必须明确同意
bash scripts/deploy_to_ecs.sh             # ECS 同步
```

## 6. PM 拍板后落地

PM 同意 10 项 (or 部分调) → 主 CLI 立即:
1. 写 `docs/reset/phase-b-charter.md` 加 worker-B1 (F1-F6) + worker-B3 (F7-F17) + worker-B 末 (C11/C12/C13/C18)
2. 写 `docs/handoff/decisions-log.md` Q-NNN entry "三方辩论 R3 ratify · 17 action + 分阶段 A5 + Phase C 6 项"
3. commit + push + (本 doc 不需 ECS deploy · 是 spec doc)
4. Phase B 启动 (派 worker-B1 / worker-B2 / worker-B3 · per multi-cli-mesh skill)

## 7. Sign-off

- **R1 v2** 三方齐 (主 CLI a3a7adc / Codex 01d1582 / Gemini conversation turn 4)
- **R2 v2** 三方齐 (本 commit 主 CLI / Codex byo5w849m / Gemini conversation turn 5)
- **R3** 主 CLI 综合 (本 doc · 17 action + 10 PM 拍板项)
- **三方共识高度一致** (5/7 决断完全一致 · A5 dissent 分阶段 · Customer Ribbon 折中)
- **PM 待 ratify 10 项** → Phase B charter 落 → Phase B 启动
