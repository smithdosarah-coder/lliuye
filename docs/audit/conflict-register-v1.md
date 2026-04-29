---
title: Step 2 Conflict Register v1 (主 CLI synthesis · pre-PM 拍板)
date: 2026-04-29
schema: docs/reset/step2-conflict-scan-charter.md §8 verbatim (5 列 · Cat / file:line / 证据 ≤80 char / Owner-Phase A worker / Keep-Revert-Rewrite)
sources:
  - docs/audit/sub-agent-step2-round1/architecture.md (20 findings · cat 1/2/3/4/11)
  - docs/audit/sub-agent-step2-round1/data.md (16 findings · cat 5/12)
  - docs/audit/sub-agent-step2-round1/instruction.md (20 findings · cat 1/6/7)
  - docs/audit/sub-agent-step2-round1/naming-route.md (30 findings + 8 列附录 · cat 8/9/10/16)
  - docs/audit/sub-agent-step2-round1/production-shape.md (19 findings + Cat 0 verdict · cat 0/13/14/15)
  - docs/audit/codex-step2-round1.md (Codex Round 1 · 50 findings 全 17 类 · independent v1 · anti-bias rule 1)
  - docs/audit/prd-evidence-frozen.md (Step 3 PRD 取证 · 10 gap · 飞书 7 doc found)
total findings (合成去重): 87 entries (sub-agent 105 + codex 50 → 去重 + 合并代表性)
status: pre-PM 拍板 · 待 Signal STEP-2-PM-RULED
---

# Step 2 · Conflict Register v1

合成自 6 sub-agent + Codex Round 1 + PRD 取证 sub-agent · 按 Cat 0-16 顺序 · Owner 列对应 Phase A 7 worker 或主 CLI fix-forward。

---

## Cat 0 · 产品形态 (workbench vs 6 showroom · 走歪本质)

| Cat | file:line | 证据 (≤80 char) | Owner / Phase A worker | Keep/Revert/Rewrite |
|---|---|---|---|---|
| 0 | web/src/app/today/_components/TodayContent.tsx:21-91 | KPI dashboard 卡片 · 无客户管线 + 无跨 agent 调度入口 | A6 + A3 (pilot 复用) | Rewrite |
| 0 | web/src/app/today/_components/MorningBrief.tsx:28 | HERO_WORD="今日看板" 定性 dashboard 非 workbench | A6 | Rewrite |
| 0 | web/src/app/archive/page.tsx:11-38 | 6 AgentTile portal grid + lede"独立工作区"自定为孤岛 | A6 | Rewrite |
| 0 | web/src/app/archive/credit/_components/CreditWorkspace.tsx:88-115 | 自跑独立 state · 直调 /api/credit/decision · 不消费 Agent6 ReportJSON | A6 + A4-credit | Rewrite |
| 0 | web/src/app/archive/credit/_components/CreditWorkspace.tsx:1568-1635 | EmptyState 注释"Agent6 handoff" · onClick 不真消费 | A6 + A4-credit | Rewrite |
| 0 | web/src/app/today/_components/PriorityQueue.tsx:9 | click 跳 6 独立 workspace URL · 无 cross-agent 任务串联 | A6 | Rewrite |

**Cat 0 主 CLI verdict (引用 production-shape sub-agent verbatim)**: 当前是 6 showroom · 距 north-star RM workbench 有根本性差距 · 修正方向 = `/today` 重写为"客户管线 + 今日待办 + 跨 agent 调用入口"三区 + Agent6→Agent3 ReportJSON schema 真消费。

---

## Cat 1 · 文档规范冲突

