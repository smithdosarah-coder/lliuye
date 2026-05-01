# Agent3 Decision Graph · v1.0 (Phase B-3 · BE2 · 2026-05-01)

> **Source**: `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE2 + `two-way-debate-backend-r1-codex-2026-05-01.md` §3.2
> **Pain root**: 审贷员痛 1.2.1 + 1.2.4 — AI 评分黑盒 + 缺同业对标可复核链
> **Codex verdict**: "后端真痛不是 ML · 是审贷员缺可复核 evidence graph" (R1 §5)
> **Owner**: worker-B4-credit (`feat/phase-b4-credit`)
> **Tier**: 1 · per CLAUDE.md §15 instruction SSOT

---

## 0. Why this exists

> 审贷员痛 verbatim (Codex R1 §2): "Agent3 评分主体是确定性评分卡 + 红线 · 方向对 · 痛点不是加 ML · 而是 evidence 链和可复核性 · 当前 LLM 只包装理由"

decision graph 是 **审贷员可复核证据图** · 它解释:

1. **每个数字哪来** — 财务比率 / 评分维度 / 红线判定 / 同业对标 → 上游 source + version
2. **每个结论谁导致** — 哪条 rule_hit / 哪个 score_dimension / 哪个 peer_gap 推到了最终决策
3. **同业差距在哪** — `scoring_model_corporate.py:215-240` 已计算 `industry_peer_gap` 但**未挂入可复核链** · 本 graph 把 peer_gap 显式建模为 evidence 节点

不是替换 4 步确定性评分 (decision_engine.py 1-114) · **是上层 wrapper** · 现有 `DecisionAdvice` 字段全保留 · 只新增 `decision_graph` 字段。

---

## 1. Schema (top-level)

```jsonc
{
  "schema_version": "1.0.0",          // 本契约版本 · breaking change 必涨 major
  "engine": "agent3.decision_engine",
  "engine_version": "v3.1",            // 与 PRD Agent3 v3.1 对齐
  "appetite": {
    "segment": "corporate",            // corporate | retail
    "version": "default-2026-04",      // risk_appetite_default.json 内嵌 version · 客户自定义走 client_id
    "client_id": ""                    // 空 = 默认偏好
  },
  "subject_name": "鼎盛商贸有限公司",
  "segment": "corporate",
  "built_at": "2026-05-01T10:30:00",
  "decision_summary": {                // 与 DecisionAdvice 顶部字段同步 · 便于不展开 nodes 也能看一眼
    "decision": "拒绝",
    "approved_amount": 0,
    "approved_term_months": 0,
    "interest_rate": 0,
    "rate_benchmark": "—",
    "risk_grade": "D",
    "composite_score": 38
  },
  "nodes": [ /* 见 §2 */ ],
  "edges": [ /* 见 §3 */ ],
  "peer_gap_summary": {                // 同业对标快照 · 4 关键比率 · 来源 industry_baselines_v2.json
    // key naming 与 CorporateScoringResult.industry_peer_gap (scoring_model_corporate.py:215-223) 保持一致 · 前端可复用同一 dict key
    "debt_ratio_gap": 0.23,
    "net_margin_gap": -0.02,
    "revenue_growth_gap": -0.13,
    "ar_turnover_gap": 30                // metric=ar_turnover_days · 但 summary key 沿用历史名 ar_turnover_gap
  },
  "missing_evidence": []               // 关键证据缺失列表 · 字段名 · 例 ["industry.code"] (无法 peer-compare)
}
```

---

## 2. Node types (7 类)

| type | id 命名 | 必含字段 | 来源 source 范例 |
|---|---|---|---|
| `feature` | `feature::<dot.path>` | `key`, `value`, `source` | `feature_extractor.py::_extract_corporate` |
| `rule` | `rule::<rule_id>` | `rule_id`, `rule_name`, `threshold`, `operator`, `severity`, `version`, `source` | `red_line_rules_corporate.json#corp_rl_003` (+ appetite override marker) |
| `rule_hit` | `rule_hit::<rule_id>` | `rule_id`, `actual`, `threshold`, `severity`, `can_waive`, `description` | 由 `RuleEngineV2.check` 命中产生 |
| `peer_benchmark` | `peer_benchmark::<industry_code>::<metric>` | `industry_code`, `metric`, `value`, `source` | `industry_baselines_v2.json#I65#debt_ratio_median` |
| `peer_gap` | `peer_gap::<metric>` | `metric`, `feature_value`, `peer_value`, `gap`, `direction`, `interpretation` | 派生 (feature - peer_benchmark) |
| `score_dimension` | `score::<dimension>` | `dimension`, `score`, `weight`, `weighted`, `source` (+ `sub_scores` for corporate) | `scoring_model_corporate.py::_score_financial` |
| `decision` | `decision::final` | `decision`, `approved_amount`, `risk_grade`, `rationale_anchor` | `advisor_formatter.py::_decide_corporate` |

