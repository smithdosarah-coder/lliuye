# PRD: 授信决策辅助智能体 — Demo改造方案

> **版本**: v1.0
> **日期**: 2026-04-13
> **作者**: 众安信科AI中台团队
> **产品线**: 乾策平台(X-Nexus) — 信贷AI智能体矩阵 Agent3
> **状态**: Demo改造PRD

---

## 1. 产品定位

**一句话定位**: 读取信贷报告 --> 四维风险评估 --> 额度建议 -- 基于报告生成助手(Agent1)产出的EnterpriseProfile和结构化财务锚点，通过确定性算法完成四维风险评分矩阵、授信额度区间测算、同业对标分析，再由LLM生成结构化审批意见书，为信贷审批人员提供30秒内可得的量化决策支撑。

**核心重新定位说明**:

| 改造前 | 改造后 |
|--------|--------|
| 报告生成引擎的API包装层(agent_credit只是调用了主项目的section_generator/form_filler) | 独立的决策辅助工具："读报告 --> 出评估" |
| 输入：客户原始材料(PDF/Word/Excel) | 输入：Agent1产出的EnterpriseProfile JSON |
| 输出：填好的授信报告Word文档 | 输出：四维风险评分 + 额度建议区间 + 同业对标 + 审批意见书 |
| 与Agent1高度耦合（直接调用form_filler.py） | 仅通过EnterpriseProfile JSON解耦消费Agent1产出 |

**与其他Agent的关系**:

| Agent | 职责 | 数据流向 |
|-------|------|----------|
| Agent1 报告生成助手 | 解析客户材料，生成EnterpriseProfile JSON + 授信报告Word | 产出 --> Agent3消费 |
| Agent2 风控策略运营助手 | 贷中监控、预警规则管理、策略沙盒 | Agent3产出风险标签 --> Agent2消费 |
| **Agent3 授信决策辅助（本PRD）** | 四维风险评估 + 额度建议 + 同业对标 + 审批意见 | 消费Agent1产出，输出给Agent2和审批人员 |

**核心价值**: 将审批人员需要2-3小时完成的企业风险评估、额度测算、同业对比工作压缩到30秒内自动完成，并输出可追溯、可解释的量化结论。

---

## 2. Demo目标

### 2.1 给谁看

| 受众 | 关注点 |
|------|--------|
| 银行信贷条线分管领导 | 能否真正缩短审批时间？风险识别是否可靠？ |
| 银行科技部门负责人 | 与现有审批系统的集成复杂度？数据安全？ |
| 银行审批岗人员 | 评分逻辑是否透明？额度建议是否合理？ |
| 众安信科商务团队 | 差异化卖点是什么？与竞品的区别？ |

### 2.2 证明什么

1. **证明"AI可以做风险研判"** -- 不只是搬运数据，而是输出有逻辑链的风险评估结论
2. **证明"评分算法透明可审计"** -- 每个评分都有子指标明细和计算依据，不是黑盒
3. **证明"额度建议有锚点"** -- 四种独立算法交叉验证，不是拍脑袋
4. **证明"Agent矩阵协同"** -- 与Agent1(报告生成)的数据流转衔接，展示矩阵价值
5. **证明"高风险企业能识别"** -- 场景2的鼎盛商贸必须被正确标记为高风险

### 2.3 Demo核心指标

| 指标 | 目标值 |
|------|--------|
| 端到端评估耗时（加载画像 --> 完整报告） | < 30秒 |
| 四维评分生成 | 4个维度均有0-100评分 + 文字解读 |
| 额度建议输出 | 建议区间（下限-上限）+ 推荐值 + 计算依据 |
| 同业对标 | 至少5家同行业企业对比3项以上关键指标 |
| 审批意见 | 生成结构化审批意见书，含风险提示和授信建议 |
| LLM调用次数 | 不超过2次（审批意见1次 + 风险解读1次） |

### 2.4 Demo交付物

- 可运行的Gradio前端，包含完整评估流程演示
- 2份预置的EnterpriseProfile JSON（正常企业 + 高风险企业）
- 10家同业企业的mock对标数据库（2个行业各10家）
- 完整评估报告的导出（JSON + 前端可视化）

---

## 3. 演示场景设计

### 场景1: 瑞恒精密制造有限公司 -- 标准授信评估（正面案例）

**企业背景**:
- 名称: 瑞恒精密制造有限公司
- 行业: 通用设备制造业（C34）
- 成立年限: 8年
- 员工数: 156人
- 申请额度: 500万元流动资金贷款

**输入数据（预置EnterpriseProfile JSON）**:

```json
{
  "company_name": "瑞恒精密制造有限公司",
  "credit_code": "91320500MA1EXAMPLE",
  "industry": "C34-通用设备制造业",
  "established_years": 8,
  "employee_count": 156,
  "registered_capital": 2000,
  "financial_anchors": {
    "revenue_latest": 8560,
    "revenue_prev": 7230,
    "net_profit_latest": 412,
    "net_profit_prev": 338,
    "total_assets": 12800,
    "total_liabilities": 5120,
    "net_assets": 7680,
    "accounts_receivable": 2340,
    "inventory": 1560,
    "operating_cash_flow": 620,
    "short_term_borrowing": 1500,
    "ebitda": 580,
    "cash_received_from_sales": 7800,
    "period": "2025年度"
  },
  "guarantee_info": {
    "type": "抵押+保证",
    "collateral": "厂房及土地（评估值3200万元）",
    "collateral_value": 3200,
    "collateral_type": "房产土地",
    "guarantor": "法定代表人连带责任保证"
  },
  "existing_credit": {
    "total_approved": 300,
    "total_used": 280,
    "overdue_history": "无"
  },
  "request": {
    "amount": 500,
    "purpose": "补充流动资金",
    "term_months": 12
  }
}
```

**演示流程**:

```
Step 1 -- 加载企业画像
  +-- 系统提示："检测到报告生成助手已生成瑞恒精密制造有限公司企业画像"
  +-- 用户点击"加载并评估"
  +-- 解析EnterpriseProfile，展示企业基本信息摘要

Step 2 -- 四维风险评分（确定性计算，无需LLM）
  +-- 财务风险评分: 基于资产负债率/流动比率/营收增长率等
  +-- 行业风险评分: 基于行业基准数据+行业周期判断
  +-- 经营风险评分: 基于成立年限/营收规模/现金流覆盖率
  +-- 担保风险评分: 基于抵押物覆盖率/担保人资质
  +-- 输出: 四维雷达图 + 综合评分

Step 3 -- 授信额度计算（确定性算法，无需LLM）
  +-- 营收法: 年营收 x 行业系数
  +-- 净资产法: 净资产 x 杠杆上限
  +-- 现金流法: 经营性现金流 x 覆盖倍数
  +-- 担保法: 抵押物评估值 x 抵押率
  +-- 输出: 建议额度区间 + 推荐值 + 计算明细

Step 4 -- 同业对标（Mock数据查询，无需LLM）
  +-- 筛选同行业（C34）已授信客户
  +-- 对比: 营收规模/资产负债率/授信额度/综合评分
  +-- 输出: 对标表格 + 分位数定位

Step 5 -- LLM生成审批意见（1次调用）
  +-- 输入: 四维评分 + 额度建议 + 对标结果 + 企业画像
  +-- 输出: 结构化审批意见书
  +-- 包含: 风险提示/额度建议/期限建议/附加条件

Step 6 -- LLM风险因素解读（1次调用）
  +-- 输入: 四维评分明细 + 异常指标
  +-- 输出: 风险因素的自然语言解读
  +-- 包含: 主要风险点/缓释因素/关注事项
```

**预期输出**:

