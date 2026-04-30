# Worker-A3 · Channel Pilot Design Draft (wait-gate read+draft pass)

> Status: **PRE-WORK · 软 wait gate** · A1 V2 (`db2f2b4`) + A2 V2 (`114b562`) 都未 cherry-pick 进 `feat/phase-a3-channel-pilot` · 主 CLI `A3-GO-AFTER-A1-A2-V2` 信号未发。
>
> 本 doc = worker-A3 在 wait-gate 期 read+draft 产物 · 不动 `ChannelWorkspace.tsx` / `realtime_stream.py` / 任何 prod 代码 · 等 GO 后按本 plan 开干。
>
> Author: worker-A3 · 2026-04-29
> Related: `docs/onboarding/A3-channel-pilot.md` · `docs/contracts/workspace-state-protocol.md` v1.1 · `docs/contracts/sse-envelope.md` v1.0 (未 cherry-pick · 通过 sibling branch 阅读) · `shared/sse_envelope.py` (A2 V2 · 未 cherry-pick) · `docs/contracts/live-fallback-banner-spec.md` v1.0

---

## 0. Wait-gate verify (做了 5 件事)

1. ✅ `git log feat/phase-a3-channel-pilot` grep 无 `WORKER-A1-CONTRACTS-V2-DONE` / `WORKER-A2-SHARED-INFRA-V2-DONE` / `A3-GO-AFTER-A1-A2-V2` · 确认 wait gate 中
2. ✅ A1 V2 hash 在 `feat/phase-a1-contracts` (`db2f2b4`) · A2 V2 hash 在 `feat/phase-a2-shared` (`114b562`) · 等主 CLI cherry-pick
3. ✅ 通过 `git show <branch>:<path>` 读 5 V1+V2 契约 + `shared/sse_envelope.py` 内容 · 不污染本 worktree
4. ✅ 读 `agent_channel/realtime_stream.py` (1047 行) + `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` (2730 行) + `web/src/lib/api/_live.ts` (184 行) 全文要点
5. ✅ 读 `docs/audit/conflict-register-v1.md` Cat 2/3/4/11 channel 条目 + `docs/audit/sub-agent-step2-round1/architecture.md` 对应 verbatim findings

---

## 1. 现状盘点 (5 处 gap · 与 onboarding §1 6 项交付一一映射)

| # | 现状 (file:line · 已确认) | 与 4-gate / envelope / banner spec 差距 |
|---|---|---|
| G-1 | `ChannelWorkspace.tsx:115` 用 `selectedSessionId` 而非 protocol §2 的 `selectedSession` | 名字漂 (轻 · 重命名即可) |
| G-2 | `ChannelWorkspace.tsx:124` `liveCandidates: Candidate[] \| null` | protocol §2 要求 `liveData: AgentSession \| null` (整 session 形态 · 不止 candidates) — 当前 `setLive(norm)` 只装候选 · 致 RadarPanel/FunnelStrip/SignalTimelinePanel 永远读 mock `s`。**最大 gap** |
| G-3 | `ChannelWorkspace.tsx:1400` `res.body.getReader()` 内联 SSE | Cat 3 · 应换 `streamSse()` from `_live.ts:76` |
| G-4 | `realtime_stream.py:228-237` done event 仅 `candidates/metrics/data_source` | Cat 4 · 缺 radar / signals / funnel / match_dimensions / product_recommendations / pitch_scripts (workspace-state-protocol §4 + sse-envelope §3.1 + `CHANNEL_PANEL_KEYS` 7 keys) |
| G-5 | `realtime_stream.py:339` Tavily key 缺 → 静默 yield mock_fallback · 前端无 banner | Cat 11 · banner-spec 规则 2 违 |
| G-6 | 无 `/api/channel/demo/run` · 无 `data/mock/workspace/channel/scenarios/*.json` | onboarding §1 第 4 项 missing |
| G-7 | 无 `web/tests/regression/channel-pilot-4gate.spec.ts` | onboarding §1 第 5 项 · 现有 `channel-mock-switch / live-wire / candidate-drawer` 3 spec 是 2026-04-28 老 wave · 4-gate 同步 smoke 缺 |
| G-8 | (Cat 13 同源 · A6 共拥) `OUTPUT_ACTIONS` 4 dead button | 不在 A3 强行修范围 · A6 export contract 完后 A3 wire onClick · plan §10 标 deferred |