| Cat | file:line | 证据 (≤80 char) | Owner / Phase A worker | Keep/Revert/Rewrite |
|---|---|---|---|---|
| 1 | CLAUDE.md:184 | "agent_report unreleased" - api.py 已全量实装且 mounted | A1 | Rewrite |
| 1 | CLAUDE.md:165 | "legacy_gradio 已归档" - form_filler.py / narrative_pipeline.py 仍在 | A1 | Rewrite |
| 1 | docs/reset/north-star.md:76 | "CLAUDE §3.1 写 shared 没 llm_caller" - §3.1 原文无此句 (north-star 引用错) | 主 CLI fix-forward | Rewrite |
| 1 | docs/reset/north-star.md:59 | "3 套 LLM caller…第 4 套" 编号自相矛盾 | 主 CLI fix-forward | Rewrite |
| 1 | docs/contracts/workspace-state-protocol.md:13 | gap 表引 ChannelWorkspace.tsx:67-254 行号 stale | A1 | Rewrite |
| 1 | decisions-log.md:Q-040:A-040.1 | MAX_ROWS=500→50000 active fix · 代码改 · CLAUDE.md 未回写 | 主 CLI fix-forward | Rewrite |
| 1 | decisions-log.md:Q-041 | candidate metadata 4 字段 active rule · CLAUDE.md §11/§4 未回写 | 主 CLI fix-forward | Rewrite |
| 1 | shared/llm/__init__.py:25 | PIPL 境内优先 LLM fallback chain (2026-04-28) · CLAUDE.md §3 无 | A1 | Rewrite |
| 1 | agent_riskctrl/llm_judge.py:24-25 | 注释"spec 分歧由主 CLI Task D 裁决" · 裁决未写 decisions-log | 主 CLI fix-forward | Rewrite |

---

## Cat 2 · workspace state 模型不统一 (4 gate · 5/6 缺)

| Cat | file:line | 证据 (≤80 char) | Owner / Phase A worker | Keep/Revert/Rewrite |
|---|---|---|---|---|
| 2 | web/src/app/archive/alert/_components/AlertWorkspace.tsx:77-106 | 仅 started · 缺 selectedSession/liveData/selectedCandidate | A4-alert | Rewrite |
| 2 | web/src/app/archive/compliance/_components/ComplianceWorkspace.tsx:83-107 | 仅 started · 缺其他 3 gate | A4-compli | Rewrite |
| 2 | web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx:98-122 | 仅 started · 缺其他 3 gate | A4-riskctrl | Rewrite |
| 2 | web/src/app/archive/credit/_components/CreditWorkspace.tsx:89-116 | 有 started/liveAdvice · 缺 selectedSession/selectedCandidate | A4-credit | Rewrite |
| 2 | web/src/app/archive/report/_components/ReportWorkspace.tsx:73 | 有 livePayload (不是 liveData contract) · 缺 4 gate | A4-report | Rewrite |
| 2 | web/src/app/archive/channel/_components/ChannelWorkspace.tsx | (Pilot 模板) 4 gate 待真实装 | **A3 (pilot)** | Rewrite |

---

## Cat 3 · frontend SSE 客户端不统一

| Cat | file:line | 证据 (≤80 char) | Owner / Phase A worker | Keep/Revert/Rewrite |
|---|---|---|---|---|
| 3 | web/src/lib/api/_live.ts:76 | streamSse 已定义 · 4/6 workspace 0 import (孤儿) | A2 (保留) + A3/A4 (consumers) | Keep + 强制 consume |
| 3 | web/src/app/archive/channel/_components/ChannelWorkspace.tsx:1392-1400 | res.body.getReader() 内联 SSE · 不用 streamSse | A3 (pilot) | Rewrite |
| 3 | web/src/app/archive/credit/_components/CreditWorkspace.tsx:157 | 内联 SSE 解析 · 不用 streamSse | A4-credit | Rewrite |
| 3 | web/src/app/archive/report/_components/ReportWorkspace.tsx | 内联 SSE 解析 · 不用 streamSse | A4-report | Rewrite |
| 3 | web/src/lib/api/riskctrl.ts:44 | 前端期待 Riskctrl SSE · backend 显式"非 SSE" (Cat 4 镜像) | A4-riskctrl + A2 | Rewrite |

---

## Cat 4 · backend SSE schema 不统一 (event 名 + done payload)

