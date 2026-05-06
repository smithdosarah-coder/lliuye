# Phase C · 产品化 Charter

> **目标**: Demo → 真正可用产品 (production-grade · 真客户真业务能跑)
> **建立**: 2026-05-06 · Claude+Codex R1+R2+R3 三轮辩论 + final verify
> **下一步**: PM 拍板 5 decision points → 用 `make-plan` skill 冻结 MVP → `multi-cli-mesh` + `do` 启动

---

## 1. 核心论点

**产品化 = 工程铁三角 (数据可信 + 状态可靠 + 可观测可恢复) + 业务闭环可验证**

> Codex R3 关键洞察: MVP 应**端到端业务流程优先 · 工程支撑层并行 · 业务指标看板第三 · 数据质量横切 critical foundation**.

---

## 2. 四 Track 总览

### Track A · MVP 端到端流程 (~3-4 人周 · 客户走访前必 ship)

| # | 项 | MVP 验收标准 |
|---|---|---|
| A1 | 客户画像聚合 | 输入客户 ID → 页面展示 CRM mock + 征信摘要 + 历史交互 统一画像 |
| A2 | AI 决策建议 | 输出建议 + 原因 + 置信度 + 数据来源 |
| A3 | 人工确认工作台 | RM 接受/修改/驳回 AI 建议 + 留下原因 |
| A4 | 审计日志 | 每次 AI 建议/人工操作/导出动作有时间/操作者/输入/输出/版本记录 |
| A5 | 走访导出物 | 生成 PDF/DOCX 走访报告 · 内容与确认后建议一致 |
| A6 | 端到端 demo 流 | 从客户选择→建议确认→导出 · 10 min 内稳定跑通 |

### Track B · MVP 工程支撑 (~1.5-2 人周 · 并行 A)

| # | 项 | MVP 验收标准 |
|---|---|---|
| B1 | 数据血缘模型 | 每个关键字段追到来源系统/字段/抓取时间/转换规则 |
| B2 | 血缘 UI/接口 | 点击 AI 建议关键结论 → 看支撑数据链路 |
| B3 | CRM mock contract | 前后端基于固定 schema 对接 · mock 数据可替换为真 CRM (15 字段见 §3) |
| B4 | 异常/缺失数据处理 | 关键字段缺失时 AI 不硬判 · 显缺失项 + 人工补充入口 |

### Track C · MVP 业务看板 (~0.5-1 人周 · 客户走访后第 1 周)

| # | 项 | MVP 验收标准 |
|---|---|---|
| C1 | 业务指标看板 | 按客户经理/客户/时间 查看转化/卡点/人工介入等核心指标 (5 指标见 §5) |

### Track D · 全栈数据质量 (~2.5-3.5 人周 · critical foundation · 横切 6 Agent)

> **Codex R3 升级**: 这是系统性问题不是 Agent1 单点 bug · Agent3/4/5/6 都依赖外部事实/政策/信号/财报/案例 · 必统一做.

| # | 项 | MVP 验收标准 |
|---|---|---|
| D1 | 数据源 Tier 化 | 4 Tier 分层 (内部权威/政府监管/行业/公开 web) · 推荐核心理由禁用 Tier 4 单一来源 |
| D2 | 证据时效硬约束 | 每条 evidence 必带 `evidence_date` + recency 加权 + prompt 时效约束 + QC freshness 维度 |
| D3 | Tavily 用法分级 | 通用 web 仅作背景上下文 · 不用核心推荐理由 · 必交叉 Tier 2-3 |
| D4 | 推荐理由 schema 化 (Codex 加) | 每条 recommendation 含 `source_tier / source_url / evidence_date / retrieved_at / freshness_days / claim_type / reason_confidence / staleness_policy_passed` |
| D5 | 数据血缘扩展 (与 B1 合并) | 加 source tier + evidence_date + retrieval_at + effective_date · UI 警告 evidence > 12m |
| D6 | 业务真实场景测试集 | 5-10 真实金融案例 (脱敏 · 含脏/老/异常数据) · 业务专家 walkthrough · CI 跑过才 ship |
| D7 | 业务专家 review 流程 | 每 PRD 必含"业务专家 review"步骤 · sign-off 才进 ship · monthly walk-through |
| D8 | CLAUDE.md §3.5 制度化 | 加 #6 "数据时效 + 业务质量双轨验证" + 负反馈闭环 (PM 露馅样例 → regression case + source blacklist + freshness rule) |
| D9 | 6 Agent 全栈 audit | Agent1 候选信号 + Agent5 政策时效 + Agent4 预警信号 + Agent6 财报数据 + Agent3 同行案例 + Agent2 历史样本 全 freshness 校验 |

