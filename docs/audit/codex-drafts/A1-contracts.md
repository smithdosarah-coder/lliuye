## 1. `docs/contracts/workspace-state-protocol.md`

用途：定义 6 个 `/archive/[agent]` workspace 的前端最小状态机，禁止各 Agent 自建不兼容 gate。

Spec body v1：

本文件保留为红区契约；现有文件已存在，且 owner 标为主 CLI、修改走 RFC（`docs/contracts/workspace-state-protocol.md:6`）。Phase A 不应重写语义，只补齐到 6 Agent 可执行。

4 gate 模型必须固定为：

```ts
type WorkspaceGateState<TSession, TCandidateId = string> = {
  started: boolean;
  selectedSession: string;
  liveData: TSession | null;
  selectedCandidate: TCandidateId | null;
};
```

语义：

| gate | 初始值 | 谁写 | 读者 | 约束 |
|---|---:|---|---|---|
| `started` | `false` | query submit / upload / history select / demo select | workspace root | `false` 时只显示 hero/query/empty，不渲染业务结果 |
| `selectedSession` | first mock session id | history select / live done | `sessionData` selector | 只表示当前基准 session id，不塞 live payload |
| `liveData` | `null` | SSE `done` normalize 后 | `sessionData` selector | live 真数据必须整体转为 AgentSession shape |
| `selectedCandidate` | `null` | card click / drawer close | drawer | drawer 状态只在 root 持有，panel 内不得自管候选状态 |

参考现有协议的 seed 代码：`started`、`selectedSession`、`liveData`、`selectedCandidate` 已在 `docs/contracts/workspace-state-protocol.md:37-52` 明确；`sessionData = liveData ?? MOCK_SESSIONS.find(...)` 在 `docs/contracts/workspace-state-protocol.md:58-59`。

Agent session shape extension：

```ts
type AgentSessionBase = {
  id: string;
  agent_id: AgentId;
  title: string;
  created_at: string;
  source: "mock" | "live" | "demo";
  input_summary: string;
  status: "ready" | "running" | "done" | "error";
  evidence: EvidenceRef[];
  artifacts?: ArtifactRef[];
};

type AgentSession<TPanels, TCandidate> = AgentSessionBase & {
  panels: TPanels;
  candidates?: TCandidate[];
  handoff?: HandoffPreview[];
  eval_trace?: {
    baseline: string;
    evidence_rate?: number;
    tool_success_rate?: number;
  };
};
```

现状漂移必须作为验收用例：5 个 workspace 缺 gate，`AlertWorkspace.tsx:77-106`、`ComplianceWorkspace.tsx:83-107`、`RiskctrlWorkspace.tsx:98-122` 只到 `started`；`CreditWorkspace.tsx:89-116` 缺 `selectedSession/selectedCandidate`；`ReportWorkspace.tsx:73` 用 `livePayload` 而非 `liveData`（`docs/audit/conflict-register-v1.md:58-62`）。前端 SSE 客户端也必须统一走 `streamSse`，因为 `_live.ts` 已提供 `streamSse`（`web/src/lib/api/_live.ts:76`），但 Channel/Credit/Report 仍有内联 reader（`docs/audit/conflict-register-v1.md:72-74`）。

Open question：`AgentSessionBase.source` 是否允许 `"demo"`，还是 demo 必须归为 `"mock"` 并用 `training_mode: true` 标识？

## 2. `docs/contracts/agent-naming-ssot.md`

用途：给 6 Agent 建唯一命名单表，作为 route、RBAC、颜色、eval baseline 的检查源。

Spec body v1：

单表列固定为 8 列，顺序不可变；此要求来自 `RESET_MASTER_PLAN.md:62` 和 `docs/reset/phase-a-charter.md:18`。

v1 draft 默认采用 `compli` 作为 Agent5 `agent_id`，因为后端 RBAC 与 store 当前已用 `compli`：`auth_service/rbac.py:42`、`web/src/lib/store/types.ts:13`、`web/src/lib/store/auth-store.ts:36-40`。但这是 proposal，不替代 PM 拍板。

| agent_id | 中文 | 业务名 | UI brand | route | 色彩 token | RBAC role | eval baseline |
|---|---|---|---|---|---|---|---|
| `channel` | 全渠道获客 | Agent1 获客 | 全渠道获客 | `/archive/channel` | `--t-channel` | `rm`, `admin` | `evaluation/agent1_channel.yaml` |
| `riskctrl` | 风控策略运营 | Agent2 风控 | 风控策略运营 | `/archive/riskctrl` | `--t-riskctrl` | `risk_manager`, `admin` | `evaluation/agent2_riskctrl.yaml` |
| `credit` | 授信决策辅助 | Agent3 授信 | 授信决策辅助 | `/archive/credit` | `--t-credit` | `rm`, `credit_officer`, `risk_manager`, `admin` | `evaluation/agent3_credit.yaml` |
| `alert` | 贷中风险预警 | Agent4 预警 | 贷中风险预警 | `/archive/alert` | `--t-alert` | `rm`, `credit_officer`, `compliance_officer`, `risk_manager`, `admin` | `evaluation/agent4_alert.yaml` |
| `compli` | 合规巡检 | Agent5 合规 | 合规巡检 | `/archive/compli` | `--t-compli` | `compliance_officer`, `admin` | `evaluation/agent5_compliance.yaml` |
| `report` | 信贷报告助手 | Agent6 报告 | 信贷报告助手 | `/archive/report` | `--t-report` | `rm`, `credit_officer`, `compliance_officer`, `risk_manager`, `admin` | `evaluation/agent6_report.yaml` |

