# Agent3 授信决策辅助 (credit) · sub-PRD v1

**agent_id**: `credit` (per `docs/contracts/agent-naming-ssot.md` v1.0)
**Status**: 🟡 v1 draft · pending PM ratification (per master PRD §3.1 G-05/G-06 · §7 open question 1)
**Owner**: 主 CLI · 修改走 RFC · worker A4-credit + A6 (handoff schema) 协作实施
**Phase**: Phase A end (schema doc) + Phase B-3 (e2e 真接 · 选 b 路 default · pending PM)
**作者**: worker-A7 · 2026-04-29

---

## 1. Original Intent (verbatim · 飞书 wiki + 本地 PRD v2.0)

**飞书源**: https://fcntbrvzmfph.feishu.cn/wiki/OOTtwSlD5iOzIlkNwMYc84JTnVb (node: `OOTtwSlD5iOzIlkNwMYc84JTnVb` · "05 · 授信决策辅助智能体")
**本地 fallback**: `docs/PRD_授信决策辅助智能体_v2.0.md`

消费 Agent6 产出的 ReportJSON + 多源补充信息 (行业基准 / 历史案例 / 征信) · 输出一张 90 秒看懂的**决策 Dashboard**:

- **批 / 不批** 二元结论 + 置信度
- **额度** (限额建议)
- **期限** (建议授信期)
- **利率** (区间)
- **红线** (触发了哪些 + 理由)

面向 **审贷会主席 / 风控主管 / 审贷员**。三板块共享决策引擎 + 红线规则库:

| 板块 | 客户类型 | 额度区间 | 关键差异 |
|------|---------|---------|---------|
| 对公 (corporate) | 中型企业 / 集团 | 50 万-5000 万 | 行业基准 + 资产负债 + 担保 |
| 普惠 (small_business) | 小微 / 个体 | 5 万-500 万 | 经营流水 + 行业波动 + 抵押 |
| 对私 (retail) | 个人 / 工薪 | 5 万-500 万 | 征信 + 收入 + 负债比 |

---

## 2. Current Repo State (2026-04-29)

### 2.1 后端

`agent_credit/api.py:1-23` 暴露 4 端点 (CLAUDE.md §11 v3.1):
- `GET /api/credit/presets/{segment}` (corporate / small_business / retail · 三板块预设)
- `POST /api/credit/decision` (SSE · 四维评分 + 红线 + 决策结论)
- `POST /api/credit/export_docx`
- `GET /api/credit/handoff/demo/{segment}` (**stub** · fixture 路径)

### 2.2 前端

`web/src/app/archive/credit/_components/CreditWorkspace.tsx` (F-015~F-019):
- 三模式 tab (对公 / 普惠 / 对私) + 四维 Radar + Gauge + 案例 + ScoreRing 实装
- EmptyState 注释含 "Agent6 handoff onClick 不真消费" (CreditWorkspace.tsx:1568-1635)
- **不消费 Agent6 ReportJSON** · 自跑独立打分 state

### 2.3 跨 Agent handoff 现状

- Agent6 → Agent3: stub `GET /api/credit/handoff/demo/{segment}` · fixture 路径 · 不接 Agent6 真 SSE 产出
- Agent3 → Agent6 (回写审批意见章节): **未实现**
- contract: `docs/contracts/channel_to_credit_handoff.md` 已建 (channel→credit) · **report→credit handoff schema 待立**

### 2.4 评估

- `evaluation/agent3_credit.yaml` baseline yaml 已建
- 信贷专业 "内部评分与人工复核一致率" + "红线判定准确率" 适用

---

## 3. Drift Gap (本 sub-PRD · G-05 + G-06 · 双 🟡 PM 拍板归属)

### 3.1 G-05 · Agent6 → Agent3 真 session 串联 (KRR: 🟡 Rewrite · 选 b 路 default)

| 维度 | 内容 |
|------|------|
| Original | Agent6 报告 UI 上"送 Agent3 做决策"按钮直接传 ReportJSON · Agent3 90 秒决策 dashboard 真消费 |
| Current | `/api/credit/handoff/demo/{segment}` stub fixture · 真 session 串联未实现 · F-015~F-019 自跑独立 state |
| KRR | 🟡 **Rewrite (b 路 default · pending PM)** · 真 session 串联属 A6 schema (定字段) + A4-credit + A4-report (consumer 真接) · **不属 PRD 单独 backlog** (codex 反对 PRD 越界占用 schema 设计) |
| Phase | Phase A (handoff schema doc) + Phase B-3 (e2e 真接) |
| Owner | A6 (schema) + A4-credit + A4-report (consumer) |
| Acceptance | handoff schema doc 落 (Phase A) · e2e smoke `report → credit handoff` 真消费 ReportJSON (Phase B-3) |

### 3.2 G-06 · 决策意见回写 Agent6 报告 (KRR: 🟡 Rewrite · 选 b 路 default)

| 维度 | 内容 |
|------|------|
| Original | Agent3 决策意见可回写 Agent6 报告"审批意见"章节 (双向闭环) |
| Current | 未实现 (Agent3 无 writeback 端点 · Agent6 无 inbound 章节注入逻辑) |
| KRR | 🟡 **Rewrite (b 路 default · pending PM)** · 同 G-05 逻辑 · 双向 schema + 双 consumer · 不属 PRD 范围 |
| Phase | Phase B-3 |
| Owner | A6 (schema 加 decision → report writeback row) + A4-credit (产出 writeback) + A4-report (回写章节) |
| Acceptance | 双向 schema doc + e2e smoke `decision → report 章节注入` 真过 |

### 3.3 PM open question 1 (per master PRD §7)

**G-05/G-06 归属决**:

