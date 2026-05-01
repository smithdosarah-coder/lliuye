# Agent6 · Material Gap Graph + Cross-Section Coherence · v1.0

> **Source**: Phase B Sprint 1 · BE3 P0 必做 · 解 RM + 审贷员痛 1.2.3 (报告章节不一致 + 缺材料闭环)
> **Owner**: worker-B4-report (Phase B Sprint 1 · 4 of 4)
> **Status**: spec only · v1.0 (Sprint 1 scaffold · partial section run 留 Phase B-3 fix-forward)
> **Sibling specs**: `agent-report-spec.md` (主 spec · v16 主管线) · `agent-handoff-schemas.md` §6.2 (反向链 Agent3→Agent6) · `agent-credit-spec.md` (BE2 decision graph)
> **依据**: `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE3 + `docs/onboarding/B4-report.md` 6 件交付
> **不破**: v16 pipeline (`v16_pipeline.run_pipeline` 签名) · `quality_blocker.check_financial_consistency` 内部 anchor 逻辑 · `pending_questions` 既有形态 · v16 mock 路径

---

## 1. 设计目标

把 v16 主管线 (classifier→generator→QC) 的 **隐式 pending_questions list** 升级为 **显式 material→section→scoring_dimension graph** · 让 RM + 审贷员看到:

- 哪份材料缺 → 影响哪些 section → 影响 Agent3 哪个评分维度 (impact_magnitude 0-100)
- 跨章节同字段数字是否一致 (现 `quality_blocker` 只比对 anchor · 不跨章节)
- Agent3 评分发现报告缺章节 → 反向回报告补章节 (per `agent-handoff-schemas.md` §6.2)

**红线**: 不引 ML / 不引 LLM 现场算 (per `CLAUDE.md` §3.1 确定性计算) · 全规则引擎 + JSON 配置驱动。

---

## 2. MaterialGapGraph Schema (核心数据结构)

### 2.1 顶层

```jsonc
{
  "graph_version": "1.0",
  "report_id": "<uuid>",
  "generated_at": "2026-05-01T03:00:00+08:00",
  "nodes": [/* §2.2 */],
  "edges": [/* §2.3 */],
  "summary": {
    "missing_material_count": 3,
    "blocking_section_count": 1,
    "advisory_section_count": 2,
    "max_score_impact": 18,           // 总评分预期下行 magnitude (0-100 累计上限)
    "affected_scoring_dimensions": ["operation_stability", "industry_position"]
  }
}
```

### 2.2 Nodes (3 类型 · 不可扩散)

| `type` | `id` 命名 | 必填字段 | 说明 |
|---|---|---|---|
| `material` | `<material_kb_key>` (e.g. `supplier_concentration` / `revenue_breakdown_by_product`) | `id` · `name` (中文显示名) · `status` (`present` / `partial` / `missing`) · `kb_path` (现有 `material_kb` 内的 key 路径 · 如 `manage.upstream.top5_supplier_share`) | 材料维度 · 与 `material_kb.py` 字段命名 align |
| `section` | `chapter_<n>_<name>` (e.g. `chapter_2_operation`) | `id` · `name` (e.g. "二、经营情况") · `status` (`done` / `pending` / `partial`) | 与 `v16_runner._CHAPTER_HEADINGS` 4 章映射一致 |
| `scoring_dimension` | `<rubric_dim_id>` (e.g. `operation_stability` / `industry_position` / `financial_health`) | `id` · `name` (e.g. "经营稳定性") · `agent` (恒为 `"credit"` · 即 Agent3) | 与 BE2 `agent-credit-spec.md` decision graph rubric_dim 字段命名 align |

**规则**:
- `material.id` 取自 `material_kb` 的稳定 key (不漂移)
- `section.id` 与 v16 输出 docx 4 章锚点 (`chapter_1_background` / `chapter_2_operation` / `chapter_3_finance` / `chapter_4_conclusion`) 一致
- `scoring_dimension.id` 与 `agent_credit/scoring_model_corporate.py` rubric_dim 命名一致 (worker-B4-credit BE2 同 sprint align)

### 2.3 Edges (2 类型)

| `type` | `from` → `to` | 必填字段 | 语义 |
|---|---|---|---|
| `provides` | `material` → `section` | `from_id` · `to_id` · `severity` (`blocking` / `advisory`) · `affected_fields: list[str]` (e.g. `["supply_chain_concentration", "buyer_diversity"]`) | 材料缺 → section 哪些字段无法填 |
| `affects` | `section` → `scoring_dimension` | `from_id` · `to_id` · `impact_magnitude: int` (0-100 · 当 section 缺该字段时对 scoring_dim 评分的预期下行幅度) · `reasoning: str` (短句 · 引规则) | section 字段缺 → scoring_dim 评分受影响 |

**impact_magnitude 计算规则** (确定性 · per §3.1):
- `affected_fields` 数量 / section 总字段数 × 该 section 对该 scoring_dim 的总权重 × 100
- 示例: 若 `chapter_2_operation` 缺 `supply_chain_concentration` 1 字段 (总 8 字段) · 该 section 对 `operation_stability` 权重 0.6 · 则 `impact_magnitude = 1/8 × 0.6 × 100 = 7.5 → round 8`

**配置位置**: `agent_report/material_gap_rules.py` 内 `_MATERIAL_TO_SECTION_RULES` + `_SECTION_TO_DIM_WEIGHTS` 两个 dict (JSON-serializable · 不写代码逻辑)。

### 2.4 fixture 形态 (per 反 5 原则 §3.5 · 不含答案字段)

`data/mock/workspace/report/scenarios/<scenario_id>.json` 加新段:

```jsonc
{
  // ... 既有 fixture 字段不动 (mock_v16_stream done shape)
  "material_gap_graph": {
    "graph_version": "1.0",
    "nodes": [/* ≥3 nodes */],
    "edges": [/* ≥2 edges */],
    "summary": {/* per §2.1 */}
  }
}
```

**3 难度分层** (per `CLAUDE.md` §3.5 反 5 原则):
- `easy_full_materials.json` · 缺 1 份次要材料 (e.g. 缺 "员工花名册" → chapter_1_background 缺 1 字段 → operation_stability 影响 magnitude=3)
- `medium_missing_critical.json` · 缺 3 份关键材料含历史数据 (e.g. 缺 "前五大供应商占比" / "最近 3 年营收明细" / "上下游账期表" → 多 section 多 dim 受影响 · max_score_impact ~18)
- `hard_cross_section_conflict.json` · 跨章节数字冲突 (e.g. 营收章 5000 万 vs 经营章 1 亿) + 缺材料 (引 §3 cross-section coherence 触发 BLOCK)

**绝不预埋答案**: `material_gap_graph` 由 `material_gap.build_graph()` 在 v16 done 时**当场算** · fixture 仅含输入 (材料 status + section status) · graph 是输出 · 单测验"输入相同时输出确定"。

---

## 3. Cross-Section Coherence (quality_blocker 第 5 维)

### 3.1 现状

`agent_report/quality_blocker.py:304-314` 的 `run_blocker(text, financial_anchor, expect_evidence)` 只 4 维:
1. placeholder
2. evidence
3. financial_consistency (anchor 比对 · 仅 `资产负债率/流动比率/速动比率/毛利率/净利率` 5 比率 · 全文级 · 不区分 section)
4. compliance_terms

**Gap**: 跨章节同字段 (e.g. 营收 / 资产 / 员工人数 / 资产负债率) 在 chapter_2 vs chapter_3 出现两次时 · 数字不一致 → 现有 `financial_consistency` 不查 (只管比 anchor) · `quality_scorer.py` 9 维度也不查。

### 3.2 第 5 维 · `cross_section_coherence`

**入口**: `quality_blocker.run_blocker(text, financial_anchor, expect_evidence, sections=None)` 加可选 `sections: list[dict] | None` 参数 (默认 None 向下兼容 · 不传则跳过第 5 维)。

**实现**: `agent_report/cross_section_coherence.py:check_cross_section_coherence(sections, anchor, tolerance_pct=1.0) -> list[BlockerIssue]`

**算法** (确定性 · 不引 LLM):
1. 从 `sections` (4 章 dict list · 每条含 `id` + `content`) 抽数字 token (复用现有 `_AMOUNT_PATTERN` + `_PCT_PATTERN`)
2. 对每章数字 · 按上下文关键词归一到 canonical key (e.g. `营收` → `revenue` · `总资产` → `total_asset` · `员工` → `headcount`)
3. 对每个 canonical key · 跨 section 收集所有提及 (section_id, value, snippet)
4. 同 key 跨 section 数值差 > `tolerance_pct` (默认 1%) → emit `BlockerIssue(dimension="cross_section_coherence", code=f"value_drift:{key}", severity="block")`
5. **Historical** (历史一致性 · v1.0 限定 · v1.1 扩展): 若 `financial_anchor.history` 含同字段历年值 (e.g. `revenue_2024 / revenue_2023`) · 章节内提及历年数据时校验是否与 anchor 一致 · 不一致 → severity="warn"

**Canonical key 表** (固定 dict · `_CANONICAL_KEYWORDS`):
```python
{
    "revenue":     ("营业收入", "营收", "营业额"),
    "total_asset": ("资产总计", "总资产"),
    "net_profit":  ("净利润", "净利"),
    "headcount":   ("员工", "员工人数", "在职"),
    "asset_liability_ratio": ("资产负债率",),
    "current_ratio": ("流动比率",),
    # ... 与 financial_anchor.ratios + amounts_wan key align
}
```

### 3.3 BlockerVerdict 不破

新维度 issue 走既有 `BlockerIssue` dataclass · 无字段扩展。`BlockerVerdict.fail_dimensions` 加新值 `cross_section_coherence` · `to_dict()` 不变。`format_verdict_text` 不动。

**测试**:
- 同 key 跨章节数值一致 → 0 issue
- 跨章节数值偏差 1.5% (> tolerance 1%) → 1 block issue
- `sections=None` (向下兼容) → 跳过第 5 维 · 既有 4 维 verdict 不变

---

## 4. §6.2 Handoff Endpoint · `POST /api/report/section_supplement` (Sprint 1 scaffold)

### 4.1 接 Agent3 反向调用 (per `agent-handoff-schemas.md` §6.2)

**Sprint 1 范围**: scaffold · 接收 + 校验 + 返回 fixture-mode `section_supplement_done` event · **不实装 partial section run** (留 Phase B-3 fix-forward · per Schema §6.7 owner = A4-credit V3 + A4-report V3 双侧)。

### 4.2 Request payload (Pydantic schema)

```python
class SectionSupplementRequest(BaseModel):
    schema_version: Literal["1.0"]
    intent_type: Literal["report_gap_supplement"]
    source_agent: Literal["credit"]
    target_agent: Literal["report"]
    report_id: str                    # Agent6 v16 done 时返的 session_id
    gap_sections: list[str]           # e.g. ["chapter_2_operation", "supplier_concentration"]
    requesting_decision_id: str       # Agent3 评分流的 decision_id
    urgency: Literal["blocking", "advisory"]
