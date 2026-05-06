# 业务专家 Review 流程 (Business Expert Review Protocol)

> **目标**: 杜绝 Agent1 类"工程师写完即认为 ship"事故 (PM 反馈"10 年前新闻当推荐核心理由")
> **建立**: 2026-05-06 · Phase C charter Track D · D7
> **Authority**: Phase C charter §13 RACI 表 · 业务专家是 Track D 的 R (责任人)

---

## 1. 触发条件 (强制走流程)

任何以下变更必须走业务专家 review · sign-off 才进 ship:

- 新 Agent 上线 (Agent1-6 任一新 endpoint / 新业务能力)
- 影响推荐/决策口径的逻辑变更
- 数据源新增 / 替换 / 抓取规则变更
- 评估指标 baseline 公布 / SLA 数字变更
- 客户走访演示前的 demo 路径冻结
- LLM prompt / 业务规则变更

---

## 2. Review 4 步流程

### 步骤 1 · PRD 必含 review 步骤 (前置)

- 任何 PRD 必含 "业务专家 review" 章节
- 列出: review 范围 / review 期 / review 方式 / sign-off 条件
- PRD 没此章节 → 工程不动手

### 步骤 2 · 业务专家 walkthrough (主体)

业务专家用 **真实金融案例** (`data/eval/real_scenario_cases.jsonl`) 走完整路径:

- 跑 `py scripts/eval/run_real_scenarios.py` 看 10/10 PASS
- 在 production `https://liuye.me/login` 5 角色登录走 demo
- 抽样 5-10 个真实客户场景 · 检查 AI 输出合理性
- 关注 **AI 输出能不能直接对客户说** (不是工程师能不能跑通)

### 步骤 3 · Sign-off 4 必查项

业务专家必校验:

| 项 | 校验标准 | 不过怎么办 |
|---|---|---|
| **AI 输出合规** | 没违反适当性销售 / KYC / 双录 / 反洗钱规则 | 阻断 ship · fix |
| **证据时效有效** | evidence 不过期 (per DP4 SLA) · 无 10 年前新闻类问题 | 阻断 · 加 freshness 校验 |
| **客户口径合理** | RM 能直接对客户念 · 不需重大改写 | 阻断 · 调 prompt |
| **数据来源可靠** | 核心理由不依赖单 Tier 4 公开 web (per D1) | 阻断 · 加 Tier 1/2/3 来源 |

### 步骤 4 · Sign-off 留底

通过的 review 必留底:

```
docs/audit/business-review/<feature-name>-<YYYY-MM-DD>.md

含字段:
- feature: <feature 名>
- pr_or_commit: <SHA>
- reviewer: <业务专家名 + 工号>
- reviewed_at: <ISO timestamp>
- walkthrough_cases: <跑了哪些真实场景 case_id>
- sign_off: PASS / NEEDS-FIX / REJECT
- notes: <业务专家给的 critical feedback>
```

---

## 3. Monthly Walkthrough (定期巡检)

每月 1 次 · 业务专家 + 主 CLI + PM 三方:

- **范围**: 最近 30 天 production 抽样 (随机 50 笔决策)
- **抽样**: `py scripts/audit/freshness_check.py` + `data/audit/business-review/sample-<YYYYMM>/`
- **重点**: 找类 Agent1 "10 年前新闻" 露馅 / 类似系统性问题
- **输出**: `docs/audit/business-review/monthly-<YYYY-MM>.md`
- **行动**: 任何露馅 case 必沉淀 → `data/eval/real_scenario_cases.jsonl` 加 regression case · CI gate

---

## 4. PM Feedback → Regression Case 闭环 (Codex R3 加)

这是 Codex R3 critical insight: **缺负反馈闭环 是 Agent1 露馅的根因之一**.

任何 PM / 业务专家 / 客户 发现的露馅 case 必走 4 步:

1. **24h 内**: 主 CLI 加进 `data/eval/real_scenario_cases.jsonl` 作 regression case
2. **48h 内**: 加进 source blacklist (如果是某来源问题) `data/source_blacklist.json`
3. **如果是 freshness 问题**: 调 `FRESHNESS_SLA_DAYS` 阈值 + 走 RFC
4. **如果是数据 tier 问题**: 调 `DOMAIN_TIER_MAP` (in `shared/data_tiers.py`)

CI 必须跑 `run_real_scenarios.py --strict` · 任何 regression case 失败阻 ship.

---

## 5. 业务专家角色

### 谁是业务专家

PM 拍板 · 不能由工程师代审 (per Codex R3 反思条 c · "业务专家 review 缺位"):

- 银行业务老师 (个金 RM / 审贷员 / 合规官 / 风险经理 至少 1 人)
- 必须有真业务经验 (≥ 5 年金融业务)
- 不能是工程岗

### 业务专家职责

- **PRD review**: 看 PRD 业务能力描述是否合理 · 数据源 / 评估指标是否真业务可达
- **Walkthrough**: 用真实 case 跑端到端
- **Sign-off**: 4 必查项过 → PASS · 任一不过 → 阻 ship + 留 critical feedback
- **Monthly**: 定期巡检 + 露馅 case sample
- **Authority**: 业务专家 sign-off 跟 PM 拍板等同 · 工程不能 override

---

## 6. 与现有协议的关系

| 协议 | 范围 | 关系 |
|---|---|---|
| **decision-ledger.md** (BE7) | 决策上链审计 | 业务专家可通过 ledger 查任意决策 audit trail |
| **llm-prompt-contract.md** (Phase A) | LLM prompt 8 段 SSOT | 业务专家 review LLM 输出口径必基此 contract |
| **agent-naming-ssot.md** (Stage 4) | 6 Agent × 8 维度命名 | 业务专家 review 用此 contract 校验命名一致 |
| **shared-change-protocol.md** (主 CLI) | 红区/黄区变更协议 | 业务能力变更走此协议 · 业务专家是 reviewer |
| **business-expert-review-protocol.md** (本文档) | 业务专家 review 流程 | 流程层 · 上述 contract 是工具层 |

---

## 7. 当前实施 status

- ✅ 真实场景测试集 (D6 ship · `data/eval/real_scenario_cases.jsonl` · 10 case)
- ✅ run_real_scenarios.py CI runner (10/10 PASS)
- ✅ freshness_check.py 6 Agent audit (`scripts/audit/freshness_check.py`)
- ⏳ PRD review 章节 hardcode (待加进 6 Agent PRD 模板)
- ⏳ Monthly walkthrough 第一次 (待 PM 排期 + 邀请业务专家)
- ⏳ docs/audit/business-review/ 目录建立 (待第一次 review)

---

**Authority**: PM 拍板 · 工程不能 override · 业务专家 sign-off 后才 ship
**Source**: Phase C charter Track D · D7 + Codex R3 final 反思 (e) "业务专家 review 缺位"
