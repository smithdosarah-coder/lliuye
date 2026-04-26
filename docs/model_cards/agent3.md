# Agent3 · 授信决策助手 Model Card

**版本**：Agent3 v3.1（对公 / 普惠 / 对私三板块 + Top-5 reason_codes）
**发布日期**：2026-04-26
**作者**：刘野（众安信科 AI 中台 / 乾策平台 X-Nexus）
**对应 DoD**：L3-11
**文档结构**：Google Research《Model Cards for Model Reporting》9 sections

---

## 1. Model Details（模型概况）

- **名称**：Agent3 · 授信决策助手（Credit Decision Assistant）
- **版本**：v3.1
- **模型类型**：复合式（确定性计算 + LLM 生成 + 规则引擎）
  - **画像消费域**：Agent6 ReportJSON + EnterpriseProfile handoff 接入
  - **评分计算域**：四维评分（财务 / 行业 / 经营 / 担保）· 对公 vs 普惠 vs 对私 双模型
  - **红线检查域**：硬红线规则（基于 `agent_credit/redlines.yaml`）
  - **案例召回域**：同业案例参考（`agent_credit/cases/`）
  - **决策书生成**：本地 python-docx 渲染（`agent_credit/decision_letter_docx.py` · 旧名 docx_export · 已 rename per Q-033 follow-up）
- **训练方式**：无微调
- **底座 LLM**：DeepSeek-Chat（境内）
- **所属**：众安信科 AI 中台

## 2. Intended Use（适用范围）

- **主用途**：基于 Agent6 ReportJSON + 客户材料 → 四维评分 + 决策建议（批准 / 有条件 / 拒绝）+ Top-5 reason_codes（FCRA AAN 对标）+ 红线判定
- **典型场景**：
  - 审贷员接 Agent6 报告 + EnterpriseProfile handoff（一键预填）
  - Agent3 跑四维评分 · 给额度 / 期限 / 利率建议
  - 输出 docx 决策意见书（含雷达图 + reason_codes Top-5 + 红线明细）
  - L1-11 跨 Agent 联动 + L1-3 RiskRadar 雷达可视化（待 Stage 2 整合）
  - L1-4 docx 导出（已落 commit `4107b16`）
- **目标用户**：审贷员 · 审贷会 · 风险经理
- **非适用**：
  - ❌ 不写报告（Agent6 职责）
  - ❌ 不作贷中预警（Agent4 职责）
  - ❌ 不替代审贷会终审决策（监管 copilot 边界）
- **定位**：copilot · 审贷员终审

## 3. Factors（关键变量）

- **Agent6 报告完整度**：财务比率 / 经营情况 / 担保信息齐全度 → 四维评分质量
- **业务板块**：对公 / 普惠 / 对私 三套独立模型（参数 + 红线规则不同）
- **行业类型**：行业卡片 `industry_cards/` 提供基准 · 长尾行业偏差大
- **担保数据稀疏**：抵押物估值滞后 / 担保人征信缺失 → 担保维度评分边界
- **红线规则版本**：监管新规 → 红线 yaml 更新滞后

## 4. Metrics（核心指标）

### 4.1 通用评估（`evaluation/agent3_credit.yaml`）

| 指标 | 目标 | Wave 1 baseline (Batch 2 + agent3 unfreeze 后) |
|---|---|---|
| `task_completion_rate` | ≥ 0.95 | ✅ PASS |
| `evidence_rate` | ≥ 0.95 | ✅ PASS |
| `hallucination_rate` | ≤ 0.02 | ✅ PASS |
| `tool_success_rate` | ≥ 0.90 | ✅ PASS |

### 4.2 领域评估（CLAUDE.md §5.2 + DoD §7.3）

| 指标 | 目标 | 状态 |
|---|---|---|
| 四维评分一致率（复测稳定性） | ≥ 0.95 | ✅ PASS |
| Top-5 标准拒贷原因码覆盖率 | 100% | ✅ PASS（agent3-corporate.yaml 15 条 + agent3-retail.yaml 16 条 · 共 31 条） |
| 红线触发准确率 vs 人工裁定 | ≥ 0.99 | ✅ PASS |
| Agent6 → Agent3 handoff 一键预填 | 通 | ✅（commit `8f1a35c` L1-11） |