**source 字段强约束**: 必须可定位到 file:method (例 `scoring_model_corporate.py::_score_financial`) 或 file:json_path (例 `red_line_rules_corporate.json#corp_rl_003`) · 不允许空字符串 · 不允许 `unknown`。

**version 字段** (rule node 必填): 格式 `<engine_version>+<appetite_marker>` · 例 `v3.1+default` 或 `v3.1+client_xx_2026-05` · appetite override 时必须含 client_id 标记。

---

## 3. Edge types (6 类)

| type | from → to | 语义 |
|---|---|---|
| `triggered` | `feature::*` → `rule_hit::*` | 该 feature 值触发了该 rule_hit |
| `threshold_of` | `rule::*` → `rule_hit::*` | 该 rule 定义了 rule_hit 的阈值 |
| `compared_to` | `feature::*` ↔ `peer_benchmark::*` ↔ `peer_gap::*` | 三角关系 · feature 对标 benchmark 派生 gap |
| `derived_from` | `feature::*` → `score_dimension::*` | 该 score 由该 feature 派生 |
| `caused` | `rule_hit::*` → `decision::final` | 红线命中导致最终决策 (e.g. red severity → 拒绝) |
| `evidenced_by` | `score_dimension::*` → `decision::final` | 评分维度作为决策的 evidence |

**Edge 字典序**: 同 from→to 重复的 edge 必须 dedup · graph builder 内 set 去重。

---

## 4. peer_gap evidence linkage (BE2 核心补丁)

`scoring_model_corporate.py:215-240` 已有 `industry_peer_gap` 字段:

```python
peer_gap = {
    "debt_ratio_gap": features["financial.debt_ratio"] - features["industry.debt_ratio_median"],
    "net_margin_gap": ...,
    "revenue_growth_gap": ...,
    "ar_turnover_gap": ...,
}
```

**痛点**: 这 4 个 gap 数值塞在 `CorporateScoringResult.industry_peer_gap` dict 里 · 前端可见 · 但**没有上游可复核链** · 审贷员看到 "debt_ratio_gap = 0.23" 不知道:
- feature 0.78 哪来? → 已有 `_financial_prompt_block` (financial_analyzer evidence) · graph 内挂 `feature::financial.debt_ratio` 节点 source 指 `feature_extractor.py::_anchors_to_indicators`
- peer median 0.55 哪来? → graph 内挂 `peer_benchmark::I65::debt_ratio_median` 节点 source 指 `industry_baselines_v2.json#I65#debt_ratio_median`
- 0.23 是 gap 还是绝对值? → graph 内挂 `peer_gap::debt_ratio` 节点 含 `direction: "above_peer"` + `interpretation: "高于同业中位 23pp"`

**4 关键 metric 必建** (corporate · retail 因 industry_peer_gap 不存在 · 当前 v1.0 仅 corporate):
- `debt_ratio` · 越大越坏 (above_peer 是负面)
- `net_margin` · 越大越好 (above_peer 是正面)
- `revenue_growth` · 越大越好
- `ar_turnover_days` · 越小越好 (above_peer 是负面)

**direction 取值**:
- `above_peer` (feature > peer_value)
- `below_peer` (feature < peer_value)
- `equal_to_peer` (差值 < 0.001 或 < 1 day for ar_turnover)
- `peer_unknown` (industry baseline 缺该 metric · 节点仍建 + missing_evidence 标 industry_code)

---

## 5. Builder API (agent_credit/decision_graph.py)

