# -*- coding: utf-8 -*-
"""Agent3 风控策略运营 — Portal Demo Tab

轻量级 UI：场景卡 + 自然语言策略描述 + 可选 CSV 上传 + 结果流式输出。
"""
from __future__ import annotations

import os
import sys

import gradio as gr

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.demo_ui import (
    load_scenarios,
    stream_agent,
    render_header_html,
    ZHONGAN_BLUE,
    ZHONGAN_TEXT_LIGHT,
)
from agent_riskctrl.agent import RiskControlAgent


def build_tab(api_key_state, provider_state):
    """Portal 调用此函数构建 Tab 内容。"""

    gr.HTML(render_header_html(
        "风控策略运营",
        "自然语言配策略 · 历史数据回测 · 差错案件分析 —— 三合一",
    ))

    scenarios = load_scenarios("agent_riskctrl")

    gr.Markdown("#### 📋 预置场景（点击自动填充指令）")

    msg_input = gr.Textbox(
        label="策略描述 / 回测指令 / 差错案件",
        placeholder="例：年营收 <500 万拒绝，征信逾期拒绝，经营年限 <2 年进人工审查。上传 CSV 后可直接做回测。",
        lines=5,
    )

    if scenarios:
        with gr.Row():
            for sc in scenarios[:3]:
                title = sc.get("title", "场景")
                desc = sc.get("description", "")
                desc_short = desc[:70] + ("…" if len(desc) > 70 else "")
                with gr.Column(scale=1, min_width=180):
                    card_btn = gr.Button(
                        f"📍 {title}\n{desc_short}",
                        variant="secondary",
                        size="sm",
                    )
                    card_btn.click(
                        lambda s=sc: s.get("input_message", ""),
                        inputs=None,
                        outputs=msg_input,
                    )
    else:
        gr.Markdown(
            f"<span style='color:{ZHONGAN_TEXT_LIGHT}'>*未发现预置场景。*</span>"
        )

    with gr.Row():
        with gr.Column(scale=2):
            file_input = gr.File(
                label="上传历史数据（CSV/Excel，可选 — 上传后触发回测）",
                file_count="multiple",
            )
            run_btn = gr.Button(
                "🚀 执行",
                variant="primary",
                elem_classes=["zhongan-btn-primary"],
            )
            gr.Markdown(
                f"<div class='muted-note'>"
                f"• 纯文字 → 自然语言配策略<br/>"
                f"• 文字 + CSV → 策略生成 + 回测<br/>"
                f"• 含「差错/误杀/漏杀」关键词 → 差错分析<br/>"
                f"首次使用请先在顶部「⚙️ 全局配置」中填写 API Key。"
                f"</div>"
            )

        with gr.Column(scale=3):
            with gr.Accordion("🔍 执行过程（实时日志）", open=False):
                process_log = gr.Markdown("*尚未开始运行*")
            gr.Markdown("### 📊 策略 / 回测 / 分析结果")
            final_output = gr.Markdown(
                "*点击场景卡或输入策略描述后点「执行」*",
            )

    def _run(api_key, provider, message, files):
        if not message or not message.strip():
            yield "⚠️ 请先输入策略描述或点击场景卡", ""
            return
        file_paths = [f.name for f in files] if files else []
        for proc, final in stream_agent(
            RiskControlAgent, api_key, provider, message, file_paths,
        ):
            yield proc or "*正在执行…*", final or "*结果生成中…*"

    run_btn.click(
        _run,
        inputs=[api_key_state, provider_state, msg_input, file_input],
        outputs=[process_log, final_output],
    )
