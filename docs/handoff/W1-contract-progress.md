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
### Commit SHA: (待 git commit 后补)
