# EnterpriseProfile / ReportJSON Handoff Contract · v1.0-2026-04-18

**冻结日期**：2026-04-18  
**版本**：v1.0  
**来源**：Agent6 报告助手（agent_report/ + truth_fill.py、material_kb.py、section_generator.py）  
**下游消费方**：Agent1 获客、Agent3 授信决策、Agent5 合规审核  
**契约维护人**：主 CLI  
**变更通告机制**：破坏性变更时主 CLI 在 docs/review/contract-changes.md 发公告

---

## 〇、契约对象语义澄清（Q-004 A-004 补）

**本契约对象**：Agent6 v16 产出的 **ReportJSON（Python dict / JSON payload）** —— 即 `agent_report/` 管线通过 `truth_fill.py` + `material_kb.py` + `section_generator.py` 汇总输出的 handoff 载荷。

**本契约对象不等同于** `shared/enterprise_profile.py` 的 Pydantic 实例 —— 该 Pydantic 类是 Agent6 **内部扁平画像**（从 KB 层 `from_kb` 工厂产出），不参与跨 Agent handoff。历史上两者名字相同但结构不同是语义模糊的历史遗留，Phase 2 将由主 CLI 发 RFC 评估 `shared/enterprise_profile.py` 升级到嵌套结构或废弃 + 走 runtime schema 校验。

**下游消费约束**：Agent1 / Agent3 / Agent5 只能按本契约的嵌套 JSON 结构消费，**禁止** `from shared.enterprise_profile import EnterpriseProfile` 当 handoff 载体反序列化。

---

## 一、顶层结构概览

**必填字段（2）**：
- profile_id: str
- company_name: str

**基本信息（9）**：unified_credit_code、industry、establishment_date、registered_capital、employee_count、region、main_business、controller_name、controller_share_pct

**核心子结构（7）**：
- FinancialAnchors（11字段）：revenue/profit/assets/liabilities/cash_flow 等
- GuaranteeInfo（5字段）：type、collateral、collateral_value、collateral_type、guarantor
- RelatedPartyInfo（2字段）：revenue_pct、txn_desc
- ExistingCredit（3字段）：total_approved、total_used、overdue_history
- CreditRequest（3字段）：amount、purpose、term_months
- Chapters（4字段）：chapter_1/2/3/4 报告正文
- AgentOutputs（1字段）：agent6_report_json（当前占位）

**元数据（3）**：source_materials、generated_at、business_line

**总计**：21 个顶层字段，其中 2 必填，19 Optional；7 个子结构，28 个子字段

---

## 二、字段详表

### 2.1 必填与基本信息

| 字段 | 类型 | 来源 | 说明 |
|---|---|---|---|
| profile_id | str | api.py:L360 | 报告标识，格式 report_<company>_<timestamp> |
| company_name | str | material_kb.py:L206 | 企业名称，regex 提取 |
| unified_credit_code | Optional[str] | （当前未提取，需人工或社信中心补充） | 统一社会信用代码 |
| industry | Optional[str] | material_kb.py:L291 | 国标行业代码，regex 提取 |
| establishment_date | Optional[str] | material_kb.py:L216 | 成立日期，YYYY-MM-DD 或 YYYY年MM月DD日 |
| registered_capital | Optional[str] | material_kb.py:L226 | 注册资本，含单位如"1000万元" |
| employee_count | Optional[int] | api.py:L369 | 员工人数，来自 KB 或手工输入 |
| region | Optional[str] | （当前置为 None） | 经营地区/省份 |
| main_business | Optional[str] | material_kb.py:L644+ | 主营业务描述 |
| controller_name | Optional[str] | material_kb.py:L314 | 实控人名称，regex 提取 |
| controller_share_pct | Optional[str] | material_kb.py:L325 | 实控人持股比例，如"80%" |

### 2.2 财务数据锚点（FinancialAnchors，单位万元）

| 字段 | 类型 | 最新年 | 前年 | 来源 |
|---|---|---|---|---|
| revenue_latest | Optional[float] | ✓ | — | truth_fill.py deterministic |
| revenue_prev | Optional[float] | — | ✓ | 同上 |
| net_profit_latest | Optional[float] | ✓ | — | 同上 |
| net_profit_prev | Optional[float] | — | ✓ | 同上 |
| total_assets | Optional[float] | ✓ | — | 同上 |
| total_liabilities | Optional[float] | ✓ | — | 同上 |
| net_assets | Optional[float] | ✓ | — | 同上 |
| accounts_receivable | Optional[float] | ✓ | — | 同上，~50% 填充率 |
| inventory | Optional[float] | ✓ | — | 同上，~50% 填充率 |
| operating_cash_flow | Optional[float] | ✓ | — | 同上 |
| short_term_borrowing | Optional[float] | ✓ | — | 同上 |
| ebitda | Optional[float] | ✓ | — | 同上，~40% 填充率 |
| period | Optional[str] | — | — | "2024年度" 或 "2025年1-9月" |

