# Agent6 Phase 2 · 模板覆盖度与业务方材料清单

**版本**：v1.0
**更新日期**：2026-04-19
**对应 DoD**：L3-12（模板覆盖度，≥2 银行模板）+ A-018（`pending_business_data` 追认）
**对应 Task**：Phase 2 Task C(CONDITIONAL 解封文档)
**模板识别**：`agent_report/template_adapter.py`

---

## 1. 5 模板结构化覆盖表

| # | 文件名 | scenario | 业务线 | 字段密度 | QC 下限 | 状态 | 真材料状态 |
|---|---|---|---|---|---|---|---|
| 1 | `普惠申报书_骨架型.docx` | inclusive_skeleton | inclusive | skeleton(460+ 字段) | 88.5 | ✅ Phase A 基线 | ✅ 已有(`94c04f5` tip) |
| 2 | `兴业资管_对公成稿B.docx` | corporate_long_form | corporate | narrative | 88.0 | ⏳ 等真材料 | ⏳ pending_business_data |
| 3 | `经纬测绘_对公成稿A.docx` | corporate_long_form | corporate | narrative | 88.0 | ⏳ 等真材料 | ⏳ pending_business_data |
| 4 | `科创贷申报书_模板.docx` | tech_credit | corporate | skeleton(脱敏构造) | 86.0 | ⏳ Phase 2 Task C 新增 | ⏳ pending_business_data |
| 5 | `小微对私授信申报书_模板.docx` | micro_personal | personal | skeleton(脱敏构造) | 82.0 | ⏳ Phase 2 Task C 新增 | ⏳ pending_business_data |

## 2. 每模板 pending_business_data 说明

### 2.1 inclusive_skeleton(普惠申报书_骨架型)

- **状态**:✅ 已有真材料并跑通 Phase A 基线
- **基线 commit**:`94c04f5`
- **关键指标**:`unfilled_marker_accuracy=1.0000`(运行时);Rule 17 维度模型卡 §4.2 记载真实 gap 0.625(等业务方启动外部触发)
- **业务方材料清单**:无需补充

### 2.2 corporate_long_form(兴业资管 + 经纬测绘)

- **状态**:⏳ 模板成稿已有,等真材料包做端到端长文 QC 验证
- **缺失**:对应客户的真实营业执照 + 3 年财报 + 征信报告 + 业务介绍 + 担保情况 + 申报方案书
- **业务方材料清单**(签订 NDA 后):
  - 营业执照 PDF
  - 2022/2023/2024 财务报表 xlsx(资产负债表 + 利润表 + 现金流量表 + 附注)
  - 企业征信报告 PDF
  - 业务介绍 DOCX(主营业务 + 客户/供应商前 5 + 在手订单)
  - 担保情况说明
  - 申报方案书(初稿,可缺,Agent6 出全稿)
- **触发信号**:`PHASE-2-GO-CORPORATE`

### 2.3 tech_credit(科创贷申报书_模板)

- **状态**:⏳ Phase 2 Task C 新增脱敏结构,模板字段就位,等真材料
- **缺失**:科创企业的研发投入明细 + 高新认定证书 + 知识产权清单 + 财务数据
- **业务方材料清单**:
  - 高新技术企业证书复印件 / 科技型中小企业入库证明
  - 近三年研发费用明细表(可来自审计报告附注或独立专项)
  - 研发人员花名册(脱敏:仅汇总人数 + 学历结构)
  - 发明专利 / 实用新型 / 软著清单
  - 营业执照 + 3 年财报 + 征信报告 + 业务介绍
  - 申报方案书(可缺)
- **触发信号**:`PHASE-2-GO-TECH`(待业务方提供)

### 2.4 micro_personal(小微对私授信申报书_模板)

- **状态**:⏳ Phase 2 Task C 新增脱敏结构,模板字段就位,等真材料
- **缺失**:申请人身份资料 + 个人征信 + 收入证明 + 经营资料(若有)
- **数据分级提示**:本模板涉及**核心**级别个人数据(身份证号 / 收入 / 征信明细),按 `docs/compliance/data-grading.md` 严禁出境,仅本地处理
- **业务方材料清单**:
  - 申请人身份证(脱敏:仅地址前缀 + 出生年月)
  - 个人征信报告 PDF(脱敏)
  - 工资流水 / 银行流水(近 12 个月)
  - 婚姻状况证明(若涉及共同申请人)
  - 经营实体材料(若个体工商户:营业执照 + 经营流水)
  - 担保资料(若有抵押 / 第三方保证)
- **触发信号**:`PHASE-2-GO-PERSONAL`(待业务方提供)

## 3. 与 A-018 / A-013 的关系

A-018 追认 `pending_business_data` yaml 扩展(`evaluation/agent6_report.yaml#coverage_by_template.per_template_baseline_runs.pending_business_data: true`)。本字段与 A-013 `baseline.pending_metrics` **正交**:

- **`pending_metrics`**:metric 级豁免,声明哪些指标本期不跑(端到端 LLM 跑批未启动)
- **`pending_business_data`**:template 级数据前提豁免,声明哪些模板缺真材料

两者并存,共同支撑 Phase 2→3 渐进式落地策略。

## 4. CLAUDE.md 合规对齐

- §3.1 确定性 vs 概率性:脱敏模板跑 LLM 属于"无锚的概率任务",必须 pending,不硬跑
- §5 评估框架:先建 rubric(本文档 §1 的 QC 下限)→ 跑基线(待真材料)→ 找最大 gap → 改代码,顺序不可乱
- §12 开发约束:字段填不了 → 标"未能自动填写",绝不编;同理,模板没真材料 → 标 pending,不编假数据

## 5. Phase 3 解锁路径

```
业务方材料到位 → worker 收信号 PHASE-2-GO-{TECH|CORPORATE|PERSONAL}
   ↓
跑 py -m evaluation.runner --agent report
   ↓
把跑通的 metric 从 pending_metrics 移到 baseline.result
   ↓
更新本文档对应模板状态:⏳ → ✅
   ↓
emit Signal: AGENT6-PHASE-3-METRICS-RESOLVED-{scenario}
```

## 6. yaml schema 变更纪律(A-018 事后约束)

> **下次 yaml schema 动手前必须走 Q-NNN(即便不在红区也属黄区)。**

本文档及其对应 yaml 字段(`pending_business_data` / `coverage_by_template`)是 A-018 事后追认的产物。后续若需新增 yaml schema 字段(如 `pending_external_review` / `pending_compliance_audit` 等),必须先发 Q-NNN 走 mesh 协调,不可径自落地。

## 7. 引用

- `agent_report/template_adapter.py` 模板识别 + 元信息归一
- `evaluation/agent6_report.yaml#coverage_by_template` yaml 契约
- `docs/handoff/decisions-log.md#A-018` 追认决策
- `docs/progress/agent6-phase-2-pending.md` Task D 配套文档
- `docs/compliance/data-grading.md` 个人数据核心级别约束
- 模型卡 §4.2 Rule 17 unfilled_marker 0.625 真实 gap 锚点
