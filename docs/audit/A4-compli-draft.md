# A4-compli Pre-A3-Cherry-Pick Draft

> Worker: A4-compli (3 of 5 in A4 batch) · Phase A Week 4-5
> Branch: `feat/phase-a4-compli-adapter` · Worktree: `D:\claude code\work-A4-compli`
> Status: §0.5 hard wait gate · A3 not cherry-picked yet · 不真动 ComplianceWorkspace.tsx
> Awaiting GO: `A4-COMPLI-GO-AFTER-A3` (commit on chore/l0-infra · trailer 含 A3 cherry-pick hash)
> 上次 rebase: `chore/l0-infra` @ `1c16594`

---

## 0. Wait gate evidence

```
$ git log origin/chore/l0-infra | grep -E "A3-CHANNEL-PILOT|A3-MERGED"
(empty)
```

A3 还没 DONE / cherry-pick · 我停在 draft 阶段。

---

## 1. Onboarding 6 deliverables · 现状盘点

| # | 交付 | 现状 | Phase A 行动 |
|---|---|---|---|
| 1 | `ComplianceWorkspace.tsx` 重构 4 gate (5 panel = 政策矩阵 + 违规榜单 + 修订意见 + 业务单号 + 政策事件) | 1661 行 · 仅 `started` boolean (line 88) · 缺 `selectedSession / liveData / selectedViolation` 三 gate (cat 2) | A3 GO 后照搬 A3 模式重构 |
| 2 | `agent_compliance/api.py` done event 加完整 envelope | line 121 `yield sse_encode({"event": "done"})` 空 payload (cat 4) · scan_engine 末尾 yield `{"type":"scan",scan_id,stats}` 被 api.py 丢弃 | 后端改：捕获 generator return value + 末尾 `scan` event · 拼 done envelope per spec §5.3 |
| 3 | SSE reader 改 streamSse | **已就绪** · `web/src/lib/api/compliance.ts:64` 已用 `streamSse` · `ComplianceWorkspace.tsx` 不内联 `getReader()` | ✅ pre-existing · 不需动 (delta vs A3) |
| 4 | `data/mock/workspace/compliance/scenarios/*.json` + `/api/compliance/demo/run` | dir 不存在 · endpoint 不存在 · 现有 demo 走 `tertiary_history` dropdown 内嵌 mock | 新建 dir + 3 scenario JSON + 新端点 |
| 5 | `web/tests/regression/compliance-pilot-4gate.spec.ts` smoke | 不存在 | 新建 Playwright spec · 4 gate 同步亮 + demo run + live run |
| 6 | agent_id 用 `compliance` (PM 拍板 · cat 8) · `compli` 别名保留 | frontend 已 `compliance` (`web/src/lib/agents.ts:20`) · backend `auth_service/rbac.py:42` `compli` · `web/src/lib/auth/agent-id.ts` 双 id 补丁 | 等 A1 V2 SSOT 落 `agent-naming-ssot.md` 后同步 · 删 `agent-id.ts` 补丁 · 留 RBAC `compli` 别名 |

---

## 2. Done envelope contract (deliverable #2 详细设计)

### 2.1 现状 (cat 4)

`api.py:_policy_scan_event_stream`（line 100）只 forward stage events 然后 hardcode `yield sse_encode({"event": "done"})`。scan_engine 最后 yield `{"type":"scan", "scan_id":sid, "stats":payload["stats"]}` 被 forward 成 `{"event":"stage", "payload":{"type":"scan",...}}`，前端无法判别"done"。

### 2.2 V2 envelope (per agent-compli-spec §5.3 + workspace-state-protocol)

```jsonc
// event: done
{
  "event": "done",
  "payload": {
    "scan_id": "compli-20260429-XXXX",
    "mode": "live | mock | fallback_tavily",
    "summary": {
      "rule_count": 68,
      "event_count": 145,
      "cell_count": 9860,
      "severe": 5,
      "normal": 8,
      "observation": 12,
      "duration_seconds": 158
    },
    "violations": [<ViolationRecord>...],   // 含 evidence_chain + recommendation + responsible_depts + deadline
    "rules_preview": [<RuleItem>...5],      // 头 5 条规则 · 给前端 Hero 展示
    "events_preview": [<EventItem>...5],
    "data_source": "cbirc | gov_cn | pbc | tavily_fallback | mock",
    "policy_meta": {"title": "...", "source_url": "...", "fetched_at": "..."}
  }
}
```

