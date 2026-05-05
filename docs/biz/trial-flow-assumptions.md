# 客户试用流程假设 v1.0 · POC → Pilot → Pro 转化

> **版本**: v1.0 · 2026-05-04 · worker-B2-biz (Phase B Sprint 2 · BE11 doc-only)
> **性质**: 假设流程 · 非合同流程 · 非已签约客户实际 SOP
> **审稿对象**: 主 CLI / PM / 销售 lead · 不发客户
> **下游**: `sales-playbook-v1.md` 客户对接动作 + `pricing-assumptions.md` 档位转化时点

---

## 0. 范围 + 红线

**做**:
- 4 阶段转化漏斗 (POC → Pilot → Pro → Enterprise)
- 每阶段时长 / 数据范围 / 账号范围 / 我方动作 / 退出条件
- 共享 vs 隔离边界 (per `multi-tenant-assumptions.md` §3)
- 客户拿到的"看 / 用 / 改" 边界 (功能 / 数据 / 评估)

**不做**:
- ❌ 真实 onboarding 工单系统 (推 Phase C)
- ❌ 客户自助开户流程 (推 Phase C · 现仅手动开 user)
- ❌ 合同条款 / 法律文本
- ❌ 客户对接 SLA 法律承诺

---

## 1. 4 阶段漏斗概览

```
[Lead 接触]
     │  访谈 1-2 次 · 不收费 · 1-2 周
     ▼
[POC 概念验证]      ← 免费试用 1-2 周 · 不签合同
     │  评估通过 / 否决
     ▼
[Pilot 试点]         ← 30-80 万 / 6 月 · 单分行 / 单业务线 (per pricing §3.1)
     │  6 月内 ROI 验证 / 续签升档 / 退出
     ▼
[Pro 标准]           ← 150-500 万 / 年 · 全总行 (per pricing §3.1)
     │  3 年合同 + 续费率
     ▼
[Enterprise 旗舰]    ← 500-2000 万 / 年 · 全行 + 信创 + 私有化 (per pricing §3.1)
```

**关键转化点**:
- **POC → Pilot**: 客户业务部 + 科技部双签 · 解决 5 方 (per DoD §0) 中至少 3 方异议
- **Pilot → Pro**: 6 月内 ROI ≥ 5x (per pricing §3.3 模型) + 内审过 · 续签升档
- **Pro → Enterprise**: 3 年内业务扩展到多分行 + 信创要求触发 + 客户 IT 战略级投入

---

## 2. POC 阶段 (1-2 周 · 免费 · 不签合同)

### 2.1 入场条件

- 客户 RFP / 主动接触 / 销售 lead 引荐 (per `sales-playbook-v1.md` 准入清单)
- 业务部主任 + 科技部分管 leader 同时表态意向 (单方接洽不进 POC)
- 客户提供 1 业务线 sample 数据 (脱敏 · 不进 production)

### 2.2 我方提供

| 维度 | 范围 |
|---|---|
| **环境** | demo.liuye.me (per ECS production · CLAUDE.md §13) · SaaS 共享 · 单租户 demo `tenant=zhongan_demo` |
| **账号** | 复用现 5 fixed user (per `auth_service/users.py:46-50`) · 不开新租户 |
| **Agent 数** | 1-2 Agent 演示 (客户选最痛的) · 不全开 6 |
| **数据** | 客户脱敏 sample · 跑 mock 模式 OR 真实 LLM (per `shared/llm_caller/` 默认 DeepSeek) |
| **演示形式** | 1 次现场演示 + 1 次远程跟进 · 客户自试 ≤ 5 工作日 |
| **评估输出** | 跑 `evaluation/runner` (per `evaluation/README.md`) · 出客户专属 baseline · 落 `evaluation/results/YYYY-MM-DD/` |
| **不交付** | 不出报告解读 · 不签 SLA · 不承诺 production · 不出价格 (问到时引到 sales-playbook §4) |

### 2.3 客户拿到的"看 / 用 / 改"

| 边界 | 范围 | 备注 |
|---|---|---|
| **看** | demo 域名 4 view (`/today` / `/dispatch` / `/archive` / `/warroom`) + 选定 Agent workspace | 完整 shell v2 体验 |
| **用** | 跑预置场景 (per DoD §3 L1-1 ≥ 2 场景 / Agent) + 跑 1 次客户脱敏数据 | mock 模式可断网跑 (per L1-10) |
| **改** | 不可改 prompt · 不可改规则 · 不可看代码 · 不可下载 audit log | POC 期完全只读 |

### 2.4 我方动作清单 (1-2 周内)

