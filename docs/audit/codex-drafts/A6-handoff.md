## 1. Agent1.candidate_company → Agent6.upload_intent

### 改
Canonical 字段用 `match_score: integer 0..100`，`similarity` 只作为 legacy optional alias，写入 fixture 时不得同时作为主字段。原因：后端 `CandidateProfile` 已用 `match_score: int`，见 `agent_channel/candidate_profile.py:78`；前端 mock 仍用 `similarity: number`，见 `web/src/lib/mock/agent-channel-sessions.ts:129-145`，这是 Cat 5 裂缝。

**Schema**
```ts
type CandidateCompanyHandoff = {
  schema_version: "agent-handoff.v1";
  chain: "agent1.candidate_company_to_agent6.upload_intent";
  source_agent: "agent1";
  target_agent: "agent6";
  handoff_id: string;
  created_at: string; // ISO-8601
  session_id: string;

  candidate_company: {
    candidate_id: string;
    company_name: string;
    unified_credit_code?: string;
    industry?: string;
    region?: string;
    scale_text?: string;
    business_line: "corporate" | "small_business" | "retail";
    match_score: number; // int 0..100 required
    similarity?: number; // deprecated, 0..1, derived only
    signal_count: number;
    signal_types: string[];
    source_urls: string[];
    risk_tags: string[];
    recommended_products: string[];
    approved_amount_yuan?: number;
    pitch?: string;
    match_dimensions?: { dim_name: string; score: number; evidence_ref?: string }[];
  };

  upload_intent: {
    intent_type: "new_credit_report";
    preferred_template?: string;
    prefill_profile: Record<string, unknown>;
    material_requests: { kind: "pdf" | "docx" | "xlsx" | "img"; label: string; required: boolean }[];
    downstream_next: "agent6.report_json_to_agent3.decision_input";
  };
};
```

### 坚持
Agent1 只交“企业候选 + 推荐意图”，不伪造 Agent6 材料解析结论。Agent6 原始职责是上传企业材料并生成授信调查报告，见 `docs/audit/prd-evidence-frozen.md:46`。

### 对方弱点
若对方继续保留 `similarity ?? match_score` 双字段兼容，会把 Cat 5 掩盖到 UI 层；冲突已登记在 `docs/audit/conflict-register-v1.md:96-98`。

### 吸收对方
允许 1 个版本窗口接受 `similarity`，但存储 fixture 必须写 `match_score`，并标 `deprecated_aliases: ["similarity"]`。

### v2 final
Fixture: `data/mock/handoff/agent1_candidate_to_agent6_upload_intent.json`
```json
{
  "schema_version": "agent-handoff.v1",
  "chain": "agent1.candidate_company_to_agent6.upload_intent",
  "candidate_company": {
    "candidate_id": "c-h1",
    "company_name": "杭州智云工业软件",
    "match_score": 94,
    "signal_types": ["投融资", "招聘", "招投标"],
    "recommended_products": ["科创信用贷", "并购贷"]
  },
  "upload_intent": { "intent_type": "new_credit_report" }
}
```

现有漂移：`web/src/lib/mock/agent-channel-sessions.ts:132` 用 `similarity`；`agent_channel/candidate_profile.py:78` 用 `match_score`；`agent_channel/api.py:374-447` 已有 channel handoff，但目标注释仍写 Agent3，不符合本链应先进 Agent6。

---

## 2. Agent6.report_json → Agent3.decision_input

### 改
定义最小 ReportJSON，不直接照搬 ReportSession UI mock。Agent3 API 当前只要求 `report_json?: dict`，见 `agent_credit/api.py:265-281`；Agent6 done payload 有 `enterprise_profile / pending_questions / downstream_handoff`，见 `agent_report/api.py:218-235`。

**Schema**
```ts
type ReportJsonToDecisionInput = {
  schema_version: "agent-handoff.v1";
  chain: "agent6.report_json_to_agent3.decision_input";
  source_agent: "agent6";
  target_agent: "agent3";
  handoff_id: string;
  session_id: string;
  report_id: string;
  created_at: string;

  report_json: {
    report_schema_version: string; // e.g. "ReportJSON.v1"
    subject: {
      name: string;
      customer_code?: string;
      unified_credit_code?: string;
      business_line: "corporate" | "small_business" | "retail";
      industry?: string;
      region?: string;
    };
    application: {
      product?: string;
      amount_yuan: number;
      tenor_months?: number;
      purpose?: string;
    };
    enterprise_profile: Record<string, unknown>;
    sections: { id: string; title: string; content: string; evidence_refs?: string[] }[];
    facts: {
      financial_metrics?: Record<string, number | string>;
      legal_risk_tags?: string[];
      collateral?: Record<string, unknown>[];
      guarantors?: Record<string, unknown>[];
    };
    qc: { block: number; warn: number; info: number; unfilled?: number };
    pending_questions: { id: string; question: string; severity: "block" | "warn" | "info" }[];
    source_materials: { id: string; name: string; kind: "pdf" | "docx" | "xlsx" | "img"; parsed: boolean }[];
  };

  decision_input: {
    stage_tab: "corporate" | "small_business" | "retail";
    report_json: ReportJsonToDecisionInput["report_json"];
    materials?: Record<string, unknown>[];
    appetite_config?: Record<string, unknown>;
    mock: false;
  };
};
```