| 维度 | 预期评分 | 说明 |
|------|----------|------|
| 财务风险 | 72 | 资产负债率40%（良好），营收增长18.4%（优秀），但应收账款偏高 |
| 行业风险 | 65 | 制造业周期性风险中等，设备制造细分景气度尚可 |
| 经营风险 | 78 | 8年经营历史，规模适中，现金流覆盖良好 |
| 担保风险 | 82 | 抵押物覆盖率640%（充足），法人连带保证加强 |
| **综合评分** | **74** | 建议授信，额度区间428-642万元，推荐500万元 |

### 场景2: 鼎盛商贸有限公司 -- 高风险预警案例（负面案例）

**企业背景**（用于展示系统的风险识别能力）:
- 名称: 鼎盛商贸有限公司
- 行业: 批发业（F51）
- 成立年限: 3年
- 员工数: 28人
- 申请额度: 800万元

**关键风险特征**:
- 资产负债率 78%（过高）
- 营收同比下降12%
- 应收账款周转天数180天（远超行业均值90天）
- 担保物为存货质押（价值波动大）
- 存在关联交易
- 净利率仅1.2%

**预期结论**: 综合评分 < 50，系统自动标注"高风险"，风险等级D级，建议降低额度至200万元以内或拒绝，并列出6项以上风险关注点。

---

## 4. 前端交互设计

### 4.1 整体布局（三栏式）

```
+---------------------------------------------------------------------+
|  顶部导航栏:  授信决策辅助智能体  |  企业: [瑞恒精密制造有限公司 v]   |
+------------------+----------------------------+---------------------+
|                  |                            |                     |
|  左侧面板(250px) |  中间主区域(自适应)          |  右侧面板(350px)    |
|  企业画像摘要    |  四维雷达图 + 额度条         |  审批意见书         |
|                  |  同业对标表格               |                     |
|  +-----------+   |                            |  +---------------+  |
|  | 基本信息  |   |  +------------------+      |  | 审批结论      |  |
|  | 财务概要  |   |  |   雷达图(4维)    |      |  | ----------    |  |
|  | 担保信息  |   |  |   企业得分(蓝)   |      |  | 建议授信      |  |
|  | 征信摘要  |   |  |   风险阈值(红虚) |      |  | 推荐额度:500万|  |
|  | 申请信息  |   |  |   行业均值(灰虚) |      |  | 期限: 12个月  |  |
|  +-----------+   |  +------------------+      |  |               |  |
|                  |                            |  | 风险提示      |  |
|  评估进度:       |  +------------------+      |  | ----------    |  |
|  * 画像已加载    |  | 额度建议条形图   |      |  | 1.应收账款偏高|  |
|  * 评分完成      |  | 营收法 [==600==] |      |  | 2. ...        |  |
|  * 额度已算      |  | 净资产 [==640==] |      |  |               |  |
|  * 对标完成      |  | 现金流 [=434=]   |      |  | 附加条件      |  |
|  * 意见生成      |  | 担保法 [==640==] |      |  | ----------    |  |
|                  |  |                  |      |  | 1.补充抵押物  |  |
|  [切换场景 v]    |  | 综合 [428//500//642]|   |  | 2. ...        |  |
|                  |  +------------------+      |  +---------------+  |
|                  |                            |                     |
|                  |  +------------------+      |  风险因素解读       |
|                  |  | 同业对标表格     |      |  +---------------+  |
|                  |  | 企业  营收 负债率|      |  | 主要风险点    |  |
|                  |  | *瑞恒* 8560 40% |      |  | 缓释因素      |  |
|                  |  | 同业A 12300 35% |      |  | 关注事项      |  |
|                  |  | 同业B 9100  42% |      |  +---------------+  |
|                  |  +------------------+      |                     |
+------------------+----------------------------+---------------------+
|  底部: [导出评估报告JSON]  [导出PDF预览]  [发送至审批流]  [重新评估]  |
+---------------------------------------------------------------------+
```

### 4.2 可视化组件

#### 4.2.1 四维风险雷达图

使用Gradio Plot组件 + Plotly绘制：

```python
# 雷达图数据结构
radar_data = {
    "dimensions": ["财务风险", "行业风险", "经营风险", "担保风险"],
    "scores": [72, 65, 78, 82],        # 该企业得分
    "thresholds": [60, 60, 60, 60],    # 风险阈值线（低于此线标红）
    "industry_avg": [68, 62, 70, 75],  # 行业均值参考线
}
```

- 企业得分：实线填充（蓝色半透明）
- 风险阈值：虚线（红色）
- 行业均值：虚线（灰色）
- 低于阈值的维度自动标红并加感叹号标注

#### 4.2.2 额度建议条形图

水平条形图，展示四种测算方法的结果和最终建议区间：

```
营收法     |--------[====600====]--------|
净资产法   |------[===640===]------------|
现金流法   |----[==434==]----------------|
担保法     |----------[=====640=====]----|
                                        
综合建议   |---[428 ####500#### 642]-----|
           0    200   400   600   800  1000 (万元)

图例: [灰色条]=各方法测算值  [蓝色粗条]=建议区间
      黄色标记=申请额度位置  绿色标记=推荐额度
```

#### 4.2.3 同业对标表格

Gradio DataFrame组件，支持排序和高亮：

| 企业名称 | 营收(万) | 资产负债率 | 净利率 | 已授信额度(万) | 综合评分 | 分位 |
|----------|---------|-----------|-------|---------------|---------|------|
| **瑞恒精密(本企业)** | **8,560** | **40.0%** | **4.8%** | **申请500** | **74** | **P62** |
| 华鼎机械 | 12,300 | 35.2% | 5.6% | 800 | 81 | P78 |
| 正达装备 | 9,100 | 42.1% | 4.2% | 600 | 71 | P55 |
| 嘉铭工业 | 6,800 | 38.5% | 5.1% | 400 | 69 | P48 |
| ... | ... | ... | ... | ... | ... | ... |
| **行业中位数** | **7,200** | **41.0%** | **4.5%** | **450** | **68** | **P50** |

- 本企业行加粗蓝底高亮
- 优于行业中位数的指标绿色，劣于的红色
- 支持按任意列排序

### 4.3 交互流程

**Step 1: 企业画像加载**

```
+----------------------------------------------+
|  i 检测到报告生成助手已生成以下企业画像:        |
|                                              |
|  [文件] 瑞恒精密制造有限公司                   |
|     行业: C34-通用设备制造业                   |
|     画像生成时间: 2026-04-12 14:30            |
|     财务数据期间: 2025年度                     |
|                                              |
|  [ 加载并评估 ]    [ 手动上传JSON ]            |
+----------------------------------------------+
```

**Step 2: 评估进度实时更新**

每个步骤完成后实时更新左侧状态指示灯：
1. `o 画像加载中...` --> `* 画像已加载 [ok]`
2. `o 风险评分中...` --> `* 四维评分完成 [ok]`（显示雷达图）
3. `o 额度计算中...` --> `* 额度建议已生成 [ok]`（显示额度条）
4. `o 同业对标中...` --> `* 对标分析完成 [ok]`（显示对标表格）
5. `o 审批意见生成中...` --> `* 审批意见就绪 [ok]`（显示意见书）

**Step 3: 场景切换**

左侧面板底部"切换场景"下拉菜单：
- 瑞恒精密制造有限公司（正常案例）
- 鼎盛商贸有限公司（高风险案例）

切换后自动重新运行全流程，雷达图/额度条/对标表格/审批意见全部刷新。

---

## 5. 后端架构

### 5.1 模块总览

