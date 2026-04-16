# -*- coding: utf-8 -*-
"""风控策略运营 Agent — 核心逻辑

三大能力：
1. 策略配置助手：自然语言 -> 结构化规则（LLM）
2. 策略效果回溯分析：CSV数据 + 规则 -> 回测报告
3. 差错案件智能分析：误杀/漏杀 -> 优化建议
"""

from __future__ import annotations

import sys
import os
import json
import re
from typing import Generator

# 将项目根目录加入路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.base_agent import BaseAgent
from .prompts import SYSTEM_RULE_PARSER, SYSTEM_BACKTEST_ANALYSIS, SYSTEM_ERROR_ANALYSIS
from .rule_engine import RuleSet, parse_natural_language_rules, apply_ruleset
from .backtesting import load_csv_data, run_backtest, BacktestResult, _summarize_data
from .metrics import (
    calculate_confusion_matrix,
    calculate_ks,
    calculate_psi,
    format_metrics_report,
)


class RiskControlAgent(BaseAgent):
    """风控策略运营Agent：策略配置 / 回测分析 / 差错分析"""

    agent_name = "risk_control"
    agent_title = "风控策略运营"

    def process_message(
        self,
        user_message: str,
        uploaded_files: list[str] | None = None,
    ) -> Generator[dict, None, None]:
        """主入口：根据用户意图分流到三大流程。"""

        intent = self._detect_intent(user_message, uploaded_files)

        if intent == "backtest":
            yield from self._flow_backtest(user_message, uploaded_files)
        elif intent == "error_analysis":
            yield from self._flow_error_analysis(user_message, uploaded_files)
        else:
            yield from self._flow_rule_config(user_message, uploaded_files)

    # ==================================================================
    # 意图检测
    # ==================================================================

    def _detect_intent(
        self, message: str, files: list[str] | None
    ) -> str:
        """简单关键词意图检测。"""
        msg = message.lower()
        has_csv = bool(
            files
            and any(
                f.lower().endswith((".csv", ".xlsx", ".xls")) for f in files
            )
        )

        error_keywords = ["差错", "误杀", "漏杀", "误判", "漏判", "错误案例", "误伤"]
        backtest_keywords = ["回测", "回溯", "验证", "效果", "历史数据"]

        if any(kw in msg for kw in error_keywords):
            return "error_analysis"
        if has_csv and any(kw in msg for kw in backtest_keywords):
            return "backtest"
        if has_csv and not any(kw in msg for kw in error_keywords):
            return "backtest"
        return "rule_config"

    # ==================================================================
    # 流程1: 策略配置助手
    # ==================================================================

    def _flow_rule_config(
        self, user_message: str, uploaded_files: list[str] | None
    ) -> Generator[dict, None, None]:
        """自然语言 -> 结构化风控规则"""

        yield self._thinking("解析策略意图...")

        # 如果有CSV文件，先读取数据摘要作为参考
        data_context = ""
        if uploaded_files:
            for fp in uploaded_files:
                if fp.lower().endswith((".csv", ".xlsx", ".xls")):
                    try:
                        df = load_csv_data(fp)
                        data_context = (
                            f"\n\n参考数据字段（来自上传文件）：\n"
                            f"{', '.join(df.columns.tolist())}\n"
                            f"数据示例:\n{df.head(3).to_string(index=False)}"
                        )
                    except Exception:
                        pass
                    break

        user_prompt = f"请将以下策略意图转换为结构化规则：\n\n{user_message}{data_context}"

        yield self._tool_call("llm_parse_rules")
        try:
            llm_result = self.llm_json(
                system=SYSTEM_RULE_PARSER,
                user=user_prompt,
            )
            if not isinstance(llm_result, dict):
                llm_result = {"rules": llm_result} if isinstance(llm_result, list) else {}
        except Exception as e:
            yield self._tool_result("llm_parse_rules", f"LLM调用失败: {e}")
            yield self._message(f"策略解析失败: {e}")
            yield self._done("策略解析失败")
            return

        yield self._tool_result("llm_parse_rules", "规则解析完成")

        # 解析为 RuleSet
        ruleset = parse_natural_language_rules(llm_result)

        if not ruleset.rules:
            yield self._message("未能从您的描述中提取出有效规则，请尝试更具体的描述。")
            yield self._done("未生成有效规则")
            return

        # 格式化规则列表
        report = self._format_ruleset(ruleset)
        yield self._message(report)
        yield self._done("策略配置完成")

    # ==================================================================
    # 流程2: 策略效果回溯分析
    # ==================================================================

    def _flow_backtest(
        self, user_message: str, uploaded_files: list[str] | None
    ) -> Generator[dict, None, None]:
        """读取CSV数据，回测策略效果"""

        if not uploaded_files:
            yield self._message("请上传历史授信数据文件（CSV/Excel），我将为您进行策略回测。")
            yield self._done("等待数据上传")
            return

        # 1. 读取数据
        yield self._thinking("读取历史数据...")
        csv_path = None
        for fp in uploaded_files:
            if fp.lower().endswith((".csv", ".xlsx", ".xls")):
                csv_path = fp
                break

        if not csv_path:
            yield self._message("未找到CSV/Excel数据文件，请上传正确格式的文件。")
            yield self._done("无有效数据文件")
            return

        try:
            df = load_csv_data(csv_path)
        except ValueError as e:
            yield self._message(f"数据加载失败: {e}")
            yield self._done("数据加载失败")
            return

        yield self._message(
            f"已加载数据: **{len(df)}** 行 x **{len(df.columns)}** 列\n\n"
            f"字段: {', '.join(df.columns.tolist())}"
        )

        # 2. 用LLM生成规则
        yield self._thinking("分析数据特征，生成风控策略...")
        data_summary = _summarize_data(df)

        user_prompt = (
            f"用户指令: {user_message}\n\n"
            f"请根据以下数据摘要生成风控策略规则：\n\n{data_summary}"
        )

        yield self._tool_call("llm_generate_rules")
        try:
            llm_result = self.llm_json(
                system=SYSTEM_RULE_PARSER,
                user=user_prompt,
            )
            if not isinstance(llm_result, dict):
                llm_result = {"rules": llm_result} if isinstance(llm_result, list) else {}
        except Exception as e:
            yield self._tool_result("llm_generate_rules", f"失败: {e}")
            yield self._message(f"策略生成失败: {e}")
            yield self._done("策略生成失败")
            return

        yield self._tool_result("llm_generate_rules", "规则生成完成")
        ruleset = parse_natural_language_rules(llm_result)

        if not ruleset.rules:
            yield self._message("未能生成有效策略规则，请尝试提供更具体的策略要求。")
            yield self._done("无有效规则")
            return

        yield self._message(self._format_ruleset(ruleset))

        # 3. 执行回测
        yield self._tool_call("backtest")
        backtest_result = run_backtest(df, ruleset)
        yield self._tool_result(
            "backtest",
            f"通过{backtest_result.approved} | "
            f"拒绝{backtest_result.rejected} | "
            f"人工{backtest_result.manual_review}",
        )

        # 4. 格式化回测结果
        bt_report = self._format_backtest_result(backtest_result)

        # 5. LLM分析回测结果
        yield self._thinking("AI分析回测结果...")
        try:
            analysis = self.llm_chat(
                system=SYSTEM_BACKTEST_ANALYSIS,
                user=f"回测结果如下：\n\n{bt_report}",
            )
            yield self._message(f"## 回测结果\n\n{bt_report}\n\n## AI分析\n\n{analysis}")
        except Exception:
            yield self._message(f"## 回测结果\n\n{bt_report}")

        yield self._done("回测分析完成")

    # ==================================================================
    # 流程3: 差错案件智能分析
    # ==================================================================

    def _flow_error_analysis(
        self, user_message: str, uploaded_files: list[str] | None
    ) -> Generator[dict, None, None]:
        """分析误杀/漏杀案例，优化策略"""

        yield self._thinking("准备差错分析...")

        # 读取数据
        case_data = ""
        if uploaded_files:
            yield self._tool_call("read_files")
            try:
                file_contents = self.read_files(uploaded_files)
                case_data = (
                    file_contents
                    if isinstance(file_contents, str)
                    else str(file_contents)
                )
            except Exception as e:
                case_data = f"文件读取失败: {e}"
            yield self._tool_result("read_files", f"已读取 {len(uploaded_files)} 个文件")

        if not case_data.strip():
            case_data = "（无上传数据，仅基于用户描述分析）"

        # LLM差错分析
        yield self._tool_call("error_analysis")
        user_prompt = (
            f"用户描述：{user_message}\n\n"
            f"案件数据：\n{case_data[:5000]}"
        )

        try:
            analysis = self.llm_chat(
                system=SYSTEM_ERROR_ANALYSIS,
                user=user_prompt,
            )
            yield self._tool_result("error_analysis", "分析完成")
            yield self._message(f"## 差错案件分析报告\n\n{analysis}")
        except Exception as e:
            yield self._tool_result("error_analysis", f"分析失败: {e}")
            yield self._message(f"差错分析失败: {e}")

        yield self._done("差错分析完成")

    # ==================================================================
    # 格式化辅助
    # ==================================================================

    def _format_ruleset(self, ruleset: RuleSet) -> str:
        """格式化RuleSet为Markdown"""
        lines = [f"## 风控策略规则集", ""]
        if ruleset.description:
            lines.append(f"**策略说明：** {ruleset.description}")
            lines.append("")

        lines.append(
            "| 优先级 | 规则ID | 名称 | 条件 | 动作 |"
        )
        lines.append("|--------|--------|------|------|------|")

        for rule in ruleset.rules:
            cond_str = " AND ".join(
                f"`{c.field} {c.operator} {c.value}`"
                for c in rule.conditions
            )
            action_cn = {
                "approve": "通过",
                "reject": "拒绝",
                "manual_review": "人工审查",
            }.get(rule.action, rule.action)
            lines.append(
                f"| {rule.priority} | {rule.rule_id} | {rule.name} "
                f"| {cond_str} | {action_cn} |"
            )

        lines.append("")
        for rule in ruleset.rules:
            if rule.description:
                lines.append(f"- **{rule.rule_id}** {rule.name}：{rule.description}")

        return "\n".join(lines)

    def _format_backtest_result(self, result: BacktestResult) -> str:
        """格式化BacktestResult为Markdown"""
        lines = [
            f"**数据总量**: {result.total_records} 行",
            f"**通过**: {result.approved} ({result.approved / result.total_records * 100:.1f}%)"
            if result.total_records > 0
            else f"**通过**: {result.approved}",
            f"**拒绝**: {result.rejected} ({result.rejected / result.total_records * 100:.1f}%)"
            if result.total_records > 0
            else f"**拒绝**: {result.rejected}",
            f"**人工审查**: {result.manual_review} ({result.manual_review / result.total_records * 100:.1f}%)"
            if result.total_records > 0
            else f"**人工审查**: {result.manual_review}",
            f"**通过率**: {result.approval_rate:.2%}",
            "",
        ]

        # 各规则命中详情
        rule_stats = result.metrics.get("rule_stats", [])
        if rule_stats:
            lines.append("### 各规则命中详情")
            lines.append("| 规则ID | 名称 | 动作 | 命中数 | 命中率 |")
            lines.append("|--------|------|------|--------|--------|")
            for rs in rule_stats:
                lines.append(
                    f"| {rs['rule_id']} | {rs['rule_name']} | {rs['action']} "
                    f"| {rs['hit_count']} | {rs['hit_rate']:.2%} |"
                )
            lines.append("")

        return "\n".join(lines)
