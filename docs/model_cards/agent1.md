# Agent1 · 全渠道获客助手 Model Card

**版本**：Agent1 v4.0（信号驱动搜索 · 2026-04-16 + Batch 2 code-arch external_search）
**发布日期**：2026-04-26
**作者**：刘野（众安信科 AI 中台 / 乾策平台 X-Nexus）
**对应 DoD**：L3-11
**文档结构**：遵循 Google Research《Model Cards for Model Reporting》9 sections（2018）

---

## 1. Model Details（模型概况）

- **名称**：Agent1 · 全渠道获客助手（Channel · Look-alike Acquisition）
- **版本**：v4.0（信号驱动 + 数据飞轮 E2E）
- **模型类型**：复合式 AI Agent（非单一模型）
  - **信号搜索域**：`SearchProvider` 抽象（Mock / Tavily / 企查查实现）
  - **企业画像域**：知识库扫描 + 公开信息聚合
  - **匹配评分域**：lookalike 评分（多维度加权 · 行业 + 规模 + 信号一致度）
  - **产品推荐域**：客户产品目录匹配 + 营销倾向性融合
- **训练方式**：**无微调**（数据飞轮用 prompt few-shot 注入）
- **底座 LLM**：DeepSeek-Chat（境内 · 仅文案改写 + 推荐理由生成）
- **所属**：众安信科 AI 中台
- **联系**：liuye@zhongan.com

## 2. Intended Use（适用范围）

- **主用途**：基于客户经理给定锚点客户 + 知识库 · 召回相似企业候选清单 + 信号时间线 + 推荐产品
- **典型场景**：
  - 银行客户经理输入 1-3 家锚点客户 + 上传名录 / 政策 / 行业指引知识库
  - Agent1 召回 ≥ 30 家相似企业 + 每家 ≥ 2 种信号类型（CLAUDE.md §5.2 信号多样性硬指标）
  - 导出候选 xlsx + 推荐产品 + 匹配理由
  - 一键 handoff Agent6（生成报告） / Agent3（决策辅助）
- **目标用户**：客户经理 · 营销支持
- **非适用**：
  - ❌ 不作授信决策（Agent3 职责）
  - ❌ 不作贷中预警（Agent4 职责）
  - ❌ 不作合规检查（Agent5 职责）
- **定位**：copilot · 召回结果需客户经理终审 + 实地核查后才纳入营销名单

## 3. Factors（关键变量）

- **锚点客户质量**：锚点企业的工商完整度 / 行业代码精度 → 召回精度
- **知识库覆盖度**：名录 / 政策 / 行业指引 三类知识库齐全度
- **SearchProvider 可用性**：Tavily 无 key 时降级到 Mock fixture（DoD §0 容忍）· 企查查 API 限额
- **行业类型**：制造业 / 商贸 / 服务业 / 建筑 → 行业基准 `industry_cards/` 提供模板
- **数据时效**：工商档案 / 政策更新滞后 → 召回时效边界

## 4. Metrics（核心指标）

### 4.1 通用评估（`evaluation/agent1_channel.yaml`）

| 指标 | 目标 | Batch 2 baseline (2026-04-26) |
|---|---|---|
| `task_completion_rate` | ≥ 0.95 | PARTIAL（Tavily 无 key fallback Mock） |
| `evidence_rate` | ≥ 0.95 | 待 Wave 3+ 真数据校 |
| `hallucination_rate` | ≤ 0.02 | 待 Wave 3+ 真数据校 |
| `tool_success_rate` | ≥ 0.90 | 待 Wave 3+ 真数据校 |
| `precision@10` | ≥ 0.70 | stub（待 Phase 1 深柱真数据） |
| `recall@10` | ≥ 0.60 | stub |

### 4.2 领域评估（CLAUDE.md §5.2 信贷专业）

