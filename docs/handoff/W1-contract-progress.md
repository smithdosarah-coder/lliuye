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
### Commit SHA: (本棒 commit 后填)
