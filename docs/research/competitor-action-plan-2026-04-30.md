# 竞品借鉴落地方案 · 2026-04-30

> 主 CLI ultrathink · 基于 `competitor-borrow-2026-04-30.md` (sub-agent 竞品分析) · PM 视角 actionable
> 不重复竞品摘要 · 直出: 各自优劣 + 我们落地方案 + 排序 + 风险

---

## 1. 各自优劣对比

### 1.1 我们 vs 南京银行 PDF (科创金融业务方法论)

| 维度 | 南京银行 (优) | 我们 (差) |
|---|---|---|
| 业务方法论 | 18 年科创金融积累 · 六维画像 / 三主看三辅看 / 投贷联动 | 通用四维评分 · 没"懂科创"差异 |
| 真实数据 | 1751 亿累放 · 2 万+科创客户 · 88 创投 + 42 服务机构生态圈 | mock 数据 · 4 角色无真实样本 |
| 组织架构沉淀 | 三支队伍联合会商 · 12 对公场景 + 5 零售场景 LBS | 4 角色协作 contract 未实化 |

| 维度 | 南京银行 (差) | 我们 (优) |
|---|---|---|
| 工具化 | PPT 拍照 62 页 · 业务做法不是产品 · 数智化是辅助 | 6 Agent 矩阵 + Evidence-First + QC blocker · 工具化系统 |
| 信息密度 | 会议室投影 · 文字稀 · 案例为主 | 8 列命名 SSOT + 6 Agent contract + RBAC matrix |
| 重用性 | 业务方法 → 不可直接复用 (要银行自己沉淀) | 平台 + Agent 抽象 · 多家行可复用 |

**结论**: 南京银行有"业务方法论" · 我们有"产品工程化"。借鉴方向: **把南京银行的业务知识沉淀到我们的 Agent rubric / evaluation baseline 里 · 用工具化能力承接业务方法**。

### 1.2 我们 vs 竞品 URL `:13000/` + CRM zip (营销中台 v4.0)

| 维度 | 竞品 (优) | 我们 (差) |
|---|---|---|
| 工作台形态 | modal-driven (10 模块在 modal · 不切路由 · 真 in-context) | 6 路由跳转 (`/archive/[agent]`) · 跳出工作台 |
| 全局命令 | Ctrl+K 聚合搜索 (客户 + 产品 + 策略 3 段 suggestion) | 无全局命令面板 |
| 任务看板 | 任务 = 跨模块联动 (营销 → 风控 → 协同 自动流转) | `/warroom` kanban 是假任务卡 · 没接 handoff |
| Hero 反馈 | "今日效率提升 35.8%" 实时数字给 RM 闭环感 | `/today` Hero 无 metric strip |
| PRD 完整度 | V2.0 2626 行 16 节 · 5 角色 × 12 模块 = 60 RBAC 矩阵 | 6 sub-PRD worker-A7 v1 · RBAC 散在 code |

| 维度 | 竞品 (差) | 我们 (优) |
|---|---|---|
| 技术栈 | Vue3 + jQuery + ECharts CDN · 单页 147 KB inline HTML · 不可维护 | Next.js 16 + TS + Zustand + Playwright + 4 主题渐变 |
| 数据真实 | 全 mock 数据 inline app.js · 无真后端 | 6 Agent 后端 + Evidence-First · 真 SSE + QC + LLM caller 抽象 |
| 视觉设计 | 主色 #1E40AF + 36px 按钮 + 4 状态 · 粗 | shell-v2 4 主题 (Canvas/Matcha/Dusk/Ink) + Float-badge SVG + 8 档渐变 token |
| 角色矩阵 | 5 角色含"产品经理 + 部门领导" · 营销偏 | 4 角色 (RM + 审贷员 + 合规官 + 风险经理) · 信贷场景精准 |
| 验收 / QC | 无 quality gate · demo 跑通即可 | quality_scorer 9 维度 + 反幻觉 + Evidence-First 三阶段 |