### 坚持
Agent3 消费的是 Agent6 产出的结构化报告，不是 demo preset。Original Intent 明确 Agent3 消费 ReportJSON，见 `docs/audit/prd-evidence-frozen.md:28`；当前缺口是 `/handoff/demo/{segment}` 仍是 stub，见 `docs/audit/prd-evidence-frozen.md:64-65`。

### 对方弱点
若对方把 `web/src/lib/mock/agent-report-session.ts:133-148` 的 UI `ReportSession` 当 ReportJSON，会把 preview/timeline/conversation 混进风控决策输入，污染边界。

### 吸收对方
可吸收 UI mock 的 `materials`、`coverage`、`qcCounts` 概念；但落到 contract 时改名为 `source_materials`、`qc`。

### v2 final
Fixture: `data/mock/handoff/agent6_report_json_to_agent3_decision_input.json`
```json
{
  "chain": "agent6.report_json_to_agent3.decision_input",
  "report_json": {
    "report_schema_version": "ReportJSON.v1",
    "subject": { "name": "福建惠民商贸有限公司", "business_line": "corporate" },
    "application": { "product": "对公经营贷", "amount_yuan": 5600000 },
    "sections": [{ "id": "business", "title": "经营情况", "content": "..." }],
    "qc": { "block": 2, "warn": 2, "info": 1 }
  },
  "decision_input": { "stage_tab": "corporate", "mock": false }
}
```

现有漂移：`agent_credit/api.py:222-249` 仍读 demo handoff；`agent_credit/api.py:487` 写明 `report_json/preset_name` 双源 fallback；north-star 要真 handoff data flow，见 `docs/reset/north-star.md:83-88`。

---

## 3. Agent3.decision → Agent4.client_pool_signal

### 改
Agent3 决策结果必须转成“贷后客户池信号”，不是完整审批建议书。Agent3 mock advice 关键字段在 `agent_credit/api.py:365-381`：`decision / approved_amount / approved_term_months / interest_rate / risk_grade / composite_score / conditions`。Agent4 队列消费形态是 `customer / tier / reason / updated`，见 `web/src/lib/mock/agent-alert-session.ts:107-114`。

**Schema**
```ts
type DecisionToClientPoolSignal = {
  schema_version: "agent-handoff.v1";
  chain: "agent3.decision_to_agent4.client_pool_signal";
  source_agent: "agent3";
  target_agent: "agent4";
  handoff_id: string;
  decision_id: string;
  created_at: string;

  decision: {
    subject_name: string;
    customer_code?: string;
    decision: "approved" | "approved_cut" | "conditional_approved" | "rejected" | "manual_review";
    approved_amount_yuan?: number;
    approved_term_months?: number;
    interest_rate?: number;
    rate_benchmark?: string;
    risk_grade?: string;
    composite_score?: number;
    conditions: string[];
    red_lines: { code: string; severity: "high" | "medium" | "low"; waived: boolean }[];
  };

  client_pool_signal: {
    client_id: string;
    customer: string;
    pool_action: "add_to_monitoring" | "update_monitoring" | "do_not_add";
    tier: "red" | "yellow" | "green";
    reason: string;
    signal_sources: ("credit_decision" | "red_line" | "condition" | "manual")[];
    monitor_start_at: string;
    review_due_at?: string;
    linked_decision_id: string;
  };
};
```

### 坚持
只要授信获批或有条件批准，就应至少进入 Agent4 green/yellow 池；拒绝或红线高危进入 red/不新增监控由策略决定。north-star 闭环包含“模拟放款 → Agent4 在贷监控”，见 `docs/reset/north-star.md:34-42`。

### 对方弱点
若对方直接把 Agent3 `advice` 原样塞给 Agent4，会导致 Agent4 同时理解 `risk_grade`、`tier`、`level`，复现 Cat 5 的三方命名问题。

### 吸收对方
保留 Agent3 的 `risk_grade` 作为 evidence，不作为 Agent4 主分级；Agent4 主字段统一 `tier`。