### 2.3 实装路径

`api.py:_policy_scan_event_stream` 改：
1. 记 `last_scan_event = None`
2. 循环里若 `evt.get("type") == "scan"` → `last_scan_event = evt` 不 forward 成 stage
3. 循环结束后从 `load_scan_result(last_scan_event["scan_id"])` 拉完整 payload
4. 拼 `done_payload` 含 §2.2 字段 → `yield sse_encode({"event":"done","payload":done_payload})`

错误路径：scan event 缺失 → done payload `{"scan_id": "", "summary": null, "error": "scan not persisted"}` + 单独 error event。

---

## 3. 4-gate state model (deliverable #1 详细设计)

照 A3 channel 模板 · 适配 compliance 5 panel：

```typescript
// 现 (1 gate):
const [started, setStarted] = useState(false);

// 目标 (4 gate · per agent-compli-spec §7.1 + A3 onboarding):
const [started, setStarted] = useState(false);              // gate 1: kicked off
const [selectedSessionId, setSelectedSessionId] = useState(MOCK_SESSIONS[0].session_id);  // gate 2
const [liveData, setLiveData] = useState<ComplianceDoneEnvelope | null>(null);            // gate 3 · 来自 done event
const [selectedViolationId, setSelectedViolationId] = useState<string | null>(null);      // gate 4

// 衍生 view state (不 hoist · panel 内部):
const [view, setView] = useState<"by_violation" | "by_clause" | "by_event">("by_violation");
const [mode, setMode] = useState<"mock" | "live">("live");
const [scanProgress, setScanProgress] = useState<ScanProgress | null>(null);
```

### 3.1 5 panel 全派生自 result

| Panel | 数据派生 | 切 session 重渲 | 选 violation 联动 |
|---|---|---|---|
| 政策矩阵 (`PolicyMatrix`) | `liveData.violations` × `liveData.rules_preview` 交叉 | ✓ | — |
| 违规榜单 (`ViolationList`) | `liveData.violations` 按 severity 三段分组 + view tab | ✓ | — |
| 修订意见 (`RevisionDraft`) | `selectedViolationId → liveData.violations.find(...).revisions` | ✓ | ✓ |
| 业务单号 (`ViolationDetail`) | `selectedViolationId → ...events` (event_id 卡片) | ✓ | ✓ |
| 政策事件 (`PolicyTicker`) | `liveData.policy_meta` + 历史 `policy_scan` 拉 | ✓ | — |

### 3.2 三 trigger 路径全归 4 gate

| Trigger | 流程 | gate 影响 |
|---|---|---|
| Primary `triggerPolicyScan` (上传政策 · 真接 SSE) | done 事件回填 `liveData` + `setStarted(true)` + 自动选 violations[0] → `selectedViolationId` | started=yes, mode=live, liveData=full, selectedViolation=auto |
| Secondary `triggerTemplateCheck` (matrix_check 同步) | 不写 `liveData` (matrix_check 返简 JSON 非 envelope) · 仅 banner 提示 | started=yes, mode=live, liveData=null |
| Tertiary `tertiary_history` (dropdown demo) | 走 `/api/compliance/demo/run?scenario=demo-online-loan` SSE → done 同样回填 | started=yes, mode=mock, liveData=full, banner=demo |

---

## 4. Mock scenarios + demo/run (deliverable #4 详细设计)

### 4.1 文件结构

```
data/mock/workspace/compliance/scenarios/
├── compli-online-loan-001.json    # 互联网贷款 · 5/8/12 (主 demo)
├── compli-aml-001.json             # 反洗钱 · 3/7/8
└── compli-data-protect-001.json   # 个人信息保护 · 2/6/10 (Wave 2 备)
```

每个文件 = 完整 done envelope shape (§2.2) · 直接 `yield` 出去无需后端运算。

