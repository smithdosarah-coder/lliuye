# Agent6 · Material Gap Graph + Cross-Section Coherence · v1.0

> **Source**: Phase B Sprint 1 · BE3 P0 必做 · 解 RM + 审贷员痛 1.2.3 (报告章节不一致 + 缺材料闭环)
> **Owner**: worker-B4-report (Phase B Sprint 1 · 4 of 4)
> **Status**: spec only · v1.0 V2 (Sprint 1 scaffold · partial section run 留 Phase B-3 fix-forward · 含 Codex 插入点 1 Q1/Q2/Q3 战术修)
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
| `scoring_dimension` | `<rubric_dim_id>` (Sprint 1 = current code IDs · 见下方规则) | `id` · `name` (e.g. "经营情况") · `agent` (恒为 `"credit"` · 即 Agent3) | Sprint 1 接 current code · BE2 ratify 后 fix-forward |

**规则**:
- `material.id` 取自 `material_kb` 的稳定 key (不漂移)
- `section.id` 与 v16 输出 docx 4 章锚点 (`chapter_1_background` / `chapter_2_operation` / `chapter_3_finance` / `chapter_4_conclusion`) 一致
- `scoring_dimension.id` **Sprint 1 = current code IDs** (per Codex 插入点 1 verdict Q1 战术修):
  - 来源: `agent_credit/scoring_model_corporate.py:79-84` `DEFAULT_WEIGHTS`
  - 取值集合 (corporate 业务线 · 4 dims): `"financial"` (财务 35%) · `"industry"` (行业 15%) · `"operational"` (经营 25%) · `"guarantee"` (担保 25%)
  - `name` 中文显示名约定: `财务情况` / `行业情况` / `经营情况` / `担保情况`
  - **不 wait BE2** (worker-B4-credit BE2 decision graph rubric 是 Sprint 2/3 future) · BE2 ratify 后由本 worker fix-forward 升级 (e.g. `operational` 拆 `operation_stability` + `management_quality` 时 · 同步改 material_gap_rules.py SECTION_TO_DIM_WEIGHTS)
  - retail (对私) 业务线现 shape 不同 (FICO-style 300-850 + category_scores dict · per `scoring_model_retail.py`) · Sprint 1 不覆盖 · 留 reserved/inclusive 业务线扩展时同 BE2 fix-forward

### 2.3 Edges (2 类型)

| `type` | `from` → `to` | 必填字段 | 语义 |
|---|---|---|---|
| `provides` | `material` → `section` | `from_id` · `to_id` · `severity` (`blocking` / `advisory`) · `affected_fields: list[str]` (e.g. `["supply_chain_concentration", "buyer_diversity"]`) | 材料缺 → section 哪些字段无法填 |
| `affects` | `section` → `scoring_dimension` | `from_id` · `to_id` · `impact_magnitude: int` (0-100 · 当 section 缺该字段时对 scoring_dim 评分的预期下行幅度) · `reasoning: str` (短句 · 引规则) | section 字段缺 → scoring_dim 评分受影响 |

**impact_magnitude 计算规则** (确定性 · per §3.1):
- `affected_fields` 数量 / section 总字段数 × 该 section 对该 scoring_dim 的总权重 × 100
- 示例: 若 `chapter_2_operation` 缺 `supply_chain_concentration` 1 字段 (总 8 字段) · 该 section 对 `operation_stability` 权重 0.6 · 则 `impact_magnitude = 1/8 × 0.6 × 100 = 7.5 → round 8`

**配置位置**: `agent_report/material_gap_rules.py` 内 `_MATERIAL_TO_SECTION_RULES` + `_SECTION_TO_DIM_WEIGHTS` 两个 dict (JSON-serializable · 不写代码逻辑)。

### 2.4 fixture 形态 (per 反 5 原则 §3.5 #5 · fixture 只存 inputs · 不含答案字段)

