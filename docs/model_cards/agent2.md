# Agent2 · 风控规则助手 Model Card

**版本**：Agent2 v3.1（DSL 生成 + 回测）
**发布日期**：2026-04-26
**作者**：刘野（众安信科 AI 中台 / 乾策平台 X-Nexus）
**对应 DoD**：L3-11
**文档结构**：Google Research《Model Cards for Model Reporting》9 sections

---

## 1. Model Details（模型概况）

- **名称**：Agent2 · 风控规则助手（Risk Control · DSL Generation + Backtest）
- **版本**：v3.1
- **模型类型**：规则引擎 + LLM-judge 复合式
  - **DSL 生成域**：LLM 解析策略诉求 → 生成 DSL 规则
  - **回测域**：scikit-learn KS / PSI / 通过率指标计算
  - **指标分析域**：冠军 / 挑战者 A/B 对比
  - **基线对照**：`baseline_ruleset` 标准对照组（待 Wave 2 轨 8b 落）
  - **LLM-judge**：规则生成质量 LLM 评判（待 Wave 2 轨 8b 落）
- **训练方式**：无微调
- **底座 LLM**：DeepSeek-Chat（境内）
- **所属**：众安信科 AI 中台 / 乾策平台

## 2. Intended Use（适用范围）

- **主用途**：策略经理给出风控诉求（如"识别多头借贷高风险"）+ 历史样本 CSV → Agent2 生成 DSL 规则 + 回测 KS / 通过率 + 冠军挑战者对比
- **典型场景**：
  - 策略经理输入诉求文本 + 上传 7500 行历史贷款 csv（轨 8a 数据已落）
  - Agent2 生成 DSL 规则集 · 跑回测出 KS 0.30+ / PSI < 0.25 / 通过率
  - 冠军 vs 挑战者 A/B 对比 · 输出推荐方案
  - 导出回测报告 PDF + DSL JSON
- **目标用户**：策略经理 · 风险经理
- **非适用**：
  - ❌ 不作个案授信决策（Agent3 职责）
  - ❌ 不作贷中预警（Agent4 职责）
  - ❌ 不作合规违规判定（Agent5 职责）
- **定位**：copilot · DSL 规则需策略经理审核 + 灰度上线后才纳入生产规则集

## 3. Factors（关键变量）

- **样本质量**：历史贷款样本量 / 标签准确度（坏账定义） / 字段缺失率 → DSL 规则质量
- **诉求清晰度**：策略经理诉求文本明确度（目标坏账率 / 通过率约束）
- **DSL 表达力**：当前 DSL 支持算术 / 逻辑 / 时间窗 + 嵌套规则 · 不支持复杂图谱关联
- **LLM 解析**：诉求文本歧义 → 规则生成偏差（缓解：LLM-judge 待 8b 落）

## 4. Metrics（核心指标）

### 4.1 通用评估（`evaluation/agent2_riskctrl.yaml`）

| 指标 | 目标 | Batch 2 baseline (2026-04-26) |
|---|---|---|
| `task_completion_rate` | ≥ 0.95 | PARTIAL（5/10 完成） |
| `evidence_rate` | ≥ 0.95 | pending（5 pending 指标待 Wave 2 轨 8c 跑真 baseline） |
| `hallucination_rate` | ≤ 0.02 | pending |
| `tool_success_rate` | ≥ 0.90 | pending |

### 4.2 领域评估（CLAUDE.md §5.2 信贷专业）

| 指标 | 目标 | 状态 |
|---|---|---|
| 规则 DSL 生成可执行率 | ≥ 0.95 | pending（待 8b adapter 探针） |
| 回测 KS 指标计算与 scikit-learn 一致率 | ≥ 0.99 | pending（待 8c 真 baseline） |
| 冠军 / 挑战者 A/B 对比功能可用 | UI + API 齐 | 后端齐 · UI 在 Stage 4 frontend-integration |

## 5. Evaluation Data（评估数据）

- **Agent2 数据底座**：`data/mock/agent2-samples/loans.csv` 7500 行 / 29 列（P3F 轨 8a 落 · `merged_v2: true`）
- **字段字典**：`data/mock/agent2-samples/field_dictionary.md` 328 行
- **评估框架**：`evaluation/runner/` + `evaluation/runner/adapters/agent2_riskctrl.py`（Wave 2 轨 8b 后续完善）
- **真 baseline**：待 Wave 3 轨 8c

## 6. Training Data（训练数据）

无微调。

- **静态知识**：DSL grammar 定义 + 标准规则模板库（agent_riskctrl/templates/）
- **prompt 模板**：`agent_riskctrl/prompts.py`
- **基线对照**：`baseline_ruleset.json`（待 8b 落）
- **历史样本**：客户提供历史贷款 csv（实施期接入 · 不入 git）

## 7. Quantitative Analyses（定量分析）

- **当前状态**：5/10 评估指标完成 · 5 pending 待 Wave 2 轨 8b code-arch + Wave 3 轨 8c evaluation
- **DSL 规则模板**：基础规则集已稳定（>10 模板）· 复杂图谱关联待扩展
- **冠军挑战者**：后端 A/B 框架已齐 · UI 在轨 4 frontend-integration Stage 4 v2 hero 中

## 8. Ethical Considerations（伦理与局限）

### 8.1 已知局限

- **DSL 表达力边界**：复杂关联规则（图谱 / 多跳）当前不支持 · 需走人工补
- **样本偏差**：历史样本若有标签噪声 · DSL 规则会放大偏差 · 缓解：LLM-judge + 灰度
- **冷启动**：无历史样本时仅能生成模板规则 · 不出 KS
- **LLM 幻觉**：诉求歧义时 LLM 可能生成不合理规则 · 缓解：LLM-judge + 策略经理审核

### 8.2 伦理边界

- 输出**显式标"建议规则"** · 不直接进生产
- **策略经理灰度 + 审批** 必走 · DoD L2-10/L2-11
- **审计日志** `data/audit/*.jsonl` 留痕（L2-12）
- **核心风控模型不外包**（《商业银行互联网贷款管理暂行办法》2025）· Agent2 仅辅助生成 · 银行自主审核 + 上线决策

### 8.3 合规声明

- 遵循《商业银行互联网贷款管理暂行办法》2025 自主风控条款
- 遵循 CAC AI 治理框架 2.0 偏见测试条款（pending）

## 9. Caveats & Recommendations（注意事项与建议）

**使用前**：
1. 历史样本 csv ≥ 5000 行 · 标签字段定义清晰
2. 诉求文本明确（目标 / 约束 / 边界）
3. 灰度环境就绪

**使用中**：
1. DSL 规则灰度 ≥ 2 周 · 监控 KS / 通过率 / 误拒率
2. 冠军挑战者 A/B 至少 30 天再切换
3. 异常样本人工标注回流（数据飞轮）

**不要做**：
- ❌ DSL 规则未灰度直接上线
- ❌ 把客户 PII（身份证 / 银行账户明文）作为 DSL 入参
- ❌ 跳过策略经理审核

**版本管理**：v3.1 → v3.2（待）：Wave 2 轨 8b 后 + Wave 3 轨 8c 后 reason_codes 派生（pending_dsl_alignment 见 `docs/reason_codes/agent2_riskctrl.yaml`）
