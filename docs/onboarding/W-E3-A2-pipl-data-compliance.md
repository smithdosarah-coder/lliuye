# Worker A2 (Stage E.2 第 1 批) · PIPL Data Compliance + LLM Provider Abstract · Onboarding

> Worker CLI 在 `D:/claude code/work-A2-contracts` (branch
> `feat/contracts-bootstrap-A2`) · 复用 worktree。
> 上批 Stage D.1 frontend (`ab25ad2` → ae58f2f) 已 cherry-pick MERGED ·
> 本批 Stage E.3 启动 (PIPL 数据合规)。

## Goal

实装 master plan §E.3 — PIPL 数据合规 · **banking 必修** ·
解决 Q-040 提的 Tavily 境外问题。

核心:
- LLM 提供商抽象层 (LLMProvider Protocol) · 支持 DeepSeek + DashScope + Qwen + Moonshot
- Tavily 境外 → 切境内备份 (百度 / 搜狗 search API · 替代 fallback)
- 数据加密层 (LLM call body 加密存 audit · 按需解密)
- .env 强随机密钥 (移除 _DEFAULT_DEMO_SECRET fallback · production 强制)

## Acceptance

- [ ] **新建** `shared/llm/` module:
  - `base.py` (LLMProvider Protocol · chat/chat_json)
  - `providers/{deepseek,dashscope,qwen,moonshot}.py`
  - `router.py` (按 .env LLM_PROVIDER 选)
- [ ] **6 Agent backend** 改用 `shared/llm/router` (现各 Agent 直接 import deepseek client)
- [ ] **shared/sources/impls/** 加 `baidu_search.py` + `sogou_search.py` · degrader 接入
- [ ] **数据加密**: `audit_service/recorder.py` prompt/response 加 AES-GCM 加密 · query 解密
- [ ] curl 测各 provider 真接 (env 切换 · DeepSeek/DashScope/Qwen 各跑一次)
- [ ] pytest `shared/llm/tests/` ≥ 15 case (provider 切换 · fallback chain · 加密)
- [ ] commit trailer:
  ```
  Signal: WORKER-A2-STAGE-E3-PIPL-COMPLIANCE-DONE
  RECOVER-FROM: ab25ad2 (D.1 frontend done · 本批接续)
  NEW-MODULE: shared/llm/{base,providers/*,router,tests}
  COMPLIANCE: PIPL · 境内 LLM 备份 · Tavily 境内替代 · audit 加密
  ```

## Boundary

- **改**: 6 Agent backend (改 import shared/llm) · audit_service/recorder.py (加密)
- **加**: shared/llm/* · shared/sources/impls/{baidu_search,sogou_search}.py
- **不动**: web/* · auth_service/* · im_service/* · CLAUDE.md · RFC

## Method

1. 设计 LLMProvider Protocol (chat / chat_json / stream)
2. 4 provider impl (DeepSeek 现 + DashScope + Qwen + Moonshot)
3. router 按 .env 切 (LLM_PROVIDER=deepseek|dashscope|qwen|moonshot)
4. 6 Agent 改 import (surgical · 不改业务)
5. baidu/sogou search 替 Tavily 境内 fallback
6. AES-GCM 加密 audit (cryptography 库)
7. pytest 15+ case · curl 验 4 provider

## Estim

10-15 hr (LLM provider 抽象 + 4 impl + 加密 + 集成测试)