**结论**: 竞品的真价值是**产品形态确认了 north star** (modal-driven + Ctrl+K + 实时反馈) · 不是技术。我们工程比它强 · 但 RM 工作流体验落后竞品 1 个迭代。

---

## 2. 落地方案 (排序 · 工程量 · 验收)

按 **优先级 × ROI × 阻塞 north star 程度** 排序:

### 🔴 P0 · Phase B-3 RM workbench charter 必加 (2-3 周)

#### Action 1: `/today` modal-driven 改造 (借鉴点 1 主线)

**对应 north star**: §3.1 "RM workbench 是主角 · 6 Agent 是工作台内可调用能力矩阵 · 不是 6 孤岛页"。

**工程拆解** (3 周 · per worker-B3 charter):
- Week 1: 写 `<AgentDialog kind="report|credit|...">` 通用 modal · Lazy load 6 workspace UI tree
- Week 2: `/today` Hero 6 Agent tile · 点击开 modal (不跳路由) · ESC + click outside 关
- Week 3: handoff schema 接管 modal 间数据传递 (modal A close → modal B auto-open with payload)

**验收 (DoD)**:
- RM 全程不离 `/today` · 6 Agent 全部 modal 内调用完整一单 (Agent1 → 6 → 3 → 4 → 5)
- modal 内 SSE / form / export 全 work · 不退化
- `/archive/[agent]` 路由保留为 deep-link (legacy URL 不 break · 客服转发链接仍工作)

**风险**:
- Modal 嵌套 SSE 取消逻辑 (打开/关闭 modal 时 abort fetch) · 需 useEffect cleanup 严格
- handoff payload schema 跨 modal 传递 · 用 zustand store 中转
- 6 个 workspace UI 抽出 modal 形态 · 可能要 refactor 而非简单 inline (尤其 ReportWorkspace 1832 行复杂)

**产出**:
- `web/src/app/today/page.tsx` 改造 · `<AgentDialog>` 组件 · 6 modal wrapper
- `docs/contracts/modal-state-protocol.md` (新 · modal 间 handoff 数据传递契约)

#### Action 2: Agent3 评分按客群分模板 (借鉴点 2 主线 · 科创六维画像)

**对应 north star**: §2.4 "懂科创" 是城商行第一卖点 · Agent3 当前通用四维 = 不懂业务。

**工程拆解** (1.5 周):
- Day 1-2: 写 3 个 segment baseline:
  - `evaluation/agent_credit_kechuang.yaml` (科创六维: 产业/技术/融资/团队/业务合作/政策)
  - `evaluation/agent_credit_corp.yaml` (对公: 财务 + 经营 + 同业)
  - `evaluation/agent_credit_inclusive.yaml` (普惠: 团队 + 还款来源 + 经营场景)
- Day 3-4: `truth_fill.py` 加 `infer_customer_segment()` 确定性规则:
  ```python
  def infer_customer_segment(profile: dict) -> str:
      # 注册年限 + 营收 + 融资轮次 + 行业代码 → 科创/对公/普惠
      if profile["industry_code"] in ["软件", "新能源", "生物医药", "电子"]:
          if profile["funding_rounds"] >= 1 or profile["years_since_founding"] < 5:
              return "kechuang"
      if profile["annual_revenue"] >= 5000_0000:
          return "corp"
      return "inclusive"
  ```
- Day 5-7: `agent_credit/api.py` dispatch by segment · prompt 8 段 contract 加 segment context
- Day 8-10: 写 mock 客户样本 3 segment × 3 难度 (per CLAUDE.md §3.5 5 原则) · 验 evaluation baseline

**验收 (DoD)**:
- 输入科创企业 → 出六维画像 + 团队/经营/未来加权评分 · 财务降权
- 输入对公企业 → 出财务三大表 + 经营 + 同业评分 · 财务正常权重
- 输入小微企业 → 团队 + 还款来源加权 · 不强行套财务模板
- 评估通过率: 3 segment 各跑 baseline · field_completeness ≥ 0.85 · evidence_rate ≥ 0.90

