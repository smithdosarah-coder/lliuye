# -*- coding: utf-8 -*-
"""
Agent2 · 风控策略 · v3.1 DSL + 回测

定位（不可跨界）：
  输入策略诉求 + 样本 CSV → 输出 DSL 风控规则 + 回测指标（KS / 通过率 / 坏账率）。
  不做个案决策（那是 Agent3）。

工具域（MCP 式拆分）：
  - DSL 生成域：从自然语言策略诉求生成可执行 DSL 规则
      入口：rule_engine
  - 回测域：样本 CSV 喂给规则，跑历史回测
      入口：backtesting
  - 指标分析域：KS / AUC / 通过率 / 坏账率计算，规则可解释性评估
      入口：metrics

架构核心：
  与 Agent3 的区别 —— Agent3 是"对一个客户做多维判断"，Agent2 是"对一批客户用一条规则筛"。
  两者都走规则引擎，但规则的生命周期不同：Agent2 的规则是策略产物（可迭代），Agent3 的规则是红线（刚性）。

工具域公开 API（`<域>_<动作>` 命名）都在 `agent_riskctrl.domains` 子包下：
  `from agent_riskctrl.domains import dsl_gen_parse_from_llm, backtest_run, ...`
"""

