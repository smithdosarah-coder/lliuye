# Worker-A4-credit · Pre-cherry-pick Draft

> **状态**: §0.5 硬 wait gate 进行中 · 当前 worktree `feat/phase-a4-credit-adapter` · A3 channel pilot **未** cherry-pick 进 `chore/l0-infra` · 本文是 draft 不动真代码
>
> **依赖**:
> - A3 channel pilot DONE → cherry-pick `chore/l0-infra` → 主 CLI 发 `A4-CREDIT-GO-AFTER-A3` GO 信号 (trailer 含 cherry-pick hash)
> - A6 handoff contract DONE → `docs/contracts/agent-handoff-schemas.md` 落地 ReportJSON shape (本 draft §6 EmptyState 改造的契约)
> - A2 shared infra DONE → `web/src/lib/api/_live.ts` 的 `streamSse` 可消费 (本 draft §4 cat 3 修)
>
> **Author**: worker-A4-credit · 2026-04-29 · pre-dispatch draft
>
> **Onboarding source**: `docs/onboarding/A4-credit.md` (主 CLI 写 · 仅在 `chore/l0-infra` 上 · 本 worktree 通过 `git show chore/l0-infra:docs/onboarding/A4-credit.md` 读)

---

## 0. 现状摘要 (audit-anchored)

| 维度 | 现状 (line ref) | 目标态 |
|---|---|---|
| 4 gate state | `web/src/app/archive/credit/_components/CreditWorkspace.tsx:89-116` 含 `mode/tab/progress/scanned/started/liveAdvice/decisionId/decisionRunning/decisionError` 9 useState · 缺 `selectedSession` + `selectedCandidate` 两 gate (cat 2) | 顶层 4 gate (`started` / `selectedSession` / `liveData` / `selectedCandidate`) + segment/preset 提至外层 controller hook |
| SSE 客户端 | `CreditWorkspace.tsx:157` 内联 `res.body.getReader() + TextDecoder + buf.split("\n\n")` (cat 3) | 改 `streamSse` (per `web/src/lib/api/_live.ts`) · 删 80 余行内联 reader |
| backend done envelope | `agent_credit/api.py:387` (mock 路) + `:465` (live 路) 均 `{"event": "done"}` 空载 (cat 4) · 完整 payload 在 `advising_done` event (mock L323-385 全填 / live L449-454 视 pipeline 是否到 stage 而定) | done event 携完整 envelope (符合 channel pattern · `radar/redlines/cases/advice/scoring/segment/preset/source` 全字段) · mock + live 路对称 |
| demo / live 边界 | `CreditWorkspace.tsx:199-206` `selectHistoricalDemo()` setStarted=true 但不 hit backend · 无 mock-session banner (cat 11) | demo 路独立端点 `/api/credit/demo/run` + 显式 banner |
| EmptyState handoff | `CreditWorkspace.tsx:1571-1665` `onPrimary` → `runDecision({mockMode:false})` 直调 `/api/credit/decision` · 不消费 Agent6 ReportJSON (cat 0 北极星核心) | `onPrimary` → 选 Agent6 已完成报告 list → 拉 ReportJSON → 注入 enterprise_profile → 起决策 (从"独立运行"转为"下游引擎") |
| export error | `CreditWorkspace.tsx:1784-1786` `console.error` 静默 (cat 13) | 错误展示 fallback banner |
| 共享 hook | 6 workspace 各自实现 SSE + 状态管理 | 抽 `useWorkspaceRun.ts` + `WorkspaceBanner.tsx` + `EmptyWorkspace.tsx` + `sseWorkspaceClient.ts` (其中一子 worker 兼任) |

---

## 1. 4 gate state 改造方案 (cat 2)

per `docs/contracts/workspace-state-protocol.md` §2 · A3 ChannelWorkspace pattern · credit 适配:

