| Cat | file:line | 证据 (≤80 char) | Keep / Revert / Rewrite |
|---|---|---|---|
| 0 | web/src/app/today/_components/TodayContent.tsx:29 | Link `/dispatch` + agent running cards, not RM workbench core | Rewrite |
| 0 | web/src/app/archive/page.tsx:11 | 6 AgentTile grid links to `/archive/<key>` showroom | Rewrite |
| 0 | docs/reset/north-star.md:35 | RM→Agent1→Agent6→Agent3→Agent4→Agent5 closed loop | Keep |
| 1 | docs/reset/north-star.md:76 | says CLAUDE §3.1 stale: shared llm already landed | Rewrite |
| 1 | docs/reset/north-star.md:77 | Q-040/Q-041 active decisions not back-written to CLAUDE | Rewrite |
| 2 | docs/contracts/workspace-state-protocol.md:37 | required started gate | Keep |
| 2 | web/src/app/archive/credit/_components/CreditWorkspace.tsx:112 | only `started`, no selectedSession/liveData/selectedCandidate model | Rewrite |
| 2 | web/src/app/archive/report/_components/ReportWorkspace.tsx:73 | `livePayload`, not shared `liveData` contract | Rewrite |
| 3 | web/src/lib/api/_live.ts:76 | `streamSse` exists as shared client | Keep |
| 3 | web/src/app/archive/channel/_components/ChannelWorkspace.tsx:1392 | Channel hand-rolls `fetch /api/channel/run` reader | Rewrite |
| 3 | web/src/lib/api/riskctrl.ts:44 | frontend expects Riskctrl SSE | Rewrite |
| 4 | agent_riskctrl/api.py:50 | Riskctrl endpoints explicitly “非 SSE” | Rewrite |
| 4 | agent_alert/api.py:107 | emits `{event:"stage", payload: cleaned}` no stage name | Rewrite |
| 4 | agent_compliance/api.py:121 | emits empty `{event:"done"}` | Rewrite |
| 5 | data/mock/README.md:32 | `data/mock/` as拟真数据底座 | Keep |
| 5 | web/src/lib/mock/today.ts:2 | Today view has separate mock fixture source | Rewrite |
| 5 | agent_report/mock_fixtures.py:175 | disk fixture else embedded stub fallback | Rewrite |
| 6 | prompts.py:42 | root Agent6 system prompt source | Rewrite |
| 6 | agent_credit/prompts.py:16 | Agent3 owns separate decision system prompt | Rewrite |
| 6 | agent_compliance/prompts.py:83 | Agent5 owns separate event extract prompt | Rewrite |
| 7 | llm.py:69 | root `OpenAI(...)` LLMClient | Rewrite |
| 7 | shared/llm/__init__.py:2 | `shared.llm` abstraction exists | Rewrite |
| 7 | agent_report/api.py:264 | Agent6 `_build_llm_caller` fourth caller | Rewrite |
| 8 | web/src/lib/agents.ts:104 | AgentKey is `"compliance"` | Rewrite |
| 8 | auth_service/rbac.py:42 | RBAC valid agent is `"compli"` | Rewrite |
| 8 | web/src/lib/auth/agent-id.ts:16 | patch map `compliance: "compli"` | Rewrite |
| 9 | web/src/lib/agents.ts:58 | metadata path resurrects `/channel` | Rewrite |
| 9 | web/src/lib/agents.ts:112 | metadata path resurrects `/compliance` | Rewrite |
| 9 | web/src/components/shell/Masthead.tsx:21 | top-level `/credit`,`/channel` still matched | Rewrite |
| 10 | web/src/components/shell/AuthGate.tsx:21 | guard regex allows `/archive/compli`, not compliance | Rewrite |
| 10 | auth_service/rbac.py:10 | backend grants `compli` | Rewrite |
| 10 | web/src/lib/store/auth-store.ts:36 | frontend store duplicates RBAC matrix | Rewrite |
| 11 | web/src/app/archive/compliance/_components/ComplianceWorkspace.tsx:97 | live fail banner, no silent mock | Keep |
| 11 | agent_channel/realtime_stream.py:339 | missing Tavily key → `mock_fallback` path still exists | Rewrite |
| 11 | web/src/app/archive/credit/_components/CreditWorkspace.tsx:199 | tertiary demo sets started without backend | Keep |
| 12 | evaluation/agent6_report.yaml:92 | Agent6 has pending metrics block | Rewrite |
| 12 | evaluation/runner/adapters/agent3_credit.py:198 | tool_success_rate stub, no runtime tool trace | Rewrite |
| 12 | evaluation/runner/adapters/agent1_channel.py:202 | no runtime dump → common metrics pending | Rewrite |
| 13 | web/src/lib/api/riskctrl.ts:7 | export_docx stub, 404 tolerated | Rewrite |
| 13 | agent_riskctrl/api.py:5 | only dsl_gen/backtest endpoints listed | Rewrite |
| 13 | docs/contracts/agent-compli-spec.md:113 | spec wants export_xlsx/pdf too | Rewrite |
| 14 | web/src/lib/agents.ts:60 | uses legacy `--color-brass` | Rewrite |
| 14 | web/src/lib/agents.ts:47 | uses legacy `--color-ink` accent | Rewrite |
| 14 | web/src/components/ui/Button.tsx:35 | focus ring still `--color-brass` | Rewrite |
| 15 | docs/reset/state-snapshot.md:110 | production says ECS runs `main` | Rewrite |
| 15 | docs/reset/state-snapshot.md:151 | reset main CLI says `chore/l0-infra` | Rewrite |
| 15 | CLAUDE.md:200 | required flow push GitHub `main` then ECS pull | Rewrite |
| 16 | CLAUDE.md:5 | product roles: RM / reviewer / compliance / risk | Rewrite |
| 16 | CLAUDE.md:82 | Agent2 trigger says “策略经理” | Rewrite |
| 16 | auth_service/users.py:46 | demo users include rm/compliance/risk, no strategy_manager | Rewrite |

Dissent appendix: 我可能会比其他 sub-agent 更倾向把 Cat 11 的部分 demo/live 处理判为 Keep，因为 Compliance/Alert/Report 已有显式 banner 与 training-mode 标识；但 Channel 的 backend fallback 仍是边界风险，所以我未整体放过。Cat 15 我只能用 repo 文档与本地 git 状态交叉判断，未联网/未 SSH ECS，因此 production sync finding 是“证据不足但高风险”的 Rewrite。Cat 2 上我没有把每个 workspace 缺少完整 4 gate 都列满，优先抽了 Credit/Report 作为代表；若其他扫描者要求严格逐文件登记，应扩展为 6 workspace 明细。