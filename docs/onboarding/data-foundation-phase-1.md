# data-foundation (拟真数据底座) Phase 1 Onboarding

**状态**：APPROVED
**发布日期**：2026-04-23
**Signal 入口**：`PRODUCT-HARDENING-BATCH-1-DISPATCHED`
**前置**：
- PM 判定现有 mock "太简单 + 太结果导向"，要求重建
- Entity-first 数据架构：企业锚点 → 信号衍生（见 Q-023）
- Batch 2 在用户回埋坑清单后才启动（MVP 3 家完整材料包）

---

## 你是谁

你是 **data-foundation** worker CLI，负责 **1 周内** 建起"拟真数据底座"——宽基 100 家企业池 + 深柱 15 家名单 + 埋坑清单模板。Batch 2 将产深柱 3 家完整材料包（等用户回填埋坑清单后）。

- Worktree：`D:/claude code/demo-data-foundation`
- 分支：`feat/data-foundation`（从 `chore/l0-infra` 分出）
- Upstream remote：`D:/claude code/credit_report_agent_work`

---

## 数据架构哲学（必读）

**Entity-first · 企业锚点 → 信号衍生**：
- 不为每个 Agent 单独 mock 数据
- 先 mock 一批真实企业（实体），各 Agent 按需消费该企业衍生的信号
- 宽基 100 家（工商+行业+规模+舆情浅度）→ Agent1 检索池
- 深柱 15 家（11 类信号完整材料包）→ Agent3/4/5/6/2 深度数据

**反"结果导向"的 4 条设计原则**（PM 底线，不可违）：
1. **盲测法**：PM 设计埋坑，worker 不看答卷只建材料
2. **难度分层**：简单 20% / 中等 50% / 困难 20% / 极端 10%
3. **真实来源锚定**：参考 A 股年报 / 央行征信模板 / 银保监处罚公告——改名字改数字保量级
4. **脱敏再造不凭空编**：每家企业选一个真实"标杆"作地基

---

## 本批次任务

### 📐 Task A — data/mock/ schema + 目录规范

**目标**：为宽基 / 深柱两层数据立 YAML schema + 目录约定。

**模块路径**：
- 新建：`data/mock/README.md`（架构哲学 + 目录说明 + 消费方指南）
- 新建：`data/mock/schemas/wide-base.yaml`（宽基 schema：company_id / name / industry_l1 / industry_l2 / region / size / listed_bool / registered_capital / establish_year / brief_profile / 2-3 个浅舆情信号）
- 新建：`data/mock/schemas/deep-pillar.yaml`（深柱 schema：11 类信号字段定义 —— 工商 / 3 年财报 / 12 月流水 / 征信 / 担保 / 合同 / 舆情 / 政策关联 / 贷后行为 / 风险标记 / 策略样本元数据）
- 新建：`data/mock/wide-base/` 目录（等 Task B 填）
- 新建：`data/mock/deep-pillar/` 目录（等 Task C 列出名单 + Batch 2 填）

**指标/验证**：
- 任意第三方读 README 能理解底座意图
- schema YAML 用 `yamllint` 跑通

**工作量**：S（0.5 天）
**完成信号**：`Signal: DATA-SCHEMA-DONE`

---

### 📊 Task B — 宽基 100 家骨架 + 填充

**目标**：产 100 家企业骨架记录，按以下行业/难度分布：

| 行业 | 家数 |
|---|---|
| 制造业（精密机械/食品/家具/纺织/化工/电子）| 25 |
| 零售商贸（连锁/家电/建材/服装/农副）| 20 |
| 服务业（物流/咨询/餐饮/医疗/教育）| 15 |
| 地产关联（建材/装饰/物业）| 10 |
| 农业（养殖/种植/加工）| 8 |
| 科技（软件/硬件/SaaS）| 12 |
| 跨境外贸 | 5 |
| 集团 / 对私 | 5 |

难度：简单 20 + 中等 50 + 困难 20 + 极端 10（简单只含"材料齐全清晰无红线"，其他档预留脏度 slot 给 Batch 2）

