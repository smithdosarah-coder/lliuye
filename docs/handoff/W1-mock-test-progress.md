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
### Commit SHA: <pending · 本段 append 完 main session 看 git log>
