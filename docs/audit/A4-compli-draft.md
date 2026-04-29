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
