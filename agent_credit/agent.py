# -*- coding: utf-8 -*-
"""Agent3 v2.0 — CreditDecisionAgent（授信决策辅助）

定位变更（vs v1.0）：
  - v1.0: 读原始材料 → 五维评分 → A-E 评级 → 审批建议
  - v2.0: 消费 Agent6 的 ReportJSON（或预设 profile） → DecisionEngine 5 段流水线
          → 输出 DecisionAdvice (决策 / 额度 / 期限 / 利率 / 红线 / 附加条件)
          → 回写 Agent6 生成 `{client}_{ts}_decided.docx`

对外契约：
  process_message(user_message, uploaded_files) 仍用 BaseAgent 事件协议（yield dict）。
  user_message 可以是：
    - 空字符串 + uploaded_files[0] 指向 ReportJSON（优先）或 profile JSON
    - 含 "#preset:<name> segment:<corporate|retail>" 标记 → 载入 mock_data 预设
    - 否则提示用户。

额外 API：
  - load_profile_from_report_json(path)
  - load_preset_profile(preset_name, segment)
  - run_decision(profile, segment) -> DecisionAdvice
  - writeback_to_agent6(advice, report_json_path) -> docx_path
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Generator, Literal

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.base_agent import BaseAgent
from shared.report_handoff import (
    load_report_json, apply_decision_writeback,
)

from .decision_engine import DecisionEngine, DecisionPipelineResult
from .advisor_formatter import DecisionAdvice
from .risk_appetite_config import RiskAppetiteConfig

Segment = Literal["corporate", "retail"]

_MOCK_DIR = Path(__file__).parent / "mock_data"


# ---------------------------------------------------------------------------
# Profile 载入辅助
# ---------------------------------------------------------------------------

def _load_preset_profile(preset_name: str, segment: Segment) -> dict:
    sub = "corporate_profiles" if segment == "corporate" else "retail_profiles"
    path = _MOCK_DIR / sub / f"{preset_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"预设 profile 不存在：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _list_preset_profiles(segment: Segment) -> list[str]:
    sub = "corporate_profiles" if segment == "corporate" else "retail_profiles"
    d = _MOCK_DIR / sub
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.json"))


def _profile_from_report_json(report_json: dict) -> dict:
    """把 Agent6 ReportJSON 转成对公 profile dict（FeatureExtractor 可消费）。"""
    facts = report_json.get("facts", {}) or {}
    sections = report_json.get("sections", {}) or {}

    # 从 facts 优先取；缺的再从正文正则兜底
    full_text = "\n".join(sections.get(k, "") or "" for k in ("ch1", "ch2", "ch3", "ch4"))

    def _grab_num(pat: str) -> float:
        m = re.search(pat, full_text)
        if not m:
            return 0.0
        try:
            return float(m.group(1).replace(",", ""))
        except (ValueError, TypeError):
            return 0.0

    def _amount_wan(raw: str) -> float:
        if not raw:
            return 0.0
        m = re.search(r"([0-9,.]+)", raw)
        if not m:
            return 0.0
        try:
            num = float(m.group(1).replace(",", ""))
        except (ValueError, TypeError):
            return 0.0
        if "亿" in raw:
            return num * 10000
        return num

    profile: dict = {
        "company_name": report_json.get("client_name", "") or facts.get("company_name", ""),
        "industry": facts.get("industry", ""),
        "establishment_date": facts.get("establishment_date", ""),
        "registered_capital": facts.get("registered_capital", ""),
        "legal_representative": facts.get("legal_representative", ""),
        "employee_count": int(_grab_num(r"员工[人数：:]*\s*([0-9,]+)")) or 0,
        "financial": {
            "revenue": _amount_wan(facts.get("revenue_latest", "")),
            "net_profit": _amount_wan(facts.get("profit_latest", "")),
        },
        "request": {
            "amount": _amount_wan(facts.get("credit_amount_requested", "")) or 300,
            "term_months": 0,
            "purpose": "",
        },
        "_source_report_json": True,
        "_report_sections_preview": {k: (v or "")[:200] for k, v in sections.items()},
    }

    # 期限：'3 年' → 36 个月
    term_str = facts.get("term_requested", "")
    m_term = re.search(r"(\d+)", term_str or "")
    if m_term:
        profile["request"]["term_months"] = int(m_term.group(1)) * 12

    # ReportJSON extras 兜底（如 Agent6 已产出结构化财务）
    extras = report_json.get("extras", {}) or {}
    if isinstance(extras.get("financial"), dict):
        profile["financial"].update(extras["financial"])
    if isinstance(extras.get("request"), dict):
        profile["request"].update(extras["request"])

    return profile


# ---------------------------------------------------------------------------
# CreditDecisionAgent v3.1
# ---------------------------------------------------------------------------

class CreditDecisionAgent(BaseAgent):
    """授信决策辅助 v3.1 — 消费 ReportJSON → DecisionAdvice → 回写 Agent6 docx"""

    agent_name = "credit_decision"
    agent_title = "授信决策辅助 v3.1"

    def __init__(self, api_key: str = "", model_provider: str = "deepseek",
                 base_url: str = "", model_name: str = "",
                 appetite_corp: RiskAppetiteConfig | None = None,
                 appetite_retail: RiskAppetiteConfig | None = None):
        super().__init__(api_key=api_key, model_provider=model_provider,
                         base_url=base_url, model_name=model_name)

        # PB#3 (2026-05-06 · Q-053): Agent3 LLM 迁 shared.llm_caller
        # 替代 BaseAgent.llm_chat / llm_json (root llm.LLMClient 旧入口) ·
        # 走 PIPL fallback chain (deepseek + dashscope) + audit hook (region 字段)
        # caller 构造失败 fallback 到 BaseAgent (向下兼容 · 不破现有流程)
        try:
            from shared.llm_caller import make_text_caller, make_json_caller
            chat_func = make_text_caller(
                agent_id="credit",
                endpoint="/api/credit/decision",
                api_key=api_key,
            )
            json_func = make_json_caller(
                agent_id="credit",
                endpoint="/api/credit/decision",
                api_key=api_key,
            )
        except ImportError:
            chat_func = self.llm_chat
            json_func = self.llm_json

        self.engine = DecisionEngine(
            llm_chat_func=chat_func,
            llm_json_func=json_func,
            appetite_corp=appetite_corp,
            appetite_retail=appetite_retail,
        )
        # 最近一次运行结果，供 UI/writeback 使用
        self.last_result: DecisionPipelineResult | None = None
        self.last_report_json_path: str = ""
        self.last_segment: Segment = "corporate"

    # ------------------------------------------------------------------
    # BaseAgent 协议：process_message
    # ------------------------------------------------------------------

    def process_message(
        self,
        user_message: str,
        uploaded_files: list[str] | None = None,
    ) -> Generator[dict, None, None]:
        """user_message 格式约定：
          - "#preset:zhongrui_network segment:corporate"
          - "#report_json:<path>"
          - 否则若 uploaded_files[0] 存在且为 JSON，视作 ReportJSON
        """

        # ---- 1. 解析输入，拿到 (profile, segment) ----
        segment: Segment = "corporate"
        profile: dict | None = None
        report_json_path = ""

        msg = user_message or ""
        m_seg = re.search(r"segment:(corporate|retail)", msg)
        if m_seg:
            segment = m_seg.group(1)  # type: ignore
        m_preset = re.search(r"#preset:([\w\-]+)", msg)
        m_rjson = re.search(r"#report_json:(\S+)", msg)

        try:
            if m_preset:
                yield self._thinking(f"载入预设 profile：{m_preset.group(1)}（{segment}）")
                profile = _load_preset_profile(m_preset.group(1), segment)
            elif m_rjson:
                report_json_path = m_rjson.group(1)
                yield self._thinking(f"解析 ReportJSON：{report_json_path}")
                rj = load_report_json(report_json_path)
                profile = _profile_from_report_json(rj)
                segment = "corporate"  # Agent6 报告目前只产对公
            elif uploaded_files:
                first = uploaded_files[0]
                if str(first).lower().endswith(".json"):
                    report_json_path = first
                    yield self._thinking(f"解析上传的 ReportJSON：{first}")
                    rj = load_report_json(first)
                    # 判定是 ReportJSON 还是直接 profile
                    if "sections" in rj and "facts" in rj:
                        profile = _profile_from_report_json(rj)
                        segment = "corporate"
                    else:
                        profile = rj
                        # 简单判定 segment
                        segment = "retail" if profile.get("name") else "corporate"
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError) as e:
            yield self._message(f"输入解析失败：{e}")
            yield self._done("终止")
            return

        if profile is None:
            presets_corp = _list_preset_profiles("corporate")
            presets_retail = _list_preset_profiles("retail")
            yield self._message(
                "未提供输入。请任选其一：\n"
                f"  1. 消息里写 `#preset:<名称> segment:corporate` —— 可选 {presets_corp}\n"
                f"  2. 消息里写 `#preset:<名称> segment:retail` —— 可选 {presets_retail}\n"
                "  3. 消息里写 `#report_json:<路径>`（Agent6 产出的 ReportJSON）\n"
                "  4. 或直接上传 ReportJSON / profile JSON 文件\n"
            )
            yield self._done("等待输入")
            return

        subject = profile.get("company_name") or profile.get("name") or "未命名主体"
        self.last_segment = segment
        self.last_report_json_path = report_json_path

        yield self._tool_result("load_profile",
                                f"{subject}（{'对公' if segment == 'corporate' else '对私'}）")

        # ---- 2. 跑 DecisionEngine.run_stream，翻译 stage → BaseAgent 事件 ----
        stage_labels = {
            "feature_extracting": ("特征抽取", "feature_extractor"),
            "feature_done":       None,
            "scoring":            ("评分测算", "scoring_model"),
            "scoring_done":       None,
            "rule_checking":      ("红线检查", "rule_engine"),
            "rule_done":          None,
            "case_retrieving":    ("案例检索", "case_retriever"),
            "case_done":          None,
            "advising":           ("决策整合", "advisor_formatter"),
            "advising_done":      None,
            "all_done":           None,
        }

        result: DecisionPipelineResult | None = None
        last_tool: str | None = None
        for stage, payload in self.engine.run_stream(profile, segment):
            label = stage_labels.get(stage)
            if label:
                desc, tool = label
                yield self._thinking(f"{desc}...")
                yield self._tool_call(tool)
                last_tool = tool
                continue
            # 完成事件
            if stage == "feature_done":
                yield self._tool_result(
                    "feature_extractor",
                    f"抽取 {len(payload)} 项特征"
                )
            elif stage == "scoring_done":
                if segment == "corporate":
                    yield self._tool_result(
                        "scoring_model",
                        f"综合 {payload.composite_score} 分 / 等级 {payload.risk_grade}"
                    )
                else:
                    yield self._tool_result(
                        "scoring_model",
                        f"FICO {payload.fico_score} / 档位 {payload.grade}"
                    )
            elif stage == "rule_done":
                yield self._tool_result(
                    "rule_engine",
                    f"触发 {len(payload)} 条红线"
                    + ("（含红灯）" if any(h.severity == "red" for h in payload) else "")
                )
            elif stage == "case_done":
                yield self._tool_result(
                    "case_retriever",
                    f"Top {len(payload)} 相似案例，最高相似度 "
                    f"{(payload[0].similarity if payload else 0):.0%}"
                )
            elif stage == "advising_done":
                advice: DecisionAdvice = payload
                yield self._tool_result(
                    "advisor_formatter",
                    f"决策：{advice.decision} / 额度 {advice.approved_amount} 万 / "
                    f"利率 {advice.interest_rate*100:.2f}%"
                )
            elif stage == "all_done":
                result = payload

        if result is None:
            yield self._message("流水线异常：未获得最终结果")
            yield self._done("失败")
            return

        self.last_result = result
        advice = result.advice

        # ---- 3. 汇总报告 ----
        report_md = self._build_report_md(advice, segment, result)
        yield self._message(report_md)

        # 若来自 ReportJSON，自动尝试回写
        if report_json_path and advice and advice.decision != "拒绝":
            try:
                out_path = self.writeback_to_agent6(advice, report_json_path)
                yield self._tool_result("writeback", f"已回写：{out_path}")
                yield self._file(out_path)
            except (OSError, RuntimeError, ValueError, TypeError, AttributeError, KeyError) as e:
                yield self._message(f"回写失败（不阻塞决策结果）：{e}")

        yield self._done(
            f"决策完成 — {advice.decision}" if advice else "完成"
        )

    # ------------------------------------------------------------------
    # 直接 API（给 Gradio app.py / 单测调用）
    # ------------------------------------------------------------------

    def load_preset_profile(self, preset_name: str, segment: Segment) -> dict:
        return _load_preset_profile(preset_name, segment)

    def load_profile_from_report_json(self, path: str) -> dict:
        rj = load_report_json(path)
        return _profile_from_report_json(rj)

    def list_presets(self, segment: Segment) -> list[str]:
        return _list_preset_profiles(segment)

    def run_decision(self, profile: dict, segment: Segment) -> DecisionPipelineResult:
        result = self.engine.run(profile, segment)
        self.last_result = result
        self.last_segment = segment
        return result

    def run_decision_stream(self, profile: dict, segment: Segment):
        """给 UI 直接拿 (stage, payload) 序列。"""
        for stage, payload in self.engine.run_stream(profile, segment):
            yield stage, payload
            if stage == "all_done":
                self.last_result = payload
                self.last_segment = segment

    def writeback_to_agent6(self, advice: DecisionAdvice,
                            report_json_path: str) -> str:
        """把 DecisionAdvice 回写成 `{client}_{ts}_decided.docx`。"""
        if not advice:
            raise ValueError("advice 为空，无法回写")
        meta = {
            "决策": advice.decision,
            "额度": f"{advice.approved_amount} 万元",
            "期限": f"{advice.approved_term_months} 个月",
            "利率": f"{advice.interest_rate*100:.2f}% ({advice.rate_benchmark})",
            "评分": f"{advice.composite_score} / {advice.risk_grade} 级",
            "红线": f"{len(advice.red_line_hits)} 条",
        }
        return apply_decision_writeback(
            report_json_path=report_json_path,
            decision_text=advice.approval_section_text or advice.decision_reason,
            decision_meta=meta,
        )

    def reload_rules(self, segment: Segment | None = None):
        self.engine.reload_rules(segment)

    def refresh_appetite(self, segment: Segment, appetite: RiskAppetiteConfig):
        self.engine.refresh_appetite(segment, appetite)

    # ------------------------------------------------------------------
    # Markdown 汇总（供 Chatbot / 调试）
    # ------------------------------------------------------------------

    def _build_report_md(self, advice: DecisionAdvice, segment: Segment,
                         result: DecisionPipelineResult) -> str:
        if advice is None:
            return "未生成决策意见"

        icon = {"批准": "✅", "有条件批准": "⚠️", "拒绝": "❌"}.get(advice.decision, "❓")
        lines = [
            f"# {icon} 授信决策 — {advice.subject_name}",
            "",
            f"**决策**：{advice.decision}　|　**额度**：{advice.approved_amount} 万元"
            f"　|　**期限**：{advice.approved_term_months} 个月",
            f"**利率**：{advice.interest_rate*100:.2f}%（{advice.rate_benchmark}）"
            f"　|　**评分**：{advice.composite_score}（{advice.risk_grade}）",
            "",
        ]

        # 评分明细
        scoring = result.scoring_result
        if segment == "corporate" and scoring is not None:
            lines += [
                "## 四维评分",
                "| 维度 | 评分 |",
                "|------|------|",
                f"| 财务 | {scoring.financial_score} |",
                f"| 行业 | {scoring.industry_score} |",
                f"| 经营 | {scoring.operational_score} |",
                f"| 担保 | {scoring.guarantee_score} |",
                "",
            ]
            if getattr(scoring, "amount_methods", None):
                lines.append("## 额度测算（四法）")
                for k, v in scoring.amount_methods.items():
                    lines.append(f"- {k}：{v} 万")
                lines.append("")
        elif segment == "retail" and scoring is not None:
            lines += [
                "## 评分卡大类",
                "| 大类 | 得分 |",
                "|------|------|",
            ]
            for k, v in (scoring.category_scores or {}).items():
                lines.append(f"| {k} | {v} |")
            lines.append("")

        # 红线
        if advice.red_line_hits:
            lines.append(f"## 触发红线（{len(advice.red_line_hits)} 条）")
            sev_mark = {"red": "🟥 红灯", "yellow": "🟧 黄灯", "green": "🟩 绿灯"}
            for h in advice.red_line_hits:
                mark = sev_mark.get(h.get("severity", "green"), "🟩 绿灯")
                lines.append(
                    f"- {mark} **{h.get('rule_name')}**"
                    f"（实际 {h.get('actual_value')}，阈值 {h.get('threshold')}）"
                )
            lines.append("")
            if advice.red_line_explanations:
                lines.append("### 红线解读")
                for e in advice.red_line_explanations:
                    lines.append(
                        f"- `{e.get('rule_id')}` [{e.get('severity')}]"
                        f" {e.get('explanation')}"
                    )
                    if e.get("waiver_advice"):
                        lines.append(f"  - 豁免建议：{e.get('waiver_advice')}")
                lines.append("")

        # 附加条件
        if advice.conditions:
            lines.append("## 附加条件")
            for c in advice.conditions:
                lines.append(f"- {c}")
            lines.append("")

        # 相似案例
        cases = result.case_matches or []
        if cases:
            lines.append("## 相似历史案例（Top 3）")
            lines.append("| 案例 | 相似度 | 决策 | 批复 | 利率 |")
            lines.append("|------|-------|------|------|------|")
            for c in cases[:3]:
                lines.append(
                    f"| {c.company_name} | {c.similarity*100:.0f}% | {c.decision} "
                    f"| {c.approved_amount} 万 | {c.interest_rate*100:.2f}% |"
                )
            lines.append("")

        # 决策说明
        lines.append("## 决策说明")
        lines.append(advice.decision_reason or "—")

        return "\n".join(lines)