### 4.2 端点

```python
# agent_compliance/api.py 新增
@app.post("/api/compliance/demo/run")
async def compliance_demo_run(req: DemoRunRequest):
    """SSE · 重放预置 scenario · stage events 用固定时间轴模拟 + done 直接出。"""
    # body: {scenario: "compli-online-loan-001"}
    # 加 data_source: "mock_scenario" 标记
```

stage events 模拟节奏：rule_extract 200ms → event_extract 300ms → matrix_match 500ms → done。前端 4 gate 走完整流程，不是 instant fill (per empty-state-design-protocol "training mode banner 必显")。

---

## 5. agent_id 统一 (deliverable #6 详细设计)

PM 已拍板 (conflict-register §拍板 1 + cat 8)：**全栈用 `compliance`**。

| 文件 | 现状 | 动作 |
|---|---|---|
| `web/src/lib/auth/agent-id.ts` | 双 id 补丁 (line 1-18) | **整文件删** · 等 A1 SSOT 落地 |
| `web/src/components/shell/AuthGate.tsx:21` | regex 允许 `compli` 不允许 `compliance` | 改 regex 用 `compliance` |
| `auth_service/rbac.py:42` | `VALID_AGENTS` 含 `compli` | 加 `compliance` 进 list · `compli` 保留作 alias (RBAC backwards compat) |
| `auth_service/users.py` | `compliance_officer` role | 不动 (不是 agent_id) |
| `evaluation/agent5_compliance.yaml:3` | `agent: compliance` ✅ | 不动 |

**等 A1 V2 SSOT** (`docs/contracts/agent-naming-ssot.md`) 落地后再触发 · 不在 A3 cherry-pick 之前动。

---

## 6. PRESERVES 清单 (cat 11-5 · features-inventory ID 待 PM 确认)

A3 GO 后真动 ComplianceWorkspace.tsx 时 commit trailer 必含：

```
PRESERVES: F-policy-matrix, F-policy-ticker, F-evidence-trail, F-compli-live-fail-banner
NEW-DOM: data-testid="compli-pilot-..."  (4 gate 关键 DOM · spec 待写)
SMOKE-PASS: web/tests/regression/compliance-pilot-4gate.spec.ts
```

**红线 PRESERVE** (本 worker 必不破)：
- `compliance-live-fail-banner` (cat 11-5 · Codex Keep · 现 ComplianceWorkspace.tsx:304-342) · live fail 时显 banner + retry · 不允许 silent swap mock
- `compliance-demo-banner` (training mode 黄色 banner · ComplianceWorkspace.tsx:291-302)
- `EvidenceProvider` + `EvidenceTrail` + `UnfilledFields` (line 251-254) · Evidence-First 协议入口
- `data-testid="compli-workspace"` 根 div + `data-started` / `data-trigger` 属性

---

## 7. 不在范围 (Phase A thin adapter 之外 · 后续 Stage C 干)

- ❌ 17 capability (C1-C17) 全实装 · 我只做 4-gate + done envelope
- ❌ `/api/compliance/upload_kb` 三槽位真接 (C1) · 现走 hardcode policy_doc
- ❌ cbirc 政策源替换 Tavily (C14) · 是 A2 共享 sources 的事
- ❌ `export_xlsx` / `export_pdf` (C11/C13 · cat 13) · 后续 batch
- ❌ 误报标记 (C16) / LLM 缓存 (C15)
- ❌ `prompts.py` 加 source_text 溯源 (cat 6)
- ❌ `scan_engine.py` Caller 5 dup init 重构 (cat 7)
- ❌ `/path` 字段 6 处指 legacy (cat 9 · A1 干)

---

## 8. 红线复述 (onboarding §3)

- ❌ A3 cherry-pick 前真动 ComplianceWorkspace.tsx (本 doc 即遵循)
- ❌ commit 不带 `Signal:` trailer
- ❌ 改 `web/*` 不带 `PRESERVES: F-XXX` + `NEW-DOM:` + `SMOKE-PASS:`
- ❌ 跨 worktree
- ❌ 直接 push origin
- ❌ 破 live fail banner (cat 11-5 Codex Keep)

