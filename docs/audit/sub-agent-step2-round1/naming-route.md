---
sub-agent: naming-route
cat: [8, 9, 10, 16]
date: 2026-04-29
round: 1
---

| Cat | file:line | 证据 (≤80 char) | Keep / Revert / Rewrite |
|---|---|---|---|
| 8 | web/src/lib/agents.ts:20 | `AgentKey` 用 `"compliance"` · 全栈 frontend key | Keep (AgentKey 是前端 UI key) |
| 8 | web/src/lib/store/types.ts:12 | `AgentId` 用 `"compli"` · RBAC + store 契约 key | Keep (AgentId 是内部 store key) |
| 8 | web/src/lib/auth/agent-id.ts:16 | `compliance → compli` 补丁映射 · 双 id 并存全栈 | Rewrite (统一单一 id · 消除补丁层) |
| 8 | web/src/lib/agents.ts:47 | `accent: "var(--color-ink)"` · 已下架旧 token | Rewrite (改 `var(--t-report)`) |
| 8 | web/src/lib/agents.ts:60 | `accent: "var(--color-brass)"` · 旧 token | Rewrite (改 `var(--t-channel)`) |
| 8 | web/src/lib/agents.ts:75 | `accent: "var(--color-sage)"` · 旧 token · 不在 §7 | Rewrite (改 `var(--t-credit)`) |
| 8 | web/src/lib/agents.ts:88 | `accent: "var(--color-amber)"` · 旧 token | Rewrite (改 `var(--t-riskctrl)`) |
| 8 | web/src/lib/agents.ts:101 | `accent: "var(--color-ember)"` · 旧 token | Rewrite (改 `var(--t-alert)`) |
| 8 | web/src/lib/agents.ts:114 | `accent: "var(--color-brass-dim)"` · 旧 token | Rewrite (改 `var(--t-compli)`) |
| 8 | web/src/lib/agents.ts:45-115 | `path` 字段 `/report` `/channel` 等 · 非 `/archive/*` canon 路由 | Rewrite (path 应为 `/archive/report` 等或移除 path 字段) |
| 8 | evaluation/agent5_compliance.yaml:3 | `agent: compliance` · eval baseline 用 AgentKey "compliance" | Rewrite (统一后选一个 id 命名) |
| 8 | auth_service/rbac.py:42 | `VALID_AGENTS` 含 `"compli"` · 后端用 AgentId | Keep (后端统一用 AgentId · 与 store/types.ts 一致) |
| 9 | web/src/app/archive/channel/ | 命名子目录存在 (`_components/` + css) · 无 `page.tsx` · 非独立路由 · 仅组件托管 | Keep (无路由污染 · 组件托管合理) |
| 9 | web/src/lib/agents.ts:58 | `path: "/channel"` · 顶层路径 · 顶层 `/channel` 目录不存在 · path 指向不存在路由 | Rewrite (改为 `/archive/channel` 或移除) |
| 9 | web/src/lib/agents.ts:45 | `path: "/report"` · 顶层路径 · 顶层 `/report` 目录不存在 | Rewrite (同上) |
| 9 | web/src/lib/agents.ts:73 | `path: "/credit"` · 顶层路径 · 顶层 `/credit` 目录不存在 | Rewrite (同上) |
| 9 | web/src/lib/agents.ts:86 | `path: "/riskctrl"` · 顶层路径 · 顶层 `/riskctrl` 目录不存在 | Rewrite (同上) |
| 9 | web/src/lib/agents.ts:99 | `path: "/alert"` · 顶层路径 · 顶层 `/alert` 目录不存在 | Rewrite (同上) |
| 9 | web/src/lib/agents.ts:112 | `path: "/compliance"` · 顶层路径 · 顶层 `/compliance` 目录不存在 | Rewrite (同上) |
| 9 | web/src/app/ (顶层) | `/design` 在 §7 canon list 但目录未建 · 访问 404 | Rewrite (补建 design/ 目录 or 删 §7 声明) |
| 10 | auth_service/rbac.py:42 | `VALID_AGENTS` = `("channel","report","credit","alert","compli","riskctrl")` · compli 已对齐 backend | Keep |
| 10 | web/src/lib/store/auth-store.ts:36-40 | `ACCESS` 含 `"compli"` (AgentId) · 与 rbac.py 镜像一致 | Keep |
| 10 | web/src/lib/store/auth-store.ts:36 | `rm` 角色权限含 `"compli"` 全部 6 agent · 与 rbac.py 一致 | Keep |
| 10 | web/src/app/archive/[agent]/RbacGuard.tsx:22 | 用 `AGENT_KEY_TO_ID[agent]` 做 access check · 依赖补丁映射层 · compliance→compli | Rewrite (映射层消除后需直接传 AgentId) |
| 10 | web/src/lib/auth/agent-id.ts:1-18 | 整个 `AGENT_KEY_TO_ID` 文件是 compliance/compli 不一致的补丁产物 | Rewrite (根本修复 = 全栈统一单一 id) |
| 16 | CLAUDE.md:5 | §1 列 4 角色: 客户经理/审贷员/合规官/风险经理 | SSOT 声明 |
| 16 | CLAUDE.md:82 | §4 第 2 行: "Agent2 风控 \| **策略经理**发起" · 不在 §1 4 角色内 | Rewrite (§4 表格改"风险经理"或 §1 补第 5 角色) |
| 16 | auth_service/users.py:49 | `"risk_manager"` 是 backend role · 中文名对应"风险经理" (李华/陈凯) | Keep (backend role 正确) |
| 16 | auth_service/users.py:46-50 | 5 user 含 `rm/credit_officer/compliance_officer/risk_manager/admin` · 无 "策略经理" role | Keep (无漂移 · 漂移在文案层) |
| 16 | web/src/lib/store/types.ts:28 | `Role` 中文注释: `rm="客户经理"` / `credit_officer="审贷官"` · CLAUDE.md §1 写"审贷员" | Rewrite (审贷官 → 审贷员 · 对齐 §1) |
| 16 | api_server.py:376 | IM prompt: `riskctrl` = "辅助**策略经理**写 DSL" · §4 漂移蔓延到 runtime | Rewrite (对齐"风险经理"或专项 PM 决议) |