per Codex 插入点 1 verdict Q3 战术修 (反 5 原则 §3.5 #5 必坚持):
> fixture 只存 inputs · `material_gap_graph` 是 computed output · test 里 assert · **graph 字段绝不进 fixture file**。

`data/mock/workspace/report/scenarios/<scenario_id>.json` shape (**仅 inputs**):

```jsonc
{
  // 既有 fixture 字段不动 (mock_v16_stream done shape · profile / sections / qc / pending_questions 等)

  // ↓ 本 worker 新增字段 · 仅 inputs · graph 不进
  "material_gap_inputs": {
    "scenario_id": "medium_missing_critical",
    "difficulty_tier": "medium",
    "materials": [
      // 每份材料的 status 输入 (present / partial / missing) · 不含 impact magnitude
      {"id": "supplier_concentration", "name": "前五大供应商占比", "status": "missing"},
      {"id": "revenue_history_3y",     "name": "最近 3 年营收明细", "status": "missing"},
      {"id": "upstream_aging",         "name": "上下游账期表",     "status": "partial"}
    ],
    "section_status": [
      // 4 章 status 输入 · 不含 impact 字段
      {"id": "chapter_1_background", "status": "done"},
      {"id": "chapter_2_operation",  "status": "partial"},
      {"id": "chapter_3_finance",    "status": "done"},
      {"id": "chapter_4_conclusion", "status": "pending"}
    ],
    "cross_section_numbers": {
      // hard 档专用 · 跨章节同字段数字 (test cross_section_coherence 用 · easy/medium 不填)
      // shape: {canonical_key: [{section_id, value, snippet}, ...]}
    }
  }

  // ❌ 不允许出现的字段:
  //   "material_gap_graph": {...}   ← 这是 build_graph() 当场算的 output · 进 fixture = 预埋答案
  //   "section_impact": {...}        ← 同上
  //   "max_score_impact": 18         ← 同上
}
```

**3 难度分层** (per `CLAUDE.md` §3.5 反 5 原则 #2 难度分层):

| 文件 | 难度 | inputs (shape) | 期望 graph (test assert · 不进 fixture) |
|---|---|---|---|
| `easy_full_materials.json` | 简单 (20%) | 1 missing material (e.g. `headcount_roster`) · 4 section 全 done | nodes ≥ 3 · edges ≥ 2 · `max_score_impact ≤ 5` |
| `medium_missing_critical.json` | 中等 (50%) | 3 missing material (含历史数据) · 1 section partial | nodes ≥ 6 · edges ≥ 5 · `max_score_impact 12-20` (跨 ≥ 2 dim) |
| `hard_cross_section_conflict.json` | 困难 (20%) | 2 missing material + `cross_section_numbers` 含数字冲突 (e.g. `revenue` 章 2 5000 万 vs 章 3 1 亿) | nodes ≥ 5 · edges ≥ 4 · `max_score_impact ≥ 15` · cross_section_coherence BLOCK ≥ 1 |

**极端档** (10%) Sprint 1 不落 · 留 Sprint 2 (per Codex 插入点 1 Q4 v2 final verdict)。

**Test 校验** (per Q3 verdict + 反 5 原则 #5):
- `tests/agent_report/test_material_gap.py::test_fixture_no_graph_field`: 遍历 3 fixture · assert `"material_gap_graph" not in fixture` (fail-fast 防回归预埋答案)
- `test_material_gap.py::test_build_graph_deterministic`: 同 inputs (fixture 1) → 多次 build → 输出一致 (verify build_graph 是纯函数)
- `test_material_gap.py::test_build_graph_correctness`: 每 fixture 调 `material_gap.build_graph(inputs)` · assert 期望 `max_score_impact` 落预期区间 + `affected_scoring_dimensions` 包含期望 dim ID

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

**Sprint 1 = ack (received not processed)** · per Codex 插入点 1 verdict Q2 战术修:
> Sprint 1 §6.2 是 scaffold (PM 拍板 GO) · ack=`received not processed` · 用 `done` 会误导 frontend re-score (frontend 看到 done event 会以为 partial section run 已完 + 触发 Agent3 re-score · 但实际 scaffold 啥都没做) · 改 `ack` 更准。

```
event: section_supplement_started
data: {"report_id": "...", "gap_sections": [...], "scaffold_mode": true}

event: section_supplement_ack       // ← Sprint 1 用 ack (Phase B-3 partial section run 实装后改 done)
data: {
  "report_id": "...",
  "received_sections": ["chapter_2_operation"],   // ← 改名 received_sections (不再 supplemented_sections · 避免误导 frontend "已补完")
  "scaffold_mode": true,
  "partial_section_run_pending": "Phase B-3",
  "supplement_status": "scaffold_ack",            // Sprint 1 仅 ack received · B-3 partial run 完后才 done · 改 status="ran_partial"
  "next_step": "Phase B-3 fix-forward 后 Agent3 重评 (per §6.2 消费侧约束) · Sprint 1 frontend 不应触发 re-score"
}
```

**Phase B-3 升级路径** (与 worker-B4-credit BE2 V3 双侧):
- `event: section_supplement_ack` → `event: section_supplement_done` (event name 升级)
- `received_sections` → `supplemented_sections`
- `supplement_status: "scaffold_ack"` → `"ran_partial"`
- `partial_section_run_pending` 字段移除
- frontend 接 `done` 才触发 Agent3 re-score · 接 `ack` 仅显示"已收到 · partial run 等 B-3 实装"

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

- v1.0 author: worker-B4-report · 2026-05-01 (DRAFT-PREPARED commit `79e9098`)
- v1.0 V2 author: worker-B4-report · 2026-05-01 (DRAFT-V2 含 Codex 插入点 1 Q1/Q2/Q3 战术修)
- 依据: `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE3 (R1+R2+R3 三轮辩论 ratify) + `docs/onboarding/B4-report.md` (6 件 verbatim)
- 配套 contract: `agent-handoff-schemas.md` §6.2 · `agent-report-spec.md` (主 spec · 不破) · `agent-credit-spec.md` (BE2 future · Sprint 2/3 ratify · 不 wait)
- v1.1 升级触发: Phase B-3 实装 partial section run + `event: section_supplement_ack` → `done` 改名 + `data/mock/handoff/agent3-to-6-gap.json` fixture 实装 + BE2 ratify 后 scoring_dimension.id 升级 (e.g. `operational` 拆 `operation_stability` + `management_quality`)

### 7.1 V2 战术修变更 log (per Codex 插入点 1 verdict NEEDS-WORK)

| Q | 变更 | 改动位置 |
|---|---|---|
| Q1 | scoring_dimension.id Sprint 1 = current code IDs (`financial / industry / operational / guarantee`) · 不 wait BE2 future · BE2 ratify 后 fix-forward | §2.2 nodes 表 + 规则段 |
| Q2 | endpoint event: `section_supplement_done` → `section_supplement_ack` (Sprint 1 = received not processed · 避免误导 frontend re-score) · `supplemented_sections` → `received_sections` | §4.3 SSE response |
| Q3 | fixture **只存 inputs** · `material_gap_graph` 是 computed output · graph 字段绝不进 fixture · test 里 assert (含 `test_fixture_no_graph_field` fail-fast 防回归) | §2.4 整段重写 |
