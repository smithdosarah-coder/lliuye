# Worker-B4-report · Codex Pre-Dispatch Draft (插入点 1)

> **Sprint**: Phase B Sprint 1 · 4 of 4 · BE3 P0 必做
> **Branch**: `feat/phase-b4-report` · worktree `D:\claude code\work-B4-report`
> **依据**: `docs/onboarding/B4-report.md` (6 件 verbatim) + `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE3 + `docs/contracts/agent-report-material-gap.md` v1.0 (本 worker 同 sprint 写)
> **PM 拍板** (4 件 GO · 2026-05-01): 4 设计决策全接 · fixture 落 `data/mock/workspace/report/scenarios/*.json` · cross_section_coherence = quality_blocker 第 5 维 · Codex 插入点 1 = main CLI 责任
> **Reasoning effort target**: medium (per Q-043 codex protocol v2 默认 · sequential single bg)

---

## Block A · 6 件交付映射

**改**

不要把 6 件实装为"重写 v16 pipeline 的 classifier→generator→QC 三阶段"。v16 是稳定核心 (`v16_pipeline.run_pipeline` 482 行 + `agent_report/v16_runner.py` 5 阶段 SSE wrapper 已稳)。BE3 是**audit 阶段后置 wrapper**:

```
v16_pipeline (不动) → quality_blocker (加第 5 维 · 向下兼容) → material_gap.build_graph (新建 · 消费 done summary) → done_payload 注入 material_gap_graph 字段
```

**坚持**

6 件交付分 6 文件落地 (per `agent-report-material-gap.md` §5):

| # | 交付 | 文件 | 入口签名 |
|---|---|---|---|
| 1 | material gap graph | `agent_report/material_gap.py` | `build_graph(pending_questions, classified_json, qc_summary, financial_anchor) -> dict` |
| 2 | section impact | (同 1 module · `_compute_section_impact()` private) | — |
| 3 | cross-section coherence (第 5 维) | `agent_report/cross_section_coherence.py` + `quality_blocker.run_blocker(..., sections=None)` | `check_cross_section_coherence(sections, anchor, tolerance_pct=1.0) -> list[BlockerIssue]` |
| 4 | §6.2 handoff endpoint scaffold | `agent_report/handoff_section_supplement.py` + `api.py` route | `POST /api/report/section_supplement` |
| 5 | fixture (3 难度分层) | `data/mock/workspace/report/scenarios/easy_full_materials.json` + `medium_missing_critical.json` + `hard_cross_section_conflict.json` | — |
| 6 | 单元测试 | `tests/agent_report/test_material_gap.py` | 6 test case |

**对方弱点**

Codex 看完 onboarding 可能挑 4 处:
1. **Sprint 1 §6.2 handoff 是 scaffold 不实装 partial section run** — 易被挑"endpoint 接 payload 但啥也不做就是空壳"。回应见 Block C 决策 3 · partial section run 跨 Sprint 与 worker-B4-credit BE2 协调 · Schema §6.7 已标 owner = A4-credit V3 + A4-report V3 双侧 · Phase B-3 (与 Agent6→Agent3 单链路同 sprint)。Sprint 1 scaffold 必要性: BE2 worker-B4-credit 同 sprint 测调用契约 · 不能等 B-3。
2. **cross_section_coherence 引入"canonical key 表"是黑名单** — 易被挑"`_CANONICAL_KEYWORDS` 是关键词黑名单 vs CLAUDE.md 反对黑名单"。回应: 这不是反幻觉黑名单 · 是 NER 同义词归一表 · 与 `quality_blocker._PLACEHOLDER_PATTERNS` (已存在的关键词 list) 同性质 · 都是确定性 token 识别。规则覆盖不到时按"unknown_key"跳过 · 不假阳。
3. **impact_magnitude 计算公式** — 易被挑"`affected_fields 数 / section 总字段数 × 权重 × 100` 公式没引论文 / 没历史校准"。回应: 这是 Sprint 1 v1.0 公式 · 公式参数 (section 总字段数 · section→dim 权重) 全在 `material_gap_rules.py` JSON-serializable dict · 后续可按真客户回归校准 (worker-B7 decision ledger Phase 后跑 baseline · per `evaluation/agent_report.yaml`)。
4. **fixture 3 scenario 是否够覆盖** — 反 5 原则 §3.5 难度分层应 4 档 (简单 20% / 中等 50% / 困难 20% / 极端 10%)。回应: Sprint 1 落 3 档 (简单 / 中等 / 困难) · 极端档 (跨 6 章节多冲突 + 多缺材料) 留 Sprint 2 · `worker-B4-credit` BE2 同 sprint 共享 fixture 时再扩。

**吸收对方**

如果 Codex 反对 Sprint 1 §6.2 scaffold + 主张完整 partial section run · 接受 · 但请明确 partial section run 入口签名 (e.g. `v16_pipeline.run_pipeline(..., section_filter: list[str] | None = None)`) · 由 main CLI 协调 worker-B4-credit BE2 sprint 是否同步加 · 我可加但工程量从 1.5-2 周 → 2.5-3 周 (溢 Sprint 1 边界 · per Phase B charter v2 §3 排期)。

**v2 final**

Sprint 1 范围 lock:
1. material_gap.py + material_gap_rules.py + cross_section_coherence.py 3 新模块全实装
2. quality_blocker.run_blocker 加 sections=None 参数 (向下兼容)
3. handoff_section_supplement.py + `POST /api/report/section_supplement` endpoint scaffold (接 payload + 校验 + 返 ack event)
4. v16_runner.done_payload 注入 material_gap_graph 字段
5. fixture 3 难度档 (data/mock/workspace/report/scenarios/{easy_full_materials, medium_missing_critical, hard_cross_section_conflict}.json)
6. tests/agent_report/test_material_gap.py 6 case (graph build / impact magnitude / cross-section drift / handoff scaffold ack / 向下兼容 sections=None / 反 5 原则 fixture 不含答案字段 verify)

DONE signal commit trailer:
```
BE-DELIVERED: BE3 (Agent6 material gap + cross-section coherence)
SCHEMA-DOC: docs/contracts/agent-report-material-gap.md
HANDOFF-LINK: agent-handoff-schemas.md §6.2 (Agent3→Agent6 反向链)
CROSS-SECTION-COHERENCE: yes (跨章节语义 sanity check · 第 5 维)
FIXTURE-UPDATED: data/mock/workspace/report/scenarios/*.json (3 档)
TESTS-PASS: tests/agent_report/test_material_gap.py 全 pass
PRESERVES: v16 pipeline (run_pipeline 签名不破) · pending_questions 形态 · quality_blocker 4 维原逻辑 · v16 mock 路径
HARDLINE-PHASE-B-#4: 部分 met (BE3 部分 · 6 Agent 后端真业务能力 1/13)
SPRINT-1-SCAFFOLD: §6.2 handoff endpoint = scaffold (partial section run 留 Phase B-3 fix-forward · per Schema §6.7)
```

---

## Block B · 4 设计决策

### B.1 Material gap graph schema (PM 拍板 GO)

3 节点类型 (`material` / `section` / `scoring_dimension`) + 2 边类型 (`provides` / `affects`) · `impact_magnitude: int 0-100` · `severity: blocking/advisory` · 详 `agent-report-material-gap.md` §2。

**关键 align**: `scoring_dimension.id` 与 worker-B4-credit BE2 `agent-credit-spec.md` rubric_dim 命名一致 · 与 worker-B7 BE7 decision ledger schema 字段命名一致 (跨 Agent 链 align)。

### B.2 Cross-section coherence = quality_blocker 第 5 维 (PM 拍板 GO · 不引入新模块独立跑)

`quality_blocker.run_blocker(text, financial_anchor, expect_evidence, sections=None)` 加可选 `sections` 参数 (默认 None 向下兼容 · 不传则跳过第 5 维)。`BlockerVerdict.fail_dimensions` 加新值 `cross_section_coherence`。`BlockerIssue` dataclass 不扩展。详 `agent-report-material-gap.md` §3。

### B.3 §6.2 Sprint 1 = scaffold (PM 拍板 GO · 不实装 partial section run)

`POST /api/report/section_supplement` 接 payload + Pydantic 校验 + 返 fixture-mode `section_supplement_done` event 含 `scaffold_mode: true` + `partial_section_run_pending: "Phase B-3"`。partial section run 真实装留 Phase B-3 fix-forward (per Schema §6.7 双侧 owner)。详 `agent-report-material-gap.md` §4。

### B.4 fixture 反 5 原则适配 (PM 拍板 GO · 落 data/mock/workspace/report/scenarios/*.json)

3 难度档 fixture · **绝不预埋答案** (graph 由 `material_gap.build_graph()` 当场算 · fixture 仅含输入) · 单测验"输入相同时输出确定"。详 `agent-report-material-gap.md` §2.4。

---

## Block C · 红线 verify

per `docs/onboarding/B4-report.md` §3 + Codex R2 双方共识:

- ✅ 不重写 v16 pipeline (material_gap.py 是 audit 阶段后置 wrapper · run_pipeline 签名不破)
- ✅ 不引入 ML (全规则引擎 + JSON 配置驱动)
- ✅ 不引 LLM 现场算 material gap / cross-section coherence (per `CLAUDE.md` §3.1 确定性计算)
- ✅ 不跨 worktree (本 worker 仅在 `D:\claude code\work-B4-report` 内动)
- ✅ commit Signal: trailer (per Q-043 codex protocol v2)
- ✅ 不破 v16 mock 路径 (Stage 5a smoke 已验 · 本 worker 实装时跑 `tests/agent_report/test_v16_fill_sse.py` 回归)

---

## Block D · Codex 重点检查项 (插入点 1)

请 Codex 重点验:

1. **schema align verify**: `material_gap_graph` 字段命名 (`scoring_dimension.id`) 与 `agent-credit-spec.md` (BE2 worker-B4-credit 同 sprint) rubric_dim 命名是否一致 · 跨 Agent decision ledger (worker-B7 BE7) schema 是否兼容
2. **§6.2 scaffold 边界合理性**: Sprint 1 scaffold + Phase B-3 实装 partial section run · vs 一 Sprint 内全实装 · 哪个更符合 Phase B charter v2 §3 排期 + Schema §6.7 双侧 owner 约束
3. **cross_section_coherence canonical key 表风险**: 是否构成黑名单 (vs CLAUDE.md 反对黑名单) · 还是同义词归一表 (NER 性质)。我视为后者 · 请验
4. **impact_magnitude 计算公式可校准性**: Sprint 1 v1.0 公式 (`affected_fields 数 / section 总字段数 × 权重 × 100`) · 是否 Phase C / worker-B7 baseline 校准前的合理 placeholder
5. **fixture 反 5 原则合规性**: 3 档难度分层是否符合 `CLAUDE.md` §3.5 (简单 20% / 中等 50% / 困难 20% / 极端 10%) · 我落 3 档 (简单 / 中等 / 困难) · 极端留 Sprint 2 · 是否 ok 还是必须 Sprint 1 4 档
6. **不破 v16 mock 路径**: `mock_v16_stream` done payload 形态 + 加 `material_gap_graph` 字段是否破前端 (前端 PreviewPanel / MaterialPanel hydrate 兼容)
7. **handoff endpoint 校验严格度**: `gap_sections` 元素必属 `_CHAPTER_HEADINGS` ∪ `material_kb` 已知 key · 是否过严 (Agent3 可能传新 key 名)

---

## Block E · Sign-off

- author: worker-B4-report · 2026-05-01
- contract sibling: `docs/contracts/agent-report-material-gap.md` v1.0 (本 worker 同 commit 写)
- 等 main CLI fire Codex insertion point 1 (medium · sequential · in worker-B1-flywheel V2 + worker-B4-credit codex review queue 后)
- Codex verdict 后再开 Build phase (commit 粒度 = TaskCreate 粒度 · 8 commits per `agent-report-material-gap.md` §5 + verify commit 1)
