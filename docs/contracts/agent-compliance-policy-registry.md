# Agent5 Compliance · Policy Registry & Violation Reason Schema · v1.0

> **Worker**: worker-B4-compliance · Phase B Sprint 2 · BE4 deliverable
> **Status**: ratified `feat/phase-b4-compliance` 2026-05-04
> **Authority**: Tier 1 (`docs/contracts/*.md` per CLAUDE.md §15) — RFC to amend.

Solves 合规官 pain 1.3.1+2 (per `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE4): policy version management + auditable conflict reasoning.

---

## 1. Layered storage model (`shared/policy_registry/`)

Three sqlite tables. One row per real-world entity. All ids are deterministic SHA-256 prefixes so re-importing the same body yields the same ids — prerequisite for `policy_coverage` and `conflict_recall` metrics by id.

```
policies          (POL-xxxxxxxx)  one row per policy *family*
  └── policy_versions  (VER-xxxxxxxx)  one row per immutable revision
        └── policy_clauses  (CL-xxxxxxxx)  one row per segmented clause
```

### 1.1 `policies`

| col | type | notes |
|---|---|---|
| `policy_id` | TEXT PK | `POL-` + 16 hex of SHA-256(case-folded(issuer + title)) |
| `title` | TEXT | display name |
| `issuer` | TEXT | one of `银保监 / 央行 / 证监会 / 国务院 / 人大 / 其他` |
| `category` | TEXT | optional bucket |
| `description` | TEXT | optional |
| `created_at` | TEXT | sqlite default |

### 1.2 `policy_versions`

| col | type | notes |
|---|---|---|
| `version_id` | TEXT PK | `VER-` + 16 hex of SHA-256(policy_id::effective_date::body_sha) |
| `policy_id` | TEXT FK | family link |
| `effective_date` | TEXT | YYYY-MM-DD; empty if unknown |
| `fetched_at` | TEXT | ISO timestamp |
| `body_sha` | TEXT | SHA-256 of canonicalised body text |
| `source_url` | TEXT | crawl URL |
| `body_text` | TEXT | full normalised text (truncated to 256 KB) |
| `clause_count` | INTEGER | denorm count for fast list view |
| `superseded_by` | TEXT NULL | later `version_id` (link old → new) |
| `created_at` | TEXT | sqlite default |

### 1.3 `policy_clauses`

| col | type | notes |
|---|---|---|
| `clause_id` | TEXT PK | `CL-` + 16 hex of SHA-256(version_id::article_no::paragraph_index) |
| `version_id` | TEXT FK | revision link |
| `article` | TEXT | e.g. "第六条" |
| `paragraph_index` | INTEGER | 0-based ordinal inside the article |
| `text` | TEXT | clause text (paragraph-marker stripped) |
| `category` | TEXT | bucket from `_CATEGORY_HINTS` (8 + 其他) |
| `keywords` | TEXT | JSON list (≤ 8) |
| `threshold` | TEXT | JSON dict of detected quantitative caps/floors |
| `severity_hint` | TEXT | `critical / major / minor` |

### 1.4 Default DB path

`data/policy_registry/policies.sqlite` — override via `LIUYE_POLICY_REGISTRY_DB_PATH`.

---

## 2. Loader (`agent_compliance/policy_loader.py`)

Pure deterministic, no LLM. Segments raw policy text into clauses and registers them.

### 2.1 Segmentation rules

1. Split at `第X条` headers (re-uses the regex from `scan_engine._ARTICLE_RE`).
2. Inside each article, split at line-start paragraph markers — supports both half-width `(一)` and full-width `（一）`, plus `一、` / `1.`.
3. A trailing single-paragraph article still gets one clause at `paragraph_index = 0`.
4. Threshold extraction: same templates as `scan_engine._THRESHOLD_PATTERNS` plus `min_years` and `max_hours`.
5. Category inference: 8-bucket vocabulary lookup with `其他` fallback.
6. Severity:
   - `critical` if threshold non-empty AND text contains `强制 / 严禁 / 必须 / 不得 / 禁止`
   - `major` if either condition alone holds
   - `minor` otherwise

### 2.2 Façade

| function | purpose |
|---|---|
| `segment_policy_text(text)` | preview without writing |
| `load_policy(...)` | segment + register in one call (idempotent) |
| `clauses_to_scan_rules(clauses)` | bridge to `scan_engine.matrix_check` rule shape |

---

## 3. Diff (`agent_compliance/policy_diff.py`)

Pure deterministic, `difflib.SequenceMatcher` only — no LLM in the diff path.

### 3.1 Algorithm

1. **Pass 1** — pair by `(article, paragraph_index)` exact key. Identical text → `unchanged`. Different → `change` with `similarity = ratio()`.
2. **Pass 2** — fuzzy match remaining clauses across versions when `ratio ≥ 0.55` (greedy best-match). Detects relocations.
3. **Pass 3** — surplus on each side becomes `add` / `delete`.

### 3.2 Output (`ClauseDiff`)

| field | notes |
|---|---|
| `diff_type` | `add / delete / change / unchanged` |
| `old_clause_id`, `new_clause_id` | nullable (None for add/delete) |
| `old_article`, `new_article` | tracks relocations |
| `old_text`, `new_text` | raw clause bodies |
| `similarity` | float [0.0, 1.0] |
| `hunks` | `difflib.ndiff(...)` rows for side-by-side display |

`summarize_diff(diffs)` returns `{add, delete, change, unchanged, total, avg_similarity}` for UI counters.

---

## 4. Violation reason (`agent_compliance/violation_schema.py`)

Every Agent5 violation that crosses a worker boundary (SSE → frontend, scan persistence, ledger, docx export) carries a `ViolationReason` with **7 mandatory fields** plus a derived narrative.

### 4.1 Schema

| # | field | type | notes |
|---|---|---|---|
| 1 | `policy_id` | str | registry `POL-xxxx` (prefix-validated) |
| 2 | `policy_version` | str | registry `VER-xxxx` (prefix-validated) |
| 3 | `clause_id` | str | registry `CL-xxxx` (prefix-validated) |
| 4 | `conflict_field` | str | dimension violated (e.g. `营业收入` / `可疑交易报告时限`) |
| 5 | `business_excerpt` | str ≤ 300 | verbatim event slice |
| 6 | `policy_excerpt` | str ≤ 300 | verbatim clause slice |
| 7 | `confidence` | float [0.0, 1.0] | `1.0` hard-rule / `0.7` LLM / `0.5` fallback |

Plus derived: `review_reason` — single-sentence narrative computed deterministically:

```
{conflict_field} 不符合 {clause_id_short}「{policy_excerpt[:40]}」
（业务证据: {business_excerpt[:40]}; 置信度 {confidence:.2f}）
```

### 4.2 Construction

`build_violation_reason(rule, event, cell, policy_id="", policy_version="", confidence_override=None)` returns `ViolationReason | None`. **Returns `None` when the registry-aware id triplet is missing or excerpts are empty** (per `CLAUDE.md §3.3` Evidence-First — prefer "未能自动填写" over a half-valid reason).

### 4.3 Hard line

- 0 LLM calls in the reason path.
- 0 dependency on `scan_engine` (avoids circular imports; the schema is consumable by registry, ledger, evaluation runner, and docx export).

---

## 5. Wiring into `scan_engine.run_policy_scan_and_persist`

Two helpers added (additive — no existing key removed):

| helper | when triggers |
|---|---|
| `_registry_rules_for_policy(policy_doc, policy_meta)` | only when `policy_meta` has `title` + `issuer`. Falls back silently otherwise. |
| `_enrich_violations_with_reasons(violations, rules_by_id, events_by_id)` | always; non-registry violations get `reason = None` (schema consistent). |

### 5.1 New SSE / payload fields

| field | location | notes |
|---|---|---|
| `path` | `rule_extract` stage | `"registry"` or `"heuristic"` |
| `reason_filled` | `revision_generate` stage | count of violations with non-None reason |
| `rule_path` | persisted scan payload | top-level mirror of stage path |
| `registry_info` | persisted scan payload | `{policy_id, version_id, is_new_version, clause_count}` |
| `violations[].reason` | persisted scan payload | `ViolationReason.to_dict()` or `None` |
| `stats.reason_filled_count` | persisted scan payload | uint counter |

### 5.2 Backward compatibility

- All existing keys kept untouched. Old consumers that ignore `reason` or `rule_path` continue to work.
- `policy_meta=None` (legacy callers) → registry path skipped, heuristic rules + `reason=None`.

---

## 6. Handoff schema integration (per `agent-handoff-schemas.md` §6.1)

`Agent5.violation_blocked → Agent3.re_decision` becomes machine-actionable when the reason carries the registry triplet:

- Agent3 can re-fetch the exact violated clause via `policy_registry.get_clauses(version_id)` filtered by `clause_id`.
- Agent3 stamps the re-decision input_hash including `reason.policy_version` so it's clear which policy revision drove the gate.

`agent-handoff-schemas.md` reference is kept stable; the `version_id` bump is captured by the SHA chain.

---

## 7. Active rule (back-write target for `CLAUDE.md §3.7`)

> **§3.7.6 Compliance ViolationReason 7-field invariant (BE4 · 2026-05-04)**
> Every violation row crossing a worker boundary in Agent5 paths must
> carry the 7-field `ViolationReason` (or `null` when the registry
> triplet is missing — never a partial reason). Stripping any of the 7
> fields → `review` block. Helper: `agent_compliance.violation_schema.build_violation_reason`.

Back-written to root `CLAUDE.md` in the spec-doc commit.

---

## 8. Metric improvement (per onboarding spec)

Both metrics live in `evaluation/agent5_compliance.yaml` `domain` section. Pre-BE4 they were stubbed at `0.5` because no runtime dump existed.

| metric | pre-BE4 (stub) | post-BE4 (integration verified) |
|---|---|---|
| `policy_coverage` | 0.5 (stub) | **1.0** on fixture (`tests/agent_compliance/test_policy_registry_integration.py`) |
| `conflict_recall` | 0.5 (stub) | **1.0** on fixture |

Real production runs against a human-annotated gold set will fall short of 1.0; the BE4 deliverable is **infrastructure** (deterministic clause_ids + registry round-trip + 7-field reason) that lets the metric *measure something real* instead of a stub.

---

## 9. Tests

| suite | count | covers |
|---|---|---|
| `tests/shared/test_policy_registry.py` | 16 | hashing determinism · idempotent register · clause_id stability across re-imports · mark_superseded |
| `tests/agent_compliance/test_policy_loader.py` | 20 | article + paragraph segmentation · 6 threshold templates · 8-bucket categories · severity rules · idempotent v1==v1 / v1≠v2 · scan_rules bridge |
| `tests/agent_compliance/test_policy_diff.py` | 13 | identical sets · pure add/delete · threshold tightening · cross-article relocation · summarize counters · registry round-trip |
| `tests/agent_compliance/test_violation_schema.py` | 22 | 7-field invariants · prefix gates · excerpt truncation · confidence path · narrative format |
| `tests/agent_compliance/test_policy_registry_integration.py` | 2 | end-to-end metric ≥ 0.85 · backward-compat fallback path |

**73 tests pass.**

---

## 10. Hard lines (per onboarding red lines)

| red line | enforcement |
|---|---|
| 不破 scan_engine pipeline | Two helpers added; no existing key removed; all 6 `/api/compliance/*` routes import + route-list-smoke OK. |
| 不写黑名单兜底 | Threshold templates + category buckets are *structural-language enumerable* (per `CLAUDE.md §12`). Unknown fields/categories pass through verbatim. |
| diff 用 difflib 确定性 | Only `difflib.SequenceMatcher` + `difflib.ndiff`; no LLM; no fuzzy semantic embedder. |
| MAX_ROWS=50000 (Q-040) | n/a — Agent2 backtest constraint, not Agent5. |
| Q-041 不破 | n/a — Agent1 candidate metadata, not Agent5. |
| LLM 走 shared/llm_caller | `scan_engine.build_llm_*caller` already routes through `shared.llm_caller.make_text_caller / make_json_caller`. BE4 path itself is 0 LLM. |