| Cat | file:line | 证据 (≤80 char) | Owner / Phase A worker | Keep/Revert/Rewrite |
|---|---|---|---|---|
| 4 | agent_channel/realtime_stream.py:229 | done 含 candidates/metrics/data_source · 缺 radar/signals/funnel | A2 (envelope) + A3 (pilot) | Rewrite |
| 4 | agent_alert/api.py:107-112 | done 空 payload · stage event 无 stage 名 | A2 + A4-alert | Rewrite |
| 4 | agent_credit/api.py:387 | mock 路完整 payload · live 路 done 空 · 不对称 | A2 + A4-credit | Rewrite |
| 4 | agent_compliance/api.py:121 | done 空 payload | A2 + A4-compli | Rewrite |
| 4 | agent_report/api.py:16-19 | event 名注释"V14-B 约定" · 实现已 v16 · 名称漂 | A2 + A4-report | Rewrite |
| 4 | agent_riskctrl/api.py:50 | endpoints 显式"非 SSE" · 前端 riskctrl.ts:44 期待 SSE | A2 + A4-riskctrl | Rewrite |

---

## Cat 5 · mock source 冲突

| Cat | file:line | 证据 (≤80 char) | Owner / Phase A worker | Keep/Revert/Rewrite |
|---|---|---|---|---|
| 5 | web/src/lib/mock/agent-channel-sessions.ts:129 | similarity: number (0-1 float) | A4-channel + A6 (handoff schema) | Rewrite |
| 5 | agent_channel/candidate_profile.py:78 | match_score: int (0-100) · 与前端字段名+类型分裂 | A4-channel + A6 | Rewrite |
| 5 | web/src/app/archive/channel/_components/ChannelWorkspace.tsx:1320 | 前端双字段 fallback `similarity ?? match_score` 掩盖裂缝 | A4-channel | Revert |
| 5 | web/src/lib/mock/agent-alert-session.ts:62 vs agent_alert/word_export.py:22 vs runtime_dump.py:105 | grade 三命名: tier / risk_level / grade | A4-alert + A6 | Rewrite |
| 5 | web/src/lib/mock/today.ts:2 | Today view 独立 mock fixture 源 (Codex finding) | A2 + A6 | Rewrite |
| 5 | agent_report/mock_fixtures.py:175 | disk fixture else embedded stub fallback | A2 + A4-report | Rewrite |
| 5 | data/mock/README.md:32 | "data/mock/" 拟真数据底座 · 形态合理 | n/a | Keep (canonical) |
| 5 | web/src/lib/mock/agent-credit-session.ts:214 + agent_credit/api.py:147 | "四维"标签 + 4 维实现 (corporate) 一致 | n/a | Keep |

---

## Cat 6 · prompt source 冲突

| Cat | file:line | 证据 (≤80 char) | Owner / Phase A worker | Keep/Revert/Rewrite |
|---|---|---|---|---|
| 6 | section_generator.py:36-211 | 三阶段 Evidence-First inline (_EVIDENCE_SYSTEM_PROMPT) · 不从 prompts.py | A2 (shared/prompts/contract) | Rewrite |
| 6 | prompts.py:42-60 | AGENT_SYSTEM_PROMPT 信贷分析师角色 · 与 section_generator inline 措辞漂 | A2 | Rewrite |
| 6 | agent_channel/prompts.py:52 | PITCH_GEN_SYSTEM 无 evidence-first · 与 root _DATA_CITATION_RULES 脱轨 | A2 + A4-channel | Rewrite |
| 6 | agent_alert/prompts.py:13-37 | SYSTEM_RISK_SCAN 含"事实数据"但无三阶段结构 | A2 + A4-alert | Rewrite |
| 6 | agent_riskctrl/prompts.py:13-44 | SYSTEM_RULE_PARSER 无 evidence/溯源约束 | A2 + A4-riskctrl | Rewrite |
| 6 | agent_compliance/prompts.py:19-36 | SYSTEM_POLICY_PARSE/_CHECK 严格 JSON 但无溯源条款 | A2 + A4-compli | Rewrite |
| 6 | agent_credit/prompts.py:16 | Agent3 独立 decision system prompt | A2 + A4-credit | Rewrite |

