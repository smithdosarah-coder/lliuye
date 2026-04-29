verdict: AGREE

issue-1-fixed: yes  
`shared/llm_caller/retry.py:53-80` adds `api_key` into `_try_each` and bypasses `provider.is_available()` when explicit `api_key` is provided. Both `chat_with_fallback` and `chat_json_with_fallback` pass it through at `retry.py:117-119` and `retry.py:141-143`. Provider construction already consumes the explicit key via `provider.py:135-140`.

issue-2-fixed: yes  
`shared/sse_envelope.py:250-255` now rejects fully empty done payloads, including `make_done()` and `data_source`-only cases. Tests cover empty, data-source-only, and accepted payload-bearing cases.

issue-3-fixed: yes  
`shared/llm_caller/client.py:150-169` adds `LLMCaller.simple_chat()`. `client.py:217-264` adds `make_text_caller()`, and `client.py:267-315` adds `make_json_caller()`. They are exported from both `client.py:318-323` and `shared/llm_caller/__init__.py:68-96`.

issue-4-fixed: yes  
`shared/prompts/contract.py:267-282` now always skips `_PENDING_A1_SPEC` sections, regardless of `strict`; `strict=True` still raises after collecting pending sections. This matches the module comment intent: default render no longer leaks placeholders.

remaining concerns: none blocking for the 4 V1 DISAGREE items.  
Minor note: I reviewed the target commit via git object inspection because the current checkout is on `chore/l0-infra` at `bcb0cf3`, not `feat/phase-a2-shared` at `114b562`; I did not run the test suite from that branch.