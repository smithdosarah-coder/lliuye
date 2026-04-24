# Batch 2 · data-foundation Phase 2 Onboarding（Agent4 预警 mock）

**状态**：Batch 2 GO
**发布日期**：2026-04-24
**Signal 入口**：`PRODUCT-HARDENING-BATCH-2-DF-P2-ACK`
**前置**：Phase 1 v2（commit `e4f23b5` `PHASE-1-DATA-FOUNDATION-V2-APPROVED`）—— Agent6/3/1/5 mock 已落地并通过 15 硬指标
**参照决策**：`docs/handoff/decisions-log.md` Q-028（反 5 原则 + 环境边界）/ Q-029（Batch 1 closeout · 测试阶段豁免 · Batch 2 四轨分配）

---

## 1. 背景与目标

Phase 1 v2 已落地 **Agent6 / Agent3 / Agent1 / Agent5** 的数据底座（深柱 5 家材料包 + channel-kb + compliance-kb），但 Phase 1 三套 mock 都是**文件夹 + pdf + xlsx 形态**。Agent4 的消费形态完全不同——

- **Agent4 预警**（本 Phase）：输入 = 在贷客户池 CSV + 内部流水时间序列 + 外部信号流 md；核心能力 = 跨源交叉规则（外部舆情/司法/工商 × 内部流水异变 × 静态画像），输出红/黄/绿分级榜单。与"能不能搜到"无关，反 5 原则 §3.5 表**明确豁免、允许全 mock**——mock 外部信号不偷能力，反而给规则引擎提供稳态 context 可测。
- **Agent2 风控**（Phase 3）：消费形态 = 策略样本 CSV + DSL 回测，再单独拆。

按**消费形态**切 Phase（不按 Agent 编号切）是本次分期的唯一合理分法。

**规模**：100-200 家在贷客户 · 每家一份 ≥12 月流水 csv + 一份 3-10 条外部信号 md。

**硬边界**：本 Phase 只产 mock 数据，**不动** `agent_alert/` / SearchProvider / evaluation / web / shared。实盘外搜接入归 code-arch 轨（Batch 2 并行）。

---

## 2. Task 清单

### Task A · 在贷客户池 `alert-pool/clients.csv`

**目标**：一份 100-200 行 CSV，每行一家在贷客户的**薄画像 + 授信结构**。

**路径**：`data/mock/alert-pool/clients.csv`

**字段（必须齐全）**：

| 字段 | 说明 |
|---|---|
| `client_id` | `AP001` ~ `AP180` · 与 Task B/C 文件名对齐 |
| `company_name` | 脱敏企业名 · 参照 `channel-kb/historical-clients/` 命名风格 |
| `industry_l1` / `industry_l2` | 一级/二级行业 · 制造业占 50% · 贸易/物流/零售/服务/科技/建筑/农业点缀 |
| `region` | 省市区 · 长三角/珠三角/环渤海各约 30% · 中西部点缀 |
| `scale` | 小型/中型/大型 |
| `credit_line_wan` | 授信额度（万元）· 30-20000 合理分布 |
| `balance_wan` | 当前余额（万元）· 通常 ≤ 授信额度 |
| `interest_rate` | 年利率（%）· 3.5-7.5 |
| `term_months` | 期限（月）· 6/12/24/36 为主 |
| `product` | 流贷/专精特新贷/科技贷/经营贷/供应链金融/融资租赁 等（呼应 `channel-kb/product-catalog/`） |
| `first_draw_date` | 首放日期 · 近 3 年 |
| `last_review_date` | 上次体检日 · 近 12 月 |

**难度分布（PM 私下维护 · 产物零答案字段）**：

| 档 | 家数 | PM 内部画像（**不得写进 csv**） |
|---|---|---|
| easy | ~20 | 画像干净 · 流水规整 · 信号无负面 · 应判绿 |
| medium | ~100 | 多数正常 · 个别波动 · 应判黄(边缘)或绿 |
| hard | ~40 | 回款骤降 / 余额接近上限 / 外部多条负面 · 应判黄或红 |
| extreme | ~20 | 失信被执/限消 + 内部流水异常 + 工商变更 · 应判红 |

