# -*- coding: utf-8 -*-
"""Agent3 v2.0 — 授信决策辅助 Gradio 界面

双 Tab 结构：
  🏢 对公授信决策
  👤 对私授信决策

每个 Tab 的布局：
  - 左栏（scale=1）：模型配置 + 预设场景选择 + 流水线状态灯 + Dashboard 摘要
  - 右栏（scale=2）：决策卡片（决策/额度/期限/利率/红线/附加条件/相似案例/决策说明）
  - 底部操作：[重新计算] [导出 JSON] [回写 Agent6（对公）] [⚙风险偏好]

UI 原则（遵循 CLAUDE.md 交互设计）：
  - 不让用户思考：预设场景一键载入，所有字段自动展开
  - 证据支撑：每条红线显示实际值 vs 阈值；额度四法并列显示
  - 渐进式展示：先看决策卡，细节按需展开到下方
  - 反馈引导：状态灯实时流转，不卡顿
"""

from __future__ import annotations

import os
import sys
import json
import time
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import gradio as gr

from shared.base_app import build_config_sidebar
from shared.report_handoff import list_available_reports
from .agent import CreditDecisionAgent, _list_preset_profiles
from .advisor_formatter import DecisionAdvice
from .risk_appetite_config import RiskAppetiteConfig

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

_STAGE_LABELS_CORP = [
    ("feature_extracting", "① 特征抽取"),
    ("scoring",            "② 四维评分"),
    ("rule_checking",      "③ 红线检查"),
    ("case_retrieving",    "④ 案例检索"),
    ("advising",           "⑤ 决策整合"),
]

_STAGE_LABELS_RETAIL = [
    ("feature_extracting", "① 变量抽取"),
    ("scoring",            "② 评分卡计算"),
    ("rule_checking",      "③ 红线检查"),
    ("case_retrieving",    "④ 案例检索"),
    ("advising",           "⑤ 决策整合"),
]

_LIGHT_PENDING = "⚪"
_LIGHT_RUNNING = "🔵"
_LIGHT_DONE = "🟢"
_LIGHT_WARN = "🟡"


# ---------------------------------------------------------------------------
# 渲染辅助
# ---------------------------------------------------------------------------

def _format_status_lights(stage_map: list[tuple[str, str]],
                          current_stage: str,
                          done_stages: set[str]) -> str:
    rows = []
    for s_key, s_label in stage_map:
        if s_key in done_stages:
            dot = _LIGHT_DONE
        elif current_stage == s_key:
            dot = _LIGHT_RUNNING
        else:
            dot = _LIGHT_PENDING
        rows.append(f"- {dot} {s_label}")
    return "\n".join(rows)


def _render_decision_card(advice: DecisionAdvice | None) -> str:
    if advice is None:
        return "> 尚未运行决策流水线。请选择场景后点击「🚀 运行决策」。"

    icon = {"批准": "✅", "有条件批准": "⚠️", "拒绝": "❌"}.get(advice.decision, "❓")
    lines = [
        f"## {icon} 决策：{advice.decision}",
        "",
        f"| 项目 | 数值 |",
        f"|------|------|",
        f"| 主体 | **{advice.subject_name}** |",
        f"| 批复额度 | **{advice.approved_amount} 万元** |",
        f"| 期限 | {advice.approved_term_months} 个月 |",
        f"| 利率 | {advice.interest_rate*100:.2f}% ({advice.rate_benchmark}) |",
        f"| 评分 | {advice.composite_score} / {advice.risk_grade} 级 |",
        f"| 红线 | {len(advice.red_line_hits)} 条"
        + ("（含硬红线）" if any(h.get("is_hard") for h in advice.red_line_hits) else "")
        + " |",
        "",
    ]

    if advice.conditions:
        lines.append("### 附加条件")
        for c in advice.conditions:
            lines.append(f"- {c}")
        lines.append("")

    if advice.red_line_hits:
        lines.append("### 触发红线")
        for h in advice.red_line_hits:
            mark = "🟥" if h.get("is_hard") else "🟧"
            lines.append(
                f"- {mark} **{h.get('rule_name')}**"
                f"（实际 {h.get('actual_value')}，阈值 {h.get('threshold')}，"
                f"{h.get('severity')}）"
            )
        lines.append("")

    lines.append("### 决策说明")
    lines.append(advice.decision_reason or "—")
    return "\n".join(lines)