---

## 9. ACK plan

| 阶段 | Signal | Trailer 含 |
|---|---|---|
| Pre-A3 | 本 commit (`A4-COMPLI-DRAFT-LANDED`) | DRAFT-PATH: `docs/audit/A4-compli-draft.md` |
| Post-A3 GO · backend done envelope | `WORKER-A4-COMPLI-DONE-ENVELOPE-LANDED` | DONE-ENVELOPE-FIELDS: scan_id/mode/summary/violations/rules_preview/events_preview/data_source/policy_meta |
| Post-A3 GO · frontend 4 gate | `WORKER-A4-COMPLI-4GATE-LANDED` | GATES-IMPLEMENTED: started/selectedSession/liveData/selectedViolation (4/4) · PANELS-DERIVED-FROM-RESULT: 5/5 · PRESERVES + NEW-DOM + SMOKE-PASS trailer 全 |
| Post-A3 GO · demo/run + scenarios | `WORKER-A4-COMPLI-DEMO-RUN-LANDED` | SCENARIOS: 3 · ENDPOINT: `/api/compliance/demo/run` |
| Post-A3 GO · agent-id sync (依赖 A1 SSOT) | `WORKER-A4-COMPLI-AGENT-ID-UNIFIED` | SSOT-CHERRY-PICK: <hash> · DELETED: `web/src/lib/auth/agent-id.ts` |
| 全完 | `WORKER-A4-COMPLI-ADAPTER-DONE` | 4 gate / done envelope / agent-id / SMOKE-PASS / PRESERVES / NEW-DOM 全 |

---

## 10. 等 GO

主 CLI cherry-pick A3 进 chore/l0-infra (commit signal `WORKER-A3-CHANNEL-PILOT-DONE` + GO commit `A4-COMPLI-GO-AFTER-A3`) 后我：

1. `git fetch origin chore/l0-infra && git rebase chore/l0-infra` 拉 A3 到我 worktree
2. 真按 §2 改 `agent_compliance/api.py`
3. 真按 §3 重构 `ComplianceWorkspace.tsx`
4. 真按 §4 建 scenarios + demo/run
5. 真按 §6 PRESERVES 跑 Playwright smoke
6. 等 A1 V2 SSOT cherry-pick → §5 agent-id 同步
7. ACK chain per §9

---

## A3 模板抄段清单

> 读 `D:\claude code\work-A3-channel-pilot` (A3 worker 私分支 · HEAD `34d890c`) · 列我 ComplianceWorkspace 抄哪些段。Cherry-pick 后**不**会自动 conflict-free，因为路径不同 (`/archive/channel/` vs `/archive/compliance/`)，但模式 1:1 复刻。

### A. 4-gate state hoist (frontend · 高优先抄)

**A3 出处**: `ChannelWorkspace.tsx:113-129`

```tsx
/* workspace-state-protocol §2 · 4 gate state model · Phase A worker-A3 (2026-04-29)
   (1) started · (2) selectedSession · (3) liveData · (4) selectedCandidate
   sessionData = liveData ?? mock[selectedSession] · 5 panel 单点派生 */

const [started, setStarted] = useState<boolean>(false);
const [selectedSession, setSelectedSession] = useState<string>(DEFAULT_SESSION_ID);
const [liveData, setLiveData] = useState<ChannelSession | null>(null);
const [selectedCandidate, setSelectedCandidate] = useState<string | null>(null);

const sessionData: ChannelSession =
  liveData ??
  MOCK_SESSIONS_MAP[selectedSession] ??
  MOCK_SESSIONS_MAP[DEFAULT_SESSION_ID];
const isLive = liveData !== null;
```

**Compliance 改造** (字段重命名 · 不复制):