```

### 4.3 Response (SSE stream · 与 v16 fill 同 envelope)

```
event: section_supplement_started
data: {"report_id": "...", "gap_sections": [...], "scaffold_mode": true}

event: section_supplement_done
data: {
  "report_id": "...",
  "supplemented_sections": ["chapter_2_operation"],
  "scaffold_mode": true,
  "partial_section_run_pending": "Phase B-3",
  "supplement_status": "scaffold_ack",  // Sprint 1 仅 ack · B-3 改 "ran_partial"
  "next_step": "Agent3 接到后重评 (per §6.2 消费侧约束)"
}
```

**校验规则**:
- `report_id` 在 `session_store` 必存 · 不存在返 404
- `gap_sections` 任意元素必属 `_CHAPTER_HEADINGS` ∪ `material_kb` 已知 key · 否则 422
- `urgency=blocking` 时同步返 done event (HTTP 200 · 阻塞 Agent3) · `advisory` 时异步 fire-and-forget

### 4.4 fixture (Phase B-3 升级时落)

`data/mock/handoff/agent3-to-6-gap.json` (per Schema §6.2 placeholder · v1.1 Sprint 1 仅落 schema · v1.2 fixture 实装在 worker-B7 decision ledger sprint)。

---

## 5. 模块文件结构 (worker-B4-report 新建 + 改)

```
agent_report/
  material_gap.py                  # NEW · build_graph + section_impact + summary
  material_gap_rules.py            # NEW · _MATERIAL_TO_SECTION_RULES + _SECTION_TO_DIM_WEIGHTS dict
  cross_section_coherence.py       # NEW · check_cross_section_coherence + _CANONICAL_KEYWORDS
  handoff_section_supplement.py    # NEW · §6.2 endpoint handler (Sprint 1 scaffold)
  api.py                           # MOD · 加 POST /api/report/section_supplement route + done payload 注 material_gap_graph
  v16_runner.py                    # MOD · _run_v16_in_thread done_payload 加 material_gap_graph 字段 · build_graph 在 audit 阶段调

