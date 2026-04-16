# -*- coding: utf-8 -*-
"""Gradio 界面工厂 — 提供通用组件构建函数"""

from __future__ import annotations
import sys
import os
import gradio as gr

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import MODEL_CONFIG


def build_config_sidebar():
    """通用配置侧栏：API密钥 + 模型选择"""
    providers = list(MODEL_CONFIG.keys())
    provider = gr.Dropdown(
        choices=providers,
        value=providers[0] if providers else "deepseek",
        label="模型厂商",
    )
    api_key = gr.Textbox(label="API Key", type="password", lines=1)
    base_url = gr.Textbox(label="Base URL (可选)", lines=1)
    model_name = gr.Textbox(label="模型名 (可选)", lines=1)
    status = gr.Textbox(label="状态", interactive=False, lines=2)
    return provider, api_key, base_url, model_name, status


def build_file_upload(file_types: list[str] | None = None,
                      label: str = "上传文件",
                      file_count: str = "multiple"):
    """通用文件上传组件"""
    return gr.File(
        label=label,
        file_types=file_types,
        file_count=file_count,
    )


def build_chatbot():
    """通用聊天区域"""
    return gr.Chatbot(label="处理过程", height=500)


def create_stream_handler(agent_class):
    """通用的 stream_chat 处理函数工厂

    返回一个函数，消费 agent.process_message() 的 Generator 事件，
    实时更新 chatbot 和 status 控件。
    """

    def stream_chat(message, files, provider, api_key, base_url, model_name,
                    chatbot_history):
        if not api_key:
            yield chatbot_history + [{"role": "assistant",
                                      "content": "请先填写 API Key"}], "未配置"
            return

        agent = agent_class(
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
                history_out = history + [
                    {"role": "assistant", "content": current_response}
                ]
                yield history_out, event["content"]

            elif etype == "message":
                current_response += f"\n{event['content']}\n"
                history_out = history + [
                    {"role": "assistant", "content": current_response}
                ]
                yield history_out, "完成"

            elif etype == "tool_call":
                current_response += f"\n🔧 调用 {event['name']}...\n"
                history_out = history + [
                    {"role": "assistant", "content": current_response}
                ]
                yield history_out, f"执行 {event['name']}"

            elif etype == "tool_result":
                result_preview = str(event.get("result", ""))[:200]
                current_response += f"\n📋 {event['name']}: {result_preview}\n"
                history_out = history + [
                    {"role": "assistant", "content": current_response}
                ]
                yield history_out, f"{event['name']} 完成"

            elif etype == "done":
                history_out = history + [
                    {"role": "assistant", "content": current_response}
                ]
                yield history_out, event.get("content", "完成")

    return stream_chat