---

## Cat 8 · 8 列对齐表 (附录)

| agent_id | 中文 | 业务名 | UI brand | route | 色彩 token | RBAC role | eval baseline |
|---|---|---|---|---|---|---|---|
| channel (AgentKey) / channel (AgentId) | 全渠道获客 | look-alike 获客 | "全渠道获客" | /archive/channel (canon) · AgentDef.path="/channel" (错) | --t-channel (#3C7B7B) · agents.ts 用 --color-brass (旧 · 违 §7) | rm / admin | evaluation/agent1_channel.yaml (agent: channel) |
| report (AgentKey) / report (AgentId) | 信贷报告助手 | Agent6 报告 | "信贷报告助手" | /archive/report · AgentDef.path="/report" (错) | --t-report (#B08640) · agents.ts 用 --color-ink (旧 · 违 §7) | rm / credit_officer / compliance_officer / risk_manager / admin | evaluation/agent6_report.yaml (agent: report) |
| credit (AgentKey) / credit (AgentId) | 授信决策辅助 | Agent3 授信 | "授信决策辅助" | /archive/credit · AgentDef.path="/credit" (错) | --t-credit (#3E6292) · agents.ts 用 --color-sage (旧 · 违 §7) | rm / credit_officer / risk_manager / admin | evaluation/agent3_credit.yaml (agent: credit) |
| alert (AgentKey) / alert (AgentId) | 贷中风险预警 | Agent4 预警 | "贷中风险预警" | /archive/alert · AgentDef.path="/alert" (错) | --t-alert (#C85A3C) · agents.ts 用 --color-ember (旧 · 违 §7) | rm / credit_officer / compliance_officer / risk_manager / admin | evaluation/agent4_alert.yaml (agent: alert) |
| compliance (AgentKey) / compli (AgentId) | 合规巡检 | Agent5 合规 | "合规巡检" | /archive/compliance · AgentDef.path="/compliance" (错) | --t-compli (#5B7A48) · agents.ts 用 --color-brass-dim (旧 · 违 §7) | compliance_officer / admin (compli) | evaluation/agent5_compliance.yaml (agent: compliance · 与 AgentId 不符) |
| riskctrl (AgentKey) / riskctrl (AgentId) | 风控策略运营 | Agent2 风控 | "风控策略运营" | /archive/riskctrl · AgentDef.path="/riskctrl" (错) | --t-riskctrl (#6B4A6D) · agents.ts 用 --color-amber (旧 · 违 §7) | risk_manager / admin | evaluation/agent2_riskctrl.yaml (agent: riskctrl) |
