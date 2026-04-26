# Agent5 · 合规助手 Model Card

**版本**：Agent5 v3.1（政策事件驱动）
**发布日期**：2026-04-26
**作者**：刘野（众安信科 AI 中台 / 乾策平台 X-Nexus）
**对应 DoD**：L3-11
**文档结构**：Google Research《Model Cards for Model Reporting》9 sections

---

## 1. Model Details（模型概况）

- **名称**：Agent5 · 合规助手（Compliance · Policy-Event-Driven）
- **版本**：v3.1
- **模型类型**：政策解析 + 矩阵 cross check + LLM 解读
  - **政策解析域**：LLM 解析新政策条款 → 结构化条款图谱
  - **业务矩阵域**：行内业务制度库（SOP / 准入 / KYC / 风偏 / 审查清单）建模
  - **违规判定域**：政策 × 业务规则交叉 → 冲突点识别
  - **缺陷分类域**：违规等级（硬违规 / 流程缺陷）+ 整改建议生成
- **训练方式**：无微调
- **底座 LLM**：DeepSeek-Chat（境内 · 政策语义解析 + 整改话术）
- **触发模型**：**政策发布事件驱动**（vs 定期巡检 · 见 Q-029 决策档锚定）
- **所属**：众安信科 AI 中台 / 乾策平台

## 2. Intended Use（适用范围）

- **主用途**：监管发布新政策时 → Agent5 自动 cross check 行内业务制度 → 输出违规冲突点明细 + 整改建议
- **典型场景**：
  - 央行 / 金管总局 / CAC 发布新规（如助贷新规 2025-10）
  - Agent5 自动抓取政策原文（实时 SearchProvider）+ 解析条款
  - 与行内业务制度库 cross check · 识别冲突点（红 / 黄 / 绿）
  - 输出合规检查报告 docx + Top-N reason_codes + 整改建议
  - 触发跨域协同：Agent3 重新评分 / Agent4 红灯扫描
- **目标用户**：合规官 · 内审员 · 风险经理
- **非适用**：
  - ❌ 不作单点合规查询（Agent5 是政策事件驱动）
  - ❌ 不作授信决策（Agent3 职责）
  - ❌ 不作贷中预警（Agent4 职责 · 但 Agent4 / 5 共享 `shared/kb_scan/` 矩阵扫描底座）
- **定位**：copilot · 合规官终审 + 上报合规委员会

## 3. Factors（关键变量）

- **政策原文质量**：监管发布的政策条款明确度 · LLM 解析准确度
- **业务制度库齐全度**：SOP / 准入 / KYC / 风偏 / 审查清单 5 类覆盖
- **政策时效**：新政策发布到 Agent5 处理的延迟（通常 < 24 小时）
- **跨条款关联**：单政策多条款 / 多政策叠加冲突识别难度
- **行业自律 vs 监管硬性**：自律建议 vs 监管硬规分级判定

## 4. Metrics（核心指标）

### 4.1 通用评估（`evaluation/agent5_compliance.yaml`）

| 指标 | 目标 | Batch 2 baseline (2026-04-26) |
|---|---|---|
| `task_completion_rate` | ≥ 0.95 | PARTIAL（conflict 跑通 · Tavily 降级） |
| `evidence_rate` | ≥ 0.95 | 待 Wave 3+ 真政策真数据校 |
| `hallucination_rate` | ≤ 0.02 | 待 Wave 3+ 真政策真数据校 |
| `tool_success_rate` | ≥ 0.90 | 待 Wave 3+ 真政策真数据校 |

### 4.2 领域评估（CLAUDE.md §5.2 + DoD §7.5）

| 指标 | 目标 | 状态 |
|---|---|---|
| 政策条款解析准确率（vs 人工标注） | ≥ 0.95 | 待 Wave 3+ |
| 违规冲突点召回率 | ≥ 0.90 | 待 Wave 3+ |
| 条款引用错误率 | ≤ 0.01 | 待 Wave 3+ |
| Top-N reason_codes 字典 | ≥ 8 条 | ✅（`docs/reason_codes/agent5_compliance.yaml` 8 条 · P3F 轨 5 落） |

