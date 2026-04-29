## Block A · PRD Master + 6 Sub Spec

**改**
A7 不应直接把 10 个 G-XX 写成“功能 backlog”。先把 `docs/audit/prd-evidence-frozen.md:88-99` 的 G-01..G-10 升级为 5 列 drift table：`Original Intent / Current Repo State / Keep-Revert-Rewrite / Evidence / Owner+Deadline+Acceptance`。证据源固定为飞书 7 doc + 本地 fallback，已在 `docs/audit/prd-evidence-frozen.md:14-46` 列出。

**坚持**
产物必须满足 Phase A 硬线 #7：`docs/prd/master-2026-04-29.md` + 6 sub-PRD v1 + 飞书双写，见 `docs/reset/phase-a-charter.md:17`、`docs/reset/phase-a-charter.md:128-134`。双写流程按 `lark-doc`：wiki URL 先 `wiki spaces get_node` 取 `obj_token`，再 create/update docx，不直接拿 wiki token 当 file token。

**对方弱点**
容易被 worker onboarding 锚定成“补 PRD 文档”，但真正缺口是 PRD intent 和当前 repo shape 的裁决表；也容易把 Agent6 v15/v16 当 PRD 范围问题，其实 legacy_gradio 是 Block B 的隔离问题。

**吸收对方**
如果 worker 已做飞书节点结构，应吸收 node_token、目录位置、权限信息，但不吸收任何未带 repo 证据行号的产品判断。

**v2 final**
`docs/prd/master-2026-04-29.md` 章节大纲：
1. North Star：RM Workbench，不是 6 单页 showroom，证据 `RESET_MASTER_PLAN.md:16-20`、`docs/reset/north-star.md:83-87`
2. 用户角色：客户经理 / 审贷员 / 合规官 / 风险经理，消除“策略经理”漂移，证据 `CLAUDE.md:5`、`CLAUDE.md:82`
3. 6 Agent 边界：沿用 `CLAUDE.md:77-88`
4. Cross-agent handoff：Agent1→Agent6、Agent6→Agent3、Agent3→Agent6
5. Evaluation reset：见 Block C
6. Drift table：10 G-XX 全量裁决
7. Delivery plan：A3/A4/A6/A7/B1 owners + deadline + acceptance
8. Feishu double-write log：wiki/doc token、更新时间、责任人

6 sub-PRD 只写 v1 大纲，不写长正文：
- `docs/prd/agent1-channel-v1.md`：look-alike 获客、KB 上传、外网企业池、Top10 线索、产品推荐；覆盖 G-01/G-02
- `docs/prd/agent2-riskctrl-v1.md`：自然语言 DSL、回测、case diagnosis、报告导出；覆盖 G-03/G-04
- `docs/prd/agent3-credit-v1.md`：消费 ReportJSON、90 秒 dashboard、授信建议、回写审批意见；覆盖 G-05/G-06
- `docs/prd/agent4-alert-v1.md`：在贷客户池、内外双路命中、红黄绿榜、drill；覆盖 G-07
- `docs/prd/agent5-compliance-v1.md`：政策事件触发、规则/事件 N×M、业务单号级榜单；覆盖 G-08/G-09
- `docs/prd/agent6-report-v1.md`：v16 主线、ReportJSON、Word 导出、工具栏真实后端；覆盖 G-10

## Block B · legacy_gradio 5 件实施方案

**改**
不要真删 `legacy_gradio/`。PM 已裁决“v16 真稳前不真删”，见 `docs/audit/conflict-register-v1.md:331-342`；当前风险是它仍可 import，见 `docs/audit/conflict-register-v1.md:178`。

**坚持**
全栈隔离：默认不可 import、不可 lint、不可 test、不可 coverage、不可 mypy、不可被 worker 默认阅读。`CLAUDE.md:12` 现在还写“fallback 演示从 archive 恢复”，必须改成“全栈隔离，详 §15”。

**对方弱点**
如果对方主张真删，会破坏客户侧 v15 演示备用路径；如果只改文档不加 import guard，生产代码仍可误 import。

**吸收对方**
可吸收“最终真删”的方向，但必须以 PM `Authorize-By` trailer + v16 客户真实材料验证完成为前置。

**v2 final**
1. 新增 `legacy_gradio/__init__.py`：

```python
"""Archived Gradio report assistant.

This package is isolated by default. Set ALLOW_LEGACY_GRADIO=1 only for an
explicit emergency demo fallback approved by PM.
"""

from __future__ import annotations

import os

if os.getenv("ALLOW_LEGACY_GRADIO") != "1":
    raise ImportError(
        "legacy_gradio is archived and isolated. "
        "Set ALLOW_LEGACY_GRADIO=1 only for an explicit emergency fallback."
    )
```

2. `pyproject.toml`：
- `[tool.ruff].exclude` 在 `pyproject.toml:43-53` 加 `"legacy_gradio"`
- `[tool.mypy].exclude` 在 `pyproject.toml:94-102` 加 `"^legacy_gradio/"`
- `[tool.pytest.ini_options].addopts` 在 `pyproject.toml:118-122` 加 `"--ignore=legacy_gradio"`
- `[tool.coverage.run].omit` 在 `pyproject.toml:140-146` 加 `"legacy_gradio/*"`

