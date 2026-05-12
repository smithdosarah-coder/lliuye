# B.4 SLO 4 · 6 Agent Schema + Prompt Audit (2026-05-11)

**Owner**: fix-bugs worker · Phase B.4 · branch `feat/b34-fix-bugs`
**Goal**: 6 Agent 产出从"通用 AI 味"→"中国对公信贷 50-5000 万银行风格 actionable"
**Method**: 6 parallel Explore agents · read-only · file:line evidence

---

## 共性走歪 (5 pattern)

| Pattern | 命中 Agent | 真因 |
|---|---|---|
| P1 · `_template_*` fallback 通用化 | channel · credit · alert · compliance · riskctrl | LLM 不可用时 fallback 抽掉 business specifics ("匹配度较高" / "经营状况良好" / "需关注") |
| P2 · few-shot 真案例缺失 | channel · credit · alert · compliance · riskctrl | prompts.py few-shot list 默认空 OR 仅 1 对自动生成 OR 仅 input-only seed |
| P3 · LLM user_prompt 缺数据时效/source tier 透传 | channel · credit · alert · compliance | freshness_score / source_confidence 在 evidence_pipeline 算了但没塞进 LLM 看 (违 §3.5.1 #6 半步) |
| P4 · dimension-specific reasoning 缺 | credit (4 维) · riskctrl (KS interpretation) | LLM 看不到 "vs 同业 benchmark" 锚点 · 输出停在数字层不到 business 解读层 |
| P5 · 段路由不存在 (report) | report v16 | 财务/行业/担保 通用 REWRITE 一锅煮 · 三段式约束在 prompt 但无强制 |

---

## per-Agent 真痛清单 (按 prompt tune 优先级)

### Agent1 channel

- **P1**: `agent_channel/product_recommender.py:280-295` `_template_pitch()` 返 "匹配度较高" · 无 industry/scale/signal 锚点
- **P1**: `agent_channel/sse_extras.py:540-585` `_PRODUCT_DB` intro 留空 "见银行产品手册"
- **P3**: `agent_channel/realtime_stream.py:1018-1046` user_prompt 透传 industry/geo/scale/similarity OK · 但 evidence_dimensions (BE1 annotate) 权重/分数没传 LLM
- **P2**: `agent_channel/prompts.py:89-93` `PITCH_FEWSHOT_EXAMPLES` 仅 1 对自动生成 · 应 3-5 对真行业案例 (制造业中标 / 新能源专精特新 / 化工设备贷)
- ✅ Q-041 4 字段 (industry/geo/scale/similarity) 已实装 per `sse_extras.py:256-257`

### Agent3 credit

- **P1+P4**: `agent_credit/advisor_formatter.py:329-344, 431-447` `_template_reason_corporate()` 四维评分仅返 "财务 X / 行业 X / 经营 X / 担保 X" · 无 "流动比率 1.8 vs 同业 1.5 健康" 等 dimension-specific
- **P4**: `agent_credit/advisor_formatter.py:487-495` `_summarize_cases()` 仅 "(相似度 X% / 通过)" · 无 industry/scale/risk_profile dimension breakdown
- **P1**: `agent_credit/advisor_formatter.py:287-293` red-line `_template_redline` 缺 `policy_text` quote
- **P2**: `agent_credit/prompts.py:139` `FEW_SHOT_EXAMPLES = []` default · `LIUYE_FEWSHOT_POC_ENABLED` defaults "0" · 双重 disabled
- **风险**: `decision_engine.py:181-205` ledger 无 quality gate · template fallback decision_reason 也写入 ledger

### Agent4 alert

- **P1**: `agent_alert/alert_engine.py:163, 208, 276` "需关注 X" 系列 · passive watchlist marker 无 RM action
- **P3**: `agent_alert/scan_engine.py:290-296` `_llm_disposition()` user_prompt 没塞 `evidences[].freshness_score` / `source_confidence` (signal_quality.py 算了 BE5 没用)
- **P2**: `agent_alert/disposition.py:127-135` 模板缺 real case 注释
- **新增需求**: disposition 缺 `follow_up_milestones: [{stage, days_from_today, responsible, condition}]`
- ✅ DISPOSITION_TEMPLATES 5 类 × 3 级 = 13 entries 在 disposition.py:40-125 · 已 concrete

### Agent5 compliance

- **P2**: `agent_compliance/scan_engine.py:191-197` `REVISION_SYSTEM` 缺 real 政策违规处置 case
- **业务化缺**: `agent_compliance/violation_schema.py:189-219` `_FIELD_LABEL_MAP` 缺 regulatory bucket (准入/KYC/风偏/审查清单/SOP) · `derive_conflict_field()` 默认返 "合规阈值" 不进 desk routing
- **P1**: `agent_compliance/scan_engine.py:572-584` `_template_revisions` 兜底 "修改相关业务条款"
- **新增需求**: revision schema 加 `disposition: 暂停|冻结|强制整改|监测|风险提示` enum
- ✅ `policy_excerpt` + `clause_text_hash` 红线 #8 已强 enforce per `violation_schema.py:147-160`
- ✅ B.3.4 Bug D fix (commit `623f895`) verified · `policy_excerpt`/`business_excerpt` 全链路通

### Agent6 report (v16)

- **P5 段路由缺**: `v16_op_handlers.py:467-477` 财务三段式约束在 `_REWRITE_SYSTEM_PROMPT` · 但无段路由识别 · 通用 REWRITE 一锅煮
- **行业卡片缺**: `v16_op_handlers.py:520-545` `_build_material_summary_for_rewrite()` 仅含 financial_block + facts + raw_statements · 无 industry_cards / policy_cards 注入 (`material_anchor.py` / `industry_benchmark.py` 在但没接 v16)
- **QC 闸过宽**: `quality_scorer.py:26-55` 合格线 75/100 · 财务深度 < 7 / 数据一致性 < 6 / 缺材料标注 < 5 仍 pass · 应 `fatal_fail`
- **P2**: `section_generator.py:185-200` `_STYLE_REFERENCE` 仅 2 框架样本 · 缺财务/行业/担保真样本
- **担保无 handler**: v16 无担保章节专用 handler · 通用 REWRITE 处理

### Agent2 riskctrl

- **P4**: `agent_riskctrl/metrics.py:285-289` KS interpretation 返 "策略区分能力较强 · 建议优化" · 无 benchmark range / vs-baseline delta
- **新增需求**: `agent_riskctrl/api.py:254-262` `dsl_gen` schema_hint 缺 `strategy_intent_mapping` 字段 (诉求→rule logic 显式映射)
- **新增需求**: `agent_riskctrl/api.py:512-518` ks_panel 缺 interpretation layer (`benchmark_range: [0.35, 0.50]` · `vs_baseline: "+0.07"`)
- **新增需求**: `agent_riskctrl/backtesting.py:434` samples 三档缺 `concentration` drilldown ("拒绝集中在制造业 · 占拒绝总量 62%")
- **P2**: `agent_riskctrl/api.py:254-260` rule_parse prompt 无 few-shot real 策略案例
- ✅ `MAX_ROWS=50000` 确认 per `backtesting.py:25` (Q-040 fix)

---

## 跨 Agent 共用机制 (已落地 · 不重复造)

| 机制 | 位置 | 状态 |
|---|---|---|
| 8 段 SSOT prompt builder | `shared/prompts/contract.py` + `agent_helpers.py` | safety + evidence-first (含 freshness Track D) 已实装 · 其他 6 段 PENDING |
| LLM caller (PIPL fallback) | `shared/llm_caller/` | 6 agent 已迁 (caller 3 + 5 done · caller 4 report 待) |
| decision_ledger | `shared/decision_ledger/` BE7 | 6 agent 写 ledger · 但无 quality gate (audit P1 风险) |
| signal_quality (freshness + source) | `shared/evidence_freshness.py` + `agent_alert/signal_quality.py` | 算了 · LLM prompt 没消费 (P3) |

---

## prompt tune 工作量预估 (per agent)

| Agent | 改文件数 | 改 LOC | 优先级 |
|---|---|---|---|
| channel | 3 (prompts.py · product_recommender.py · sse_extras.py · realtime_stream.py) | ~80 | 高 (RM 直接读 pitch) |
| credit | 2 (advisor_formatter.py · prompts.py) | ~120 | 高 (审贷员决策依据) |
| alert | 3 (alert_engine.py · disposition.py · scan_engine.py) | ~70 | 中 (内部 RM 看) |
| compliance | 3 (scan_engine.py · violation_schema.py · prompts.py) | ~100 | 中 (合规官看) |
| report | 3 (v16_op_handlers.py · quality_scorer.py · section_generator.py) | ~150 | 高 (审贷员核心交付物) |
| riskctrl | 4 (api.py · metrics.py · backtesting.py · prompts.py) | ~100 | 中 (风险经理看) |

**共 ~620 LOC** · 6 commit · 估 2-3 day · per CLAUDE.md "commit 粒度 = TaskCreate 粒度"。

---

## PB#2 governance 合规自查 (`docs/contracts/pb2-prompt-governance.md`)

| Codex 7 守则 | 本次 tune 触动 | 合规 |
|---|---|---|
| #1 prompt 只保留任务/schema/拒答边界/证据 | 加 4 字段/财行经担/disposition enum (都是 schema · 不是阈值) | ✅ |
| #2 阈值/权重/排序移 Python | benchmark_range / freshness SLA / QC fatal_fail 都在 Python | ✅ |
| #3 prompt ≤ 220 行 | 新增 few-shot ~30 行/agent · 现 prompts.py ~150 行 → 总 ~180 行 | ✅ |
| #4 禁多条件决策树 | disposition enum 在 schema · category 推断在 Python | ✅ |
| #5 输出 schema 化 | violation_schema + GenResult + RuleSet 都 Pydantic enforce | ✅ |
| #6 加规则配 1 fail case | data/eval/real_scenario_cases.jsonl 现 10 case · 每 tune 补 1 fail case | 待补 |
| #7 同义规则合并 | tune 加 vocab + few-shot · 不加重复约束 | ✅ |

**风险**: 守则 #6 需在每 tune commit 同步补 fail case (jsonl entry) · 不补则 review 阻断。

---

## 下一步 (本 audit 后)

1. Task #2 · 写 `docs/contracts/agent-output-rubric-2026-05-11.md` (per agent pass-fail · 1-5 Likert)
2. Tasks #3-#9 · 6 agent prompt tune (per audit 真痛 · 每 agent 独立 commit + fail case)
3. Task #10 · admin 真号 6 助手 E2E verify (按 rubric 1-5 评分 · ≥ 4 平均)
4. Final · WORKER-SLO-4-OUTPUT-QUALITY-READY-FOR-MERGE 信号 + 4 artifacts
