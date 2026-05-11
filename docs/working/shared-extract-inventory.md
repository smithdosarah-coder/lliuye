# shared-extract inventory · B.3.4 P0-R1 (2026-05-11)

> **Worker**: shared-extract (B.3.4 P0-R1)
> **Branch**: `feat/b34-shared-extract`
> **依据**: codex R7 brutal verdict — *"shared contract + shared invariants + local adapters where domain truly differs"*
> **不依据**: KT "everything shared" 极端 · 也不依据"完全不动"保守
> **方法**: Explore agent 全 6 Agent 4 模块扫描 + 主 CLI spot-check verify (`diff` + `wc -l`)

---

## 0. TL;DR · brutal verdict (打脸 KT 假设)

**KT 2026-05-10 retro 假设**: 6 助手同构重复 · 4 模块都需 extract · 工期 2-3 天。
**Inventory verify verdict**: **3/4 模块的 shared 基建已存在 · 仅 output_validator 真重复 (5 文件 95% 相同)**。

| 模块 | KT 假设 | 实际状态 | 真工作量 |
|---|---|---|---|
| evidence_pipeline | 6 助手同构 | ✅ 6/6 已 `from shared.evidence import EvidenceFirstPipeline` · domain hooks 是合理 local | normalize confidence 策略 (alert/credit 已 BE5 升级 · 其他 4 个还静态值) |
| output_validator | 5 助手同构 | ❌ **真同构** · 5 文件 51-55 行 · 唯一差异 = docstring + AGENT 常量 · 264 LOC → 可降至 ~90 LOC | **抽 shared 单点 · 0.5 天** |
| knowledge_base | 3 助手同构 | ✅ 3/3 已继承 `shared.kb_scan.KnowledgeBase` · agent-specific 字段是合理 extension | 不动 (per R7 "local adapters where domain truly differs") |
| RBAC | 6 助手 inline 重复 | ✅ `auth_service/rbac.py` single source · 6 Agent api.py 用 `require_action` decorator · 无 inline duplication | 不动 |

**真 P0 工作量**: ~0.5 天 (output_validator extract) + 0.5-1 天 (evidence_pipeline confidence invariant) + contract test = **1.5-2 天 · 不是 2-3 天**。

**对 PM 的请示**: 是否要把"凭空 extract 已共享的模块"砍掉 · 改为只做以下 3 件 (见 §6 重新提案)？

---

## 1. evidence_pipeline · 6/6 Agent

| Agent | file | LOC | 主类/主函数 | 与 `shared.evidence` 关系 | domain-specific 占比 | 共享提案 |
|---|---|---|---|---|---|---|
| alert | `agent_alert/evidence_pipeline.py` | 191 | `AlertEvidencePipeline(EvidenceFirstPipeline)` + `AlertSummaryContext` dataclass | **继承** shared 基类 · import `EvidenceFirstPipeline / EvidenceItem / GroundedDraft / AuditFinding / EvidenceBundle / UNFILLED_MARKER` | ~60% (context dataclass + collect 钩子 + signal_quality 调用) | 留 local · 已合理 |
| channel | `agent_channel/evidence_pipeline.py` | 187 | (同模式 · 候选企业上下文) | 继承 shared | ~60% | 留 local · 已合理 |
| compliance | `agent_compliance/evidence_pipeline.py` | 149 | (同模式 · 政策违规上下文) | 继承 shared | ~60% | 留 local · 已合理 |
| credit | `agent_credit/evidence_pipeline.py` | 185 | (同模式 · 决策建议上下文 · BE5 用 signal_quality) | 继承 shared | ~60% | 留 local · 已合理 |
| report | `agent_report/evidence_pipeline.py` | 148 | (同模式 · 章节生成上下文) | 继承 shared | ~60% | 留 local · 已合理 |
| riskctrl | `agent_riskctrl/evidence_pipeline.py` | 147 | (同模式 · DSL 规则上下文) | 继承 shared | ~60% | 留 local · 已合理 |

**Verdict**: shared 基类 (`shared.evidence.EvidenceFirstPipeline`) **早就抽了**。6 个 per-Agent 文件是**合理的 domain adapter** (context dataclass + collect 钩子) · 不是重复。

