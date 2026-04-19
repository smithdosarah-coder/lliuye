# Agent4 预警 · Phase 0 Onboarding（baseline 首跑）

**对应 worktree**：`D:\claude code\demo-agent4`（`feat/agent4-productize`，主 CLI 创建后交付）
**发布日期**：2026-04-19
**前置**：已读 `AGENT_IDENTITY.md` + `CLAUDE.md` + 本文
**目标**：**不做 productize**，只把 Agent4 的 evaluation runner 挂通、跑出一版首跑基线，让后续 Phase 1 productize 有量化锚点。

---

## 为什么是 Phase 0 而不是 Phase 1

CLAUDE.md §5.2 硬规则："质量问题先建 rubric、跑基线、找最大 gap，再改代码"。Agent1 已经踩过这个坑（Option 2 没基线先码，review 时发现 runner 不通）。Agent4 不重复这个错误——baseline 跑通后再谈 productize。

---

## Task A · evaluation adapter（1 天）

### 目标
在 `evaluation/runner/adapters/` 下新建 `agent4_alert.py`，对接 `evaluation/agent4_alert.yaml` 的 4 个 domain 指标。

### 实现参考
对照 `evaluation/runner/adapters/agent6_report.py` 和 Agent3 的 `agent3_credit.py`（如已存在）——同样的 `@register_evaluator` + 继承 `BaseEvaluator` 模式。

### Phase 0 仅覆盖可确定性计算的指标

| 指标 | Phase 0 是否实现 | 方法 |
|---|---|---|
| `task_completion_rate` | ✅ | 扫描 100 家客户 fixture，数完成数 |
| `evidence_rate` | ✅ | 每个红/黄灯客户检查是否含 `evidence` 字段 + 非空 |
| `hallucination_rate` | ✅ | 虚构客户/事件检测（白名单外的 entity_id 判为幻觉） |
| `tool_success_rate` | ✅ | 工具调用 stub 的 success/total 比 |
| `cross_hit_precision` | 🟡 Phase C stub | 需真实外部扫描数据 |
| `recall_on_known_bad` | 🟡 Phase C stub | 需标注库 |
| `grade_distribution_sanity` | ✅ | 红/黄/绿分布检查（红 < 5%、绿 > 70%） |
| `scan_latency_p95` | ✅ | 单次扫描耗时 P95 |

未实现的 Phase C 指标 **不要假装能跑**——返回 `value=None, method="manual"`（照 `agent6_report.py` 的 `_stub_metric` 模式）。

### DoD
- [ ] `evaluation/runner/adapters/agent4_alert.py` 可 import 无报错
- [ ] `@register_evaluator("alert")` 挂进 registry
- [ ] `py -m evaluation.runner --list` 能看到 `alert`
- [ ] `py -m evaluation.runner --agent alert` 能跑出 `PARTIAL` 结果（确定性指标有值，Phase C stub 明确 `None`）

### 冒烟（必须实测过才 commit）
```bash
py -m evaluation.runner --list                    # 包含 "alert"
py -m evaluation.runner --agent alert             # 执行，输出到 evaluation/results/
```

---

## Task B · baseline 首跑（0.5 天）

### 目标
在 `feat/agent4-productize` 分支上用 Task A 的 adapter 跑一次 baseline，落盘 `evaluation/results/4_YYYYMMDD.yaml`。

### DoD
- [ ] 跑出 `evaluation/results/4_<8位日期>.yaml` 文件
- [ ] 4 个确定性指标全部有数值（非 N/A）
- [ ] 更新 `evaluation/agent4_alert.yaml` 的 `baseline` 区块 —— `last_run` + `commit`
- [ ] **红线闸门（CLAUDE.md §5.1 + §5.2）**：
  - `hallucination_rate <= 0.01` ✅
  - `evidence_rate >= 0.95` ✅
  - `task_completion_rate >= 0.95` ✅
  - 任一不过 → 标记 `baseline_failed: true`，写 `docs/progress/agent4-phase-0-gap.md`，**不要**强改 adapter 或 fixture 让指标达标

### 冒烟
```bash
py -m pytest agent_alert/ -q                      # 现有测试保持通过
ls evaluation/results/4_*.yaml                    # 基线文件存在
```

---

## 红区边界（守死）

- ❌ 不碰 `shared/` / `docs/contracts/` —— A-004 §〇 红区
- ❌ 不改其他 Agent 的代码（`agent_channel/` `agent_credit/` `agent_report/` 等）
- ❌ 不动 `web/` 前端（frontend CLI 在做）
- ❌ 不修改 `evaluation/runner/base_evaluator.py` / `registry.py` / `cli.py` / `__main__.py` 框架（`de1b6b5` / `705326d` 已锁）
- ❌ **Phase 0 不做产品化**：不加 UI、不改 API endpoint、不加 Pipeline 节点

允许：
- ✅ 新增 `evaluation/runner/adapters/agent4_alert.py`
- ✅ 修改 `evaluation/agent4_alert.yaml`（补充 Phase 0 baseline 字段）
- ✅ `agent_alert/` 内部加 test fixture（`agent_alert/tests/fixtures/*.json` 之类）
- ✅ 如果 Agent4 现有 code 确实有 bug 阻止 baseline 跑通 → 修复 bug（但写 `docs/progress/agent4-phase-0-bugs.md` 记录）

---

## Commit / Signal

**硬规则**（R-A/B/C）：
- **R-A · 冒烟必实测**：commit message 声明的命令必须在当前工作树跑过
- **R-B · 单 commit 单 Signal**：一 commit 一 Signal
- **R-C · cherry-pick 改 Signal**：cross-branch copy 用新 Signal

### 里程碑 Signal

| 时点 | Signal |
|---|---|
| 读完 onboarding | `AGENT4-PHASE-0-ACK` |
| Task A 完成（adapter 挂通） | `AGENT4-ADAPTER-READY` |
| Task B 完成（baseline 落盘） | `AGENT4-BASELINE-FIRST-RUN` |
| 红线闸门全绿，ready for review | `AGENT4-PHASE-0-READY-FOR-REVIEW` |
| Review 通过后收工 | `WINDOW-CLOSED-CLEAN` |

### 主 CLI review 后的下一步

Phase 0 green → 主 CLI 在 `docs/scorecard/GLOBAL.md` 完整度矩阵把 Agent4 从 50% 抬到 ~60%，并下发 `docs/onboarding/agent4-phase-1.md`（productize：仪表盘 + 导出 + 原因码）。

---

## Q/A 协议

对 onboarding 或 spec 有疑问 → **不要私下决定**。流程：
1. 在 worktree 内建 `docs/handoff/agent4-questions.md` 或直接 append `docs/handoff/decisions-log.md` 一个 `Q-NNN` 块
2. commit trailer `Signal: Q-NNN-RAISED`
3. 等主 CLI 写 `A-NNN` 回答后再继续

---

## ACK

```bash
git commit --allow-empty -m "ack(agent4): Phase 0 onboarding absorbed" -m "" -m "Signal: AGENT4-PHASE-0-ACK"
```

随后按 Task A → B 顺序推进。
