---
proposal: 对公回归验收方案
trigger: PHASE-2-GO-CORPORATE(业务方对公真材料包到位)
status: DRAFT · 等待材料到位启动
targets: Rule 16 跨模板稳定 + 对公长文 QC ≥ 88
date: 2026-04-19
---

# 对公回归验收方案

> 业务方提供对公真材料包后,Agent6 v16 CLI 一次跑完两个目标:
> (a) Rule 16 跨模板稳定性验证,(b) 对公长文 QC ≥ 88 的产出合规。
> 本文件定义"跑什么 / 要什么材料 / 怎么算 PASS"。材料到位后直接照表执行,
> 不再临时议。

---

## 1. 输入材料粒度(业务方需提供)

**硬要求**(缺一项即无法启动):

| # | 材料 | 格式 | 用途 | 备注 |
|---|---|---|---|---|
| 1 | 营业执照副本 | PDF | OCR → USC / 注册资本 / 实收资本 / 经营范围 / 法人 / 家庭住址 | enterprise_info 注入 |
| 2 | 财务报表(≥ 3 年) | XLSX / 标准三表 | financial_analyzer → 同比/较年初/三大活动现金流/趋势归因 | 对公 QC 财务深度 30 分权重的基础 |
| 3 | 企业基本介绍 | DOCX / TXT | KB 上下文:产品、行业地位、客户集中度、核心业务 | 经营情况分析 14 分权重 |

**强烈建议**(缺失直接影响 QC 上限):

| # | 材料 | 缺失时 QC 惩罚 |
|---|---|---|
| 4 | 征信报告(企业 + 实控人) | 征信分析维度最多得 2.2 / 14(对公 B 基线缺 ①对公贷款 / ④对公查询 / ⑥实控人逾期) |
| 5 | 现有担保情况(担保合同 / 抵质押清单) | 担保评估维度最多得 2.5 / 10(对公 B 基线证实) |
| 6 | 业务合同样本(在手订单 / 主要客户) | 经营分析 ⑤在手订单、③主要供应商子项扣分 |
| 7 | 申报方案书(额度 / 期限 / 品种 / 敞口) | 申报硬字段 2 分权重几乎全失(对公 B 基线 2.3/10) |

**样本覆盖需求**:
- **最少 2 个行业包**(如:制造业 + 服务业 或 商贸 + 建筑),否则 cross-industry 目标不成立。
- 每个包独立完整(不共用材料),且**模板形态差异化**(至少 1 个经纬/兴业类长文对公,1 个普惠/骨架类)。

---

## 2. 回归 Checklist(按表执行)

### 2.1 预检(材料到位后第 1 步)

```
# 每个行业包单独验证
py -c "from material_kb import build_material_kb; kb = build_material_kb('<material_dir>'); print('facts:', len(kb.facts), 'tables:', len(kb.tables))"
# 预期:facts ≥ 30 / tables ≥ 3,否则材料侧不齐,不要启动回归
```

### 2.2 Rule 16 稳定性回归(每份材料包跑 1 次)

```
py v16_pipeline.py --source samples/兴业资管_对公成稿B.docx --material <material_dir_1>
py v16_pipeline.py --source samples/经纬测绘_对公成稿A.docx --material <material_dir_2>
```

每份输出跑年份前缀审计(参照 Rule 16 决策档 §4 方法):

```
py -c "
from docx import Document; import re
d = Document('outputs/<docx>')
full = '\n'.join([p.text for p in d.paragraphs] +
                 [p.text for t in d.tables for r in t.rows for c in r.cells for p in c.paragraphs])
yp = re.compile(r'(20\d{2})\s*年?\s*(同比|环比|较年初|较上年末|较去年|较上年)')
dup = re.compile(r'(\d+(?:\.\d+)?万元|\d+\.\d+%)\s*[、,，]\s*\\1')
print('year-prefix:', len(yp.findall(full)), '  dup:', len(dup.findall(full)))
print('positive 对比短语:', len(re.findall(r'(同比|环比|较年初)', full)))
"
```

### 2.3 QC + Phase A runner(每份输出跑 1 次)

```
# docx 级 QC(自带 pipeline 产出)
cat outputs/<docx>_v16_qc.md

# runner 跨维度验收
py -m evaluation.runner --agent report --artifacts outputs/<docx>_v16.docx
```

### 2.4 基线对比

跟对公 B 已有 FAIL 基线(61.6,`outputs/兴业资管_对公成稿B_v16_qc.md`)按 9 维度逐项比对,记录每维 Δ。