**唯一可优化点 · 共享 invariant**:
- alert/credit 用 BE5 `signal_quality.quality_bundle` 计算 `freshness × source_confidence` 综合 confidence
- 其他 4 Agent 仍用静态 0.5/0.75
- **建议**: 抽 `shared/evidence/confidence_policy.py` · 暴露 `compute_confidence(evidence_item) -> float` · 让 6 Agent 统一调 (per CLAUDE.md §3.7 active rule "证据时效 SLA")
- **风险**: 中 · 需逐 Agent 验回归

---

## 2. output_validator · 5/6 Agent (+ Agent6 quality_blocker)

### 2.1 5 个 output_validator (alert/channel/compliance/credit/riskctrl)

| Agent | file | LOC | 主函数 |
|---|---|---|---|
| alert | `agent_alert/output_validator.py` | 55 | `validate_text` / `assert_clean` / `soft_clean` |
| channel | `agent_channel/output_validator.py` | 51 | (同) |
| compliance | `agent_compliance/output_validator.py` | 51 | (同) |
| credit | `agent_credit/output_validator.py` | 52 | (同) |
| riskctrl | `agent_riskctrl/output_validator.py` | 55 | (同) |

**diff 实测** (主 CLI verify):
```
< AGENT = "agent_alert"
---
> AGENT = "agent_channel"
```
+ docstring 不同 · 函数体逐字相同 · 全部 import `shared.qc` 4 个函数。

**Verdict**: 教科书级 duplication · 264 LOC 可降至 ~60 LOC shared + 6 × ~5 LOC adapter (~90 LOC) · **省 170 LOC** + 1 改 5 改的痛点根除。

**抽离提案**:
```python
# shared/output_validator.py (新)
def make_output_validator(agent_id: str) -> OutputValidator:
    """Factory · 6 Agent 各自 import 时传 agent_id · 行为完全一致"""
    ...

# agent_alert/output_validator.py (5 LOC)
from shared.output_validator import make_output_validator
validator = make_output_validator("agent_alert")
validate_text = validator.validate_text
assert_clean = validator.assert_clean
soft_clean = validator.soft_clean
```

**风险**: 低 · 5 文件 95% 相同 · 行为不变 · 只换 import 路径 · 0 业务逻辑变。

### 2.2 Agent6 quality_blocker (特殊)

- `agent_report/quality_blocker.py` · 14.7KB · 5 维 QC (placeholder / evidence / financial_consistency / compliance_terms / cross_section_coherence)
- 与 5 个 output_validator 语义**相似但不同** (硬阻断 + 回溯链)
- **Verdict**: 留 Agent6 local · **不要硬扯到 shared** (per R7 "local adapters where domain truly differs")
- **如果硬抽**: 增加 Agent6 重构风险 + 没省 LOC · 反 ROI

---

## 3. knowledge_base · 3/6 Agent (alert/channel/compliance)

| Agent | file | 与 `shared.kb_scan.KnowledgeBase` 关系 | agent-specific 字段 |
|---|---|---|---|
| alert | `agent_alert/knowledge_base.py` | **继承** | `scenario_meta` 等 |
| channel | `agent_channel/knowledge_base.py` | **继承** | (信号库相关) |
| compliance | `agent_compliance/knowledge_base.py` | **继承** | `policy_clauses` 等 |

**credit/report/riskctrl 没 knowledge_base.py**:
- credit: 用 `agent_credit/mock_data/` fixture + context 注入 (per `mock_fixtures.py` 模式)
- report: 用 `agent_report/mock_fixtures.py` + material_kb 上传管线
- riskctrl: 用 `agent_riskctrl/demo.py` 3 scenario fixture (CLAUDE.md §11 已锚定)

**Verdict**: shared 基类已存在 · 3 Agent 各自 extend 是合理 domain adapter。**不抽**。

---

## 4. RBAC · auth_service single source

- **single source**: `auth_service/rbac.py` · 主接口 `can_action(role, agent, action)` + `require_action(agent, action)` decorator
- **6 Agent api.py 使用模式**: alert/channel/compliance/report/riskctrl 直接 `@require_action(...)` decorator · credit 加 `demo_mode_visible()` helper · **无 inline duplication**
- **Verdict**: **不抽**。已是 textbook single source pattern · 抽不动也没必要。

---

## 5. 总结 · 4 模块抽离优先级 (revised based on inventory)