## 5. Evaluation Data（评估数据）

- **Mock 样本**：`data/mock/agent3-samples/`（对公 + 普惠 + 对私 三板块 fixture）
- **真 baseline**：`evaluation/baselines/2026-04-26-real-run.md` Agent3 段（🟢 PASS）
- **评估框架**：`evaluation/runner/` + `evaluation/runner/adapters/agent3_credit.py`（Batch 2 重写）
- **评估配置**：`evaluation/agent3_credit.yaml`

## 6. Training Data（训练数据）

无微调。

- **静态知识**：`agent_credit/scoring_models/` 双模型参数 + `agent_credit/redlines.yaml` 红线规则 + `agent_credit/cases/` 同业案例库
- **prompt 模板**：`agent_credit/prompts.py`
- **动态经验**：`data/feedback/YYYY-MM-DD.jsonl` 审贷员修改记录
- **reason_codes 字典**：`docs/reason_codes/agent3-corporate.yaml` + `docs/reason_codes/agent3-retail.yaml`（共 31 条 · 对标 FCRA AAN）

## 7. Quantitative Analyses（定量分析）

详见 `evaluation/baselines/2026-04-26-real-run.md`：

- **Wave 1 后**：通用 + 领域指标全 PASS
- **Top-5 reason_codes**：corporate 15 条 + retail 16 条 · 100% 覆盖红 / 黄 / 绿 三 severity
- **四维评分**：财务 / 行业 / 经营 / 担保 各权重 25% · 对公 / 普惠 / 对私 不同
- **红线规则**：硬红线 5 条 / 软告警 5 条 · 各 segment 不同

## 8. Ethical Considerations（伦理与局限）

### 8.1 已知局限

- **行业卡片覆盖度**：当前覆盖 30+ 主流行业 · 长尾（如新兴产业 / 跨境业务）覆盖不全
- **担保维度数据稀疏**：抵押物估值依赖外部评估机构 · 时效与精度边界
- **小微企业**：财务数据完整度通常低 · 评分置信度边界
- **政策更新滞后**：红线规则 yaml 需人工 maintain · 监管新规出台 1-2 周内补齐

### 8.2 伦理边界

- 输出**显式标"建议"**（DoD L2-10）· UI 醒目标识
- **审批人 / 复核人字段** + 电子签章位（L2-11）
- **审计日志** `data/audit/*.jsonl` 留痕（L2-12）
- **决策意见书 docx 本地渲染** · 不走境外 API（L2-15）
- **copilot 期**：AI 建议 → 审贷员 / 审贷会终审

### 8.3 合规声明

- 遵循《商业银行互联网贷款管理暂行办法》2025 + 助贷新规 + CAC AI 治理 2.0 + 数安法 + 个保法
- Top-5 reason_codes 对标 FCRA AAN 国际标准
- 决策证据链 100% 可追溯（30 秒内追到原材料）

## 9. Caveats & Recommendations（注意事项与建议）

**使用前**：
1. 必接 Agent6 ReportJSON（不接受裸输入）
2. 业务板块明确（corporate / inclusive / retail 三选一）
3. 红线规则 yaml 已对齐当年监管最新

**使用中**：
1. 四维评分仅参考 · 审贷员看雷达图 + reason_codes 终审
2. 红线触发硬阻断 · 不绕过
3. 决策书 docx 本地渲染 · 不上传境外
4. 修改回流 `/api/feedback`（数据飞轮）

**不要做**：
- ❌ 跳过审贷员终审直接出账
- ❌ 用 Agent3 做合规违规判定（Agent5 职责）
- ❌ 把决策书原文 PDF 传境外 LLM（合规红线）

**版本管理**：v3.1 → v3.2（待）：行业卡片扩展 / 红线 yaml 监管新规同步 / RiskRadar 雷达图前端 v2 hero（Stage 4）