**零答案字段红线**：

- CSV 列**不得出现** `risk_level` / `alert_flag` / `difficulty` / `expected_color`
- 不单独产 `answer_key.csv` / `labels.json`

**复用**：允许从 `channel-kb/historical-clients/` 的 10-15 家扩展授信结构字段作为子集，其余新建。脱敏再造（§3.5 第 4 条）——测试阶段重名 OK（引 Q-029.D），对外演示前再追溯。

**完成信号**：`Signal: ALERT-POOL-CLIENTS-DONE`

---

### Task B · 内部交易流水 `alert-pool/transactions/<client_id>.csv`

**目标**：每家客户一份流水时间序列，近 12-24 月（日或月级按客户画像选）。

**路径**：`data/mock/alert-pool/transactions/AP001.csv` ... `AP180.csv`（与 Task A `client_id` 严格对齐）

**字段**：

| 字段 | 说明 |
|---|---|
| `date` | `YYYY-MM-DD`（日级）或 `YYYY-MM`（月级）· 同一 client 内部体例一致 |
| `amount` | 金额（元）· 正数 |
| `type` | `inflow` / `outflow` / `fee` / `overdue` / `other` |
| `counterparty` | 对手方 · 主要对手 2-5 个 + 零散 |
| `note` | 可空 · "月末结款" / "工资" / "税费" / "采购付款" 等 |

**行为变化样本（hard/extreme ~60 家必须合理埋）**：

- **回款骤降**：近 3 月月均 inflow < 12 月均值 60%
- **余额异常波动**：周内多次大额 outflow 后立刻大额 inflow（对敲嫌疑）· counterparty 不要都是同一家（太明显即答案）
- **逾期事件**：1-3 条 `type=overdue`
- **集中度骤升**：单一 counterparty 月度占比 > 80%

easy/medium ~120 家：不设异常或仅设季节性正常波动（年末冲量、春节低谷）。

**命名混乱允许但仍 parse 得动**：主 CSV 外可夹 1-2 份月度辅助件 xlsx（例 `AP042_流水_2024Q1.xlsx` / `AP042_202312_转账明细.csv`）· 日期格式跨 client 可不同 · 列顺序同一 client 一致。

**复用**：可 `ls data/mock/deep-pillar/*/4、银行流水/` 看形态作锚定，**绝不复制数字**（独立再造 · 保量级）。产物独立存 `alert-pool/transactions/`，不复制 deep-pillar。

**零答案字段**：不出现 `is_anomaly` / `risk_tag` / `alert_flag` · 异常体现在**数字上**而非标注。

**完成信号**：`Signal: ALERT-POOL-TRANSACTIONS-DONE`

---

### Task C · 外部信号流 `alert-pool/external-signals/<client_id>.md`

**目标**：每家客户一份外部信号时间线 md · 近 12 月 3-10 条。

**路径**：`data/mock/alert-pool/external-signals/AP001.md` ... `AP180.md`（与 Task A client_id 严格对齐）

**md 模板**：

```markdown
# <企业名>（<client_id>）· 外部信号时间线

> 舆情/司法/工商/行业监管四源拼接 · 近 12 月 · 每条出处注明。

## <YYYY-MM-DD> · <信号类型>

<自然语言描述 2-4 行：时间、主体、事件、潜在影响>

出处：<媒体/法院/监管机构>

---

## <YYYY-MM-DD> · ...
```

**信号类型（每家挑 3-10 条）**：

- **舆情**：行业媒体负面 / 关联方爆雷 / 客户维权 / 经营异常传闻
- **工商变更**：股东变更、法人变更、减资、经营范围、地址搬迁
- **司法**：被起诉、失信被执、限消、股权冻结、刑事立案
- **行业事件**：所属行业监管处罚、同行业暴雷、产业政策调整、原材料剧烈波动