---

## 2. State 模型 · 4 gate canonical (改动最小化路径)

### 2.1 改完目标

```tsx
// web/src/app/archive/channel/_components/ChannelWorkspace.tsx · default export

const [started, setStarted] = useState<boolean>(false);                              // (1) 已有 · 不动 (line 129)
const [selectedSession, setSelectedSession] = useState<string>(MOCK_SESSIONS[0].id); // (2) 重命名 selectedSessionId
const [liveData, setLiveData] = useState<ChannelSession | null>(null);               // (3) 旧 liveCandidates: Candidate[] | null → ChannelSession | null
const [selectedCandidate, setSelectedCandidate] = useState<string | null>(null);    // (4) 重命名 selectedCandidateId

const sessionData: ChannelSession =
  liveData ??
  MOCK_SESSIONS_MAP[selectedSession] ??
  MOCK_SESSIONS[0];
```

`sessionData` 单点派生 · 5 panel 全消费它 · 切下拉 / live SSE done / 切 demo 三路全经由这一个推导。

### 2.2 重命名映射 (gate 名字 ↔ 现有名字)

| protocol §2 名 | 现 ChannelWorkspace 名 | 改法 |
|---|---|---|
| `started` | `started` | keep |
| `selectedSession` | `selectedSessionId` | rename (sed-like · 全文件 · ~16 处) |
| `liveData` | `liveCandidates` | rename + 类型从 `Candidate[] \| null` 升 `ChannelSession \| null` |
| `selectedCandidate` | `selectedCandidateId` | rename (~6 处) |

### 2.3 子组件 props 协议 (5 panel)

```tsx
function RadarPanel({ sessionData }: { sessionData: ChannelSession }) { /* radar = sessionData.radar */ }
function FunnelStrip({ sessionData }: { sessionData: ChannelSession }) { /* funnel = sessionData.funnel */ }
function CandidatesPanel({ sessionData, onSelectCandidate }: ...) { /* candidates = sessionData.candidates */ }
function SignalTimelinePanel({ sessionData }: { sessionData: ChannelSession }) { /* signals = sessionData.signals */ }
function ConversationPanel({ sessionData, messages, ... }: ...) { /* messages 仍走 lift-up state */ }
```

**反模式禁止**: `function RadarPanel() { const s = CHANNEL_SESSION; ... }` (硬绑 mock · workspace-state-protocol §2.2 已定 · 现有 5 panel 已部分接 props · 但 RadarPanel/FunnelStrip/SignalTimelinePanel 接的是 `sessionData=s` 即 mock currentSession · live 时不切 — 这就是 G-2)

### 2.4 ChannelSession 类型扩展 (前端)

现 `ChannelSession` (in `web/src/lib/mock/agent-channel-sessions.ts`) 定义 (per protocol §10 已含): `id / benchmark / benchmarkName / query / signals / candidates / funnel / radar / conversation / match / qcCounts / candidateCount / stage / recentSessions`

`liveData` 形态 = 同 `ChannelSession` · 由 `normalizeBackendDone(envelope)` 函数从 done event 构造:

```tsx
function normalizeBackendDone(evt: DonePayload): ChannelSession {
  return {
    id: evt.session_id ?? "live",
    benchmark: "(实时搜索)",
    benchmarkName: "实时",
    query: { /* 从用户输入回填 */ },
    candidates: (evt.candidates ?? []).map(normalizeBackendCandidate),  // 复用现 line 1200 normalizeBackendCandidate
    radar: evt.radar ?? [],          // 8-axis P50 (新增 · backend 输出)
    signals: evt.signals ?? [],      // 8 信号源状态 (新增)
    funnel: evt.funnel ?? [],        // 5 阶段 (新增)
    matchDimensions: evt.match_dimensions ?? [],
    productRecommendations: evt.product_recommendations ?? [],
    pitchScripts: evt.pitch_scripts ?? [],
    conversation: [],                // live 模式 conversation 走 lift-up state · 这里空数组
    match: { /* default */ },
    qcCounts: { block: 0, warn: 0, info: 0 },
    candidateCount: (evt.candidates ?? []).length,
    stage: "已扫描",
    recentSessions: [],
  };
}
```

