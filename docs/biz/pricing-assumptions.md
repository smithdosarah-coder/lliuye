# 定价假设 v1.0 · 信贷 6 Agent 矩阵商业化

> ⚠️ **OBSOLETE / REFERENCE-ONLY (Q-052 · 2026-05-04 · PM ratify)**: 本 doc 不再是 Phase B 验收硬线 (charter v2 #2 OBSOLETE) · PM 不审本 doc · 商务团队 if 引用须二次确认 · 众安信科商务团队负责定价 / 销售 / 友商对位 / 异议 FAQ · 永不实装 multi-tenant (客户本地化部署 = 天生系统隔离) · 详 `docs/handoff/decisions-log.md` Q-052

> **版本**: v1.0 · 2026-05-04 · worker-B2-biz (Phase B Sprint 2 · BE11 doc-only · per Codex R2 缩 scope 反对实装)
> **性质**: **架构假设 + 市场锚点 doc**, 不是定价合同 / 不是采购报价单 / 不是客户对外商务文件
> **审稿对象**: 主 CLI / PM / 销售 lead · 不发客户 (per `phase-b-charter.md` line 100-108 红线)
> **下游**: `sales-playbook-v1.md` 报价话术 + `trial-flow-assumptions.md` POC 转化口径 + Phase C 真实装 reference

---

## 0. 范围界定 (per Codex R2 BE11 缩 scope · `BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` line 52)

**做**:
- 定价档位 + 计费维度 + per-Agent / per-seat / per-call 三维模型
- 市场对标锚点 (壹账通 Smart Lender / 同盾诸葛 / 百融 CybotStar / 拓尔思拓天 / Gamma)
- 客户付费意愿假设 + ROI 模型骨架 (供 sales-playbook 引用)
- 不同档位对应的功能 / SLA / 数据隔离差异

**不做** (per Codex R2 + PM 拍板 #6):
- ❌ 真 isolation / metering / billing 实装 (推 Phase C 或已签 POC 前置)
- ❌ 客户 quote letter / RFP 应答模板 (按客户定制 · 不放 doc)
- ❌ 合同条款 / SLA 法律文本 (法务出 · 非 worker scope)
- ❌ 当前真实 cost 反推 (没真实流量数据 · 不凭印象编)

---

## 1. 锚点 · 市场基线 (2025 真实成交数据)

数据来源: `docs/scorecard/definition-of-done.md` §0 证据 1 + 用户 memory `reference_market_benchmark_2025.md`。

| # | 对标产品 | 公开成交锚 | 对应我方 Agent | 对位含义 |
|---|---|---|---|---|
| 1 | 金融壹账通 Smart Lender | 报告自动化率 80% / 审批 1 日 / 客户经理效能 6 倍 | **Agent6 报告 + Agent3 授信** | 对标"贷前 + 授信"打包定价锚 |
| 2 | 金融壹账通 Gamma | 国有大行 100% / 股份行 100% / 城商行 99% 渗透 | **Agent3 授信** | 市场容量饱和 · 增量靠差异化 (decision graph + peer_gap) |
| 3 | 同盾诸葛金融大模型 | 风险识别 78%→94% / 误报 -45% / 人工误判 -72% | **Agent2 风控 + Agent4 预警** | 性能基线 · KS / 通过率 / 误报率口径锚 |
| 4 | 百融 CybotStar | 950+ 区域银行覆盖 | **Agent1 获客** | 区域银行密度大 · 单笔金额低 (per-seat / per-call 适配) |
| 5 | 拓尔思拓天大模型 | 单笔合同 ~2000 万 | **6 Agent 矩阵打包** | 一次性买断 + 私有化部署锚价 |
| 6 | 2025 银行业大模型中标 | 290 个 / 15.06 亿合计 | **整体市场锚** | 平均单笔 ~520 万 · 长尾偏小行 / 单 Agent |
| 7 | 助贷新规 + CAC AI 治理 2.0 + 商业银行互联网贷款管理办法 | 自主风控 + 备案 + 可解释强制 | **L2 合规层** | 规则强制 = 必须配 Agent5 合规 + 决策 ledger (per CLAUDE.md §3.7.5) |

**锚点结论**:

- **整体市场单笔均值 ~500 万 (290 单 / 15 亿)** → 6 Agent 打包定价区间 **300-800 万** 合理
- **头部产品 2000 万 / 单 (拓尔思)** → 私有化 + 信创 + 全 Agent + SLA 套餐顶价
- **Gamma 国有 100% 渗透** → 我方进国有大行难度大 (壁垒高 · 走差异化"可审计"打)
- **百融 950+ 区域银行** → 我方区域 / 城商 / 农商 sweet spot · 单笔 50-200 万

---

## 2. 6 Agent 当前版本 + 计费可分性 (per CLAUDE.md §11)

| Agent | 当前版本 | 触发源 | 用户角色 (per `auth_service/rbac.py`) | 计费维度建议 | 备注 |
|---|---|---|---|---|---|
| Agent1 获客 | v4.0 (信号驱动 · 候选 4 字段 metadata) | 客户经理 | `rm` | **per-seat (RM 数)** | RM 重复用 · 不适合 per-call |
| Agent2 风控 | v3.1 (DSL + 回测 · `MAX_ROWS=50000`) | 风险经理 | `risk_manager` | **per-DSL-publish + 回测次数** | 低频高价 · 一笔 DSL 上线值钱 |
| Agent3 授信 | v3.1 (对公 / 普惠 / 对私) | 审贷会 | `credit_officer` | **per-decision (per case)** | 高频 · 与放贷量挂钩 |
| Agent4 预警 | v3.1 (知识库批量扫描) | 客户行为变化驱动 | `risk_manager` | **per-客户池规模 + per-alert** | 客户池规模决定底价 · alert 量决定增量 |
| Agent5 合规 | v3.1 (政策事件驱动) | 政策发布 | `compliance_officer` | **per-政策扫描次 + 业务制度库规模** | 低频 · 但每次扫描成本高 (政策长 + 业务库大) |
| Agent6 报告 | v16 (classifier→generator→QC) | 客户经理 | `rm` / `credit_officer` | **per-report (per docx 产出)** | 高频 · 与放贷件量挂钩 |

**复合计费**:
- **Agent3 + Agent6 打包**: 因 Agent6 输出是 Agent3 输入 (handoff 关系 · per `auth_service/rbac.py:25`) · 一起卖更顺
- **Agent4 + Agent5 打包**: 都消费 `shared/kb_scan/` 底座 · 都是事件驱动 · 客户感受类似
- **Agent1 单卖**: RM workflow 独立 · 适合区域行先打开口

---

## 3. 三档定价模型 (假设 · 不是报价)

### 3.1 档位概览

| 档位 | 客户类型 | 定价区间 (RMB) | 部署方式 | Agent 范围 | 数据隔离 (per `multi-tenant-assumptions.md`) | SLA |
|---|---|---|---|---|---|---|
| **Pilot 试点** | POC 期 / 单分行 / 单业务线 | **30-80 万 / 6 月** | SaaS 共享 (我方 ECS) | 1-2 Agent 单选 | 逻辑隔离 (`tenant_id` 字段筛 · per Phase C 实装) | 5×8 工时响应 |
| **Pro 标准** | 单银行总行 / 多分行 | **150-500 万 / 年** | 私有化 (银行机房) 或 SaaS 独立实例 | 3-6 Agent 自选 | 物理隔离 (独立部署 instance) | 7×24 / 4h 响应 |
| **Enterprise 旗舰** | 国有大行 / 头部股份 / 强信创需求 | **500-2000 万 / 年** | 私有化 + 信创兼容 (鲲鹏 / 麒麟 / 曙光) | 6 Agent 全 + 定制扩展 | 物理隔离 + 网络隔离 + 数据本地化 | 7×24 / 1h 响应 + 现场支持 |

### 3.2 计费维度细分

#### Pilot 试点 (per-Agent · per-seat / per-call 选择性混合)

| Agent | 基础包含 | 超量阶梯 |
|---|---|---|
| Agent1 获客 | 5 RM seat · 50 候选 / RM / 月 | 超出 1 元 / 候选 |
| Agent2 风控 | 1 risk_manager seat · 5 DSL 上线 / 月 + 100 回测 / 月 | DSL 1 万 / 次 · 回测 100 元 / 次 |
| Agent3 授信 | 100 case / 月 | 200 元 / case |
| Agent4 预警 | 1000 客户池 + 500 alert / 月 | 客户池 5 元 / 客户 / 月 · alert 1 元 / 条 |
| Agent5 合规 | 50 政策扫描 / 月 | 1000 元 / 扫描 |
| Agent6 报告 | 200 report / 月 | 100 元 / report |

#### Pro 标准 (年费 + 容量包)

- 基础年费覆盖 1 总行 + N 分行 unlimited internal seat (RM / credit / compliance / risk · per `auth_service/users.py:46-50` 5 user 角色模型)
- 容量包按 quarter 续: 每 100 万 case / 每 10 万 alert / 每 1000 report 阶梯
- Agent 数选 3 / 4 / 5 / 6 → 年费阶梯 150 / 250 / 350 / 500 万

#### Enterprise 旗舰 (一次性 + 维护)

- 一次性: 软件许可 + 私有化部署 + 信创适配 + 培训 (合计 500-1500 万)
- 年度维护: 一次性的 18-22% (对标拓尔思 · 业内常规)
- 定制扩展按人天报价 (建议 8000-15000 元 / 人天 · 按 PM / 工程师角色分级)

### 3.3 ROI 模型骨架 (供 sales-playbook 引用)

#### Agent6 报告 (锚壹账通 80% 自动化 + 6 倍效能)

| 输入 (银行侧) | 假设值 | 节省 |
|---|---|---|
| 客户经理人数 | 200 | — |
| 单 RM 每月报告产出 | 30 | — |
| 单报告平均人工耗时 | 4 小时 | — |
| 自动化率 (我方 Agent6) | 70% (保守 · vs 壹账通 80% 锚) | — |
| 释放人时 / 月 | 200 × 30 × 4 × 0.7 = 16800 小时 | 即 100 RM 全月产能 |
| 单 RM 月成本 (含五险一金) | 1.5 万 | — |
| 月节省人力成本 | 100 × 1.5 = **150 万 / 月** | 年化 1800 万 |

→ Pro 档 200-300 万 / 年 vs 1800 万 / 年节省 → **ROI 6-9x · 6 月内回本**

#### Agent3 授信 (锚同盾诸葛 误报 -45%)

| 输入 | 假设值 |
|---|---|
| 单银行年放贷件量 | 10000 件 |
| 单件人工审贷耗时 | 2 小时 |
| 误判率 (无 AI) | 5% (500 件 / 年) |
| 单笔误判平均损失 | 50 万 (坏账 + 调查成本) |
| 我方误判降幅 (保守 30% · vs 同盾 -45% / -72%) | 150 件 / 年 |
| 年节省坏账损失 | 150 × 50 = **7500 万 / 年** | — |

→ Enterprise 档 500-800 万 / 年 vs 7500 万 / 年节省 → **ROI 9-15x**

> ⚠️ ROI 模型基于公开锚点假设 · 真实客户 POC 期必跑 baseline (per `evaluation/README.md`) 才能给客户具体数字。Doc 不做承诺 · sales-playbook 引用时必加 disclaimer "实际值随客户数据浮动"。

---

## 4. 价格敏感度 + 决策博弈 (per DoD §0 5 方采购模型)

银行采购 5 方否决权 (业务 / 科技 / 合规 / 数据管理 / 采购) · 每方价格敏感度不同:

| 决策方 | 在意什么 | 价格敏感度 | 我方 doc 应对 |
|---|---|---|---|
| 业务 (业务部 / 风控部 / 合规部 主任) | ROI · 节省人力 · 不背锅 | 中 (要看 ROI 倍数 ≥ 5x) | sales-playbook 凸显 ROI 模型 (§3.3) |
| 科技 (信息科技部) | 部署能跑 · 集成成本 · 不增维护负担 | 中 (本身预算大 · 但要部署成本可控) | trial-flow 凸显 SaaS / 私有化两条路径 |
| 合规 (合规 / 内审) | 可解释 · 可审计 · 不出监管事故 | 低 (合规出事故罚款百万至千万 · 价格不是杠杆) | 强调 BE7 decision ledger + Agent5 + 等保 / 信创 |
| 数据管理 | 数据不出境 · 分级合规 · 备案 | 低 | trial-flow 凸显本地处理 (per `definition-of-done.md` L2-15) + DeepSeek 境内 |
| 采购 (采购部 / 财务) | 单价 · 续费率 · 替换成本 | **高** (本职杀价) | doc 留 15-20% 议价空间 · 不放底价 |

**杀价博弈应对**:
- Pilot 档 30-80 万底价不松 (低于 30 万 = 不赚 · 仅当客户能引到大单时考虑)
- Pro 档 ≥ 150 万 (低于此线 = 不如不做 · 维护成本吃掉利润)
- Enterprise 档可议 · 但维护费 18% 不松 (业内常规)
- 三档之间留**功能阶梯而非价格阶梯** (Pilot 砍 SLA + 砍 Agent 数 · 不是单纯打折)

---

## 5. 不同档位的功能 / 数据 / SLA 差异表

| 维度 | Pilot | Pro | Enterprise |
|---|---|---|---|
| Agent 数 | 1-2 | 3-6 | 6 全 |
| User seat | 5-10 | 50-200 (总行 unlimited) | unlimited |
| 数据隔离 | 逻辑隔离 (tenant_id 字段) | 物理隔离 (独立 instance) | 物理 + 网络隔离 + 本地化 |
| 部署 | SaaS 共享 (ECS) | SaaS 独立 OR 私有化 | 私有化 + 信创 |
| LLM 调用 | DeepSeek 境内 (per CLAUDE.md §3.7.3 PIPL) | DeepSeek + DashScope fallback | 客户自选 (含本地化大模型 · DeepSeek-R1 / Qwen 私有部署) |
| Audit log 保留 | 90 天 (per `decision_ledger` short retention) | 5 年 (standard) | 10 年 (long · 客户自托管) |
| Decision ledger jurisdiction (per CLAUDE.md §3.7.5) | `HQ` 默认 | `HQ` / `BRANCH` 二选 | 银 / 保 / 证 / 自定义 enum 全开 |
| 评估基线 (per `evaluation/README.md`) | 共享 baseline | 客户专属 baseline (落 `evaluation/baselines/`) | 客户专属 + per-季度回归 |
| Few-shot 注入 (per CLAUDE.md §6 + B1 worker BE10) | 共享 prompts | 客户私有 few-shot (`data/feedback/<tenant_id>/`) | 客户私有 + 训练数据不离场 |
| 升级路径 | 试用期内 → 直升 Pro / Enterprise | Pro → Enterprise (年中续费可升) | 已顶 |
| SLA | 5×8 / 工时响应 / 24h 解决 | 7×24 / 4h 响应 / 12h 解决 | 7×24 / 1h 响应 / 4h 解决 + 现场 |

---

## 6. 计费 / metering 实装路径 (Phase C 推 · per Codex R2)

**Phase B 不做** (per BE11 charter line 100-108):
- 不实装 `tenant_id` 字段到 `audit_service/recorder.py` schema
- 不实装 Stripe / 内部 billing 系统
- 不实装 quota / rate limit per tenant
- 不实装 usage dashboard

**Phase C 实装路径骨架** (供 PM Phase C charter 起草参考):

1. **Step 1 · schema migration (1.5 周)**: `audit_service/recorder.py` 加 `tenant_id` + `org_id` 字段 · 历史数据 backfill 默认 `tenant=zhongan_demo` · 加 index
2. **Step 2 · metering aggregation (1 周)**: 跑 `scripts/metering/daily_aggregate.py` · 按 (tenant_id, agent_id, endpoint) 聚合 LLMCall + DecisionLedger entry → 落 `data/metering/YYYY-MM-DD.jsonl`
3. **Step 3 · quota enforcement (1 周)**: `auth_service/dependencies.py` 加 `check_quota` decorator · 超额 fail-fast 返 402 Payment Required + 引导升级
4. **Step 4 · billing reconciliation (1 周)**: 月底跑 reconcile · 出 `tenant_id × 服务项 × 用量` Excel · 走线下对账
5. **Step 5 · usage dashboard (1.5 周)**: `/admin/billing` 页面 · 复用 `web/` shell v2 · 展示 tenant 用量 + ROI 折线
6. **Step 6 · Stripe / 内部 billing 集成 (2 周 · 视客户付款方式)**: 国内银行多走 PO / 银行转账 · Stripe 优先海外客户

**总 Phase C metering 工程量 ~8-10 周** (单线 wall-clock · 不并行 sales-playbook trial)。**触发条件**: 至少 2 个 Pilot 客户签字 + 1 个 Pro 客户在谈 (per Codex R2 "已签 POC 前置")。

---

## 7. 假设清单 (本 doc 凡 "假设 / 应该 / 推测" 处)

| # | 假设 | 验证方式 | 风险 |
|---|---|---|---|
| A1 | 银行付费意愿与"节省人力 + 降低坏账损失"挂钩 | 销售 lead 客户走访 5+ 家访谈 | 高 · 没真实客户验证 |
| A2 | Pro 档 150-500 万年费区间合理 | 与拓尔思 / 壹账通公开成交对比 + 销售试探报价 3 家 | 中 · 锚点是头部 · 区域 / 城商 / 农商可能更低 |
| A3 | per-seat / per-call 计费客户能接受 | 销售试探 · 国内银行更习惯一次性 + 年度维护 | 中 · 国内偏好 license + 维护费模型 |
| A4 | Enterprise 档信创兼容是杀手锏 | 与国有 / 头部股份业务部访谈 | 中 · 信创已成标配 · 不一定是杠杆 |
| A5 | 6 Agent 全打包性价比 > 单 Agent | ROI 模型 §3.3 自洽 | 中 · 客户可能只买 1-2 Agent (per `auth_service/rbac.py` ACCESS 角色 6 Agent map) |
| A6 | 18-22% 维护费业内可接受 | 拓尔思 / 壹账通公开数据 | 低 |
| A7 | LLM cost 占比 ≤ 总收入 5% | 跑 production 后 audit_service 成本反推 (Phase C) | 中 · 每月 cost 没真实数据 · 凭 `audit_service/recorder.py:cost_cny` 字段假设 |

> **A7 critical**: 没真实流量 · 不能给客户精确 cost 估算。Phase C 真客户接入后 1 个月 audit log 反推后修正本 doc。

---

## 8. 与其他 doc 的对接

- `multi-tenant-assumptions.md`: §6 metering 实装路径 → 详 multi-tenant doc 数据模型
- `trial-flow-assumptions.md`: §3 Pilot 档 → 详 trial-flow Pilot 6 月转化窗口
- `sales-playbook-v1.md`: §3.3 ROI 模型 → sales-playbook 客户话术引用 (含 disclaimer)
- `docs/scorecard/definition-of-done.md` L4: §3 Enterprise 档 → DoD L4 商业交付 8 条对齐
- `docs/contracts/decision-ledger.md` v1.0: §5 jurisdiction enum → 档位差异化映射

---

## 9. 修订日志

- v1.0 · 2026-05-04 · worker-B2-biz · 初稿 · 4 doc 系列首发

**下一次修订触发**:
- 至少 1 个 Pilot 客户实际签字 → 实际成交价回写 §1 锚点表 + §3.1 区间收紧
- Phase C metering 第一个月真实 cost 数据 → §7 A7 修正
- 销售 lead 客户访谈 5 家 → §7 A1-A5 升级为 verified