def _render_corp_scoring(scoring) -> str:
    if scoring is None:
        return ""
    lines = [
        "### 四维评分",
        f"| 维度 | 评分 |",
        f"|------|------|",
        f"| 财务 | {scoring.financial_score} |",
        f"| 行业 | {scoring.industry_score} |",
        f"| 经营 | {scoring.operational_score} |",
        f"| 担保 | {scoring.guarantee_score} |",
        f"| **综合** | **{scoring.composite_score}（{scoring.risk_grade} 级）** |",
        "",
    ]
    if getattr(scoring, "amount_methods", None):
        lines.append("### 额度测算（四法）")
        lines.append("| 方法 | 金额(万) |")
        lines.append("|------|---------|")
        label_map = {
            "revenue_method": "营收法",
            "netasset_method": "净资产法",
            "cashflow_method": "现金流法",
            "collateral_method": "担保法",
        }
        for k, v in scoring.amount_methods.items():
            lines.append(f"| {label_map.get(k, k)} | {v} |")
        lines.append("")
    return "\n".join(lines)


def _render_retail_scoring(scoring) -> str:
    if scoring is None:
        return ""
    lines = [
        f"### 评分卡结果",
        f"- **FICO 得分**：{scoring.fico_score}（档位 {scoring.grade}）",
        f"- **预授信上限**：{scoring.approved_limit_cap} 万元",
        f"- **利率定价**：{scoring.rate_tier}",
        "",
        "### 大类得分",
        "| 大类 | 得分 |",
        "|------|------|",
    ]
    label = {
        "repayment_capacity": "偿债能力",
        "repayment_willingness": "还款意愿",
        "stability": "稳定性",
        "collateral": "抵押估值",
    }
    for k, v in (scoring.category_scores or {}).items():
        lines.append(f"| {label.get(k, k)} | {v} |")
    lines.append("")
    return "\n".join(lines)


def _render_cases(cases) -> str:
    if not cases:
        return "_无相似历史案例_"
    lines = ["| 案例 | 相似度 | 决策 | 批复额度 | 利率 |",
             "|------|--------|------|---------|------|"]
    for c in cases[:5]:
        lines.append(
            f"| {c.company_name} | {c.similarity*100:.0f}% | {c.decision} "
            f"| {c.approved_amount} 万 | {c.interest_rate*100:.2f}% |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 业务逻辑：运行决策
# ---------------------------------------------------------------------------

def _build_agent(provider, api_key) -> CreditDecisionAgent:
    return CreditDecisionAgent(
        api_key=api_key or "dummy",
        model_provider=provider or "deepseek",
    )


def _run_pipeline(segment: str, preset_name: str,
                  report_json_path: str,
                  provider: str, api_key: str,
                  stage_map: list[tuple[str, str]]):
    """generator：产出 (status_lights_md, decision_card_md, scoring_md, cases_md,
                    writeback_file_update, status_text, advice_state)"""
    agent = _build_agent(provider, api_key)

    # 载入 profile
    try:
        if report_json_path and os.path.exists(report_json_path):
            profile = agent.load_profile_from_report_json(report_json_path)
        elif preset_name:
            profile = agent.load_preset_profile(preset_name, segment)  # type: ignore
        else:
            yield (
                "> 请先选择预设场景或上传 ReportJSON",
                "> 未启动",
                "", "", gr.update(), "等待输入", None, None, None
            )
            return
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError) as e:
        yield (
            f"❌ 载入失败：{e}", "", "", "", gr.update(),
            "载入失败", None, None, None,
        )
        return

    done_stages: set[str] = set()
    current = ""
    lights = _format_status_lights(stage_map, "", done_stages)
    yield (lights, "> 流水线启动中...", "", "", gr.update(),
           "启动", None, None, None)

    scoring = None
    cases = None
    advice = None
    result = None

    for stage, payload in agent.run_decision_stream(profile, segment):  # type: ignore
        if stage.endswith("_done") or stage == "all_done":
            # 完成事件
            base_stage = stage.rsplit("_done", 1)[0]
            if base_stage == "feature":
                done_stages.add("feature_extracting")
            elif base_stage == "scoring":
                done_stages.add("scoring")
                scoring = payload
            elif base_stage == "rule":
                done_stages.add("rule_checking")
            elif base_stage == "case":
                done_stages.add("case_retrieving")
                cases = payload
            elif base_stage == "advising":
                done_stages.add("advising")
                advice = payload
            elif stage == "all_done":
                result = payload
                if result is not None:
                    advice = result.advice
                    scoring = result.scoring_result
                    cases = result.case_matches
            current = ""
        else:
            current = stage

        lights = _format_status_lights(stage_map, current, done_stages)
        card = _render_decision_card(advice) if advice else "> 流水线进行中..."
        scoring_md = (_render_corp_scoring(scoring)
                      if segment == "corporate"
                      else _render_retail_scoring(scoring))
        cases_md = _render_cases(cases) if cases is not None else ""
        status = f"执行 {current}" if current else ("完成" if advice else "运行中")
        yield (lights, card, scoring_md, cases_md, gr.update(),
               status, advice, result, profile)

    # 完成
    lights = _format_status_lights(stage_map, "", done_stages)
    status = f"✅ 决策完成：{advice.decision}" if advice else "完成"
    yield (lights, _render_decision_card(advice),
           _render_corp_scoring(scoring) if segment == "corporate" else _render_retail_scoring(scoring),
           _render_cases(cases), gr.update(),
           status, advice, result, profile)


