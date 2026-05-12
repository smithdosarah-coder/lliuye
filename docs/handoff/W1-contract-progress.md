# W1-contract Progress (append-only)

> 接力 sub-agent 必读 · main session 监控源 · sub-agent checkpoint 每次 append 一段

<!-- 第一棒 sub-agent 在此 append 第一段 -->

## 2026-05-11 23:30 · checkpoint 2/14 (第 2 棒) · claude-W1-contract

### What I did (sub-agent · 30-45 min slot)
- 读 v3 §2.1 (LiuyeChatEvent line 34-90 + TurnErrorPayload + PermissionRequestEventPayload verbatim) + §2.2 (Artifact + ArtifactPatch line 111-156)
- 写 `shared/contracts/liuye/schemas/artifact.schema.json` (Artifact root + ArtifactPatch nested via `definitions/ArtifactPatch`)
- 写 `shared/contracts/liuye/schemas/liuye_chat_event.schema.json` (envelope + TurnErrorPayload + PermissionRequestEventPayload via `definitions`)
- 跑 draft-07 metaschema 验证 (Python jsonschema 4.26.0 替代 ajv-cli · 等价 metaschema check) · 2 schema 均 OK
- 跑 runtime sanity (13 check · valid 样本 + 6 reject 路径) · 全 PASS

### 关键决策
- **ArtifactPatch 用 `definitions/ArtifactPatch`** (不拆独立 schema 文件): brief 14 文件清单只列 5 schema · ArtifactPatch 是 Artifact 的内嵌协议 (v3 §2.2 一起出现) · 不单立 patch.schema.json · codegen `json-schema-to-typescript` 会生成 nested `ArtifactPatch` interface
- **`liuye_chat_event.schema.json` oneOf 分 3 支**: (a) turn.error → 必须 TurnErrorPayload (b) permission.request → 必须 PermissionRequestEventPayload (c) 其他 9 event payload 暂开放 (留 W1 后续 schema iteration 细化 artifact.patch/evidence.attached/tool.progress payload · 否则现在锁死会回头改 6 处)
- **`Artifact.snapshot` 用 open schema (无 type)**: per-type 校验 (CreditDecisionV1 / ReportDraftV1 / ChannelSearchV1) 在 inputSchemas.ts (Zod) 那一棒做 · JSON Schema 这层只校 5 type enum
- **TurnErrorPayload 必填 7 字段**: 严格抄 v3 §2.1 line 56-67 (`code` / `message` / `retryable` / `human_hint` / `trace_id` / `turn_id` / `seq`) + 3 optional (`tool_call_id` / `retry_after_ms` / `fallback_available`)
- **PermissionRequestEventPayload 必填 4 字段**: 严格抄 v3 §2.1 line 69-82 (`request_id` / `risk_tier` / `action` / `idempotency_key`) + 7 optional · risk_tier 3 enum 锁死 · scope 3 enum 锁死

### Hidden gotcha 发现
- v3 §2.1 line 53 `payload: unknown` 在 TS 是 "any but typed" · JSON Schema 里没法 verbatim 翻 · 必须用 `{}` (open object) 或 oneOf 按 event 分支. 我选 oneOf 分 3 支 · 未来补 9 event payload 细节时只动 oneOf 第 3 支 + 加 4-7 个新分支 · 不会破现有契约
- `Artifact.snapshot: unknown` 同理 · open schema · 等同 `{}`
- `chunk_total` 缺失视为非分片 (brief §4.2 + v3 §2.2 verbatim) · 我没用 dependencies/dependentRequired 互锁 chunk_index↔chunk_total · 因为 "缺失视非分片" 是 legacy 兼容要求 · 严格依赖会破老 patch · 留待 W1 D2+ patch 处理逻辑层校 (verify-contracts.ts 之外的 runtime 验)

### Next 棒 (第 3 棒) 预计交付
- 3 schema: `tool_call.schema.json` (含 ToolCall 8-status enum + invoker_id/reviewer_id + ProgressMessage nested) + `kb_doc.schema.json` (tier 1-4 + pipl_region cn/overseas) + `evidence_ref.schema.json` (freshness fresh/critical/expired + decision_id?)
- 跑同款 ajv-py validate · 累计 5 schema 通过 metaschema + runtime sanity
- 估 30-45 min · ToolCall 字段最多 (12 字段) · KBDoc/EvidenceRef 较少

### Blocker
- none