```
credit_decision_agent/
+-- app.py                      # Gradio前端入口
+-- credit_decision_agent.py    # 主Agent（CreditDecisionAgent）
+-- risk_scorer.py              # 四维风险评分引擎（纯确定性计算）
+-- amount_calculator.py        # 授信额度计算器（纯确定性计算）
+-- benchmark.py                # 同业对标模块（Mock数据查询）
+-- decision_prompts.py         # LLM提示词（审批意见+风险解读）
+-- models.py                   # 数据模型定义（dataclass）
+-- mock_data/
|   +-- enterprise_ruiheng.json # 预置企业画像（场景1-正常）
|   +-- enterprise_dingsheng.json # 预置企业画像（场景2-高风险）
|   +-- benchmark_c34.json      # 制造业对标数据库（10家企业）
|   +-- benchmark_f51.json      # 批发业对标数据库（10家企业）
|   +-- industry_baselines.json # 行业基准数据
+-- shared/                     # 复用模块（符号链接或包引用）
|   +-- base_agent.py           # Agent基类
|   +-- enterprise_profile.py   # EnterpriseProfile定义
|   +-- llm.py -> ../../llm.py  # LLM调用封装
+-- tests/
    +-- test_risk_scorer.py
    +-- test_amount_calculator.py
    +-- test_benchmark.py
```

### 5.2 保留、改造、新建模块清单

| 模块 | 动作 | 说明 |
|------|------|------|
| `shared/base_agent.py` | **保留** | Agent基类，提供LLM调用、状态管理等基础能力 |
| `shared/enterprise_profile.py` | **保留** | EnterpriseProfile数据结构定义，新增financial_anchors字段规范 |
| `shared/llm.py` | **保留** | LLM调用封装（DeepSeek/OpenAI），复用主项目的llm.py |
| `agent_credit/agent.py` | **改造(重写)** | 原来调用form_filler的逻辑全部移除，重写为CreditDecisionAgent |
| `agent_credit/app.py` | **改造(重写)** | 原来的Gradio前端重写为三栏布局+可视化组件 |
| `agent_credit/prompts.py` | **改造(重写)** | 原来的报告生成prompt全部替换为审批意见/风险解读prompt |
| `agent_credit/risk_classifier.py` | **删除** | 原有的简单风险分类逻辑，被risk_scorer.py替代 |
| `agent_credit/rating_engine.py` | **删除** | 原有的评级引擎，被四维评分矩阵替代 |
| `agent_credit/approval_engine.py` | **删除** | 原有的审批引擎，被amount_calculator.py + LLM审批意见替代 |
| `risk_scorer.py` | **新建** | 四维风险评分引擎，纯确定性计算 |
| `amount_calculator.py` | **新建** | 授信额度计算器，四种算法并行 |
| `benchmark.py` | **新建** | 同业对标模块，基于mock数据 |
| `decision_prompts.py` | **新建** | 审批意见+风险解读的LLM prompt |
| `models.py` | **新建** | 所有数据模型定义（RiskAssessment/AmountRecommendation等） |
| `mock_data/` | **新建** | 全部mock数据文件 |

### 5.3 CreditDecisionAgent（主Agent -- 改造重写）

```python
class CreditDecisionAgent(BaseAgent):
    """授信决策辅助主Agent
    
    职责：编排评估流程，协调各子模块，管理评估状态。
    设计原则：确定性计算优先，LLM仅用于自然语言生成（2次调用）。
    
    关键改造：
    - 移除：对form_filler.py / section_generator.py的所有调用
    - 移除：客户材料解析逻辑（这是Agent1的职责）
    - 新增：消费EnterpriseProfile JSON作为唯一输入
    - 新增：编排 RiskScorer -> AmountCalculator -> BenchmarkEngine -> LLM 流程
    """
    
    def __init__(self, api_key: str, provider: str = "deepseek"):
        super().__init__(api_key, provider)
        self.risk_scorer = RiskScorer()
        self.amount_calculator = AmountCalculator()
        self.benchmark_engine = BenchmarkEngine()
    
    def evaluate(self, profile: EnterpriseProfile) -> DecisionReport:
        """
        完整评估流程（端到端 < 30秒）
        
        Phase 1 -- 确定性计算（< 1秒，无LLM调用，可并行）
          - 四维风险评分
          - 额度区间计算（依赖风险等级，需在评分后）
          - 同业对标查询
        
        Phase 2 -- LLM生成（< 25秒，2次调用，串行）
          - 审批意见书
          - 风险因素解读
        
        Phase 3 -- 组装输出（< 1秒）
          - 组装DecisionReport
          - 生成风险标签集（供Agent2消费）
        """
        pass
    
    def evaluate_stream(self, profile: EnterpriseProfile) -> Generator:
        """流式评估，每完成一步yield中间结果给前端更新状态灯"""
        pass
```

### 5.4 risk_scorer.py -- 四维风险评分引擎（新建）

**设计原则**: 纯确定性计算，零LLM调用。所有评分规则写死在代码中，可审计、可回溯。评分采用分段线性插值，避免阶跃断点。

#### 5.4.1 财务风险评分（Financial Risk Score）

```python
class FinancialRiskScorer:
    """
    评分区间: 0-100（越高越好，表示风险越低）
    
    子指标及权重:
    +-- 资产负债率 (25%) -- 低于40%满分，60-70%中等，>80%高风险
    +-- 流动比率 (15%) -- >2.0满分，1.0-2.0中等，<1.0高风险
    +-- 营收增长率 (20%) -- >15%满分，0-15%中等，负增长扣分
    +-- 净利率 (15%) -- >8%满分，3-8%中等，<3%低分
    +-- 经营性现金流/净利润 (15%) -- >1.0满分，0.5-1.0中等，<0.5高风险
    +-- 应收账款周转天数 (10%) -- <60天满分，60-120天中等，>120天高风险
    """
    
    WEIGHTS = {
        "debt_ratio": 0.25,
        "current_ratio": 0.15,
        "revenue_growth": 0.20,
        "net_margin": 0.15,
        "cashflow_quality": 0.15,
        "ar_turnover": 0.10,
    }
    
    # 评分映射表（分段线性插值）
    # 格式: [(输入值, 得分), ...] -- 中间值线性插值
    SCORE_MAPS = {
        "debt_ratio": [
            # 资产负债率: 越低越好
            (0.0, 100), (0.30, 100), (0.40, 85),
            (0.50, 70), (0.60, 55), (0.70, 35),
            (0.80, 15), (1.0, 0),
        ],
        "current_ratio": [
            # 流动比率: 越高越好，但过高也不加分
            (0.0, 0), (0.5, 15), (1.0, 50),
            (1.5, 75), (2.0, 90), (3.0, 100),
        ],
        "revenue_growth": [
            # 营收增长率: 正增长好
            (-0.30, 0), (-0.10, 25), (0.0, 50),
            (0.05, 65), (0.10, 80), (0.15, 90), (0.30, 100),
        ],
        "net_margin": [
            # 净利率: 越高越好
            (-0.05, 0), (0.0, 20), (0.03, 50),
            (0.05, 70), (0.08, 85), (0.12, 100),
        ],
        "cashflow_quality": [
            # 经营性现金流/净利润: >1说明现金流质量好
            (-0.5, 0), (0.0, 20), (0.5, 50),
            (1.0, 80), (1.5, 95), (2.0, 100),
        ],
        "ar_turnover": [
            # 应收账款周转天数: 越短越好
            (30, 100), (60, 85), (90, 65),
            (120, 45), (150, 25), (180, 10), (240, 0),
        ],
    }
    
    def score(self, anchors: dict) -> FinancialRiskDetail:
        """
        输入: financial_anchors字典
        输出: FinancialRiskDetail（总分 + 各子指标得分 + 异常标记）
        
        计算步骤:
        1. 从anchors推导各子指标原始值
           - debt_ratio = total_liabilities / total_assets
           - current_ratio = (total_assets - 固定资产估算) / total_liabilities
             (简化: 用(accounts_receivable+inventory+cash)/short_term_borrowing近似)
           - revenue_growth = (revenue_latest - revenue_prev) / revenue_prev
           - net_margin = net_profit_latest / revenue_latest
           - cashflow_quality = operating_cash_flow / net_profit_latest
           - ar_turnover = accounts_receivable / revenue_latest * 365
        2. 对每个子指标做分段线性插值得到0-100分
        3. 加权求和得到维度总分
        4. 标记异常指标（得分<50的子指标）
        """
        pass
    
    def _interpolate(self, value: float, score_map: list) -> int:
        """分段线性插值"""
        pass
```