注意 `evt.signals / evt.radar / evt.funnel` 是 done event 顶层 flat 字段 · 因 A2 `make_done(panels={...})` 把 panels expand 到顶层 (见 §3 drift note)。

---

## 3. Done envelope shape · spec 与 A2 impl 的 drift (重要)

### 3.1 Drift 现象

| 来源 | 形态 |
|---|---|
| `docs/contracts/sse-envelope.md` v1.0 §2.1 (A1 V2 spec) | **嵌套**: `{ event, version, agent, session_id, ok, ts, duration_ms, metrics, payload: {...}, warnings, errors, trace_id }` |
| `shared/sse_envelope.py` v1.0 (A2 V2 impl · `make_done`) | **扁平**: `{ event, data_source, [session_id], [metrics], [downstream], **panels-展开, **extras }` |

A2 helper 把 `panels=` dict 直接展开到 done event 顶层 (impl line 268-270) · 不嵌 `payload`。`agent / version / ok / ts / duration_ms / warnings / errors / trace_id` 在 helper 中**不存在** (codec contract V1 spec 与 V2 实装漂)。

### 3.2 A3 选项 + 决定

- **A**: 跟 A2 impl 走 (扁平 · 用 `make_done(panels=..., metrics=..., data_source=..., session_id=..., ...)`) · 这是 **采用方案** · 因 A2 V2 已 ratified 且 onboarding §2 必读列出 `shared/llm_caller/` + `shared/sse_envelope.py` 是 A3 import 目标
- **B**: 严格按 V1 spec 嵌套 envelope · 改 A2 helper · — **不采用** · 越界 (A3 范围不含改 shared)

### 3.3 A3 落地 done event 形状 (verbatim)

```python
# agent_channel/realtime_stream.py · 改后 line 228 起
from shared.sse_envelope import make_done, DATA_SOURCE_LIVE, DATA_SOURCE_MOCK_FALLBACK, CHANNEL_PANEL_KEYS

# (上文照常 stage 流出 enrich + pitch + rank 后)
candidates_out = candidates                                    # 已有
signals_out    = _aggregate_signal_sources(raw_signals)        # 新 helper · 8 信号源 status / hits / coverage
radar_out      = _build_radar_p50(tags, candidates)            # 新 helper · 8-axis P50 对标 (聚合 candidates radar_8axis 取 median)
funnel_out     = _build_funnel(raw_signals, scored, candidates)# 新 helper · 5 阶段 (signal/aggregate/rank/enrich/pitch) 计数
match_dim_out  = _aggregate_match_dimensions(candidates)       # top-level 聚合 (per-candidate 已有 · 取 union)
products_out   = _aggregate_product_recommendations(candidates)# top-level
pitch_out      = _aggregate_pitch_scripts(candidates)          # top-level

yield make_done(
    panels={
        "candidates": candidates_out,
        "signals": signals_out,
        "radar": radar_out,
        "funnel": funnel_out,
        "match_dimensions": match_dim_out,
        "product_recommendations": products_out,
        "pitch_scripts": pitch_out,
    },
    metrics={
        "signalTotal": len(raw_signals),
        "companiesFound": len(company_map),
        "final": len(candidates),
        "kb_files_used": kb_files_used_count,    # 已有 KB 上传时填
    },
    data_source=data_source,                       # "live" | "mock_forced" | "mock_fallback" | "cached"
    session_id=str(uuid.uuid4()),                  # 新增 · 之前没有
    warnings=warnings_collected,                   # 走 **extras 通道塞 (A2 helper 不专门 take)
)
```

`warnings_collected` 注: A2 `make_done` 形参没 `warnings` · 所以走 `**extras`。会落到顶层 `warnings: [...]`。前端 `streamSse` onEvent 解析时读 `evt.warnings ?? []`。

### 3.4 Forward-compat hook

A1 V2 spec (sse-envelope.md §2.1) 嵌套形 envelope 是更未来的契约。A3 当前用扁平 · A2 helper 后续 v1.1 / v2 升级嵌套时 · A3 done 路径只需把 `make_done` 的调用换成 `make_done_v2` (假设) · 不动其他逻辑。**本 PR 不做 forward-compat 兜底** (按 CLAUDE.md "Don't add error handling, fallbacks, or validation for scenarios that can't happen") · 留给 A2 V2.1 把 helper 升级时拉。

---

## 4. SSE 客户端 · streamSse 接入

