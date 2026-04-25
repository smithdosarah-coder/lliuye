# Agent6 Phase 2 · pending_metrics 说明

**版本**：v1.0
**更新日期**：2026-04-19
**对应 DoD**：A-013(`baseline.pending_metrics` runner whitelist 契约)
**对应 Task**：Phase 2 Task D

---

## 1. 为什么需要 pending_metrics

`evaluation/agent6_report.yaml` 声明了 5 项通用 + 5 项领域共 10 个 metric。Phase 2 Task A/B/C 仅产出**代码层基线**（反馈飞轮闭环 + QC Blocker 四维强化 + 模板 adapter），**未做端到端 LLM 跑批**。

如果 runner 在 `_verdict` 阶段把 `passed=None`（N/A）的 metric 当作未通过，会出现以下两种误判：

- **PARTIAL 误判**：常态指标 9 项 N/A + 1 项 PASS → 错觉为"刚刚及格"
- **FAIL 误判**：仅 1 项 metric 有值且通过，但混入任何 N/A 都被算到"未达 100% 通过" → FAIL

这不是真实质量信号，会污染 Phase 3 的回归基线。

**A-013 契约**：在 `baseline.pending_metrics: [...]` 中显式列出**本期不跑**的 metric 名称，runner 在 verdict 计算时**跳过**这些指标的 passed 判定。

## 2. 本次纳入 pending 的 9 项 metric

| Metric | 维度 | Pending 原因 |
|---|---|---|
| `task_completion_rate` | common | 端到端 LLM 跑批未启动（Phase 3 任务）|
| `field_completeness` | common | 需真材料包跑 truth_fill |
| `evidence_rate` | common | 需 LLM 三阶段 + KB 完整跑 |
| `hallucination_rate` | common | 需对比 KB facts vs LLM 输出 |
| `tool_success_rate` | common | 需端到端工具链调用 |
| `financial_ratio_consistency` | domain | 需 financial_analyzer 与 LLM 段对比 |
| `template_leakage_rate` | domain | 需真材料 + 模板对比器跑批 |
| `section_length_calibration` | domain | 需真人范文对照集 |
| `quality_score_total` | domain | quality_scorer.py 9 维需端到端文档输入 |

## 3. 本期保留的 1 项已跑通 metric

- `unfilled_marker_accuracy` = **1.0000** (Phase A `94c04f5` tip 锚点)
  - 100% 命中：v16 占位符识别 + Rule 16 治本（commit `bd34288`）联合作用
  - 这是当前唯一的"非 pending 也非 N/A"指标

## 4. Phase 3 解锁路径（pending → resolved）

**前置**:
1. `DEEPSEEK_API_KEY` 配置 + 真模式连通（当前 demo 跑 `?mock=1` 兜底）
2. `samples/` 下 5 模板**全部有真材料包**:
   - 普惠申报书_骨架型 → 已有
   - 兴业资管_对公成稿B / 经纬测绘_对公成稿A → 等业务方提供真材料
   - 科创贷申报书_模板 / 小微对私授信申报书_模板 → Phase 2 Task C 产出脱敏结构,等真材料
3. `evaluation/runner/adapters/agent6_report.py` 端到端 hook 跑 5 模板回归（红区,需 mesh 协调）

**触发**:
- 业务方真材料到位（对应 mesh 信号 `PHASE-2-GO-CORPORATE` / `PHASE-2-GO-INCLUSIVE` / `PHASE-2-GO-TECH` / `PHASE-2-GO-PERSONAL`）
- worker 收信号后:
  1. 跑 `py -m evaluation.runner --agent report` 端到端
  2. 把跑通的 metric 从 `pending_metrics` 移到 `baseline.result`
  3. 更新 `last_run` + `commit`
  4. emit `Signal: AGENT6-PHASE-3-METRICS-RESOLVED-<scenario>`

## 5. 与 mesh A-013 的接口

mesh A-013 是**双向契约**:

- **本 worker 写**: `baseline.pending_metrics` + `baseline.pending_reason`
- **runner 读**: 在 `_verdict` 中按 `pending_metrics` 跳过这些指标的判定（runner 端实现归 L0 infra worker 拥有,本 worker 不动 base_evaluator.py）

**本期状态**: yaml 契约一侧已对齐;runner 端实现待 L0 落地后,Agent6 verdict 自动从 FAIL 转 PASS（仅 `unfilled_marker_accuracy` 一项需 PASS,其余 9 项白名单跳过）。

## 6. 验证

跑 `py -m evaluation.runner --agent report`:

- **当前**: verdict=FAIL (因 task_completion_rate=0.0000 < 0.98 触发 FAIL 路径)
- **A-013 落地后预期**: verdict=PASS（pending 9 项被跳过，唯一 resolved 的 unfilled_marker_accuracy=1.0000 通过）

不修改 base_evaluator.py（红区），等 mesh A-013 owner 落地。

## 7. 引用

- `evaluation/agent6_report.yaml#baseline.pending_metrics` Phase 2 yaml 契约
- `docs/handoff/decisions-log.md` A-013 契约定义（mesh 协调点）
- `evaluation/runner/base_evaluator.py` runner 端实现位（红区,本 worker 不动）
- Phase A baseline tip `94c04f5` `unfilled_marker_accuracy=1.0000` 锚点