#### 5.4.2 行业风险评分（Industry Risk Score）

```python
class IndustryRiskScorer:
    """
    评分区间: 0-100
    
    子指标及权重:
    +-- 行业景气度 (30%) -- 基于industry_baselines.json中的prosperity_index
    +-- 行业集中度 (20%) -- CR10越低风险越分散，评分越高
    +-- 政策敏感度 (25%) -- 受政策调控影响程度（预设分类）
    +-- 周期性 (25%) -- 强周期行业扣分
    
    数据来源: industry_baselines.json（预置，Demo阶段为静态数据）
    """
    
    # 政策敏感度得分映射
    POLICY_SCORES = {"low": 85, "medium": 65, "high": 40}
    
    # 周期性得分映射
    CYCLICALITY_SCORES = {"low": 90, "medium": 65, "high": 35}
    
    def score(self, industry_code: str, baselines: dict) -> IndustryRiskDetail:
        """
        从行业基准数据中查找对应行业的各项指标，直接映射为评分。
        未知行业代码使用默认中等基准。
        """
        pass
```

#### 5.4.3 经营风险评分（Operational Risk Score）

```python
class OperationalRiskScorer:
    """
    评分区间: 0-100
    
    子指标及权重:
    +-- 成立年限 (20%) -- >5年满分，3-5年中等，<3年高风险
    +-- 营收规模 (20%) -- 与行业中位数对比的分位数评分
    +-- 现金流覆盖率 (25%) -- 经营性现金流/短期借款
    +-- 客户集中度 (15%) -- 前5大客户收入占比（若有数据，缺失则给默认60分）
    +-- 存货周转效率 (20%) -- 存货/营收比，越低越好
    """
    
    SCORE_MAPS = {
        "established_years": [
            (0, 10), (1, 25), (2, 40), (3, 55),
            (5, 75), (8, 90), (10, 95), (15, 100),
        ],
        "cashflow_coverage": [
            # 经营性现金流 / 短期借款
            (0.0, 10), (0.2, 30), (0.4, 55),
            (0.6, 70), (0.8, 85), (1.0, 95), (1.5, 100),
        ],
        "inventory_ratio": [
            # 存货/营收比: 越低越好
            (0.05, 100), (0.10, 85), (0.15, 70),
            (0.20, 55), (0.30, 35), (0.40, 15), (0.50, 0),
        ],
    }
    
    def score(self, profile: dict, baselines: dict) -> OperationalRiskDetail:
        pass
```

#### 5.4.4 担保风险评分（Guarantee Risk Score）

```python
class GuaranteeRiskScorer:
    """
    评分区间: 0-100
    
    子指标及权重:
    +-- 抵押物覆盖率 (40%) -- 抵押物评估值/申请额度
    +-- 抵押物类型 (25%) -- 房产土地>设备>存货>应收账款
    +-- 保证人强度 (20%) -- 法人连带保证、第三方担保、集团担保
    +-- 担保组合完整度 (15%) -- 多种担保方式组合加分
    """
    
    # 抵押物覆盖率评分
    COVERAGE_SCORE_MAP = [
        (0.0, 0), (0.5, 20), (1.0, 50),
        (1.5, 70), (2.0, 85), (3.0, 95), (5.0, 100),
    ]
    
    # 抵押物类型得分
    COLLATERAL_TYPE_SCORES = {
        "房产土地": 90,
        "设备": 65,
        "应收账款": 55,
        "存货": 40,
        "信用（无抵押物）": 10,
    }
    
    # 保证人强度得分
    GUARANTOR_SCORES = {
        "集团担保": 90,
        "第三方企业担保": 80,
        "法定代表人连带责任保证": 70,
        "实际控制人保证": 60,
        "无保证人": 20,
    }
    
    def score(self, guarantee_info: dict, request_amount: float) -> GuaranteeRiskDetail:
        pass
```

#### 5.4.5 综合评分汇总器

```python
class RiskScorer:
    """四维评分汇总器 -- 编排四个子评分器"""
    
    DIMENSION_WEIGHTS = {
        "financial": 0.35,    # 财务维度权重最高
        "industry": 0.15,
        "operational": 0.25,
        "guarantee": 0.25,
    }
    
    RISK_GRADES = [
        (80, "A"),   # >= 80: A级（低风险）
        (65, "B"),   # >= 65: B级（中低风险）
        (50, "C"),   # >= 50: C级（中等风险）
        (0,  "D"),   # <  50: D级（高风险）
    ]
    
    def score_all(self, profile: EnterpriseProfile) -> RiskAssessment:
        """
        返回:
        - 四维分数 + 各子指标明细
        - 综合加权评分
        - 风险等级: A(>=80)/B(>=65)/C(>=50)/D(<50)
        - 异常指标列表（用于LLM解读）
        - 风险标签集（用于下游Agent2消费）
        """
        pass
```

### 5.5 amount_calculator.py -- 额度计算器（新建）

**设计原则**: 四种算法并行计算，取有效算法结果的加权区间作为建议区间，推荐值取加权中位数。

```python
class AmountCalculator:
    """授信额度测算引擎
    
    四种独立算法:
    1. 营收法 -- 年营收 x 行业系数（系数来自industry_baselines.json）
    2. 净资产法 -- 净资产 x 风险等级对应杠杆上限
    3. 现金流法 -- 年经营性现金流 x 期限覆盖倍数
    4. 担保法 -- 抵押物评估值 x 折扣率（按抵押物类型）
    
    综合区间: 取所有有效算法结果的[P25, P75]作为建议区间
    推荐值: 有效算法结果的加权中位数
    """
    
    # 行业营收系数（申请额度/年营收的合理比例）
    REVENUE_COEFFICIENTS = {
        "C34": (0.05, 0.08),   # 通用设备制造: 5%-8%
        "F51": (0.03, 0.06),   # 批发业: 3%-6%
        "C39": (0.06, 0.10),   # 计算机制造: 6%-10%
        "C26": (0.04, 0.07),   # 化学原料制造: 4%-7%
        "DEFAULT": (0.04, 0.08),
    }
    
    # 风险等级对应杠杆上限（净资产法）
    LEVERAGE_LIMITS = {
        "A": 0.10,   # 优质客户: 净资产的10%
        "B": 0.08,
        "C": 0.05,
        "D": 0.02,   # 高风险: 严格控制
    }
    
    # 现金流覆盖倍数
    CASHFLOW_MULTIPLIERS = {
        12: 0.70,   # 1年期: 现金流的70%
        24: 1.20,   # 2年期: 现金流的120%
        36: 1.50,   # 3年期: 现金流的150%
    }
    
    # 抵押率（按抵押物类型）
    COLLATERAL_RATES = {
        "房产土地": 0.70,
        "设备": 0.50,
        "存货": 0.40,
        "应收账款": 0.60,
    }
    
    def calculate(self, profile: EnterpriseProfile,
                  risk: RiskAssessment) -> AmountRecommendation:
        """
        返回:
        - 四种算法各自的建议额度（数据不足的标记is_binding=False）
        - 综合建议区间 [lower, upper]
        - 推荐额度（加权中位数）
        - 与申请额度的对比结论
        - 每种算法的计算过程明细（可追溯）
        """
        pass
    
    def _revenue_method(self, anchors: dict, industry: str) -> MethodResult:
        """
        营收法: 
          额度下限 = 年营收 x 行业系数下限
          额度上限 = 年营收 x 行业系数上限
          建议额度 = (下限+上限)/2
        
        示例(瑞恒): 8560 x 0.05 = 428万 ~ 8560 x 0.08 = 685万
                    建议额度 = 557万
        """
        pass
    
    def _net_asset_method(self, anchors: dict, risk_grade: str) -> MethodResult:
        """
        净资产法:
          净资产 = 总资产 - 总负债（或直接使用net_assets字段）
          建议额度 = 净资产 x 风险等级杠杆上限
        
        示例(瑞恒, B级): 7680 x 0.08 = 614万
        """
        pass
    
    def _cashflow_method(self, anchors: dict, term_months: int) -> MethodResult:
        """
        现金流法:
          建议额度 = 年经营性现金流 x 覆盖倍数
          覆盖倍数根据贷款期限查表
        
        示例(瑞恒, 12个月): 620 x 0.70 = 434万
        """
        pass
    
    def _collateral_method(self, guarantee: dict) -> MethodResult:
        """
        担保法:
          建议额度 = 抵押物评估值 x 抵押率
          抵押率根据抵押物类型查表
        
        示例(瑞恒, 房产土地3200万): 3200 x 0.70 = 2240万
        注意: 此值通常远高于其他方法，在综合时被约束
        """
        pass
    
    def _synthesize(self, results: list[MethodResult],
                    requested: float) -> tuple[float, float, float, str]:
        """
        综合区间计算:
        1. 筛选is_binding=True的有效算法
        2. 按建议额度排序
        3. 取P25作为下限，P75作为上限（若只有2-3个有效算法，取min/max）
        4. 推荐值 = 有效算法建议额度的加权平均
        5. 与申请额度对比:
           - 申请在区间内 -> "within_range"
           - 申请低于下限 -> "below_range"
           - 申请高于上限 -> "above_range"
        """
        pass
```

