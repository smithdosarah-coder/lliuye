# Agent Output Rubric · 6 Agent 业务可用 pass-fail

> **Tier**: 1 (per CLAUDE.md §15 · 红区 · RFC 改)
> **Authority**: PM 2026-05-11 12:55 GO ratify (B.4 SLO 4 dispatch)
> **Owner**: fix-bugs worker · B.4 Phase
> **Status**: 🟢 RATIFIED
> **配套**: `docs/contracts/pb2-prompt-governance.md` (PB#2 7 守则 + 越权 4 判定 + 不可照搬 3 条) · `docs/contracts/llm-prompt-contract.md` (8 段 SSOT)

---

## 0. 为什么有这份契约

PM SLO 4 verbatim: "Agent 产出结果是实打实能用于业务中的"。

走歪诊断 (audit `docs/working/slo4-schema-audit-2026-05-11.md`): 6 Agent schema 都在 · LLM 生成内容"通用化 AI 味重" · 不是中国对公信贷 (50-5000 万 RMB) 银行风格 · 客户经理 / 审贷员 / 合规官 / 风险经理 拿到产出**不敢用**因为:
- 没具体数字依据 (e.g. "经营状况良好" 无比率)
- 没 actionable step (e.g. "需关注" 无 RM 动作)
- 没 evidence 锚 (e.g. claim 无出处)
- 没 fresh / source-tier 上下文 (e.g. 10 年前新闻当推荐核心理由)

本 rubric 是 **B.4 SLO 4 prompt tune 的目标定义** · 也是 **D 任务 admin 真号 1-5 评分 anchor**。

---

## 1. 1-5 Likert anchor (agent-neutral · 共形)

业务可用度 1-5 评分 (银行 RM/审贷员/合规官/风险经理 视角):

| 分 | 标签 | 判定 (任一 anchor 命中即定级) |
|---|---|---|
| **5** · 直接可用 | 银行员工原文交付客户/审贷会 · 无需改 | (a) 每条 claim 带 evidence_date + source_tier · (b) 财/行/经/担 vocab 准 · (c) actionable step 含责任方 + 时限 · (d) 数字与 Python 计算层 100% 一致 |
| **4** · 小改可用 | 1-2 处 wording 调整后可用 · evidence 完整 | (a) evidence 全 · (b) 行话基本对 (偶有可口语化的词) · (c) actionable 但无明确时限 · (d) 数字 ≥ 99% 一致 |
| **3** · 需调整可用 | ~ 30% 重写 · evidence 部分缺 · 用词偶 generic | (a) ≥ 50% claim 有 evidence · (b) 行话 50% 准 · (c) action 笼统 ("尽快处理") · (d) 数字有 1-2 处 stale |
| **2** · cosmetics 可用 | frame 在但内容 generic · evidence 链断 | (a) < 50% claim 有 evidence · (b) "经营良好" "需关注" "可能存在" 多发 · (c) 无 actionable · (d) 数字偶错 |
| **1** · 不可用 | 完全 generic / lorem · 无业务价值 | (a) 无 evidence · (b) lorem 残留 · (c) 占位符未替 (`{客户名}` / `{未能自动填写}`) · (d) 编造数字/政策 |

**B.4 SLO 4 ship 硬线**: 6 Agent 真号 sample 平均 ≥ **4** · 任一 < **3** → stop the line · 不能 GO。

---

## 2. 跨 Agent 共形 pass-fail (任一 fail = 不能 GO)

| # | 维度 | Pass | Fail |
|---|---|---|---|
| C1 | **Evidence-First** (§3.3) | 每条数字/判断/结论带可追溯出处 (file / 段落 ID / URL) | claim 无 source · 或 source 为 "见银行产品手册" / "材料显示" 等 placeholder |
| C2 | **数据时效** (§3.5.1 #6) | 推荐核心理由 freshness 满足 SLA (新闻 ≤ 180d · 财报 ≤ 120d · 处罚 ≤ 365d · 政策 ≤ 365d · 案例 ≤ 730d) | 推荐核心理由用 stale 证据 (e.g. 2014 年新闻推 2026 年贷款) |
| C3 | **Tier 交叉** (§3.5.1 #6) | 推荐核心理由 ≥ 1 条 Tier 2-3 (政府监管 / 行业) 证据 · 不依赖 Tier 4 单源 | 推荐核心理由仅 Tier 4 (公开 web) 单源 |
| C4 | **银行风格 actionable** | action 含 (责任方 · 时限 · 触发条件 / 结果) | action 用 "需关注" / "建议跟进" / "可能存在风险" / "尽快处理" / "进一步评估" |
| C5 | **占位符零残留** | `{客户名}` / `{未能自动填写: X}` / `{TBD}` 等占位符必在 SSE 渲染前替换或显式标 "未能自动填写: 具体字段" | placeholder 直接出现在 UI / docx / SSE event 文本 |
| C6 | **数字一致** (§3.1) | 财务比率 / 红线阈值 / 同比 / 通过率 / KS / freshness_days 由 Python 算 · LLM 仅引用 | LLM 现场算比率 (e.g. 自己除一下报"资产负债率 45%") |
| C7 | **PIPL 合规** (§3.7.3) | LLM 调用走 `shared/llm_caller/` · 境内 fallback chain (deepseek + dashscope) · audit log 含 region | 跨境 LLM 调用 / 裸 OpenAI client / 无 audit |

---

## 3. per-Agent pass-fail

### 3.1 Agent1 channel (look-alike 获客 · RM 视角)

**输入**: 画像描述 + 知识库
**必填字段** (`/api/channel/run` done event):

| 字段 | Pass | Fail |
|---|---|---|
| `candidates[].industry` | 具体行业 (e.g. "制造业 · 电子元件") | "未知" / "未获取" / `null` / 通用一级 ("工业") |
| `candidates[].geo` | 省+市/区 (e.g. "浙江 · 杭州 · 余杭区") | "未知" / 仅省 / 仅国 |
| `candidates[].scale` | 微型/小型/中型/大型 + 数值锚 (e.g. "中型 · 营收 1.5 亿") | "未知" / 仅 label |
| `candidates[].similarity` | float [0,1] · 与 query 真匹配 | 0.0 / null / 编造数字 |
| `match_dimensions[]` | dim_name + hit_evidence + score · 4 维 (行业/区域/规模/信号) | 数组空 / 无 hit_evidence |
| `product_recommendations[].intro` | 行业上下文 (e.g. "制造业新建项目 3-5年 LPR+80-150bp") | "见银行产品手册" |
| `pitch_scripts[].script_text` | 50-80 字 · 含 (信号锚 + 产品 + 数字 + 行业话术) | "我行可提供支持 · 详细沟通" 通用模板 |

**1-5 评分锚** (RM 视角):
- 5: 看 pitch 后直接复制粘贴发客户 · 名字行业匹配 · 数字具体 · 信号新鲜
- 4: 名字行业对 · 数字 1 处需补 · 信号 1 周内
- 3: 名字对 · 数字 generic · 信号 1 月内
- 2: 名字对 · 内容 generic ("匹配度较高") · 信号无具体来源
- 1: lorem / 名字串位 / 信号 stale (≥ 6 月)

### 3.2 Agent3 credit (授信决策 · 审贷员视角)

**输入**: Agent6 ReportJSON + 材料
**必填字段** (advice payload + decision_graph):

| 字段 | Pass | Fail |
|---|---|---|
| `sub_scores` 4 维 (财/行/经/担) | int [0,100] · 每维有 dimension_reasoning (e.g. "财: 流动比率 1.8 vs 同业 1.5 健康") | 仅 int · 无 reasoning · 或 reasoning 通用 "财务良好" |
| `decision_reason` | ≥ 200 字 · 引用 4 维 metrics + peer benchmark + 红线触发说明 + 担保覆盖 | "综合评分 X · 四维评分 X/X/X/X · 建议放款" 通用模板 |
| `red_line_hits[].policy_quote` | 政策原文 verbatim + 阈值差 (e.g. "对公资产负债率 ≥ 80% 黄灯触发 · 实际 85%") | 仅 description · 无 policy_text |
| `case_matches[].similarity_breakdown` | {industry_match, revenue_closeness, score_closeness} dimension dict | 仅 similarity float |
| `advice.approved_amount` + `amount_justification` | 含 3 法对照 (营收法/净资产法/担保法) + 取数逻辑 | 仅 amount 数字 |
| `conditions[]` (放款条件) | RM-actionable · 含阶段性 (初审/中审/放款) + 触发条件 | "审批通过后放款" 通用 |

**1-5 评分锚** (审贷员视角):
- 5: 审贷会原文采用 · 4 维 specific · 红线引政策原文 · 案例对照 dimension 全
- 4: 主体可用 · 1 维 reasoning 需补 metric
- 3: frame 在 · 但 50% dim 是通用 ("行业良好")
- 2: 仅返数字 · 无 reasoning
- 1: template fallback ("综合评分 75 建议放款 3000 万")

### 3.3 Agent4 alert (预警榜单 · RM 处置视角)

**输入**: 在贷客户池 + 规则库
**必填字段** (`/api/alert/scan` done event):

| 字段 | Pass | Fail |
|---|---|---|
| `hit_list.red/yellow/green[].matched_rules` | 规则名 + 命中具体值 + 阈值 (e.g. "财务恶化: 资产负债率 85% > 80%") | 仅规则名 · 无具体值 |
| `evidences[]` | 含 (source · snippet · url · evidence_date · freshness_days · source_confidence) | 仅 source + snippet · 无 freshness / confidence |
| `dispositions[company_name]` | 80-150 字 · 含 (24h/7d/30d 三阶段 + RM/分行/合规 责任方 + 触发条件) | "需关注" / "建议跟进" / "尽快处理" |
| `follow_up_milestones[]` (NEW) | `[{stage, days_from_today, responsible, condition}]` | 字段缺 |

**1-5 评分锚** (RM 处置视角):
- 5: disposition 三阶段全 · 时限明确 · 触发条件可 KPI
- 4: 主体可用 · 一个 milestone 模糊
- 3: 仅 24h 第一步 · 后续 generic
- 2: "建议核查" 无时限
- 1: "需关注" / "可能存在风险"

### 3.4 Agent5 compliance (违规清单 · 合规官视角)

**输入**: 新政策 + 业务制度库
**必填字段** (`ViolationReason` schema · `agent_compliance/violation_schema.py`):

| 字段 | Pass | Fail |
|---|---|---|
| `policy_excerpt` (≤ 300 chars) | 监管原文 verbatim · 含条款编号 (e.g. "银保监 [2025] 12 号 第 3 条") | 改写 / 通用 / 缺条款号 |
| `clause_text_hash` | sha256 16 hex · 必 populate (红线 #8) | empty / null / 不匹配 registry |
| `business_excerpt` (≤ 300 chars) | 业务记录 verbatim · 含 event_id | LLM 改写 |
| `conflict_field` | 准入/KYC/风偏/审查/SOP/期限/额度 等 regulatory bucket | 默认 "合规阈值" |
| `confidence` | float [0,1] · 1.0 hard-rule / 0.7 LLM / 0.5 fallback | 缺字段 |
| `evidence_date` / `freshness_days` / `staleness_passed` | 必 populate · 政策 ≤ 365d SLA | 缺字段 / SLA 超 |
| `revisions[].disposition` (NEW) | enum 暂停/冻结/强制整改/监测/风险提示 | 缺字段 |
| `revisions[].text` | 具体改写建议 + 法律部触发条件 | "修改相关业务条款" |

**1-5 评分锚** (合规官视角):
- 5: 合规官直接据此写法律部 work order · disposition 明确 · 政策原文可查 hash
- 4: 主体可用 · disposition 需补一条
- 3: violation 列了但 revision generic
- 2: 仅返 violation_id · disposition 缺
- 1: "可能违规 · 需进一步审核"

### 3.5 Agent6 report (信贷报告 · 审贷员视角)

**输入**: 企业材料 + 模板
**必填字段** (ReportJSON + docx):

| 字段 | Pass | Fail |
|---|---|---|
| 财务章 (4 chapter §3.1 中财务) | 三段式 (数据罗列 ≥ 4 同比 / 外因引行业卡 / 内因引材料源) | "经营状况良好 · 财务稳健" 通用 |
| 行业章 | 引 industry_card + policy_card · 排名/趋势/政策 | "行业前景广阔" 无数据 |
| 经营章 | 引材料 excerpt · 不 LLM 编 | LLM 编经营内容 |
| 担保章 | 含 (押品名 · 评估价 · 担保方资信 · 增级方式) | 通用 "押授信担保" |
| QC 9 维 (`quality_scorer.py`) | 总分 ≥ 75 + dim 闸 (财务 ≥ 7 / 一致性 ≥ 6 / 缺标注 ≥ 5) | 总分 ≥ 75 但 dim 闸 fail (现行 bug · audit P5) |
| `pending_tag[]` | 缺字段标 "【未能自动填写: 具体字段】" | LLM 编 / 留 placeholder |

**1-5 评分锚** (审贷员视角):
- 5: 4 chapter 三段式全 + dim 闸全 ≥ 7 · 审贷员直接进会
- 4: 主体可用 · 1 章某段需补 metric
- 3: frame 在但担保章 generic
- 2: 财务章无同比 / 行业章无卡
- 1: 通用模板 ("公司经营稳健 · 财务状况良好 · 行业前景广阔")

### 3.6 Agent2 riskctrl (DSL + 回测 · 风险经理视角)

**输入**: 策略诉求 + 样本 CSV
**必填字段** (`/api/riskctrl/dsl_gen` + `/api/riskctrl/backtest`):

| 字段 | Pass | Fail |
|---|---|---|
| `ruleset.rules[].strategy_intent_mapping` (NEW) | "诉求: X → 字段 Y → 阈值 Z → action · 原因: ..." 显式映射 | LLM 仅返 conditions JSON · 无 mapping |
| `ks.ksPeak` + `ks_interpretation` (NEW) | float + {label "中等区分能力" · benchmark_range [0.35, 0.50] · vs_baseline "+0.07"} | 仅 float |
| `samples[].concentration` (NEW) | "拒绝集中在制造业 · 占拒绝总量 62%" segment drilldown | 仅三档 count |
| `business_metrics.pass_rate` + `vs_baseline` | "通过率 75% · 较 baseline 降 5pp" | 仅 % |
| `rule_stats[].interpretability_label` (NEW · per llm_judge) | "优秀 (4.5-5)" / "可用 (3.5-4.5)" / "需改进 (2.5-3.5)" / "不可用 (<2.5)" | 仅 score float |
| `MAX_ROWS=50000` (§3.7.1) | sample 量 ≥ MAX_ROWS 上限 | 回退到 500 (Q-040 违反) |

**1-5 评分锚** (风险经理视角):
- 5: rule 看得懂 (诉求→logic 映射全) · KS 有 benchmark · 拒绝集中度明确
- 4: 主体可用 · 1 rule mapping 缺
- 3: rule JSON 在但需自己解读
- 2: 仅 conditions · 无 mapping · KS 仅数字
- 1: 通用 "建议优化" / "策略区分能力较强"

---

## 4. 评估方法

### 4.1 真号 E2E 评分流程 (Task D)

1. **环境**: ECS production (139.196.30.69 · 走 `liuye.me` Cloudflare tunnel) · admin 真号登录
2. **样本**: 每 agent 1 真业务 case (per `data/eval/real_scenario_cases.jsonl` 选 1 · 或新构 1)
3. **跑通**: agent demo 真上传/输入 → 真业务产出 (SSE 全程录)
4. **评分**: 2 评分员 (PM + worker) 独立按本 rubric 1-5 评 → 取均值
5. **artifacts**: 6 docx/json/决策书 sample + LLM 调用 log + 评分表 → `docs/working/slo4-real-call-samples-2026-05-11/`

### 4.2 fail case 配套 (PB#2 守则 #6)

每 agent prompt tune commit 必同时:
- 加 1 fail case entry 到 `data/eval/real_scenario_cases.jsonl`
- entry 含 (case_id · scenario · 预期 fail · 实际 LLM 输出 · 改后 LLM 输出)
- 触发 regression CI · 后续不复现

### 4.3 stop-the-line trigger (任一命中 = 不能 GO)

| Trigger | Severity |
|---|---|
| 6 agent 真号 sample 平均 < 4 | 🔴 STOP |
| 任一 agent < 3 | 🔴 STOP |
| C1-C7 跨 agent 共形 pass-fail 任一 fail | 🔴 STOP |
| placeholder 残留 (`{客户名}` / `lorem` / `{未能自动填写: ...}` 无具体字段名) | 🔴 STOP |
| LLM 现场算财务比率 (§3.1 违) | 🔴 STOP |
| 跨境 LLM 调用 / 无 audit log (§3.7.3 违) | 🔴 STOP |

---

## 5. 修改路径 (RFC)

本 rubric 改动需:
- PM `Authorized-By` trailer
- 同 commit 加 `docs/handoff/decisions-log.md` Q-NNN entry
- 同 commit update `docs/reset/state-snapshot.md`

per CLAUDE.md §15 Tier 1 ladder · `pb2-prompt-governance.md` + `llm-prompt-contract.md` 同 tier · 本 rubric 不 override 两者 · 而是把"业务可用"具体化到 per-agent 1-5 评分。

---

## Authority

- **Original brief**: PM 2026-05-11 12:55 (B.4 SLO 4 dispatch · commit `59d32fd`)
- **Audit basis**: `docs/working/slo4-schema-audit-2026-05-11.md` (6 parallel Explore agent · file:line evidence)
- **Author**: fix-bugs worker · 主 CLI Claude Opus 4.7
- **Effective**: 2026-05-11 (B.4 SLO 4 ship 前所有 prompt tune commit 必参照本 rubric)
