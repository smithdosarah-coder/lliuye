# -*- coding: utf-8 -*-
"""Agent 基类 — 统一 Generator 事件协议"""

from __future__ import annotations
import sys
import os
import json
import re
from typing import Generator, Any

# 将项目根目录加入路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from llm import LLMClient
from pydantic import BaseModel


class BaseAgent:
    """所有Agent的基类，提供统一的事件协议和LLM调用"""

    agent_name: str = "base"
    agent_title: str = "基础Agent"

    def __init__(self, api_key: str = "", model_provider: str = "deepseek",
                 base_url: str = "", model_name: str = ""):
        # LLMClient 从 config.MODEL_CONFIG 按 provider 自动取 base_url 和 model，
        # 保留 base_url/model_name 参数以兼容旧调用点，但不传给 LLMClient。
        self.llm = LLMClient(provider=model_provider, api_key=api_key)
        self.stats = {"filled": 0, "errors": []}

    def process_message(self, user_message: str,
                        uploaded_files: list[str] | None = None
                        ) -> Generator[dict, None, None]:
        """子类必须实现此方法，通过yield返回事件"""
        raise NotImplementedError

    # ---- 事件辅助方法 ----

    def _thinking(self, msg: str) -> dict:
        return {"type": "thinking", "content": msg}

    def _message(self, msg: str) -> dict:
        return {"type": "message", "content": msg}

    def _tool_call(self, name: str, status: str = "running") -> dict:
        return {"type": "tool_call", "name": name, "status": status}

    def _tool_result(self, name: str, result: str) -> dict:
        return {"type": "tool_result", "name": name, "result": result}

    def _file(self, path: str) -> dict:
        return {"type": "file", "path": path}

    def _done(self, msg: str = "完成") -> dict:
        return {"type": "done", "content": msg}

    # ---- LLM 调用辅助 ----

    def llm_chat(self, system: str, user: str) -> str:
        """简单LLM调用，返回文本"""
        return self.llm.simple_chat(system, user)

    def llm_json(self, system: str, user: str,
                 model_class: type[BaseModel] | None = None,
                 retries: int = 3) -> dict | BaseModel:
        """LLM调用，返回结构化JSON，带重试"""
        if model_class:
            schema = json.dumps(model_class.model_json_schema(),
                                ensure_ascii=False, indent=2)
            system += f"\n\n请严格以JSON格式输出，schema如下：\n{schema}"

        system += "\n\n仅输出JSON，不要其他文字。用```json```包裹。"

        for attempt in range(retries):
            try:
                resp = self.llm.simple_chat(system, user)
                # 提取JSON
                resp = re.sub(r'```json\s*', '', resp)
                resp = re.sub(r'```\s*', '', resp)
                json_match = re.search(r'\{[\s\S]*\}', resp)
                if not json_match:
                    # 尝试匹配数组
                    json_match = re.search(r'\[[\s\S]*\]', resp)
                if json_match:
                    data = json.loads(json_match.group())
                    if model_class and isinstance(data, dict):
                        return model_class.model_validate(data)
                    return data
            except (json.JSONDecodeError, Exception) as e:
                if attempt == retries - 1:
                    raise ValueError(
                        f"LLM未返回有效JSON（{retries}次重试后）: {str(e)[:200]}"
                    )
        return {}

    # ---- 文件读取辅助 ----

    def read_files(self, file_paths: list[str]) -> dict[str, str]:
        """读取多个文件，返回 {文件名: 内容}"""
        from tools import tool_read_files
        return tool_read_files(file_paths)

    def search_web(self, query: str) -> str:
        """联网搜索"""
        from tools import tool_search_web
        return tool_search_web(query)
