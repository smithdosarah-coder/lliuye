---
sub-agent: architecture
cat: [1, 2, 3, 4, 11]
date: 2026-04-29
round: 1
---

| Cat | file:line | 证据 (≤80 char) | Keep / Revert / Rewrite |
|---|---|---|---|
| 1 | CLAUDE.md:184 | "agent_report/ 为 API wrapper 层 unreleased" — api.py 已全量实现且 api_server 挂载 | Rewrite |
| 1 | CLAUDE.md:165 | "legacy_gradio/ 已归档" — legacy_gradio/ 内 form_filler.py/narrative_pipeline.py 仍存在 | Rewrite |
| 1 | docs/reset/north-star.md:76 | "CLAUDE.md §3.1 写 'shared/ 没 llm_caller' stale" — §3.1 原文无此句，north-star 引用错误 | Rewrite |
| 1 | docs/reset/north-star.md:59 | "3 套 LLM caller…第 4 套" 编号矛盾 (标题说 3 套, 正文列 4 套: root/shared/report/_build) | Rewrite |
| 1 | docs/contracts/workspace-state-protocol.md:13 | gap 表引 ChannelWorkspace.tsx:67-254 — 文件实际行已重写，行号 stale | Rewrite |
| 2 | web/src/app/archive/alert/_components/AlertWorkspace.tsx:77-106 | 有 started · 无 selectedSession / liveData / selectedCandidate 三 gate | Rewrite |
| 2 | web/src/app/archive/compliance/_components/ComplianceWorkspace.tsx:83-107 | 有 started · 无 selectedSession / liveData / selectedCandidate 三 gate | Rewrite |
| 2 | web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx:98-122 | 有 started · 无 selectedSession / liveData / selectedCandidate 三 gate | Rewrite |
| 2 | web/src/app/archive/credit/_components/CreditWorkspace.tsx:89-116 | 有 started/liveAdvice · 无 selectedSession / selectedCandidate gate | Rewrite |
| 2 | web/src/app/archive/report/_components/ReportWorkspace.tsx | 有 liveFailErr · 无 selectedSession / selectedCandidate / liveData gate | Rewrite |
| 3 | web/src/app/archive/channel/_components/ChannelWorkspace.tsx:1400 | `res.body.getReader()` 内联 SSE 解析 · 未用 shared `streamSse` | Rewrite |
| 3 | web/src/app/archive/credit/_components/CreditWorkspace.tsx:157 | `res.body.getReader()` 内联 SSE 解析 · 未用 shared `streamSse` | Rewrite |
| 3 | web/src/lib/api/_live.ts:76 | `streamSse` 已定义 · 但 4/6 workspace 完全不 import · 0 调用 | Rewrite |
| 4 | agent_channel/realtime_stream.py:229 | done 只含 candidates/metrics/data_source · 缺 radar/signals/funnel (workspace-state-protocol §4 要求) | Rewrite |
| 4 | agent_alert/api.py:112 | `{"event":"done"}` 空 payload · 无任何 panel 数据字段 | Rewrite |
| 4 | agent_credit/api.py:387 | done 事件: mock 路有完整 payload · live 路 `{"event":"done"}` 空 — 不对称 | Rewrite |
| 4 | agent_report/api.py:16-19 | 事件名注释标 "V14-B 约定"(旧版命名) · 实现已是 v16 · contract 名称漂 | Rewrite |
| 11 | legacy_gradio/app.py | CLAUDE.md 声明 legacy_gradio 已归档 · 但 form_filler.py 仍在 legacy_gradio/ 可被 import | Revert |
| 11 | web/src/app/archive/channel/_components/ChannelWorkspace.tsx:182 | "live 优先 · mock fallback" derive 有 fallback · 但无 banner (banner-spec 规则 2 缺 mock 选择通知) | Rewrite |
| 11 | web/src/app/archive/credit/_components/CreditWorkspace.tsx:1658 | 历史(示例)按钮无 mock-session banner · 选后静默渲 mock (banner-spec 规则 2 违反) | Rewrite |
