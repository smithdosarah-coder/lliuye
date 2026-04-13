# 信贷报告助手项目 KT 文档

> 编写时间：2026-04-09
> 目的：让下一个 Claude 无缝接续开发工作

---

## 一、项目概述

### 1.1 功能定位
自动填写银行信贷报告模板（普惠授信申报及审查审批意见表）。系统读取客户材料（财务报表、企业资料等），用 LLM 自动填写表单字段，输出填好的 Word 文档，并标注未能自动填写的字段。

### 1.2 技术架构

```
用户上传材料 → material_kb.py (KB构建) → form_filler.py (填写引擎) → 输出Word文档
                      ↓
              truth_fill.py (确定性预填充)
```

### 1.3 启动方式
```bash
python app.py  # Gradio 前端入口
```

---

## 二、核心文件说明

| 文件 | 行数 | 职责 |
|------|------|------|
| `app.py` | ~500 | Gradio 前端入口 (v7.23) |
| `agent.py` | ~1000 | Agent 核心逻辑 (v7.5，支持双模式) |
| `form_filler.py` | ~6580 | 表单填写引擎（主流水线） |
| `material_kb.py` | ~717 | 材料知识库构建（多维度事实提取） |
| `truth_fill.py` | ~756 | 确定性预填充（绕过 LLM 的精确填写） |
| `prompts.py` | ~800 | LLM 提示词模板 |
| `llm.py` | ~200 | LLM 调用封装 |
| `tools.py` | ~400 | 工具函数（文件读取等） |
| `quality_check.py` | ~300 | 质量检查 |
| `period_matcher.py` | ~150 | 时间周期匹配工具 |

---

## 三、当前开发状态：五项架构改造

### 3.1 改造背景
用户反馈初期方案"治标不治本"——针对具体问题的补丁式修复无法解决根本问题。经重新设计，确定了五项架构级改造，目标是让机器生成的报告质量尽可能接近人工报告。

### 3.2 五项改造总览

| 序号 | 改造名称 | 状态 | 核心目标 |
|------|----------|------|----------|
| 改造五 | truth_fill 扩展 | ✅ 已完成 | 确定性提取覆盖所有可提取事实 |
| 改造二 | KB 材料理解层重构 | ✅ 已完成 | 从全量截断改为按需检索 |
| 改造一 | 模板语义解析层 | ✅ 已完成 | LLM 理解模板语义规范 |
| 改造三 | 语义块驱动填写引擎 | ✅ 已完成 | 按语义块而非字段类型批处理 |
| 改造四 | 生成时约束 | ✅ 已完成 | 结构化输出+生成时验证 |

**依赖关系**：改造五 → 改造二 → 改造一 → 改造三 → 改造四

**状态**：✅ 五项改造全部完成

---

## 四、改造五：truth_fill 扩展（已完成）

### 4.1 改造内容

#### 4.1.1 `material_kb.py` 完全重写

**之前**：307行，单文件提取，硬编码表格编号（"表格2"=上游供应商），仅提取约12种事实类型

**之后**：~717行，核心改进：
- 扫描**所有上传文件**（不只一个"授信补充"文档）
- **语义表头识别**：通过列名关键词识别表格类型，而非硬编码编号
- 15+ 维度事实提取
- 7 个正则提取函数

