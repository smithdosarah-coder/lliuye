---
sub-agent: instruction
cat: [1, 6, 7]
date: 2026-04-29
round: 1
---

| Cat | file:line | 证据 (≤80 char) | Keep / Revert / Rewrite |
|---|---|---|---|
| 7 | `agent_report/api.py:264-301` | `_build_llm_caller()` 裸 `OpenAI(base_url="api.deepseek.com")` · 第 4 套 caller · 跳 llm.LLMClient + shared/llm 全部 | Rewrite |
| 7 | `llm.py:56` | Caller 1: `class LLMClient` · OpenAI 兼容封装 · 带 cache/json/FC · 大多数 agent 用此套 | Keep (主干) |
| 7 | `shared/llm/router.py:27-32` | Caller 2: `shared.llm` Protocol + fallback chain · 2026-04-28 建 · `_REGISTRY` 4 provider | Keep (待接管) |
| 7 | `agent_riskctrl/llm_judge.py:123-124` | Caller 3: `from llm import LLMClient` lazy init · 独立 `LLMJudge` 基类 · 游离 shared/llm | Rewrite |
| 7 | `shared/llm/__init__.py:25` | 注释声明"6 Agent 现有 import 不强制改 (additive · spec gap 留 main CLI fix-forward)" | Keep (待 worker-A2 接管) |
| 7 | `shared/kb_scan/impls/channel_signal.py:311` | 唯一生产侧 `from shared.llm.router import chat_with_fallback` · 5 个 agent_*/api.py 均未用 | Rewrite (扩展接入) |
| 7 | `agent_alert/api.py:312-313` | `from llm import LLMClient(provider="deepseek")` · 未走 shared/llm fallback chain | Rewrite |
| 7 | `agent_compliance/scan_engine.py:84-85,99-100` | 两处 `LLMClient(provider="deepseek")` · 重复初始化 · 未走 shared/llm | Rewrite |
| 7 | `agent_riskctrl/api.py:141-142` | `LLMClient(provider=req.provider, api_key=req.api_key)` · 直接暴露 provider 选择给前端 · 跳 fallback | Rewrite |
| 6 | `section_generator.py:36-211` | 三阶段 Evidence-First prompt 内联定义 (`_EVIDENCE_SYSTEM_PROMPT` 等) · 未从 `prompts.py` 引入 | Rewrite |
| 6 | `prompts.py:42-60` | `AGENT_SYSTEM_PROMPT` 定义信贷分析师角色 · 与 `section_generator.py` 三阶段 inline prompt 角色定义重叠但措辞漂 | Rewrite |
| 6 | `agent_channel/prompts.py:52` | `PITCH_GEN_SYSTEM = "你是资深银行客户经理"` · 无 evidence-first 约束 · 与 root `prompts.py` `_DATA_CITATION_RULES` 脱轨 | Rewrite |
| 6 | `agent_alert/prompts.py:13-37` | `SYSTEM_RISK_SCAN` 含 "以事实和数据为依据" 但无 evidence-first 三阶段结构 · 与 Agent6 实现范式不一致 | Rewrite |
| 6 | `agent_riskctrl/prompts.py:13-44` | `SYSTEM_RULE_PARSER` 无任何 evidence/溯源约束 · 对照 root `_DATA_CITATION_RULES` 漂移明显 | Rewrite |
| 6 | `agent_compliance/prompts.py:19-36` | `SYSTEM_POLICY_PARSE` / `SYSTEM_COMPLIANCE_CHECK` · "严格以JSON格式输出" 约束 · 无出处/溯源条款 | Rewrite |
| 1 | `decisions-log.md:Q-040:A-040.1` | `MAX_ROWS=500→50000` active fix · 代码已改 (`backtesting.py:25`) · **未回写 CLAUDE.md** | Rewrite |
| 1 | `decisions-log.md:Q-041` | `candidate metadata 4 字段 (industry/geo/scale/similarity)` active rule · B.5 dispatch 时注入 · **未回写 CLAUDE.md §11/§4** | Rewrite |
| 1 | `shared/llm/__init__.py:25` | PIPL 境内优先 LLM fallback chain 是架构决策 (2026-04-28) · **CLAUDE.md §3.x 无此条款** | Rewrite |
| 1 | `agent_riskctrl/llm_judge.py:24-25` | 注释标"spec 分歧由主 CLI Task D 裁决" · 裁决结果未写入 decisions-log · 悬空 | Rewrite |
