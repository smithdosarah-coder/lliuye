# Agent2 风控策略运营 (riskctrl) · sub-PRD v1

**agent_id**: `riskctrl` (per `docs/contracts/agent-naming-ssot.md` v1.0)
**Status**: 🟡 v1 draft · pending PM ratification (per master PRD §3.1 G-03/G-04)
**Owner**: 主 CLI · 修改走 RFC · worker A4-riskctrl 实施
**Phase**: Phase A end (Rewrite acceptance) + Phase B (深化模型)
**作者**: worker-A7 · 2026-04-29

---

## 1. Original Intent (verbatim · 飞书 wiki + 本地 PRD v1.0)

**飞书源**: https://fcntbrvzmfph.feishu.cn/wiki/CQfMwbT9NiTk2pksMqXcunMPnWd (node: `CQfMwbT9NiTk2pksMqXcunMPnWd` · "07 · 风控策略运营助手")
**本地 fallback**: `docs/PRD_风控策略运营助手_v1.0.md`

支持自然语言配策略 / 自动回测评估 / 差错案件诊断 · 让风险经理(原"策略经理"漂 · 统一为"风险经理"per master PRD §5.1) 无需编写代码即可完成策略全生命周期管理:

```
自然语言诉求 → DSL RuleSet 生成 → 自动回测 (KS / AUC / 通过率 / 坏账率) → PDF 报告
                                  ↓
                       差错案件诊断 (case_diagnosis 端点)
```

**3 demo 场景全覆盖** (per 飞书 PRD §2):
1. 小微信用贷 (5-50 万 · 个人经营贷)
2. 消费金融 (≤ 5 万 · 短期)
3. 担保圈 (担保关联风险)

---

## 2. Current Repo State (2026-04-29)

### 2.1 后端

`agent_riskctrl/api.py:1-39` 暴露 2 端点 (CLAUDE.md §11 v3.1):
- `POST /api/riskctrl/dsl_gen` (自然语言→RuleSet JSON)
- `POST /api/riskctrl/backtest` (RuleSet + CSV → KS/通过率/坏账率)

mock=true 切 fixture RuleSet (单一 fixture · 仅小微信用贷场景)。

**缺**:
- ❌ `/api/riskctrl/export_docx` (前端 RiskctrlWorkspace 已调 · 404 容忍 stub · conflict-register Cat 13-1)
- ❌ `/api/riskctrl/export_pdf` (PDF 报告 · 飞书 PRD §3 核心需求)
- ❌ `/api/riskctrl/case_diagnosis` (差错案件诊断 · 飞书 PRD §2)

### 2.2 前端

`web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx` (F-028~F-031):
- features-inventory.md:315-348 实装 1 场景 mock RuleSet 演示
- 4 模块 tab (策略生成 / 回测 / 差错诊断 / 报告导出) · 后两个 dead button

### 2.3 后端运行时常量 (per CLAUDE.md §3.7.1 active rule)

- `agent_riskctrl/backtesting.py:22, 67, 84` `MAX_ROWS=50000` (Q-040 修复后 · 2026-04-26 落地)
- 真实风控样本量 5-50 万行 · 不允许回退 ≤ 500

### 2.4 评估

- `evaluation/agent2_riskctrl.yaml` baseline yaml 已建
- 信贷专业指标 "财务比率计算正确率 ≥ 99%" 适用 (DSL 中数学表达式校验)

---

## 3. Drift Gap (本 sub-PRD · G-03 + G-04)

### 3.1 G-03 · 回测报告导出 (KRR: 🟢 Rewrite)

| 维度 | 内容 |
|------|------|
| Original | 回测完成后输出 PDF 报告含 KS/AUC/通过率/坏账率图表 + 自然语言分析 |
| Current | 仅 dsl_gen + backtest 2 端点 · 无 export_docx/pdf · 前端 dead button |
| KRR | 🟢 **Rewrite** · 端点缺 = 前端 dead button · 银行客户报告导出是核心 PRD 锚 (违 bank delivery DoD 体验红线) |
| Phase | Phase A end |
| Owner | A4-riskctrl + A6 (export contract 协同) |
| Acceptance | `/api/riskctrl/export_docx` + `/api/riskctrl/export_pdf` 通 + 前端按钮调 + smoke pass |

### 3.2 G-04 · 3 demo 场景 + case_diagnosis (KRR: 🟢 Rewrite)

| 维度 | 内容 |
|------|------|
| Original | 3 demo 场景全覆盖 (小微信用贷 / 消费金融 / 担保圈) + case_diagnosis 端点 (差错案件诊断) |
| Current | 仅 1 fixture RuleSet (小微) · 无 case_diagnosis 端点 · 前端 F-028~F-031 仅消费 1 场景 |
| KRR | 🟢 **Rewrite** · 1/3 场景 + 缺核心端点 = 不可演示完整生命周期 · 客户走访前必补 |
| Phase | Phase A end |
| Owner | A4-riskctrl |
| Acceptance | 3 fixture 解锁 + `/api/riskctrl/case_diagnosis` 通 + F-028~F-031 三场景切换 smoke pass |

---

## 4. 产品形态详细 (Phase A end MVP)

### 4.1 用户旅程 (风险经理在 RM workbench 调 riskctrl tile)