| A3 channel | → | A4-compli |
|---|---|---|
| `selectedCandidate` | → | `selectedViolationId` (per agent-compli-spec §7.1) |
| `liveData: ChannelSession` | → | `liveData: ComplianceDoneEnvelope \| null` (新 type) |
| `sessionData = liveData ?? MOCK[selectedSession]` | → | 同模式 · 但 mock map 取 `MOCK_COMPLIANCE_SESSIONS_MAP` |
| 无 view state | → | 加 `const [view, setView] = useState<"by_violation"\|"by_clause"\|"by_event">("by_violation")` (compliance-only · 不在 4 gate · 衍生 UI state) |
| 无 selectedSession reset 时清 view | → | `handleSelectSession` 同步 reset view 到 `"by_violation"` 默认 |

### B. handleSelectSession (frontend · 直抄结构)

**A3 出处**: `ChannelWorkspace.tsx:215-225`

```tsx
const handleSelectSession = useCallback((id: string) => {
  const sess = MOCK_SESSIONS_MAP[id];
  if (!sess) return;
  setSelectedSession(id);
  setMessages(sess.conversation);
  setLiveData(null);
  setSelectedCandidate(null);
}, []);
```

**Compliance 改造**: 加 `setSelectedViolationId(null)` + `setView("by_violation")` reset · `setLiveData(null)` 不变 · `setMessages` 看 compliance 是否需要 conversation hoist (现 ComplianceWorkspace 没看到 · 可不抄)。

### C. normalizeBackendDone (frontend · 模式抄 · 字段全换)

**A3 出处**: `ChannelWorkspace.tsx:1368-1398` (32 行)

```tsx
function normalizeBackendDone(
  evt: Record<string, unknown>,
  tplFallback: ChannelSession,
): ChannelSession {
  const candidates = (evt.candidates as Array<Record<string, unknown>> ?? [])
    .map((c, i) => normalizeBackendCandidate(c, i));
  const radar = Array.isArray(evt.radar) && evt.radar.length > 0
    ? (evt.radar as RadarDimension[]) : tplFallback.radar;
  // ... signals/funnel 同模式
  return {
    ...tplFallback,
    id: "live",
    candidates: candidates.length > 0 ? candidates : tplFallback.candidates,
    stage: "已扫描",
    radar, signals, funnel,
  };
}
```

**Compliance 改造** · `normalizeComplianceBackendDone(evt, tplFallback)` → `ComplianceDoneEnvelope`:
- 读 `evt.violations / evt.matrix / evt.events / evt.recommendations` 4 panel keys (per `shared/sse_envelope.py:120-125 AGENT_PANEL_KEYS_RECOMMENDED["compliance"]`)
- 加 `evt.summary` (rule_count/event_count/severe/normal/observation/duration_seconds)
- 加 `evt.policy_meta` 透传给 PolicyTicker (但 PolicyTicker 主源仍是 `/policy_scan` GET · done.policy_meta 是补强)
- tplFallback 走 `MOCK_COMPLIANCE_SESSIONS_MAP[selectedSession]` (任一档 · easy 默认)

### D. streamSse + LiveFailError handling (frontend · 直抄结构 · endpoint 换名)