```tsx
// web/src/app/archive/credit/_components/CreditWorkspace.tsx
import { useState } from "react";
import { CREDIT_MOCK_SESSIONS, type CreditSession } from "@/lib/mock/agent-credit-sessions";

export default function CreditWorkspace() {
  const [started, setStarted] = useState<boolean>(false);
  const [selectedSession, setSelectedSession] = useState<string>(CREDIT_MOCK_SESSIONS[0].id);
  const [liveData, setLiveData] = useState<CreditSession | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<string | null>(null);

  const sessionData =
    liveData ??
    CREDIT_MOCK_SESSIONS.find((s) => s.id === selectedSession) ??
    CREDIT_MOCK_SESSIONS[0];

  // 推导: segment / preset 由 sessionData 决定 · 不再独立 useState
  const segment = sessionData.segment;        // "corporate" | "small_business" | "retail"
  const presetName = sessionData.preset_name;
  // ...
}
```

### 1.1 触发源 (state 写入点)

| state | 写入触发 | 拟 line ref |
|---|---|---|
| `setStarted(true)` | (a) Agent6 handoff 拉到 ReportJSON, (b) `<select>` 切到历史 demo session, (c) 演示模式 CTA, (d) live SSE 起 stream | EmptyState onPrimary/onSecondary/onTertiary + 历史下拉 onChange |
| `setSelectedSession(id)` | 历史下拉 `<select onChange>` 切 mock session id | 待加 `<select>` 元素 (借 A3 ChannelWorkspace.tsx:1059-1065 模式) |
| `setLiveData(payload)` | SSE `event === "done"` (新版 done envelope) 整体注入 | streamSse onDone callback |
| `setSelectedCandidate(id)` | `CaseTable.tsx` 行 click → setSelectedCandidate(case_id) → 弹 `CandidateDetailDrawer` (案例详情) | `_components/CaseTable.tsx` row onClick |

### 1.2 现有 state 收编

- `mode/setMode` → 由 `sessionData.segment` 派生 (sessionData 切 → segment 跟着切)
- `tab/setTab` (radar/limit/cases) → **保留** · 这是 panel 内显示 tab · 不混 gate
- `progress/setProgress` (5 步动画) → **删** · 旧"动态进度条 mock" · 真 SSE pipeline 替代
- `scanned/setScanned` → 由 `liveData != null || selectedSession != initial` 派生 · 删 useState
- `liveAdvice/setLiveAdvice` → 收编入 `liveData.advice`
- `decisionId/setDecisionId` → 收编入 `liveData.decision_id`
- `decisionRunning/decisionError` → 收编入新 `useWorkspaceRun` hook 内部 (status/error)

---

## A3 模板抄段清单 (cherry-pick 后逐段移植)