def _export_json(advice: DecisionAdvice | None):
    if advice is None:
        return gr.update(value=None), "尚无结果可导出"
    Path("outputs").mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    subject = (advice.subject_name or "decision").replace("/", "_")
    path = Path("outputs") / f"{subject}_{ts}_advice.json"
    path.write_text(advice.to_json(), encoding="utf-8")
    return gr.update(value=str(path), visible=True), f"已导出 {path}"


def _writeback_agent6(advice: DecisionAdvice | None, report_json_path: str,
                      provider: str, api_key: str):
    if advice is None:
        return gr.update(value=None), "尚无决策结果可回写"
    if not report_json_path or not os.path.exists(report_json_path):
        return gr.update(value=None), "无 ReportJSON，无法回写"
    if advice.decision == "拒绝":
        return gr.update(value=None), "拒绝决策不回写报告"
    agent = _build_agent(provider, api_key)
    try:
        out = agent.writeback_to_agent6(advice, report_json_path)
        return gr.update(value=out, visible=True), f"已回写：{out}"
    except (OSError, RuntimeError, ValueError, TypeError, AttributeError, KeyError) as e:
        return gr.update(value=None), f"回写失败：{e}"


# ---------------------------------------------------------------------------
# Tab 构建
# ---------------------------------------------------------------------------

def _build_corp_tab(provider, api_key):
    with gr.Column():
        with gr.Row():
            # 左栏
            with gr.Column(scale=1):
                gr.Markdown("### 场景选择")
                presets = _list_preset_profiles("corporate")
                preset = gr.Dropdown(
                    choices=presets,
                    value=(presets[0] if presets else None),
                    label="预设场景（Mock 企业）",
                )
                reports = list_available_reports()
                rjson = gr.Dropdown(
                    choices=[r["path"] for r in reports],
                    label="或选择 Agent6 ReportJSON（优先）",
                    value=None,
                    allow_custom_value=True,
                )
                run_btn = gr.Button("🚀 运行决策", variant="primary")

                gr.Markdown("### 流水线状态")
                lights = gr.Markdown(
                    _format_status_lights(_STAGE_LABELS_CORP, "", set())
                )

                gr.Markdown("### 评分 & 额度")
                scoring_md = gr.Markdown("_待运行_")

            # 右栏
            with gr.Column(scale=2):
                decision_card = gr.Markdown(
                    "> 选择场景后点击「🚀 运行决策」启动流水线"
                )

                with gr.Accordion("相似历史案例", open=False):
                    cases_md = gr.Markdown("_待运行_")

                with gr.Row():
                    export_btn = gr.Button("📤 导出 JSON")
                    writeback_btn = gr.Button("📝 回写 Agent6 报告", variant="secondary")
                    refresh_rj_btn = gr.Button("🔄 刷新 ReportJSON 列表")
                file_out = gr.File(label="产出文件", visible=False)
                status_text = gr.Textbox(label="状态", interactive=False, lines=1)

        # State
        advice_state = gr.State(None)
        result_state = gr.State(None)
        profile_state = gr.State(None)

        # 事件
        run_btn.click(
            fn=lambda preset_v, rj_v, prov, key: _run_pipeline(
                "corporate", preset_v, rj_v, prov, key, _STAGE_LABELS_CORP),
            inputs=[preset, rjson, provider, api_key],
            outputs=[lights, decision_card, scoring_md, cases_md,
                     file_out, status_text,
                     advice_state, result_state, profile_state],
        )

        export_btn.click(
            fn=_export_json,
            inputs=[advice_state],
            outputs=[file_out, status_text],
        )

        writeback_btn.click(
            fn=_writeback_agent6,
            inputs=[advice_state, rjson, provider, api_key],
            outputs=[file_out, status_text],
        )

        def _refresh():
            rs = list_available_reports()
            return gr.update(choices=[r["path"] for r in rs])
        refresh_rj_btn.click(fn=_refresh, inputs=[], outputs=[rjson])