1. **D1**: 销售引荐 → 主 CLI 起 demo session · `tenant=zhongan_demo_<客户简称>` slug 待用 (不开真 tenant · 仅口头标识)
2. **D2-3**: 客户提供脱敏 sample · 主 CLI 准备演示场景 · 跑 baseline 落 `evaluation/results/`
3. **D4**: 现场演示 · 4 角色 demo (RM / credit / compliance / risk) · 全 4 view 走一遍
4. **D5-9**: 客户自试 5 工作日 · 我方监控 audit log + 答疑
5. **D10-12**: 复盘 · 出 POC 评估报告 (我方提供给客户的 1-2 页 doc · 含 baseline + 痛点解决 + ROI 模型 §3.3)
6. **D13-14**: 双签确认进 Pilot · OR 客户否决退出

### 2.5 退出条件 (POC → Pilot)

**进 Pilot (3 项 AND)**:
- 客户业务部 + 科技部双签意向 (邮件 / 微信留底 · 非合同)
- 评估 baseline 通过 (per `evaluation/<agent>.yaml` `blocker_threshold` 全绿)
- 客户报价口径接受 (Pilot 30-80 万 · 6 月)

**否决 (任一)**:
- 客户 5 方 (业务 / 科技 / 合规 / 数据管理 / 采购) 中 ≥ 2 方否决
- baseline 跑客户数据时 `hallucination_rate > 0.05` OR `evidence_rate < 0.85` (远超 blocker_threshold)
- 客户预算 < 30 万 (走不进 Pilot 档底价)

**退出动作**:
- 我方保留客户 sample 评估结果 (匿名化 · 用于反 5 原则 §3.5 难度分层 mock 数据补充 · 进 `data/mock/` · 不外传)
- 客户 sample 数据 7 日内删 (audit log + temp 文件)
- 客户专属 baseline 留底 6 月 (`evaluation/baselines/poc/<客户简称>_<日期>.json`)
- 客户 demo session log 留底 90 日

---

## 3. Pilot 阶段 (6 月 · 30-80 万 · 单分行 / 单业务线)

### 3.1 入场条件

- POC 通过 + 客户业务 + 科技双签
- 合同签完 (法务出 · 非本 doc scope)
- 客户付款 30% 预付款到账 (per `pricing-assumptions.md` 应付节奏)

### 3.2 我方提供

| 维度 | 范围 |
|---|---|
| **环境** | SaaS 共享 (per `multi-tenant-assumptions.md` §3 Pilot 档 "逻辑隔离") |
| **账号** | 客户专属 tenant slug (e.g. `tenant=icbc-shanghai-puhui`) · 5-10 user seat (per pricing §3.2) |
| **Agent 数** | 1-2 Agent (客户合同选定) |
| **数据** | 客户真实数据 · per `multi-tenant-assumptions.md` §2.2 `data_residency="cn"` 强约束 |
| **LLM** | DeepSeek 境内主 + DashScope fallback (per CLAUDE.md §3.7.3) |
| **Audit log retention** | 90 日 (per `multi-tenant-assumptions.md` §5.2 short class) |
| **Decision ledger jurisdiction** | `HQ` 默认 |
| **Few-shot** | 共享 prompt (per `multi-tenant-assumptions.md` §2.8 Pilot 档不污染) · 客户反馈进我方共享 baseline |
| **SLA** | 5×8 工时响应 / 24h 解决 |
| **支持** | 月度对接会 1 次 · 客户专属 Slack / 飞书群 · 邮件答疑 ≤ 4h |
| **评估** | 月度跑 baseline · 落 `evaluation/baselines/pilot/<tenant>_YYYY-MM.json` · 客户出月报 |

### 3.3 客户拿到的"看 / 用 / 改"

| 边界 | 范围 | 备注 |
|---|---|---|
| **看** | 全 4 view + 选定 Agent workspace + admin billing dashboard 限定子集 (仅自家 tenant 用量) | per `multi-tenant-assumptions.md` §6 |
| **用** | 自家真实数据 · per-call 走 quota 限额 (per pricing §3.2) · 超额阶梯计费 | 计费 metering Phase C 实装前手动月底对账 |
| **改** | 客户可改自家 few-shot (Pilot 末期开放 · 仅自家 tenant 私有 prompt) · 不可改代码 · 不可看 prompt source | per `multi-tenant-assumptions.md` §2.8 Phase C |

> **Pilot 档 metering 现状**: Phase B / Phase C Step 1-3 完成前 metering 跑手工脚本 · 月底导 `data/metering/<tenant>/YYYY-MM.csv` · 客户对账。Step 4 quota enforcement 实装后切自动。

### 3.4 6 月里程碑