### 4.1 改前 (line 1387-1445 简略)

```ts
const res = await fetch(`${apiBase}/api/channel/run`, { method: "POST", body: JSON.stringify({...}) });
if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
const reader = res.body.getReader();
const decoder = new TextDecoder();
let buf = "";
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  buf += decoder.decode(value, { stream: true });
  const blocks = buf.split("\n\n");
  buf = blocks.pop() ?? "";
  for (const block of blocks) {
    /* 手撕 data: ... 行 + JSON.parse */
    if (evt.event === "done" && Array.isArray(evt.candidates)) setLive(norm);
  }
}
```

### 4.2 改后

```ts
import { streamSse, LiveFailError, liveFailBannerText } from "@/lib/api/_live";

try {
  await streamSse(
    `${apiBase}/api/channel/run`,
    { query: queryText, mock: false, top_n: 8 },
    (evt) => {
      setStreamEvents((prev) => [...prev, evt.data]);
      if (evt.type === "done") {
        const live = normalizeBackendDone(evt.data as DonePayload);
        setLiveData(live);
      }
    },
  );
} catch (err) {
  if (err instanceof LiveFailError) {
    const text = liveFailBannerText(err, "Channel /api/channel/run");
    setStreamErrorTop(text);          // 已有的 lift-up banner 槽 · workspace 顶部红条直接显
    onStreamError?.(text);
  } else {
    setStreamError(err instanceof Error ? err.message : String(err));
  }
}
```

注意 `streamSse` callback 收的 `evt.data` 是已 JSON.parse 的 dict · `evt.type` 是外层 `event:` 名 (e.g. "done" / "stage" / "error")。`evt.data` 可直接喂 `normalizeBackendDone`。

### 4.3 LiveFailError vs 后端 error event

- `streamSse` 内部:4xx/5xx/network/SSE error event 都 throw `LiveFailError` (line 158-163) · 调用侧 try/catch 一处搞定
- `evt.type === "error"` 在 callback 里**不会**触发 (因为 streamSse 自己 throw 了) · 所以 `setStreamErrorTop` 只走 catch 分支
- 这与 banner-spec 规则 1 (live failed → banner) 完全对齐

---

## 5. Banner-spec 规则 2 实装 · Tavily silent fallback fix

### 5.1 问题原貌 (realtime_stream.py:339)

```python
if not tavily_key:
    logger.warning("[channel.signal_search] TAVILY_API_KEY missing → mock_fallback")
    yield ("final", _mock_signal_fallback(query, tags), "mock_fallback")
    return
```

只 log · 不 yield event · 前端只能从 done 的 `data_source="mock_fallback"` 推断 · 但当前 ChannelWorkspace 没读这个字段 · 故静默。Codex 已标 banner-spec 规则 2 违。

### 5.2 改后 (双管齐下)

**Backend 改 1** · `_parallel_signal_search_core` 在 fallback 路径前 yield 一个 `warning` 事件 (走 stage 通道 · 因 A2 helper `make_stage(stage=..., status="warning")` 是合法形态):

```python
from shared.sse_envelope import make_stage, encode_event

if not tavily_key:
    logger.warning("[channel.signal_search] TAVILY_API_KEY missing → mock_fallback")
    yield ("warning", "TAVILY_API_KEY missing · 已降级为 mock 演示数据 · 配置 key 后可恢复 live")
    yield ("final", _mock_signal_fallback(query, tags), "mock_fallback")
    return
```

`run_channel_search_stream` 把 `("warning", msg)` tuple 翻译为:
```python
yield make_stage(stage="signal_search", status="warning", message=msg)
```
+ 收集到 `warnings_collected` 列表 (per-call) · 在 done envelope `warnings` 字段透传 (per §3.3)。

**Backend 改 2** · `data_source` 已有 · 不动。

**Frontend 改 1** · `streamSse` callback 收 `evt.type === "stage"` 且 `evt.data.status === "warning"` 时 `setStreamErrorTop("⚠️ " + evt.data.message)` (沿用现有 banner UI · 不另起新组件)。

**Frontend 改 2** · `done` 事件如果 `evt.data.data_source === "mock_fallback"` · 顶部加二级提示条 (灰色 · 不阻断) "本次结果为 mock_fallback 演示 · 真接 Tavily 后会显 live"。

