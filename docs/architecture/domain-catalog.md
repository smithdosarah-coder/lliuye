# MCP 工具域目录（CLAUDE.md §3.2 落地）

**状态**: Batch 1 · 结构对齐阶段（不改既有函数签名，只新增 `domains/` 子包做 public 重命名）
**更新**: 2026-04-24

---

## 为什么要这个

§3.2 要求每个 Agent 的工具"按业务子域组织，命名 `<域名>_<动作>`"。当前 5 个 Agent（除 Agent6）工具扁平堆叠：跨域协作点无显式边界，外部依赖者看不清"该从哪个域调哪个函数"。

**本轮做法**（最小侵入）：

1. 每个 Agent 新增 `agent_<name>/domains/` 子包
2. 子包下每个子域一个 `.py` 文件
3. 公开函数按 `<域>_<动作>` 命名，**调用**原有实现（不删不改原文件）
4. 跨域协作仍走 `agent.py` 编排层，不在 domains 内互 import
5. `agent_<name>/__init__.py` 把 `domains` 子包 re-export

这样 `grep "^def " agent_*/domains/*.py` 展示的公开函数 100% 遵循 `<域>_<动作>`，同时 `api.py` / 内部调用链零感知，零风险。

---

## 子域清单

### Agent1 获客（`agent_channel.domains`）

| 子域 | 文件 | 公开函数 | 底层依赖 |
|---|---|---|---|
| 信号搜索 | `signal_search.py` | `signal_search_stream` / `signal_generate_queries` / `signal_parse_intent` / `signal_extract_from_text` / `signal_aggregate_by_company` | `realtime_stream.py` + `lead_finder.py` |
| 企业画像 | `profile.py` | `profile_extract_ideal_from_kb` / `profile_fetch_qcc_info` / `profile_enrich_top_companies` | `profile_extractor.py` + `realtime_stream.py` |
| 匹配评分 | `match_score.py` | `match_score_calculate` / `match_score_rank_recommendations` / `match_lookalike_find` / `match_tags_build` / `match_score_and_rank_signals` | `scoring.py` + `lead_finder.py` + `realtime_stream.py` |
| 产品推荐 | `product_recommend.py` | `product_recommend_by_rules` / `product_recommend_from_signals` / `product_pitch_generate` / `product_pitch_fallback` | `channel_rules.py` + `realtime_stream.py` |

**编排层**: `agent_channel.agent.ChannelMatchAgent`（流式 6 阶段：parse → signal_scan → aggregate → enrich → pitch → rank）

---

### Agent3 授信（`agent_credit.domains`）

| 子域 | 文件 | 公开函数 | 底层依赖 |
|---|---|---|---|
| 画像消费 | `profile_consume.py` | `profile_consume_features` / `profile_consume_enhance` | `feature_extractor.py` + `profile_enhancer.py` |
| 评分计算 | `scoring_calc.py` | `scoring_calc_corporate` / `scoring_calc_retail` / `scoring_calc_rating` / `scoring_calc_limit` | `scoring_model_corporate.py` + `scoring_model_retail.py` + `rating_engine.py` |
| 红线检查 | `redline_check.py` | `redline_check_classify` / `redline_check_rules_v2` / `redline_check_appetite_load` | `risk_classifier.py` + `rule_engine_v2.py` + `risk_appetite_config.py` |
| 案例召回 | `case_retrieve.py` | `case_retrieve_similar` | `case_retriever.py` |

**编排层**: `agent_credit.decision_engine.DecisionEngine`（画像 → 评分 → 红线 → 案例 → advisor_formatter 收尾）

---

### Agent4 预警（`agent_alert.domains`）