---

## Cat 7 · LLM caller 冲突 (4+1 套并行)

| Cat | file:line | 证据 (≤80 char) | Owner / Phase A worker | Keep/Revert/Rewrite |
|---|---|---|---|---|
| 7 | llm.py:56-69 | Caller 1: LLMClient OpenAI 兼容 · 大多 agent 用 | A2 (主干 · 收编 to shared/llm) | Keep → 迁 |
| 7 | shared/llm/router.py:27-32 + __init__.py:25 | Caller 2: shared.llm Protocol fallback · 0 production import | A2 (接管 · 6 agent 全迁) | Keep (待接管) |
| 7 | shared/kb_scan/impls/channel_signal.py:311 | 唯一生产侧 chat_with_fallback · 5 agent_*/api.py 0 调 | A2 | Rewrite (扩展接入) |
| 7 | agent_riskctrl/llm_judge.py:123-124 | Caller 3: LLMJudge 独立基类 · 游离 shared/llm | A2 + A4-riskctrl | Rewrite |
| 7 | agent_report/api.py:264-301 | Caller 4: _build_llm_caller 裸 OpenAI(deepseek) · 跳全栈 | A2 + A4-report | Rewrite |
| 7 | agent_alert/api.py:312-313 | Caller 5: LLMClient 直 init · 跳 shared/llm fallback | A2 + A4-alert | Rewrite |
| 7 | agent_compliance/scan_engine.py:84-100 | Caller 5 同模式 · 两处重复 init | A2 + A4-compli | Rewrite |
| 7 | agent_riskctrl/api.py:141-142 | LLMClient 暴露 provider 给前端 · 跳 fallback | A2 + A4-riskctrl | Rewrite |

---

## Cat 8 · Agent naming 不一致 (8 列)