**新增函数**：
```python
def _identify_table_type(header_row: list[str]) -> str | None:
    # 识别：shareholders, upstream, downstream, financing, affiliates,
    # r_and_d, bank_flows, orders, tax_data, receivables_top5,
    # other_receivables_top5, payables_top5, assets, patents

def _extract_basic_info(all_text: str, facts: dict):
    # 提取：company_name, establishment_date, registered_capital,
    # paid_in_capital, social_insurance_count, employee_count,
    # legal_representative, industry, operating_address

def _extract_controller_info(all_text: str, facts: dict):
    # 提取：controller_name, controller_id, controller_share_pct,
    # spouse_name, spouse_id, controller_resume

def _extract_credit_history(all_text: str, facts: dict):
    # 提取：credit_cooperation_history, prev_approval_date,
    # is_existing_customer, prev_credit_exposure, prev_guarantee_method,
    # prev_pd_rating, loan_drawdown_info

def _extract_risk_info(all_text: str, facts: dict):
    # 提取：risk_signals, negative_info, esg_rating, aml_risk_level

def _extract_order_info(all_text: str, facts: dict):
    # 提取：orders_count, orders_total_amount, orders_uncollected

def build_material_kb(file_contents: dict[str, str]) -> dict[str, Any]:
    # 返回结构化 KB：source_files, facts (扁平字典), tables (类型化表格数据)
```

#### 4.1.2 `truth_fill.py` 新增 4 个预填充函数

```python
def prefill_shareholder_table(doc, nested_tables, kb, log=None) -> int:
    """填写股东表格（区分于关联企业表）"""
    # 关键：检查表头有"股东名称/认缴出资/出资比例"但没有"成立时间/净利润/融资"

def prefill_asset_table(doc, nested_tables, kb, log=None) -> int:
    """填写借款人/实控人资产表"""

def prefill_bank_flow_table(doc, nested_tables, kb, log=None) -> int:
    """填写银行流水核验表"""

def prefill_labeled_fields_from_kb(labeled_fields, kb) -> dict[str, str]:
    """确定性预填标签字段（客户经理、联系电话、注册资本等）"""
    # 覆盖：客户经理, 联系电话, 注册资本, 实收资本, 法定代表人,
    # 社保人数, 员工人数, 实控人持股比例, 反洗钱风险等级
```

#### 4.1.3 `form_filler.py` 集成修改

1. **Import 更新**（第35行）：
   ```python
   from truth_fill import (
       prefill_supply_chain_tables,
       prefill_kb_structured_tables,
       prefill_shareholder_table,
       prefill_asset_table,
       prefill_bank_flow_table,
       prefill_labeled_fields_from_kb,
   )
   ```

2. **Pipeline 集成**（第2109-2141行）：添加了股东表、资产表、银行流水表的 KB 预填调用

3. **`_is_bank_internal_lf` 重写**（第2240行）：
   - 之前：跳过 10 个关键词（申报额度、PD评级、担保方式等）
   - 之后：只跳过真正银行内部签名字段（审查员、审批人、分管行长、行长、日期、共同调查人）

4. **标签字段预填替换**：旧硬编码2字段逻辑替换为 `prefill_labeled_fields_from_kb()` 调用

5. **`_build_company_profile` 增强**：新增 establishment_date, paid_in_capital, social_insurance_count, operating_address, controller_share_pct, spouse_name, 客户类型, prev_approval_date, prev_credit_exposure, 订单汇总

---

## 五、改造二：KB 材料理解层重构（已完成）

### 5.1 问题诊断

之前 `_build_materials_text` 方法采用"全量截断"策略——LLM 收到的是截断的文本块，无法知道哪些材料与当前填写任务最相关。

### 5.2 解决方案

改为"按需检索"模式：每个填写阶段只接收相关的 KB 维度数据。

### 5.3 完成内容

#### 5.3.1 `material_kb.py` 新增函数

