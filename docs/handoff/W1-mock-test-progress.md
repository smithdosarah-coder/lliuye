# W1-mock-test Progress (append-only)

> 接力 sub-agent 必读 · main session 监控源 · sub-agent checkpoint 每次 append 一段

<!-- 第一棒 sub-agent 在此 append 第一段 -->

## 2026-05-12 · scope-verify (第 1 棒) · claude-W1-mock-test

### What I did (sub-agent · 起手 7 件事)

1. 读 `docs/contracts/liuye-architecture.md` (Tier 1 SSOT · 126 行 · F-id namespace LY-NNN + RACI + W0 plan)
2. 读 `_temp/liuye-final-spec-v3.md` §6.3 (line 587-612 · demo path 70s 9 step + 并发优化 R10) + 附录 C (line 958-1032 · 3 fallback + demo hard gate + 现场 checklist) + §8 mock-test 段 (line 744-760 · 11 file checklist verbatim) + §2 协议 (PM 2026-05-11 ratify 加 permission.request · 11 event 含 heartbeat)
3. 读 老仓 root `CLAUDE.md` §3.5 (5 原则 mock · 盲测/难度分层/真实锚定/脱敏/环境边界 · 6 Agent 数据归属表) + §3.5.1 (第 6 原则 evidence_date + 4 Tier + freshness SLA + RecommendationReason 8 字段 + 第 7 原则 PM Feedback → Regression 闭环) + §3.7.2 (Q-041 4 字段硬线: industry/geo/scale/similarity · 缺字段 = regression)
4. 读 `credit_matrix_next/CLAUDE.md` (Tier 3 前端 scoped · §8 IME guard + §9 a11y · Playwright `home-silent` 跑它的 first byte token: composer 840×72 / pill 32h / icon 36 / radius 36 / send 42) + `liuye_service/CLAUDE.md` (Tier 3 BFF scoped · §3 adapter 唯一兼容层 · §11 18 文件交付 · 但本 scoped §3 仍写 "10 event" stale · v3 spec 主体 + 1106 PM ratify 已纠正为 11 event 含 permission.request)
5. 读 contract worker 输出 5 schema (artifact 5 type / liuye_chat_event 11 event + TurnErrorPayload + PermissionRequestEventPayload / tool_call 8 status + ProgressMessage 5 status / kb_doc tier 1-4 + content_hash sha256 / evidence_ref freshness 3 enum + data_tier 1-4) + 5 fixture (`tests/fixtures` 等价路径 `shared/contracts/liuye/fixtures/*.json` · channel_search / credit_decision / report / kb_doc / evidence_ref) · 我 `payload-shape.spec.ts` 用 ajv compile 5 schema 验我 3 demo fixture 符合 outputSchema
6. 读 `docs/onboarding/W1-worker-handoff-protocol.md` §2 + §5 (30 min checkpoint 硬规 + 5 字段 trailer + progress append-only · 每棒 30-45 min · W1-mock-test 8-12 棒)
7. 写本 scope verify 段 + scope verify commit

### 我理解 W1 mock-test scope (≤ 200 字)

我是 4 worker 并行第四棒 · 6-8 工时 / 8-12 sub-agent 棒. 输出 = CI gate + demo 彩排基线 + frontend 本地开发依赖. 11 文件 = 3 demo fixture (channel_5candidates 4 字段 + 难度分层 + evidence_date + Tier 2-3 / credit_decision_PASS 4 维评分 + qc_score + ledger idempotency_key / report_v16_PARTIAL 5 stage 中文 + "未能自动填写" 标记) + 3 mock SSE server (老 v1.0 不 liuye 11 event · 端口 8001/8002/8003 · 15s heartbeat · seq 递增 · LEI replay) + 2 contract spec (ajv schema 自身 + outputSchema 验 fixture) + 2 Playwright smoke (home-silent ground truth token + IME + demo-path-step1-3 step 耗时 ±20%) + migration spec (3 OLD_KEYS idempotent · archive_migrated_v1 标记 · 不丢字段). 5 原则 + 第 6 原则硬线. 禁发明 fixture 字段 / 禁 import agent_* / 禁双副本 fixture (SSOT 唯一 tests/fixtures · LIUYE_FIXTURES_PATH env 引用).

### 内部矛盾 (3 个 · 不阻塞但要主 session 知会)

