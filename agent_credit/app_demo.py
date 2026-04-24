# -*- coding: utf-8 -*-
"""Agent3 v2.0 授信决策辅助 — Portal Demo Tab

v2.0 变更：
  - 不再"上传材料 → 构画像"，改为"选场景 → 跑流水线 → 出 Dashboard"
  - 与 `app.py` 共用业务逻辑，此处仅做 Portal 集成需要的轻量包装
  - 支持对公/对私 Tab 切换
"""
from __future__ import annotations

import os
import sys

import gradio as gr

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.demo_ui import render_header_html, ZHONGAN_TEXT_LIGHT
from agent_credit.agent import CreditDecisionAgent, _list_preset_profiles
from agent_credit.app import (
    _render_decision_card, _render_corp_scoring, _render_retail_scoring,
    _render_cases, _format_status_lights, _run_pipeline,
    _STAGE_LABELS_CORP, _STAGE_LABELS_RETAIL,
)


def _safe_run(segment: str, stage_map, preset_v, api_key, provider):
    """把 _run_pipeline 包一层，让 UI 层看到真实异常而不是 Gradio 默认吞掉。"""
    import traceback
    try:
        yield from _run_pipeline(segment, preset_v, "", provider, api_key, stage_map)
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError) as e:
        err = f"❌ **运行时异常**：`{type(e).__name__}: {e}`\n\n```\n{traceback.format_exc()[-1200:]}\n```"
        print("[agent_credit UI ERROR]", traceback.format_exc(), flush=True)
        # 9 个输出：lights, card, scoring_md, cases_md, file, status, advice, result, profile
        yield ("❌ 异常中断", err, "", "", gr.update(), f"异常：{e}", None, None, None)


def build_tab(api_key_state, provider_state):
    """Portal 调用：构建授信决策辅助 Tab。"""

    gr.HTML(render_header_html(
        "授信决策辅助 v2.0",
        "消费 Agent6 报告 / 预设场景 → 五段流水线 → 决策 Dashboard → 回写 Word",
    ))

    with gr.Tabs():
        # ========== 对公 ==========
        with gr.Tab("🏢 对公授信"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 选择场景")
                    corp_presets = _list_preset_profiles("corporate")
                    corp_preset = gr.Dropdown(
                        choices=corp_presets,
                        value=(corp_presets[0] if corp_presets else None),
                        label="预设企业",
                    )
                    corp_run_btn = gr.Button("🚀 运行决策", variant="primary")

                    gr.Markdown("### 流水线状态")
                    corp_lights = gr.Markdown(
                        _format_status_lights(_STAGE_LABELS_CORP, "", set())
                    )

                    gr.Markdown("### 四维评分 & 额度")
                    corp_scoring_md = gr.Markdown("_待运行_")

                with gr.Column(scale=2):
                    corp_card = gr.Markdown(
                        "> 选择预设企业后点击「🚀 运行决策」"
                    )
                    with gr.Accordion("相似历史案例", open=False):
                        corp_cases_md = gr.Markdown("_待运行_")
                    corp_file_out = gr.File(label="产出文件", visible=False)
                    corp_status = gr.Textbox(
                        label="状态", interactive=False, lines=1
                    )

            corp_advice_state = gr.State(None)
            corp_result_state = gr.State(None)
            corp_profile_state = gr.State(None)

            def _corp_click(preset_v, api_key, provider):
                yield from _safe_run(
                    "corporate", _STAGE_LABELS_CORP, preset_v, api_key, provider)

            corp_run_btn.click(
                fn=_corp_click,
                inputs=[corp_preset, api_key_state, provider_state],
                outputs=[corp_lights, corp_card, corp_scoring_md,
                         corp_cases_md, corp_file_out, corp_status,
                         corp_advice_state, corp_result_state, corp_profile_state],
            )

        # ========== 对私 ==========
        with gr.Tab("👤 对私授信"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 选择客户")
                    retail_presets = _list_preset_profiles("retail")
                    retail_preset = gr.Dropdown(
                        choices=retail_presets,
                        value=(retail_presets[0] if retail_presets else None),
                        label="预设客户",
                    )
                    retail_run_btn = gr.Button("🚀 运行决策", variant="primary")

                    gr.Markdown("### 流水线状态")
                    retail_lights = gr.Markdown(
                        _format_status_lights(_STAGE_LABELS_RETAIL, "", set())
                    )

                    gr.Markdown("### 评分卡")
                    retail_scoring_md = gr.Markdown("_待运行_")

                with gr.Column(scale=2):
                    retail_card = gr.Markdown(
                        "> 选择预设客户后点击「🚀 运行决策」"
                    )
                    with gr.Accordion("相似历史案例", open=False):
                        retail_cases_md = gr.Markdown("_待运行_")
                    retail_file_out = gr.File(label="产出文件", visible=False)
                    retail_status = gr.Textbox(
                        label="状态", interactive=False, lines=1
                    )

            retail_advice_state = gr.State(None)
            retail_result_state = gr.State(None)
            retail_profile_state = gr.State(None)

            def _retail_click(preset_v, api_key, provider):
                yield from _safe_run(
                    "retail", _STAGE_LABELS_RETAIL, preset_v, api_key, provider)

            retail_run_btn.click(
                fn=_retail_click,
                inputs=[retail_preset, api_key_state, provider_state],
                outputs=[retail_lights, retail_card, retail_scoring_md,
                         retail_cases_md, retail_file_out, retail_status,
                         retail_advice_state, retail_result_state, retail_profile_state],
            )

    gr.Markdown(
        f"<div style='color:{ZHONGAN_TEXT_LIGHT};font-size:12px;margin-top:8px'>"
        f"v2.0：流水线前 4 段无 LLM 调用；第 5 段若配置了 API Key 则调 1-2 次。"
        f"无 API Key 也可跑完整流程（走模板兜底）。</div>"
    )