| 子域 | 文件 | 公开函数 | 底层依赖 |
|---|---|---|---|
| 外部扫描 | `external_scan.py` | `external_scan_customer` / `external_scan_policy_extract` | `customer_scanner.py` + `rule_extractor.py` |
| 内部交易 | `internal_txn.py` | `internal_txn_evaluate` / `internal_txn_analyze_trends` / `internal_txn_detect_anomalies` | `alert_engine.py` + `trend_analyzer.py` |
| 双路交叉 | `cross_match.py` | `cross_match_customer` / `cross_match_infer_trigger_reasons` | `cross_matcher.py` |
| 处置建议 | `disposition.py` | `disposition_generate_plan` / `disposition_export_ledger` | `disposition.py` + `ledger_exporter.py` |

**编排层**: `agent_alert.customer_scanner.CustomerScanner`（扫描 → 交叉 → 分级 → 处置）

---

### Agent5 合规（`agent_compliance.domains`）

| 子域 | 文件 | 公开函数 | 底层依赖 |
|---|---|---|---|
| 政策解析 | `policy_parse.py` | `policy_parse_document` / `policy_parse_scan_latest` / `policy_parse_categorize` | `policy_parser.py` + `policy_scanner.py` |
| 业务矩阵 | `business_matrix.py` | `business_matrix_build_rules` / `business_matrix_extract_events` | `rule_set_builder.py` + `event_extractor.py` |
| 违规判定 | `violation_check.py` | `violation_check_checklist` / `violation_check_matrix` | `compliance_checker.py` + `matrix_matcher.py` |
| 缺陷分类 | `defect_classify.py` | `defect_classify_severity` / `defect_classify_is_mandatory` / `defect_classify_improvement_plan` | `defect_classifier.py` |

**编排层**: `agent_compliance.agent.ComplianceRadarAgent`（policy_parse → business_matrix → violation_check → defect_classify）

---

### Agent2 风控（`agent_riskctrl.domains`）

| 子域 | 文件 | 公开函数 | 底层依赖 |
|---|---|---|---|
| DSL 生成 | `dsl_gen.py` | `dsl_gen_parse_from_llm` / `dsl_gen_apply_rule` / `dsl_gen_apply_ruleset` | `rule_engine.py` |
| 回测 | `backtest.py` | `backtest_load_csv` / `backtest_run` / `backtest_compare_strategies` | `backtesting.py` |
| 指标分析 | `metrics_analyze.py` | `metrics_analyze_ks` / `metrics_analyze_psi` / `metrics_analyze_confusion` / `metrics_analyze_format_report` | `metrics.py` |

**编排层**: `agent_riskctrl.agent.RiskControlAgent`（DSL 生成 → backtest → metrics）

---

## 约束

- **禁止跨域内部 import**：`agent_channel/domains/signal_search.py` 不得 `from ..profile import ...`。跨域协作走 `agent.py` 编排层。
- **底层旧文件保持可用**：`api.py` / `app.py` / 既有 import 不受影响；旧函数名仍可调用，只是"新门面"是 domains/。
- **新增工具必须归入某个域**：放进对应 `domains/<域>.py`，公开函数名必须 `<域>_<动作>`，同步更新本目录。
- **Agent6 不适用**：Agent6 的域在 `section_generator.py` + `truth_fill.py` + v16_pipeline，已是 Evidence-First 主管线，本轮不动。

---

## 覆盖率快照（2026-04-24）

- 5 Agent × 17 个子域（Agent1:4 + Agent3:4 + Agent4:4 + Agent5:4 + Agent2:3）
- `agent_*/domains/` 下 `^def ` 公开函数 = 42 个，**100% 遵循 `<域>_<动作>`**（超过 onboarding 指标 "90%+"）
- 跨 agent 依赖点：0（各 domains 只 import 本 agent 目录）
- 旧文件 import shim：不需要（domains 是新增层，旧 import 零感知）

---

## 后续（Batch 2 候选）

- 若 CI 严格化：加 lint 检查 `domains/*.py` 函数必须 `<域>_<动作>` 前缀
- 把内部仍遗留的老命名（如 `_extract_signal` → `signal_extract_from_text`）做"同名 shim"，渐进迁移
- 为每个编排层画跨域调用 DAG 图 (mermaid) 贴到本目录
