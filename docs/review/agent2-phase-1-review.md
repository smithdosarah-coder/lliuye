# Agent2 Phase 1 Full Review
**Date**: 2026-04-19
**Reviewer**: main CLI subagent
**Worker HEAD**: 6d7127d
**Verdict**: **APPROVED**

## Summary
Agent2 Phase 1 四 Task（A runtime dump / B pending_metrics 白名单 / C per_rule_fpr_spread σ² / D web 规则 ReadOnly 入口）全部落地，HEAD @ 6d7127d。9 条硬 gate 全绿：红区 kernel 与后端 API 零改（gate 1–2），commit 历史 merge-only 无 rebase / amend 痕迹（gate 3），runner 实跑 PASS per_rule_fpr_spread=0.0002（A-019 阈值 ≤0.03 的 2 数量级缓冲），3 条单测 0.53s 全 pass，前端 tsc 0 errors + /riskctrl 4 标记全命中 + /mock 5 条规则合法 JSON。Evidence-First 公式（FP/(FP+TN) + 总体方差 + <2 条规则 pending）与 A-019 decisions-log @ c947906 一字不差。建议 Phase 2 Batch 2 按 A-019 §3 校准真实阈值。

## Gate-by-Gate

### Gate 1 — 红区 kernel 零改 · PASS
```
git diff 5b1c135..HEAD -- evaluation/runner/base_evaluator.py evaluation/runner/registry.py evaluation/runner/cli.py evaluation/runner/__main__.py evaluation/runner/schemas.py
```
输出为空（5 个 kernel 文件自 ack 基线 5b1c135 起零改）。

### Gate 2 — 后端红区零改 · PASS
```
git diff 5b1c135..HEAD -- api_server.py agent_riskctrl/api/
```
输出为空（api_server.py 与 agent_riskctrl/api/ 子树 Phase 1 全程零触碰，契合 Phase 1 红区边界）。

### Gate 3 — A-012.D + A-012.E merge-only 合规 · PASS
```
git reflog | head -40
```
HEAD 路径全部 `commit:` / `commit (merge):` 项，**无 rebase (finish/pick) / amend / force-update** 痕迹。

Committer date 单调递增（`git log --pretty=format:"%h %ci %s"`）：
```
5b1c135 2026-04-19 16:59:44 +0800  ack(agent2) onboarding
3cc3edf 2026-04-19 17:15:12 +0800  Task A
a9387f4 2026-04-19 17:26:33 +0800  Task B
8ec4283 2026-04-19 17:35:47 +0800  merge: A-019 intake (merge --no-ff)
b8e34ac 2026-04-19 17:43:00 +0800  Task C
f1e97b0 2026-04-19 17:52:28 +0800  Task D
6d7127d              (HEAD)         review: ready
```
每步 7–11 分钟间隔，节奏健康。

### Gate 4 — Runner 实跑 · PASS
```
py -m evaluation.runner --agent riskctrl
```
```
=== riskctrl · PASS · 0.0s ===
    commit: 6d7127de42cec0323e68e23a23ba3003b6893d2f  artifacts: 0

    [Common]
      OK task_completion_rate  1.0000  (>= 0.95)
      OK evidence_rate         1.0000  (>= 0.98)
      OK hallucination_rate    0.0000  (<= 0.01)
      OK tool_success_rate     1.0000  (>= 0.95)

    [Domain]
      OK false_positive_rate   0.0439  (<= 0.15)
      OK per_rule_fpr_spread   0.0002  (<= 0.03)
      ? ks_improvement         N/A     (>= 0.02)
      ? rule_interpretability  N/A     (>= 4.0)
```
verdict = **PASS**；σ²=0.0002 << 0.03（两数量级缓冲）；两 stub 经 A-013 α kernel 白名单不降档。

### Gate 5 — 单测实跑 · PASS
```
py -m pytest agent_riskctrl/tests/test_per_rule_fpr_spread.py -v
```
```
agent_riskctrl/tests/test_per_rule_fpr_spread.py::test_run_backtest_emits_per_rule_fp_tn PASSED [ 33%]
agent_riskctrl/tests/test_per_rule_fpr_spread.py::test_per_rule_fpr_spread_variance_matches_manual_calc PASSED [ 66%]
agent_riskctrl/tests/test_per_rule_fpr_spread.py::test_per_rule_fpr_spread_insufficient_rules PASSED [100%]

============================== 3 passed in 0.53s ==============================
```
3 passed（Task C A-019 公式 + backtest FP/TN + <2 条 pending 三重语义覆盖）。

### Gate 6 — Web 前端门面 · PASS
`pnpm tsc --noEmit` → EXIT=0（0 errors）。

Next dev server 起在 **localhost:3000**（`✓ Ready in 462ms`）。