**分布红线（必须有"合理矛盾"）**：

- easy ~20：3-4 条**干净**（奖项、新签合同、行业白名单、展会）
- medium ~100：3-6 条**混合**（中性为主 + 1-2 条中性偏负面如小额诉讼）
- hard ~40：5-8 条**偏负面**（工商变更 + 中小额诉讼 + 行业负面 · 尚未失信被执）
- extreme ~20：6-10 条**密集高风险**（**失信被执/限消/股权冻结至少 1 条** + 股东大变动 + 多方起诉）
- **至少 10 家制造矛盾**：外部全负面但内部流水健康 / 外部中性但内部流水已异常——训练 Agent4 不被单源误导

**零答案字段红线**：

- md 不出现 `red_flag` / `risk_score` / `alert_level` / `should_trigger`
- 不写 "这是高风险客户，Agent4 应判红" 这类元注释
- 读者只能看到**时间线事件描述**，交叉判断全留给 Agent4

**出处合理性**：可 mock 媒体（财新网/每经网/21 世纪经济报道）、法院（XX 市中级人民法院）、监管机构（国家金融监督管理总局 XX 监管分局），**不指向真实已发生具体案件**。日期均匀分布 2025-05 ~ 2026-04，不集中在某周。

**完成信号**：`Signal: ALERT-POOL-SIGNALS-DONE`

---

## 3. 全部完成

三 Task commit 通过 + 自检过关 → `Signal: READY-FOR-DATA-FOUNDATION-B2-REVIEW`

---

## 4. 红线（反 5 原则本 Phase 落地）

| # | 原则 | 具体要求 |
|---|---|---|
| 1 | 盲测法 | clients.csv / transactions / signals 零答案字段（无 risk_level / alert_flag / red_flag / risk_score） |
| 2 | 难度分层 | 100-200 家覆盖 20/100/40/20 四档 · 档位 PM 私下维护 |
| 3 | 真实来源锚定 | 流水形态参照 `deep-pillar/*/4、银行流水/` · 信号参照公开工商/司法新闻形态 · **不复制内容** |
| 4 | 脱敏再造 | 企业名/法院名/媒体名/金额全部 mock · 测试阶段重名 OK（Q-029.D） |
| 5 | 环境边界 | Agent4 §3.5 表明确豁免 · 全 mock 外部信号不偷能力 |

### 目录硬边界

- ✅ 只动 `data/mock/alert-pool/`（新建）
- ✅ 允许微调本 onboarding（`docs/onboarding/batch-2-data-foundation-phase-2.md`）
- ❌ 不动 `data/mock/deep-pillar/` / `channel-kb/` / `compliance-kb/`（Phase 1 稳定 · 允许**读**不允许**写**）
- ❌ 不动 `agent_alert/` / `agent_*/` / `web/` / `evaluation/` / `shared/`

`git diff --stat` 只出现 `data/mock/alert-pool/**` + 可选的本 onboarding 微调。

### "合理矛盾"硬要求

不要出现"红档信号全负面 + 流水全异常 + 画像全拉胯"这种**过度整齐**——那是把答案递嘴边。必须存在：

- 部分红客户：外部干净 + 内部流水异常（内部先知道）
- 部分红客户：外部爆雷 + 内部流水滞后（外部先知道）
- 部分黄客户：外部多条负面但内部健康（观察期）
- 部分绿客户：外部 1 条非敏感工商变更（不该触发）

混淆性交叉样本**至少 10 家**。

### 格式多样

- CSV + md 为主 · 允许零星 xlsx 月报辅助
- 文件名允许中文+日期+序号混用（参照 `deep-pillar/DP001_龙峰精工/` 的形态）
- 主 CSV 必须规整可 parse（clients.csv 一份 · transactions/AP<id>.csv 主干一份）

---

## 5. 硬指标（交付前自检）

喊 `READY-FOR-DATA-FOUNDATION-B2-REVIEW` 前必须**7 条全过**：

