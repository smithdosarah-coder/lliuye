# Agent6 · 信贷报告助手 Model Card

**版本**：Agent6 v7.23 (+ v16 章节生成管线)
**发布日期**：2026-04-19
**作者**：刘野（众安信科 AI 中台 / 乾策平台 X-Nexus）
**对应 DoD**：L3-11
**文档结构**：遵循 Google Research《Model Cards for Model Reporting》9 sections（2018）。

---

## 1. Model Details（模型概况）

- **名称**：Agent6 · 信贷报告助手（Credit Report Assistant）
- **版本**：v7.23（生产） + v16（章节改写管线，quality / corporate 线）
- **模型类型**：复合式 AI Agent（非单一模型）
  - **确定性计算层**：`financial_analyzer.py`（Python 规则引擎）
  - **抽取层**：`material_kb.py` + `truth_fill.py`（结构化预填）
  - **生成层**：DeepSeek-Chat（境内）经 `section_generator.py` 三阶段 Evidence-First 协议
  - **质量闸门**：`quality_scorer.py` + QC Blocker
- **训练方式**：**无微调**。数据飞轮用 prompt few-shot 注入替代 SFT（CLAUDE.md §6）
- **底座 LLM**：DeepSeek-Chat（境内，温度 0.3，max_tokens 8192）
- **所属**：众安信科 AI 中台
- **联系**：liuye@zhongan.com

## 2. Intended Use（适用范围）

- **主用途**：辅助银行客户经理 / 审贷员生成企业 / 个人信贷申报书填充与章节改写
- **典型场景**：
  - 上传企业营业执照 + 3 年财报 + 征信报告 + 业务介绍 → 自动填 460 项 + 章节叙事改写 + 导出 docx
  - 普惠小微授信（对私板块）模板
  - 对公授信申报模板（长文叙事版本）
- **目标用户**：
  - 客户经理：发起报告生成、补全外因问题
  - 审贷员：复核填写结果、提交修改反馈
  - 合规官：调阅审计日志、复核证据链
- **非适用**：
  - ❌ 不作最终授信决策（Agent3 职责；Agent6 只出报告）
  - ❌ 不作合规违规判定（Agent5 职责）
  - ❌ 不作预警扫描（Agent4 职责）
- **定位**：copilot（辅助），非 autopilot（不替代人工审批）——依据金管总局 2025 表态"AI 现阶段只能辅助，不能替代"。

## 3. Factors（关键变量）

影响输出质量的因素：

- **材料齐全度**：营业执照 / 3 年财报 / 征信 / 业务介绍 / 担保情况 / 申报方案书（缺任一项 QC 上限下降，详见 `docs/proposals/corporate-regression-acceptance.md`）
- **模板形态**：骨架型（普惠，460 项字段）vs 长文型（对公，章节叙事）
- **行业类型**：制造业 / 商贸 / 服务业 / 建筑业 —— 行业卡片 `industry_cards/` 提供模板
- **业务线分流**：`business_line=corporate/inclusive/reserved` 决定走 V15 narrative 管线或 V14 骨架管线
- **LLM 可用性**：`DEEPSEEK_API_KEY` 缺失 → 降级返回空串，下游按"未能自动填写"走 QC

## 4. Metrics（核心指标）

### 4.1 通用评估（`evaluation/agent6_report.yaml`）

| 指标 | 目标 | v7.23 基线 |
|---|---|---|
| `field_completeness` 字段填充率 | ≥ 0.93 | 0.935（460 / 492） |
| `evidence_rate` 证据溯源率 | ≥ 0.95 | ✅ |
| `hallucination_rate` 幻觉检出率 | ≤ 0.02 | ✅ |
| `tool_success_rate` 工具调用正确率 | ≥ 0.90 | ✅ |
| `task_completion_rate` 任务完成度 | ≥ 0.95 | 1.0000（Phase A tip `94c04f5`） |

### 4.2 Phase A 骨架型基线（2026-04-19，tip `94c04f5`）

| 指标 | 值 | 状态 |
|---|---|---|
| `task_completion_rate` | 1.0000 | ✅ |
| `template_leakage_rate` | 0.75–0.875 | 骨架复用基线（预期内） |
| `unfilled_marker_accuracy` | 0.6250 | ❌ Rule 17 真实 gap（见 §6） |
| 骨架型回归 QC 总分 | 90.0 | ✅ PASS（基线 88.5 → +1.5） |
| Rule 16 年份前缀命中 | 0 | ✅ 治本已落（commit `bd34288`） |

### 4.3 领域评估（CLAUDE.md §5.2）

- 财务比率计算正确率（vs Python 确定性结果）≥ 0.99 — 依靠 `financial_analyzer.py`
- 红线判定准确率 — 走 `quality_check.py` 规则库
- 合规术语规范率 — 由 `quality_scorer.py` 9 维度之一评估
- 信号多样性（Agent6 不涉及；Agent1 才用）

