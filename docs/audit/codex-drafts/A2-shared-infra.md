## 1. `shared/llm_caller/` 唯一 LLM caller

**module file paths**  
`shared/llm_caller/{client,prompts,audit,retry,provider}.py`

**用途 1 句**  
把 root `llm.py` 的成熟调用能力和 `shared/llm/router.py` 的 PIPL 境内优先 fallback 收编成唯一生产入口，后续 6 agent 只保留 thin adapter。

**API design**

```python
# shared/llm_caller/provider.py
@dataclass(frozen=True)
class ProviderSpec:
    name: Literal["deepseek", "qwen", "dashscope", "moonshot"]
    model: str
    region: Literal["cn", "overseas"]
    config_key: str
    api_key_env: str

@dataclass
class LLMResult:
    content: str = ""
    json_payload: dict | list | None = None
    provider: str = ""
    model: str = ""
    region: str = "cn"
    usage: dict[str, int] = field(default_factory=dict)
    cached: bool = False
    fallback_chain: list[str] = field(default_factory=list)
    fallback_tried: list[str] = field(default_factory=list)

class LLMProvider(Protocol):
    def chat(self, messages: list[dict], **kwargs) -> LLMResult: ...
    def chat_json(self, messages: list[dict], schema_hint: str = "", **kwargs) -> LLMResult: ...
    def is_available(self) -> bool: ...

def get_provider(name: str | None = None) -> LLMProvider: ...
def resolve_fallback_chain(chain: list[str] | None = None) -> list[str]: ...
def list_providers() -> list[ProviderSpec]: ...
```

```python
# shared/llm_caller/client.py
class LLMCaller:
    def __init__(self, chain: list[str] | None = None, audit: bool = True, cache_enabled: bool = True): ...
    def chat(self, messages: list[dict], *, temperature: float | None = None, response_format: dict | None = None, tools: list[dict] | None = None, tool_choice: str = "auto") -> LLMResult: ...
    def simple_chat(self, system: str, user: str, *, temperature: float | None = None) -> str: ...
    def chat_json(self, system: str, user: str, *, schema_hint: str = "", temperature: float | None = None) -> dict | list | None: ...

def make_text_caller(**kwargs) -> Callable[[str, str], str]: ...
def make_json_caller(**kwargs) -> Callable[[str, str, str], dict | list | None]: ...
```

```python
# shared/llm_caller/retry.py
@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 2
    backoff_seconds: float = 0.2
    retry_on: tuple[type[Exception], ...] = (TimeoutError, RuntimeError)

def call_with_retry(fn: Callable[[], LLMResult], policy: RetryPolicy) -> LLMResult: ...
```

```python
# shared/llm_caller/audit.py
@dataclass
class LLMAuditRecord:
    run_id: str | None
    agent_id: str | None
    provider: str
    region: str
    model: str
    fallback_chain: list[str]
    fallback_tried: list[str]
    usage: dict[str, int]
    status: Literal["ok", "fallback", "error"]

def emit_llm_audit(record: LLMAuditRecord) -> None: ...
```

```python
# shared/llm_caller/prompts.py
def messages(system: str, user: str) -> list[dict[str, str]]: ...
def json_schema_hint(schema: dict | str) -> str: ...
```

**现有 caller 怎么 deprecate**

- `llm.py:54-70` 的 `LLMClient` 保留为兼容 shim，内部委托 `shared.llm_caller.client.LLMCaller`；原因是现有 cache/json/tool 能力成熟。
- `shared/llm/router.py:27-35` 的 `_REGISTRY` 和 fallback chain 迁入 `provider.py`；`shared/llm/__init__.py:23-25` 当前声明“不强制迁移”，A2 应改成 deprecated re-export。
- `agent_report/api.py:264-301` 的 `_build_llm_caller()` 删除硬编 `OpenAI(base_url="https://api.deepseek.com")`，改 `make_text_caller()`。
- `agent_riskctrl/llm_judge.py:123-124`、`agent_alert/api.py:312-313`、`agent_compliance/scan_engine.py:84-100` 改 thin adapter 调 `make_text_caller/make_json_caller`。
- `shared/kb_scan/impls/channel_signal.py:311` 是唯一生产侧 fallback 使用点，应改 import 到新包。

**pytest 测点**

- fallback 默认链境内优先：`deepseek -> dashscope/qwen -> moonshot`，失败 metadata 记录 `fallback_tried`。
- no key 时 provider skipped，全失败抛统一异常。
- `simple_chat/chat_json` 返回兼容 root `LLMClient` 的 string / dict shape。
- deprecated `shared.llm.router.chat_with_fallback` re-export 行为不破坏唯一生产 import。
- audit record 不写 prompt 原文，只写 provider/model/usage/fallback。

**待 PM 拍板 open question**

PIPL fallback 顺序必须定稿：`deepseek,qwen,dashscope,moonshot` 还是沿用当前 `shared/llm/router.py:35` 的 `deepseek,dashscope`；`moonshot` 是否允许默认链内启用，还是只能显式 opt-in。