3. `CLAUDE.md` 新增 §15：
- archived 备用：只为 v15 客户演示 emergency fallback
- 解锁路径：PM 明确授权 + `ALLOW_LEGACY_GRADIO=1` + 不接入 `api_server.py` / `web/`
- 真删条件：PM 判定 v16 客户真实材料稳定 + worker PR + `Authorize-By` trailer + `git rm -rf legacy_gradio/`

4. `CLAUDE.md §2` 改 `CLAUDE.md:12`：
从“如需 fallback 演示从 archive 恢复”改为“已全栈隔离，默认不可 import；紧急解锁路径详 §15”。

5. Worker onboarding template：
在主 CLI 每次写 `docs/onboarding/<task>.md` 的模板处加入默认提示：`不读 legacy_gradio/，不引用 legacy_gradio/，除非 PM 显式解锁并设置 ALLOW_LEGACY_GRADIO=1`。调度模板位置参考 `docs/reset/codex-mesh-protocol.md:293-304`。

## Block C · Active Rule + Cat 16 + Cat 12

**改**
Cat 1 只接 A7 范围内 3 条 active rule 回写，不抢主 CLI 的 `/design`、Cat15 sync。Cat12 全部重定义指标，不只 bump 版本号。Cat16 采用“策略经理→风险经理”全栈搜替。

**坚持**
active decision 必须回写 root `CLAUDE.md`，这是 PM 硬线，见 `RESET_MASTER_PLAN.md:57-63`、`RESET_MASTER_PLAN.md:77-86`。

**对方弱点**
只改 eval yaml 版本号会继续让 runner stub 假绿；只改 CLAUDE 文案不改 runtime prompt，会让 `api_server.py:376` 继续污染 IM 场景。

**吸收对方**
如果 A1 已落地 naming SSOT，则 A7 只消费 SSOT，不重复定义 agent_id；但 PRD 用户故事仍必须统一成“风险经理”。

**v2 final**
3 active rule 回写 `CLAUDE.md`：
1. Q-040：Agent2 backtest `MAX_ROWS=50000` 是正式规则，不得降回 500；证据 `docs/audit/sub-agent-step2-round1/instruction.md:25`
2. Q-041：candidate metadata 必含 `industry / geo / scale / similarity` 4 字段；证据 `docs/audit/sub-agent-step2-round1/instruction.md:26`
3. PIPL：LLM fallback chain 境内优先，生产 Agent 不得绕过 shared LLM fallback；证据 `docs/audit/sub-agent-step2-round1/instruction.md:27`、`CLAUDE.md:175`

Cat16 改动：
- `CLAUDE.md:82`：Agent2 触发人改“风险经理发起”
- `api_server.py:376`：IM prompt 改“辅助风险经理写 DSL”
- `web/src/lib/store/types.ts:28`：审贷官改审贷员
- `auth_service/users.py:46-50` 保留 `risk_manager`
- PRD 用户故事全部写“风险经理”，不再出现“策略经理”
- 全仓 `rg "策略经理"` 应 0 命中，除 historical audit docs 可保留

Cat12 8 个 Rewrite 指标方案，证据 `docs/audit/conflict-register-v1.md:187-195`：
1. Agent2 yaml/api version 对齐：不只 v4.0，新增 `dsl_validity_rate / backtest_metric_accuracy / case_diagnosis_coverage / export_report_success`
2. Agent3 yaml/api version 对齐：新增 `reportjson_consumption_rate / redline_accuracy / decision_consistency / handoff_writeback_success`
3. Agent4 yaml/api version 对齐：新增 `cross_hit_precision / internal_transaction_ingest_success / drill_actionability / silent_fallback_rate=0`
4. Agent5 yaml/api version 对齐：新增 `policy_event_trigger_success / matrix_match_precision / business_order_granularity / revision_quality`
5. Agent3 “四维评分”重定义为每 segment 内四维，不声称跨段汇总四维
6. Agent6 `last_run/commit null` 改为基线必须落盘；pending metrics 必须有 owner/date
7. Agent3 `tool_success_rate` stub 改 runtime trace 采集，未采集则 metric 状态 `blocked`，不能 PASS
8. Agent1 common metrics pending 改 runtime dump 采集；SearchProvider 未启用时显式 `blocked_by_env`，不能 silent mock

Cat12 Keep：
- `evaluation/agent1_channel.yaml:3` v4.0 与 API v4.0 保持
- `evaluation/agent6_report.yaml:3` v16 与 `CLAUDE.md:185` 保持

## Dissent Appendix

我反对把 A7 变成“PRD 写手”。A7 的真实价值是裁决 drift，而不是把旧 PRD 重排版。10 个 G-XX 里至少 G-05/G-06 属 A6 handoff contract + A4 credit/report 实现，不应由 PRD 文档假装完成。

我也反对立即真删 `legacy_gradio/`。从工程洁癖看真删最干净，但 PM 已说明客户侧演示仍用 v15，`agent_report` wrapper 也标 unreleased。正确做法是默认不可 import + 工具链全排除 + PM 授权解锁，而不是删除备用路径。

最后，Cat12 不能用版本号对齐冒充评估修复。评估漂移的核心是指标语义和 runtime trace 缺失，必须把 stub 变成 blocked/pending，而不是 PASS。