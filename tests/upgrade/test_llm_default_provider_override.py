"""LLM_DEFAULT_PROVIDER · 根 llm.LLMClient 的默认 provider 覆盖开关.

背景 (2026-09-08 形态版演示): ECS 上 DEEPSEEK_API_KEY 失效 (401) · 授信/获客示例卡死;
DashScope key 有效 · 用 env 把硬编码默认 deepseek 整体改指 qwen_cloud · 不逐处改调用方.
"""
import llm


def _client(**kw):
    return llm.LLMClient(cache_enabled=False, **kw)


def test_override_redirects_default_deepseek_and_drops_foreign_key(monkeypatch):
    monkeypatch.setenv("LLM_DEFAULT_PROVIDER", "qwen_cloud")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test-dashscope")
    c = _client(provider="deepseek", api_key="sk-old-deepseek")
    assert c.provider == "qwen_cloud"
    assert c.model == llm.MODEL_CONFIG["qwen_cloud"]["model"]
    assert c.api_key == "sk-test-dashscope"  # DeepSeek 的 key 不能塞给 DashScope


def test_override_leaves_explicit_other_provider_alone(monkeypatch):
    monkeypatch.setenv("LLM_DEFAULT_PROVIDER", "qwen_cloud")
    monkeypatch.setenv("ZHIPU_API_KEY", "sk-test-zhipu")
    c = _client(provider="glm_cloud")
    assert c.provider == "glm_cloud"
    assert c.api_key == "sk-test-zhipu"


def test_no_override_without_env(monkeypatch):
    monkeypatch.delenv("LLM_DEFAULT_PROVIDER", raising=False)
    c = _client(provider="deepseek", api_key="sk-explicit")
    assert c.provider == "deepseek"
    assert c.api_key == "sk-explicit"


def test_unknown_override_value_is_ignored(monkeypatch):
    monkeypatch.setenv("LLM_DEFAULT_PROVIDER", "no_such_provider")
    c = _client(provider="deepseek", api_key="sk-explicit")
    assert c.provider == "deepseek"
    assert c.api_key == "sk-explicit"