### 5.3 区分 3 类 banner (live-fallback-banner-spec §2 规则 1+2)

| 触发 | banner 类型 | UI 样式 |
|---|---|---|
| live SSE 4xx/5xx/network/error event (LiveFailError) | 规则 1 · 红条 + retry button | `streamErrorTop` 现有红色样式 |
| Tavily key 缺 (mock_fallback yielded) | 规则 1 衍生 · 黄条 (warn 级) | 复用 streamErrorTop · 黄色 variant (CSS class `ch-banner-warn`) |
| 用户选 mock 历史 session (selectedSession 切下拉) | 规则 2 · 灰条 (训练模式提示) | 静默灰条 "示例数据 (training mode)" |

3 类 banner 共用 banner DOM 槽 · variant 切样式即可。

---

## 6. /api/channel/demo/run 新端点 + scenario JSON

### 6.1 端点 contract

```python
# agent_channel/api.py · 新增
@app.post("/api/channel/demo/run")
def channel_demo_run(req: DemoRunRequest):
    """
    pure mock · 不调 LLM / Tavily · 从 data/mock/workspace/channel/scenarios/<id>.json 读
    · 模拟 stage 流 (有 sleep · 视觉与 live 一致) · done 一次性出 7 panels.
    """
    scenario_id = req.scenario_id  # "easy" / "medium" / "hard" · 三档 (反 5 原则 §3.5)
    return StreamingResponse(_demo_stream(scenario_id), media_type="text/event-stream")

def _demo_stream(scenario_id: str):
    path = Path(f"data/mock/workspace/channel/scenarios/{scenario_id}.json")
    if not path.exists():
        yield encode_event(make_error(f"scenario_not_found: {scenario_id}", code="DEMO_404"))
        return
    data = json.loads(path.read_text("utf-8"))
    # 模拟 6 stage (intent / signal / aggregate / rank / enrich / pitch) · 每 stage sleep 0.3s
    for stage in ["intent", "signal", "aggregate", "rank", "enrich", "pitch"]:
        yield encode_event(make_stage(stage, "running", message=data.get(f"stage_{stage}_msg", f"{stage}...")))
        time.sleep(0.3)
        yield encode_event(make_stage(stage, "done"))
    yield encode_event(make_done(
        panels={
            "candidates":              data["candidates"],
            "signals":                 data["signals"],
            "radar":                   data["radar"],
            "funnel":                  data["funnel"],
            "match_dimensions":        data["match_dimensions"],
            "product_recommendations": data["product_recommendations"],
            "pitch_scripts":           data["pitch_scripts"],
        },
        metrics=data["metrics"],
        data_source="mock_forced",
        session_id=f"demo_{scenario_id}_{int(time.time())}",
    ))
```

`DemoRunRequest`: `{ scenario_id: "easy" | "medium" | "hard" }` · 默认 `medium`.

### 6.2 Scenario JSON shape

`data/mock/workspace/channel/scenarios/easy.json`:

```json
{
  "scenario_id": "easy",
  "difficulty": "简单 (信号密度高 · 候选清晰 · radar 8 维全亮)",
  "stage_intent_msg": "从一句话里抽 3 个标签...",
  "stage_signal_msg": "5 路并行搜索 (招聘 / 招标 / 资质 / 融资 / 新闻)...",
  "candidates": [/* 8 个候选 · 每个含 radar_8axis / match_dimensions / product_recommendations / pitch_scripts */],
  "signals":    [/* 8 信号源 status 全 hit · coverage > 80% */],
  "radar":      [/* 8 轴 P50 vs 候选 top1 */],
  "funnel":     [/* 5 阶段计数 · 简单档前后落差小 */],
  "match_dimensions":        [/* top-level 聚合 ≥ 8 个维度 */],
  "product_recommendations": [/* Top3 产品 · score > 0.85 */],
  "pitch_scripts":           [/* 8 候选 × 1 话术 */],
  "metrics": { "signalTotal": 32, "companiesFound": 18, "final": 8, "kb_files_used": 3 }
}
```

3 文件: `easy.json` / `medium.json` / `hard.json` · 数据来源**反 5 原则**:
- 真实形态锚定 A 股年报 / 银保监公告 / 公开企业名录 (脱敏)
- 难度分层: easy 信号密度 > 80% · medium ~50% · hard ~20% (radar 多维半亮)
- 无 "答案字段" (无 difficulty / match_score 标签塞进去 · Agent 内部已计算)