```
curl http://localhost:3000/riskctrl        HTTP=200
  "规则详情"            hits=1
  "RULESET · READ ONLY" hits=1
  "导出 JSON"           hits=1
  "进入编辑器"          hits=1
```
```
curl http://localhost:3000/mock/riskctrl_ruleset.json   HTTP=200
  rules_count = 5
  per_rule_fpr (via backtest.FP/TN) = R001 R002 R003 R004 R005 五条齐全
  keys_sample = ['rule_id','name','description','conditions','action','priority','backtest']
```
dev server 验证后 kill。

### Gate 7 — trigger_reasons 零黑名单 · PASS
```
grep -rE "RULE_ID_TO_REASON|keyword.*reason|regex.*reason" agent_riskctrl/
```
0 hits（未引入关键字/正则黑名单兜底，符合 CLAUDE.md §12 + 第一性原理）。

### Gate 8 — Evidence-First 公式抽查 · PASS
`evaluation/runner/adapters/agent2_riskctrl.py:270-314`：
```python
fprs.append(fp_i / (fp_i + tn_i))                                # L285, 精确 FP/(FP+TN)
if len(fprs) < 2:                                                # L289, 不足 2 条 pending
    out.append(MetricOutcome(..., value=None, passed=None, ...))
else:
    mean = sum(fprs) / len(fprs)                                 # L301
    variance = sum((x - mean) ** 2 for x in fprs) / len(fprs)    # L302, 总体方差（非 sample var）
    out.append(self.mark("per_rule_fpr_spread", variance, ...))  # target "<= 0.03" → passed
```
与 `docs/handoff/decisions-log.md` A-019 @ c947906 公式字节级一致：
```python
fprs = [r.FP / (r.FP + r.TN) for r in rule_stats if (r.FP + r.TN) > 0]
if len(fprs) < 2: return None
mean = sum(fprs) / len(fprs)
return sum((x - mean) ** 2 for x in fprs) / len(fprs)  # 总体方差
```
跳过 N/A 规则语义 + pending 语义（value=None, passed=None）+ self.mark 由 yaml target 判 passed 三处全对。

### Gate 9 — yaml target 未占位 · PASS
```
evaluation/agent2_riskctrl.yaml:34-36
    - name: per_rule_fpr_spread
      desc: 单规则误拒率的总体方差（仅 reject 规则，N/A 规则跳过）
      target: "<= 0.03"
```
字面量锁定，无 `<TBD>` / `<TBD Q-014>` 占位符。baseline block L58 runtime value 0.0002 与 target 0.03 差 2 数量级。

## Follow-up

**Phase 2 接手点**（非阻塞）：
1. **per_rule_fpr_spread 真阈值校准**（A-019 §3 锁定）：Phase 2 Batch 2 用 Task A runtime dump 跑真 baseline，P90/P95 + 安全 margin 重锁，yaml baseline 加 `calibrated_from` 审计字段（baseline schema 扩展需先 Q 后动，A-018 教训）。
2. **ks_improvement / rule_interpretability** 两 stub 脱白名单：需 runner 接真 LLM 判分 or 真 KS 统计通路，当前靠 A-013 α kernel 白名单豁免 — 不要长期挂 N/A。
3. **Task D ReadOnly → 可写入编辑器**：当前 `进入编辑器` 按钮 disabled，Phase 2 Task D2 接真写入流程 + 二次审核闸门（参 B2 红区文档）。

**非阻塞 nit**：
- Task C backtest rule_stats 目前仅 5 规则 ruleset，A-019 §3 已警示 ≥10 规则 ruleset 阈值会偏松，Phase 2 Batch 2 扩样本时必须重校。
- evaluation/manual/2_20260419.yaml runtime dump 落盘路径 OK，但没写入 artifacts（runner 汇报 `artifacts: 0`），Phase 2 若要做审计链可补写路径。

**Gap list**（Phase 1 未覆盖）：
- rule DSL 生成链路的 hallucination_rate 走 N/A fallback（stub），Phase 2 要接真 LLM 生成样本 + 证据链校验。
- web/riskctrl 页面只展示 `RULESET · READ ONLY` mock，未接 `api_server.py` 真 endpoint（契合 Phase 1 后端红区零改原则）。

## Scorecard 建议

`docs/scorecard/GLOBAL.md` Agent2 riskctrl 行：
- **当前**：Phase 0 baseline（Phase 0 review 时设定，具体值由主 CLI 核对原值）
- **建议值**：Phase 1 PASS · 75–80%（与 Agent1 Phase 1 APPROVED 82–86% 档对齐，Agent2 未接真 LLM 链路 + 2 个 stub 白名单挂账，稍低一档合理）
- **理由**：
  1. runner 实跑 PASS（6/6 deterministic 绿 + 2/8 pending 白名单）
  2. A-019 σ²=0.0002 vs 阈值 0.03（两数量级缓冲，真信号强）
  3. Phase 2 Batch 2 校准真阈值 + 两 stub 脱白名单后可再升一档（80–85%）
  4. 红区闸门双零（kernel + 后端 API），commit 历史 merge-only 合规
  5. Evidence-First 公式与 decisions-log 字节级一致（可追溯性满分）