| 模块 | 重复程度 | 抽离 ROI | 风险 | 工期 | 优先级 (新) |
|---|---|---|---|---|---|
| **output_validator** | **极高 (95%)** | **极高 (省 170 LOC + 1改5改根除)** | 低 | 0.5 天 | **P0 必做** |
| **evidence_pipeline confidence invariant** | 中 (alert/credit 已升 · 4 个未升) | 中 (统一 freshness × source_confidence policy) | 中 | 0.5-1 天 | **P1 应做** |
| evidence_pipeline 主类 | 低 (已 shared) | 低 (没 LOC 可省) | 中 | — | ❌ 不做 |
| knowledge_base | 低 (3/3 已 extend shared) | 低 | 中 | — | ❌ 不做 |
| RBAC | 0 (已 single source) | 0 | — | — | ❌ 不做 |

---

## 6. 重新提案 · 给 PM 拍板

**原 brief**: 抽 4 模块 (evidence_pipeline / output_validator / knowledge_base / RBAC) · 2-3 天。
**Inventory 后真实**: 3/4 已抽好 · 真活只剩 1 个半。

### 三选一 (按工期升序)

**Option A · 最小 scope** (1 天):
- 仅做 output_validator extract (P0)
- 跳过 confidence invariant (留给以后)
- 1 个 commit + contract test + 5 Agent 切 import + regression

**Option B · 推荐 scope** (1.5-2 天):
- output_validator extract (P0)
- + evidence confidence policy 统一 (P1) · 用 flag-canary (per CLAUDE.md §3.7.7) 先开 1 Agent 看效果
- + 写 4 模块 contract spec doc (即使不动 evidence_pipeline 主类 · 也固化 contract 给 P1 fix-contract worker 看)

**Option C · 全 brief 跑完** (2-3 天 · 不推荐):
- 强 extract 已共享的 evidence_pipeline / knowledge_base / RBAC
- 反 R7 verdict ("local adapters where domain truly differs")
- 可能引入回归 + 没省 LOC + 反 ROI

### 主 CLI 我的预判: 选 B

**理由**:
1. R7 verdict 明确反对"everything shared" · A 太保守 · C 反 verdict
2. 给 P1 fix-contract worker (WorkSession) 留 contract spec 是必需的 · 不能跳
3. confidence invariant 是 BE5 已开的口子 · 趁 alert/credit 还热把其他 4 个补齐 · 一致性收益高
4. 1.5-2 天 · 在 brief "2-3 天" 工期上限内

---

## 7. 不确定问题 · 留给 PM/codex 二审

1. **Option A vs B vs C 选哪个** · 我推 B · PM 是否同意？
2. **confidence invariant 在 evidence_pipeline 落地时 · 是否要 flag-gate** (per CLAUDE.md §3.7.7 渐进式落地硬规)? 我倾向: 是 · 先开 1 Agent canary · 验回归 · 再 6 Agent 全开。
3. **agent_report/quality_blocker.py 是否真的留 local 不动** · 还是要在 shared/output_validator/ 里加一个 "extended QC" 接口给 Agent6 复用 · 让它继承共享基类？我倾向: 留 local · 不强抽 (Agent6 v16 主管线刚稳 · 不动它最安全)。
4. **抽离后是否要写 deprecation shim** (per CLAUDE.md §3.6 LLM caller deprecation 模式)？我倾向: 否 · output_validator 没有 6 Agent 之外的 production import (Grep 验证过)。

---

## 8. 下一步 (等主 CLI 拍板)

- [ ] PM/主 CLI 选 Option A/B/C
- [ ] 确认 confidence invariant 是否 flag-gate
- [ ] 拍板后 · 进 Step 2 写 contract spec (B/C 才需要 · A 可跳)
- [ ] 进 Step 3 TDD red (写 contract test · CI 红)
- [ ] 进 Step 4 TDD green (实现 · CI 绿)
- [ ] 进 Step 5 5 Agent 切 import + regression
- [ ] Step 6 fire `WORKER-SHARED-EXTRACT-READY-FOR-MERGE`

**Signal commit (本 doc 完成时)**: `STEP-1-INVENTORY-DONE` · trailer 全套 · 等主 CLI cherry-pick + 拍板 Option A/B/C 才进 Step 2。