Consumers must not invent aliases. `web/src/lib/auth/agent-id.ts:11-17` is explicitly a temporary compatibility shim because it maps `compliance` to `compli`. `web/src/lib/agents.ts:14-20` currently defines UI `AgentKey` with `"compliance"` while store `AgentId` uses `"compli"` at `web/src/lib/store/types.ts:8-14`; that split is the primary bug.

Routes must be canonical `/archive/<agent_id>` only. Current `web/src/lib/agents.ts:45/58/73/86/99/112` uses `/report`, `/channel`, `/credit`, `/riskctrl`, `/alert`, `/compliance`, conflicting with CLAUDE canon `/archive/[agent]` at `CLAUDE.md:126-129`.

Colors must use `CLAUDE.md:132` tokens only. Current legacy tokens at `web/src/lib/agents.ts:47/60/75/88/101/114` violate the same red line.

Open question：Cat 8 单一 id 最终选 `compliance` 还是 `compli`？若选 `compliance`，本表 Agent5 route 改 `/archive/compliance`，RBAC/store/backend 全量迁移。

## 3. `docs/contracts/sse-envelope.md`

用途：统一 6 Agent 后端 SSE event 名和 `done` payload，让前端只消费一种 envelope。

Spec body v1：

所有 `/api/<agent>/.../run` 或 live scan endpoint 必须输出：

```ts
type SseEnvelope<T = unknown> = {
  event: "stage" | "delta" | "artifact" | "done" | "error";
  agent_id: AgentId;
  session_id: string;
  run_id: string;
  ts: string;
  payload: T;
};
```

Event 规范：

| event | payload 必填 | 说明 |
|---|---|---|
| `stage` | `{ stage, status, progress, message? }` | 阶段开始/完成；`status` only `running/done/skipped` |
| `delta` | `{ target, patch }` | 可选，用于流式文本/局部 panel |
| `artifact` | `{ kind, name, url, mime? }` | Word/XLSX/PDF/export 产生时发 |
| `done` | `DonePayload` | 唯一 hydrate 信号 |
| `error` | `{ stage?, code, message, retryable }` | 失败也必须带 `session_id/run_id` |

`DonePayload` 共形：

```ts
type DonePayload = {
  session: AgentSession<any, any>;
  summary: {
    title: string;
    hero: string;
    status: "done" | "partial" | "error";
  };
  panels: Record<string, unknown>;
  candidates?: unknown[];
  handoff?: HandoffPreview[];
  artifacts?: ArtifactRef[];
  metrics?: Record<string, number | string | boolean>;
  evidence: EvidenceRef[];
  warnings?: string[];
};
```

禁止 `done` 空 payload。当前 drift：`agent_alert/api.py:112`、`agent_compliance/api.py:121` 都 yield `{"event":"done"}`；`agent_credit/api.py:387` mock 路 done 空，live 路 `agent_credit/api.py:465` 也空；Channel done 只含 candidates/metrics/data_source，缺 radar/signals/funnel（`agent_channel/realtime_stream.py:137-139`、`:229`）；Report 注释声称 done 有 `session_id/report_docx_url/...`（`agent_report/api.py:17-19`），实现又包装 `payload`（`agent_report/api.py:230-237`），需要改为同一 envelope。

前端 reader 只接受 `event:` framing，不接受裸 JSON line；已有 parser 在 `web/src/lib/api/_live.ts:127` 识别 `event: `，应成为唯一客户端入口。

Open question：`delta` 是否 Phase A 必须实现，还是仅保留事件名但 A2 helper 不暴露？

## 4. `docs/contracts/llm-prompt-contract.md`

用途：统一 6 Agent 的 system prompt 结构，防止角色、证据、工具和评估钩子各写一套。

Spec body v1：

所有 agent prompt 必须由 `shared/prompts/contract.py` 生成，不允许业务代码 inline 大段 system prompt。当前冲突：`section_generator.py:36-211` 有三阶段 Evidence-First inline prompt；`prompts.py:42-60` 另有信贷分析师角色；Agent1/4/2/5/3 各自 prompt 缺统一证据条款（`docs/audit/conflict-register-v1.md:111-117`）。

模板固定 8 段，顺序不可变：