---

## 2. `shared/sse_envelope.py` 后端 SSE 共形

**module file paths**  
`shared/sse_envelope.py`

**用途 1 句**  
统一 6 agent 后端 SSE event 名、stage payload 和 done payload，让前端唯一 `_live.ts streamSse` 能消费同一 shape。

**API design**

```python
@dataclass(frozen=True)
class SSEEnvelope:
    event: Literal["stage", "data", "done", "error"]
    payload: dict[str, Any]
    run_id: str | None = None
    agent_id: str | None = None
    stage: str | None = None
    status: Literal["queued", "running", "done", "error"] | None = None

def stage_event(
    *,
    agent_id: str,
    run_id: str,
    stage: str,
    status: Literal["queued", "running", "done", "error"],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]: ...

def data_event(
    *,
    agent_id: str,
    run_id: str,
    payload: dict[str, Any],
    stage: str | None = None,
) -> dict[str, Any]: ...

def done_event(
    *,
    agent_id: str,
    run_id: str,
    result: dict[str, Any],
    data_source: Literal["live", "mock", "fixture", "mixed"],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]: ...

def error_event(
    *,
    agent_id: str,
    run_id: str,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]: ...

def sse_encode(event: dict[str, Any]) -> str: ...
```

Common `done` shape:

```python
{
  "event": "done",
  "payload": {
    "agent_id": "...",
    "run_id": "...",
    "status": "done",
    "result": {...},
    "data_source": "live|mock|fixture|mixed",
    "metadata": {...}
  }
}
```

**现有 caller 怎么 deprecate**

- `agent_channel/realtime_stream.py:228-237` 当前 done 顶层散放 `candidates/metrics/data_source`，改为 `done_event(result={...})`。
- `agent_alert/api.py:105-112` 当前 stage 包一层 `{"event":"stage","payload":cleaned}`，done 是空 `{"event":"done"}`；改为 stage/done helper。
- `agent_credit/api.py:387` mock/live done 不对称，必须都走 `done_event()`。
- `agent_compliance/api.py:121` 在 conflict register 里记录为空 done，改同一 helper。
- `agent_report/api.py:16-19` 注释仍标 V14-B event 约定，改引用 A1 `docs/contracts/sse-envelope.md`。
- `agent_riskctrl/api.py:50` 被登记为“显式非 SSE”，但前端 `web/src/lib/api/riskctrl.ts:44` 期待 SSE；A2 只给 helper，A4 决定 endpoint 迁移。

**pytest 测点**

- `stage_event` 必含 `event/payload/agent_id/run_id/stage/status`。
- `done_event` 禁止空 payload，`result` 必须 dict。
- `sse_encode` 输出 `data: <json>\n\n`，中文不 ASCII escape 也能被 JSON parse。
- `error_event` 不泄露 traceback 默认内容，details 显式传才出现。
- 旧顶层字段 `candidates/metrics` 不应出现在 done 顶层。

**待 PM 拍板 open question**

`done.payload.result` 是否按 agent 自由 schema，还是 A1 合同必须规定 6 agent 顶层 keys；Channel charter 已点名 `candidates / signal_timeline / radar / profile_brief / hero_summary`（`docs/reset/phase-a-charter.md:77-79`），其他 5 agent 是否也要同级强约束。

---

## 3. `shared/prompts/contract.py` 8 段 prompt skeleton

**module file paths**  
`shared/prompts/contract.py`

**用途 1 句**  
先落 8 段 prompt skeleton，等 A1 `docs/contracts/llm-prompt-contract.md` done 后只填内容不换 API。

**API design**

```python
class PromptSection(str, Enum):
    SAFETY = "safety"
    EVIDENCE_FIRST = "evidence_first"
    AGENT_ROLE = "agent_role"
    TOOL_USE = "tool_use"
    OUTPUT_SCHEMA = "output_schema"
    SELF_CHECK = "self_check"
    FEW_SHOT = "few_shot"
    EVALUATION_HOOK = "evaluation_hook"

@dataclass(frozen=True)
class PromptContract:
    agent_id: str
    sections: Mapping[PromptSection, str]
    version: str = "skeleton-v0"

    def render_system(self, include: Iterable[PromptSection] | None = None) -> str: ...
    def validate_required(self) -> None: ...

def skeleton(agent_id: str) -> PromptContract: ...
def render_system_prompt(agent_id: str, overrides: Mapping[PromptSection, str] | None = None) -> str: ...
def render_messages(agent_id: str, user: str, overrides: Mapping[PromptSection, str] | None = None) -> list[dict[str, str]]: ...
```

8 段来自 Phase A A1 交付定义：`safety/evidence-first/agent-role/tool-use/output-schema/self-check/few-shot/evaluation-hook`，见 `docs/reset/phase-a-charter.md:52-57`。本轮我未读 `docs/onboarding/A2-shared-infra.md`，也不假设 A1 合同正文。

**现有 caller 怎么 deprecate**