### 2.3 担保信息（GuaranteeInfo）

| 字段 | 示例 | 来源 |
|---|---|---|
| type | "保证" / "抵押" / "质押" | 申报表或人工补充 |
| collateral | "住宅一套" / "土地使用权" / "无抵押" | material_kb.py + manual |
| collateral_value | 280 (万元) | 申报表或评估报告 |
| collateral_type | "住宅" / "土地" / "车辆" | 申报表 |
| guarantor | "法人连带保证" / "配偶连带保证" | material_kb.py + 风险部补充 |

### 2.4 关联交易（RelatedPartyInfo）

| 字段 | 示例 | 说明 |
|---|---|---|
| related_party_revenue_pct | 0.45 | 关联交易占营收比例，0-1 之间 |
| related_party_txn_desc | "大量交易来自关联公司 XXX，年度金额 8100 万，占营收 45%" | 具体描述 |

### 2.5 既有授信（ExistingCredit）

| 字段 | 类型 | 说明 |
|---|---|---|
| total_approved | Optional[float] | 历史授信总额（万元） |
| total_used | Optional[float] | 已用额度（万元） |
| overdue_history | Optional[str] | "2024年曾出现M1逾期1次(已结清)" / "无逾期记录" |

### 2.6 申报信息（CreditRequest）

| 字段 | 单位 | 示例 |
|---|---|---|
| amount | 万元 | 500 |
| purpose | 文本 | "补充流动资金" / "门店装修升级" |
| term_months | 月 | 12 / 24 |

### 2.7 报告正文（Chapters）

| 字段 | 规范 | 来源 |
|---|---|---|
| chapter_1_background | 3-5句，企业背景与基本信息 | section_generator.py Phase 2 |
| chapter_2_operation | 5-8句，经营情况、上下游、市场位置 | 同上 |
| chapter_3_finance | 6-10句，财务分析（必须三段式：数据→外因→内因） | 同上 + Phase 3 校验 |
| chapter_4_conclusion | 待 Agent3 回填，审批意见与评级 | (stub 当前为占位) |

**质量规范**（section_generator 硬规则）：
- 禁止从训练数据补充未材料化的信息
- 数字必须来自证据清单(✓标记)，不得编造
- 缺失数据需具体列出所需材料，禁止"材料不足"兜底
- 浮点数保留2位小数
- 财务分析禁止只写模糊结论

---

## 三、下游消费指引

### Agent1 获客
**关键字段**：profile_id | company_name | industry | region | business_line | request.amount | financial_anchors.revenue_latest

**用途**：lead pool 营收/行业/地区多维聚类，lookalike 策略分流

### Agent3 授信决策
**关键字段**：financial_anchors.* | guarantee_info.* | existing_credit.overdue_history | chapters.chapter_3_finance

**用途**：自动填充授信申报表"财务分析"段，四维评分代入

### Agent5 合规审核
**关键字段**：company_name | controller_name | related_party_info | source_materials

**用途**：实控人AML查询、关联交易风险预警、溯源

---

## 四、已知不稳定字段

| 字段 | 原因 | 当前状态 | 降级 |
|---|---|---|---|
| business_line | V15刚引入，Agent1评估中 | Optional，可为None | 按 revenue 启发式推断 |
| chapter_4_conclusion | 待Agent3回填 | stub占位符 | 缺失时用ch3摘要 |
| agent6_report_json | 预留，功能未启用 | 始终None | 忽略 |
| ebitda | 不是所有企业可算 | 30-40%填充率 | 改用EBIT/营利润 |
| accounts_receivable/inventory | 仅细表可提 | 50%填充率 | 询问企业补充 |

---

## 五、破坏性变更规则

**通告形式**：主 CLI 在 docs/review/contract-changes.md 发公告

**下游响应**：收到通告后 3 工作日内评估并发 PR

**破坏性变更类型**：
- 顶层字段删除/重命名
- 子结构新增 Required 字段
- 字段类型改变（int→float）
- 枚举值删除或含义变化
- 单位转换（万元→元）

**向后兼容**（无需公告）：
- 新增 Optional 字段
- 字段长度上限扩大
- 枚举值新增（不删除原值）

---

## 六、验证清单

接收方应执行：
1. ✓ profile_id、company_name 非空
2. ✓ 财务一致：total_assets ≈ liabilities + net_assets (误差<0.1)
3. ✓ 关联交易：related_party_revenue_pct ∈ [0, 1]
4. ✓ 担保完整：有 collateral 则有 value
5. ✓ 字段类型：Pydantic ValidationError 时降级处理

---

**维护者**：主 CLI | **冻结日期**：2026-04-18 | **下次审查**：2026-05-18

