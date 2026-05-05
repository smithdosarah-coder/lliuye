# BE13 个人画像 POC Runbook (skeleton · PREP-only)

> **Sprint 3 · worker-B7-final · BE13 减半 0.75-1 周** (per phase-b-charter v2.2 line 212 · Q-046 BE7 已 B4-credit Sprint 2 提前 ship)
> **Status**: PREP-only skeleton · BE12 真业务 ship 后 worker 接通 → POC 跑首轮
> **Owner**: worker-B7-final (`feat/phase-b7-final`) · ship 阶段移交主 CLI cherry-pick
> **依据**: docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md BE13 + onboarding/B7-final.md
> **锚定**: PersonalInsightPayload TypedDict 在 commit `9479428` (位于 `feat/phase-b4-channel` branch · 不在本分支 worktree HEAD · ship 闸 cherry-pick to main 顺序 dependency: B4-channel BE12 schema 必先 merge 后才能 cherry-pick B7 PREP)

---

## 0. POC 是什么 / 不是什么

**是**:
- 给 BE12 子域 (`/api/channel/personal_insight/{candidate_id}`) 配一套 **4 维度加权评价**, 跑首轮 baseline + 提交 ledger 上链 evidence
- 验 BE7 decision_ledger (sqlite-backed · 4 retention default · subject_id PII hash) 在 BE12 真业务调用时**真上链** + evidence_chain 含 BE12 payload 引