**Track D 实施顺序 (Codex R3 verbatim)**: D1 → D2 → D3 → D4/D5 → D6 → D7 → D8 → D9 (标准/契约先 · 测试/制度后)

---

## 3. CRM Mock Contract · 最小 15 字段

```yaml
customer_id: string  # 主键
name: string
age: int
mobile_masked: string  # 138****5678 脱敏
city: string
occupation: string
income_monthly: number
employment_status: enum [employed | self_employed | retired | student | unemployed]
existing_products: list[string]  # 现持产品
credit_score: int
debt_ratio: float  # 0.0-1.0
risk_level: enum [conservative | balanced | growth | aggressive]
last_contact_at: timestamp
relationship_manager_id: string  # RM 工号
consent_status: enum [granted | pending | revoked]
```

**冻结策略**: 15 字段 + 枚举值 + 空值策略 + 版本策略 一次冻 · 后续仅 additive change · breaking change 走 RFC.

---

## 4. 证据链关系 (三联追溯)

```
source_field → lineage_id → decision_id → audit_event_id → export_id
```

- **audit_event**: 谁在何时触发 / 模型版本 / 输入快照 hash / 输出建议 / 人工动作
- **lineage**: decision_id 用了哪些字段 · 每字段来自系统/表/字段/时间点/转换规则
- **export**: PDF/DOCX 带 export_id · 引用 decision_id / 确认版本 / 导出时间 / 文件 hash

> 从导出物反查 AI 结论 → 追到输入数据 → 人工确认动作

---

## 5. 业务指标 5 件 (Track C 看板)

1. **闭环转化率** — AI 建议后完成走访/办理 比例
2. **卡点分布** — 流程停在画像/建议/确认/导出/客户确认 占比
3. **人工介入率** — AI 建议被修改/驳回 比例
4. **客户确认率** — 客户接受/确认下一步 比例
5. **建议采纳后收益** — 采纳后产生 授信/理财/保险/贷款 金额

---

## 6. 监控 SLA 6 项 (Codex R 加)

1. **Freshness SLA** — 核心证据超阈值报警 (新闻 >180d / 财报 >120d / 监管处罚 >365d)
2. **Tier Mix 报警** — 核心理由 Tier 3/4 占比过高
3. **Stale Evidence Rate** — 按客户/行业/agent/数据源 统计过期证据率
4. **No-Date Evidence 报警** — 无 evidence_date 的核心理由 fail/降级
5. **Drift Sampling** — 每天抽 N 条推荐理由 业务专家+LLM judge 双审
6. **PM Feedback → CI Case** — 每条线上露馅样例必进回归集

---

## 7. 风险 Top 3

| # | 风险 | 缓解 |
|---|---|---|
| 1 | 🔴 **数据看似自动化但没人敢用** (缺证据链/解释/人工兜底) | Track D 全做 + Track A4/A5 (审计+导出) |
| 2 | 🟡 **CRM mock vs 真实差异过大** (后期集成推翻) | B3 contract 早期冻结 + 客户联调 |
| 3 | 🟡 **AI 建议不可控** (口径不稳/合规风险/不可解释) | A2 置信度 + 来源 + D4 schema 化 + A4 审计 |