```python
# 维度定义（17个维度）
DIMENSION_FIELDS = {
    "basic_info": [...],      # 企业基本信息
    "controller": [...],      # 实控人
    "shareholders": [...],    # 股东
    "business": [...],        # 业务
    "supply_chain": [...],    # 供应链
    "affiliates": [...],      # 关联企业
    "financing": [...],       # 融资
    "credit_history": [...],  # 授信历史
    "risk": [...],            # 风险
    "orders": [...],          # 订单
    "assets": [...],          # 资产
    "bank_flows": [...],      # 银行流水
    "r_and_d": [...],         # 研发
    "tax_data": [...],        # 税务
    "customer_manager": [...],# 客户经理
    "patents": [...],         # 专利
    "receivables": [...],     # 应收应付
}

# 字段类型→维度映射（56个关键词）
FIELD_TYPE_DIMENSIONS = {
    "企业名称": ["basic_info"],
    "实控人": ["controller", "basic_info", "shareholders"],
    "上游": ["supply_chain"],
    # ... 等
}

# 核心函数
def build_dimension_text(kb, dimensions, max_chars=8000, include_raw_tables=False) -> str:
    """根据维度列表构建 KB 文本，只包含相关维度"""

def infer_dimensions_for_field(field) -> list[str]:
    """从字段上下文推断相关维度"""

def infer_dimensions_for_batch(fields) -> list[str]:
    """从字段批次推断相关维度"""

def infer_dimensions_for_label(label, context="") -> list[str]:
    """从标签推断相关维度"""

def infer_dimensions_for_example(example_text) -> list[str]:
    """从示例段落推断相关维度"""
```

#### 5.3.2 `form_filler.py` Prompt 函数修改

1. **`build_field_extraction_prompt`**（第729行）：
   - 新增 `kb` 参数
   - 使用 `infer_dimensions_for_batch` 推断维度
   - 调用 `build_dimension_text` 获取相关材料

2. **`build_labeled_field_prompt`**（第1278行）：
   - 新增 `kb` 参数
   - 使用 `infer_dimensions_for_label` 推断维度

3. **`build_example_rewrite_prompt`**（第1387行）：
   - 新增 `kb` 参数
   - 使用 `infer_dimensions_for_example` 推断维度

#### 5.3.3 Pipeline 调用更新

三个调用点已更新，传入 `kb=getattr(self, "kb", None)`：
- 第2225行：`build_field_extraction_prompt(..., kb=getattr(self, "kb", None))`
- 第2326行：`build_labeled_field_prompt(..., kb=getattr(self, "kb", None))`
- 第2447行：`build_example_rewrite_prompt(..., kb=getattr(self, "kb", None))`

---

## 五点五、改造一：模板语义解析层（已完成）

### 5.5.1 问题诊断

之前系统把模板当作"容器来填充"，LLM 只看到字段上下文，不理解字段在审批决策中的作用、数据来源、填写要求。

### 5.5.2 解决方案

在 Phase 0.5 阶段，让 LLM 分析模板语义规范，生成字段语义指导，注入后续填写 prompt。

### 5.5.3 完成内容

#### `form_filler.py` 新增函数（第723-886行）

```python
def build_template_semantic_analysis_prompt(
    fields, checkboxes, examples, labeled_fields, nested_tables
) -> tuple[str, str]:
    """构建模板语义分析 prompt，让 LLM 理解模板规范"""

def parse_template_semantic_analysis(response: str) -> dict:
    """解析 LLM 返回的语义分析结果"""

def enhance_prompt_with_semantics(
    base_prompt: str, field_semantics: dict, field_ids: list[str]
) -> str:
    """将语义分析结果注入填写 prompt"""
```

#### Pipeline 集成（第2307-2321行）

```python
# ★ 改造一: Template semantic analysis (Phase 0.5)
self._template_semantics = {}
if fields or checkboxes or examples or labeled_fields:
    try:
        self._log(progress_cb, "正在分析模板语义规范...")
        sys_p, usr_p = build_template_semantic_analysis_prompt(
            fields, checkboxes, examples, labeled_fields, nested_tables
        )
        resp = self.llm(sys_p, usr_p)
        self._template_semantics = parse_template_semantic_analysis(resp)
        # ...
    except Exception as e:
        self._template_semantics = {}
```

#### `build_field_extraction_prompt` 更新

- 新增 `template_semantics` 参数
- 自动注入字段语义指导（类型、数据来源、填写提示）

### 5.5.4 语义分析输出格式