### 5.6 benchmark.py -- 同业对标模块（新建）

```python
class BenchmarkEngine:
    """同业对标分析引擎
    
    数据源: mock_data/benchmark_{industry_code}.json
    对标维度: 营收、资产负债率、净利率、已授信额度、综合评分
    """
    
    def __init__(self, data_dir: str = "mock_data"):
        self.data_dir = data_dir
        self._cache = {}
    
    def compare(self, profile: EnterpriseProfile,
                risk: RiskAssessment) -> BenchmarkResult:
        """
        返回:
        - 同行业企业列表（最多10家，按营收规模排序）
        - 本企业在各指标的分位数（P0-P100）
        - 优于/劣于行业中位数的指标列表
        - 最相似企业（营收规模最接近的3家）的详细对比
        - 对标结论摘要（一句话）
        """
        pass
    
    def _load_peers(self, industry_code: str) -> list[dict]:
        """加载同行业对标数据，结果缓存"""
        pass
    
    def _calculate_percentile(self, value: float,
                               peers: list[float]) -> int:
        """计算分位数: 在peers中value排第几百分位"""
        pass
```

### 5.7 模块间调用流程

```
                    +----------------------+
                    |  EnterpriseProfile   |  (来自Agent1)
                    |  (JSON)              |
                    +----------+-----------+
                               |
                    +----------v-----------+
                    | CreditDecisionAgent  |
                    |   .evaluate()        |
                    +----------+-----------+
                               |
              Phase 1: 确定性计算（< 1秒）
          +------------+------------+
          v            v            v
   +-------------+ +---------+ +-----------+
   | RiskScorer  | | Amount  | | Benchmark |
   | .score_all()| | Calc    | | Engine    |
   |             | | .calc() | | .compare()|
   +------+------+ +----+----+ +-----+-----+
          |              |            |
          v              v            v
   RiskAssessment  AmountRecom.  BenchmarkResult
          |              |            |
          +--------------+------------+
                         |
              Phase 2: LLM生成（< 25秒，2次调用）
                         |
                +--------v--------+
                |   LLMClient     |
                |  .chat() x 2    |
                |  +-- 审批意见    |
                |  +-- 风险解读    |
                +--------+--------+
                         |
              Phase 3: 组装输出（< 1秒）
                         |
                +--------v--------+
                | DecisionReport  |
                |  +-- risk       |
                |  +-- amount     |
                |  +-- benchmark  |
                |  +-- opinion    |
                |  +-- risk_tags  |
                +-----------------+
```

**注意**: AmountCalculator.calculate()需要RiskAssessment的risk_grade作为输入（净资产法依赖风险等级），所以实际执行顺序是：
1. RiskScorer.score_all() + BenchmarkEngine.compare() **并行**
2. AmountCalculator.calculate() **在RiskScorer完成后**

---

## 6. 数据模型

### 6.1 输入模型: EnterpriseProfile

由Agent1（报告生成助手）产出，本Agent作为消费方。关键字段详见第9节接口定义。

### 6.2 RiskAssessment（四维评分结果）

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SubScore:
    """子指标得分"""
    name: str                    # 子指标名称，如"资产负债率"
    raw_value: float             # 原始值，如0.40
    display_value: str           # 展示值，如"40.0%"
    score: int                   # 得分0-100
    weight: float                # 权重
    is_anomaly: bool = False     # 是否异常（得分<50）
    anomaly_desc: str = ""       # 异常描述，如"资产负债率偏高(78%)"

@dataclass
class DimensionScore:
    """单维度评分"""
    dimension: str               # "financial"|"industry"|"operational"|"guarantee"
    dimension_cn: str            # "财务风险"|"行业风险"|"经营风险"|"担保风险"
    total_score: int             # 该维度加权总分 0-100
    sub_scores: list[SubScore]   # 子指标明细
    anomalies: list[str]         # 异常项描述列表

@dataclass
class RiskAssessment:
    """四维风险评估完整结果"""
    company_name: str
    assessment_time: str
    dimensions: dict[str, DimensionScore]   # 四个维度的评分
    composite_score: int                     # 综合加权评分
    risk_grade: str                          # A/B/C/D
    anomaly_summary: list[str]              # 所有异常汇总
    risk_tags: list[str]                    # 风险标签集，如["高负债","营收下滑"]
```

### 6.3 AmountRecommendation（额度建议）

```python
@dataclass
class MethodResult:
    """单种算法的计算结果"""
    method_name: str             # "营收法"|"净资产法"|"现金流法"|"担保法"
    suggested_amount: float      # 建议额度（万元）
    calculation_detail: str      # 计算过程描述，如"8560 x 0.065 = 556万"
    parameters_used: dict        # 使用的参数字典（可追溯审计）
    is_binding: bool = True      # 是否纳入综合计算（数据缺失时为False）

@dataclass
class AmountRecommendation:
    """额度建议完整结果"""
    method_results: list[MethodResult]   # 四种算法各自结果
    lower_bound: float                    # 建议下限（万元）
    upper_bound: float                    # 建议上限（万元）
    recommended: float                    # 推荐额度（万元）
    requested: float                      # 客户申请额度（万元）
    request_vs_suggestion: str            # "within_range"|"below_range"|"above_range"
    comparison_note: str                  # 对比说明文字
```

### 6.4 BenchmarkResult（对标结果）

```python
@dataclass
class PeerCompany:
    """对标企业"""
    name: str
    revenue: float               # 营收（万元）
    debt_ratio: float            # 资产负债率
    net_margin: float            # 净利率
    approved_amount: float       # 已授信额度（万元）
    composite_score: int         # 综合评分

@dataclass
class PercentilePosition:
    """分位数定位"""
    metric: str                  # 指标名称
    value: float                 # 本企业值
    percentile: int              # 分位数 P0-P100
    industry_median: float       # 行业中位数
    is_above_median: bool        # 是否优于中位数

@dataclass
class BenchmarkResult:
    """同业对标完整结果"""
    industry_code: str
    industry_name: str
    peer_count: int                           # 对标企业数量
    peers: list[PeerCompany]                  # 对标企业列表
    percentiles: list[PercentilePosition]     # 各指标分位数
    closest_peers: list[PeerCompany]          # 最相似企业（营收规模最近的3家）
    summary: str                              # 对标结论摘要（一句话）