| 指标 | 目标 | 状态 |
|---|---|---|
| 信号多样性 ≥ 2 种 / 候选客户 | 100% | ✅ enforcement 已落 (commit `f3bd9b5` · 已合 main) |
| 候选企业召回率 | 知识库每 10 家锚点 ≥ 30 家新候选 | 待 Phase 1 真数据 |
| 幻觉企业（搜不到实体）占比 | ≤ 0.02 | 待 Phase 1 真数据 |

## 5. Evaluation Data（评估数据）

- **Mock baseline**：`data/mock/agent1-channel/` 锚点客户 + 候选 fixture（短期）
- **Phase 1 深柱**（待）：5 家真实银行客户经理已成交客户画像 + 营销倾向性文件 + 产品目录
- **评估框架**：`evaluation/runner/` + `evaluation/runner/adapters/agent1_channel.py`（Batch 2 evaluation 已重构）
- **评估配置**：`evaluation/agent1_channel.yaml`

## 6. Training Data（训练数据）

**Agent1 不做模型微调**：

- **静态知识**：`customer/` 锚点客户库 + `industry_cards/` 行业基准
- **prompt 模板**：`agent_channel/prompts.py`
- **动态经验**：`data/feedback/YYYY-MM-DD.jsonl` 客户经理修改记录（commit `c408b3a` 飞轮 E2E loop · 已合 main）
- **外部检索**：`shared/sources/impls/` SearchProvider 偏好链 (tavily / 企查查 / akshare / gov_cn)

无任何客户 PII 进入训练 / 推理派生物。

## 7. Quantitative Analyses（定量分析）

详见 `evaluation/results/` + `evaluation/baselines/2026-04-26-real-run.md` Agent1 段：
- 当前 stub 状态 · Mock provider 跑通端到端流水
- Batch 2 code-arch 引入 external_search 真 Tavily / 企查查 fallback
- Wave 3+ 接入真数据后 precision@10 + recall@10 实测

## 8. Ethical Considerations（伦理与局限）

### 8.1 已知局限

- **召回精度上限**：依赖 SearchProvider 数据质量 · 长尾行业召回率偏低
- **知识库时效**：政策 / 名录 30 天未更新可能漏召回
- **跨域企业识别**：跨省 / 跨国分支机构识别不全（依赖工商档案完整度）
- **小微企业稀疏**：非上市非纳税大户的小微数据稀疏 · 召回精度边界

### 8.2 伦理边界

- 输出**显式标"建议"**（DoD L2-10）· UI 醒目标识
- **审批人 / 复核人字段** + 电子签章位（L2-11 · 占位）
- **审计日志** `data/audit/*.jsonl` 记录每次调用（L2-12）
- **客户数据本地处理** · 仅 SearchProvider 检索词出境 · 详见 `docs/compliance/data-localization.md`

### 8.3 合规声明

- 遵循《助贷新规》2025-10 + CAC AI 治理框架 2.0 + 数据安全法 + 个保法
- 公开信息检索（工商 / 司法 / 招聘 / 媒体）走境内 endpoint
- 客户经理终审 + 实地核查后才纳入正式营销名单（copilot 边界）

## 9. Caveats & Recommendations（注意事项与建议）

**使用前**：
1. 锚点客户至少 1-3 家 · 知识库至少 1 个名录 + 1 个行业指引
2. SearchProvider 配置健康（`TAVILY_API_KEY` 有效 · 否则降级 Mock）
3. 浏览器 Chrome 111+

**使用中**：
1. 召回结果需客户经理终审 · 实地或电话核查
2. 信号多样性 < 2 种的候选自动 SKIP（Agent1 内置硬指标）
3. 跨 Agent handoff 走 EnterpriseProfile schema · 不复制原 PDF

**不要做**：
- ❌ 把锚点客户 PII（手机 / 身份证 / 银行账户）传 Tavily
- ❌ 用 Mock fixture 当真召回结果对外营销
- ❌ 跳过信号多样性 ≥ 2 检查

**版本管理**：v4.0 → v4.1（待）：Phase 1 深柱真数据 baseline 后升级 · 触发 reason_codes 派生（pending_implementation 见 `docs/reason_codes/agent1_channel.yaml`）
