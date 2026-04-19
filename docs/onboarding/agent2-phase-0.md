# Agent2 风控 · Phase 0 Onboarding（baseline 首跑）

**对应 worktree**：`D:\claude code\demo-agent2`（`feat/agent2-productize`，主 CLI 创建后交付）
**发布日期**：2026-04-19
**前置**：已读 `AGENT_IDENTITY.md` + `CLAUDE.md` + 本文
**目标**：**不做 productize**，把 evaluation runner 挂通 + 跑一版首跑基线，让 Phase 1 productize 有锚点。

与 `agent4-phase-0.md` 结构镜像——同套 Phase 0 模式，不同的是 Agent2 的指标是 DSL 生成 + 回测。

---

## 为什么 Phase 0

同 Agent4：CLAUDE.md §5.2 "先建 rubric、跑基线、找最大 gap 再改代码"。Agent1 踩过坑，Agent2 不重复。

---

## Task A · evaluation adapter（1 天）

### 目标
新建 `evaluation/runner/adapters/agent2_riskctrl.py`，对接 `evaluation/agent2_riskctrl.yaml`。

### Phase 0 确定性指标覆盖

| 指标 | Phase 0 | 方法 |
|---|---|---|
| `task_completion_rate` | ✅ | DSL 生成输入样本数 vs 成功输出数 |
| `evidence_rate` | ✅ | 每条 DSL 规则是否有 KS / 通过率 / 坏账率 回测字段 |
| `hallucination_rate` | ✅ | DSL 字段名 ∉ 样本 schema 则判幻觉（字段比对） |
| `tool_success_rate` | ✅ | 回测 / 指标计算工具的 success/total |
| `ks_improvement` | 🟡 Phase C stub | 需人工基线对照组，Phase 0 不做 |
| `false_positive_rate` | ✅ | 回测结果里的 FP / (FP + TN) |
| `rule_interpretability` | 🟡 Phase C stub | 需人工评分或 LLM-judge，Phase 0 不做 |

Phase C stub 指标同样**不假装能跑**——返回 `value=None, method="manual"`。

### 实现参考
- `evaluation/runner/adapters/agent6_report.py` 完整 Phase A 模式
- `evaluation/runner/adapters/agent3_credit.py`（如已存在）看 Phase B adapter 写法

### DoD
- [ ] `evaluation/runner/adapters/agent2_riskctrl.py` 可 import
- [ ] `@register_evaluator("riskctrl")` 挂进 registry
- [ ] `py -m evaluation.runner --list` 包含 `riskctrl`
- [ ] `py -m evaluation.runner --agent riskctrl` 输出 `PARTIAL`

### 冒烟
```bash
py -m evaluation.runner --list
py -m evaluation.runner --agent riskctrl
```

---

## Task B · baseline 首跑（0.5 天）

### DoD
- [ ] `evaluation/results/2_YYYYMMDD.yaml` 落盘
- [ ] 确定性指标全部有值
- [ ] 更新 `evaluation/agent2_riskctrl.yaml` 的 `baseline` 区块
- [ ] **红线闸门**：
  - `hallucination_rate <= 0.01` ✅
  - `evidence_rate >= 0.98` ✅
  - `task_completion_rate >= 0.95` ✅
  - 任一不过 → 写 `docs/progress/agent2-phase-0-gap.md` 不强改

### 冒烟
```bash
py -m pytest agent_riskctrl/ -q
ls evaluation/results/2_*.yaml
```

---

## 红区边界

- ❌ `shared/` / `docs/contracts/` —— A-004 §〇
- ❌ 其他 agent_* 目录
- ❌ `web/` 前端
- ❌ `evaluation/runner/` framework 核心文件（`base_evaluator.py` / `registry.py` / `cli.py` / `__main__.py`）
- ❌ Phase 0 **不做产品化**

允许：
- ✅ `evaluation/runner/adapters/agent2_riskctrl.py` 新增
- ✅ `evaluation/agent2_riskctrl.yaml` 补 baseline 字段
- ✅ `agent_riskctrl/tests/fixtures/*` 新增
- ✅ Agent2 现有 code bug 修复（记录在 `docs/progress/agent2-phase-0-bugs.md`）

---

## Commit / Signal

R-A/B/C 硬规则同 Agent4。

### Milestone

| 时点 | Signal |
|---|---|
| 读完 onboarding | `AGENT2-PHASE-0-ACK` |
| adapter 挂通 | `AGENT2-ADAPTER-READY` |
| baseline 落盘 | `AGENT2-BASELINE-FIRST-RUN` |
| ready for review | `AGENT2-PHASE-0-READY-FOR-REVIEW` |
| Review 通过收工 | `WINDOW-CLOSED-CLEAN` |

---

## Q/A

对 onboarding 有疑问 → `docs/handoff/decisions-log.md` 写 `Q-NNN` → commit trailer `Signal: Q-NNN-RAISED`。不要私下决定。

---

## ACK

```bash
git commit --allow-empty -m "ack(agent2): Phase 0 onboarding absorbed" -m "" -m "Signal: AGENT2-PHASE-0-ACK"
```

Task A → B 顺序推进。