```json
{
  "template_overview": "模板整体结构说明",
  "sections": [{"name": "章节名", "purpose": "作用", "key_fields": [...]}],
  "field_semantics": {
    "f001": {
      "semantic_type": "事实型/计算型/判断型/选项型/描述型",
      "description": "字段语义描述",
      "data_source": "材料原文/计算推导/人工判断/选项勾选",
      "related_fields": ["相关字段ID"],
      "validation_hints": ["填写提示"]
    }
  },
  "checkbox_groups": {...},
  "writing_guidelines": [...]
}
```

---

## 五点六、改造四：生成时约束（已完成）

### 5.6.1 问题诊断

之前质量检查是"后处理修补"——LLM 生成后才发现模板泄漏、区间数字等问题，需要二次修复。

### 5.6.2 解决方案

改为"生成时约束"：
1. 在 Prompt 中注入约束规则
2. 生成后立即验证
3. 过滤无效值

### 5.6.3 完成内容

#### `form_filler.py` 新增常量和函数（第1056-1280行）

```python
# 字段验证规则（5种类型）
FIELD_VALIDATION_RULES = {
    "amount": {...},   # 金额
    "percent": {...},  # 百分比
    "date": {...},     # 日期
    "name": {...},     # 人名
    "company": {...},  # 公司
}

# 模板泄漏检测模式（10种）
TEMPLATE_LEAKAGE_PATTERNS = [
    (r"(?:张|李|王|陈|刘)XX", "虚假姓名占位符"),
    (r"\d{2,3}\s*-\s*\d{2,3}%\s*之间", "模板区间百分比"),
    # ... 等10种
]

def detect_field_type(context: str) -> str:
    """根据字段上下文推断类型"""

def validate_field_value(field_id, value, context) -> (bool, str):
    """验证字段值"""

def validate_batch_values(values, fields) -> dict:
    """批量验证"""

def filter_invalid_values(values, fields) -> dict:
    """过滤无效值"""

def build_constrained_prompt(base_system, base_user, field_types) -> (str, str):
    """添加生成时约束到 Prompt"""
```

#### Pipeline 集成

1. **Prompt 增强**：`build_field_extraction_prompt` 自动添加约束
2. **验证过滤**：应用字段值前调用 `filter_invalid_values`

### 5.6.4 约束规则

```
【生成约束·必须遵守】
1. 禁止使用模板示例值：
   - 金额区间如"1.4-1.5亿"、"65-70%之间"
   - 假姓名如"张XX"、"李XX"
   - 示例行业如"塑胶"、"注塑"、"模具"
2. 禁止保留占位符：
   - XX万元、XX年、XX公司等必须替换为真实数据
3. 数值格式规范：
   - 金额：纯数字+单位
   - 百分比：纯数字+%
   - 日期：YYYY年MM月DD日格式
```

---

## 六、Pipeline 流程详解

### 6.1 主流水线（`FormFillAgent.run`）

```
Phase 0: 模板指纹构建 + 材料加载 + KB 构建 + 财务事实库构建 + 企业画像锚点构建
    ↓
Phase 0.5: 模板语义分析 (★改造一新增)
    - 分析模板结构、字段语义类型、数据来源
    - 生成字段语义指导
    ↓
Phase 0b: 真值优先预填充
    - prefill_supply_chain_tables (上下游表格)
    - prefill_kb_structured_tables (关联企业/融资/研发表格)
    - prefill_shareholder_table (股东表格)
    - prefill_asset_table (资产表格)
    - prefill_bank_flow_table (银行流水表格)
    ↓
Phase 3: XX 字段批量提取（40字段/批次）
    ↓
Phase 4: 复选框勾选判断
    ↓
Phase 4b: 标签字段填写（label:blank 模式）
    - prefill_labeled_fields_from_kb (KB 确定性预填)
    - LLM 批量填写剩余字段
    ↓
Phase 5: 示例段落重写
    ↓
Phase 6: 嵌套表格填充
    ↓
Phase C: 残留字段处理
    ↓
Phase 7: 清理与后处理
    - 数字逗号修复
    - Markdown 语法清理
    ↓
Phase 8: 质量检查
```

