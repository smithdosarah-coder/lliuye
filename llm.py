# -*- coding: utf-8 -*-
"""
LLM 抽象层 — 统一接口,一行切换模型

支持 provider:
  deepseek / deepseek-reasoner  (官方 API)
  qwen_cloud                    (阿里云 DashScope OpenAI 兼容)
  glm_cloud                     (智谱 OpenAI 兼容)
  local_vllm                    (本地 vLLM 自部署,OpenAI 兼容)
  openai / anthropic            (海外备用)
  kimi-k2.5 / minimax           (NVIDIA 代理)

能力:
  - chat(messages, tools=None)         普通对话 / Function Calling
  - simple_chat(system, user)          简单对话
  - chat_json(system, user, schema)    强制结构化 JSON 输出
  - 磁盘缓存(按 provider+messages+schema hash),避免重复调用
  - 调用统计
"""

import hashlib
import json
import os
import time
from pathlib import Path

from openai import OpenAI

from config import LLM_CACHE_DIR, MODEL_CONFIG


def _resolve_api_key(conf: dict, explicit_key: str = "") -> str:
    """按优先级取 key: 显式传入 > 环境变量(由 conf 指定 key 名) > 空"""
    if explicit_key:
        return explicit_key
    env_name = conf.get("api_key_env", "")
    if env_name:
        return os.environ.get(env_name, "").strip()
    return ""


def _hash_messages(provider: str, model: str, messages: list[dict],
                   schema: dict | None, temperature: float) -> str:
    """消息哈希用于 cache key"""
    payload = {
        "p": provider,
        "m": model,
        "t": round(temperature, 3),
        "msg": messages,
        "schema": schema,
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:24]


class LLMClient:
    """统一的 LLM 客户端,支持普通对话、Function Calling、JSON 模式、磁盘缓存"""

    def __init__(self, provider: str = "deepseek", api_key: str = "",
                 cache_enabled: bool = True):
        self.provider = provider
        conf = MODEL_CONFIG.get(provider, MODEL_CONFIG["deepseek"])
        self.model = conf["model"]
        self.max_tokens = conf["max_tokens"]
        self.temperature = conf["temperature"]
        self.supports_json_mode = conf.get("supports_json_mode", False)

        self.api_key = _resolve_api_key(conf, api_key)
        self.client = OpenAI(
            api_key=self.api_key or "sk-placeholder",
            base_url=conf["base_url"],
        )

        self.cache_enabled = cache_enabled
        self.cache_dir = Path(LLM_CACHE_DIR) / provider
        if cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.call_count = 0
        self.cache_hit_count = 0
        self.total_tokens = 0

    def _cache_read(self, key: str) -> dict | None:
        if not self.cache_enabled:
            return None
        f = self.cache_dir / f"{key}.json"
        if f.exists():
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None

    def _cache_write(self, key: str, payload: dict) -> None:
        if not self.cache_enabled:
            return
        f = self.cache_dir / f"{key}.json"
        try:
            f.write_text(json.dumps(payload, ensure_ascii=False),
                         encoding="utf-8")
        except Exception:
            pass

    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             tool_choice: str = "auto", temperature: float | None = None,
             response_format: dict | None = None,
             use_cache: bool = True) -> dict:
        """
        统一聊天接口
        返回: {
            "content": str | None,
            "tool_calls": [{"id", "name", "arguments"}] | None,
            "usage": {"prompt", "completion", "total"},
            "from_cache": bool
        }
        """
        temp = temperature if temperature is not None else self.temperature

        # 缓存查找(只对无工具调用的情况启用)
        cache_key = None
        if use_cache and not tools:
            cache_key = _hash_messages(
                self.provider, self.model, messages, response_format, temp)
            cached = self._cache_read(cache_key)
            if cached is not None:
                self.cache_hit_count += 1
                cached["from_cache"] = True
                return cached

        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": temp,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
        if response_format:
            kwargs["response_format"] = response_format

        resp = self.client.chat.completions.create(**kwargs)
        choice = resp.choices[0]

        result = {
            "content": choice.message.content,
            "tool_calls": None,
            "usage": {
                "prompt": resp.usage.prompt_tokens if resp.usage else 0,
                "completion": resp.usage.completion_tokens if resp.usage else 0,
                "total": resp.usage.total_tokens if resp.usage else 0,
            },
            "from_cache": False,
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

        if cache_key:
            self._cache_write(cache_key, result)

        return result

    def simple_chat(self, system_prompt: str, user_content: str,
                    temperature: float | None = None) -> str:
        """简单对话,不带工具,直接返回文本"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        result = self.chat(messages, temperature=temperature)
        return result["content"] or ""

    def chat_json(self, system_prompt: str, user_content: str,
                  schema_hint: str = "",
                  temperature: float | None = None,
                  max_retries: int = 2) -> dict | list:
        """
        强制 JSON 输出
        - supports_json_mode = True 的 provider: 使用 response_format={"type":"json_object"}
        - 否则: 只能在 system_prompt 里强约束,失败时 retry
        """
        sys = system_prompt
        if schema_hint:
            sys = f"{sys}\n\n【输出格式】\n{schema_hint}\n\n必须输出严格合法 JSON,不要 markdown 代码围栏,不要任何解释文字。"

        messages = [
            {"role": "system", "content": sys},
            {"role": "user", "content": user_content},
        ]

        response_format = {"type": "json_object"} if self.supports_json_mode else None

        last_err: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                result = self.chat(
                    messages, temperature=temperature,
                    response_format=response_format,
                    use_cache=(attempt == 0),
                )
                text = (result["content"] or "").strip()
                # 去掉可能的 markdown 围栏
                if text.startswith("```"):
                    # 删首尾代码块标记
                    lines = text.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    text = "\n".join(lines).strip()
                return json.loads(text)
            except (json.JSONDecodeError, KeyError) as e:
                last_err = e
                time.sleep(0.5)
                # 下一轮强化 instruction
                messages = [
                    {"role": "system", "content": sys + "\n\n【注意】上一次输出不是合法 JSON,请重新输出严格合法的 JSON。"},
                    {"role": "user", "content": user_content},
                ]
        raise RuntimeError(f"chat_json 失败(重试 {max_retries} 次): {last_err}")

    def get_stats(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "call_count": self.call_count,
            "cache_hit_count": self.cache_hit_count,
            "total_tokens": self.total_tokens,
        }