> **A3 worktree 现状** (`D:\claude code\work-A3-channel-pilot` · HEAD `4c54cf2` · A3 worker 尚未 commit final rewrite): ChannelWorkspace.tsx 已落 Phase B partial (workspace-state-protocol §1 列 gap #2/#3/#4/#5 中 #2/#3/#5 已实装) · realtime_stream.py done event 仅含 `candidates/metrics/data_source` (cat 4 提)。
>
> **A3 worker DONE 后会再补**: 4 gate 真实装收口 + done event 全 envelope (radar/signal_timeline/funnel/profile_brief/hero_summary) + `/api/channel/demo/run` 端点 + scenarios + Playwright smoke。
>
> 故 "抄段清单" 分两批: **A · 现已可抄** (Phase B 已落 · 学其形) · **B · 等 A3 final cherry-pick 后抄** (4 gate 收口 + envelope + demo 端点)。

### A. 现已可抄 (Phase B partial · pre-A3-final)

| # | A3 段落 | A3 line ref | credit 抄到哪 | 抄什么 |
|---|---|---|---|---|
| A1 | 4 gate state hoist | `ChannelWorkspace.tsx:115-134` (`selectedSessionId` / `liveCandidates` / `started` / `selectedCandidateId` 4 useState 顺序 + 注释引 protocol §2) | `CreditWorkspace.tsx` 顶层 (替 89-116 当前 9 useState) | useState 4 行 + comment 引 `workspace-state-protocol.md §2` 行号 |
| A2 | sessionData 派生 | `ChannelWorkspace.tsx:116-118` (`MOCK_SESSIONS_MAP[selectedSessionId] ?? MOCK_SESSIONS_MAP[DEFAULT_SESSION_ID]`) | credit 顶层派生 sessionData | `liveData ?? CREDIT_MOCK_SESSIONS.find(...) ?? CREDIT_MOCK_SESSIONS[0]` 三段 fallback (workspace-state-protocol §2 推荐式) |
| A3 | selectedCandidate 派生 + ESC 关 drawer | `ChannelWorkspace.tsx:182-197` (selectedCandidate `find` + useEffect ESC keydown) | credit `CaseTable` row click drawer | 复制 ESC 关 drawer effect 整段 · 仅改 setter 名 (`setSelectedCandidate`) |
| A4 | handleSelectSession 切清 callback | `ChannelWorkspace.tsx:206-216` (切 session 时 reset conversation + setLive(null) + setSelectedCandidate(null)) | credit 历史下拉 onChange | 切 sessionData 时同步清 liveData + 关 drawer · 否则 panel 串 session 数据 |
| A5 | backend candidate normalize | `ChannelWorkspace.tsx:1196-1346` `normalizeBackendCandidate` (snake_case → camelCase · 兼容 backend `signals/match_dimensions/product_recommendations/pitch_scripts`) | credit `_components/_normalize.ts` | 学**结构** (映射函数 + fallback 链 + drawer 三件套展开) · 不学**字段** (credit 字段是 `scoring_result/rule_hits/case_matches/advice` · 重新映) |
| A6 | runRealSearch SSE pattern (反模式 · 学反例) | `ChannelWorkspace.tsx:1379-1446` 内联 `res.body.getReader() + buf.split("\n\n")` | (不抄) | **明确不抄** · 这是 cat 3 反模式 · credit 直接走 streamSse (本 draft §4) · A3 worker final 也会改 |
| A7 | "切换演示" click-to-fire pattern | `ChannelWorkspace.tsx:1448-1461` (pendingSessionId 临时 state + 显式 button apply 才切) | credit 历史下拉 (可选) | 若 PM 要求"下拉选完再 click apply"才切 · 抄此 pattern · 否则 onChange 直切 |

### B. 等 A3 final cherry-pick 后抄 (A3 worker DONE 才有)

| # | A3 段落 | 预期 line | credit 抄到哪 | 抄什么 | 何时可抄 |
|---|---|---|---|---|---|
| B1 | 4 gate 真收口 (workspace-state-protocol §2 全照搬 · 现有 partial 收齐) | (待 A3 worker 改) | credit 顶层 4 useState 收口 | 收编后的 4 gate 顺序 + 派生函数 + `setStarted` 写入触发源四类完整 | A3 commit `WORKER-A3-CHANNEL-PILOT-DONE` cherry-pick 后 |
| B2 | done event 全 envelope (cat 4) | `realtime_stream.py:228-237` 改 (加 `radar / signal_timeline / funnel / profile_brief / hero_summary`) | `agent_credit/api.py:387 + :465` `_build_done_envelope` | 学**字段命名规约** (snake_case · 顶层平摊 · 不嵌 stage_xxx) · credit 字段表本 draft §3 已列 | A3 cherry-pick 后 |
| B3 | streamSse 消费 done envelope 整体 setLiveData | A3 worker final 会替 `ChannelWorkspace.tsx:1422-1433`(只取 candidates) 为整体注入 | credit `streamSse onEvent → if "done" setLiveData(normalize(evt))` | 学整体注入模式 · 不再分 stage 累积本地 state | A3 cherry-pick 后 |
| B4 | `/api/channel/demo/run` 端点 + `data/mock/workspace/channel/scenarios/*.json` | A3 worker 新建 | credit 镜像建 `/api/credit/demo/run` + `data/mock/workspace/credit/scenarios/*.json` × 6 (本 draft §5) | 学端点签名 + scenarios JSON shape (`{sse_script: [{event, stage, payload, delay_ms}]}`) | A3 cherry-pick 后 |
| B5 | Playwright `web/tests/regression/channel-pilot-4gate.spec.ts` | A3 worker 新建 | credit 镜像建 `credit-pilot-4gate.spec.ts` (本 draft §7) | 学 5 case 结构 (empty / mock-switch / live-sse / handoff / drawer) + selector 模式 (`data-testid="channel-pilot-..."` → `credit-pilot-...`) | A3 cherry-pick 后 |
| B6 | live-fail banner 实装 (cat 11 #11) | A3 worker 改 (Tavily key 缺时显式 banner · 不再 silent mock_fallback) | credit `WorkspaceBanner.tsx` 共享组件 (若公共 hook 兼任 worker 先落) | 学 banner DOM + i18n + retry/dismiss action | A3 cherry-pick 后 (或公共 hook worker 先) |

### C. credit 与 A3 不一样 · 不能照抄 (避免误抄)

| 域 | A3 (channel) | credit | 备注 |
|---|---|---|---|
| 5 panel 内容 | RadarPanel / FunnelStrip / CandidatesPanel / SignalTimelinePanel / ConversationPanel | 3 segment panel + RadarScore + DecisionLetter (本 draft §2 拟) | 完全不同 · 仅借 "panel 接 sessionData props" 模式 |
| mock session 字段 | `benchmark / signals / candidates / radar / funnel / conversation / qcCounts / candidateCount / stage / recentSessions` | `enterprise_profile / scoring_result / rule_hits / case_matches / advice / personal_profile (retail)` (per agent-credit-spec §6) | shape 完全不同 · 仅借 array shape (≥6 sessions / 难度分层) |
| KB upload 流 | `upload_kb` 多 type · IdealProfile 12 维抽取 (`F-044/F-045`) | credit 不需 KB upload · 输入是 Agent6 ReportJSON | 完全不抄 |
| 候选 drawer | `CandidateDetailDrawer` (radar+signals + match dim + products + pitch_scripts 4 区) | credit 候选概念 ≠ channel · drawer 是 case 详情 (similarity / hit_red_lines / decision / approved_amount) | 学 drawer 整体架构 · 不学内容 |
| backend 上游 | Tavily 实搜 + 企查查 enrich + DeepSeek pitch | DeepSeek + Agent6 ReportJSON 透传 + 内部 features/scoring/rules/cases pipeline | 完全不同 |
| ConversationPanel 接 IM | 接 `archive:channel` thread → `/api/im/send target_agent="channel"` | credit 已有 ConversationPanel · 接 `archive:credit` thread (现状 OK · 保留) | 不动 |

### D. 抄段实施顺序 (cherry-pick 后)

1. A1 → 顶层 4 useState 替 (commit 2 of 实施顺序)
2. A2 → sessionData 派生 (同 commit)
3. A3 → ESC 关 drawer effect (commit 8)
4. A4 → handleSelectSession 切清 (commit 2)
5. A5 → normalize 函数学结构 · 字段重映 (commit 5 之 normalize.ts)
6. A6 → 不抄 · 直接 streamSse (commit 5)
7. A7 → 视 PM 决定是否需要 click-to-apply
8. B1 → 与 A1 合并 · A3 final 收口后再 align (commit 2 修一次)
9. B2 → backend done envelope 镜像 (commit 4)
10. B3 → streamSse done 整体 setLiveData (commit 5)
11. B4 → demo 端点 + scenarios (commit 6)
12. B5 → Playwright spec 镜像 (commit 10)
13. B6 → live-fail banner 学 (合并入 §8 公共 hook 或本 worker 实装)

---

## 2. 5 panel 派生方案 (corp/small/retail × radar/score)

per onboarding §1 #1: "credit 5 panel 是 corp/small/retail 三 segment + radar + score · 不是 channel 5 panel"。

**解读** (待 PM verify · 见 §10 open questions):
- 3 segment-conditional panel: `<CorporatePanel>` / `<SmallBusinessPanel>` / `<RetailPanel>` · 按 `segment` switch render
- 2 cross-segment panel: `<RadarScore>` / `<DecisionLetter>` (score)

```tsx
function CreditPanels({ sessionData }: { sessionData: CreditSession }) {
  return (
    <>
      {sessionData.segment === "corporate" && <CorporatePanel sessionData={sessionData} />}
      {sessionData.segment === "small_business" && <SmallBusinessPanel sessionData={sessionData} />}
      {sessionData.segment === "retail" && <RetailPanel sessionData={sessionData} />}
      <RadarScore sessionData={sessionData} />
      <DecisionLetter sessionData={sessionData} />
    </>
  );
}
```

### 2.1 现有 panel inventory (`agent-credit-spec.md` §7)

| Panel | segment | data 来源 | drawer-aware |
|---|---|---|---|
| `ProfileSummary.tsx` | both | `sessionData.enterprise_profile` | — |
| `StageTabs.tsx` | both | sessionData.stage 状态灯 | — |
| `RadarScore.tsx` (corporate) / `ScorecardBars.tsx` (retail) | seg-split | `sessionData.scoring_result.sub_scores` | — |
| `IndustryBench.tsx` | corporate | `sessionData.feature_map` + `industry_baselines` | — |
| `CaseTable.tsx` | corporate | `sessionData.case_matches` Top 5 | ✓ row onClick → drawer |
| `AmountChart.tsx` | corporate | `sessionData.amount_calculations` | — |
| `CreditSnapshot.tsx` / `CollateralPanel.tsx` / `GradeMatrix.tsx` | retail | `sessionData.personal_profile.*` | — |
| `RedLinesPanel.tsx` | both | `sessionData.rule_hits` | — |
| `DecisionLetter.tsx` | both | `sessionData.advice` | — |
| `RiskRadarPreview.tsx` (Wave 2 · 不许移除) | both | `sessionData.risk_radar_data` · `[data-scanned]` gate | — |
| `HandoffButtons.tsx` | both | session_id + segment + advice | — |
| `EvidenceTrail.tsx` (Wave 2 · 不许移除) | both | evidence refs | — |

**红线**: Wave 2 落地的 `RiskRadarPreview` + `EvidenceTrail` 不许移除 (per Q-033 + decisions-log)。

### 2.2 panel 接 props · 禁止 inline import

参 `workspace-state-protocol.md` §2.2 反模式 · credit 现有 1860 行单文件需拆 panel 子组件 · 每 panel 接 `{ sessionData: CreditSession }` props · 禁 `import { CREDIT_SESSIONS } from "@/lib/mock/agent-credit-session"` 的旧单 const 模式。

---

## 3. backend done envelope 对称修复 (cat 4)

### 3.1 当前不对称

| 路径 | line | done payload | advising_done payload |
|---|---|---|---|
| mock | `agent_credit/api.py:387` | `{"event":"done"}` 空 | L323-385 完整 (4 stage 全填) |
| live | `agent_credit/api.py:465` | `{"event":"done"}` 空 | L449-454 视 pipeline 是否 advance 到 advising stage 而定 (可能缺) |

### 3.2 拟方案

```python
# agent_credit/api.py · 两路统一 done envelope
def _build_done_envelope(
    *, segment: str, preset_name: str, source: str,
    profile: dict, scoring: dict, rules: list, cases: list, advice: dict,
    decision_id: str | None,
) -> dict:
    return {
        "event": "done",
        "segment": segment,
        "preset_name": preset_name,
        "source": source,                      # "mock" | "agent6_handoff" | "agent1_handoff" | "manual"
        "decision_id": decision_id,
        "profile": profile,                    # enterprise_profile / personal_profile
        "scoring": scoring,                    # composite_score + sub_scores
        "rule_hits": rules,                    # red lines
        "case_matches": cases,                 # Top 5
        "advice": advice,                      # decision + amount + term + rate + reason
    }
```

mock 路 (L387) 和 live 路 (L465) **都** yield 该完整 envelope。前端 `setLiveData` 时 normalize 一次性灌满 panel (无需各 stage 累积本地 state)。

### 3.3 兼容性

- 现有 `event: "stage"` 流式 events **保留** (UI 阶段灯 + 流式提示需要)
- 仅 `event: "done"` 加字段 · 不破 stage event schema
- 前端旧 reader 容忍未知字段 · 但因本 PR 同时改前端走 streamSse · 旧 reader 删

---

## 4. SSE 客户端切 streamSse (cat 3)

`CreditWorkspace.tsx:157-191` 共 35 行内联 reader · 改:

```tsx
import { streamSse } from "@/lib/api/_live";

await streamSse({
  url: `${apiBase}/api/credit/decision`,
  body: { stage_tab, mock, preset_name, enterprise_profile },
  onEvent: (evt) => {
    if (evt.event === "stage") setStageProgress(evt);
    if (evt.event === "done") setLiveData(normalize(evt));
    if (evt.event === "error") setError(evt.message);
  },
  onDone: () => setRunning(false),
});
```

- 该 streamSse 工具是 cat 3 的 SSOT · A2 onboarding 已 mandate 6 workspace 强制消费
- normalize 函数在新增 `_components/_normalize.ts` · 把 backend snake_case → 前端 camelCase

---

## 5. demo 路独立端点 + scenarios

per onboarding §1 #4:

### 5.1 backend

```python
# agent_credit/api.py
@router.post("/api/credit/demo/run")
async def credit_demo_run(req: CreditDemoRequest):
    """Demo 路 · 不调 LLM · 直接 yield SSE 从 data/mock/workspace/credit/scenarios/<scenario>.json 读"""
    scenario_path = Path("data/mock/workspace/credit/scenarios") / f"{req.scenario_id}.json"
    if not scenario_path.exists():
        raise HTTPException(404, f"scenario {req.scenario_id} not found")
    payload = json.loads(scenario_path.read_text("utf-8"))
    async def stream():
        for evt in payload["sse_script"]:
            yield sse_encode(evt)
            await asyncio.sleep(evt.get("delay_ms", 250) / 1000)
    return StreamingResponse(stream(), media_type="text/event-stream")
```

### 5.2 scenarios fixture

`data/mock/workspace/credit/scenarios/*.json` 至少 6 个 (3 corp + 3 retail · 复用 `agent-credit-spec.md` §6.2 标杆):
- `corp-dingsheng-001.json` · D 级 · 高负债 + 关联方双红线 · 批拒边界
- `corp-ruiheng-002.json` · A 级 · 直接批 300 万
- `corp-zhongrui-003.json` · B 级 · 关联交易软红线 · 有条件批
- `retail-zhangsan-001.json` · 720 良好 · 批 50 万
- `retail-lisi-002.json` · 695 边界 · 红线 · 人工复核
- `retail-wangwu-003.json` · 810 优 · 批 200 万

### 5.3 banner 显式标 demo

EmptyState tertiary CTA → `/api/credit/demo/run` · live banner 显:
> 当前为演示模式 · 数据来自 mock scenario `<scenario_id>` · 切真实输入或 Agent6 handoff 随时返回

---

## 6. Agent6 handoff EmptyState 改造 (cat 0 北极星核心)

### 6.1 当前问题

`CreditWorkspace.tsx:1620-1635` `onPrimary` "选材料 + 起决策" → `onClick={p.onPrimary}` 仅调 `runDecision({mockMode:false})` · 直接 hit `/api/credit/decision` · 用 hardcoded `presetByMode[mode]` (L140-144) · **不消费** Agent6 ReportJSON。

注释 L1633 "从 Agent6 handoff 拉报告" 是承诺未兑现。

### 6.2 拟改造 · 真消费 ReportJSON

```tsx
async function onPrimary() {
  // 1. 拉 Agent6 已完成报告 list (依赖 A6 handoff schema · 待 A6 DONE)
  const reports = await fetch("/api/report/sessions?status=done").then(r => r.json());
  // 2. 弹模态选 session
  const sessionId = await openReportPicker(reports);
  if (!sessionId) return;
  // 3. 拉 ReportJSON · 注入 enterprise_profile
  const handoff = await fetch(`/api/credit/handoff/from_report`, {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  }).then(r => r.json());
  // 4. 起决策 · stage_tab + enterprise_profile 透传
  setStarted(true);
  await streamSse({
    url: "/api/credit/decision",
    body: {
      stage_tab: stageTab,
      mock: false,
      enterprise_profile: handoff.enterprise_profile,
      report_session_id: sessionId,
    },
    onEvent: ...,
    onDone: ...,
  });
}
```

### 6.3 EmptyState UI 改

```diff
- <span className="credit-empty__cta-title">选材料 + 起决策</span>
- <span className="credit-empty__cta-sub">从 Agent6 handoff 拉报告 · 真接 LLM SSE</span>
+ <span className="credit-empty__cta-title">从 Agent6 报告起决策</span>
+ <span className="credit-empty__cta-sub">选已完成报告 · 自动注入企业画像 · LLM SSE 决策</span>
```

二级 CTA "演示模式起决策" 保留 · tertiary "历史 (示例)" 改走 §5 demo 端点。

### 6.4 Banner 显示 handoff 来源

per `agent-credit-spec.md` §2 C2: 顶部横幅"已从 Agent6 加载 [企业名] 报告（生成于 ...）" · 在 `<CreditWorkspaceHeader>` 加 `data-source="agent6_handoff"` 渲染。

### 6.5 fallback (Agent6 schema 未到位)

A6 worker DONE 前 · `/api/credit/handoff/from_report` 端点可能未实装 · pre-cherry-pick 阶段:
- 先用 `agent-credit-spec.md` §3 + `data/handoff/channel_to_credit/` 现有 enterprise_profile sample 兜底
- A6 schema 落地后 (`docs/contracts/agent-handoff-schemas.md` · A6.report_json → A3.decision_input) 再对齐字段

---

## 7. Playwright smoke 设计

`web/tests/regression/credit-pilot-4gate.spec.ts` (新) · ≥ 5 case:

| # | case | 验证点 |
|---|---|---|
| 1 | empty state initial | `data-testid="credit-empty-skeleton"` 可见 · 3 CTA 排齐 · panel 区 skeleton 不显示真数字 |
| 2 | history demo 切 session | 下拉切 corp-dingsheng → corp-ruiheng · 4 维分 + 红线 + 案例 表全切 (不残留前一 session 数字) |
| 3 | live decision SSE | 演示模式 CTA → POST `/api/credit/decision?mock=true` → 收 7 个 stage event · 收 done envelope · panel 全 hydrate |
| 4 | Agent6 handoff path | mock A6 ReportJSON list (1 entry) → onPrimary → pick → handoff loaded banner 显 · enterprise_profile 注入 SSE 请求 body |
| 5 | case row drawer | CaseTable row click → setSelectedCandidate → drawer 弹 case 详情 (similarity / hit_red_lines / decision) · ESC 关 |

附加 (cat 11/13):
- live-fail banner (mock fallback 显式)
- export_docx fail toast 显 (取代 console.error 静默)

---

## 8. 共享 hook 抽出 (workspace 共用)

per onboarding §1 #5 · A4 5 子 worker **其中一个兼任**抽公共 hook · 拟:

```
web/src/app/archive/_shared/
  ├ useWorkspaceRun.ts      // SSE 起 / done / error / cancel · 统一 status state
  ├ WorkspaceBanner.tsx     // top banner (demo 路 / live 失败 / handoff 加载)
  ├ EmptyWorkspace.tsx      // 6 agent 共用 empty skeleton 框架
  └ sseWorkspaceClient.ts   // streamSse wrapper · normalize callback 注入
```

**Credit 不兼任**抽 hook 任务 · 由 5 子 worker 中先 ready 的兼任。本 worker 只:
- 等公共 hook 落地后 import 使用 · 不重新发明
- 若公共 hook 比 credit 实装早 · credit 直接用
- 若 credit 比公共 hook 早 · credit 实装本地版 · 留 TODO comment "// TODO: migrate to _shared/useWorkspaceRun once landed"

---

## 9. 实施顺序 (DoD-anchored)

| # | 步骤 | 文件 | 验证 | 独立 commit |
|---|---|---|---|---|
| 1 | 等 A3 cherry-pick 进 `chore/l0-infra` + 主 CLI `A4-CREDIT-GO-AFTER-A3` 信号 | (无) | git log grep | (无) |
| 2 | `git rebase chore/l0-infra` 拉 A3 模板 + A2 streamSse + A6 handoff schema | (无) | rebase 干净 | rebase commit |
| 3 | 新建 `web/src/lib/mock/agent-credit-sessions.ts` · ≥ 6 session (3 corp + 3 retail) · 反 5 原则 #2 难度分层 | new file | tsc 0 error | commit 1 |
| 4 | `CreditWorkspace.tsx` 加 4 gate state + sessionData 派生 | edit | tsc + 视觉无回归 | commit 2 |
| 5 | 拆 panel 子组件 · 各接 `{ sessionData }` props · 删 inline `CREDIT_SESSIONS[mode]` 直读 | new files in `_components/` | 切下拉 panel 全切 | commit 3 |
| 6 | `agent_credit/api.py` done envelope 对称修复 (mock + live 路 yield 完整 envelope) | edit | curl `/api/credit/decision` done event 字段全 | commit 4 |
| 7 | `CreditWorkspace.tsx` SSE reader 切 streamSse · 删 35 行内联 reader | edit | tsc + decision SSE 通 | commit 5 |
| 8 | 新建 `data/mock/workspace/credit/scenarios/*.json` × 6 + `/api/credit/demo/run` 端点 | new file + edit | curl demo 端点 SSE 通 · 6 scenario 各跑通 | commit 6 |
| 9 | EmptyState onPrimary 改 Agent6 handoff 路径 (依赖 A6 schema · 见 §6.5 fallback) | edit | mock A6 list → pick → handoff banner 显 + enterprise_profile 透传 | commit 7 |
| 10 | CaseTable row click → drawer (selectedCandidate gate) | edit | row click drawer 弹 + ESC 关 | commit 8 |
| 11 | export_docx 失败 banner 替 console.error (cat 13) | edit | 模拟 export 404 → banner 显 | commit 9 |
| 12 | `web/tests/regression/credit-pilot-4gate.spec.ts` ≥ 5 case | new file | playwright 通 | commit 10 |
| 13 | features-inventory.md 加 F-credit-* + DONE commit + trailer 全字段 | edit | trailer 验过 | commit 11 (DONE) |

每步独立 commit · 每步跑 `cd web && npx tsc --noEmit` + 视觉 smoke。

---

## 10. Open questions / 待 PM 拍板

| Q | 问题 | 拟答 |
|---|---|---|
| Q1 | "5 panel = corp/small/retail × radar/score" 的精确解读 | 拟 §2 "3 segment panel + RadarScore + DecisionLetter = 5" · 待 PM verify |
| Q2 | A6 handoff schema 何时 ready | A6 worker DONE signal 后 · 同步进度看 mesh.json A6 状态 |
| Q3 | EmptyState onPrimary 与 Agent6 list 拉法 | 是否新增 `/api/report/sessions?status=done` 端点 · 还是用现有 sessionStorage 透传 (`agent-credit-spec.md` §3 触发源 2 · sessionStorage `enterprise_profile`) |
| Q4 | `legacy_gradio` 全栈隔离 (decisions-log Q-031) 对 credit 影响 | credit 不依赖 gradio · 视为零影响 · 仅需保证 import 不破 |
| Q5 | small_business segment 数据契约 | spec §6.2 仅 corporate + retail · onboarding "corp/small/retail" 多了 small · 现有 `MODE_TO_STAGE_TAB` 已 `small → small_business` · mock data shape 待补 |
| Q6 | RiskRadarPreview / EvidenceTrail Wave 2 不许移除红线如何 reconcile 4 gate 改造 | panel 拆分时 · 这两 panel 接 `sessionData.risk_radar_data` + `evidence` props · 不动其内部实现 |

---

## 11. 红线 self-check (per onboarding §3)

| 红线 | self-check |
|---|---|
| ❌ 不跨 worktree | ✓ 本 draft 仅写 `D:\claude code\work-A4-credit\docs\audit\A4-credit-draft.md` |
| ❌ commit 无 Signal trailer | ✓ 待提交 commit 拟 `Signal: A4-CREDIT-DRAFT-PREPARED` |
| ❌ 改 web/* 必带 PRESERVES + NEW-DOM + SMOKE-PASS | ✓ 本 draft 不动 web/* · 真改时 trailer 按 onboarding §4 模板填 |
| ❌ A3 cherry-pick 之前真动 CreditWorkspace.tsx | ✓ 本 draft 不动该文件 |
| ❌ 重新发明 4 gate | ✓ 本 draft §1 严格 follow `workspace-state-protocol.md` §2 模型 + A3 ChannelWorkspace pattern |

---

## 12. ACK 路径

- 本 draft commit `Signal: A4-CREDIT-DRAFT-PREPARED` (worker A4-credit pre-dispatch)
- 等主 CLI:
  - A3 cherry-pick 进 `chore/l0-infra`
  - 发 `A4-CREDIT-GO-AFTER-A3` GO 信号 commit (含 A3 cherry-pick hash trailer)
- GO 后按 §9 实施顺序逐步 commit · 末 commit `Signal: WORKER-A4-CREDIT-ADAPTER-DONE` 携 onboarding §4 全 trailer

---

**End of draft** · 一切待 GO 信号 · 不真动 CreditWorkspace.tsx