### v2 final
Fixture: `data/mock/handoff/agent3_decision_to_agent4_client_pool_signal.json`
```json
{
  "chain": "agent3.decision_to_agent4.client_pool_signal",
  "decision": {
    "subject_name": "福建惠民商贸有限公司",
    "decision": "conditional_approved",
    "approved_amount_yuan": 3000000,
    "risk_grade": "B",
    "conditions": ["补充关联交易审计说明"]
  },
  "client_pool_signal": {
    "client_id": "CR-2026-04-21-0037",
    "customer": "福建惠民商贸有限公司",
    "pool_action": "add_to_monitoring",
    "tier": "yellow",
    "reason": "有条件批准 + 关联交易补充条件",
    "signal_sources": ["credit_decision", "condition"]
  }
}
```

现有漂移：Agent4 export 兼容 `risk_level / level / tier`，见 `agent_alert/word_export.py:22`、`agent_alert/word_export.py:321`；前端主字段是 `tier`，见 `web/src/lib/mock/agent-alert-session.ts:111`。

---

## 4. Agent5.policy_event → Agent4/Agent6

### 改
政策事件拆成两个 target view：给 Agent4 的“监控规则变更信号”，给 Agent6 的“报告模板/披露要求变更信号”。Agent5 API 当前请求只有 `policy_doc / business_docs / policy_meta / force_mock`，见 `agent_compliance/api.py:93-98`；PRD 原意是政策发布事件驱动，见 `docs/audit/prd-evidence-frozen.md:40`。

**Schema**
```ts
type PolicyEventHandoff = {
  schema_version: "agent-handoff.v1";
  chain: "agent5.policy_event_to_agent4_agent6";
  source_agent: "agent5";
  target_agents: ["agent4", "agent6"];
  event_id: string;
  created_at: string;

  policy_event: {
    title: string;
    policy_code?: string;
    issuer?: string;
    source_url?: string;
    published_at?: string;
    effective_at?: string;
    policy_doc: string;
    policy_meta?: Record<string, unknown>;
    severity: "critical" | "major" | "minor" | "watch";
    affected_products: string[];
    affected_segments: ("corporate" | "small_business" | "retail")[];
    extracted_rules: { rule_id: string; clause_ref: string; requirement: string; severity: string }[];
  };

  agent4_rule_signal: {
    action: "create_rule" | "update_rule" | "disable_rule";
    rule_version: string;
    watchlist_reason: string;
    tier_hint: "red" | "yellow" | "green";
    affected_pool_filter?: Record<string, unknown>;
  };

  agent6_template_signal: {
    action: "update_template" | "add_disclosure" | "request_rewrite";
    required_sections: string[];
    disclosure_text: string;
    applies_to_templates: string[];
  };
};
```

### 坚持
Agent5 不能只做手工上传扫描；contract 要预留 `published_at/effective_at/source_url`，否则无法恢复“政策发布事件驱动”。

### 对方弱点
若对方只对齐当前 `policy_scan` body，会固化“手动上传触发”的偏差；缺口已在 `docs/audit/prd-evidence-frozen.md:74-75`。

### 吸收对方
`policy_doc` 和 `policy_meta` 直接沿用当前 API 字段，降低落地成本。

### v2 final
Fixture: `data/mock/handoff/agent5_policy_event_to_agent4_agent6.json`
```json
{
  "chain": "agent5.policy_event_to_agent4_agent6",
  "policy_event": {
    "title": "消费金融公司管理办法修订版",
    "policy_code": "银保监发〔2026〕18号",
    "severity": "major",
    "affected_products": ["消费贷"],
    "extracted_rules": [{ "rule_id": "r-001", "clause_ref": "第十二条", "requirement": "加强用途核验", "severity": "major" }]
  },
  "agent4_rule_signal": { "action": "update_rule", "rule_version": "2026.04", "tier_hint": "yellow" },
  "agent6_template_signal": { "action": "add_disclosure", "required_sections": ["合规审查"], "applies_to_templates": ["retail"] }
}
```

现有漂移：`agent_compliance/api.py:131-147` 已能 SSE 扫描并持久化，但没有事件订阅入口；`web/src/lib/mock/agent-compliance-session.ts:18-21` 仍是 policy title/code UI query。

---

## 5. Export Contract 共形 Spec

### 改
6 Agent 统一 export envelope：按钮必须 wire 真 endpoint；失败必须 banner；不允许纯 UI dead button 或 console-only。Cat 13 证据：Riskctrl 后端无 export 但前端调用，见 `docs/audit/conflict-register-v1.md:208`；Channel `OUTPUT_ACTIONS` dead button，见 `docs/audit/conflict-register-v1.md:209`；Credit 失败只 console，见 `docs/audit/conflict-register-v1.md:210`。