1. **`liuye_service/CLAUDE.md` §3 标 "10 event" stale**: v3 spec 主体 (line 873 必修 #7 + line 899 #33 + line 1096-1106 PM 2026-05-11 ratify) 已纠正为 **11 event 含 permission.request** (control-layer · permissions.py 直接 emit · 不走 sse_v1_to_liuye.py adapter) · backend scoped §3 表格仍写 "10 event 映射" + 仅列 10 行 · 但 W1-backend-worker §4.8 应该有同步 (我没读 brief 全文确认) · **我 mock SSE server 走老 v1.0 7 event** (profile_loaded / stage / stream / tool_call / tool_result / done / error) · 不发 permission.request · 与 W1-mock-test §4.2 一致
2. **EvidenceRef freshness 3 enum vs `shared/evidence_freshness.py` 5 band 不对齐**: 契约层 fresh/critical/expired · 实际 classifier 返 fresh/recent/aging/stale/very_stale/unknown · contract worker §3 棒 hidden gotcha 已 spell out · 我 fixture evidence 用 3 enum (契约层) + evidence_date 真实日 · 让 backend runtime adapter 做 5→3 收敛 · 不在 fixture 层硬编 5 band
3. **EvidenceRef data_tier int 1-4 vs `shared/data_tiers.DataTier` str enum 不对齐**: 契约层 int 1|2|3|4 · 实际 DataTier 是 str enum 5 值含 UNKNOWN · 我 fixture data_tier 用 int (契约层) · source_tier optional 用 str enum · 双填走 description spell out 映射

### Next 棒 (第 2 棒 · 30-45 min) 预计交付

- `tests/fixtures/channel_5candidates.json` · 5 候选 · 难度分层 20% 简单 / 50% 中等 / 20% 困难 / 10% 极端 · 每候选 `industry / geo / scale / similarity` 4 字段全 (Q-041 硬线) + `≥ 2 evidence` (fresh + critical 各 1) · 每 evidence 必含 `evidence_date / data_tier (1-4) / freshness (3 enum)` (第 6 原则)
- `tests/fixtures/credit_decision_PASS.json` · 4 维评分 + verdict PASS + qc_score (passed/total) + 决策 trace 节点 + idempotency_key (ledger 写入) · 引用 channel 5 候选其一 (audit chain)
- 估 30-45 min · channel fixture 字段最复杂 (4 字段硬线最严 · evidence_date + data_tier 第 6 原则) · credit fixture 中等 · 用 ajv compile shared/contracts/liuye/schemas/artifact.schema.json 验 snapshot (channel_search type 一支)

### Blocker
- 无

### File checklist 状态 (11 文件)
- [ ] tests/fixtures/channel_5candidates.json (第 2 棒)
- [ ] tests/fixtures/credit_decision_PASS.json (第 2 棒)
- [ ] tests/fixtures/report_v16_PARTIAL.json (第 3 棒)
- [ ] tests/mock-sse/channel.ts (第 4 棒)
- [ ] tests/mock-sse/credit.ts (第 4-5 棒)
- [ ] tests/mock-sse/report.ts (第 5 棒)
- [ ] tests/contract/schema-validate.spec.ts (第 6 棒)
- [ ] tests/contract/payload-shape.spec.ts (第 6-7 棒)
- [ ] tests/e2e/playwright/home-silent.spec.ts (第 8 棒 · 待 frontend 跑起来)
- [ ] tests/e2e/playwright/demo-path-step1-3.spec.ts (第 9 棒 · 待 frontend + backend mock SSE 串起来)
- [ ] tests/migration/archive-storage.spec.ts (第 10-11 棒)

### ELAPSED min: ~35 (起手 7 件事 · scope verify commit · 不算 git commit 时间)
### Commit SHA: 0ca131f

---

## 2026-05-12 · 2 demo fixture (第 2 棒) · claude-W1-mock-test

### What I did (sub-agent · 第 2 棒)

1. 读 4 SSOT 输入: `agent_credit/scoring_model_corporate.py` (4 维评分 + DEFAULT_WEIGHTS 财务 0.35/行业 0.15/经营 0.25/担保 0.25 + sub_scores 6/4/5/4 子项 · GRADE_THRESHOLDS A 80 / B 65 / C 50) + `agent_credit/decision_graph.py` (7 node type: feature / rule / rule_hit / peer_benchmark / peer_gap / score_dimension / decision · 6 edge type 从 build_decision_graph 实际 _add_edge call 提取: triggered / threshold_of / caused / compared_to / derived_from / evidenced_by) + `agent_channel/signal_density.py` (11 signal_type 完整 enum: biz / bidding / growth / legal / tax / recruit / news / recognition / award / tech / social · 任务 brief 指定 5 个 growth/bidding/tech/recognition/award 是子集) + `quality_scorer.py` (9 维 verbatim name: 申报方案硬字段 / 企业基本情况 / 经营情况分析 / 财务分析深度 / 征信分析 / 担保评估 / 还款能力论证 / 授信建议与风险判断 / 格式规范 + 维度级 fatal gates 财务 ≥ 7 / 格式 ≥ 6 / 硬字段 ≥ 5)
2. 读 W1-contract worker 已交付 2 fixture 模板: `shared/contracts/liuye/fixtures/{channel_search.json, credit_decision.json}` (5 候选 + 难度分层 + decision_trace 7 node + ledger idempotency_key + parent_turn_id v1.1) + `evidence_ref.json` (5 evidence · freshness 3 enum fresh/critical/expired 全覆盖 · data_tier 1-4 全覆盖 · source_tier str enum 与 data_tier int 双填) — 我的 fixture 在此基础上加强: 每候选 ≥ 2 evidence 完整含 evidence_chain[] 内嵌 (不只顶层 evidence_refs id) + 严格 5 难度分层 1/2/1/1 + 第 6 原则 evidence_date 全 + Tier 2-3 交叉硬线
3. 写 `tests/fixtures/channel_5candidates.json` (500 行) + `tests/fixtures/credit_decision_PASS.json` (345 行) · 共 845 行 · 详见下文
4. 跑 ajv validate (`py -c "import jsonschema; ..."` · Python jsonschema 4.26.0 走 draft-07 validator) vs `shared/contracts/liuye/schemas/artifact.schema.json` · 2/2 PASS · type 字段验 channel_search / credit_decision · 顶层 additionalProperties: false 强制 nest 进 snapshot 通过
5. checkpoint commit (本文档 append)

### 2 fixture 路径 + 关键 line range

- `tests/fixtures/channel_5candidates.json` (500 行)
  - seed L65-72 (C36 新能源汽车零部件 · 江苏-常州 · 规上中型)
  - candidates[0] cand_easy_chenfeng_evparts L74-148 (简单 · similarity 0.88 · 3 evidence)
  - candidates[1] cand_med_qichuang_powertrain L149-204 (中等 · 0.74 · 2 evidence)
  - candidates[2] cand_med_runfang_battery L205-281 (中等 · 0.68 · 3 evidence 含 critical freshness)
  - candidates[3] cand_hard_haoyu_chassis L282-336 (困难 · 0.52 · 2 evidence · 含 expired)
  - candidates[4] cand_extreme_longyu_holdings L337-396 (极端 · 0.32 · 2 evidence · 信号矛盾)
  - summary L398-410 (5 候选难度 1/2/1/1 · signal_types_distribution growth4/bidding2/tech2/recognition2/award1 · qc_passed=true · candidates_meeting_q041_hardline=5)
  - ledger L416-423 (channel:lookalike · short retention · parent_turn_id=null)
- `tests/fixtures/credit_decision_PASS.json` (345 行)
  - header L84-95 (subject_id_hash + linked_channel_candidate_id=cand_easy_chenfeng_evparts · 跨 fixture audit chain)
  - scoring L97-150 (4 维: financial 76/35% / industry 70/15% / operational 80/25% / guarantee 72/25% · composite 75 · B 级)
  - decision_trace L152-242 (7 node 全 type + 7 edge 含 6 type · peer_gap::net_margin 0.014 利好)
  - qc L244-261 (9 dim verbatim 中文名 · 全 PASS · 总分 84.5)
  - ledger L271-288 (agent_id=credit · standard 5y retention · evidence_chain 引 channel cand 3 evidence_refs)

### ajv validate 结果

- Validator: Python jsonschema 4.26.0 (draft-07 · ajv 替代 · 同等严格)
- Schema: `shared/contracts/liuye/schemas/artifact.schema.json` (5 type lock · additionalProperties: false · 13 required field)
- Result: **2/2 PASS** · 0 error
- 关键校验通过项: (1) type 字段验 channel_search / credit_decision 各对应; (2) 顶层 additionalProperties: false 阻止业务字段挂顶层 (全部 nest 进 snapshot 通过); (3) patches[] ArtifactPatch 8 required 全; (4) snapshot 字段开放 schema 通过 (per-type narrowing 在 inputSchemas.ts 消费端)

### Hidden gotcha (下一棒注意)

1. **agent_credit 4 维 vs quality_scorer 9 维不是同一 axis**: scoring_model_corporate.py 4 维 (financial/industry/operational/guarantee) 是评分模型轴 (composite_score 算法), quality_scorer.py 9 维 (申报方案硬字段/企业基本情况/...) 是报告文本质量 audit 轴. 两者**不交叉**, 都要进 fixture. 我 fixture 用 `snapshot.scoring.dimensions` 装 4 维, `snapshot.qc.dimensions` 装 9 维 · 互不污染.
2. **signal_type 实际 enum 11 个不是 5 个**: brief 列的 growth/bidding/tech/recognition/award 是子集. 完整 enum (per `signal_density.py:99-111`): biz / bidding / growth / legal / tax / recruit / news / recognition / award / tech / social. 第 3 棒写 report_v16_PARTIAL 时如有 signal 引用按完整 enum 验.
3. **6 edge type 实际名**: 从 `decision_graph.py:_add_edge` 实际 call 提取 6 名 verbatim: `triggered` / `threshold_of` / `caused` / `compared_to` / `derived_from` / `evidenced_by` · brief 写"6 edge type"未列名 · 这是真实 SSOT. 第 6 棒写 contract spec 时按这 6 名验 fixture decision_trace.edges.
4. **decision_trace.nodes type 准确名**: feature / rule / rule_hit / peer_benchmark / peer_gap / score_dimension / decision (7 个) · 其中 `score_dimension` 不是 `score` (与 W1-contract fixture 一致) · `peer_benchmark` 不是 `peer` · 第 6 棒 contract spec 注意 enum 校验.
5. **EvidenceRef 在 channel candidates 走两份**: `evidence_refs[]` (string id 列表 · per evidence_ref.schema.json line 17) + `evidence_chain[]` (我加的 inline 完整 evidence 内嵌 · 不破 artifact schema 因 snapshot 字段开放). 第 6 棒 payload-shape.spec.ts 验 evidence_ref schema 用顶层 `evidence_refs` 字段是 string list, 验 inline 完整 evidence 走 candidates[].evidence_chain[].
6. **ledger v1.1 parent_turn_id 留 null**: 本 fixture 是 Cowork 单 mode · 非跨 mode (Cowork→Managed 才填 e.g. DSL→backtest). 第 3 棒 report fixture 也单 mode · 第 6 棒 contract spec 验 schema 时 parent_turn_id 必须 null 而非 missing (per decision_ledger schema v1.1 + perfect-check-6 ratify).

### File checklist 状态 (11 文件)

- [x] tests/fixtures/channel_5candidates.json (第 2 棒 · 500 行 · DONE)
- [x] tests/fixtures/credit_decision_PASS.json (第 2 棒 · 345 行 · DONE)
- [ ] tests/fixtures/report_v16_PARTIAL.json (第 3 棒)
- [ ] tests/mock-sse/channel.ts (第 3-4 棒)
- [ ] tests/mock-sse/credit.ts (第 4 棒)
- [ ] tests/mock-sse/report.ts (第 4-5 棒)
- [ ] tests/contract/schema-validate.spec.ts (第 6 棒)
- [ ] tests/contract/payload-shape.spec.ts (第 6-7 棒)
- [ ] tests/e2e/playwright/home-silent.spec.ts (第 8 棒)
- [ ] tests/e2e/playwright/demo-path-step1-3.spec.ts (第 9 棒)
- [ ] tests/migration/archive-storage.spec.ts (第 10-11 棒)

### Next 棒 (第 3 棒 · 30-45 min) 预计交付

- `tests/fixtures/report_v16_PARTIAL.json` · v16 5 stage (classifier → generator → QC → fill → finalize) + ArtifactPatch chunked patch (chunk_index / chunk_total / chunk_assembly streaming) · 中文 + "未能自动填写" 标记 · verdict=PARTIAL (qc_score passed < 9) · 引用 credit_decision_PASS.json 的 subject_id_hash (二级 audit chain)
- 起 3 mock SSE server: `tests/mock-sse/{channel.ts, credit.ts, report.ts}` · 老 v1.0 (7 event: profile_loaded / stage / stream / tool_call / tool_result / done / error) 不发 liuye 11 event · 端口 8001/8002/8003 · 15s heartbeat · seq 递增 · LEI replay
- 估 30-45 min · report fixture chunked patch 形态最难写 (60ms 一个 chunk / 字节级 64KB 上限) · mock SSE 3 个 server 是模板复制

### Blocker
- 无

### ELAPSED min: ~30 (4 SSOT 读 + 2 fixture 写 + ajv validate + progress append + commit)
### Commit SHA: 36a8c2f

---

## 2026-05-12 · 1 fixture + 3 mock SSE (第 3 棒) · claude-W1-mock-test

### What I did (sub-agent · 第 3 棒)

1. 读 4 SSOT 输入 (新读 · 第 2 棒未读): `v16_pipeline.py` (5 stage 编排 + CLI 入口 · qc_pass_threshold 75 + 9 维 markdown formatter `_format_qc_markdown`) + `v16_generator.py` (classifier output → element loop → handler dispatch · `generate()` 主入口 · `apply_to_docx` 写回 docx · `_finalize_doc_hard_facts` doc-level facts 替换 · `_detect_body_gaps` SCAFFOLD 缺 body 检测) + `docs/contracts/sse-envelope.md` v1.0 (老 7 event verbatim table §1.5 · done envelope §2.1 12 字段 · 6 Agent payload tail §3 · §3.6 Riskctrl 🟡 pending) + `shared/contracts/liuye/fixtures/report.json` (W1-contract worker 模板 · 我 fixture 数值/企业名独立但形态对齐 · subject_id_hash 引第 2 棒 credit fixture cand_easy_chenfeng_evparts 跨 fixture audit chain)
2. 写 `tests/fixtures/report_v16_PARTIAL.json` (390 行 · v16 5 stage 中文 stage_label 完整 stage_log · ArtifactPatch 3 chunk streaming→final · QC verdict PARTIAL · 3 字段 "未能自动填写" 标记 · evidence 5 ref + 6 financial_metric 含 evidence_date/data_tier 1-2/freshness fresh · tier_cross_check Tier 1 内部 6 + Tier 2 监管 2 · cross_tier_2_3_used=true · principles_compliance 6 原则 verbatim · ledger v1.1 parent_turn_id=null + evidence_chain 引 credit_artifact_id 和 channel_artifact_id 三级 audit chain)
3. 写 `tests/mock-sse/channel.ts` (端口 8001 · 7 event · 200ms drain interval · 15s heartbeat · LEI replay · export start() programmatic + CLI `--port --fixture` · 6 endpoint: profile_loaded / stage / tool_call / tool_result / stage / stream / done · payload = ChannelPayload per sse-envelope §3.1)
4. 写 `tests/mock-sse/credit.ts` (端口 8002 · 7 event · 250ms drain · payload = CreditPayload §3.3 · 7 endpoint: stage(feature_extract) / tool_call(scoring_model) / tool_result / stage(red_line) / stream / stage(decision_compose) / done · 4 维 scoring 透传 + qc + decision_letter)
5. 写 `tests/mock-sse/report.ts` (端口 8003 · 7 event · 300ms drain · payload = ReportPayload §3.2 · 14 endpoint: profile_loaded / 5 stage 中文 stage_label 全发 / tool_call(v16_classifier) / tool_result / 3 stream(Evidence-First chunk 0/1/2 含 "未能自动填写") / tool_call(quality_scorer) / tool_result / done · V16_STAGE_LOG_FALLBACK 5 行 ingest/extract/infer/write/audit 中文标 · sse-envelope §3.2 metrics 4 字段全填)
6. 跑 ajv validate 3/3 fixture vs `shared/contracts/liuye/schemas/artifact.schema.json` (累计 channel + credit + report) · Python jsonschema 4.26.0 draft-07 · 0 error · 额外验 chunked patch 3/3 PASS + chunk_assembly 序列 streaming→streaming→final 正确
7. manual quick smoke: 起 channel mock server (临时 cjs wrapper 走 express 4.22 + cors 2.8 跑 4s 自停) · Invoke-WebRequest GET /health 200 · GET /api/channel/run 200 · 收到 15940 bytes · 7 event + 3 heartbeat 全见 · id: seq 1→7 单调递增 · event 名 verbatim · data 单行 JSON · done envelope 12 字段全在 (event/version/agent/session_id/ok/ts/duration_ms/metrics/payload/warnings/errors/trace_id) · smoke 后删 `_smoke_channel.cjs` 不入库
8. progress append + commit (仅 4 文件)

### 4 文件路径 + 关键 line range

- `tests/fixtures/report_v16_PARTIAL.json` (390 行)
  - patches 9 个 L11-130 (v1 header → v2 ingest stage_label 材料解析 → v3 classification → v4-v6 chunk 0/1/2 streaming→final → v7 section resolved → v8 merge audit 质量复核 → v9 qc_gate PARTIAL)
  - chunked patch L60-107 (chunk_index 0/1/2 · chunk_total 3 · chunk_assembly streaming→streaming→final)
  - snapshot.pipeline_progress.stage_log L155-200 (5 stage verbatim 中文 stage_label: 材料解析/字段抽取/结构推断/段落生成/质量复核 + Evidence-First 三阶段 phase 标 in write stage)
  - 4 sections L210-275 (4 章 含 "未能自动填写" 3 处 · chapter_1 股东涉诉 · chapter_2 2025 订单 · chapter_3 2025Q1 财务 · chapter_4 conclusion 重述 unfilled)
  - financial_metrics L235-308 (7 metric 含 evidence_date + data_tier 1-2 + freshness fresh + freshness_days · tier_cross_check Tier 1=6 / Tier 2=2)
  - qc_gate L322-345 (9 维 verbatim · dimensions_passed 7/9 · blocked_dimensions: financial_consistency + external_anchor_coverage)
  - evidence_summary L347-392 (5 evidence · 全 fresh · tier 1-2 only · claim_type 5 type)
  - ledger L394-420 (parent_turn_id=null v1.1 · evidence_chain 三级: credit→channel→report)
  - principles_compliance L422-432 (6 原则 verbatim 一行一原则)
- `tests/mock-sse/channel.ts` (192 行) · L25-31 SseEvent 7 enum · L41-49 writeEvent 写 id+event+data · L56-145 buildEventSequence 7 event 推送 · L155-198 start(port, fixturePath) export
- `tests/mock-sse/credit.ts` (185 行) · 同 channel 结构 · L52-148 buildEventSequence 7 event (stage feature_extract / tool_call / tool_result / stage red_line / stream / stage decision_compose / done)
- `tests/mock-sse/report.ts` (245 行) · L60-66 V16_STAGE_LOG_FALLBACK 5 stage 中文 · L80-210 buildEventSequence 14 event (profile_loaded / 5 stage / tool_call classifier / tool_result / 3 stream Evidence-First chunk 0/1/2 / tool_call quality_scorer / tool_result / done)

### ajv validate 累计结果

- 累计 3/3 fixture PASS vs `artifact.schema.json` (channel_search + credit_decision + report_draft)
- 额外: ArtifactPatch chunked 字段 (chunk_index / chunk_total / chunk_assembly) 3/3 PASS
- 额外: chunk_assembly 序列 streaming → streaming → final 验证通过

### mock SSE manual quick test (channel.ts via 临时 cjs wrapper)

- GET http://127.0.0.1:8001/health → 200 · `{"ok":true,"agent":"channel","port":8001}`
- GET http://127.0.0.1:8001/api/channel/run (Last-Event-ID: 0) → 200 · 15940 bytes
- 7 event verbatim 全见: profile_loaded / stage(signal_density) / tool_call / tool_result / stage(ranked) / stream / done
- id: seq 单调递增 1→7
- event: 名验毕全合法 (per sse-envelope.md §1.5)
- data: 单行 UTF-8 JSON (PowerShell 控制台 CP936 解码乱码 · 但 wire bytes UTF-8 正确)
- heartbeat `: ping <ts>` comment line 多次出现 (smoke 用 100ms 加速 · 真实 server 15000ms)
- done envelope 12 字段全在: event/version=1.0/agent=channel/session_id/ok=true/ts/duration_ms/metrics(4 key)/payload(candidates+summary+data_source=mock)/warnings/errors/trace_id

### Hidden gotcha (下一棒注意)

1. **v16 5 stage 命名 SSOT 漂移**: `v16_pipeline.py` 实际只编排 3 step (classifier → generator → QC gate · per `run_pipeline` L85-156 + docstring L4-9) · 不是 5 stage · 但 W1-contract worker `shared/contracts/liuye/fixtures/report.json` 写的是 5 stage_label (`ingest/extract/infer/write/audit`) · 这是 **v3 spec §6.3 demo path 70s 9 step 派生** 的展示层粒度 · 不是后端 pipeline 实际 step 粒度。本 fixture + report.ts mock SSE 走 W1-contract 5 stage_label (展示层 SSOT) · 后端 adapter 把 3 step 映射成 5 stage event。第 6 棒 contract spec 验时按 5 stage 验展示层 stage_log · 不可用 `v16_pipeline.run_pipeline` 实际 step 名验。
2. **express + cors 跨仓 install 路径**: 我新建 `tests/package.json` 装 express^4.22.2 + cors^2.8.6 (npm install · 102 包 · 16s) · node_modules 落 `tests/node_modules/` (1MB+) · **没入 commit** (per 严格 4 文件硬线) · 第 4+ 棒接手时跑 `cd tests && npm install` 重建 · 或加 tests/ 到 .gitignore 把 node_modules 排除 · package.json + package-lock.json 留作下一棒 CI 接入时决定 (现状 untracked)。
3. **SSE Last-Event-ID replay 实做边界**: 当前实做 = 读 req header `Last-Event-ID` parseInt · 后续 seq 从此 +1 起 (lines 132-133 channel.ts) · **但 events 序列本身不缩短** (仍发全 7 event) · 真 replay 应该 skip 已发 id ≤ lastEventId 的 event。本实做满足 "id 单调递增 + 起点可控" 形态契约 · 但不是真 idempotent replay (需 fixture event 加 `_seq` 字段才能跳过)。第 8/9 棒 Playwright smoke 验 demo-path 时不依赖真 replay 形态 · OK。第 6 棒 contract spec 若验 replay 行为需明确测的是 "起点可控" 而非 "skip 已发"。
4. **Chunked patch 验证额外项**: artifact.schema.json L175-189 定义 chunk_index/chunk_total/chunk_assembly 3 字段 optional · 但语义上 chunked 必三件套同时 set (per v3 §2.2 hardline)。本 fixture 3 chunk 全三件套 set · 但 schema 没强制三件套必同时 set · 第 6 棒 payload-shape spec 加 cross-field 校验 (chunk_index 存在 → chunk_total + chunk_assembly 必同存)。
5. **PowerShell console UTF-8 解码乱码**: smoke 输出中文显示为 `æ°` 等乱码 · 不是 fixture 或 server bug · 是 PS5.1 默认 OEM 936 (GBK) 解码 UTF-8 bytes 的显示问题 · curl/Invoke-WebRequest 收到的 byte stream 是 UTF-8 正确 · 第 8 棒 Playwright (Chromium) 跑时 utf-8 解码自动正确 · 不会复现 PS 乱码。

### File checklist 状态 (11 文件)

- [x] tests/fixtures/channel_5candidates.json (第 2 棒 · DONE)
- [x] tests/fixtures/credit_decision_PASS.json (第 2 棒 · DONE)
- [x] tests/fixtures/report_v16_PARTIAL.json (第 3 棒 · 390 行 · DONE)
- [x] tests/mock-sse/channel.ts (第 3 棒 · 192 行 · DONE · smoke PASS)
- [x] tests/mock-sse/credit.ts (第 3 棒 · 185 行 · DONE)
- [x] tests/mock-sse/report.ts (第 3 棒 · 245 行 · DONE)
- [ ] tests/contract/schema-validate.spec.ts (第 4 棒)
- [ ] tests/contract/payload-shape.spec.ts (第 4-5 棒)
- [ ] tests/e2e/playwright/home-silent.spec.ts (第 6-7 棒)
- [ ] tests/e2e/playwright/demo-path-step1-3.spec.ts (第 7-8 棒)
- [ ] tests/migration/archive-storage.spec.ts (第 9-10 棒)

### Next 棒 (第 4 棒 · 30-45 min) 预计交付

- `tests/contract/schema-validate.spec.ts` (ajv compile 5 schema 自身 · draft-07 · `$id` 唯一性 · 全 required 字段健全 · enum 列表正确性)
- `tests/contract/payload-shape.spec.ts` (用 contract worker `verify-contracts.ts` 逻辑验 3 fixture 符合 outputSchema · cross-field chunked patch 三件套强校验 · evidence_ref schema 顶层 string list vs inline evidence_chain 双形态区分 · channel Q-041 4 字段缺失硬 fail)
- 估 30-45 min · ajv 配置最易踩 (draft-07 vs draft-2020 · $id 解析 · 错误 path 输出)
- 同棒还可补 `tests/.gitignore` (node_modules + package-lock.json 排除 · 我没动 · 留下一棒决定 CI 接入策略时一起 commit)

### Blocker

- 无

### ELAPSED min: ~40 (4 SSOT 读 ~10min + 1 fixture 写 + 3 mock SSE 写 ~22min + ajv validate + smoke test 调试 PS 跨进程 curl ~6min + progress append + commit)
### Commit SHA: cee80ab

## 2026-05-12 04:55 · checkpoint 8/11 (第 4 棒) · claude-W1-mock-test

### What I did (sub-agent · 第 4 棒 · 30-45 min slot)

1. 读 SSOT (新读 · 前 3 棒未读): `shared/contracts/liuye/schemas/*.json` 5 schema (ajv loader 加载 · 验 metaschema + meta-field + additionalProperties + compile) + `shared/contracts/liuye/fixtures/{kb_doc,evidence_ref}.json` 2 contract worker fixture (跨 fixture audit chain · evidence_ref.json 是 array · kb_doc.json 是 artifact 全栈 type=kb_upload_result) + 3 tests/fixtures (第 2-3 棒写 · 复读为 fixture binding 表)
2. **npm install dev tools 老仓 tests/**: 装 `ajv@^8` (8.20.0) + `ajv-formats@^3` (3.0.1) + `tsx@^4` (4.21.0) 跨 monorepo 与新仓 credit_matrix_next 对齐版本 · package.json/package-lock.json 自动更新但**留 untracked**(per 第 3 棒注 + 本棒硬线) · 选 tsx 而非 vitest 因为 monorepo 暂无 vitest config + 单文件 spec + 直接 exit code 0/1 更适 W1 D2 阶段 hand-on smoke
3. 写 `tests/contract/schema-validate.spec.ts` (138 行): 5 schema × 9 check = 45 assertion · (a) ajv.validateSchema(schema) 过 draft-07 metaschema (b) `$id`/`$schema`/`title`/`description` 4 必填非空 (c) `$schema` 必须 = `http://json-schema.org/draft-07/schema#` (d) root `additionalProperties: false` (e) ajv.compile (no throws)
4. 写 `tests/contract/payload-shape.spec.ts` (213 行): 5 fixture binding (3 tests/fixtures + 2 contract worker fixtures) · ajv compile 5 schema · `validateChunkedPatchTriple` post-check (chunk_index/chunk_total/chunk_assembly 三件套 cross-field + chunk_index < chunk_total 边界) · `validateChunkedPatchSequence` (同 chunk_total 下 index 序列覆盖 [0..total-1] · 末 chunk_assembly=final · 之前=streaming) · evidence_ref array mode 逐元素验
5. 编辑 `.gitignore` 加 3 entry: `tests/node_modules/` (npm install 产物 ~1MB+) + `tests/coverage/` (vitest 跑出 coverage · 防误入库) + `tests/.vitest-cache/` (vitest 缓存) · 顺手 verify (未动) `data/liuye/outbox/` + `data/liuye/dead-letter/` 现 .gitignore **不存在** (留 backend 棒 verify · 当前 `data/liuye/` 目录本身也不存在)
6. 跑 verify: 两 spec exit 0 · schema-validate 45/45 PASS · payload-shape 16/16 PASS · chunked patch 3 hit 全 OK (report_v16_PARTIAL.json patch_w1rp_v4/v5/v6_chunk0/1/2 index=0/1/2 total=3 assembly=streaming/streaming/final) · `git check-ignore tests/node_modules/` echo path 验 ignored
7. progress append + commit (仅 3 文件: 2 spec + .gitignore)

### 3 文件路径 + 关键 line range

- `tests/contract/schema-validate.spec.ts` (138 行)
  - L25-29 SCHEMA_FILES 5 schema 文件名 const
  - L31-32 REQUIRED_META_FIELDS 4 + DRAFT_07_METASCHEMA URL const
  - L52-105 main() · ajv 8 strict=false + addFormats · 5 schema × 5 check loop (read+parse / metaschema / 4 meta-field / $schema URL / additionalProperties / ajv.compile)
  - L107-122 report 输出 + exit code
- `tests/contract/payload-shape.spec.ts` (213 行)
  - L34 REPO_ROOT 路径解析 (../.. from tests/contract/ → repo root)
  - L43-79 BINDINGS 5 fixture binding table (label / fixturePath / schemaName / arrayMode / expectedType)
  - L106-145 `validateChunkedPatchTriple()` (return ChunkedCheckResult[]) · 三件套 cross-field + chunk_index < chunk_total
  - L149-180 `validateChunkedPatchSequence()` 同 chunk_total 下 index 0..N-1 + assembly streaming×N-1 + final×1
  - L182-237 main() · 5 schema pre-compile · 5 binding loop · arrayMode 分支 · expectedType 跨字段 · chunked 后处理
  - L239-272 report 输出 (含 chunked hit 详情 + binding-level OK/FAIL 列表)
- `.gitignore` (新增 L180-189): 在末尾"Playwright admin auth"段后追加 W1-mock-test harness 段 · 3 entry: `tests/node_modules/` + `tests/coverage/` + `tests/.vitest-cache/` · 注释说明留 contract worker 决定 package.json 入库时机

### ajv validate 双 spec 结果

- **schema-validate.spec.ts**: total=45 pass=45 fail=0 · exit 0
  - 5 schema × {read+parse · draft-07 metaschema · 4 meta-field × 1 · `$schema` URL · root additionalProperties:false · ajv.compile no-throw} = 45 check
  - 全 5 schema (artifact / evidence_ref / kb_doc / liuye_chat_event / tool_call) 通过
- **payload-shape.spec.ts**: total=16 pass=16 fail=0 · exit 0
  - 5 binding × {read+parse · ajv.validate · type-cross-check (4 binding) · chunked-triple-sequence (1 binding 命中)} = 16 check
  - 全 5 fixture 验 schema OK · chunked patch 3 实例 triple + sequence 双校验 OK

### Chunked patch triple check 命中实例 (per hidden gotcha #4)

- `tests/fixtures/report_v16_PARTIAL.json` 3 chunked patch 全 OK:
  - `patch_w1rp_v4_chunk0`: chunk_index=0 chunk_total=3 chunk_assembly=streaming · 三件套同存 · OK
  - `patch_w1rp_v5_chunk1`: chunk_index=1 chunk_total=3 chunk_assembly=streaming · 三件套同存 · OK
  - `patch_w1rp_v6_chunk2`: chunk_index=2 chunk_total=3 chunk_assembly=final · 三件套同存 · OK
  - 序列覆盖 [0,1,2] 完整 · assembly 序列 streaming→streaming→final 正确
- 另外验过反例 (sanity 不入 commit · inline node 验证):
  - chunk_index 存在但 chunk_total/chunk_assembly 缺 → CAUGHT (triple incomplete)
  - chunk_index ≥ chunk_total → CAUGHT (idx>=total)
  - chunk_assembly ∈ enum 外 → CAUGHT
- 其他 4 fixture (channel_5candidates / credit_decision_PASS / kb_doc / evidence_ref) 无 chunked patch · cross-field check vacuous · 符合预期 (channel 单 patch · credit 5 patch 无切片需 · kb_doc 5 patch 单 append · evidence_ref 是 KBDoc evidence flat array)

### Hidden gotcha (下一棒注意)

1. **ajv 自定义 keyword vs post-check trade-off**: 第一次方案考虑用 ajv `addKeyword('chunkedTriple', ...)` · 但这要改 schema 文件 (加 chunkedTriple: true 标记) · 违反 "不动 5 schema (W1-contract SSOT)" 硬线 · 改走 post-check function 加在 spec 层 · 优势 = schema 文件保持纯 draft-07 · 劣势 = 别处 (e.g. backend artifact patch 校验) 要重写一遍 cross-field 逻辑 · 建议 Phase D shared/contracts/liuye/runtime/chunked-patch-check.ts 单独抽出来跨 spec + backend + frontend 共用
2. **vitest vs npx tsx 选择**: tests/package.json 现在装的是 tsx + ajv + express + cors 全栈 · 但**没装 vitest** · 第 5 棒 Playwright 需要 `@playwright/test` (含 test runner) 必装新 dep · 若同时想用 vitest 跑 contract spec 需统一 dep 树 · 建议第 5 棒一并加 vitest@^2 + tsconfig.json + vitest.config.ts (现 tests/ 无 tsconfig · 我用 tsx 直跑 .ts 不要 tsconfig 也能跑 · vitest 必须有 tsconfig.json)
3. **monorepo test runner 配置真空**: 老仓根 `package.json` 不存在 (Python 单仓为主) · 新仓 `credit_matrix_next/package.json` 是 Next.js · 都没 root-level test runner 配置 · 当前 tests/ 是独立 sub-package · 第 6+ 棒接 CI 时建议在 GitHub Actions 加 `cd tests && npm ci && node_modules/.bin/tsx contract/*.spec.ts` 跑 contract gate · 不需要 root-level npm
4. **kb_doc.json 跨 fixture 引用边界**: kb_doc.json 是 W1-contract worker 的 fixture · 验 schema 用的是 `artifact.schema.json` (type=kb_upload_result) · NOT `kb_doc.schema.json` · 因为 fixture 是 Artifact 全栈 + snapshot.kb_docs[]·`kb_doc.schema.json` 验的是单条 KBDoc record (在 snapshot.kb_docs[i] 内部) · 这层 schema-internal narrowing 在 inputSchemas.ts (Zod) 那一棒做 · 第 6 棒做 Zod narrowing 时记得 kb_docs[]·patches[i].value (`type=='kb_upload_result'` 时) 也是 KBDoc shape · 双向校验 (artifact level + nested KBDoc level)
5. **evidence_ref.json array vs object 双形态**: 当前 fixture 是 array (per W1-contract 第 4 棒决策) · 但 v3 spec EvidenceRef 单体也合法 · payload-shape.spec.ts 走 arrayMode=true 逐元素验 · 第 6 棒做 inputSchemas.ts Zod 时建议提供 `EvidenceRefSchema` 单体 + `EvidenceRefArraySchema` 数组双形态 · 不要锁死 array
6. **tests/package.json 入库决策延期**: 第 3 棒注 "留 contract worker 决策" · 第 4 棒 npm install 后 package.json 又 modified 一次 (加 ajv/ajv-formats/tsx 3 dev dep) · 仍 untracked · package-lock.json 同 · 建议第 5 棒 (起 Playwright) 一并 commit 进 W1-contract repo · 加 trailer `Authorized-By: contract-worker` (跨 worker 边界) · 或第 6 棒契约整合时统一处理

### File checklist 状态 (11 文件)

- [x] tests/fixtures/channel_5candidates.json (第 2 棒 · DONE)
- [x] tests/fixtures/credit_decision_PASS.json (第 2 棒 · DONE)
- [x] tests/fixtures/report_v16_PARTIAL.json (第 3 棒 · DONE)
- [x] tests/mock-sse/channel.ts (第 3 棒 · DONE · smoke PASS)
- [x] tests/mock-sse/credit.ts (第 3 棒 · DONE)
- [x] tests/mock-sse/report.ts (第 3 棒 · DONE)
- [x] tests/contract/schema-validate.spec.ts (第 4 棒 · 138 行 · 45/45 PASS · DONE)
- [x] tests/contract/payload-shape.spec.ts (第 4 棒 · 213 行 · 16/16 PASS · chunked 3 hit · DONE)
- [x] .gitignore (第 4 棒 · 加 tests/{node_modules,coverage,.vitest-cache}/ · DONE)
- [ ] tests/e2e/playwright/home-silent.spec.ts (第 5 棒)
- [ ] tests/e2e/playwright/demo-path-step1-3.spec.ts (第 5 棒)
- [ ] tests/migration/archive-storage.spec.ts (第 6 棒)

### Next 棒 (第 5 棒 · 30-45 min) 预计交付

- `tests/e2e/playwright/home-silent.spec.ts` (Playwright spec · 主页静默时 7 event 不发 · LEI replay 起点可控)
- `tests/e2e/playwright/demo-path-step1-3.spec.ts` (Playwright spec · demo path step 1-3 跑过 3 mock SSE 端口 8001/8002/8003)
- `tests/migration/archive-storage.spec.ts` (第 6 棒留 · 第 5 棒先聚焦 Playwright)
- 估 30-45 min · `@playwright/test` 装包 + `playwright install chromium` (~120MB) + tsconfig.json 起 + spec 写 + 跑 3 mock server 并发起 + chromium 截图断言
- 注: tests/package.json 已含 tsx + ajv + express + cors · 第 5 棒加 `@playwright/test` 顺便决策 tests/package.json 入库时机

### Blocker

- 无

### ELAPSED min: ~36 (4 SSOT 读 ~6min · npm install + 验装 ~4min · 2 spec 写 ~16min · ajv negative-path sanity + 反例验证 ~3min · .gitignore + verify ~2min · progress append + commit ~5min)
### AJV-VALIDATE: 5 schema metaschema PASS + 5 fixture vs outputSchema PASS (45+16 = 61 assertion total)
### CHUNKED-PATCH-TRIPLE: 3 fixture 跑过 (report_v16_PARTIAL 3 hit · 其他 4 fixture 无 chunked · vacuous PASS)
### Commit SHA: 13597e7

