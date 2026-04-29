# -*- coding: utf-8 -*-
"""Agent5 合规巡检雷达 v2.0 - 独立启动入口

复用 agent_compliance/app_demo.py 的 build_tab，但包装为独立 Blocks。
"""

from __future__ import annotations

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import gradio as gr
from shared.demo_ui import CUSTOM_CSS, ZHONGAN_BLUE
from agent_compliance.app_demo import build_tab


def create_ui():
    """构建合规巡检雷达单独 UI（独立启动时使用）"""
    with gr.Blocks(title="合规巡检雷达 v2.0") as demo:
        gr.HTML(f"""
<div class="portal-header">
    <h1>合规巡检雷达 v2.0</h1>
    <div class="subtitle">矩阵扫描 · 分级榜单 · 证据链到单号</div>
</div>
""")

        # 独立模式下，API Key / Provider 仅作为占位（当前 Demo 场景无需 LLM）
        api_key_state = gr.State("")
        provider_state = gr.State("deepseek")

        build_tab(api_key_state, provider_state)

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7864,
        share=False,
        show_error=True,
        css=CUSTOM_CSS,
        theme=gr.themes.Soft(primary_hue="blue"),
    )