```md
<section id="safety">
禁止编造事实、政策、数字、样本量；无证据输出“未能自动填写”。
</section>

<section id="evidence-first">
先列 evidence set，再生成结论，再自审。每个数字/判断/建议必须回指 evidence_id。
</section>

<section id="agent-role">
agent_id、中文角色、业务边界来自 agent-naming-ssot；不得写“策略经理”等漂移角色。
</section>

<section id="tool-use">
确定性计算走 Python/规则/检索工具；LLM 只做概率性分析、解释、话术、政策解读。
</section>

<section id="output-schema">
输出必须匹配调用方 JSON schema；未知字段不得自由扩展。
</section>

<section id="self-check">
交付前检查：证据缺失、数字可计算性、越权建议、schema 合法性。
</section>

<section id="few-shot">
仅注入通过 evaluation 收集的 few-shot；样例必须标来源与适用 agent。
</section>

<section id="evaluation-hook">
输出 trace_id、evidence_rate 所需字段，供 evaluation baseline 复跑。
</section>
```

硬约束来自 CLAUDE：确定性计算不能交给 LLM（`CLAUDE.md:20-27`）；Evidence-First 三阶段是全局协议（`CLAUDE.md:42-44`）；评估先跑 baseline 再改代码（`CLAUDE.md:90-108`）；few-shot 来源是 feedback 优化（`CLAUDE.md:110-117`）。

Agent role 必须引用 `agent-naming-ssot.md`。当前 `api_server.py:376` 写 “辅助策略经理写 DSL”，但 root 角色是银行客户经理/审贷员/合规官/风险经理（`CLAUDE.md:5`），且用户表只有 `risk_manager`（`auth_service/users.py:48-49`）。

Open question：prompt contract 是否允许 Agent6 保留 v16 三阶段专用措辞，还是全部映射为同一 8 段模板后只放 agent-specific appendix？

## 5. `docs/arch/instruction-source-of-truth.md`

用途：定义 reset 期间所有指令来源的优先级，避免 CLAUDE、onboarding、contracts、decisions-log 互相覆盖。

Spec body v1：

优先级从高到低：

1. `docs/contracts/*.md` 和 `docs/arch/instruction-source-of-truth.md`
2. root `CLAUDE.md`
3. scoped child instruction files, e.g. package/local `CLAUDE.md`
4. worker onboarding docs, e.g. `docs/onboarding/*.md`
5. `docs/handoff/decisions-log.md`

解释：

Contracts 是接口事实源；A1 本身就是产出 5 份契约（`docs/reset/phase-a-charter.md:46-56`）。Root `CLAUDE.md` 是工程行为和产品北极星，包含 6 Agent 边界、Evidence-First、IA canon、功能色、部署规则（`CLAUDE.md:33-38`、`:42-44`、`:126-132`、`:221-222`）。Onboarding 只约束 worker 执行，不得覆盖 contracts。Decisions-log 记录 PM 决策，但 active decision 必须回写 root `CLAUDE.md` 才完成；这个机制已写在 `RESET_MASTER_PLAN.md:61`，最近决策读取入口在 `CLAUDE.md:254`。

冲突处理：

| 情况 | 处理 |
|---|---|
| contract vs code | code 改到 contract，除非先走 RFC 改 contract |
| contract vs CLAUDE | contract 胜，主 CLI 后续回写 CLAUDE |
| CLAUDE vs onboarding | CLAUDE 胜，onboarding 只能补任务细节 |
| decisions-log vs CLAUDE | decisions-log 先作为待回写证据；未回写前不得推翻 CLAUDE |
| reset 状态变化 | 同步 `docs/reset/state-snapshot.md`，因为 CLAUDE 要求任何 reset 迭代都更新（`CLAUDE.md:286-291`） |

现状需特别标注一个路径漂移：Phase A 硬线 #1 写 `docs/contracts/{..., instruction-source-of-truth}.md`（`docs/reset/phase-a-charter.md:11`），但 worker-A1 细则写 `docs/arch/instruction-source-of-truth.md`（`docs/reset/phase-a-charter.md:56`），本 draft 按用户指定落 `docs/arch/...`。

Open question：是否同时保留 `docs/contracts/instruction-source-of-truth.md` stub，内容 redirect 到 `docs/arch/...`，以满足硬线 #1 的路径 lint？

## Dissent Appendix

我可能会和并行 worker 分歧在三点。第一，Agent5 单一 id 我倾向 v1 先用 `compli`，因为 RBAC/backend/store 已经一致；另一个合理方案是选 `compliance`，语义更完整且贴合现有 evaluation 文件。第二，SSE envelope 我把 `done.payload.session` 作为唯一 hydrate 源；worker 可能会保留各 Agent 顶层业务字段以减少迁移成本，但这会继续放大前端分支。第三，instruction SSOT 我把 decisions-log 放最低，只允许它作为“待回写事实”；worker 可能认为 PM 决策应高于 CLAUDE。我的理由是 master plan 已要求 active decision 回写 root，不回写就不算 done。