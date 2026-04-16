# -*- coding: utf-8 -*-
"""风控策略运营 Agent — Gradio 界面

左侧(scale=1)：配置栏 + 文件上传（CSV）
右侧(scale=3)：chatbot 对话区
"""

from __future__ import annotations

import sys
import os

# 将项目根目录加入路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import gradio as gr

from .agent import RiskControlAgent


# ---------------------------------------------------------------------------
# 核心交互
# ---------------------------------------------------------------------------

def _stream_chat(
    message: str,
    files,
    provider: str,
    api_key: str,
    base_url: str,
    model_name: str,
    chatbot_history: list,
):
    """消费 agent.process_message() 的 Generator 事件，实时更新 chatbot。"""

    if not api_key:
        history = (chatbot_history or []) + [
            {"role": "assistant", "content": "请先填写 API Key。"}
        ]
        yield history, "未配置"
        return

    agent = RiskControlAgent(
        api_key=api_key,
        model_provider=provider,
        base_url=base_url,
        model_name=model_name,
    )

    file_paths = [f.name for f in files] if files else []
    history = list(chatbot_history) if chatbot_history else []

    if message:
        history.append({"role": "user", "content": message})

    current_response = ""

    for event in agent.process_message(message, file_paths):
        etype = event.get("type", "")

        if etype == "thinking":
            current_response += f"\n> {event['content']}\n"
            yield history + [
                {"role": "assistant", "content": current_response}
            ], event["content"]

        elif etype == "message":
            current_response += f"\n{event['content']}\n"
            yield history + [
                {"role": "assistant", "content": current_response}
            ], "完成"

        elif etype == "tool_call":
            current_response += f"\n🔧 调用 {event['name']}...\n"
            yield history + [
                {"role": "assistant", "content": current_response}
            ], f"执行 {event['name']}"

        elif etype == "tool_result":
            result_preview = str(event.get("result", ""))[:200]
            current_response += f"\n📋 {event['name']}: {result_preview}\n"
            yield history + [
                {"role": "assistant", "content": current_response}
            ], f"{event['name']} 完成"

        elif etype == "done":
            yield history + [
                {"role": "assistant", "content": current_response}
            ], event.get("content", "完成")


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

def create_app() -> gr.Blocks:
    """创建 Gradio 界面"""

    with gr.Blocks(
        title="风控策略运营Agent",
    ) as app:
        gr.Markdown("# 风控策略运营 Agent")
        gr.Markdown(
            "AI辅助风控策略配置、策略效果回溯分析、差错案件智能分析优化"
        )

        with gr.Row():
            # ---- 左侧：配置栏 ----
            with gr.Column(scale=1):
                gr.Markdown("### 配置")
                api_key_input = gr.Textbox(
                    label="API Key",
                    type="password",
                    placeholder="输入 LLM API Key",
                )
                model_provider = gr.Dropdown(
                    label="模型厂商",
                    choices=["deepseek", "openai", "anthropic", "kimi-k2.5", "minimax"],
                    value="deepseek",
                )
                base_url_input = gr.Textbox(
                    label="Base URL（可选）",
                    placeholder="自定义API地址",
                )
                model_name_input = gr.Textbox(
                    label="模型名称（可选）",
                    placeholder="留空使用默认模型",
                )

                gr.Markdown("---")
                gr.Markdown("### 数据上传")
                file_upload = gr.File(
                    label="上传数据文件（CSV / Excel）",
                    file_types=[".csv", ".xlsx", ".xls"],
                    file_count="multiple",
                )

                status_text = gr.Textbox(
                    label="状态", interactive=False, lines=1
                )

            # ---- 右侧：对话区 ----
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="Agent 对话",
                    height=500,
                )
                user_input = gr.Textbox(
                    label="策略指令",
                    placeholder=(
                        "描述您的风控策略，例：拒绝注册资本低于100万且成立不满2年的企业"
                    ),
                    lines=2,
                )
                send_btn = gr.Button("发送", variant="primary")

        # ---- 事件绑定 ----
        send_btn.click(
            fn=_stream_chat,
            inputs=[
                user_input,
                file_upload,
                model_provider,
                api_key_input,
                base_url_input,
                model_name_input,
                chatbot,
            ],
            outputs=[chatbot, status_text],
        )

        # 支持回车发送
        user_input.submit(
            fn=_stream_chat,
            inputs=[
                user_input,
                file_upload,
                model_provider,
                api_key_input,
                base_url_input,
                model_name_input,
                chatbot,
            ],
            outputs=[chatbot, status_text],
        )

    return app


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = create_app()
    app.launch(server_name="0.0.0.0", server_port=7862, share=False)