### File checklist 状态
- [x] shared/contracts/liuye/schemas/artifact.schema.json (2/14)
- [x] shared/contracts/liuye/schemas/liuye_chat_event.schema.json (2/14)
- [ ] shared/contracts/liuye/schemas/tool_call.schema.json (第 3 棒)
- [ ] shared/contracts/liuye/schemas/kb_doc.schema.json (第 3 棒)
- [ ] shared/contracts/liuye/schemas/evidence_ref.schema.json (第 3 棒)
- [ ] shared/contracts/liuye/inputSchemas.ts (第 4 棒 · Zod 3 字段)
- [ ] 5 fixture/*.json (第 5 棒)
- [ ] contracts.lock.json (第 6 棒 · schema_hash 计算)
- [ ] scripts/sync-contracts.ts (W0 已存 · 后续棒只扩)
- [ ] scripts/verify-contracts.ts (W0 已存 · 后续棒只扩)

### ELAPSED min: 35
### Commit SHA: 539c3e3

## 2026-05-12 00:15 · checkpoint 3/14 (第 3 棒) · claude-W1-contract

### What I did (sub-agent · 30-45 min slot)
- 读 v3 §2.3 (ToolCall + ToolDefinition + ProgressMessage line 157-218 verbatim) + §2.4 (KBDoc line 224-235 + EvidenceRef line 237-247 verbatim)
- 读 shared/data_tiers.py (DataTier 4 + UNKNOWN 共 5 str enum · 域名 32 map · 推荐校验) + shared/evidence_freshness.py (ClaimType 13 · FRESHNESS_SLA_DAYS · classify_freshness 5 band) + shared/recommendation_schema.py (RecommendationReason 8 字段 pydantic)
- 写 `shared/contracts/liuye/schemas/tool_call.schema.json` (ToolCall root 14 字段 + ProgressMessage nested via `definitions/ProgressMessage`)
- 写 `shared/contracts/liuye/schemas/kb_doc.schema.json` (KBDoc 10 字段 · tier 1-4 int · pipl_region cn/overseas · content_hash sha256 64-hex pattern)
- 写 `shared/contracts/liuye/schemas/evidence_ref.schema.json` (EvidenceRef 14 字段 · freshness 3 enum · data_tier 1-4 · decision_id? + evidence_date + retrieved_at + source_url + source_tier 可选)
- 跑 draft-07 metaschema (5/5 累计 OK) + 18 runtime check (3 valid full/minimal + 15 reject 路径 · status 8 / ProgressMessage 5 / agent 6 / percent 0-100 / additionalProperties / tier 1-4 / pipl_region / content_hash hex / freshness 3 / data_tier / source_tier / required) · 全 PASS

### 关键决策
- **ToolCall.status 8 enum 严格按 v3 §2.3 line 179-181 verbatim**: queued / connecting / running / streaming / idle_timeout / completed / failed / aborted · 必修 #9 验证: 实际 v3 spec 列的就是 8 态 · NOT 9 NOT 7
- **ProgressMessage.status 是另一个 5 enum** (pending / running / done / warning / error · v3 §2.3 line 207 verbatim) · 与 ToolCall.status 8 enum **不重叠** · 我在 description 显式说明这是 stage-level lifecycle · NOT tool-level · 验证用例覆盖了 "ProgressMessage 用 'completed' = reject" 路径
- **ProgressMessage 用 `definitions/ProgressMessage` 内嵌**: 与 artifact.schema 的 `definitions/ArtifactPatch` 同模式 · 14 文件清单只列 5 schema · ProgressMessage 是 ToolCall 的内嵌协议 (v3 §2.3 一起出现) · codegen 出 nested interface
- **invoker_id 严格 required** (per v3 §2.3 line 168 `invoker_id: string;` 无 `?`) · reviewer_id optional · 系统触发的 Managed job 用 `system:<job_kind>` 占位 (description 注明)
- **percent 用 integer 0-100** (matrix §3 Q1 决议) · 不用 number 也不用 float · `minimum: 0` + `maximum: 100`
- **tool_call.error 用 inline object** (不拆 definitions): 复用 TurnErrorPayload 子集 (code/message/trace_id 必填) · 不强约束跟 TurnErrorPayload 一致 (ToolCall.error 可能比 TurnErrorPayload 少字段)
- **KBDoc.tier 用 int 1-4** (v3 §2.4 line 228 verbatim `tier: 1 | 2 | 3 | 4`) · NOT str enum · description 显式注明 SSOT 映射 (1↔internal_authoritative · 2↔government · 3↔industry · 4↔public_web) 由 consumer adapter 做 · 不在 schema 层强约束 (避免 reverse-lookup 表泄漏到契约)
- **content_hash 用 regex `^[a-fA-F0-9]{64}$`** · sha256 锁定 64 hex (v3 §2.4 line 233 `content_hash: string; // sha256`) · 不是普通 minLength 1 · 反向验证 `deadbeef` 短串 reject 路径覆盖
- **EvidenceRef.freshness 3 enum vs evidence_freshness.py 5 band**: 这是最大 hidden gotcha (见下) · 契约层锁 fresh/critical/expired (v3 §2.4 verbatim) · UI 层用 fresh/recent/aging/stale/very_stale · 我在 description 显式 spell out 5→3 mapping (fresh→fresh · recent→fresh · aging→critical · stale→critical · very_stale→expired) 留给 consumer adapter
- **EvidenceRef.decision_id? optional** + `related_artifact_ids[] required`: brief 明确 "仅 cross-decision link 时填" · description 注明 normal in-artifact backing 用 related_artifact_ids · matrix case map 留 ratify · 不在 schema 层做条件 required

### Hidden gotcha 发现 (3 个 · 关键提示下一棒)
1. **freshness 3 enum vs 5 band 严重不对齐**: v3 §2.4 line 242 契约层 freshness 只有 `fresh|critical|expired` 3 个 · 但 `shared/evidence_freshness.classify_freshness()` 实际返 `fresh|recent|aging|stale|very_stale` 5 个 UI 标签 + 缺数据返 `unknown` · 这意味着 **runtime adapter 必须做 5→3 收敛**: fresh→fresh / recent→fresh (< 180d 全归 fresh · 不区分 < 30d) / aging→critical (< 365d) / stale→critical (< 730d) / very_stale→expired / unknown→expired · 下一棒写 Zod inputSchemas.ts 时要小心 · 我已在 schema description 留下完整 mapping 表 · 别让 frontend 直接把 5-band 灌进 EvidenceRef.freshness
2. **data_tier int 1-4 vs DataTier str enum 不对齐**: v3 §2.4 line 243 契约层 `data_tier: 1|2|3|4` 是 int · 但 `shared/data_tiers.DataTier` 是 str enum (`internal_authoritative|government|industry|public_web|unknown`) · DataTier.UNKNOWN (Tier 5) 不在契约里 · backend 序列化时要做 enum → int 转换 + UNKNOWN 单独处理 (默认按 Tier 4 还是 reject?) · 下一棒 inputSchemas.ts 用 Zod `.refine()` 验证 source_tier ↔ data_tier 一致性时要注意 · 我在 EvidenceRef.source_tier description 显式 spell out 4 映射 + unknown 单独
3. **ProgressMessage.status 5 enum 与 ToolCall.status 8 enum 不重叠 (但有重名 `running`)**: 都有 `running` · 容易代码层混淆 · 例: ProgressMessage 用 `completed` 是非法的 (它应该 emit `done`) · ToolCall 用 `done` 也是非法的 (它应该 emit `completed`) · 我在两处 description 显式 spell out 区别 · 写 fixture 时下一棒要把这俩 status 实例分别正确生成 · 不能复制粘贴

### Next 棒 (第 4 棒) 预计交付
- `shared/contracts/liuye/inputSchemas.ts` (Zod · v3 §2.7 line 311-339 verbatim 3 字段: CustomerNoSchema 14 digit + 校验位 · ProductEnumSchema 3 enum · TermMonthsSchema int 1-360 · ValidationMessages 中文 map)
- 1-2 fixture/*.json 预热 (e.g. fixtures/credit_decision.json + fixtures/channel_search.json · 用 ajv compile schema 验 fixture)
- 估 30-45 min · Zod 简单 (3 字段 + validate) · fixture 难度中等 (要把 5 schema 串起来出真实 sample)

### Blocker
- none

### File checklist 状态
- [x] shared/contracts/liuye/schemas/artifact.schema.json (5/14)
- [x] shared/contracts/liuye/schemas/liuye_chat_event.schema.json (5/14)
- [x] shared/contracts/liuye/schemas/tool_call.schema.json (5/14 · 第 3 棒)
- [x] shared/contracts/liuye/schemas/kb_doc.schema.json (5/14 · 第 3 棒)
- [x] shared/contracts/liuye/schemas/evidence_ref.schema.json (5/14 · 第 3 棒)
- [ ] shared/contracts/liuye/inputSchemas.ts (第 4 棒 · Zod 3 字段)
- [ ] 5 fixture/*.json (第 4-5 棒)
- [ ] contracts.lock.json (第 6 棒 · schema_hash 计算)
- [ ] scripts/sync-contracts.ts (W0 已存 · 后续棒只扩)
- [ ] scripts/verify-contracts.ts (W0 已存 · 后续棒只扩)

### ELAPSED min: 38
### Commit SHA: a1d58c4

## 2026-05-12 00:55 · checkpoint 8/14 (第 4 棒) · claude-W1-contract

### What I did (sub-agent · 30-45 min slot)
- 读 v3 §2.7 line 311-345 (Zod 3 字段 + ValidationMessages 中文 map verbatim) + §2.2 (Artifact + ArtifactPatch line 111-156)
- 读 `agent_credit/scoring_model_corporate.py:18-30` (CorporateScoringResult 4 维 + sub_scores/sub_details/industry_peer_gap) + `agent_credit/decision_graph.py:112-145` (DecisionGraph 7 node type + 6 edge type · 实做 verbatim)
- 读 `shared/recommendation_schema.py` (8 字段 schema · source_tier 5 str enum 用于 EvidenceRef.source_tier 对齐) + `shared/evidence_freshness.py:81-94` (FRESHNESS_SLA_DAYS 13 ClaimType · 用于 evidence_date 真实分层)
- 新仓 `npm install zod` (zod 4.4.3 装入 `credit_matrix_next/node_modules`) + 拿临时 tsc test dir 跑 `tsc --noEmit` 验 inputSchemas.ts 类型 · 0 error PASS
- 写 `shared/contracts/liuye/inputSchemas.ts` (Zod · 3 字段 + ValidationMessages 中文 map · v3 §2.7 verbatim · 不发明字段)
- 写 `shared/contracts/liuye/fixtures/credit_decision.json` (Artifact type=credit_decision · status=resolved · version=4 + 4 patches · snapshot 含 4 维评分 PASS B 级 + 7-node decision graph + 6 edge type 全覆盖 + ledger idempotency_key · verdict=PASS qc_score 9/9 · 中等难度脱敏 C34 通用设备制造业)
- 写 `shared/contracts/liuye/fixtures/evidence_ref.json` (5 entry array · freshness 3 enum 全覆盖 fresh×3 / critical×1 / expired×1 · data_tier int 1-4 全覆盖 1/2/3/4×2 · source_tier 4 种覆盖 government / industry / internal_authoritative / public_web · decision_id 2/5 填 3/5 不填 · evidence_date 跨过去 60-350d · 真实 URL 脱敏例 `annual-report.example.cn` / `industry-research.example.cn` / `internal://crm/...` / `news.example.com`)
- 跑 ajv validate (Python jsonschema 4.26.0 Draft7Validator) · 累计 5 schema metaschema 0 error + 2 fixture PASS (credit_decision vs artifact · 5 evidence_ref entries vs evidence_ref · 全 PASS)

### 关键决策
- **inputSchemas.ts 与 v3 §2.7 1:1 verbatim · 不补充不优化**: 即使 Zod 4 (4.4.3) 与 spec 写时 Zod 3 略有差异 · 测过 `z.enum([...], { message })` + `z.coerce.number().int(msg).min(min,msg).max(max,msg)` 在 Zod 4.4.3 下完全等价 · safeParse error.issues[0].message 返期望 code string · 不需调整
- **Zod 4 安装到新仓而非老仓**: brief 明确 "新仓 W0 T1 已装 typescript + tsx 但未装 zod" · 我 `cd credit_matrix_next && npm install zod` 装 4.4.3 (deps 自然 latest · root §3.6 PIPL 不涉及 Zod 网络调用 · 兼容 OK) · package.json 现含 `"zod": "^4.4.3"` (未 commit · 留 W0 main session 决定是否锁版本 + 一起 commit)
- **credit_decision.json 中等难度选择**: C34 通用设备制造业 (一般 PMI ~50-52 · 周期性中等) · 标的"沧澜精密机械有限公司" 完全脱敏 (沧澜 = 古词 · 非真实存续 · annualreport / qichacha 0 hit · 行业 4 维评分 72/65/78/70 = composite 72 · 风险等级 B · 决策"通过"含 5% reduction (申请 2800 万 → 批 2600 万) · 模拟真实审贷会"折扣放" 而非"全批" · 这是中等难度信号
- **decision_trace 节点选择**: 实做有 7 node type (feature/rule/rule_hit/peer_benchmark/peer_gap/score_dimension/decision) 我只 mock 7 节点 (各 1 个 · 不堆叠) · 真实场景一笔决策 30-80 节点 · fixture 不为复杂而复杂 (per CLAUDE.md 反结果导向第 5 原则 "环境边界 · 不替它做本该外搜的工作") · 6 edge type 全覆盖 (triggered / threshold_of / caused / evidenced_by / derived_from / compared_to·占 3 处)
- **ledger.idempotency_key 用 BE7 模式**: `credit:CORP_CREDIT:<subject_hash_16hex>:<ts_minute_truncated>` per `shared/decision_ledger/schema.py` LedgerEntry input_hash + decision_id 习惯 · subject_id_hash 16-hex 而非 plain (PII never plain · root §3.7.5 硬线)
- **evidence_ref 5 entry 分布**: fresh × 3 + critical × 1 + expired × 1 (合 brief "freshness 3 enum 各至少 1" 含 fresh 偏多) + data_tier 1/2/3/4 至少 1 evidence (1 × 1 / 2 × 1 / 3 × 1 / 4 × 2) + decision_id optional 2/5 填 (扣 brief "1-2 个填 1-2 个不填" — 注意 decision_id 是 cross-decision link · related_artifact_ids 是 in-artifact backing · 5 entry 中 4 个填 related_artifact_ids · 第 5 个 expired news 两者都不填 mock 出 "纯背景类 evidence" 形态)
- **evidence_date 选择跨度**: 60d / 100d / 250d / 200d / 350d 过去 · 60d/100d 落在所有 SLA fresh 区 · 250d 落 case_study fresh (730d SLA) · 200d 是 news 临界 critical (180d SLA 刚过 = critical) · 350d 是 news expired (远过 180d SLA = expired) · 完全合 v3 §2.4 contract 3 enum
- **source_url 脱敏 + 真实形态**: 4 种 URL 形态全覆盖 — `https://annual-report.example.cn/...` (政府/机构 cn TLD) · `https://industry-research.example.cn/...` (行业研究) · `internal://crm/case-study/...` (内部源伪 scheme · 与 recommendation_schema.source_url 一致) · `https://news.example.com/...` (公开 web) · 全合 EvidenceRef.source_url uri-reference 格式 + 合 root §3.5.1 第 6 原则 "脱敏再造"

### Hidden gotcha 发现 (3 个 · 关键提示下一棒)
1. **Zod 4 与 v3 §2.7 (写于 Zod 3 时代) 兼容性 — 全部测过 OK**: v3 spec line 326 `z.enum([...], { message: 'X' })` 是 Zod 4 新 API (Zod 3 用 `errorMap`) · 但 spec 写法在 Zod 4.4.3 下原样 PASS (验过 `safeParse('C').error?.issues[0]?.message === 'BAD'`) · `z.coerce.number().int(msg).min(min,msg).max(max,msg)` 同 (Zod 4 仍兼容 v3 spec verbatim 写法) · **下一棒不需要调整 inputSchemas.ts** · 写 backend 校验时 backend Pydantic ValueError code 也要返同一组 error code (`CUSTOMER_NO_FORMAT` 等) · 走 BE worker 的事
2. **`package.json` 多了 `zod` 依赖未 commit**: 我跑 `npm install zod` 装到 `credit_matrix_next/node_modules` 但**未** commit 新仓 `package.json` 改 (本 worker scope 在老仓 · 新仓 lock 走第 6 棒) · 下一棒/第 6 棒做新仓 contracts.lock.json 时记得**一起** commit `credit_matrix_next/package.json` 含 `"zod": "^4.4.3"` (W0 sub-agent D 出 lock spec 时 zod 应在 deps · 不在 devDeps · runtime 用)
3. **`additionalProperties: false` 在 artifact.schema 顶层 + snapshot open** 是一对 hidden 兼容点: artifact 顶层只允许 spec 列出的 13 字段 (id/schema_version/type/status/source_tool_call_id/owner_agent/title/version/patches/snapshot/verdict/qc_score/evidence_refs/created_at/updated_at + optional resolved_at) · 任何"额外字段"如 `metadata` / `subject_name` 顶层都 reject · **必须** nest 进 snapshot · 我 credit_decision.json 把 header/scoring/decision_trace/decision/ledger 都 nest 在 snapshot 里 · 而 snapshot 自身是 open schema (无 type/无 additionalProperties false) · 这是 spec 故意设计的"协议层窄 · 业务层宽" · 第 5 棒写 report.json / channel_search.json 同模式 · 别把业务字段写顶层

### Next 棒 (第 5 棒) 预计交付
- 3 fixture/*.json (report.json + channel_search.json + kb_doc.json · 各按 v3 §2.2 Artifact (前两个) + §2.4 KBDoc (kb_doc.json) 形态)
- report.json: type=report_draft · owner_agent=report · snapshot 含 N 节段 Evidence-First 三阶段产出 · verdict 含 quality_scorer 9 维评 · 中等-困难难度 (per CLAUDE.md §3.5 5 原则)
- channel_search.json: type=channel_search · owner_agent=channel · snapshot 含 5+ 候选 + 4 字段 (industry/geo/scale/similarity · Q-041 retain · root §3.7.2) + 信号 timeline · 中等难度
- kb_doc.json: KBDoc 单条 · tier 1-4 选 · pipl_region cn (默认) · content_hash 真 sha256 64-hex · source_type 5 种选 · verification_method 4 种选 · simple difficulty
- 估 30-45 min · 3 fixture 体量同本棒 credit_decision.json (≈ 150-200 行 each) · 累计 8 fixture 一起跑 ajv validate

### Blocker
- none

### File checklist 状态
- [x] shared/contracts/liuye/schemas/artifact.schema.json (8/14)
- [x] shared/contracts/liuye/schemas/liuye_chat_event.schema.json (8/14)
- [x] shared/contracts/liuye/schemas/tool_call.schema.json (8/14)
- [x] shared/contracts/liuye/schemas/kb_doc.schema.json (8/14)
- [x] shared/contracts/liuye/schemas/evidence_ref.schema.json (8/14)
- [x] shared/contracts/liuye/inputSchemas.ts (8/14 · 第 4 棒)
- [x] shared/contracts/liuye/fixtures/credit_decision.json (8/14 · 第 4 棒)
- [x] shared/contracts/liuye/fixtures/evidence_ref.json (8/14 · 第 4 棒)
- [ ] shared/contracts/liuye/fixtures/report.json (第 5 棒)
- [ ] shared/contracts/liuye/fixtures/channel_search.json (第 5 棒)
- [ ] shared/contracts/liuye/fixtures/kb_doc.json (第 5 棒)
- [ ] contracts.lock.json (第 6 棒 · schema_hash 计算 + 新仓 package.json 加 zod dep)
- [ ] scripts/sync-contracts.ts (W0 已存 · 后续棒只扩)
- [ ] scripts/verify-contracts.ts (W0 已存 · 后续棒只扩)

### ELAPSED min: 32
### Commit SHA: 4822cf0

## 2026-05-12 01:30 · checkpoint 11/14 (第 5 棒) · claude-W1-contract

### What I did (sub-agent · 30-45 min slot)
- 读 v3 §2.2 (Artifact + ArtifactPatch chunked line 111-156) + §2.4 (KBDoc/EvidenceRef line 224-248 verbatim)
- 读 v16 5 stage (`agent_report/api.py:133-139` 常量 STAGE_INGEST/EXTRACT/INFER/WRITE/AUDIT + `v16_runner.py:43-49` 同 SSOT) + 4 章模板 (`agent_report/api.py:173-178` _CHAPTER_TITLES + `v16_runner.py:71-76` _CHAPTER_HEADINGS) + classifier op/label 枚举 (`v16_generator.py` Classification.op PRESERVE/FILL/REWRITE · label SCAFFOLD/PRESERVE/FILL/CLEAR/SLOT/CHECKBOX/REWRITE)
- 读 `agent_channel/realtime_stream.py:659` signal_types 5 enum verbatim (`bidding / recognition / tech / growth / award`) + scoring.py 4 字段映射
- 写 `shared/contracts/liuye/fixtures/report.json` (Artifact type=report_draft · status=resolved · version=7 + 7 patches · 含 3 chunk ArtifactPatch 演示 chapter_1_background body 分片 streaming→final · snapshot 含 v16 5 stage stage_log + classification 统计 + 4 section + report_json + qc_gate 9 维 + ledger BE7 idempotency_key · 困难难度脱敏沧澜精密机械 C34 + 3 处 "未能自动填写" 标记 · QC PARTIAL 7/9)
- 写 `shared/contracts/liuye/fixtures/channel_search.json` (Artifact type=channel_search · status=resolved · version=3 + 3 patch · snapshot 含 5 候选难度分层 简单×1 / 中等×2 / 困难×1 / 极端×1 · 每候选必含 Q-041 4 字段 industry/geo/scale/similarity · 5 signal_type 全覆盖 growth/bidding/tech/recognition/award · evidence_refs ≥ 2/候选 · summary by_difficulty + signal_types_distribution + qc + banner_state · 5 候选名脱敏 + 真实形态参考)
- 写 `shared/contracts/liuye/fixtures/kb_doc.json` (Artifact type=kb_upload_result · status=resolved · version=5 + 5 patch · snapshot.kb_docs 4 KBDoc 全覆盖 tier 1-4 各 1 + pipl_region cn×3 + overseas×1 + content_hash 64 hex (4 sha256 模拟值) + 4 file_type pdf/xlsx/docx/scanned_image + 4 verification_method signature/cross_check/manual/unverified + ingest_summary 含 core_claim_blocked_count Tier 4 不能作为核心 claim 单一来源)
- 跑 ajv validate (Python jsonschema 4.26.0 Draft7Validator) · 累计 5/5 PASS:
  - credit_decision.json (type=credit_decision) vs artifact.schema PASS
  - report.json (type=report_draft) vs artifact.schema PASS
  - channel_search.json (type=channel_search) vs artifact.schema PASS
  - kb_doc.json (type=kb_upload_result) vs artifact.schema PASS
  - evidence_ref.json (5 entry array) vs evidence_ref.schema 全 PASS

### 关键决策
- **report.json 用 困难难度 + QC PARTIAL**: 不是为难而难 · 真实 v16 一笔报告 stage_log 必跑 5 段 + 9 QC 维 + 3 处"未能自动填写"是真实形态 (per CLAUDE.md §3.5 #2 难度分层 困难 20% 占位 · 全 fixture 5 个里 report 占困难档) · 中等难度 credit_decision.json (PASS 9/9) + 困难 report.json (PARTIAL 7/9) + 简单 kb_doc.json (PASS) + 难度分层 channel_search.json (5 候选混档)
- **ArtifactPatch chunked 演示 chapter_1_background body 分片**: 3 chunk (chunk_index 0/1/2 · chunk_total 3 · chunk_assembly streaming→streaming→final) · 模拟 64KB 上限内的真实分片场景 (Section 字数 ≥ 256 字 LLM 流式输出 · 真实 SSE 路径会拆 2-4 chunk) · 不演示极端 1-chunk-1-byte (那是 spec 边界 case · 不是 happy path fixture)
- **report.json snapshot 顶层挂 9 业务字段** (header / pipeline_progress / classification / sections / report_json / qc_gate / ledger 等) 全 nest 在 snapshot · artifact 顶层只挂 13 spec 字段 (id/schema_version/type/status/source_tool_call_id/owner_agent/title/version/patches/snapshot/verdict/qc_score/evidence_refs/created_at/updated_at + resolved_at) · 严格遵守第 4 棒 hidden gotcha #3
- **channel_search.json 5 候选 4 字段 verbatim**: 严格 Q-041 硬线 · industry / geo / scale / similarity 每候选都填 · similarity 是数值 (0.41-0.92 分布) · industry 是带括号的人读形态 ("通用设备制造业(C34)") · scale 4 档枚举 中型/中大型/大型/中型(集团型) · geo "省-市" 形态 · banner_state.has_blocker=false 因 5 候选满足 Q-041 4 字段 (root §3.7.2 + Stage B.5 dispatch 注入)
- **5 signal_type verbatim from `realtime_stream.py:659`**: bidding / recognition / tech / growth / award · 每候选 2 signal · 全 5 type 在 5 候选间均匀分布 · signal_summary 含具体金额/日期/项目 · 不是空话 (per CLAUDE.md 真实锚定 + 脱敏再造)
- **kb_doc.json 用 Artifact wrap KBDoc[]**: Artifact.type=kb_upload_result 是 5 enum 之一 (per artifact.schema enum) · owner_agent=report (KBDoc 上传由 Agent6 报告主管 · 与 v3 §2.4 KBDoc 协议+ liuye_service/orchestrator.py 预计接入 path 一致) · KBDoc 实体放 snapshot.kb_docs[] · 每 KBDoc 严格遵守 kb_doc.schema 必填 9 字段 · `_meta` 是扩展业务字段 (snapshot open schema 允许) 含 file_type / page_count / evidence_date / retrieved_at / data_tier / source_url / source_tier · 不污染 KBDoc 协议层 (协议层只有 v3 §2.4 列的 10 字段)
- **content_hash 64 hex 模拟 sha256**: 4 个 KBDoc 各 1 hash · 符合 `^[a-fA-F0-9]{64}$` (kb_doc.schema pattern) · 不是真 sha256 (fixture 用 · 不算真值) 但模式合法 · 重复 32 hex 拼 2 次构造 (e.g. `c4b3a29178f0e1d2c3b4a59687f0e1d2` × 2)
- **pipl_region overseas 单一 Tier 4 entry + pipl_note**: 演示 PIPL fallback chain 跨境合规场景 (root §3.6 + v3 §2.4) · pipl_note 字段 (snapshot open schema 允许) 显式 spell out "Tier 4 + overseas 不能作为核心 claim 单一来源 · 需 Tier 2-3 交叉佐证" · 后续 backend 适配器写 PIPL audit log 时取此字段 ground truth

### Hidden gotcha 发现 (1 个 · 关键提示下一棒)
1. **fixture 业务字段 nest 进 snapshot 是必修**: 我 3 个 fixture 都用 snapshot 包业务数据 · artifact 顶层严格只列 spec 13 字段 (additionalProperties: false 强约束) · 第 6 棒做 contracts.lock.json 计算 schema_hash 时 · 要确认 lock 锁的是**协议层 hash** (artifact.schema.json 等 5 schema 文件本身) · 不锁 fixture (fixture 是 consumer 验证用例 · 不进 lock · 否则 fixture 内容微调 lock 全错位)
2. **`_meta` 字段是 snapshot 业务扩展约定**: kb_doc.json snapshot.kb_docs[i]._meta 是我加的扩展位 (放 file_type / page_count / evidence_date / OCR 信息 / source_url / source_tier 等 backend 消费需要但 KBDoc 协议层未列字段) · 下一棒/backend worker 设计 KBDocConsumerView 时 · 协议层走 v3 §2.4 verbatim 10 字段 · UI / 后端业务层走 `_meta` extension (与 EvidenceRef 同模式 · EvidenceRef 协议层 9 字段 + retrieved_at/source_url/source_tier 等扩展)

### Next 棒 (第 6 棒) 预计交付
- `contracts.lock.json` 真值计算 (5 schema 各 sha256 · `LIUYE_CONTRACT_VERSION` env name · 锁老仓 commit SHA · 5 protected fields list verbatim from spec)
- 新仓 `credit_matrix_next/package.json` 加 `zod: ^4.4.3` deps · 一起 commit (第 4 棒 hidden gotcha #2 留单)
- `scripts/sync-contracts.ts` 扩 (W0 T1 smoke 基础上加 5 协议处理 · 跑 json-schema-to-typescript 出 `credit_matrix_next/lib/protocols/generated.ts` + Python codegen 跑 datamodel-code-generator 出 `liuye_service/contracts/generated.py`)
- `scripts/verify-contracts.ts` 扩 (跑 5 schema metaschema + 5 fixture 验证 + lock 一致性 + Zod inputSchemas tsc --noEmit · 全 PASS 才 exit 0)
- 估 45-60 min (lock hash + 双仓 codegen + CI 接入 · 多步骤)

### Blocker
- none

### File checklist 状态
- [x] shared/contracts/liuye/schemas/artifact.schema.json (11/14)
- [x] shared/contracts/liuye/schemas/liuye_chat_event.schema.json (11/14)
- [x] shared/contracts/liuye/schemas/tool_call.schema.json (11/14)
- [x] shared/contracts/liuye/schemas/kb_doc.schema.json (11/14)
- [x] shared/contracts/liuye/schemas/evidence_ref.schema.json (11/14)
- [x] shared/contracts/liuye/inputSchemas.ts (11/14)
- [x] shared/contracts/liuye/fixtures/credit_decision.json (11/14)
- [x] shared/contracts/liuye/fixtures/evidence_ref.json (11/14)
- [x] shared/contracts/liuye/fixtures/report.json (11/14 · 第 5 棒)
- [x] shared/contracts/liuye/fixtures/channel_search.json (11/14 · 第 5 棒)
- [x] shared/contracts/liuye/fixtures/kb_doc.json (11/14 · 第 5 棒)
- [ ] contracts.lock.json (第 6 棒 · schema_hash 计算 + 新仓 package.json 加 zod dep)
- [ ] scripts/sync-contracts.ts (第 6 棒 · 扩 5 协议处理)
- [ ] scripts/verify-contracts.ts (第 7 棒 · 扩 CI 接入)

### ELAPSED min: 38
### Commit SHA: <pending fill after commit>