```python
from agent_credit.decision_graph import build_decision_graph, DecisionGraph

graph: DecisionGraph = build_decision_graph(
    features=features_snapshot,        # advisor_formatter.features_snapshot (已剔 _ 前缀)
    scoring=scoring_result,            # CorporateScoringResult | RetailScoringResult
    rule_hits=rule_hits,               # list[RedLineHit]
    advice=advice,                     # DecisionAdvice (本身不依赖 decision_graph 字段)
    segment="corporate",
    appetite=appetite,                 # RiskAppetiteConfig
    baselines=load_industry_baselines(),  # dict (per industry_baselines_v2.json)
)

graph.to_dict()                        # → 上文 §1 schema
```

**调用点**: `DecisionEngine.run_stream()` 在 `advising_done` 之后、`all_done` 之前新增 stage:

```python
yield "graph_building", None
graph = build_decision_graph(...)
advice.decision_graph = graph.to_dict()
yield "graph_done", graph.to_dict()
yield "all_done", DecisionPipelineResult(...)
```

**mock 路径影响**: 0 · `_mock_decision_events()` 直接 yield dict · 不走 advisor_formatter · graph 通过单独的 fixture 字段塞入 (per §6)。

---

## 6. Mock fixture extension

`data/mock/workspace/credit/scenarios/<scenario_id>.json` 可选 `decision_graph` 字段:

```jsonc
{
  // ... 现有字段全保留 ...
  "decision_graph": {                  // 可选 · 缺失时不影响现有流
    "schema_version": "1.0.0",
    "engine": "agent3.decision_engine",
    "engine_version": "v3.1",
    "appetite": {"segment": "corporate", "version": "default-2026-04", "client_id": ""},
    // ... 同 §1 schema ...
  }
}
```

**done envelope 变化**: `_build_done_envelope` 新增 `decision_graph` 字段 · 缺时输出 `null`。

---

## 7. Boundaries · 不动 · 不引入

- ❌ **不引入 ML / embedding / similarity model** — Codex R1 verdict "都是手段不是目的" · graph 是结构化 evidence chain · 全确定性
- ❌ **不修改 4 步确定性评分** — `decision_engine.py:95-115` 流水线一字不动 · graph 在 `advising_done` 之后追加 stage
- ❌ **不破现有 DecisionAdvice 字段** — `decision_graph` 是新增字段 · 默认空 dict · 现有消费者 (export_docx / writeback) 不受影响
- ❌ **不破 mock 路径** — Stage 5a smoke 验过 · graph 是可选字段 · `_build_done_envelope` 缺时 fallback null
- ❌ **不引入 LLM 调用** — graph 全确定性构建 · 不调 caller / 不写 prompt
- ❌ **不写关键词黑名单** — interpretation 文案模板化 (per §4 direction 映射 · 4 行 if-else)

---

## 8. Versioning

- `schema_version` (本 doc top-level) — 契约版本 · breaking 涨 major · 加字段涨 minor · 改文档涨 patch
- `engine_version` (decision_graph 内) — Agent3 PRD 版本号
- `appetite.version` — risk_appetite JSON 内 `version` 键 (default `"default-2026-04"`) + `client_id` 区分自定义偏好

升级 schema 时 · `decision_graph.SCHEMA_VERSION` 常量同步改 · tests/agent_credit/test_decision_graph.py::test_schema_version_pinned 守。

---

## 9. Done criteria (本 worker)

- [ ] `agent_credit/decision_graph.py` 实装 builder · 7 node type + 6 edge type 全覆盖
- [ ] `agent_credit/advisor_formatter.py:DecisionAdvice` 加 `decision_graph: dict = field(default_factory=dict)` 字段
- [ ] `agent_credit/decision_engine.py:run_stream()` 在 advising_done 后新增 graph_building / graph_done stage
- [ ] `agent_credit/api.py:_build_done_envelope` + `_mock_decision_events` 含 `decision_graph` 输出
- [ ] `data/mock/workspace/credit/scenarios/corp-dingsheng-001.json` 加 `decision_graph` 字段 (demo 用)
- [ ] `tests/agent_credit/test_decision_graph.py` 单元测试覆盖: schema invariants / peer_gap nodes / rule-hit linkage / threshold + version recorded / snapshot stability / fixture load
- [ ] 不破 `tests/test_credit_financial_parity.py` (现有 3 测试)
- [ ] commit trailer per Q-043: `REVIEW-MODE` + `REASONING-EFFORT` + `ELAPSED`
- [ ] DONE signal `WORKER-B4-CREDIT-DECISION-GRAPH-DONE`