---

## 8. 总时间表 (Codex R 估)

- **Track A**: 3-4 人周
- **Track B**: 1.5-2 人周 (并行 A)
- **Track C**: 0.5-1 人周 (依赖走访)
- **Track D**: 2.5-3.5 人周 (critical · 横切 6 Agent)

**总有效人周**: 6-8

**日历期**:
- 2-3 人并行: **4-6 周**
- 单 CLI 主导: **7-9 周**

---

## 9. 依赖关系图

```
Track A (端到端流程)  ─┬─ A1→A2→A3→A4→A5→A6 (sequential)
                      │
Track B (工程支撑)     ─┴─ B3 (CRM contract) 必先 → A1
                          B1+B2 (血缘) 与 A2/A3 并行
                          B4 (异常处理) 横切 A 全程

Track D (数据质量)     ── D1→D2→D3 (标准先) → D4+D5 (并 B 合)
                          D6+D7+D8 (制度) → D9 (6 Agent 全栈 audit)
                          *D 阻断 A2 (AI 决策建议) ship 前必先 D1+D2*

Track C (看板)         ── 客户走访 + Track A 验收后启
```

**依赖硬线**:
- A1 客户画像 ← 依赖 B3 CRM contract
- A2 AI 建议 ← 依赖 D1+D2 (Tier + freshness · 否则 ship 出 10 年前新闻)
- A4 审计 ← 依赖 B1 数据血缘
- A5 导出物 ← 依赖 A2/A3/A4 全 ship
- C1 看板 ← 依赖 A6 端到端跑通后取真数据

---

## 10. PM 必拍 5 个 Decision Points (PM 拍板才能开干)

### DP1 · MVP 范围
**问题**: Track ABCD 全 MVP 还是只 Track A+B+D · Track C 延后?
**默认**: Track A+B+D MVP · Track C 走访后第 1 周
**风险**: 全 MVP = 6-8 人周 · 客户走访可能等不及

### DP2 · CRM contract 冻结
**问题**: 15 字段 + 枚举 + 空值 + 版本策略 现在冻结吗?
**默认**: 现在冻结 · 后续 additive only · breaking change 走 RFC
**风险**: 客户给真 CRM 时字段不一致 · adapter 层吸收

### DP3 · 证据链强度
**问题**: 哪些决策必须有 lineage+audit · 缺证据是否 block?
**默认**: AI 决策建议 (A2) + 走访导出 (A5) 必须 · 缺核心证据 block
**风险**: block 严会让 demo 跑不动 · 不 block 会重复 Agent1 露馅事故

### DP4 · Freshness SLA
**问题**: 各 Agent 数据过期阈值 + 降级策略
**默认 (Codex 给)**: 新闻 >180d / 财报 >120d / 监管处罚 >365d / 政策 >365d / 同行案例 >730d
**风险**: 阈值松了仍露馅 · 紧了 evidence 不够

### DP5 · 上线策略
**问题**: shadow mode / human review / partial rollout / rollback?
**默认**: 客户走访演示用 partial rollout (5 用户内部) · 客户银行真接入用 shadow mode + human review (前 2 周 RM 必审 AI 建议)
**风险**: shadow mode 做不好 RM 体验差

---

## 11. 客户走访 SOP (8 节)

1. **走访目标与假设** (这次走访验证什么 · 不期望验证什么)
2. **角色清单**: 销售 / 风控 / 运营 / 管理层 各自 demo focus
3. **现流程 mapping** (银行内现工作流 · 我们 fit 哪步)
4. **CRM 字段验证** (我们 15 字段 contract vs 客户真 CRM 差异)
5. **决策解释与证据需求** (客户问"凭什么推荐" · 现场可答 evidence link)
6. **看板指标优先级** (5 指标对客户哪几个最关心)
7. **FAQ**: 数据缺失 / 错误解释 / 人工覆盖 / 审计追溯 / 更新频率
8. **输出模板**: 问题 / 影响 / 优先级 / owner / 是否进 R3

