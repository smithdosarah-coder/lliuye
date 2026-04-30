# 三方辩论 R2 · Codex 互检 (主 CLI R1 + Gemini R1)

> Codex high reasoning · sandbox read-only · 主 CLI 落盘代写 · 任务 ID bbiio8mke

## 视觉

同意 Gemini 主判 · 但**不建议把 platform shell-v2 4 主题系统整套废掉**:
- 4 主题确有品牌资产: `tokens.css` 标 shell-v2 4 主题与 lock 来源 · 6 Agent 功能色已成 token (web/src/app/tokens.css:1-5,68-74)
- 但工作台是高频金融生产界面 · 可用性优先于品牌氛围
- 当前 `.shell-root` 是全屏多段渐变和呼吸噪声层 (web/src/app/shell.css:21-29,36-52) · 红色预警语义会被背景稀释
- **结论 折中**: 主题保留为顶栏/按钮/状态/细线 · **不再铺满工作区底色** · 主工作区改中性 `#F7F9FC` 或接近 `--chalk` 的低噪声背景

弃黑洞: agree (web/src/app/login/_components/CosmicStageR3F.tsx:3-8 · login.css:75-84 是 Gargantua/Interstellar 黑洞复刻 · 金融语义负面)

删手写斜体: agree (字体 token 仍有 `--italic` · login 多处 eyebrow/title/separator 用 · web/src/app/tokens.css:24-30 · login.css:211-239,392-411) · 金融工作台统一无衬线中文优先 · display 只用于品牌不进数据区

## IA

**三选一融合**: 主 CLI A3 + Codex C3 先做 · Gemini `/dispatch @` 作为方向但不一口吃下:
- `/archive` 当前是 6 Agent tile 入口 · 文案"每一位助手是独立工作区" (archive/page.tsx:8-12,30-36) · Masthead 一级"AI 助手" (Masthead.tsx:18-22) · 确实偏 Agent 而非客户
- 但立刻 Agent 全搬 `/dispatch @` 扩大风险
- 当前 `/today` AI 助手卡整卡跳 `/dispatch` · running/open 文案装饰态 (TodayContent.tsx:28-38)
- **C3 半天修路由更划算**: AI 助手卡进 `/archive` 或具体 agent/session · 消息/协作仍进 `/dispatch`
- A3 同步弱化 `/archive` 为历史/能力中心 · RM 默认起点回 `/today`

## UX

**A4 与 Gemini Action Card 是同一条链路两层 · 不冲突 · 应合并**:
- A4 = 所有告警就地可处置
- Gemini Action Card = `/dispatch` 聊天流结构化操作卡
- 现有 `/dispatch` 已有 `handoff_card` / 接手退回 / 事件发布 / 阶段推进 (HandoffCard.tsx:53-69,100-116) · Composer `/handoff` 生成卡片+ticket (ComposerBar.tsx:276-302)
- **应合并成 Action Card 组件族**: 告警 / 交接 / 补材料 / 通过 / 驳回 共享

**A5 不反对但反对完整仲裁 UI**:
- 当前有 Agent5 合规冲突矩阵 + dispatch handoff · 但**没有跨 Agent 冲突 schema**
- 检索成熟结构主要是 handoff/ticket · 不是 Agent3 approve vs Agent5 block 的仲裁模型 (types.ts:78,96-114 · ticket-store.ts:271-286)
- **PM mindset 下应降级**: 先做"冲突提示 + 人工裁决记录" P1 spike · 不做完整仲裁引擎
- → 与主 CLI R2 加补 (A5 完整 1 周) 有 dissent · Codex 更保守

## 中文金融

同意把主 CLI A1 scope **升级到 Gemini 颗粒度**:
- 当前 Today 客户金额是 `¥{amount.toLocaleString()} 万` (CustomerRow.tsx:86-89) · 只做了千分位但单位"万元短写" · 不满足金融表格扫描
- 应新增统一 formatter: 内部金额保留元 · 展示支持 `¥50,000,000.00` · tabular figures · 右对齐 · 列表列宽固定
- 已有 `.font-tabular` 但映射到 mono · 不等于金融金额规范 (globals.css:74-77)

术语纯中文 agree:
- MorningBrief 仍有"待办 · Tickets / Alerts / Active" · 待办 hint 明示 mock fallback (MorningBrief.tsx:184-201)
- 改"待办工单 / 今日预警 / 活跃客户 / 流转中任务 / 风险拦截" · 英文只留开发态或命令态

## 加补

**C3 仍要做**: `TodayContent.tsx:28` 整卡跳 `/dispatch` 是低成本错路由 · 0.5 天 quick win

**A2 工程量可从 1.5 周砍到约 1 周**: Agent6→Agent3 链路已存在 · 拉报告 session / POST `/api/credit/handoff/from_report` / 把 `enterprise_profile` 注入 `report_json` 起决策 (CreditWorkspace.tsx:250-323) · 空态 CTA 已接 (CreditWorkspace.tsx:495-501) · 剩余主要是搬到 `/today` RM 工作台 · 不是从零打通

**Hero 真指标必须做**: 根因 `TICKET_FALLBACK_COUNT = 4` 且 stats 直接用 fallback (MorningBrief.tsx:35-37,145-147) · ticket-store 已能订阅 `handoff.requested` 自动建 ticket (ticket-store.ts:271-286) · 与主 CLI A1/A2 方向一致 · 路径点名 C4

## R2 Verdict

接受 Gemini 约 80%: 视觉 / 字体 / 金额 / `/archive` 孤岛判断成立 · 反对"一步撤品牌主题 / Agent 全进 @ 菜单"的激进落地 · 技术上应分阶段。

接受主 CLI 约 75%: A1/A2/A3/A4/A6 成立 · **A5 留问题但降 scope · 先做冲突提示与人工裁决记录** (vs 主 CLI R2 加补 A5 完整 1 周 · 有 dissent)。

补充保留 C3、C4 · 因 Agent6→Agent3 handoff 已在 `CreditWorkspace` 存在 · A2 可从 1.5 周压到约 1 周。