| 月 | 我方动作 | 客户动作 | 评估 |
|---|---|---|---|
| M1 | onboarding · user 创建 · 数据 import · baseline 跑 | 业务部用户上手 · 测 5 case | 跑 baseline · 落 M1 snapshot |
| M2 | 答疑 · 修客户报告的 1-2 个 prompt edge case | 业务部稳定使用 · audit modify 数 ≥ 50 (feedback) | M1 vs baseline 不退化 |
| M3 | **中期评审** · 出 ROI 中期报告 (per pricing §3.3 模型 actual vs 预测) | 业务部 + 科技部听汇报 · 决定续签意向 | M3 baseline + ROI |
| M4-5 | 持续优化 · few-shot 从 feedback 提取 (per CLAUDE.md §6 数据飞轮) | RM 业务规模扩量 | feedback ≥ 200 条 / 月 |
| M6 | **终期评审** · 出 ROI 终期报告 + Pro 续签报价 + Pro 升档可行性评估 | 5 方决策 (per DoD §0) · 续签 / 退出 | 全维度评估 + 是否进 Pro |

### 3.5 退出条件 (Pilot → Pro · 续签 OR 退出)

**进 Pro (4 项 AND)**:
- 6 月 ROI ≥ 5x (per pricing §3.3 模型 · 实际值 vs 模型)
- `evaluation/baselines/pilot/<tenant>` 末月不退化 > 2% (per DoD §3 L3-4)
- 业务部 + 科技部 + 合规部 三签 (退合规可选 · 进 Pro 必需)
- 续签价 / 容量包谈拢 (per pricing §3.2 阶梯)

**退出 (任一)**:
- ROI < 3x (经营层不批续费)
- 客户业务方向调整 (e.g. 目标市场变 · Agent 不适用)
- baseline 退化 > 5% (我方代码退化 · 客户失信)
- 价格谈崩 (客户要 < 100 万 / 年)

**Pilot 末期我方动作**:
- M5 末发续签报价 + Pro 档差异化 doc · 给客户 1 月决策窗口
- M6 终期评审会 · 出 PPT (per `docs/handoff/<客户简称>-pilot-终期评审.pptx`)
- Pro 续签合同走法务 · 不在本 doc

**退出后数据处置** (per `multi-tenant-assumptions.md` §5.2):
- 客户数据按 retention class 倒计时 · short=90d / standard=5y / long=10y
- 解约后 30 日内客户可申请数据导出 (Excel + jsonl 包) · 之后冻结
- 客户可申请保留我方代码版本 (本地部署 · 走 Enterprise 一次性 license)

---

## 4. Pro 阶段 (1-3 年 · 150-500 万 / 年 · 全总行)

### 4.1 入场条件

- Pilot 通过 + 5 方 (per DoD §0) ≥ 3 方明确支持
- 合同 ≥ 1 年 · 续约模式协商 (按年 / 按 3 年)
- 客户付款 50% 预付款 + 季度结算

### 4.2 我方提供

| 维度 | 范围 |
|---|---|
| **环境** | SaaS 独立 instance OR 私有化 (per pricing §3.1 "Pro 标准") |
| **账号** | 总行 unlimited internal seat (per `multi-tenant-assumptions.md` §6 客户自管 user) |
| **Agent 数** | 3-6 Agent (合同选定 · 阶梯定价 per pricing §3.2) |
| **数据** | 客户真实数据 · 物理隔离 · `tenants/<tenant_id>/` 独立目录 |
| **LLM** | 客户可 BYOK (per `multi-tenant-assumptions.md` §5.3) |
| **Audit log retention** | 5 年 (standard) |
| **Decision ledger jurisdiction** | `HQ` / `BRANCH` 二选 |
| **Few-shot** | 客户私有 (`data/tenants/<tenant>/few_shots/`) · 不污染共享 |
| **SLA** | 7×24 / 4h 响应 / 12h 解决 |
| **支持** | 周度对接会 (前 3 月) → 月度 (稳定后) · 客户技术对接人 1-2 人 driver-side |

### 4.3 客户拿到的"看 / 用 / 改"

| 边界 | 范围 | 备注 |
|---|---|---|
| **看** | 全 4 view + admin billing 全自家 tenant + audit log 自家 tenant 子集 | admin 角色客户自管 |
| **用** | 全自家真实数据 · unlimited seat · per-call 容量包阶梯 | metering Phase C 实装后自动 |
| **改** | 客户可改 few-shot · 可定制评估 baseline · 可加客户专属 reason_codes (per DoD L2-7) · **不可改代码** | 代码客户拿 read-only access (Enterprise 起) |

### 4.4 退出条件 (Pro → Enterprise · 升档 OR 续 Pro OR 退出)

**升 Enterprise**:
- 客户业务扩展到多分行 (≥ 3 分行)
- 客户信创要求触发 (国资委 / 银保监整改通知)
- 客户 IT 战略升级 (一把手项目 / 5 年规划列入)
- 投入预算 ≥ 500 万 · 接受私有化部署

**续 Pro**:
- 业务稳定 · 3 年内不扩
- 续约价不上调超 10% / 年