---

## 12. 验收口径 (Done Definition · per Track)

| Track | UAT 标准 |
|---|---|
| A | 5 角色登录 + 端到端走 6 件 demo flow + 截图存档 |
| B | tsc clean + Python pytest pass + UI 点击 lineage 可达 + 缺失字段降级 demo |
| C | 看板 5 指标 mock 数据可显 · 真接产品后真值替 |
| D | 6 Agent 全跑 freshness audit · 0 条核心证据 evidence_date 缺失 / >12m |

---

## 13. RACI (主 CLI 主导 · 后续可加业务)

| 项 | R 负责 | A 拍板 | C 咨询 | I 知会 |
|---|---|---|---|---|
| Track A | 主 CLI | PM | Codex (technical) | 业务专家 |
| Track B | 主 CLI | PM | Codex | — |
| Track C | 主 CLI | PM | Codex | — |
| Track D | 主 CLI + Codex | PM | 业务专家 (D6/D7) | — |
| 业务专家 review (D7) | 业务专家 | PM | Codex+Claude | 主 CLI |
| 客户走访 | PM | PM | 主 CLI (技术答辩) | — |

---

## 14. Skill 调用 final 调度

| Skill | 用在哪 |
|---|---|
| `make-plan` | 现在: 冻结 R3 MVP 范围 + 验收 + 依赖 → 写各 Track sub-plan |
| `do` | 按 Track A/B/C/D 执行 (含 plan 阶段执行) |
| `multi-cli-mesh` | Track A+B+D 并行 (主 CLI 协调 + worktree mesh 跑分支) |
| `webapp-testing` | A1-A6 端到端走访流 + B2 血缘 UI + C1 看板 e2e 验证 |
| `browser-automation` | 录制走访 demo 操作路径 (替代手动截图) |
| `xlsx` | CRM mock 数据 + B1 血缘字段表 + 5 指标样例 |
| `docx` | A5 走访报告模板 + 银行培训手册 |
| `pdf` | A5 最终导出物 verify 与确认版本一致 |

---

## 15. PM 拍板后立即开干顺序

1. **PM 拍 5 decision points** (DP1-5 · ~10 min)
2. 主 CLI 用 `make-plan` 冻结 R3 charter (本文档) · 写各 Track sub-plan (~30 min)
3. 主 CLI 用 `multi-cli-mesh` 起 worktree mesh (Track A+B+D 并行 worker)
4. **第 1 周 sprint goal**: B3 (CRM contract 冻) + D1-D3 (Tier + freshness 标准 + Tavily 分级) + A1 (客户画像聚合 起)
5. **后续按 dependency 推 4-6 周** (2-3 人并行)

---

## Appendix · 5 层根因 + 5 反思 (Agent1 案例 · CLAUDE.md §3.5 改造源动力)

**5 层根因**:
1. 数据时效未设计
2. 数据源 Tier 错误 (Tavily 通用 web 当核心来源)
3. 无证据生命周期管理
4. Prompt 无时效约束
5. QC 闸缺 evidence_freshness 维度
+ Codex 加 6: 推荐理由缺可审计结构化字段
+ Codex 加 7: 缺负反馈闭环 (PM 露馅样例没沉淀成 regression)

**5 反思条**:
a) demo 优先 · 真生产数据未验
b) 测试集偏 mock 干净
c) 业务专家 review 缺位
d) Evidence-First 协议盲点 (Evidence ≠ Recent)
e) PRD 数据源未 specify

---

**status**: PM 待拍 5 decision points · 拍后立即开干
**source**: Claude R1+R2+R3 + Codex R1+R2+R3 + Codex final verify
**signal**: PHASE-C-CHARTER-DRAFT-2026-05-06