### 6.2 关键数据结构

```python
@dataclass
class FieldSlot:
    """XX 占位符"""
    field_id: str           # f001, f002, ...
    context_before: str     # 前40字符
    context_after: str      # 后40字符
    xx_text: str            # "XX" 或 "XXXX"
    para_idx: int
    run_idx: int
    char_offset: int
    cell_path: tuple
    is_example: bool = False

@dataclass
class CheckboxSlot:
    """未勾选复选框"""
    cb_id: str
    option_text: str
    group_context: str
    # ...

@dataclass
class ExampleParagraph:
    """示例段落"""
    ex_id: str
    original_text: str
    section_context: str
    # ...

@dataclass
class LabeledField:
    """标签:空白 字段"""
    lf_id: str
    label: str              # 如 "客户名称"
    context_line: str
    # ...
```

---

## 七、已知问题与修复记录

### 7.1 BOM (U+FEFF) SyntaxError
- **现象**：`SyntaxError: invalid non-printable character U+FEFF`
- **原因**：UTF-8 BOM 字节
- **修复**：文件开头检查并移除 `\xef\xbb\xbf`

### 7.2 终端编码乱码
- **现象**：Windows 终端 `print()` 显示乱码
- **验证**：通过写入文件 `encoding='utf-8'` 后读取，确认数据正确
- **结论**：终端显示问题，不影响实际数据

### 7.3 股东表与关联企业表混淆
- **原因**：旧逻辑通过硬编码表格编号识别
- **修复**：`prefill_shareholder_table` 通过表头语义区分：股东表有"股东名称/出资比例"但无"成立时间/净利润/融资"

---

## 八、重要设计决策

### 8.1 Truth-First 原则
所有可确定性提取的事实，优先用正则/表格解析提取，不走 LLM。这避免了 LLM 幻觉问题。

### 8.2 企业画像锚点
`_build_company_profile()` 生成的锚点块会注入所有 LLM 调用，防止幻觉和模板交叉污染。

### 8.3 语义表头识别
通过 `_identify_table_type(header_row)` 识别表格类型，替代硬编码表格编号，使系统适应不同模板。

---

## 九、下一步工作

### 9.1 继续改造二

目标：修改 `_build_materials_text` 或新增维度检索方法

关键调用点：
- Phase 3: `build_field_extraction_prompt` 当前接收 `materials`（全量截断文本）
- Phase 4b: `build_labeled_field_prompt` 50K 截断
- Phase 5: `build_example_rewrite_prompt` 40K 截断
- Phase 6: `build_table_fill_prompt` 变量截断

每个应改为只接收与当前填写任务相关的 KB 维度。

### 9.2 后续改造

按依赖顺序：
1. 改造一：模板语义解析层（LLM 理解模板规范）
2. 改造三：语义块驱动填写引擎
3. 改造四：生成时约束

---

## 十、快速上手检查清单

- [ ] 阅读 `material_kb.py` 理解 KB 结构
- [ ] 阅读 `truth_fill.py` 理解预填充逻辑
- [ ] 阅读 `form_filler.py` 的 `run()` 方法理解 Pipeline
- [ ] 查看 `_build_materials_text` 理解当前截断策略
- [ ] 运行 `python app.py` 验证环境
- [ ] 检查 `outputs/` 目录的生成结果

---

## 十一、联系方式

如有问题，可参考：
- 项目目录：`C:\Users\xk-liuye\xwechat_files\wxid_1327183271712_1b91\msg\file\2026-04\credit_report_agent_work`
- 输出目录：`outputs/`
- 运行日志：`fill_run_output.txt`
