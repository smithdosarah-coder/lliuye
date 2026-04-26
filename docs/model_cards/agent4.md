# Agent4 · 贷中预警助手 Model Card

**版本**：Agent4 v3.1（知识库驱动批量扫描 + 双路交叉）
**发布日期**：2026-04-26
**作者**：刘野（众安信科 AI 中台 / 乾策平台 X-Nexus）
**对应 DoD**：L3-11
**文档结构**：Google Research《Model Cards for Model Reporting》9 sections

---

## 1. Model Details（模型概况）

- **名称**：Agent4 · 贷中预警助手（In-Loan Alert · Cross-Source Scan）
- **版本**：v3.1
- **模型类型**：知识库驱动 + 规则引擎 + LLM 解读
  - **外部扫描域**：工商变更 / 司法诉讼 / 经营异常 / 行政处罚（实时 SearchProvider）
  - **内部交易域**：流水异动 / 大额支取 / 跨省高频（客户内部数据）
  - **双路交叉域**：外部 + 内部信号叠加 → 红 / 黄 / 绿分级
  - **处置建议域**：LLM 生成处置话术 + 升级路径
- **训练方式**：无微调
- **底座 LLM**：DeepSeek-Chat（境内 · 解读 + 话术）
- **所属**：众安信科 AI 中台 / 乾策平台

## 2. Intended Use（适用范围）

- **主用途**：基于在贷客户池 + 规则库 + 外部信号流 · 跨源交叉扫描 · 输出红 / 黄 / 绿分级客户榜单 + 处置建议
- **典型场景**：
  - 风险经理上传在贷客户池（含客户 ID + 工商信息 + 内部流水）
  - Agent4 跑 30 天 / 90 天扫描 → 生成红灯客户台账
  - 红灯客户给处置建议（电话回访 / 现场尽调 / 提前到期 / 收贷）
  - 导出预警台账 xlsx
  - 跨域协同：触发 Agent5 合规审查 / Agent3 重新评分
- **目标用户**：风险经理 · 资产保全
- **非适用**：
  - ❌ 不作单点查询（Agent4 是批量扫描型 · 单点查询走 Agent3 / Agent6）
  - ❌ 不作合规违规判定（Agent5 职责）
  - ❌ 不作授信决策（Agent3 职责）
- **定位**：copilot · 风险经理终审 + 处置决策

## 3. Factors（关键变量）

- **客户池规模**：100 / 1000 / 10000 家 · 影响扫描时长 + 误报率
- **外部信号源覆盖**：SearchProvider（Tavily / 企查查 / 公示系统）数据时效
- **内部数据完整度**：流水 / 征信 / 担保 字段缺失率 → 误报上升
- **规则库版本**：行内业务规则更新滞后 → 漏报 / 误报
- **触发时间窗**：30 / 60 / 90 天 → 信号灵敏度 vs 误报率 trade-off

## 4. Metrics（核心指标）

### 4.1 通用评估（`evaluation/agent4_alert.yaml`）

| 指标 | 目标 | Batch 2 baseline (2026-04-26) |
|---|---|---|
| `task_completion_rate` | ≥ 0.95 | PARTIAL（B1 fixture · 未消费 alert-pool · Q-030 预期漂移） |
| `evidence_rate` | ≥ 0.95 | 待 Phase 1 真数据校 |
| `hallucination_rate` | ≤ 0.02 | 待 Phase 1 真数据校 |
| `tool_success_rate` | ≥ 0.90 | 待 Phase 1 真数据校 |

### 4.2 领域评估（CLAUDE.md §5.2 + DoD §7.4）

| 指标 | 目标 | 状态 |
|---|---|---|
| 客户池扫描完成率（100 家全量跑通） | ≥ 0.95 | 待 Phase 1（alert-pool data-foundation Phase 2） |
| 红灯客户精准率（抽样 20 家人工复核） | ≥ 0.80 | 待 Phase 1 |
| 误报率（对标同盾诸葛 -45% 优化基线） | ≤ 0.15 | 待 Phase 1 |
| Top-5 reason_codes 字典 | ≥ 8 条 | ✅（`docs/reason_codes/agent4_alert.yaml` 8 条 · P3F 轨 5 落） |

## 5. Evaluation Data（评估数据）

- **Mock 样本**：`data/mock/agent4-alert-pool/`（在贷客户池 + 内部流水 + 外部信号 fixture · Batch 2 Phase 2 已落 commit `271eb6f`）
- **评估框架**：`evaluation/runner/` + `evaluation/runner/adapters/agent4_alert.py`
- **评估配置**：`evaluation/agent4_alert.yaml`
- **真 baseline**：待 Phase 1 alert-pool 接入

## 6. Training Data（训练数据）

无微调。

- **静态知识**：行内业务规则库 + `industry_cards/` 行业基准
- **prompt 模板**：`agent_alert/prompts.py`
- **动态经验**：`data/feedback/` 风险经理修改记录（红灯标 false positive 等）
- **reason_codes 字典**：`docs/reason_codes/agent4_alert.yaml`（8 条 · 4 外部 + 3 内部 + 1 双路 · P3F 轨 5 落）

## 7. Quantitative Analyses（定量分析）

- **当前状态**：B1 fixture 跑通 · 未消费 alert-pool（待 Phase 1 真数据接入）
- **8 reason_codes**：4 外部扫描（工商 / 诉讼 / 经营异常 / 行政处罚）+ 3 内部交易（流水异动 / 大额支取 / 跨省高频）+ 1 双路交叉
- **红 / 黄 / 绿分级**：基于 severity + decision_hint 二维标签

## 8. Ethical Considerations（伦理与局限）

### 8.1 已知局限

- **跨源时序对齐**：外部信号（实时）+ 内部信号（T+1）时间窗对齐误差 → 误报
- **小微客户数据稀疏**：内部交易少 → 仅靠外部信号 · 红灯精度边界
- **政策时效**：监管新规驱动的预警规则更新滞后
- **季节性**：经营异常的季节性波动可能产生误报（缓解：6 月基线 + 趋势）

### 8.2 伦理边界

- 输出**显式标"建议处置"** · 风险经理决策（DoD L2-10）
- **审批人 / 复核人字段**（L2-11）
- **审计日志** `data/audit/*.jsonl` 留痕（L2-12）
- **客户内部数据本地处理** · 仅外部 SearchProvider 检索词出境（L2-15）
- **copilot 期**：AI 红灯 → 风险经理人工复核 + 处置决策

### 8.3 合规声明

- 遵循《商业银行互联网贷款管理暂行办法》2025 自主风控 + 数安法 + 个保法
- 处置建议不替代银行内部资产保全 SOP

## 9. Caveats & Recommendations（注意事项与建议）

**使用前**：
1. 在贷客户池数据齐全（≥ 100 家 · 含内部流水 + 工商 + 征信）
2. SearchProvider 配置健康（Tavily / 企查查 key 有效 · 否则降级 Mock）
3. 行内业务规则库版本对齐当年最新

**使用中**：
1. 红灯客户先抽样 20 家人工复核 + 标注 false positive 回流
2. 误报率监控 · 超阈值触发规则库 review
3. 处置建议给风险经理 · 不直接执行收贷 / 提前到期

**不要做**：
- ❌ 把客户内部流水明文发境外
- ❌ 跳过人工复核直接执行处置
- ❌ 用 mock 数据当真红灯客户对外沟通

**版本管理**：v3.1 → v3.2（待）：Phase 1 alert-pool 真数据接入 + 真 baseline + reason_codes 派生（已落字典 · 后端派生待 Wave 3+）