**风险**:
- segment 推断错 (e.g. 科创但传统行业代码) · 加用户手动 override UI
- 客群 baseline yaml × 3 维护成本 · 通用部分抽 `agent_credit_common.yaml` base + segment 增量

**产出**:
- 3 个 segment yaml + truth_fill segment 推断 + agent_credit dispatcher + 9 mock 样本 + 3 evaluation 报告

---

### 🟡 P1 · Phase B-1 数据飞轮顺带做 (1.5 周)

#### Action 3: 任务看板真接 handoff (借鉴点 4 前半)

**工程量**: 1 周 · 复用 `docs/contracts/agent-handoff-schemas.md` worker-A6 已落 contract。

**拆解**:
- Day 1-2: `/warroom` 4 列 kanban 接 handoff event subscriber (Agent6 报告 done → push "等 Agent3 评分" 任务卡)
- Day 3-4: 任务卡状态机 (待办→进行中→待审→完成) 跟 Agent stage 联动
- Day 5-7: RM 任务卡可点击直接跳到对应 Agent modal (借 Action 1 modal 系统)

**验收 (DoD)**:
- 1 单从 Agent1 拉到 Agent5 全程任务卡自动流转 · RM 不手动建任务
- 任务卡含: 客户名 / 当前 Agent / 上一步产出 / 下一步操作 / SLA 时长

#### Action 4: `/today` Hero 实时效率指标 strip (借鉴点 4 后半)

**工程量**: 0.5 周。

**拆解**:
- Day 1: 后端 endpoint `GET /api/today/metrics` 聚合 (Agent4 hit_list count / Agent3 完件数 / Agent6 done count · 含日同比 + 周同比)
- Day 2: 前端 `<MetricStrip>` 组件 3-5 数字 chip · per agent tone color
- Day 3: 接 zustand · poll 每 30s

**验收**: `/today` Hero 显式 "今日处理 N 单 / 红线命中 M 件 / 报告生成 K 份" · KPI 实时反馈 RM。

---

### 🟢 P2 · Phase B 末 · 增量优化 (1.5 周)

#### Action 5: Agent1 Look-alike 增强 (借鉴点 3)

**工程量**: 1 周 · F-005 fix-forward 路径。

**拆解**:
- Day 1-2: `agent_channel/sources_config.py` 加 "internal_customer_kb" 源 (读 `customer/` 已成交客户)
- Day 3-4: similarity 算法权重: 50% 已成交相似 + 30% 行业 + 15% 区域 + 5% 规模
- Day 5-7: 加 12 场景预设 ("新成立 < 1 年" / "新中标" / "新获 PE/VC" 等) → SearchProvider 不同 query template

**验收**: 候选客户列表显式标"内源 (已成交) vs 外源 (Tavily)" · similarity 4 维度 explainable。

#### Action 6: 全局 Ctrl+K 命令面板 (借鉴点 1 后半)

**工程量**: 0.5 周 · 加 `<CommandPalette>` (cmdk 风格 + shell-v2 token)。

**拆解**:
- Day 1: `web/src/components/shell/CommandPalette.tsx` 全局 Cmd+K / Ctrl+K trigger
- Day 2: 聚合 3 段 suggestion: 客户 (cust_*) / Agent 调用 (/agent6 出报告) / 历史会话 (thread_*)
- Day 3: 接 zustand store · 本地索引 (不依赖 backend)

**验收**: Cmd+K → 输入 "张总" → 看到 客户列表 + 相关 Agent 调用历史 + 跳转。

---

### ⚫ P3 · 不做 (治理债)

- **5 角色权限矩阵单表化** (借鉴点 5): 等 worker-A1 SSOT v2 顺带补 · 不主动启动
- **PRD 16 节模板套** (借鉴点 5 后半): 我们 6 sub-PRD 已 worker-A7 v1 落地 · 增量 fix-forward · 不重写

---

## 3. 总体路线图 + 工程量 + 排期