**Endpoint matrix**
| Agent | Required endpoints | Current evidence |
|---|---|---|
| Agent1 Channel | `POST /api/channel/export_xlsx`, `POST /api/channel/export_docx`, optional `export_pdf` returns 501 | implemented `agent_channel/api.py:225-307`; handoff `agent_channel/api.py:390-447` |
| Agent2 Riskctrl | `POST /api/riskctrl/export_pdf`, `POST /api/riskctrl/export_docx`, optional `export_xlsx` for backtest rows | missing; only dsl/backtest at `agent_riskctrl/api.py:97`, `agent_riskctrl/api.py:185` |
| Agent3 Credit | `POST /api/credit/export_docx`, optional `export_pdf` mirror, optional `export_xlsx` decision facts | implemented `agent_credit/api.py:511-528` |
| Agent4 Alert | `POST /api/alert/export_docx`, `POST /api/alert/export_xlsx`, optional case `export_pdf` | docx implemented `agent_alert/api.py:160-165` |
| Agent5 Compliance | `POST /api/compliance/export_docx`, `POST /api/compliance/export_xlsx`, `POST /api/compliance/export_pdf` | docx implemented `agent_compliance/api.py:255-265`; spec already asks xlsx/pdf at `docs/contracts/agent-compli-spec.md:113-115` |
| Agent6 Report | `POST /api/report/export_docx`, optional `export_pdf`, optional `export_xlsx` field audit | docx implemented `agent_report/api.py:805-822` |

**Common request**
```ts
type ExportRequest = {
  session_id?: string;
  artifact_id?: string;
  format: "docx" | "xlsx" | "pdf";
  payload?: Record<string, unknown>; // fallback direct payload
  title?: string;
};
```

**Common response**
- Success: binary attachment with `Content-Disposition`, `Content-Type`, and `X-Agent-Export-Type`.
- Missing format: HTTP `501 { error: { code: "EXPORT_NOT_IMPLEMENTED", endpoint, format } }`.
- Validation: HTTP `400 { error: { code: "VALIDATION_FAILED", details } }`.
- Runtime failure: HTTP `500 { error: { code: "EXPORT_FAILED", message } }`.

### 坚持
Button contract: every visible export button has `onClick`, loading/disabled state, and explicit error UI. Shared fallback rule follows `docs/contracts/live-fallback-banner-spec.md:16-32`; no silent mock.

### 对方弱点
A pure endpoint table is insufficient; Cat 13 is half backend, half UI wire. `web/src/app/archive/channel/_components/ChannelWorkspace.tsx:1694-1722` shows buttons can exist without action.

### 吸收对方
Permit “not implemented” endpoints in Phase A if they return 501 and banner, rather than hiding buttons or letting 404 leak.

### v2 final
Acceptance:
- `rg "export_docx|export_xlsx|export_pdf" agent_* web/src/lib/api web/src/app/archive` shows every visible action has endpoint/client/handler.
- Failed live export displays banner per `web/src/lib/api/_live.ts:9` and message shape at `web/src/lib/api/_live.ts:183`.
- No `/today/*` spec in this contract; PM pushed RM workbench rewrite to Phase B-3, see `docs/audit/conflict-register-v1.md:317-321`.

## 待 PM 拍板 Open Questions
1. Cat 5 final naming: `match_score` 是否正式保留为 canonical，`similarity` 是否在 one-release 后删除。
2. Agent2 export minimum: Phase A 是否要求真实 PDF，还是 501 + banner 即可过硬线。
3. Agent4 `tier` 是否全局定为 red/yellow/green，禁止 `risk_level/level/grade` 进入新 contract。
4. Agent6 ReportJSON version 是否用 `ReportJSON.v1` 重开，避免继承 mock 文案里的 `v7.23`。
5. Export PDF 是否全部 Agent 都要 endpoint stub，还是只对 Agent2/5 强制。

## Dissent Appendix
我不同意把 A6 扩成 `/today` workbench 设计。north-star 的确要求 `/today` 改成 RM workbench，见 `docs/reset/north-star.md:83-88`，但 PM 已在 register 中拍板推 Phase B-3，见 `docs/audit/conflict-register-v1.md:317-321`。A6 此轮应把“链路数据能交接”定义清楚，否则会再次把产品形态问题和 schema 问题搅在一起。

我也不同意继续用 UI mock 类型当后端 contract。mock 是展示形态，包含 conversation、timeline、preview；handoff 是跨 Agent 最小业务事实。Contract 应先收敛字段，再让 UI 适配。