# -*- coding: utf-8 -*-
"""Agent1 全渠道流量匹配 — 独立启动入口（alias → app_demo）。

v2.0 取消了 v1.0 的"手填企业 → 渠道推荐"单查 UI，
改为"上传 3 类文件 → look-alike 扫描"。独立入口复用 app_demo.build_tab()。
"""
from __future__ import annotations

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agent_channel.app_demo import _standalone_main, build_tab  # noqa: F401


def create_app():
    """向后兼容入口：外部若曾经 from agent_channel.app import create_app 时仍可用。

    当前直接调用独立启动函数，内部会自行构建 Blocks。
    """
    import gradio as gr
    from shared.demo_ui import CUSTOM_CSS

    with gr.Blocks(title="全渠道流量匹配 — look-alike 获客", css=CUSTOM_CSS) as demo:
        api_key_state = gr.State("")
        provider_state = gr.State("deepseek")
        with gr.Accordion("⚙️  全局配置", open=True):
            with gr.Row():
                provider_input = gr.Dropdown(
                    choices=["deepseek", "kimi", "minimax", "openai", "anthropic"],
                    value="deepseek",
                    label="模型厂商",
                    scale=1,
                )
                api_key_input = gr.Textbox(
                    label="API Key",
                    type="password",
                    scale=3,
                )
                save_btn = gr.Button("保存", variant="primary", scale=1)
            status = gr.Markdown("")

            def _save(p, k):
                if not k or len(k) < 10:
                    return "", p, "❌ API Key 格式异常"
                return k, p, f"✅ 已保存：provider={p}"

            save_btn.click(_save, inputs=[provider_input, api_key_input],
                           outputs=[api_key_state, provider_state, status])

        build_tab(api_key_state, provider_state)

    return demo


if __name__ == "__main__":
    _standalone_main()