```

### 6.5 DecisionReport（完整评估报告 -- 最终输出）

```python
@dataclass
class DecisionReport:
    """完整的授信决策评估报告"""
    # 元信息
    report_id: str                    # UUID
    company_name: str
    assessment_time: str              # ISO 8601
    assessor: str = "AI授信决策辅助智能体v1.0"
    
    # 输入数据快照（可追溯）
    profile_snapshot: dict            # EnterpriseProfile的JSON快照
    
    # 四大评估结果
    risk_assessment: RiskAssessment
    amount_recommendation: AmountRecommendation
    benchmark_result: BenchmarkResult
    
    # LLM生成内容
    approval_opinion: str             # 审批意见书（结构化文本）
    risk_interpretation: str          # 风险因素解读（结构化文本）
    
    # 结论
    overall_conclusion: str           # "建议授信"|"审慎授信"|"建议拒绝"
    suggested_conditions: list[str]   # 附加条件列表
    
    # 下游输出（流向Agent2）
    risk_tags: list[str]              # 风险标签集
    watch_metrics: list[dict]         # 贷后监控指标
    
    def to_json(self) -> str:
        """导出为JSON（归档/审计用）"""
        pass
    
    def to_summary_dict(self) -> dict:
        """导出前端展示用的摘要字典"""
        pass
```

### 6.6 评估状态机

```
IDLE --> LOADING --> SCORING --> CALCULATING --> BENCHMARKING --> GENERATING --> DONE
  |                                                                             |
  +-- 任意阶段异常 ----> ERROR（显示错误信息，支持重试）                          |
                                                                                |
  <------------------------ 用户点击"重新评估" ---------------------------------+
```

每个状态对应前端左侧面板的一个状态灯。

---

## 7. LLM调用设计

整个评估流程仅做 **2次** LLM调用，严格控制成本和延迟。所有数字计算均由Python确定性完成，LLM仅负责"把计算结果翻译成人话"。

### 7.1 调用1: 审批意见生成

**触发时机**: Phase 2，所有确定性计算完成后。

**Prompt策略**:

```python
APPROVAL_OPINION_SYSTEM = """你是一名资深银行信贷审批专家。
你的任务是基于量化评估结果撰写结构化的授信审批意见书。

【铁律】
1. 所有数字必须来自下方输入，不得编造或推算
2. 风险提示必须与异常指标一一对应
3. 附加条件要具体、可执行（不要写"加强管理"这种空话）
4. 语言专业简洁，符合银行内部审批文书风格
5. 结论必须明确：同意/审慎同意/建议拒绝，不要模棱两可
"""

APPROVAL_OPINION_USER = """
## 企业基本信息
{company_summary}

## 四维风险评分
- 财务风险: {financial_score}/100（{financial_grade}）
  异常项: {financial_anomalies}
- 行业风险: {industry_score}/100（{industry_grade}）
  异常项: {industry_anomalies}
- 经营风险: {operational_score}/100（{operational_grade}）
  异常项: {operational_anomalies}
- 担保风险: {guarantee_score}/100（{guarantee_grade}）
  异常项: {guarantee_anomalies}
- 综合评分: {composite_score}/100，风险等级: {risk_grade}

## 额度测算结果
- 营收法: {revenue_amount}万元（{revenue_detail}）
- 净资产法: {netasset_amount}万元（{netasset_detail}）
- 现金流法: {cashflow_amount}万元（{cashflow_detail}）
- 担保法: {collateral_amount}万元（{collateral_detail}）
- 建议区间: {lower_bound}-{upper_bound}万元
- 推荐额度: {recommended}万元
- 客户申请: {requested}万元（{comparison_note}）

## 同业对标摘要
{benchmark_summary}

---
请严格按以下结构输出审批意见书：

### 一、基本情况
（企业概况、申请事项，2-3句话）

### 二、风险评估结论
（综合评分、风险等级、主要风险点，3-5句话）

### 三、额度及期限建议
（建议额度、期限、还款方式，带具体数字和计算依据）

### 四、风险缓释措施
（担保安排、附加条件、监管要求，列表形式，至少3条）

### 五、审批意见
（"同意/审慎同意/建议拒绝" + 一句话结论）
"""
```

**参数**: Temperature=0.2, max_tokens=1000
**预期输出**: 400-600字

### 7.2 调用2: 风险因素解读

**触发时机**: 调用1完成后串行执行。

**Prompt策略**:

```python
RISK_INTERPRETATION_SYSTEM = """你是一名银行风险分析师。
请基于异常指标和评分明细，用通俗易懂但专业的语言解读风险因素。

【铁律】
1. 每个风险点必须引用具体数字
2. 解读要让非财务专业的审批人员也能理解
3. 不要重复审批意见书的内容，聚焦"为什么这是风险"和"严重程度如何"
4. 缓释因素要对冲具体的风险点，不要泛泛而谈
"""