- **(a) PRD 锚 + A6 schema 双线推**: 本 PRD 把 G-05/G-06 提为 PRD-level 必出项 · A6 schema doc + A4 consumer 实接均算 PRD acceptance · 工程量大 (Phase A end 必交 e2e)
- **(b) 仅 A6 schema doc · e2e 推 Phase B-3** (本 PRD default · codex + A7 共识): G-05/G-06 不算 PRD 单独项 · A6 schema doc 是 Phase A 必出 · e2e 真接推 Phase B-3 商业化阶段

PM 若选 a · 本 sub-PRD §3.1 + §5.1 fix-forward + decisions-log Q-NNN ack。

---

## 4. 产品形态详细 (Phase A end MVP · 选 b 路)

### 4.1 用户旅程 (审贷员在 RM workbench 调 credit tile)

1. 审贷员从 Agent6 报告 UI 点 "送 Agent3 决策" 按钮 (F-009~F-014 工具栏)
2. Agent6 把 ReportJSON 提交到 `/api/credit/decision` (SSE · ReportJSON 作为 input · per Phase B-3 真接 · Phase A 仅 schema doc)
3. Agent3 三板块决策引擎:
   - 对公: 行业基准卡 + 资产负债比 + 担保结构 → 四维评分
   - 普惠: 经营流水 + 行业波动 + 抵押率 → 四维评分
   - 对私: 征信 + 收入 + 负债比 → 四维评分
4. 红线规则库扫: 触发 N 条红线 → 显式列 + 引用规则 ID
5. 决策 Dashboard (90 秒看懂):
   - **批/不批** + 置信度 (确定性 · 规则命中)
   - **额度建议** (区间 · 含 cap)
   - **期限建议** (短/中/长)
   - **利率建议** (区间 · 含 LPR 锚)
   - **类似案例** (历史 5 案例召回)
6. Phase B-3: 审贷员录入决策意见 → `/api/credit/writeback` → Agent6 报告"审批意见"章节注入

### 4.2 确定性 vs 概率性边界 (per CLAUDE.md §3.1)

- **确定性**: 财务比率计算 / 红线阈值判定 / 行业基准对比 → Python (`financial_analyzer.py` + 规则引擎)
- **概率性**: 行业意见 / 决策建议自然语言 / 类似案例召回排序 → LLM (走 `shared/llm_caller`)
- **禁止**: LLM 现场算资产负债比 · LLM 直接判定红线触发 · LLM 直接给最终批/不批结论 (人工最后 confirm)

### 4.3 LLM caller 迁移 (per CLAUDE.md §3.6)

`agent_credit/api.py` 直 `LLMClient(provider=...)` → 迁 `LLMCaller(agent_id="credit", endpoint="/api/credit/decision").chat()` · A4-credit 子任务实施。

---

## 5. Phase 拆分

### 5.1 Phase A end 必出

- handoff schema doc 落 `docs/contracts/channel_to_credit_handoff.md` 已 channel→credit; **必须新立 `report_to_credit_handoff.md`** (Agent6.ReportJSON → Agent3.decision_input schema)
- LLM caller 迁 `LLMCaller(agent_id="credit")`
- 角色统一: "审贷官" → **"审贷员"** 全栈搜替 (per master PRD §5.1)

### 5.2 Phase B-3 推延

- G-05 e2e: Agent6 → Agent3 真 SSE 串联 + ReportJSON 真消费
- G-06 双向闭环: Agent3 → Agent6 writeback 章节注入
- 历史案例库扩充 (从 5 → 50+ · per Q-040 mock 量级 follow-up)
- 三板块决策模型迭代 (基于真实审贷历史微调评分权重)

---

## 6. 不做 (per CLAUDE.md §4 + master PRD)

- ❌ 写报告 (是 Agent6 职责 · Agent3 仅消费 ReportJSON)
- ❌ 拓客 / 候选搜索 (Agent1 职责)
- ❌ LLM 现场算财务比率 (CLAUDE.md §3.1 红线)
- ❌ LLM 直给最终决策 (人工 confirm 是 copilot 期硬线 · per CLAUDE.md §9)
- ❌ 不在 Phase A 强推 e2e 真接 (走 b 路 · 不阻 Phase A 验收)

---

## 7. 评估锚定 (per master PRD §5.2)

- **Baseline yaml**: `evaluation/agent3_credit.yaml`
- **API 版本对齐**: Agent3 v3.1 (对公 / 普惠 / 对私三板块)
- **通用指标**: `field_completeness` (四维评分必出率 ≥ 99%) · `evidence_rate` (红线触发必引用规则 ID) · `tool_success_rate` (handoff 消费成功率 Phase B-3 ≥ 90%)
- **信贷专业**: 内部评分与人工复核一致率 ≥ 75% · 红线判定准确率 ≥ 95% · 财务比率计算正确率 ≥ 99%

---

## 8. 引用

- Tier 1: `docs/contracts/agent-naming-ssot.md` v1.0 + `channel_to_credit_handoff.md` (G-05 schema 模板) + `sse-envelope.md` v1.0 + `llm-prompt-contract.md` v1.0
- Tier 2: CLAUDE.md §3.1 (确定性边界) + §3.6 (LLM caller 迁) + §4 (Agent3 边界) + §9 (copilot 期硬线) + master-2026-04-29.md §3.1 G-05/G-06 + §7 open question 1
- 飞书: https://fcntbrvzmfph.feishu.cn/wiki/OOTtwSlD5iOzIlkNwMYc84JTnVb

---

**作者**: worker-A7 · Phase A Week 2-3 · 2026-04-29
**状态**: v1 draft · pending master PRD + PM open question 1 (G-05/G-06 归属) ratification