- `section_generator.py:36-211` 的 `_EVIDENCE_SYSTEM_PROMPT` 等 inline 三阶段 Evidence-First prompt 改为从 contract skeleton 渲染。
- `prompts.py:42-60` 的 `AGENT_SYSTEM_PROMPT` 与 Agent6 inline prompt 角色重复，保留 agent-specific override，不再做全局 SSOT。
- `agent_channel/prompts.py:52` 的 `PITCH_GEN_SYSTEM` 缺 evidence-first 约束，迁成 `overrides[AGENT_ROLE]`。
- `agent_alert/prompts.py:13-37`、`agent_riskctrl/prompts.py:13-44`、`agent_compliance/prompts.py:19-36`、`agent_credit/prompts.py:16` 都只保留业务 role/output override，不再自建完整 system prompt。
- Cat 6 证据汇总见 `docs/audit/sub-agent-step2-round1/instruction.md:19-24`。

**pytest 测点**

- `skeleton(agent_id)` 总是包含 8 个 `PromptSection`。
- `validate_required()` 对缺段抛 `ValueError`，对空 skeleton 可通过但标记 `version="skeleton-v0"`。
- `render_system()` 输出段落顺序稳定，避免测试 snapshot 抖动。
- overrides 只能覆盖已知 section，未知 key 抛错。
- `render_messages()` 输出 OpenAI-compatible `[{role:"system"}, {role:"user"}]`。

**待 PM 拍板 open question**

A1 合同完成前，A2 是否允许填充最小安全文本，还是 skeleton 段落必须保持占位空文本；我倾向占位但可运行，避免 A2 偷跑定义 prompt 政策。

---

## 4. `tests/shared/` pytest spec

**module file paths**  
`tests/shared/test_llm_caller.py`  
`tests/shared/test_sse_envelope.py`

**用途 1 句**  
用无网络、可 monkeypatch 的单元测试锁住唯一 caller、PIPL fallback、SSE 共形和向后兼容 shim。

**API design**

```python
# tests/shared/test_llm_caller.py
def test_default_fallback_chain_cn_first(monkeypatch): ...
def test_fallback_skips_unavailable_and_records_tried(monkeypatch): ...
def test_chat_json_returns_dict_shape(monkeypatch): ...
def test_make_text_caller_matches_legacy_signature(monkeypatch): ...
def test_shared_llm_router_deprecated_reexport(monkeypatch): ...
def test_audit_record_excludes_prompt_text(): ...
```

```python
# tests/shared/test_sse_envelope.py
def test_stage_event_shape(): ...
def test_done_event_shape_requires_result(): ...
def test_error_event_shape_has_code_message(): ...
def test_sse_encode_round_trips_json(): ...
def test_done_event_has_no_legacy_top_level_agent_payload_fields(): ...
```

**现有 caller 怎么 deprecate**

- Tests should freeze that `llm.py:54` legacy `LLMClient` remains importable while implementation direction moves to new caller.
- Tests should freeze `shared/llm/router.py:105-144` wrapper compatibility for `chat_with_fallback/chat_json_with_fallback`, because `shared/kb_scan/impls/channel_signal.py:311` is already production import.
- Tests should cover the replacement path for `agent_alert/api.py:306-317` and `agent_compliance/scan_engine.py:78-104` by asserting `make_text_caller/make_json_caller` signatures match their current local builders.
- Tests should not call real OpenAI/DeepSeek; `agent_report/api.py:282-294` is exactly the anti-pattern.

**pytest 测点**

- No env keys: providers unavailable, no network attempt, deterministic exception.
- Main provider raises, backup succeeds: result provider is backup, `fallback_chain` full, `fallback_tried` includes main.
- Explicit chain filters unknown providers or raises clear config error; PM choice needed.
- SSE event JSON can be parsed by frontend `_live.ts streamSse` style reader.
- Empty done payload is invalid, matching Cat 4 failures in `agent_alert/api.py:112` and `agent_credit/api.py:387`.

**待 PM 拍板 open question**

现有 `shared/llm/tests/test_router.py` 是否保留在原目录作为 compatibility tests，还是迁到 `tests/shared/test_llm_caller.py` 后删除；我建议保留一小组 re-export tests，避免唯一生产 import 断裂。

---

## Dissent Appendix

我的主要异议：不要把 `shared/llm/` 直接重命名删除。虽然 conflict register 说 `shared/llm/router.py:27-32 + __init__.py:25` 是“0 production import”，实际 `rg` 显示 `shared/kb_scan/impls/channel_signal.py:311` 已经生产侧 import `chat_with_fallback`。所以 A2 应该新增 `shared/llm_caller/`，再让 `shared/llm/` 成为 deprecated re-export，而不是硬切。第二个异议：PIPL fallback 不应由工程师默认扩大到 moonshot；`shared/llm/base.py:24` 已区分 `cn/overseas`，但 PM 必须拍板境外 provider 是否进入默认链。第三个异议：A2 不应替 A1 写 prompt 政策正文，只能按 `docs/reset/phase-a-charter.md:12` 和 `:52-57` 落 8 段骨架。