```
Phase B (假设 4-6 周 · 现 Phase A 收尾中)
├── Week 1-3 (Phase B-3 RM workbench · 🔴 P0):
│   ├── Action 1 modal-driven 改造 (3 周 · main path)
│   └── Action 2 Agent3 segment 评分 (1.5 周 · 并行)
├── Week 4 (Phase B-1 数据飞轮顺带 · 🟡 P1):
│   ├── Action 3 任务看板真接 handoff (1 周)
│   └── Action 4 Hero 实时指标 (0.5 周 · 并行)
└── Week 5-6 (Phase B 末 · 🟢 P2):
    ├── Action 5 Agent1 Look-alike 增强 (1 周)
    └── Action 6 全局 Ctrl+K (0.5 周 · 并行)
```

**总工程量**: ~8 周 worker-time · 含并行可压到 5-6 周 wall-clock。

**核心 ROI 排序**:
1. Action 1 (modal-driven) → 直接拉齐 north star · UX 体感最强
2. Action 2 (科创六维) → 体现"懂业务" · 城商行客户 sales pitch 关键
3. Action 3 (handoff 实化) → handoff contract 终于真用上
4. Action 4 (Hero 指标) → RM 反馈循环闭环
5. Action 5/6 → 增量优化

---

## 4. 风险 + 不做的边界

### 4.1 主要风险

| 风险 | 缓解 |
|---|---|
| Action 1 modal 化破 6 workspace 现有 UI 投入 | Feature flag · 双轨过渡 · `/archive/[agent]` 留 deep-link |
| Action 2 segment 推断准确率 | 用户手动 override UI · evaluation baseline 跑前 dry-run |
| 工程量超 6 周 | Action 5/6 推到 Phase C · P0+P1 优先 ship |
| 银行客户对"科创"细分敏感 (e.g. 城商行无科创支行) | 提供"通用对公"作为默认 fallback segment · 不强制选 |

### 4.2 不做的边界 (per CLAUDE.md §3 红线)

- ❌ 不做"投贷联动 / 五融生态" (银行业务创新 · 不是 AI 工具 · 模糊产品边界)
- ❌ 不做"产品经理 / 部门领导"角色 (营销中台风 · 偏离信贷场景)
- ❌ 不做单页 inline HTML 架构 (技术倒退 · 不可维护)
- ❌ 不做"社交 / IM" 功能 (我们 `/dispatch` 是 Agent 协作 IM · 不是企业内 IM)

---

## 5. PM 拍板项 (我提案 · 等你批)

| # | 提案 | 选项 | 推荐 |
|---|---|---|---|
| 1 | Phase B-3 RM workbench charter 是否加 Action 1+2 | A) 加 (P0 必做) · B) Action 1 加 · Action 2 推 Phase C · C) 都推 | **A** (north star 直击) |
| 2 | Agent3 segment 命名 | A) 科创/对公/普惠 · B) 科创/对公/小微 · C) 行业自定义 | **A** (与南京银行术语对齐) |
| 3 | 任务看板真接 handoff (Action 3) 在 Phase B-1 还是 Phase B-3 | A) B-1 (数据飞轮顺带) · B) B-3 (与 modal 一起) | **A** (handoff contract 已就绪 · 不依赖 modal) |
| 4 | Action 5/6 是否推 Phase C | A) 推 (Phase B 不做) · B) 留 Phase B 末 (周 5-6) | **B** (Ctrl+K + Look-alike 都是体验加分项 · 客户演示有用) |
| 5 | "科创六维" 是否作为 worker-B2 商业化 doc 的核心 sales pitch | A) 是 · B) 否 (作为 1 个 feature 不主推) | **A** (城商行第一卖点) |

---

## 6. Sign-off

- 起草: 主 CLI ultrathink (基于 sub-agent `competitor-borrow-2026-04-30.md`)
- 待 PM 拍板: §5 表 5 项
- 落地后回写: `docs/reset/phase-b-charter.md` 加 worker-B3 RM workbench (Action 1+2) + worker-B1 (Action 3+4) + decisions-log Q-NNN entry