### 6.3 前端集成点

`ChannelWorkspace.tsx` QueryBar 加第 3 个按钮 "Demo 演示模式" · 点开 popover 选 easy/medium/hard · 调 `/api/channel/demo/run` (复用 streamSse · 端点改了 · onEvent / done 一致路径) · `setLiveData` 落入。

---

## 7. Playwright smoke · channel-pilot-4gate.spec.ts

### 7.1 spec 大纲

```ts
// web/tests/regression/channel-pilot-4gate.spec.ts
import { test, expect } from "@playwright/test";

test.describe("channel pilot 4-gate", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/archive/channel");
    // 假设 auth bypass · 跟现有 channel-mock-switch.spec.ts 一致
  });

  test("Gate 1+2 (started + selectedSession) · 切下拉 → 5 panel 同步亮", async ({ page }) => {
    await page.getByTestId("channel-session-select").selectOption("sess_dingchuan");
    await page.getByTestId("channel-session-apply").click();
    // 5 panel 全亮且数据来源 mock
    await expect(page.getByTestId("channel-pilot-radar")).toBeVisible();
    await expect(page.getByTestId("channel-pilot-funnel")).toBeVisible();
    await expect(page.getByTestId("channel-pilot-candidates")).toBeVisible();
    await expect(page.getByTestId("channel-pilot-signals")).toBeVisible();
    await expect(page.getByTestId("channel-pilot-conversation")).toBeVisible();
    // 取第一个候选名 · 验切下拉真切了 (vs default sess_zrgs)
    await expect(page.getByTestId("channel-pilot-candidates")).toContainText("鼎川");
  });

  test("Gate 3 (liveData) · demo run → 5 panel 全填 mock_forced", async ({ page }) => {
    await page.getByTestId("channel-demo-run-btn").click();
    await page.getByTestId("channel-demo-easy").click();
    await page.waitForSelector('[data-testid="channel-pilot-banner-mock-forced"]');
    // done 后 5 panel 同步出现
    for (const t of ["radar", "funnel", "candidates", "signals", "conversation"]) {
      await expect(page.getByTestId(`channel-pilot-${t}`)).toBeVisible();
    }
  });

  test("Gate 4 (selectedCandidate) · click 候选 → drawer 出", async ({ page }) => {
    await page.getByTestId("channel-session-apply").click();
    await page.getByTestId("channel-candidate-card").first().click();
    await expect(page.getByTestId("channel-candidate-drawer")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("channel-candidate-drawer")).toBeHidden();
  });

  test("Banner-spec rule 2 · live 但 Tavily 缺 → mock_fallback banner 显", async ({ page, context }) => {
    // mock backend stage warning event (用 page.route 拦截 + 注入)
    await context.route("**/api/channel/run", async (route) => {
      const sse = [
        `event: stage\ndata: {"event":"stage","stage":"signal_search","status":"warning","message":"TAVILY_API_KEY missing · 已降级"}\n\n`,
        `event: done\ndata: ${JSON.stringify({event:"done", data_source:"mock_fallback", candidates:[], radar:[], signals:[], funnel:[], match_dimensions:[], product_recommendations:[], pitch_scripts:[], metrics:{signalTotal:0,companiesFound:0,final:0}})}\n\n`,
      ].join("");
      route.fulfill({ status: 200, headers: {"Content-Type": "text/event-stream"}, body: sse });
    });
    await page.getByTestId("scout-search-input").fill("找浙江精密零部件 PE 投后企业");
    await page.getByTestId("scout-search").click();
    await expect(page.getByTestId("channel-pilot-banner-mock-fallback")).toContainText("TAVILY");
  });
});
```

### 7.2 New DOM data-testid (统一用 `channel-pilot-*` 前缀)

- `channel-pilot-radar` (RadarPanel root)
- `channel-pilot-funnel` (FunnelStrip root)
- `channel-pilot-candidates` (CandidatesPanel root)
- `channel-pilot-signals` (SignalTimelinePanel root)
- `channel-pilot-conversation` (ConversationPanel root)
- `channel-pilot-banner-mock-forced` (demo run banner)
- `channel-pilot-banner-mock-fallback` (Tavily key 缺 warn banner)
- `channel-pilot-banner-live-fail` (live 4xx/5xx red banner)
- `channel-demo-run-btn` (QueryBar 第 3 button)
- `channel-demo-easy / -medium / -hard` (popover 3 选项)
- `channel-candidate-card` (现有可能已有 · verify)
- `channel-candidate-drawer` (drawer root · 现有可能已有 · verify)