1. 风险经理选场景 (小微信用贷 / 消费金融 / 担保圈)
2. 自然语言描述策略诉求 (e.g. "30 天逾期率 < 5% · 申请通过率 ≥ 60%")
3. SSE `/api/riskctrl/dsl_gen` → DSL RuleSet JSON 返 · 显式可视化 (规则树)
4. 风险经理可编辑 RuleSet (UI 表单 · 不直接编代码)
5. 上传样本 CSV (历史贷款样本 · 字段字典 per CLAUDE.md §3.5 row Agent2)
6. SSE `/api/riskctrl/backtest` → 回测 metrics (KS / AUC / 通过率 / 坏账率) · 渐进式可视化
7. 一键 `/api/riskctrl/export_docx` 或 `/api/riskctrl/export_pdf` → 完整报告 (含图表 + 分析文本)
8. 差错案件诊断: `/api/riskctrl/case_diagnosis` 输入单笔差错样本 → LLM grounded 分析"为什么过 / 应否过"

### 4.2 确定性 vs 概率性边界 (per CLAUDE.md §3.1)

- **确定性**: KS / AUC / 通过率 / 坏账率 计算 · DSL 解析 · 规则命中 → Python (`agent_riskctrl/backtesting.py`)
- **概率性**: 自然语言 → DSL 翻译 / 差错案件诊断分析 / PDF 报告自然语言段 → LLM (走 `shared/llm_caller`)
- **禁止**: LLM 现场算 KS/AUC · LLM 直接判定通过率阈值 · LLM 写黑名单代码

### 4.3 LLM caller 迁移 (per CLAUDE.md §3.6)

`agent_riskctrl/llm_judge.py` LLMJudge 基类 → 迁 `LLMCaller(agent_id="riskctrl", endpoint="judge").chat()` · A4-riskctrl 子任务实施。

### 4.4 MAX_ROWS active rule (per CLAUDE.md §3.7.1)

- backtest 端点输入 CSV 行数上限 = 50000 (chunk read · 不一次全 load)
- > 50000 行 chunk 处理 · 前端 progress event 渐进式展示
- 任何 worker 不得回退 ≤ 500 · review 阻断

---

## 5. Phase 拆分

### 5.1 Phase A end 必出

- G-03 export_docx + export_pdf 端点 + 前端按钮真接
- G-04 3 fixture (小微 / 消费 / 担保) + case_diagnosis 端点 + F-028~F-031 三场景 smoke
- LLM caller 迁 `LLMCaller(agent_id="riskctrl")` (per CLAUDE.md §3.6 deprecation 路径)

### 5.2 Phase B 深化

- DSL 翻译模型迭代: prompt + few-shot 优化 · 复杂规则 (跨表 / 时序窗口) 支持
- 担保圈关联图谱可视化 (前端 D3 / Cytoscape)
- 真实 ECS 历史样本接入 (脱敏 · per §3.5 反 5 原则)
- 评估 dashboard: 策略历史版本对比 (与 v3.1 v3.2 KS 增量趋势)

---

## 6. 不做 (per CLAUDE.md §4 + master PRD)

- ❌ 个案授信决策 (是 Agent3 职责)
- ❌ LLM 现场算 KS/AUC (CLAUDE.md §3.1 红线)
- ❌ 不让 LLM 判定红线是否触发 (Agent3 / 客户经理人审职责)
- ❌ MAX_ROWS 回退 ≤ 500 (Q-040 active rule · review 阻断)

---

## 7. 评估锚定 (per master PRD §5.2)

- **Baseline yaml**: `evaluation/agent2_riskctrl.yaml`
- **API 版本对齐**: Agent2 v3.1 (DSL + 回测)
- **通用指标**: `tool_success_rate` (DSL 解析成功率 ≥ 95%) · `task_completion_rate` (回测全流程完成率 ≥ 90%)
- **信贷专业**: 财务比率计算正确率 (vs Python 确定性结果 ≥ 99%) · 内部评分与人工复核一致率 (case_diagnosis 一致率 ≥ 70%)

---

## 8. 角色统一 (per master PRD §5.1)

本 sub-PRD 内 "策略经理" 文案漂全部统一为 **"风险经理"** (`risk_manager`)。CLAUDE.md §4 Agent2 触发列同更 · 主 CLI 同 commit 修 api_server.py:376 IM prompt 文案。

---

## 9. 引用

- Tier 1: `docs/contracts/agent-naming-ssot.md` v1.0 + `sse-envelope.md` v1.0 + `llm-prompt-contract.md` v1.0
- Tier 2: CLAUDE.md §3.1 (确定性边界) + §3.6 (LLM caller 迁) + §3.7.1 (Q-040 MAX_ROWS active rule) + §4 (Agent2 边界) + master-2026-04-29.md §3.1 G-03/G-04
- Tier 5: decisions-log Q-040 (MAX_ROWS · 已 active 落 §3.7.1)
- 飞书: https://fcntbrvzmfph.feishu.cn/wiki/CQfMwbT9NiTk2pksMqXcunMPnWd

---

**作者**: worker-A7 · Phase A Week 2-3 · 2026-04-29
**状态**: v1 draft · pending master PRD ratification
