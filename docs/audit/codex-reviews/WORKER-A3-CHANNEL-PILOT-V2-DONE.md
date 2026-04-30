verdict: PENDING (V2 fix landed · codex re-review 触发中)

context: 2026-04-29 codex V1 verdict DISAGREE (`WORKER-A3-CHANNEL-PILOT-DONE.md` 同目录) · 4 issue fix landed in single V2 commit on 2026-04-30 morning.

## 4 issue fix summary

### Issue 1 · ConversationPanel 不从 sessionData 派生 (cat 2 partial)
- **before**: `web/src/app/archive/channel/_components/ChannelWorkspace.tsx:212/461/1465` · `messages` state 仅 mock session 切换时 reset · 走 live SSE 后 ConversationPanel 卡 stale mock
- **after**: QueryBar 新增 `setMessages` + `setSelectedCandidate` prop · `runRealSearch` 在 `setLiveData(live)` 后同步 `setMessages(live.conversation)` + `setSelectedCandidate(null)` · live 注入路径 panel 全 swap 干净 · `runDemoScenario` 同模式

### Issue 2 · UI demo control + Playwright 验 (无 wiring)
- **before**: `/api/channel/demo/run` endpoint 已 land (worker-A3 C5) · UI 无 button · Playwright 仅拦 `/api/channel/run` (不验 demo path)
- **after**:
  - `ChannelWorkspace.tsx` QueryBar 加 `runDemoScenario(scenarioId)` 函数 → streamSse `/api/channel/demo/run` → 同 setLiveData/setMessages/setSelectedCandidate 路径
  - 3 档 button: `[data-testid="channel-demo-easy"]` / `channel-demo-medium` / `channel-demo-hard`
  - Playwright T5 case (`channel-pilot-4gate.spec.ts:168+`) · page.route 拦 demo endpoint · 验 endpoint hit + scenario_id="medium" payload + done.data_source="mock_forced" + 5 panel hydrate + candidate 切到 demo 注入 · 验 mock_fallback banner 不出 (mock_forced ≠ fallback)

### Issue 3 CRITICAL · data_source enum no-op (A4 会 inherit bad pattern)
- **before**: `agent_channel/realtime_stream.py:190+249-253+269+491` · `data_source = "tavily"` 透传 done envelope · 违 sse-envelope canonical 5 enum · A4 worker copy 模板会 inherit bad pattern
- **after**:
  - 初始值 `data_source: str = DATA_SOURCE_LIVE` · `provider_source: str | None = None`
  - `_parallel_signal_search_iter` 的 `("final", signals, raw_source)` 解构后 normalize:
    - `raw_source == "tavily"` → `data_source = DATA_SOURCE_LIVE`, `provider_source = "tavily"`
    - `raw_source in (DATA_SOURCE_MOCK_FORCED, DATA_SOURCE_MOCK_FALLBACK)` → 透传
    - 未知值不 silent 改写 (让上层看到原值 · 调试友好)
  - stage signal_scan done event 用 `data_source` (envelope enum) · provider_source 单独字段 (仅 live 时有)
  - `make_done` 收 `data_source=data_source` (canonical enum) + `**done_extras` (含 `provider_source` 仅 live 时)
  - 上游 `_parallel_signal_search_iter` API 不变 (仍 yield "tavily"/"mock_forced"/"mock_fallback") · 仅在消费侧 normalize · 测试不破
  - 前端 `formatChannelEvent` signal_scan done 显示同步: `provider ?? data_source` · UX "来源 tavily" 不退化

### Issue 4 · gate-4 smoke 弱 (drawer optional)
- **before**: `web/tests/regression/channel-pilot-4gate.spec.ts:159-169` · drawer locator 模糊 + `if (drawerOpened)` conditional · 不强制失败 · selectedCandidate 不 prove
- **after**: T3 改 mandatory (`channel-pilot-4gate.spec.ts:145+`) · `[data-testid="channel-candidate-card"]` first toBeVisible → click → `[data-testid="channel-candidate-drawer"]` toBeVisible → ESC → toBeHidden · 全 expect · 无 conditional · drawer DOM 形态变更直接破 spec (设计意图)

## Verification (本 V2 commit)

- `cd web && npx tsc --noEmit` → PASS (TSC_EXIT=0)
- `py -m pytest tests/shared/test_sse_envelope.py tests/shared/test_llm_caller.py -q` → 83 passed
- `py -m pytest tests/agent_channel/ -q` → 193 passed / 1 fail (`test_happy_path_real_tavily` · pre-existing Tavily HTTP 401 integration · 与本 fix 无关)
- `npx playwright test tests/regression/channel-pilot-4gate.spec.ts --project=chromium` → 5 passed (15.6s · T1/T2/T3-加固/T4/T5-新增)

## Touch surface

- `agent_channel/realtime_stream.py` (~+30 lines · normalize block + stage event update + make_done call)
- `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` (~+90 lines · QueryBar prop 扩 + runDemoScenario + 3 demo button + formatChannelEvent provider_source 兼容)
- `web/tests/regression/channel-pilot-4gate.spec.ts` (T3 重写 + T5 新增 · ~+100 lines)
- `docs/features-inventory.md` (F-066 NB 改 wired + smoke_test T5)
- `docs/reset/state-snapshot.md` (本日段)

## 不变 (intentionally unchanged)

- `_parallel_signal_search_iter` API 内部仍 yield "tavily" (provider 标识 · 内部细节 · 不污染 envelope) · normalize 在外层一次性做
- `agent_channel/api.py` `/api/channel/demo/run` endpoint 早已 emit DATA_SOURCE_MOCK_FORCED · 本 V2 不动
- `shared/sse_envelope.py` `make_done` 通过 **extras 收 provider_source · A2 helper 不需 first-class promote (low priority)