quality_blocker.py (agent_report/) # MOD · run_blocker 加 sections=None 参数 + 调 check_cross_section_coherence

data/mock/workspace/report/scenarios/
  easy_full_materials.json         # NEW (or MOD existing)
  medium_missing_critical.json     # NEW
  hard_cross_section_conflict.json # NEW

tests/agent_report/
  test_material_gap.py             # NEW · 6 test case 覆盖 graph + impact + cross-section + handoff scaffold

docs/contracts/
  agent-report-material-gap.md     # 本 doc · v1.0
```

---

## 6. 红线 (per onboarding §3 + Codex R2)

- ❌ 不重写 v16 pipeline (classifier→generator→QC 是稳定核心 · material_gap.py 是 audit 阶段后置 wrapper)
- ❌ 不引入 ML
- ❌ 不引 LLM 现场算 material gap / cross-section coherence (per `CLAUDE.md` §3.1)
- ❌ 不破 `pending_questions` 既有形态 (向下兼容 · graph 是新增 sibling 字段)
- ❌ 不破 `quality_blocker.check_financial_consistency` 内部 anchor 比对逻辑 (新维度独立 module)
- ❌ 不破 v16 mock 路径 (Stage 5a smoke 已验)
- ❌ Sprint 1 不实装 partial section run (留 Phase B-3 · 仅 endpoint scaffold + ack)

---

## 7. Sign-off

- v1.0 author: worker-B4-report · 2026-05-01
- 依据: `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE3 (R1+R2+R3 三轮辩论 ratify) + `docs/onboarding/B4-report.md` (6 件 verbatim)
- 配套 contract: `agent-handoff-schemas.md` §6.2 · `agent-report-spec.md` (主 spec · 不破) · `agent-credit-spec.md` (BE2 同 sprint · scoring_dim 命名 align)
- v1.1 升级触发: Phase B-3 实装 partial section run + `data/mock/handoff/agent3-to-6-gap.json` fixture 实装