**A3 出处**: `ChannelWorkspace.tsx:1443-1486` (within QueryBar's `runRealSearch`)

```tsx
try {
  await streamSse(
    `${apiBase}/api/channel/run`,
    { query: queryText, mock: false, top_n: 8 },
    (sseEvt) => {
      if (sseEvt.type === "stage" && sseEvt.data.status === "warning") {
        onStreamWarning?.(`⚠️ ${sseEvt.data.message}`);
      }
      if (sseEvt.type === "done") {
        const live = normalizeBackendDone(sseEvt.data, sessionData);
        setLiveData(live);
        const wlist = sseEvt.data.warnings;
        if (Array.isArray(wlist) && wlist.length > 0) {
          onStreamWarning?.(`⚠️ ${String(wlist[0])}`);
        }
      }
    },
  );
} catch (err) {
  if (err instanceof LiveFailError) {
    onStreamError?.(liveFailBannerText(err, "Channel /api/channel/run"));
  } else {
    onStreamError?.(err instanceof Error ? err.message : String(err));
  }
}
```

**Compliance 改造**:
- 已有 `triggerPolicyScan` (line 139-169) 已用 `runPolicyScan` (`compliance.ts:53` 内部用 streamSse) ✅ **不需 inline 重写** · 但要加 done event 处理 callback (现 `runPolicyScan` 只回 `scanId` · 不回 envelope)
- `compliance.ts:53-78 runPolicyScan` 现状只捕 `evt.data.payload.type === "scan"` 取 scan_id · **改造**: 改 callback 让它收 done event 整 envelope 回 caller (signature 变 → return `{scanId, doneEnvelope}` 或加 `onDone` callback)
- LiveFailError 路径已就绪 (`recordLiveFail` line 110-129 + banner line 304-342) · **PRESERVE 不动**

### E. Backend make_done envelope (backend · 直抄模式)

**A3 出处**: `agent_channel/realtime_stream.py:247-272` + `shared/sse_envelope.py make_done`

```python
from shared.sse_envelope import (
    make_done, make_stage, make_error, encode_event,
    DATA_SOURCE_LIVE, DATA_SOURCE_MOCK_FORCED,
)

yield make_done(
    panels={
        "candidates": candidates,
        "signals": _aggregate_signal_sources(raw_signals),
        "radar": _build_radar_p50(candidates),
        "funnel": _build_funnel(...),
        "match_dimensions": _aggregate_match_dimensions(candidates),
        "product_recommendations": _aggregate_product_recommendations(candidates),
        "pitch_scripts": _aggregate_pitch_scripts(candidates),
    },
    metrics={"signalTotal": len(raw_signals), "companiesFound": ..., "final": ...},
    data_source=ds_for_envelope,
    session_id=session_id,
    warnings=warnings,
)
```

**Compliance 改造** · `agent_compliance/api.py:_policy_scan_event_stream`:

```python
from shared.sse_envelope import (
    make_done, make_stage, make_error, encode_event,
    DATA_SOURCE_LIVE, DATA_SOURCE_MOCK_FORCED, DATA_SOURCE_MOCK_FALLBACK,
    AGENT_PANEL_KEYS_RECOMMENDED,
)

# 现状: api.py:121 hardcode `yield sse_encode({"event":"done"})` 空 payload
# 改: scan_engine 末尾 yield `{"type":"scan", scan_id, stats}` 被 forward 成 stage · 截获

last_scan_id = None
for evt in run_policy_scan_and_persist(...):
    if evt.get("type") == "scan":
        last_scan_id = evt["scan_id"]
        continue  # 不 forward 成 stage · 留到 done envelope 拼
    # forward stage events as before...

if last_scan_id:
    payload = load_scan_result(scan_id=last_scan_id)
    yield encode_event(make_done(
        panels={
            "violations": payload["violations"],   # 含 evidence_chain + recommendations
            "matrix": payload["matrix"],            # rule × event 交叉
            "events": payload["events"],            # 业务单号详情
            "recommendations": _aggregate_recommendations(payload["violations"]),
        },
        metrics={
            "rule_count": payload["rule_count"],
            "event_count": payload["event_count"],
            "cell_count": payload["cell_count"],
            "severe": payload["stats"]["severe_count"],
            "normal": payload["stats"]["normal_count"],
            "observation": payload["stats"]["observation_count"],
            "duration_seconds": ...,  # 累加 stage durations
        },
        data_source=DATA_SOURCE_LIVE if has_llm else DATA_SOURCE_MOCK_FALLBACK,
        session_id=last_scan_id,
        # extras:
        rules_preview=payload["rules"][:5],
        events_preview=payload["events"][:5],
        policy_meta=payload.get("policy_meta", {}),
    ))
else:
    yield encode_event(make_error("scan not persisted", code="SCAN_PERSIST_FAILED"))
```

**注意**: `import` 路径 — A3 worktree 已有 `shared/sse_envelope.py` (A2 V2 cherry-pick 进了 A3 分支 commit `2bfc5ad`) · A4-compli 等 chore/l0-infra GO 后 rebase 拉到 · 现 A4-compli worktree 的 `shared/` 还是 V1 形态 · **不能现在写**。

### F. /api/compliance/demo/run (backend · 直抄 channel demo/run · 路径换 + 难度键换)

**A3 出处**: `agent_channel/api.py:196-282` (87 行)

A3 用 `scenario_id: "easy" | "medium" | "hard"` 三档 · 调用 `data/mock/workspace/channel/scenarios/{id}.json` · stages 走 `["parse", "signal_scan", "aggregate", "enrich", "pitch", "rank"]` 6 步 sleep 0.25s · 末尾 `make_done(panels=..., data_source=DATA_SOURCE_MOCK_FORCED, session_id=f"demo_{id}_{ts}")`。

**Compliance 改造**:
- 难度键改 `online_loan / aml / data_protect` (per agent-compli-spec §6.2) · 不用 easy/medium/hard
- stages 走 `["rule_extract", "event_extract", "matrix_match", "revision_generate"]` 4 步 (per `scan_engine.run_policy_scan_and_persist`)
- panels 4 keys (violations/matrix/events/recommendations) 直接从 scenario JSON 读
- `_SCENARIO_DIR = PROJECT_ROOT / "data" / "mock" / "workspace" / "compliance" / "scenarios"`

### G. Scenario JSON shape (data · 直抄结构 · 字段全换)

**A3 出处**: `data/mock/workspace/channel/scenarios/medium.json`

顶层字段：`scenario_id / difficulty / _lineage / stage_messages / metrics / candidates / signals / radar / funnel / match_dimensions / product_recommendations / pitch_scripts`。

**Compliance 改造**: 顶层 `scenario_id / difficulty / _lineage / stage_messages` 复用 · 数据 panel 改：
```jsonc
{
  "scenario_id": "online_loan",
  "difficulty": "中等 (68 rule × 145 event ≈ 9860 cell · 5 严重 / 8 一般 / 12 观察)",
  "_lineage": "锚定 银保监互联网贷款管理办法 · 改名改数字保量级 · 反 5 原则 §3.3+§3.4",
  "stage_messages": {
    "rule_extract": "解析 2 份政策 → 68 条规则...",
    "event_extract": "解析 3 份业务文件 → 145 条事件...",
    "matrix_match": "9860 单元 hard-rule fast path 6500 + LLM slow path 280...",
    "revision_generate": "25 条违规批量生成整改建议..."
  },
  "metrics": {"rule_count": 68, "event_count": 145, "cell_count": 9860,
              "severe": 5, "normal": 8, "observation": 12,
              "duration_seconds": 158},
  "violations": [<ViolationRecord>...],
  "matrix": [<RuleEventCell>...],
  "events": [<EventItem>...],
  "recommendations": [<Recommendation>...],
  "rules_preview": [<RuleItem>...5],
  "events_preview": [<EventItem>...5],
  "policy_meta": {"title": "...", "source_url": "...", "fetched_at": "..."}
}
```

3 档 `online_loan / aml / data_protect` · 矩阵规模与严重数依 spec §6.2 · 反 5 原则 §3.5 mock 5 硬规：盲测 / 难度分层 / 真实来源锚定 / 脱敏再造 / 环境边界（不 mock 外部政策搜·只 mock 已抓的）。

### H. Playwright smoke (test · 直抄结构 · selector 换)

**A3 出处**: `web/tests/regression/channel-pilot-4gate.spec.ts` (215 行 · 4 test)

T1 gate 1+2 · T2 gate 3 (mock SSE inject) · T3 gate 4 (drawer + ESC) · T4 banner-spec rule 2 (warning banner)。

`beforeEach` 注 localStorage `platform.auth.v1` (Zustand persist) seed `wangzhe rm` 角色 · `context.route("**/api/channel/run", inject SSE)` 模拟 SSE flat envelope。

**Compliance 改造** · `web/tests/regression/compliance-pilot-4gate.spec.ts`:
- T1 · gate 1+2 · `[data-testid="compli-session-select"]` + `compli-session-apply` → 4 panel + ConversationPanel 同步亮
- T2 · gate 3 · `**/api/compliance/policy_scan` 路由拦截 · 注入 done envelope `{violations, matrix, events, recommendations, summary, data_source: "live"}`
- T3 · gate 4 · `[data-testid="compli-violation-card"]:first-child` click → `[data-testid="compli-violation-detail"]` 出 + `RevisionDraftPanel` 联动 + ESC 关
- T4 · banner-spec rule 2 · 注入 done.warnings → `[data-testid="compli-live-fail-banner"]` 黄色 (区分 cat 11-5 红色 LiveFailError)
- T5 (compliance 加) · view tab 切换 (`by_violation / by_clause / by_event`) · 三视角无状态污染

`SEED_AUTH` 角色用 `compliance_officer` 或 `rm` (RBAC 看 A1 SSOT · 现 `auth_service/users.py` 有 `compliance_officer`)。

### I. 不抄 · A3 channel 独有

| A3 段 | 为什么不抄 |
|---|---|
| `IdealProfile12` 12 维 + KbType 3 类 (line 46-90) | F-044/F-045 · channel 独有的"先抽画像再扫"两阶段 · compliance 没有 |
| `kbIds / kbSummaries / kbStatus / kbErrors` 4 状态 (line 133-152) | 同上 · channel KB 三槽位上传 UI · compliance 上传 UI 简单 (现走 hardcode) |
| `externalTrigger` (line 162-165) | F-045 · IdealProfile card "开始扫描" external SSE trigger · compliance 不需 |
| `Radar/RadarChart/PolarGrid` recharts import (line 21-27) | channel 独有 8 维雷达 · compliance MatrixScan 是热力图 (CSS grid · 不用 recharts) |
| `pickReply / nextThinkDelayMs` canned-replies | channel 独有 IM 风对话 · compliance 也有 ConversationPanel 但已用自己的 fixtures |

### J. 抄段顺序 (post-GO 真动时)

1. **后端** (E) · `agent_compliance/api.py:_policy_scan_event_stream` 改 done envelope · scan_engine 不动 (yield 形态已对) · 跑 `pytest agent_compliance/tests` 确认无 regress
2. **后端** (F) · `/api/compliance/demo/run` 加 · scenarios/*.json 三档建 (G) · curl SSE 确认事件流
3. **前端** (A+B) · `ComplianceWorkspace.tsx` 顶层 4 gate state hoist · `handleSelectSession` 加
4. **前端** (C+D) · `normalizeComplianceBackendDone` + `runPolicyScan` callback 改 (lib/api/compliance.ts signature 扩 + ComplianceWorkspace 接 done envelope)
5. **前端 panel 改造** · 5 panel 全 props 化 (ViolationListPanel / ViolationDetailPanel / RevisionDraftPanel / PolicyMatrix / PolicyTicker) · 派生 `sessionData` 单源 · view tab hoist
6. **smoke** (H) · `compliance-pilot-4gate.spec.ts` 5 test · `npx playwright test compliance-pilot-4gate`
7. **commit chain** per §9 · 每 commit 单一职责
8. **agent-id 同步** (§5) · 等 A1 V2 SSOT 落地 · 单独 commit

### K. 与 A3 的最大差异 (compliance 独有)

| 差异点 | 影响 |
|---|---|
| **view 三视角** (`by_violation / by_clause / by_event`) | ViolationList 顶 tab 切换 · 三视角不同左栏 group 逻辑 (PRD §4.4) · A3 没有 |
| **5 panel ≠ 4 panel envelope** | 政策事件 (PolicyTicker) 数据源是独立 GET `/api/compliance/policy_scan` · 不在 done envelope 里 · live 与 demo 路径都需独立拉 |
| **streamSse 已就绪** | `compliance.ts:64` 已用 streamSse · 我不像 A3 要从 inline `getReader()` 迁 · 但 `runPolicyScan` callback signature 要扩支持 `onDone(envelope)` |
| **live fail banner 已实装** | cat 11-5 Codex Keep · A3 是新建 banner · 我是不破现有 (PRESERVES 重点) |
| **ConversationPanel** | 两边都有 · compliance 已有自己的 `COMPLIANCE_EVIDENCE` fixture · 不抄 channel 的 canned-replies |
| **drawer ESC close** | A3 是 candidate drawer · 我是 violation detail panel (中栏 · 非 drawer) · ESC 行为 = 清 selectedViolationId 不是关 drawer |