**退出**:
- 客户战略调整 (并购 / 业务线砍掉)
- 我方代码不再维护对应 Agent (我方放弃市场)
- 监管事故触发客户合规重审

---

## 5. Enterprise 阶段 (3-5 年 · 500-2000 万 / 年 · 全行 + 信创)

per `pricing-assumptions.md` §3.1 + `multi-tenant-assumptions.md` §3 "物理 + 网络隔离 + 数据本地化"。

不展开 (本 doc 范围: 假设流程 · Enterprise 一案一议)。

---

## 6. 阶段切换的契约对齐

per `multi-tenant-assumptions.md` §7 SSOT 升级路径:

| 阶段切换 | 触发文档动作 |
|---|---|
| POC 通过 | 主 CLI 起 `docs/handoff/<客户简称>-poc-evaluation.md` 留底 |
| Pilot 启动 | 创真 tenant slug · 走 Phase C `docs/contracts/multi-tenant.md` 实装路径 (Step 1) |
| Pilot 结 (M3) | 主 CLI 写 `docs/scorecard/pilot-<客户简称>-m3.md` |
| Pilot 结 (M6) | 续签 / 退出 决策 · 写 `docs/handoff/<客户简称>-pilot-final.md` |
| Pro 启动 | tenant 升档 · `tenant.pricing_tier="pro"` · 物理隔离实装 · 走 RFC 改 |
| Enterprise 启动 | 私有化部署 · 一案一议 · 走客户专属 RFC + 法务 + 信创 |

---

## 7. 假设清单

| # | 假设 | 验证方式 | 风险 |
|---|---|---|---|
| T1 | POC 1-2 周够客户决策 | 销售实战 3 家以上验证 | 中 · 国有大行可能要 4-6 周 |
| T2 | Pilot 6 月够验证 ROI | 业内常规 (壹账通 / 同盾) | 低 |
| T3 | 客户接受脱敏 sample 走 demo | 数据管理部访谈 | 中 · 部分行禁止任何外传 |
| T4 | Pro 私有化部署可 1-2 周 onboarding | 工程 spike (Phase C 启动后) | **高** · 私有化首次必踩坑 |
| T5 | Enterprise 信创兼容 (鲲鹏 / 麒麟 / 曙光) 已有路径 | per DoD L4-2 doc | 中 · doc 已有 · 实跑没验证 |
| T6 | 续签率 ≥ 70% (Pilot → Pro) | 6 月后真实数据 | 中 · 无历史数据基线 |
| T7 | 客户接受 quota 阶梯计费 | 销售试探 3 家 | 中 · 国内偏好一次性 license |
| T8 | 解约后 30 日数据导出窗口够 | 客户访谈 | 低 |
| T9 | POC → Pilot 转化率 ≥ 30% | 销售实战 | 中 · 无基线 |
| T10 | Pilot 期客户技术对接人愿配合 (≥ 1 PM + 1 IT) | 客户访谈 | 中 · 客户 IT 资源紧张 |

---

## 8. 反结果导向 5 原则约束 (per CLAUDE.md §3.5)

POC 数据用回 mock 库时:
- 盲测: PM 决数据进库 · worker 不预知客户答案
- 难度分层: 简单 / 中等 / 困难 / 极端 4 档
- 真实来源锚定: 客户脱敏后形态保留 (扫描件 / 多年跨度 / 数字矛盾)
- 脱敏再造: 改名字 + 改数字保量级 · 不直接用真实存续企业
- 环境边界: 不替 Agent 做该外搜的工作 (Agent1 / Agent5 候选必走 SearchProvider)

POC 阶段客户 sample 进 mock 库走 PM 显式拍板 + `Authorized-By: PM` trailer。

---

## 9. 与其他 doc 的对接

- `pricing-assumptions.md` §3.1: 三档定价 → 本 doc §2-5 对应阶段
- `pricing-assumptions.md` §3.3: ROI 模型 → 本 doc §3.4 Pilot M3 + M6 评审引用
- `multi-tenant-assumptions.md` §3: 隔离矩阵 → 本 doc 各阶段"我方提供"段
- `multi-tenant-assumptions.md` §9: 真实装条件 → 本 doc §3.1 Pilot 入场触发 Phase C
- `sales-playbook-v1.md`: 阶段对应客户话术 + 异议 FAQ
- `docs/scorecard/definition-of-done.md` L1-L4: → 本 doc 各阶段验收依据
- `evaluation/README.md`: 跑 baseline / blocker_threshold → 本 doc §2.2 + §3.4

---

## 10. 修订日志

- v1.0 · 2026-05-04 · worker-B2-biz · 初稿

**下一次修订触发**:
- 第 1 个真实 POC 客户走完 → §2 修正实际时长 + 否决率
- 第 1 个 Pilot 客户走完 6 月 → §3 修正 M1-M6 实际节奏
- §7 假设 T1-T10 任一反证 → 修对应段