**不是**:
- 不演销售/价格/multi-tenant 叙事 (per Q-052 #6 charter v2 #5 改验收口径)
- 不做 Agent7 新建 (per BACKEND-DEEP-WORK-V2-1-FINAL §5 不做边界 · Codex evidence-based 反对 · 复用 Agent1 子域足够)
- 不重平台/不造 orchestrator (per BE13 brief)
- 不替 B4-channel 做 BE12 真业务 (B4-channel ownership · 我只 read-only verify schema + 跑评价)

---

## 1. 4 维度评价定义 (POC-4-DIMS)

per BE13 brief · 替代旧"经营策略 20%"维度名 (Codex re-review V2 修正 · BE12 schema 实际维度).

| 维度 | 权重 | 依据字段 (per PersonalInsightPayload @ 9479428) | 计算 (deterministic · per CLAUDE.md §3.1) | yaml metric name |
|---|---|---|---|---|
| 1. 个人画像 | **35%** | `person_features` 6 字段 (role/industry_yr/education/age_range/risk_appetite/decision_path) | `filled_ratio*0.7 + oracle_match*0.3` (oracle 缺时 score=filled_ratio) | `person_features_accuracy` |
| 2. 产品适配 | **25%** | `product_fit` (recommended_products / fit_score / fit_reasons / miss_reasons) | `normalized_fit*0.6 + has_recommend*0.2 + has_reason*0.2` | `product_fit_score` |
| 3. 合规+话术 | **20%** | `compliance_check` + `talking_points` (8 子项) | `compliance(0.40 总) + talking(0.50 总) + 缓冲(0.10)` | `compliance_talkpoints_completeness` |
| 4. PII+latency | **20%** | `pii_redacted` + `latency_ms` | `pii_gate * (0.5 + latency_score*0.5)` · 4 tier (5s/10s/30s/inf) | `pii_latency_compliance` |

**加权综合分 (POC verdict)**:
- `weighted_score = sum(value * weight) over 4 dim` (max 1.0)
- `PASS ≥ 0.85` · `PARTIAL [0.70, 0.85)` · `FAIL < 0.70`
- 任何 dim value=None → `verdict=PENDING` (不误导基线)

实现位置:
- 配置: `evaluation/agent1_personal_insight.yaml`
- 计算: `evaluation/runner/adapters/agent1_personal_insight.py:Agent1PersonalInsightEvaluator`
- 加权 helper: `evaluation/runner/adapters/agent1_personal_insight.py:compute_weighted_poc_verdict`

---

## 2. Evaluation runner trigger (BE12 真业务 ship 后启用)

### 2.1 启用步骤 (worker · BE12 真业务 ship 时执行)

```bash
# (1) 加 _LAZY_MODULES 注册 (worker 改 1 行)
# evaluation/runner/registry.py:24-31
#   _LAZY_MODULES = {
#       ...
#       "personal_insight": "evaluation.runner.adapters.agent1_personal_insight",  # ← 加
#   }

# (2) Worker 落 runtime artifact (BE12 endpoint 真业务跑后 dump · 见 §2.2 协议)
#   evaluation/manual/personal_insight_latest.json

# (3) PM 落 oracle gold (反 5 原则 #1 盲测 · adapter 不预知)
#   evaluation/manual/personal_insight_oracle.json

# (4) 跑 baseline
py -m evaluation.runner --agent personal_insight --out evaluation/results/$(date +%Y-%m-%d)-be13-poc-first-run.json

# (5) 写 baseline doc + 提交
#   evaluation/baselines/$(date +%Y-%m-%d)-be13-poc-first-run.md
```

### 2.2 Artifact runtime dump 协议

worker B4-channel BE12 真业务 ship 时 · `/api/channel/personal_insight/{candidate_id}` endpoint 跑完后 · 落:

```json
{
  "runs": [
    {
      "candidate_id": "<candidate uuid>",
      "payload": <PersonalInsightPayload schema · 见 agent_channel/personal_insight.py:73-83>,
      "endpoint_status": 200,
      "schema_valid": true,
      "llm_calls": {
        "total": <int>,
        "success": <int>,
        "audit_ids": [<shared/llm_caller audit ctx ids>]
      },
      "ledger_decision_id": "<uuid · BE7 上链 id 用于 §3 verify>"
    }
  ],
  "oracle": {
    "source": "pm-design-be13-poc",
    "generated_at": "<ISO 8601>",
    "gold_person_features_by_candidate_id": {
      "<cid>": {"role": "...", "industry_yr": ..., ...}
    },
    "difficulty_tier": {"<cid>": "easy|medium|hard|extreme"}
  }
}
```

### 2.3 Baseline 不退化 gate

跑前对比 `evaluation/baselines/2026-05-04-sprint2-end.md` channel 段:
- 现状: `🟡 PARTIAL · Sprint 1+2 未启 (charter v2 Sprint 3 启 BE1+BE12)`
- BE13 POC 跑后: 新增 `personal_insight` 段 · 不动 channel 段 · channel baseline 完全不变

如 BE12 真业务 ship 同时改了 `channel` adapter 行为 → 必跑 `--agent channel` 对比 sprint2-end baseline · 任何指标退化 = 阻断 ship。

---

## 3. Ledger Integration Verify Checklist (BE7 read-only)

per CLAUDE.md §3.7.5 + docs/contracts/decision-ledger.md v1.0.

> 本 worker (B7-final) **read-only verify** · 不动 `shared/decision_ledger/*` (BE7 已 ship · B4-credit Sprint 2 owns)
> BE12 真业务 ship 时 worker B4-channel 在 endpoint 调 `record_decision()` · 本 checklist 给那时 verify 用.

### 3.1 必查项 (V1-V8)

| # | 检查项 | 期望 | 验证命令 / 方法 |
|---|---|---|---|
| V1 | `agent_id="channel"` 上链 | 上链记录 · `query_agent("channel")` 返结果 | `from shared.decision_ledger import query_agent; query_agent("channel", limit=10)` |
| V2 | `endpoint` 字段格式 | `/api/channel/personal_insight/<candidate_id>` (含 candidate_id) | 检查返回行 `endpoint` 字段 startswith `/api/channel/personal_insight/` |
| V3 | `subject_id` PII hash 强制 | 16-hex prefix · 非原文 candidate_id | `len(row["subject_id"]) == 16 and not row["subject_id"].isalpha() and row["subject_id"] != candidate_id_plain` |
| V4 | `subject_id` 一致性 | 同 candidate_id 多次上链 · subject_id 一致 (salt deterministic) | `from shared.decision_ledger import hash_subject_id; assert hash_subject_id("test_cid_001") == hash_subject_id("test_cid_001")` |
| V5 | `evidence_chain` 含 BE12 payload 引 4 字段 | `person_features_source` / `product_fit_llm_call_id` / `compliance_sources` / `talking_llm_call_id` 全在 | 检查 `evidence_chain` keys ⊇ {"person_features_source", "product_fit_llm_call_id", "compliance_sources", "talking_llm_call_id"} |
| V6 | `retention_class` default | `"short"` (per channel default · §3.7.5 line 51) | `row["retention_class"] == "short"` |
| V7 | `jurisdiction` default | `"HQ"` (env LIUYE_LEDGER_JURISDICTION 未设时) | `row["jurisdiction"] == "HQ"` |
| V8 | `input_hash` / `output_hash` SHA-256 | 64-hex · canonical (sorted keys + UTF-8) | `len(row["input_hash"]) == 64 and len(row["output_hash"]) == 64` |

### 3.2 失败隔离 verify (per BE7 spec §1.4)

ledger 写入失败 = silent-fail · 不破 BE12 endpoint flow:

- **V9 silent-fail test**: 关闭 sqlite (`chmod 000 data/ledger/decisions.sqlite` Linux / 改 sqlite mode Windows) · 跑 endpoint · 期望 endpoint 200 + payload 完整 + ledger entry 缺失 (sqlite warning log 出现)
- **V10 idempotency**: 同 `decision_id` 多次 record_decision → INSERT OR REPLACE 不抛异常 · `query_agent` 仅返 1 行 (per `store.py:171` INSERT OR REPLACE)

### 3.3 PII never-plain 守 (per CLAUDE.md §3.7.5 红线)

per `shared/decision_ledger/store.py:155` 强制 hash · 任何 plain PII 进入视作 regression:

- **V11 plain PII fence**: grep `data/ledger/decisions.sqlite` 任何 sqlite row 的 `subject_id` 字段 · 必全 16-hex · 任何长度 ≠ 16 或含中文 / 含 18 位身份证格式 = regression
  ```python
  import re, sqlite3
  conn = sqlite3.connect("data/ledger/decisions.sqlite")
  bad = list(conn.execute(
      "SELECT subject_id FROM decisions WHERE subject_id IS NOT NULL "
      "AND (length(subject_id) != 16 OR subject_id GLOB '*[^0-9a-f]*')"
  ))
  assert not bad, f"plain PII regression: {bad}"
  ```
- **V12 evidence_chain plain PII**: 即使 subject_id hash 了 · `evidence_chain` JSON 不能有原文身份证号 / 统一社会信用代码 (regex `\d{18}` / `[0-9A-Z]{18}` 守) — 留 BE12 真业务 ship 后 worker 守:
  ```python
  import re
  for row in conn.execute("SELECT evidence_chain FROM decisions"):
      assert not re.search(r"\b\d{15,18}\b", row[0]), f"plain id in evidence_chain: {row[0][:200]}"
  ```

### 3.4 Discovery question (PM 决)

**Q**: `personal_insight` 含 PII (`education` / `age_range` / `decision_path`) · 是否升级 `retention_class` "short → standard" 配合银保监 archive?

- **PRO**: 银保监对个人金融信息留存 5y 是常见要求 · 升级匹配
- **CON**: §3.7.5 default 已锁定 channel=short (90d) · 改 default 是 PM 显式拍板 + commit `Authorized-By: PM` trailer 才允许 (per spec §3.7.5 "谁可放宽")
- **建议**: BE12 真业务 ship 跑首轮 POC 后 · 主 CLI + Codex R1/R2 双 AI 辩论 (per Q-049) → PM 拍板 → 加 §3.7.5 第 6 行特殊规则 OR 显式 endpoint-level retention override

---

## 4. POC 跑首轮 checklist (BE12 真业务 DONE 后执行)

```
[ ] B4-channel WORKER-B4-CHANNEL-PERSONAL-INSIGHT-DONE signal cherry-pick 进 main
[ ] worker-B7-final 重启 · git fetch origin && git rebase origin/main
[ ] §2.1 step 1: 改 evaluation/runner/registry.py:24-31 加 "personal_insight" 入 _LAZY_MODULES
[ ] §2.1 step 2: 跑真 endpoint 5-10 candidate · 落 evaluation/manual/personal_insight_latest.json
[ ] §2.1 step 3: PM 设计 oracle gold · 落 evaluation/manual/personal_insight_oracle.json (反 5 原则 #1 盲测)
[ ] §2.1 step 4: py -m evaluation.runner --agent personal_insight
[ ] §2.1 step 5: 写 evaluation/baselines/<date>-be13-poc-first-run.md (4 维 value + weighted_score + verdict)
[ ] §3.1 V1-V8 ledger verify 跑 · 8 项全 pass
[ ] §3.2 V9-V10 失败隔离 + idempotency verify
[ ] §3.3 V11-V12 PII never-plain 守 verify
[ ] §3.4 PM 拍板 retention "short → standard" 升级? (per discovery question)
[ ] 跑 channel adapter 对比 sprint2-end baseline 不退化
[ ] commit DONE signal: WORKER-B7-FINAL-BE13-POC-DONE (POC-PREP-DONE 升级到 POC-DONE)
[ ] trailer: REVIEW-MODE / REASONING-EFFORT / ELAPSED / POC-4-DIMS (4 维真值) /
    LEDGER-INTEGRATION-VERIFY (yes 含 V1-V12 evidence) /
    GREP-GUARD-LEGACY-LLM: BASELINE=30; NEW=0
```

---

## 5. 反 5 原则 §3.5 守 (POC 数据 self-check)

| # | 原则 | 本 POC 守法 |
|---|---|---|
| 1 | 盲测 | oracle 由 PM 设计 · adapter 不预知 (worker 实现 adapter 时不见 oracle 内容) |
| 2 | 难度分层 | oracle.difficulty_tier 字段 · easy 20% / medium 50% / hard 20% / extreme 10% |
| 3 | 真实来源锚定 | A 股年报董监高披露 / 央行小微问卷 / 银保监投诉公告真实形态 |
| 4 | 脱敏再造 | 不直接用真实存续企业 candidate 数据 · 改名改数字保量级 (per `data/personal_insight_kb/` 建库) |
| 5 | 环境边界 | `person_features` 内部 KB · `compliance_check.sources` 走 shared/sources 实搜 (pbc_gov + ofac · **不 mock**) · `talking_points` 走 shared/llm_caller 实调 (LLM grounded · **不 mock 输出**) |

---

## 6. 红线 (硬 · 违 = REJECT V2)

per onboarding/B7-final.md §"红线":

- 不破现有 BE7 decision_ledger 4 retention default (per CLAUDE.md §3.7.5)
- LLM 调用走 `shared/llm_caller/` · **禁止新增 legacy direct LLM import / legacy client constructor 直连** (per Q-052 P2.6 · 具体 grep pattern 见 onboarding `GREP-GUARD-LEGACY-LLM` 段)
  - BASELINE=30 hits / 14 file at HEAD post-rebase (= dispatch HEAD 269aba1) ✅ verified
  - DIFF guard: `git diff origin/main...HEAD -- '*.py'` 必 0 新增
  - 不 touch 已知残留 14 file (per Q-052 P2.6 修正版)
- 不动 shell / today / auth / dispatch (B5 owns)
- 不动 Agent1 workspace · `agent_channel/*` (B4-channel owns) · 仅 read-only verify schema @ 9479428
- 4 维度评价确定性 · 不让 LLM 现场算 (per CLAUDE.md §3.1)
- evaluation runner baseline 不退化 (vs `evaluation/baselines/2026-05-04-sprint2-end.md`)
- 反 5 原则 §3.5 守 (POC 数据 · 见 §5)
- POC 不演销售/价格/multi-tenant (per Q-052 #6 charter v2 #5 改验收口径)

---

## 7. PREP-only 当前完成度 (本 commit · 2026-05-05)

| 工件 | 状态 | 文件 |
|---|---|---|
| 4 维度 baseline yaml | ✅ ship | `evaluation/agent1_personal_insight.yaml` (180 lines) |
| evaluation adapter scaffold | ✅ ship | `evaluation/runner/adapters/agent1_personal_insight.py` (~330 lines) |
| 加权综合分 helper | ✅ ship | `compute_weighted_poc_verdict()` 同 file |
| 本 runbook skeleton | ✅ ship | `docs/runbook/be13-personal-insight-poc.md` |
| ledger integration verify checklist | ✅ ship | 本 runbook §3 V1-V12 |
| BE12 schema read-only verify | ⚠️ external checkpoint | `git show 9479428:agent_channel/personal_insight.py` · schema 在 `feat/phase-b4-channel` branch · 当前 worktree HEAD 不见 · ship 闸 cherry-pick to main 必先于 B7 (顺序 dependency) |
| BE7 ledger read-only verify | ✅ ship | shared/decision_ledger/{__init__,schema,store,hashing}.py 全 BE7 ship · 4 retention default 锁 §3.7.5 · subject_id 强制 hash · silent-fail 不破 endpoint flow |
| _LAZY_MODULES 注册 | ⏳ pending (per PREP-only) | BE12 真业务 ship 时 worker 加 1 行 |
| oracle gold 落地 | ⏳ pending (per PREP-only) | BE12 真业务 ship 时 PM 设计 · 反 5 原则 #1 盲测 |
| 首轮 baseline 跑 | ⏳ pending (per PREP-only) | BE12 真业务 ship 时跑 §2.1 + §4 checklist |
| ledger integration verify (真跑) | ⏳ pending (per PREP-only) | BE12 真业务 ship 时跑 §3 V1-V12 |

---

## 8. Sign-off (本 PREP-only 阶段)

- author: worker-B7-final · 2026-05-05
- review: 等主 CLI Codex peer-review (插入点 2 · per Q-043 codex protocol v2 + Q-049 双 AI 辩论默认)
- ratify: PM 看完 PREP commit + Codex AGREE 后 GO · 主 CLI cherry-pick 进 main

POC 真跑 (本 runbook §4) → 等 B4-channel BE12 真业务 DONE 信号 → worker-B7-final V2 接通 → 写 BE13-POC-DONE 升级 (含 4 维真值 + V1-V12 evidence + ledger upload 真上链 evidence)。