1. `alert-pool/clients.csv` 行数 100-200（不含表头）
2. `alert-pool/transactions/AP<id>.csv` 时间序列 ≥ 12 月
3. `alert-pool/external-signals/AP<id>.md` 时间线 3-10 条（`^##` 计数）
4. `client_id` 跨三处一致：`grep -c '^AP' clients.csv` ≈ `ls transactions/ | wc -l` ≈ `ls external-signals/ | wc -l`
5. 零答案字段：`grep -rEi 'risk_level|alert_flag|red_flag|risk_score|difficulty|expected_color' data/mock/alert-pool/` **期望 0**
6. 难度分布大致 20/100/40/20（PM 内部对照 · 不写产物）
7. `git diff --stat` 只出现 `data/mock/alert-pool/**` + 本 onboarding（如微调）· 无越界

任一不过关不得喊 READY。

---

## 6. commit 粒度

三 Task 独立 commit，trailer 分别带：

- Task A：`Signal: ALERT-POOL-CLIENTS-DONE`
- Task B：`Signal: ALERT-POOL-TRANSACTIONS-DONE`
- Task C：`Signal: ALERT-POOL-SIGNALS-DONE`
- 自检 commit（或合并入 Task C）：`Signal: READY-FOR-DATA-FOUNDATION-B2-REVIEW`

失败可精准 `git revert <sha>`。

---

## 7. Kickoff Prompt

原样贴进 worker CLI 新窗口：

```
你是 data-foundation worker · Batch 2 · Phase 2 Agent4 mock。

【第一步】Resume doc-only commit，trailer `Signal: PRODUCT-HARDENING-BATCH-2-DF-P2-ACK`，仅记录"已接收 Phase 2 onboarding，准备开工"即可。

【第二步】强制 onboarding：
1. git fetch origin chore/l0-infra
2. git log origin/chore/l0-infra --format='%h %s' -15
3. 读 docs/handoff/decisions-log.md Q-028/A-028（环境边界反 5 原则）+ Q-029/A-029（Batch 2 四轨 + 测试豁免）
4. 读 docs/onboarding/batch-2-data-foundation-phase-2.md 全文
5. 读 docs/onboarding/data-foundation-phase-1-v2.md（Phase 1 反 5 原则范本）
6. 读 项目 CLAUDE.md §3.5 环境边界表（确认 Agent4 全 mock 豁免）
7. ls data/mock/deep-pillar/DP001_龙峰精工/4、银行流水/ 感受流水形态
8. 读 data/mock/channel-kb/historical-clients/ 1-2 份 md 感受企业名风格

【第三步】按 §2 顺序 Task A → B → C：
- A · clients.csv · 100-200 行薄画像 · 零答案 · 难度 20/100/40/20 · Signal: ALERT-POOL-CLIENTS-DONE
- B · transactions/AP<id>.csv · ≥12 月 · hard/extreme 埋行为变化不标注 · Signal: ALERT-POOL-TRANSACTIONS-DONE
- C · external-signals/AP<id>.md · 3-10 条 · 混合矛盾 · 零答案 · Signal: ALERT-POOL-SIGNALS-DONE

【红线】
- 只动 data/mock/alert-pool/ · 不动 deep-pillar/channel-kb/compliance-kb/agent_*/web/evaluation/shared
- 零答案：产物不得出现 risk_level/alert_flag/red_flag/risk_score/difficulty/expected_color
- 合理矛盾：红档不要信号流水全红，至少 10 家混淆交叉样本
- 数字脱敏再造保量级 · 测试阶段重名 OK（Q-029.D）
- 每 Task 独立 commit 带对应 Signal

【最终】三 Task 全过 + 7 条硬指标自检通过 → commit trailer `Signal: READY-FOR-DATA-FOUNDATION-B2-REVIEW`，停下等 main CLI 复核。

开干。
```

---

**维护者**：main CLI
**下次更新触发**：worker 交付 `READY-FOR-DATA-FOUNDATION-B2-REVIEW` 后 main CLI 复核 / 用户判方向变更