---

## 8. 改动顺序 · 9 commit (每步独立 · trailer 见 onboarding §5)

| # | 改动 | 文件 | 验证 | trailer signal |
|---|---|---|---|---|
| C1 | state 重命名 (selectedSessionId → selectedSession · selectedCandidateId → selectedCandidate) + 升 liveCandidates → liveData 整 session shape · 加 sessionData 派生 | `ChannelWorkspace.tsx` | `cd web && npx tsc --noEmit` 0 err · 视觉无回归 (mock 默认渲染) | `WORKER-A3-PANEL-1-MIGRATED` |
| C2 | RadarPanel + FunnelStrip + SignalTimelinePanel 三只子 panel 改 props 真消费 sessionData (live 时切) | 同上 | tsc + 切下拉 panel 跟切 + live 模式 panel 跟 live 切 | `WORKER-A3-PANEL-2-MIGRATED` |
| C3 | CandidatesPanel + ConversationPanel 同步真消费 sessionData (虽然两者已部分接 props · 校齐 sessionData 派生路径) | 同上 | tsc + 候选 click → drawer · ESC 关 | `WORKER-A3-PANEL-3-MIGRATED` |
| C4 | SSE reader inline → streamSse + LiveFailError 接 streamErrorTop · normalizeBackendDone 函数加 | `ChannelWorkspace.tsx` (~ line 1387-1445) + 加 normalizeBackendDone | tsc + live 路 + 4xx 拦 banner 出 | `WORKER-A3-PANEL-4-MIGRATED` |
| C5 | backend done envelope 用 make_done · 加 _aggregate_signal_sources / _build_radar_p50 / _build_funnel / 3 top-level aggregator helper | `agent_channel/realtime_stream.py` (line 228 + 新增 helper 函数 ~80 行) | curl /api/channel/run 看 done event 全 7 panel · pytest agent_channel/ | `WORKER-A3-DONE-ENVELOPE-LANDED` |
| C6 | banner-spec rule 2 · realtime_stream Tavily 缺 yield warning + done envelope warnings 透传 | 同上 + ChannelWorkspace.tsx 接 stage warning | curl 模拟 · 前端 banner 出 | `WORKER-A3-PANEL-5-BANNER` |
| C7 | /api/channel/demo/run + 3 scenario JSON | `agent_channel/api.py` 加 endpoint + `data/mock/workspace/channel/scenarios/{easy,medium,hard}.json` | curl /api/channel/demo/run · stage 流 · done 7 panel | `WORKER-A3-DEMO-ENDPOINT-LANDED` |
| C8 | Playwright smoke channel-pilot-4gate.spec.ts | `web/tests/regression/channel-pilot-4gate.spec.ts` | `npx playwright test channel-pilot-4gate.spec.ts` 全绿 | `WORKER-A3-SMOKE-LANDED` |
| C9 | features-inventory.md 加 F-channel-pilot-* + state-snapshot.md 同 commit 段 + DONE | docs only | manual review | `WORKER-A3-CHANNEL-PILOT-DONE` (final · trailer 全集 per onboarding §5) |

每步 trailer 含 `PRESERVES: F-005 F-041 F-042 F-043 F-044 F-045` (channel 已有的全保留) · `NEW-DOM: data-testid="channel-pilot-..."`(随每 commit 累加) · `SMOKE-PASS: <spec>` (C8 后).

---

## 9. 红线 (一句话提醒自己)

- 不动 `ChannelWorkspace.tsx` / `realtime_stream.py` 直到 A1+A2 V2 cherry-pick + 主 CLI `A3-GO-AFTER-A1-A2-V2` 信号到
- 不改 `shared/sse_envelope.py` (越界) · 跟 A2 V2 实装 走扁平 done · 不补 V1 spec 里的嵌套 envelope (A3 不范围)
- 不动 5 子 agent (credit/alert/compli/riskctrl/report) workspace · A4 territory
- 不复活 legacy `/channel` 顶层路由 · 仅 `/archive/channel`
- commit 必带 `Signal:` trailer (onboarding §4 红线 + §5 ACK)
- 改 `web/*` 必带 `PRESERVES: F-XXX` + `NEW-DOM: data-testid=...` + `SMOKE-PASS: <spec>` (CLAUDE.md §13.5)