**做法**：参考 A 股年报 + 天眼查公开数据模板批量产，8-10 字段/家。**PM 抽检 20%**（命中率不足 80% 的反工重做）。

**模块路径**：
- 新建：`data/mock/wide-base/companies.yaml`（100 家一个文件，按行业分块）
- 新建：`data/mock/wide-base/source-notes.md`（每家企业的"标杆参考"脚注，便于 PM 验真）

**指标/验证**：
- 100 家全覆盖 8 大行业分布
- 简单/中等/困难/极端比例严格 20/50/20/10
- PM 抽 20 家校验真度 ≥ 80%
- `data/mock/wide-base/companies.yaml` 可被 Agent1 检索 API 消费（schema 对齐）

**工作量**：L（3 天）
**完成信号**：`Signal: DATA-WIDE-100-DONE`

---

### 🎯 Task C — 深柱 15 家名单 + 埋坑清单模板

**目标**：从宽基 100 家挑 15 家（覆盖 4 档难度）做深柱候选。为这 15 家各产出 **埋坑清单模板**（空模板，等 PM 填）。

**深柱选择原则**：
- 简单 3 家（2 制造业 + 1 科技）
- 中等 7-8 家（覆盖 5 大主行业）
- 困难 3 家（1 地产关联 + 1 外贸 + 1 零售商贸）
- 极端 1-2 家（必含 1 家"虚假授信"风险模式，参考银保监处罚公告）

**埋坑清单模板**（每家一份 markdown，交 PM 填）：
```
# <企业名> 埋坑清单
- 难度档：中等
- 参考标杆：<A 股某上市公司，脱敏前身>
- 请填 5-10 个"坑"（PM 设计）：
  - [ ] 财报口径冲突（示例：流水 vs 财报营收差 X%）
  - [ ] 征信时效滞后（示例：6 个月前的征信，新贷款未体现）
  - [ ] 关联交易隐蔽（示例：大客户 XX 实为法人亲属控股）
  - [ ] 资产评估虚高（示例：抵押物评估价高于市场价 Y%）
  - [ ] 历史违规未披露
  - [ ] 其他：_______
- PM 签字：____
- 回传日期：____
```

**模块路径**：
- 新建：`data/mock/deep-pillar/shortlist.md`（15 家清单 + 难度分布 + 参考标杆）
- 新建：`data/mock/deep-pillar/pit-template.md`（埋坑清单空模板）
- 新建：`data/mock/deep-pillar/pits/<company_id>.md` × 15（各家一份空表）

**指标/验证**：
- 15 家覆盖 4 档难度比例对
- 15 份埋坑清单模板格式统一，字段齐
- 向 PM 交付埋坑清单模板 URL（本文档路径）

**工作量**：S（0.5 天）
**完成信号**：`Signal: DATA-DEEP-SHORTLIST-DONE`

---

## 完成后

所有 Task 做完：`Signal: READY-FOR-DATA-FOUNDATION-B1-REVIEW`

## 红线

- ❌ 不 commit 任何真实客户数据（所有脱敏后再入库）
- ❌ 不改 `agent_*/` / `web/**`（代码层归 code-urgent / code-arch）
- ❌ 不在这轮做深柱 15 家的完整材料包（那是 Batch 2，等 PM 埋坑清单）
- ❌ 不碰 evaluation 的地盘（rubric YAML 归他）
- ✅ `data/mock/` 全权你负责
- ✅ `docs/runbook/data-foundation.md`（如需）你可以新增
- ✅ 可以 read `customer/` / `demo_data/` / `industry_cards/` 现有数据作为灵感，但**不要直接复用**（那些就是"太简单太结果导向"的源头）

## ACK 协议

1. Resume → commit doc-only，trailer `Signal: PRODUCT-HARDENING-BATCH-1-ACK`
2. Task A → B → C 顺序，每 Task 独立 commit 带对应 signal
3. 全 Task 完成 → `READY-FOR-DATA-FOUNDATION-B1-REVIEW`
4. Batch 2 触发：主 CLI 收到用户填完的 15 份埋坑清单后，再下发

**维护者**：主 CLI
**下次更新触发**：主 CLI APPROVE B1 或下发 B2