---

## 3. PASS 判据矩阵

### 3.1 Rule 16 稳定目标(两个样本都要过)

| 指标 | 阈值 | 来源 |
|---|---|---|
| 年份前缀命中(`20XX年+同比/环比/较年初`) | **= 0** | 强制 |
| 重复值残留(`X、X` 对账句) | **= 0** | 强制 |
| 正向对比短语总数 | **≥ 15** | 确保表达力未被压制 |

**任一样本违反即 FAIL**,转 Rule 17 提案(同 Rule 16 决策档 §5 模板,新错形参数槽填写)。

### 3.2 对公长文 QC 目标(两个样本都要过)

| 指标 | 阈值 | 备注 |
|---|---|---|
| 总分 | **≥ 88** | 主 CLI 指定 |
| halluc_rate | **= 0** | 不可妥协 |
| 9 维度 FAIL 项 | **≤ 1** 且该项得分 ≥ 5 | 避免单维崩塌 |
| pending_tags | **≤ 60**(对公长文基线) | 比骨架型 91 低,因对公填写率高 |

### 3.3 Phase A runner 目标

| 指标 | 阈值 | 备注 |
|---|---|---|
| task_completion_rate | ≥ 0.98 | Phase A 硬指标 |
| template_leakage_rate | **≤ 0.15**(对公) | 对公比骨架型更严(骨架型 0.75 基线) |
| unfilled_marker_accuracy | ≥ 0.90 | 对公填写率高,标记应更准 |
| LLM-judge 指标 | Phase B 到位后补 | 本阶段不阻断 |

---

## 4. 未达标时的决策分支

| 失败形态 | 诊断路径 | 响应 |
|---|---|---|
| 年份前缀 > 0 | Rule 16 在对公 prompt batch 下失效(batch size / 上下文) | 拆细 prompt batch,或加 Rule 17 强化 |
| halluc_rate > 0 | 评估 LLM 输出 vs 材料 grounding | 起 RED-LINE-TRIGGERED,立 RFC |
| 9 维某项得分 < 5 | 核对该维对应的**材料**是否齐(参照 §1) | 缺材料→业务方补;材料齐→起 Rule 17/18 提案 |
| template_leakage > 0.15 | v16 classifier 未识别出对公高填写率 section | 回到 classifier 端重标,不改 generator |
| runner task_completion < 0.98 | 某个 artifact 未产出或 adapter 异常 | 查 `evaluation/results/<date>/` 错误栈,不改业务代码 |

---

## 5. 交付物清单(通过后)

1. `outputs/兴业资管_对公成稿B_v16.docx` + `_qc.md` + `_pending.json`(产出)
2. `outputs/经纬测绘_对公成稿A_v16.docx` + `_qc.md` + `_pending.json`(产出)
3. `evaluation/results/<date>/report_*.json`(runner 输出,× 2 份)
4. `docs/decisions/rule-16-cross-industry-evidence.md`(跨行业稳定性证据档,
   结构沿用 Rule 16 决策档 5 段式,§4 回归证据列 Δ 表)
5. (若 Rule 16 在对公仍稳定)`docs/decisions/` 保留 Rule 16 不增设新 Rule
6. (若暴露新错形)`docs/decisions/rule-17-*-治本.md` 草案(参数槽填好,等规则落)

Commit trailer 带 `Signal: READY-FOR-REVIEW`(逐份 commit,对公 B 一份、经纬 A 一份、
证据档一份,共 3 个 commit)。

---

## 6. 时间 / 成本预估

- 材料预检 + 环境就绪:15 分钟
- Rule 16 单样本跑 + 审计:每样本 10-15 分钟(含 LLM 调用)
- QC + runner:每样本 2 分钟
- 证据档撰写:30-40 分钟(5 段式结构已定)
- **总耗时(2 样本)**:约 1.5-2 小时

Token 预算:v16 pipeline 对公 B 基线约消耗 80K DeepSeek input / 15K output,两样本按 2x 估 ~ 200K,不超过单日额度。

---

## 7. 边界澄清

- **不做**:对公模板的分类器重训(属于 classifier 域,红区,需 RFC)。
- **不做**:material_kb 扩展新解析器(红区)。
- **不做**:`section_generator.py` 任何改动(红区)。
- **只做**:`v16_op_handlers.py` 的 prompt 层 Rule 新增(绿区)+ 运行 + 证据归档。

若回归过程中发现需要触达红区,立即起 RFC,不要就地改。
