# 三方辩论 R1 · Main CLI 独立前端方案 (产品 PM 视角)

> R1 独立草案 · 不预设 Gemini / Codex · 三方 R1 全出齐后进 R2 互检

## 视角

主 CLI = 产品 PM 视角 (4 角色: RM 客户经理 / 审贷员 / 合规官 / 风险经理 · 银行金融场景 · Evidence-First)
- vs Gemini = 视觉/审美/IA 视角
- vs Codex = 技术/逻辑/工程量视角

## 1. 真痛点 (按 RM 工作流顺序排)

### 1.1 `/today` 不像 RM 工作起点 · 像 dashboard (P0)
- **现状**: `/today` Hero + 4 view 切换 + Agent tile · 缺 RM 真用的"客户列表 + 客户卡 + 进度"
- **证据**: design_mockups/rm-assistant-final-2026-04-19.html 是 lock 定稿但 Phase A 没全实现 · north-star §3.1 已写
- **影响**: RM (主用户 · 80% 时间在这页)

### 1.2 数字/文案不专业 · 无千分位 · 极客腔 (P0)
- **现状**: ¥1500万 / "Tickets" / "pinged" / "agent 正在跑" / "stage 权重" 等
- **证据**: web/src 多处 workspace 文案 + 无千分位 utility
- **影响**: 4 角色全受影响 (银行客户对数字格式敏感 · bank delivery DoD 已要求千分位)

### 1.3 Agent 视角主导 vs RM 视角主导 (P0 · 产品定位偏)
- **现状**: 6 Agent tile 在 `/archive` 平铺 · RM 进 `/archive/[agent]` = 选 Agent 工作 = 反向逻辑
- **应该**: RM 进 `/today` 选客户 → Agent 按客户阶段自动介入 (Cursor 模式)
- **证据**: north-star §3.1 ratify "workbench 主角 · Agent 是工作台内能力矩阵 · 不是 6 孤岛页"
- **影响**: RM (Agent 是工具 · 不是用户)

### 1.4 告警 / 待审 / handoff 无 inline actionable (P1 · UX 漏)
- **现状**: 合规告警 = 静态卡片 (read-only) · RM 看到要切页面才能处置
- **应该**: inline actionable card (阻断 / 忽略 / 升级 一键)
- **证据**: ComplianceWorkspace.tsx 现有 detail drawer 但缺 action button
- **影响**: 合规官 + RM

### 1.5 6 Agent 跨 agent 冲突无 UI 仲裁 (P1 · 产品深问题)
- **现状**: Agent3 (ROI=A) + Agent5 (BLOCK) 冲突时 UI 不显冲突 + 不显仲裁
- **应该**: `/dispatch` thread 打"⚠️ 冲突待仲裁" + 显冲突点 + 审贷员一键裁决 (RBAC final arbiter)
- **证据**: 当前 handoff schema 没 conflict resolution view · Evidence-First 仅单 agent 内自审
- **影响**: 审贷员 (final decision maker)

## 2. 推荐 action (按 ROI × 工程量排)

### Action A1: 千分位 + 信贷术语清洗 (P0 · ~2h · main CLI 一上午)
- **改**: web/src grep "¥" + 数字 → 加 Intl.NumberFormat('zh-CN') utility · 文案统一信贷语料
- **验收**: 4 角色 view 全数字含千分位 · 0 极客腔
- **风险**: 低 (text replacement)
- **Phase**: B-1 (周内可做 · 立即 ROI)

### Action A2: `/today` 真 RM 工作起点改造 (P0 · ~1.5 周)
- **改**: 客户列表 first (左栏可搜) + 客户卡片 (中栏) + Agent suggestion 按阶段自出 (右栏)
- **验收**: RM 进 `/today` 立即看自己客户列表 · 不需选 Agent
- **重叠**: 与竞品 v2 Action 1 (modal-driven) 是同一改造的具体形态
- **风险**: 中 (refactor /today)
- **Phase**: B-3 (与竞品 Action 1+2+3 同 sprint)

### Action A3: Agent 视角下沉 · `/archive` 弱化 (P1 · ~0.5 周)
- **改**: `/archive` 改"AI 助手历史 + 调用入口"低频 access · `/today` 是 RM 默认页 (登录后跳)
- **验收**: RM 80% 时间在 `/today` · `/archive` 仅 audit/历史看
- **风险**: 低 (IA 调整 · 不破现有 page)
- **Phase**: B-3 (与 A2 同 sprint)

### Action A4: 告警 actionable inline (P1 · ~0.5 周)
- **改**: ComplianceWorkspace 告警 + 任何 inline 告警卡加 "阻断/忽略/升级" 三 button
- **验收**: 合规官点告警 → 立即处置 · 不切页 · 不跳路由
- **风险**: 低 (UI 加 button + handler)
- **Phase**: B-3

### Action A5: 6 Agent 跨冲突 UI 仲裁 (P1 · ~1 周 · 产品深问题)
- **改**: `/dispatch` thread 冲突 detect → "⚠️ 冲突待仲裁" + 显冲突点 + 审贷员裁决
- **验收**: 1 单 Agent3+Agent5 冲突 → UI 显式 · 审贷员一键裁决
- **风险**: 中 (产品深问题 · 设计 + 实现并重)
- **Phase**: B-3 (与 A2+A3+A4 同 sprint · RM workbench 完整闭环)

### Action A6: 登录页视觉重设计 (P2 · ~0.3 周)
- **改**: Interstellar 黑洞 → 中性数据网格 + 微光呼吸 (保品牌实验感 · 但金融语境正向)
- **验收**: 登录页不让银行客户联想"资金被吞"
- **风险**: 低 (登录页独立)
- **Phase**: B 末 (PM 此前定 Interstellar 是品牌实验 · 需 PM 重新校验)

## 3. 反对借鉴 / 不做

### 不做 1: 6 Agent 全 modal 一步到位 (per Codex v1 + 主 CLI v2 已撤)
- 单链路 Agent6→Agent3 先验 · Phase C 加 Agent4/5

### 不做 2: 装饰 KPI ("今日效率提升 35.8%" 类) (三方一致 · 反 Evidence-First)
- 只保留待办数 + SLA (真数据)

### 不做 3: 抄竞品 5 角色 (产品经理 + 部门领导)
- 我们 4 角色 (RM + 审贷员 + 合规官 + 风险经理) 更贴信贷场景
- 产品经理是 PM 自己 · 不是客户

## 4. 主 CLI R1 verdict (≤ 200 字)

PM 反硬改 mindset 自检 · 6 action 全过得了"理有据有可行性"门槛:
- A1 (千分位/术语) · A4 (actionable) 是主 CLI 自己能做的 quick win (P0/P1 · ~2-3h+0.5周)
- A2 (`/today` 改造) + A3 (Agent 下沉) + A5 (冲突 UI) 是 Phase B-3 RM workbench 必做 (与竞品 v2 Action 1+2+3 重叠)
- A6 (登录黑洞) 待 PM 重新校验品牌实验是否保留

总 Phase B 工程量 ~3.5 周 (含并行 · A1+A4 ~3h 立做 · A2+A3+A4+A5 ~3 周 B-3 sprint)。

**核心**: RM workbench 北极星没漂 · Phase B-3 把 modal-driven + 信贷文化 + 冲突仲裁 一起做 · 不为竞品/Gemini 装饰加项。
