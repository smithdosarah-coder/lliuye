# -*- coding: utf-8 -*-
"""
LLM 抽象层 — 统一接口，一行切换模型
所有对模型的调用都通过这里，方便替换和监控
"""

import json
import time
from openai import OpenAI
from config import MODEL_CONFIG


class LLMClient:
    """统一的 LLM 客户端，支持普通对话和 Function Calling"""

    def __init__(self, provider: str = "deepseek", api_key: str = ""):
        self.provider = provider
        conf = MODEL_CONFIG.get(provider, MODEL_CONFIG["deepseek"])
        self.model = conf["model"]
        self.max_tokens = conf["max_tokens"]
        self.temperature = conf["temperature"]

        # 统一用 OpenAI SDK（DeepSeek/OpenAI 兼容，Anthropic 可通过兼容层）
        self.client = OpenAI(
            api_key=api_key,
            base_url=conf["base_url"],
        )
        # 调用统计
        self.call_count = 0
        self.total_tokens = 0

    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             tool_choice: str = "auto", temperature: float | None = None) -> dict:
        """
        统一聊天接口
        返回: {
            "content": str | None,          # 文本回复
            "tool_calls": [                  # 工具调用（可能多个）
                {"id": str, "name": str, "arguments": dict}
            ] | None,
            "usage": {"prompt": int, "completion": int, "total": int}
        }
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": temperature if temperature is not None else self.temperature,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        resp = self.client.chat.completions.create(**kwargs)
        choice = resp.choices[0]

        # 解析结果
        result = {
            "content": choice.message.content,
            "tool_calls": None,
            "usage": {
                "prompt": resp.usage.prompt_tokens if resp.usage else 0,
                "completion": resp.usage.completion_tokens if resp.usage else 0,
                "total": resp.usage.total_tokens if resp.usage else 0,
            },
        }

        if choice.message.tool_calls:
            result["tool_calls"] = []
            for tc in choice.message.tool_calls:
                args = tc.function.arguments
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"raw": args}
                result["tool_calls"].append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": args,
                })

        self.call_count += 1
        self.total_tokens += result["usage"]["total"]
        return result

    def simple_chat(self, system_prompt: str, user_content: str,
                    temperature: float | None = None) -> str:
        """简单对话，不带工具，直接返回文本"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        result = self.chat(messages, temperature=temperature)
        return result["content"] or ""

    def get_stats(self) -> dict:
        return {
            "call_count": self.call_count,
            "total_tokens": self.total_tokens,
        }