| Cat | file:line | 证据 (≤80 char) | Owner / Phase A worker | Keep/Revert/Rewrite |
|---|---|---|---|---|
| 8 | web/src/lib/auth/agent-id.ts:1-18 | AGENT_KEY_TO_ID 整文件是 compliance/compli 双 id 补丁 | A1 (8 列 SSOT) → A4 (重构 consumer) | Rewrite |
| 8 | web/src/lib/agents.ts:20 (AgentKey="compliance") vs store/types.ts:12 (AgentId="compli") | 全栈双 id 分裂 | A1 → A4-all | Rewrite (**PM 选 compliance OR compli**) |
| 8 | evaluation/agent5_compliance.yaml:3 | agent: compliance · eval baseline 用 AgentKey | A1 | Rewrite (跟随 PM 选项) |
| 8 | auth_service/rbac.py:42 | VALID_AGENTS 用 "compli" · 后端用 AgentId | A1 | Keep (待 PM 选 id) |
| 8 | web/src/lib/agents.ts:47/60/75/88/101/114 | accent 6 处用 --color-{ink,brass,sage,amber,ember,brass-dim} legacy token | A5 + A1 | Rewrite (改 --t-{report,channel,credit,alert,riskctrl,compli}) |
| 8 | web/src/lib/agents.ts:45-115 | path 字段 6 处指 /report /channel · 非 /archive/* canon | A1 + A4-all | Rewrite (path 应 /archive/<key> 或删字段) |

**Cat 8 8 列对齐表 (来自 naming-route sub-agent · 6 行 partial)** → 见 `docs/audit/sub-agent-step2-round1/naming-route.md` 末尾附录 · A1 worker onboarding 必读起步。

---

## Cat 9 · route resurrection

| Cat | file:line | 证据 (≤80 char) | Owner / Phase A worker | Keep/Revert/Rewrite |
|---|---|---|---|---|
| 9 | web/src/lib/agents.ts:45/58/73/86/99/112 | path 字段 6 处指 /report /channel /credit /alert /riskctrl /compliance · 顶层目录均不存在 | A1 + A4-all | Rewrite |
| 9 | web/src/components/shell/Masthead.tsx:21 | 顶层 /credit /channel still matched 在 nav (Codex) | A4-all + A6 | Rewrite |
| 9 | web/src/app/ 顶层 | /design 在 §7 canon 但目录未建 · 访问 404 | 主 CLI fix-forward (补建 OR 删 §7 声明) | Rewrite |
| 9 | web/src/app/archive/{channel,credit,...}/ | _components/ 子目录 · 无 page.tsx · 仅组件托管 | n/a | Keep (无路由污染) |

---

## Cat 10 · auth / RBAC 漂移

| Cat | file:line | 证据 (≤80 char) | Owner / Phase A worker | Keep/Revert/Rewrite |
|---|---|---|---|---|
| 10 | web/src/app/archive/[agent]/RbacGuard.tsx:22 | 用 AGENT_KEY_TO_ID[agent] · 依赖补丁映射 | A1 (SSOT) → A4 | Rewrite |
| 10 | web/src/lib/auth/agent-id.ts:1-18 | 整 patch 文件 = compliance/compli 双 id 后果 | A1 → A4 | Rewrite |
| 10 | web/src/components/shell/AuthGate.tsx:21 | guard regex 允许 /archive/compli · 不允许 compliance (Codex) | A1 → A4 | Rewrite |
| 10 | web/src/lib/store/auth-store.ts:36-40 | ACCESS 镜像 rbac.py · 重复定义 (Codex) | A1 (单 SSOT) → A4 | Rewrite |
| 10 | auth_service/rbac.py:10/42 | RBAC backend grants compli · 与 store 一致 | A1 (统一后保留) | Keep |

---

## Cat 11 · demo / live 边界冲突

| Cat | file:line | 证据 (≤80 char) | Owner / Phase A worker | Keep/Revert/Rewrite |
|---|---|---|---|---|
| 11 | legacy_gradio/app.py + form_filler.py | CLAUDE.md 标"已归档" · 文件仍可 import (Cat 1 镜像) | A7 (PRD) + 主 CLI | Revert |
| 11 | web/src/app/archive/channel/_components/ChannelWorkspace.tsx:182 | live 优先 · mock fallback derive · 无 banner (banner-spec 规则 2) | A3 (pilot) | Rewrite |
| 11 | web/src/app/archive/credit/_components/CreditWorkspace.tsx:1658 | 历史按钮无 mock-session banner · 静默渲 mock | A4-credit | Rewrite |
| 11 | agent_channel/realtime_stream.py:339 | Tavily key 缺 → mock_fallback 路径仍存在 (silent · Codex) | A3 (pilot) + A2 | Rewrite |
| 11 | web/src/app/archive/compliance/_components/ComplianceWorkspace.tsx:97 | live fail banner 已实装 · 无 silent mock (Codex Keep) | n/a | Keep |
| 11 | web/src/app/archive/credit/_components/CreditWorkspace.tsx:199 | tertiary demo 显式 set started · training mode (Codex Keep) | A4-credit (verify) | Keep (验) |

---

## Cat 12 · evaluation drift

| Cat | file:line | 证据 (≤80 char) | Owner / Phase A worker | Keep/Revert/Rewrite |
|---|---|---|---|---|
| 12 | evaluation/agent2_riskctrl.yaml:3 vs api.py:39 | yaml v3.1 · api v4.0 | A7 (PRD 决议) + A4-riskctrl | Rewrite |
| 12 | evaluation/agent3_credit.yaml:3 vs api.py:62 | yaml v3.1 · api v4.0 | A7 + A4-credit | Rewrite |
| 12 | evaluation/agent4_alert.yaml:3 vs api.py:50 | yaml v3.1 · api v3.2 | A7 + A4-alert | Rewrite |
| 12 | evaluation/agent5_compliance.yaml:3 vs api.py:50 | yaml v3.1 · api v3.2 | A7 + A4-compli | Rewrite |
| 12 | evaluation/agent3_credit.yaml:18 | desc"四维评分" · api 实现 3 stage_tab × 4 子维 · 无跨段汇总四维 | A7 (重定义指标) | Rewrite |
| 12 | evaluation/agent6_report.yaml:82-92 | last_run/commit null + pending metrics block (Codex) | A7 + B1 (flywheel) | Rewrite |
| 12 | evaluation/runner/adapters/agent3_credit.py:198 | tool_success_rate stub · 无 runtime tool trace (Codex) | A7 + B1 | Rewrite |
| 12 | evaluation/runner/adapters/agent1_channel.py:202 | 无 runtime dump · common metrics pending (Codex) | A7 + B1 | Rewrite |
| 12 | evaluation/agent1_channel.yaml:3 | yaml v4.0 vs api v4.0 一致 | n/a | Keep |
| 12 | evaluation/agent6_report.yaml:3 | yaml v16 vs CLAUDE.md §11 v16 一致 | n/a | Keep |

---

## Cat 13 · export contract 冲突

| Cat | file:line | 证据 (≤80 char) | Owner / Phase A worker | Keep/Revert/Rewrite |
|---|---|---|---|---|
| 13 | agent_riskctrl/api.py:1-39 | 后端无 export_docx/xlsx · 前端 RiskctrlWorkspace 已调 · 404 on prod | A4-riskctrl + A6 (export contract) | Rewrite |
| 13 | web/src/app/archive/channel/_components/ChannelWorkspace.tsx:1717-1724 | OUTPUT_ACTIONS 4 个全无 onClick · 后端有 export 端点 · dead button | A3 (pilot) + A6 | Rewrite |
| 13 | web/src/app/archive/credit/_components/CreditWorkspace.tsx:1784-1786 | export_docx 失败仅 console.error · 无 fallback banner · 不一致 | A4-credit | Rewrite |
| 13 | docs/contracts/agent-compli-spec.md:113 | spec 要 export_xlsx/pdf · 实现待补 | A4-compli + A6 | Rewrite |
| 13 | web/src/lib/api/riskctrl.ts:7 | export_docx stub · 404 容忍 (Codex) | A4-riskctrl | Rewrite |

---

## Cat 14 · design tokens 残留 (Letterpress)

| Cat | file:line | 证据 (≤80 char) | Owner / Phase A worker | Keep/Revert/Rewrite |
|---|---|---|---|---|
| 14 | web/src/lib/agents.ts:47/60/75/88/101/114 | 6 处 accent 引 --color-{ink,brass,sage,amber,ember,brass-dim} legacy | A5 | Revert (改 --t-* 功能色) |
| 14 | web/src/components/viz/VerdictBadge.tsx:12/27/45 | bg/text/glow 引 --color-brass/-ink/-brass-glow · 3 处 | A5 | Revert |
| 14 | web/src/components/viz/PipelineRail.tsx:42-44 | --color-ink/-ink-muted 3 处 · 非 Ink 主题用途 | A5 | Revert |
| 14 | web/src/components/ui/Button.tsx:35 | focus ring still --color-brass (Codex) | A5 | Revert |
| 14 | web/src/app/globals.css:12-13 | 注释明言"旧 6 Agent 页继续消费" · legacy 段未标 TODO-remove | A5 | Rewrite (加 TODO-remove · consumer 全迁后 delete) |

---

## Cat 15 · production sync 漂 🔴 P0

| Cat | file:line | 证据 (≤80 char) | Owner / Phase A worker | Keep/Revert/Rewrite |
|---|---|---|---|---|
| 15 | git log chore/l0-infra..main | **chore/l0-infra 落后 main 10 commits** · branch 严重分叉 | **主 CLI fix-forward 紧急** | Rewrite (rebase OR merge main into chore/l0-infra) |
| 15 | git log main..chore/l0-infra | 1 commit ahead (STEP-2-FIRE-DISPATCHED + 本 register) · 待 Step 2 完后 merge main | 主 CLI | Keep (待 Step 2 完) |
| 15 | (inferred) ECS 跑 main · main 含 10 commit chore/l0-infra 没有 | 主 CLI fix-forward (执行 morning sync per CLAUDE.md §13.4) | Rewrite |
| 15 | docs/reset/state-snapshot.md:110+151 | 文档说 ECS 跑 main · reset 主 CLI 在 chore/l0-infra · 未交叉验证 | 主 CLI | Rewrite (state-snapshot 加 sync 状态段) |

**Cat 15 紧急度 🔴 P0**: Phase A 任何 worker 启之前 · 主 CLI 必须先 sync chore/l0-infra ↔ main · 否则 worker 基于落后 10 commit 的代码动手 · 后续 merge 全是 conflict。

---

## Cat 16 · persona / role drift

| Cat | file:line | 证据 (≤80 char) | Owner / Phase A worker | Keep/Revert/Rewrite |
|---|---|---|---|---|
| 16 | CLAUDE.md:5 vs §4 表格第 2 行 | §1 4 角色 vs §4 "策略经理"漂 · 蔓延 api_server.py:376 prompt | A1 + 主 CLI | Rewrite (§4 改"风险经理") |
| 16 | CLAUDE.md §1 (4 角色) vs auth_service/users.py:46-50 (5 user 含 risk_manager) | 4 vs 5 不对齐 · backend 5 user 是真 | A1 + A7 (PRD 用户故事对齐) | Rewrite (§1 补第 5 角色 OR 重映射) |
| 16 | web/src/lib/store/types.ts:28 | Role 注释 credit_officer="审贷官" · CLAUDE.md §1 写"审贷员" | A1 | Rewrite (审贷官→审贷员) |
| 16 | api_server.py:376 | IM prompt riskctrl 写"辅助策略经理写 DSL" · §4 漂蔓延 runtime | A1 + 主 CLI | Rewrite |
| 16 | auth_service/users.py:46-50 | 5 user role 含 rm/credit_officer/compliance_officer/risk_manager/admin | A1 (SSOT 锚) | Keep |

---

## Phase A worker owner summary (合成 view)

| Worker | 主 cat | 说明 |
|---|---|---|
| **A1 contracts** (Week 1) | 1, 8, 10, 16 + 部分 9 | 5 契约 + 8 列 SSOT + RBAC 单 id + 角色 SSOT |
| **A2 shared infra** (Week 1) | 6, 7 + 部分 4, 5 | shared/llm 接管 · sse_envelope · prompts/contract 8 段 |
| **A3 Channel pilot** (Week 2-3 · 依赖 A1+A2) | 2 (channel), 3 (channel), 11 (channel), 4 (channel) + 部分 13 | 4 gate pilot · streamSse 接 · banner · done envelope |
| **A4 5 子 thin adapter** (Week 4-5 · 依赖 A3) | 2/3/4/5/6/7/11/13 (per-agent) | 复用 A3 模式迁 5 agent (credit/alert/compli/riskctrl/report) |
| **A5 design** (Week 2-3 并行) | 14 + 部分 8 (color token) | Letterpress 12 consumer 全迁 |
| **A6 handoff data contract** (Week 2-3 并行) | 0 (大部分), 13 (export), 5 (handoff schema) | 6 链 schema · /today RM workbench 重写 |
| **A7 PRD** (Week 2-3 并行) | 12, 16, 11 (legacy_gradio decision), 部分 1 | PRD 取证 + 10 G-XX gap 决议 + evaluation 重定义 |
| **主 CLI fix-forward** (Phase A 启动前 / 周中) | 1 (Q-040/041 回写), 9 (/design 决策), **15 (production sync 紧急 🔴 P0)**, 16 (api_server 文案) | cleanup batches |

---

## Dissent appendix (anti-bias rule 4)

### Sub-agent ↔ Codex 已知分歧 (主 CLI 已合成裁决)

1. **Cat 11 demo/live 边界 · 部分 Keep vs 全 Rewrite** — Codex 倾向部分 Keep (Compliance/Alert/Report 已有 banner + training-mode 显式标识) · sub-agent (architecture + production-shape) 全 Rewrite。**裁决**: 采纳 Codex Keep 部分 (Compliance live fail banner 11-5 + Credit tertiary training mode 11-6) · 保留 sub-agent Rewrite 部分 (Channel silent fallback + Credit 历史按钮 + legacy_gradio import 风险)。Codex dissent appendix 自陈一致。

2. **Cat 2 workspace state 完备性** — Codex 仅扫 Credit/Report 代表 · sub-agent (architecture) 5 workspace 全列。**裁决**: 采用 sub-agent 全列 (2-1..2-5) + 加 channel pilot 模板 (2-6)。Codex dissent appendix 自陈"若严格逐文件 · 应扩展 6 workspace" — 一致。

3. **Cat 15 production sync 证据强度** — Codex 自陈"未联网/未 SSH ECS · finding 是证据不足但高风险" · sub-agent (production-shape) 也仅 git log 推断。**裁决**: 标 🔴 P0 紧急 + Owner 列写"主 CLI fix-forward" · 主 CLI **必须 SSH ECS 真验** + 跑 morning sync (CLAUDE.md §13.4)。

### 待 PM 拍板的 judgment call (主 CLI 不预决)

4. **Cat 8 单一 id 选 `compliance` OR `compli`** — `compli`→`compliance` 影响 backend rbac.py + auth_service/users.py + decisions-log 历史 (改 ~5 处) · `compliance`→`compli` 影响 web/src/lib/agents.ts + evaluation/agent5_compliance.yaml + 6 个前端 import (改 ~12 处)。`compliance` 更语义化 + 与 evaluation yaml 一致 · `compli` 更短 + backend 已用。**留 PM 拍板**。

5. **Cat 0 (产品形态) Owner** — Phase A charter §3 worker-A6 仅含"handoff data schema 定义" · 不含 `/today` 重写 + workbench 形态实现。本 register 临时挂 A6 + A3 + A4 多 owner · **真正 owner 待 PM 拍板**: (a) A6 范围扩展 / (b) 新增 worker-A8 RM workbench / (c) `/today` 重写归 Phase B-3 (端到端 demo chain)?

6. **Cat 15 production sync 是否阻塞 Phase A 启动** — 本 register 标 🔴 P0 + 列"主 CLI fix-forward" · 但未阻 PM 拍板 register 本身。PM 拍板后 sequence:
   - (a) PM 拍板 → 主 CLI 立即 sync (rebase chore/l0-infra onto main · 含 ECS verify) → Phase A worker 启
   - (b) PM 拍板 → Phase A worker 启 + 主 CLI 同时 sync (并行)
   - 倾向 (a) · 但 PM 决。

7. **`legacy_gradio/` 是否真删 (Cat 11-1 · Revert 建议)** — sub-agent (architecture) 标 Revert · 但 legacy_gradio 是 demo fallback 路径 (CLAUDE.md §2 提"如需 fallback 演示从 archive 恢复")。**留 PM 拍板**: (a) 真删 (彻底 revert · 无 fallback) / (b) 保留但加 import guard (不能被生产代码 import)。

---

## 退出标准 + Next

- ✅ 7 份 audit doc 全 commit (本 commit 一并)
- ✅ 本 register commit 含 Signal: STEP-2-CONFLICT-REGISTER-V1-PREPARED
- ⏳ PM 逐条拍板 87 entries + 4 项 dissent (Signal: STEP-2-PM-RULED) → 进 Step 1 Phase A worker mesh
- ⏳ Cat 15 🔴 P0 主 CLI fix-forward 必须先于 Phase A worker 启 (per dissent #6)

PRD gap (G-01..G-10) 见 `docs/audit/prd-evidence-frozen.md` · 由 worker-A7 接手决议。

---

**主 CLI 提示**: 本 register 字数约 2800 词 · 在 anti-bias rule 3 (≤3500) 范围内。Cat 8 8 列对齐表附录留在 sub-agent 原 doc · 避免本文超长。