## 5. Evaluation Data（评估数据）

- **Mock 样本**：`data/mock/agent5-policy/`（新政策 fixture + 行内业务制度库 fixture）
- **评估框架**：`evaluation/runner/` + `evaluation/runner/adapters/agent5_compliance.py`（Batch 2 已重构）
- **评估配置**：`evaluation/agent5_compliance.yaml`
- **真 baseline**：待 Wave 3+ 真政策接入（实时 SearchProvider 抓监管发布的真新规）

## 6. Training Data（训练数据）

无微调。

- **静态知识**：行内业务制度库（SOP / 准入 / KYC / 风偏 / 审查清单 共 5 类 · 客户实施期接入）
- **prompt 模板**：`agent_compliance/prompts.py`
- **政策原文库**：`shared/sources/impls/{gov_cn,pbc_gov,flk_npc}.py` 实时抓取（金管总局 / 央行 / 网信办 / 全国人大公开发布）
- **reason_codes 字典**：`docs/reason_codes/agent5_compliance.yaml`（8 条 · 政策解析 / 业务矩阵 / 违规 / 缺陷 4 域 · P3F 轨 5 落）

## 7. Quantitative Analyses（定量分析）

- **当前状态**：conflict 框架跑通 · Tavily 降级 fallback Mock（待真 LLM key + 真政策接入）
- **8 reason_codes**：3 政策解析冲突 + 3 业务矩阵违规 + 1 违规判定 + 1 缺陷分类
- **政策事件驱动 vs 定期巡检**：Q-029 决策档明确 · 触发源是政策变更非时间触发

## 8. Ethical Considerations（伦理与局限）

### 8.1 已知局限

- **政策语义解析**：长文本 / 多条款关联政策 · LLM 解析准确度边界
- **跨条款冲突识别**：单政策多条款 + 多政策叠加 → 复合冲突识别难度
- **业务制度库时效**：行内 SOP 更新滞后 · 误报上升
- **行业自律新规**：自律建议 vs 监管硬规分级 · LLM 判定置信度边界
- **跨地域监管差异**：不同省份金融监管口径细微差异 · 缓解：客户合规部协同审

### 8.2 伦理边界

- 输出**显式标"建议合规整改"** · 合规官决策（DoD L2-10）
- **合规官 / 内审员审批字段**（L2-11）
- **审计日志** `data/audit/*.jsonl` 留痕（L2-12）
- **政策原文 + 行内制度库 本地处理** · 仅政策抓取 SearchProvider 检索词出境
- **copilot 期**：AI 冲突点识别 → 合规官人工复核 + 整改决策

### 8.3 合规声明

- 遵循 CAC AI 治理框架 2.0 强制条款（可解释性 / 偏见测试 / 内嵌安全 / 信息披露）
- 监管引用 100% 真实条款（不臆造）· 字典 reference_policy 字段必填
- 整改建议不替代合规委员会终审 + 监管报告流程

## 9. Caveats & Recommendations（注意事项与建议）

**使用前**：
1. 行内业务制度库已接入（5 类齐全）
2. SearchProvider 配置健康（gov_cn / pbc_gov / flk_npc 实时 endpoint 可用）
3. 合规委员会审批流程明确

**使用中**：
1. 红色冲突点 24 小时内合规官审 · 黄色 5 工作日 · 绿色合规通过
2. 整改建议需合规委员会审议 + 上报董事会（视严重度）
3. 政策原文链接 + 行内 SOP 章节 必须双向 ref · 保留 audit trail
4. 修改回流 `/api/feedback`（数据飞轮 · 误报反馈）

**不要做**：
- ❌ 跳过合规委员会审议直接整改 SOP
- ❌ 用 Mock 政策当真政策对外发布合规报告
- ❌ 把行内 SOP 全文传境外 LLM（合规红线）

**版本管理**：v3.1 → v3.2（待）：Wave 3+ 真政策接入 + reason_codes 后端派生（字典已落 · 派生待 Wave 3+）