def _build_retail_tab(provider, api_key):
    with gr.Column():
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 场景选择")
                presets = _list_preset_profiles("retail")
                preset = gr.Dropdown(
                    choices=presets,
                    value=(presets[0] if presets else None),
                    label="预设客户（Mock）",
                )
                run_btn = gr.Button("🚀 运行决策", variant="primary")

                gr.Markdown("### 流水线状态")
                lights = gr.Markdown(
                    _format_status_lights(_STAGE_LABELS_RETAIL, "", set())
                )

                gr.Markdown("### 评分卡")
                scoring_md = gr.Markdown("_待运行_")

            with gr.Column(scale=2):
                decision_card = gr.Markdown(
                    "> 选择客户后点击「🚀 运行决策」"
                )

                with gr.Accordion("相似历史案例", open=False):
                    cases_md = gr.Markdown("_待运行_")

                with gr.Row():
                    export_btn = gr.Button("📤 导出 JSON")
                file_out = gr.File(label="产出文件", visible=False)
                status_text = gr.Textbox(label="状态", interactive=False, lines=1)

        advice_state = gr.State(None)
        result_state = gr.State(None)
        profile_state = gr.State(None)

        run_btn.click(
            fn=lambda preset_v, prov, key: _run_pipeline(
                "retail", preset_v, "", prov, key, _STAGE_LABELS_RETAIL),
            inputs=[preset, provider, api_key],
            outputs=[lights, decision_card, scoring_md, cases_md,
                     file_out, status_text,
                     advice_state, result_state, profile_state],
        )

        export_btn.click(
            fn=_export_json,
            inputs=[advice_state],
            outputs=[file_out, status_text],
        )


def _build_appetite_tab():
    """风险偏好编辑（对公/对私双页签）。"""
    def _load_preview(segment):
        ap = RiskAppetiteConfig.default(segment)  # type: ignore
        return json.dumps({
            "segment": ap.segment,
            "grade_thresholds": ap.grade_thresholds,
            "dimension_weights": ap.dimension_weights,
            "rule_threshold_overrides": ap.rule_threshold_overrides,
            "rate_tier_map": ap.rate_tier_map,
            "lpr_base": ap.lpr_base,
        }, ensure_ascii=False, indent=2)

    with gr.Column():
        gr.Markdown("### ⚙️ 风险偏好（只读查看）")
        with gr.Row():
            with gr.Column():
                gr.Markdown("#### 对公默认")
                gr.Code(_load_preview("corporate"), language="json")
            with gr.Column():
                gr.Markdown("#### 对私默认")
                gr.Code(_load_preview("retail"), language="json")
        gr.Markdown(
            "_当前版本仅展示默认偏好。阈值调整请编辑 "
            "`agent_credit/mock_data/risk_appetite_default.json` "
            "或在代码中调用 `agent.refresh_appetite(segment, RiskAppetiteConfig(...))`。_"
        )


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def create_credit_app():
    with gr.Blocks(
        title="授信决策辅助 v2.0",
        css="""
        .gradio-container { max-width: 1600px !important; }
        .decision-card { font-size: 15px; }
        """,
    ) as app:
        gr.Markdown("# 📊 授信决策辅助 Agent3 v2.0")
        gr.Markdown(
            "**定位**：消费 Agent6 报告 → 五段流水线 → 输出决策看板 → 回写 Word 报告。"
            "**对公**：福建中锐网络等 3 家示例，<2min 出 Dashboard。 "
            "**对私**：张三餐饮等 3 户示例，<10s 出评分卡。"
        )

        # 全局配置
        with gr.Accordion("模型配置（共享）", open=False):
            provider, api_key, base_url, model_name, _status = build_config_sidebar()

        with gr.Tabs():
            with gr.Tab("🏢 对公授信决策"):
                _build_corp_tab(provider, api_key)
            with gr.Tab("👤 对私授信决策"):
                _build_retail_tab(provider, api_key)
            with gr.Tab("⚙️ 风险偏好"):
                _build_appetite_tab()

    return app


if __name__ == "__main__":
    app = create_credit_app()
    app.launch(server_name="0.0.0.0", server_port=7862, share=False)
