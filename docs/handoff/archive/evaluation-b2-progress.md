# Evaluation · Batch 2 Progress Tracker

**Worker**: evaluation (`feat/evaluation`)
**Batch**: Product Hardening · Batch 2 (真基线重跑 + EV-12 + Agent1/5 精度召回)
**Onboarding**: `docs/onboarding/batch-2-evaluation-real-baseline.md`
**Kickoff Signal**: `BATCH-2-DISPATCHED` (upstream `e68f28e`)
**Resume 日**: 2026-04-24

---

## Task 状态

| # | Task | 工作量 | 完成 Signal | 状态 | Commit |
|---|---|---|---|---|---|
| A | 6 Agent 真 baseline 重跑 (DP001-005 + channel-kb + compliance-kb) | L · 2d | `BASELINE-REAL-DONE` | ✅ done | `21180bf` |
| B | EV-12 跨 Agent 财务比率一致率 (cross_agent/ratio_consistency) | M · 1.5d | `EV-12-RATIO-CONSISTENCY-DONE` | ✅ done | `60fd682` |
| C | Agent1/5 precision@10 / recall@10 / coverage / FPR stub | S · 0.5d | `AGENT1-5-METRICS-DONE` | ✅ done | `0b7e913` |
| 末 | 整批 review 触达 | — | `READY-FOR-EVALUATION-B2-REVIEW` | 🟡 in-progress | (本 commit) |

---

## 对比 2026-04-24 首轮 · 交付数字

| 维度 | B1 (2026-04-24) | B2 (2026-04-26) | delta |
|---|---|---|---|
| 实算 slot 总数 | 20/60 | **39/60** | +19 (+95% lift) |
| pending slot | 40/60 | 21/60 | −19 |
| verdict 分布 | PASS 1 / PARTIAL 4 / FAIL 1 | PASS 1 / PARTIAL 4 / FAIL 1 | 不变 (report 仍 FAIL, 但 FAIL 原因从"骨架自比伪阳" 变成"真 v16 QC evidence_rate=0.33 真实 gap") |
| agent1 real count | 0/10 | 8/10 | +8 (channel-kb seed + MockSearchProvider 真搜) |
| agent5 real count | 0/10 | 6/10 | +6 (compliance-kb 169 SOP + synthesized new-policy 冲突扫描) |
| agent6 real count | 3/10 | 6/10 | +3 (5 DP v16 聚合, qc.score 68.3-69.4 真实) |
| EV-12 ratio_calc_consistency | pending | **1.0 (20/20 match)** | 新解锁 · blocker_threshold=0.99 通过 |
| agent3/6 ratio_* blocker_threshold | 0.95 | 0.99 | 收紧 (onboarding spec) |
| 偏乐观警示段 | 含 | 移除 | ✅ |
| 首轮高估幅度结论段 | 无 | 含 (Agent6/1/5/3 逐条) | ✅ |

---

## 关键产物

- `evaluation/baselines/2026-04-26-real-run.json` · 6 Agent × 10 metric 汇总 + EV-12 顶层字段
- `evaluation/baselines/2026-04-26-real-run.md` · 人读版 (含对比表 37 项 + 高估结论 + EV-12 段)
- `evaluation/scripts/build_real_baseline.py` · 主编排驱动 (可重复执行)
- `evaluation/scripts/produce_agent1_dump.py` / `produce_agent5_dump.py` · runtime dump 生成器
- `evaluation/manual/1_latest.json` (51 candidates) / `5_latest.json` (20 conflicts)
- `evaluation/runner/cross_agent/ratio_consistency.py` · EV-12 实现
- `evaluation/runner/tests/test_ratio_consistency.py` · 4 case 单测全 OK
- `outputs/v16_DP001..DP005/v16_pipeline_summary.json` · 5 家真 v16 产出 (gitignored)

---

## 降级说明 (onboarding 明确允许 · 已在 baseline MD 标注)

- **LLM DEEPSEEK_API_KEY auto-load**: 项目根 `.env` 需 `set -a; source .env; set +a` 显式注入; `scripts/start_uvicorn.py` wrapper 模式外的直调需手动加载. 本 batch 用 `set -a` 显式注入执行 v16 pipeline 5 DP 全部正常.
- **Tavily 外搜不可用**: agent1 走 MockSearchProvider (demo_data/mock_pool · 100 家), agent5 外部新政策走 inline synthesized stub (6 条). 真接外源待 Phase 2 Tavily / 银保监 API.
- **code-arch Batch 2 oracle 未到**: Task C 的 agent1 portrait_match_precision / agent5 policy_coverage + conflict_recall 走 stub_awaiting_code_arch_b2 分支 (precision=0.5 / recall=0.5 / coverage=0.5 / fpr=0.2), passed=None 不影响 verdict. 待 `BATCH-2-INTEGRATION-TEST-DONE` 合流后 re-run 自动升级为 deterministic.

---

## 红线合规 (自查)

- ✅ 只动 `evaluation/` 及 `evaluation/baselines/`
- ✅ `v16_*` / `agent_*/` / `data/mock/` / `rubric YAML schema` 全部未动
- ✅ 仅在 yaml 里改 `blocker_threshold` + 文案 (onboarding 允许)
- ✅ `financial_analyzer` 只读消费, 双侧独立 `extract_financial_ratios` 不 import 对方
- ✅ 每 Task 独立 commit 带对应 Signal trailer
- ✅ Final commit 带 `READY-FOR-EVALUATION-B2-REVIEW`

---

## Blocker 记录

**无 blocker 触发**. 过程中遇 DEEPSEEK_API_KEY 未自动加载 → 非 env 失败, 是 llm.py 默认不 auto-load .env, 用 `set -a; source .env; set +a` 显式注入即可, 未升 blocker.

---

## 等待 main CLI

- review `2026-04-26-real-run.{json,md}` 的数字与叙事
- review EV-12 "双 None 即架构一致" 的判定 (可能需要用户裁决: mock xlsx 形态不兼容 FinancialAnalyzer 是否算 data-foundation B2 的坑, 由主 CLI 协调)
- APPROVE 后合流 `feat/evaluation` → `chore/l0-infra`