---

## 10. Out-of-scope · deferred 标注

- **OUTPUT_ACTIONS 4 dead button** (Cat 13 channel · ChannelWorkspace.tsx:1717-1724 onClick 全空) · 后端 `/api/channel/export_xlsx` `/export_docx` `/handoff` 都存在但 button 无 wire · 等 A6 export contract 落 + A4 复用模板再补 · 本 PR **不做** (可在 DONE commit 加 `DEFERRED: F-channel-output-actions → A4-channel + A6`)
- **ChannelSession 类型 fields rename** (前端 camelCase vs backend snake_case · 部分 normalize 临 hop) · A6 handoff schema 出来后再统一 · 本 PR 仅做最小 normalize · 不动类型定义的 camelCase 现状
- **Riskctrl-style "非 SSE" → SSE 化** (Cat 4 #6) · A4-riskctrl territory · A3 无关
- **CHANNEL_EVIDENCE / EvidenceTrail 重写** · 当前 ChannelWorkspace 末尾 ev-claim-summary 走静态 const · A6 evidence schema 未到 · 本 PR 不动
- **Q-041 industry/region 抽取** 已 fix-forward · A3 不重复

---

## 11. 等 GO 信号后第一动作 (cheat sheet)

```bash
# 0. 验 GO commit 在了
git fetch
git log chore/l0-infra | head -10 | grep "A3-GO-AFTER-A1-A2-V2" || echo "still wait"

# 1. rebase 拉 A1+A2 V2 进本 worktree
git rebase chore/l0-infra
# (期望: shared/llm_caller/* + shared/sse_envelope.py 出现 · docs/contracts/sse-envelope.md + llm-prompt-contract.md V2 进来)

# 2. 验关键 import 可达
python -c "from shared.sse_envelope import make_done, CHANNEL_PANEL_KEYS, DATA_SOURCE_LIVE; print(CHANNEL_PANEL_KEYS)"
# 应输出: ('candidates', 'signals', 'radar', 'funnel', 'match_dimensions', 'product_recommendations', 'pitch_scripts')

# 3. 起改第一 commit (C1 state 重命名)
# 改 ChannelWorkspace.tsx 4 处 useState 名 + sessionData 派生 + 5 panel sessionData prop wire
# cd web && npx tsc --noEmit
# git commit · trailer Signal: WORKER-A3-PANEL-1-MIGRATED
```

---

## 12. 风险点 (3 个 · 让自己提前看清)

1. **C5 backend aggregator 现成程度未知** · `_aggregate_signal_sources` / `_build_radar_p50` / `_build_funnel` / 3 top-level aggregator 是否能从现有 `enriched / scored / candidates` 直接派生 · 取决于 `sse_extras.enrich_candidate` 内部 `radar_8axis` / `match_dimensions` 真实形态 · 若为 per-candidate 才有 · top-level radar 要 P50 median 算法 · 可能 ~30 min 代码 · 不是 0 风险
2. **A2 helper warnings 字段不 first-class** · §3.3 我把 warnings 走 `**extras` 通道塞 · 落到顶层 OK · 但若后续 A2 V2.1 给 warnings 单独 param · A3 调用要改 · 风险中
3. **Playwright route mock 是否能仿真 SSE 流** · §7.1 用 `page.route + route.fulfill` 一次性 body 灌 · 真 SSE 是流式 · `streamSse` reader 是否会因为单次 body delivery 而正常解析 (`\n\n` 分块) · 需要小验证 · 不行就改用 `MOCK_SERVER` 模式 (启 mock server 真 stream)

---

## 13. State-snapshot 同步

按 CLAUDE.md §14.1 · 任何 reset 工程迭代必同更 `docs/reset/state-snapshot.md`。本 doc 是 wait-gate 期 read+draft prep · 不属于 "改产品 / 架构 / 决策" · 主 CLI verify 后认为需要也可以加段 · 我自己**不动 state-snapshot** (避免越界做 active rule 回写)。等 GO + 实际 panel migration commit 时按 §14.1 加段。

---

**End of draft · 等 GO**