RISK_INTERPRETATION_USER = """
## 异常指标清单
{anomaly_details}

## 评分明细（各子指标）
{score_details}

## 行业对标情况
{percentile_info}

---
请按以下结构输出：

### 主要风险点
（列出2-4个最关键的风险因素，每个附带数据支撑和严重程度判断）

### 缓释因素
（列出有利因素，说明其如何对冲上述风险）

### 持续关注事项
（列出需要在贷后阶段持续监控的指标及其阈值建议）
"""
```

**参数**: Temperature=0.2, max_tokens=800
**预期输出**: 300-500字

### 7.3 容错策略

| 异常场景 | 处理方式 |
|----------|----------|
| LLM调用超时(>30秒) | 使用模板化降级文案："基于综合评分{score}分({grade}级)，{conclusion}。详细分析因系统繁忙暂不可用，请稍后重试。" |
| LLM返回空/异常 | 重试1次，仍失败则使用降级文案 |
| LLM输出结构不完整 | 接受部分输出，缺失章节标注"生成异常，请人工补充" |
| LLM编造数字(不在输入中) | 前端展示时与输入数据做交叉校验，不一致的数字标红提示 |

### 7.4 调用成本估算

| 调用 | 输入token(估) | 输出token(估) | DeepSeek成本 |
|------|--------------|--------------|-------------|
| 审批意见生成 | ~1,500 | ~800 | ~0.003元 |
| 风险因素解读 | ~1,200 | ~600 | ~0.002元 |
| **合计** | **~2,700** | **~1,400** | **~0.005元/次评估** |

---

## 8. Mock数据规格

### 8.1 预置EnterpriseProfile JSON

**文件**: `mock_data/enterprise_ruiheng.json`

即第3节场景1中的完整JSON。包含：
- 企业基本信息（名称/行业/成立年限/员工数/注册资本）
- 财务锚点（营收/净利/资产/负债/现金流/EBITDA，最近两期）
- 担保信息（类型/抵押物/评估值/保证人）
- 现有授信（已批/已用/逾期记录）
- 本次申请（金额/用途/期限）

**文件**: `mock_data/enterprise_dingsheng.json`

场景2的高风险企业JSON。关键差异：

```json
{
  "company_name": "鼎盛商贸有限公司",
  "industry": "F51-批发业",
  "established_years": 3,
  "employee_count": 28,
  "registered_capital": 500,
  "financial_anchors": {
    "revenue_latest": 4200,
    "revenue_prev": 4774,
    "net_profit_latest": 50.4,
    "net_profit_prev": 143,
    "total_assets": 3800,
    "total_liabilities": 2964,
    "net_assets": 836,
    "accounts_receivable": 2100,
    "inventory": 680,
    "operating_cash_flow": 85,
    "short_term_borrowing": 1800,
    "period": "2025年度"
  },
  "guarantee_info": {
    "type": "质押",
    "collateral": "存货质押（评估值900万元）",
    "collateral_value": 900,
    "collateral_type": "存货",
    "guarantor": "实际控制人保证"
  },
  "existing_credit": {
    "total_approved": 500,
    "total_used": 490,
    "overdue_history": "2025年6月曾逾期15天"
  },
  "request": {
    "amount": 800,
    "purpose": "补充流动资金",
    "term_months": 12
  }
}
```

### 8.2 同业对标数据库

**文件**: `mock_data/benchmark_c34.json`

10家通用设备制造业（C34）企业：

```json
{
  "industry_code": "C34",
  "industry_name": "通用设备制造业",
  "peers": [
    {
      "name": "华鼎机械股份有限公司",
      "revenue": 12300, "net_profit": 738,
      "total_assets": 18500, "total_liabilities": 6512,
      "debt_ratio": 0.352, "net_margin": 0.060,
      "ar_turnover_days": 75,
      "approved_amount": 800, "composite_score": 81
    },
    {
      "name": "正达装备制造有限公司",
      "revenue": 9100, "net_profit": 382,
      "total_assets": 13200, "total_liabilities": 5554,
      "debt_ratio": 0.421, "net_margin": 0.042,
      "ar_turnover_days": 95,
      "approved_amount": 600, "composite_score": 71
    },
    {
      "name": "嘉铭工业科技有限公司",
      "revenue": 6800, "net_profit": 347,
      "total_assets": 9200, "total_liabilities": 3542,
      "debt_ratio": 0.385, "net_margin": 0.051,
      "ar_turnover_days": 82,
      "approved_amount": 400, "composite_score": 69
    },
    {
      "name": "恒泰精工机械有限公司",
      "revenue": 15600, "net_profit": 1092,
      "total_assets": 22000, "total_liabilities": 8360,
      "debt_ratio": 0.380, "net_margin": 0.070,
      "ar_turnover_days": 65,
      "approved_amount": 1200, "composite_score": 85
    },
    {
      "name": "铭远自动化设备公司",
      "revenue": 5200, "net_profit": 208,
      "total_assets": 7800, "total_liabilities": 3432,
      "debt_ratio": 0.440, "net_margin": 0.040,
      "ar_turnover_days": 108,
      "approved_amount": 300, "composite_score": 63
    },
    {
      "name": "中联重型装备集团",
      "revenue": 28000, "net_profit": 1960,
      "total_assets": 42000, "total_liabilities": 14700,
      "debt_ratio": 0.350, "net_margin": 0.070,
      "ar_turnover_days": 58,
      "approved_amount": 2500, "composite_score": 88
    },
    {
      "name": "德普精密制造有限公司",
      "revenue": 7500, "net_profit": 300,
      "total_assets": 10500, "total_liabilities": 4410,
      "debt_ratio": 0.420, "net_margin": 0.040,
      "ar_turnover_days": 92,
      "approved_amount": 450, "composite_score": 67
    },
    {
      "name": "博力特机电科技公司",
      "revenue": 11000, "net_profit": 550,
      "total_assets": 16000, "total_liabilities": 6880,
      "debt_ratio": 0.430, "net_margin": 0.050,
      "ar_turnover_days": 88,
      "approved_amount": 700, "composite_score": 73
    },
    {
      "name": "新锐动力装备公司",
      "revenue": 4500, "net_profit": 135,
      "total_assets": 6200, "total_liabilities": 2852,
      "debt_ratio": 0.460, "net_margin": 0.030,
      "ar_turnover_days": 115,
      "approved_amount": 200, "composite_score": 58
    },
    {
      "name": "鑫瑞重工有限公司",
      "revenue": 8800, "net_profit": 440,
      "total_assets": 13500, "total_liabilities": 5535,
      "debt_ratio": 0.410, "net_margin": 0.050,
      "ar_turnover_days": 85,
      "approved_amount": 550, "composite_score": 72
    }
  ]
}
```

**文件**: `mock_data/benchmark_f51.json` -- 10家批发业（F51）企业，结构相同，数据特征体现批发业轻资产、高周转、低利润率特点。

### 8.3 行业基准数据

**文件**: `mock_data/industry_baselines.json`

```json
{
  "C34": {
    "industry_name": "通用设备制造业",
    "prosperity_index": 68,
    "cr10": 0.15,
    "policy_sensitivity": "medium",
    "cyclicality": "medium",
    "median_debt_ratio": 0.41,
    "median_net_margin": 0.045,
    "median_revenue_growth": 0.08,
    "median_ar_turnover_days": 90,
    "revenue_coefficient_range": [0.05, 0.08]
  },
  "F51": {
    "industry_name": "批发业",
    "prosperity_index": 55,
    "cr10": 0.08,
    "policy_sensitivity": "low",
    "cyclicality": "high",
    "median_debt_ratio": 0.52,
    "median_net_margin": 0.025,
    "median_revenue_growth": 0.05,
    "median_ar_turnover_days": 85,
    "revenue_coefficient_range": [0.03, 0.06]
  }
}
```

---

## 9. 与其他Agent的数据接口

### 9.1 输入接口: 消费Agent1（报告生成助手）产出

#### 接口1: EnterpriseProfile JSON

```
来源: Agent1（报告生成助手）
传输方式: 文件系统（Demo阶段） / API调用（生产阶段）
路径约定: outputs/{company_name}_profile.json
```

**必需字段**:

| 字段路径 | 类型 | 说明 | 缺失处理 |
|----------|------|------|----------|
| `company_name` | str | 企业名称 | 拒绝评估 |
| `industry` | str | 行业代码+名称（如"C34-通用设备制造业"） | 使用DEFAULT行业基准 |
| `established_years` | int | 成立年限 | 经营评分该子项给默认60分 |
| `financial_anchors.revenue_latest` | float | 最近一期营收（万元） | 营收法不可用(is_binding=False) |
| `financial_anchors.revenue_prev` | float | 上一期营收（万元） | 营收增长率不可算 |
| `financial_anchors.net_profit_latest` | float | 最近一期净利润（万元） | 净利率/现金流质量不可算 |
| `financial_anchors.total_assets` | float | 总资产（万元） | 资产负债率不可算 |
| `financial_anchors.total_liabilities` | float | 总负债（万元） | 资产负债率不可算 |
| `financial_anchors.net_assets` | float | 净资产（万元）可从前两项推导 | 净资产法退化 |
| `financial_anchors.operating_cash_flow` | float | 经营性现金流（万元） | 现金流法不可用 |
| `financial_anchors.accounts_receivable` | float | 应收账款（万元） | 应收账款周转不可算 |
| `financial_anchors.inventory` | float | 存货（万元） | 存货周转不可算 |
| `financial_anchors.short_term_borrowing` | float | 短期借款（万元） | 现金流覆盖率不可算 |
| `guarantee_info` | object | 担保信息 | 担保维度评分为0 |
| `guarantee_info.collateral_value` | float | 抵押物评估值（万元） | 担保法不可用 |
| `guarantee_info.collateral_type` | str | 抵押物类型 | 使用默认抵押率 |
| `request.amount` | float | 申请额度（万元） | 无法做额度对比 |
| `request.term_months` | int | 申请期限（月） | 现金流法使用默认12个月 |

**容错策略**: 各评分子模块对数据缺失做降级处理（标记`is_binding=False`），而非拒绝整体评估。缺失字段超过50%时，报告中增加"数据完整度警告"。

#### 接口2: 财务锚点补充

```
来源: Agent1的truth_fill.py解析结果
格式: 结构化财务数据（资产负债表/利润表/现金流量表各科目）
场景: 当EnterpriseProfile中financial_anchors不完整时，回溯原始解析结果
```

**与Agent1代码的关系**:
- Agent1的`truth_fill.py`负责从Excel/PDF提取结构化财务数据
- Agent1的`section_generator.py`使用三阶段协议（证据组装->锚定撰写->自审门控）生成报告
- Agent3**不调用**Agent1的任何代码，仅消费其JSON产出
- 本Agent消费的是Agent1处理后的EnterpriseProfile，不是原始材料

### 9.2 输出接口: 供下游Agent消费

#### 接口1: 风险标签集 --> Agent2（风控策略运营/贷中预警）

```json
{
  "company_name": "瑞恒精密制造有限公司",
  "credit_code": "91320500MA1EXAMPLE",
  "assessment_time": "2026-04-13T10:30:00",
  "risk_grade": "B",
  "composite_score": 74,
  "risk_tags": [
    "应收账款偏高",
    "行业周期性风险中等",
    "短期借款集中度高"
  ],
  "watch_metrics": [
    {
      "metric": "应收账款周转天数",
      "current_value": 98,
      "threshold": 120,
      "alert_level": "yellow"
    },
    {
      "metric": "资产负债率",
      "current_value": 0.40,
      "threshold": 0.60,
      "alert_level": "green"
    }
  ],
  "approved_amount": 500,
  "conditions": [
    "每季度提交财务报表",
    "应收账款周转天数超过120天触发预警",
    "授信期内资产负债率不得超过60%"
  ]
}
```

**用途**:
- `risk_tags` --> Agent2用于贷后预警规则匹配
- `watch_metrics` --> Agent2设置贷中监控阈值
- `conditions` --> 写入授信合同条款

#### 接口2: 完整评估报告 --> 审批系统

```
格式: DecisionReport.to_json()
传输: API POST / 文件导出
用途: 审批人员查阅、归档、合规审计
```

### 9.3 接口版本管理

```
接口版本: v1.0
向后兼容策略:
- 新增字段不影响旧版消费方
- 移除字段需提前一个版本标记deprecated
- risk_tags枚举值变更需与Agent2同步
```

---

## 10. 验收标准

### 10.1 功能验收

| 编号 | 验收项 | 通过条件 |
|------|--------|----------|
| F-01 | 企业画像加载 | 加载预置JSON后，左侧面板正确展示企业基本信息、财务概要、担保信息 |
| F-02 | 四维风险评分 | 场景1企业，四个维度均输出0-100评分，综合评分在70-80区间 |
| F-03 | 风险等级判定 | 场景1判定为B级，场景2判定为D级 |
| F-04 | 额度计算--营收法 | 瑞恒: 8560 x (0.05~0.08) = 428~685万，结果在此区间 |
| F-05 | 额度计算--净资产法 | 瑞恒: 7680 x 0.08(B级) = 614万，误差<5% |
| F-06 | 额度计算--现金流法 | 瑞恒: 620 x 0.70 = 434万，误差<5% |
| F-07 | 额度计算--担保法 | 瑞恒: 3200 x 0.70 = 2240万（上限受其他方法约束） |
| F-08 | 额度区间合理性 | 建议区间包含客户申请额度500万，推荐值在400-650之间 |
| F-09 | 同业对标 | 展示至少5家同行业企业，本企业分位数标注正确 |
| F-10 | 审批意见生成 | LLM输出包含5个结构化章节，引用的数字与评分结果一致 |
| F-11 | 风险解读生成 | LLM输出至少列出2个风险点和1个缓释因素，数据引用准确 |
| F-12 | 高风险识别 | 场景2（鼎盛商贸）综合评分<50，结论为"建议拒绝"或"审慎授信" |
| F-13 | 数据缺失容错 | 删除financial_anchors中的operating_cash_flow后，系统仍可完成评估，现金流法标记为不可用 |
| F-14 | 场景切换 | 切换场景后所有组件（雷达图/额度条/对标表格/审批意见）全部正确刷新 |

### 10.2 性能验收

| 编号 | 验收项 | 通过条件 |
|------|--------|----------|
| P-01 | 确定性计算耗时 | Phase 1（评分+额度+对标）< 1秒 |
| P-02 | LLM调用耗时 | Phase 2（2次LLM调用）< 25秒 |
| P-03 | 端到端耗时 | 从点击"加载并评估"到完整报告展示 < 30秒 |
| P-04 | LLM调用次数 | 整个评估流程恰好2次LLM调用 |

### 10.3 可视化验收

| 编号 | 验收项 | 通过条件 |
|------|--------|----------|
| V-01 | 雷达图 | 四维评分以雷达图形式展示，低于阈值的维度标红 |
| V-02 | 额度条形图 | 展示四种方法的额度条+综合建议区间，申请额度有标记 |
| V-03 | 对标表格 | 表格可排序，本企业行高亮，优劣指标分色显示 |
| V-04 | 进度指示 | 评估过程中五个步骤的状态灯实时更新 |
| V-05 | 高风险视觉区分 | 场景2评估结果的雷达图明显"塌陷"，综合评分区域标红 |

### 10.4 接口验收

| 编号 | 验收项 | 通过条件 |
|------|--------|----------|
| I-01 | EnterpriseProfile解析 | 正确解析Agent1产出的标准格式JSON |
| I-02 | 风险标签输出 | 输出的risk_tags为非空字符串数组 |
| I-03 | watch_metrics输出 | 至少包含2项监控指标，每项有current_value和threshold |
| I-04 | JSON导出 | DecisionReport.to_json()输出合法JSON，可被json.loads解析 |
| I-05 | 评估报告可追溯 | profile_snapshot包含完整的输入数据快照 |

### 10.5 边界条件验收

| 编号 | 验收项 | 通过条件 |
|------|--------|----------|
| E-01 | 空EnterpriseProfile | 仅有company_name时，系统给出"数据不足"提示而非崩溃 |
| E-02 | 极端财务数据 | 资产负债率>100%时，财务评分为0分但不报错 |
| E-03 | 未知行业代码 | 行业代码不在预置库中时，使用默认基准数据，给出提示 |
| E-04 | LLM超时 | 单次LLM调用超过30秒时，使用降级文案 |
| E-05 | 负净利润 | 净利润为负时，净利率评分为0，现金流质量指标正常计算 |
| E-06 | 抵押物类型未识别 | 不在预置类型表中的抵押物，使用最低抵押率(0.30) |

---

## 附录A: 与现有agent_credit代码的映射关系

| 现有文件 | 现有功能 | 改造后对应 |
|----------|----------|-----------|
| `agent_credit/agent.py` | 调用form_filler生成报告 | **重写** --> credit_decision_agent.py（评估编排） |
| `agent_credit/app.py` | 简单对话界面 | **重写** --> app.py（三栏可视化界面） |
| `agent_credit/prompts.py` | 报告生成prompt | **重写** --> decision_prompts.py（审批意见+风险解读） |
| `agent_credit/risk_classifier.py` | 简单风险分类(高/中/低) | **替换** --> risk_scorer.py（四维评分矩阵） |
| `agent_credit/rating_engine.py` | 企业评级 | **替换** --> risk_scorer.py综合评分 |
| `agent_credit/approval_engine.py` | 审批结论 | **替换** --> amount_calculator.py + LLM审批意见 |

## 附录B: 评分公式速查表

**财务风险综合评分**:
```
F_score = 0.25*S(debt_ratio) + 0.15*S(current_ratio) + 0.20*S(revenue_growth)
        + 0.15*S(net_margin) + 0.15*S(cashflow_quality) + 0.10*S(ar_turnover)
```

**综合评分**:
```
C_score = 0.35*F_financial + 0.15*F_industry + 0.25*F_operational + 0.25*F_guarantee
```

**额度综合区间**:
```
有效算法 = [m for m in [营收法,净资产法,现金流法,担保法] if m.is_binding]
lower = percentile(有效算法.amounts, 25)
upper = percentile(有效算法.amounts, 75)
recommended = weighted_mean(有效算法.amounts)
```

---

*文档结束 -- PRD_授信决策辅助智能体_v1.0*