## 5. Evaluation Data（评估数据）

- **Phase A 骨架型样本**：`samples/` 下普惠授信申报书模板 docx（460 项字段的骨架型回归）
- **Phase B 对公素材**（等业务方提供）：兴业 / 经纬测绘 长文对公成稿 + 真实材料包，详见 `docs/proposals/corporate-regression-acceptance.md`
- **评估框架**：`evaluation/runner/` + `evaluation/runner/adapters/agent6_report.py`
- **评估配置**：`evaluation/agent6_report.yaml`

## 6. Training Data（训练数据）

**Agent6 不做模型微调**。所有"学习"通过 prompt few-shot 注入实现：

- **静态知识**：`customer/` + `demo_data/` + `industry_cards/` + 内部规则库
- **prompt 模板**：`prompts.py`
- **动态经验**：`data/feedback/YYYY-MM-DD.jsonl`（审贷员修改记录） → 提取 few-shot 注入 prompts（第 4 环，手工 + 离线脚本）
- **外部检索**：`shared/sources/impls/` 下 6 个源按偏好链调用

无任何个人数据、客户真实数据进入训练/推理派生物（LLM 只看摘要，不看原文 PDF / 全表格式）。

## 7. Quantitative Analyses（定量分析）

详见 `evaluation/results/` 结果 YAML（按日期归档）：

- Phase A runner 跨 worktree 验证通过（2026-04-19），基线锚点 `94c04f5`
- QC 9 维度评分基线（`quality_scorer.py`）：骨架型 90.0 PASS
- Rule 16 年份前缀治本后骨架型命中归零，QC +1.5

## 8. Ethical Considerations（伦理与局限）

### 8.1 已知局限

- **Rule 17 gap**：`unfilled_marker_accuracy` 0.625（v16 占位符覆盖 62.5%，Rule 16 之外 37.5% 未覆盖）—— 已登记质量线 `RED-LINE-TRIGGERED`，等外部触发启动修复
- **对公真材料未验证**：`PHASE-2-GO-CORPORATE` 等业务方材料包到位后启动长文对公 QC ≥ 88 的合规产出验证
- **LLM 幻觉残余**：即使 Evidence-First + QC Blocker，仍可能有低频"看起来合理但无出处"的结论。缓解方式：QC Blocker + 审贷员终审 + `未能自动填写` 硬回退
- **多模态能力有限**：图片 / 扫描件 PDF 依赖 OCR 前处理，质量受原件影响
- **非结构化文本依赖**：业务介绍 DOCX 的摘要准确率直接影响"经营情况分析"14 分权重

### 8.2 伦理边界

- 输出**显式标为"建议"**（L2-10），UI 醒目标识
- **审批人 / 复核人字段** + 电子签章位（L2-11，Demo 阶段占位）
- **审计日志** `data/audit/*.jsonl` 记录每次调用（DoD L2-12）
- **合作机构 + 数据分级** 文档化（`docs/compliance/partners.md` + `data-grading.md`）
- **客户材料本地处理**，不走境外 API（L2-15）
- **copilot 期**：AI 填报告 → 审贷员审核后才用，审贷员修改回流 `/api/feedback`

### 8.3 合规声明

- 遵循《商业银行互联网贷款管理暂行办法》2025、《金融机构数据安全管理办法》、CAC《AI 安全治理框架 2.0》、《生成式 AI 服务管理办法》
- 底座 LLM（DeepSeek）已在网信办完成生成式 AI 备案
- 合作机构清单已文档化，待对接银行合规部纳入动态名录

## 9. Caveats & Recommendations（注意事项与建议）

**使用前**：
1. 确认 `DEEPSEEK_API_KEY` 已配置（否则真模式不可用，Mock 可跑）
2. 材料上传只接受 `.docx / .pdf / .xlsx / .txt`，文件名 basename 安全
3. session TTL 30 分钟自动销毁工作目录，避免核心材料长期落盘

**使用中**：
1. 所有填写结果需审贷员终审，不作最终决策依据
2. `未能自动填写` 是合规产出，不要人为替换为编造值
3. 修改建议通过 `/api/feedback` 提交，进入数据飞轮第 3 环

**使用后**：
1. session TTL 30 min 到期前下载 docx；否则 session 目录自动清理
2. 审计日志 `data/audit/*.jsonl` 按日切分，合规部定期归档

**不要做**：
- ❌ 把境外 LLM（Claude / GPT）当 Agent6 底座（合规红线）
- ❌ 直接把客户材料 PDF 传给 Tavily / 任何境外 API
- ❌ 跳过 QC Blocker 直接消费原始 LLM 输出

**版本管理**：
- v7.23（当前主干）与 v16（章节改写管线）在不同触发路径并行
- Rule 17 修复 / 对公回归结果 → 触发 Model Card 小版本升级
