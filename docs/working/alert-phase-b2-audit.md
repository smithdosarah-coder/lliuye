# Alert Worker · Phase B.2 Pre-Dispatch Audit

> **Owner**: alert worker (`feat/allin-alert`)
> **Trigger**: Phase B.2 派活 brief (PM 2026-05-10 真意 reframe + codex 5 漏项)
> **Author**: alert worker · 2026-05-10
> **目的**: 派活 4 主活 + 11 step 落地前 · 列实证 gap · 给 PM 透明 readback

---

## Phase B.2 红线 (PM 真意 verbatim)

> "我要的演示不是一键切换 · 而是把本地的 mock 数据真实上传 · 通过真实后端代码跑一遍 · 最后给出结果"

= 输入可 mock · 结果不能 mock. backend 路径都真跑.

---

## 1. 后端 `/api/alert/demo/run` (主活 A · gap 最大)

### 1.1 现状 (`agent_alert/api.py:642-667`)
- 走 `_alert_demo_event_stream` → `_load_scenario_fixture(scenario_key)` → 读 `data/mock/workspace/alert/scenarios/{baseline_100,manuf_policy_event,judicial_news_dual}.json`
- yield 5 stage 节拍 + done envelope · `mode=mock_forced` · `data_source=DATA_SOURCE_MOCK_FORCED`
- **不读 KB / 不调 LLM / 不持久化** (注释 verbatim) · 即 **结果是 fixture · 不是 backend 真跑**
- 触发不可 GO 条件 #1: "/demo/run 仍 yield fixture_event"

### 1.2 改造方向
- 砍 `_load_scenario_fixture` + `_alert_demo_event_stream` · 保留 endpoint shape (签名兼容)
- 新增: 接 `data/mock/alert-pool/` 优质 batch (180 客户 · 12 月外部 + 24 月内部) 作为 demo input
- demo 模式 = 真跑 `run_scan_and_persist` · 同 `/api/alert/scan` pipeline · 区别仅是 input source
- Tavily 真接 (per Phase B step 3 已落 `demo_mode=False`) · 失败显 banner 不 silent fallback
- LLM 真调 (disposition) · 真持久化 · 真上链 ledger

---

## 2. 后端 `scan_engine.build_alert_provider` 静默 fallback (主活 A 子项)

### 2.1 现状 (`agent_alert/scan_engine.py:53-70`)
4 路径 · 3 路 silent fallback to MockSearchProvider (有 banner · 但仍出 mock 结果):
- `force_mock=True` → demo_forced (用户显式 OK)
- `ALERT_USE_TAVILY=0` → tavily_disabled (banner OK · 但 mock 结果替代真结果)
- `TAVILY_API_KEY` 缺 → tavily_key_missing (banner · 但 mock 结果)
- Tavily build 抛 → web_fallback_<Err> (banner · 但 mock 结果)

### 2.2 PM 真意冲突
"mock 只能 mock 输入 · 不能 mock 结果" · 即使 banner 显示 · 给用户的 hit_list / disposition 仍是 mock 结果 · 不符合 reframe.

### 2.3 改造方向
2 选 1:
- **(A) 跳外部 + 内部独跑**: Tavily 不可用时 · 不切 mock provider · 直接 skip external_scan · 仅跑内部交易规则 · banner 标 "外部源不可用 · 仅内部规则命中" · severity=warn (推荐 · 反映真实 ops 形态)
- **(B) 抛错**: 让前端 banner + retry · 不出半成品 · 信息密度低

主 CLI 之前 build_alert_provider 走 (A)-style 的 mock 替代 · 改 (A)-真 = 跳外部.

---

## 3. 前端 `AlertWorkspace.tsx` (主活 B/C)

### 3.1 形态切换 toggle 缺
- 现 UI 无"输入来源切换" 控件 · 只有 `triggerPrimaryScan` / `triggerSecondaryScan` 两个按钮跑同一个 `startScan`
- 派活 §B 要求: 真实 default · demo 自动加载 alert-pool batch · 都跑真后端

### 3.2 `currentDataSource` default = "mock" (line 350)
- 派活 §不可 GO 隐含: 默认 "live" · 没 run 时 "未启动" · run 后 backend emit 真 data_source

### 3.3 silent fallback `setCurrentDataSource("mock_fallback")` (line 517)
- scan 抛错时 silent 切 "mock_fallback" 标签 · 但 `liveData=null` 即 EMPTY_SESSION (空白) · 不出错数据
- 标签让人误以为还有数据 · 应换 typed banner + retry · 不打 mock_fallback 标

### 3.4 `ALERT_GLOBAL_STATS` (line 798-800)
- 静态 hardcode mock: `weeklyProcessed: "3,200" / redRate: "4.1%" / avgDuration: "6.5 分钟"`
- import from `@/lib/mock/agent-alert-sessions:31-35`
- 不是评分但是"假统计" · 派活红线 #2 "假分" 边缘 · 应改后端真接 OR 隐到 demo-mode-only

### 3.5 假证据 fixture (Phase B.1 已删)
- `EMPTY_EVIDENCE` (line 66-74) 替代旧 `ALERT_EVIDENCE` · 真证据走 DrillDrawer signal_timeline
- ✅ 已闭环 · B.1 fix verbatim 注释 (line 63-65)

---

## 4. decision_ledger 0 接入 (主活 A 红线 #5)

### 4.1 现状
- `agent_alert/` grep `decision_ledger / record_decision / DecisionLedger` = **0 命中**
- CLAUDE.md §3.7.5 明定: alert default retention=`short` (90d) · severity=red 升 `standard` (5y) · subject_id 必 hash · jurisdiction default `HQ` · failure silent-fail
- `ledger_exporter.py` 文件存在但与 shared.decision_ledger 无关 (alert 域内 export 工具)

### 4.2 改造点
- 在 disposition 生成后 (`agent_alert/disposition.py` 或 scan_engine 末尾) · 调 `shared.decision_ledger.record_decision(...)` · 1 cluster 1 ledger entry
- subject_id = hash(client_entity_key) · 用 `shared.decision_ledger.hash_subject_id`
- decision_type = "alert_disposition" · severity = cluster.tier
- evidence_refs = [hit_id, signal_timeline 出处]
- silent-fail 包 try/except (CLAUDE.md §3.7.5 verbatim)

---

## 5. alert-pool batch (优质 input · 已就位)

### 5.1 形态
- `data/mock/alert-pool/clients.csv` · 180 客户 · 13 列 (client_id / company_name / industry_l1/l2 / region / scale / credit_line_wan / balance_wan / interest_rate / term_months / product / first_draw_date / last_review_date)
- **无 USCC 列** · entity_resolver 会 fallback name-md5 (confidence 0.5)
- `external-signals/{client_id}.md` · 180 markdown 文件 · 12 月舆情/司法/工商/监管时间线 · 含出处
- `transactions/{client_id}.csv` · 180 csv · 24 月流水 (date/amount/type/counterparty/note)
- `_gen/` · 生成脚本 · 不读

### 5.2 pipeline 入口缺
- 现 `customer_scanner.py` / `scan_engine.run_scan_and_persist` 不识别 alert-pool 形态 · 需新 loader: `load_alert_pool_batch(root: Path) → ScanInput`
- 把 clients.csv → in-loan customer pool (replace `kb_load`)
- external-signals/*.md → 替 Tavily search 一部分 (内部信号源 · 不走外网) OR 与 Tavily 并行
- transactions/*.csv → 内部交易源 (替 `_load_internal_transactions`)

### 5.3 设计选项
- **demo 模式**: 真跑 scan_engine · 但 input 来自 alert-pool/ (不走 Tavily · 走预制时间线) · backend 算法不变 · disposition 真 LLM
- **real 模式**: 走 Tavily + 内部交易表 · 客户经理上传 csv (Phase B.2 不实现 upload UI · 用 placeholder · Phase D 上)

---

## 6. 11 step 与现状映射

| Step | 状态 | 备注 |
|---|---|---|
| 0 PM 真意复述 | ✅ done | e02a569 RESUMED |
| 1 PM 真意确认 | ✅ done | PM GO 收到 |
| 2 /demo/run 真跑 | 🚧 重写 | 主 gap |
| 3 UI 形态切换 | 🚧 新加 | toggle UI |
| 4 空状态/排版 | 🚧 redesign | EMPTY_SESSION 已有 · 需 prominent CTA |
| 5 错误降级 | 🚧 改 | 删 silent mock_fallback · 改 typed banner |
| 6 §3.5 表 | ✅ partial | 内部 mock (alert-pool) 保留 · 外部 Tavily 已真接 (B step 3) · 但 build_alert_provider 仍 silent fallback |
| 7 信息密度 | 🚧 调 | 折叠展开 · CTA 突出 |
| 8 unique id no-regression | ✅ done | step 5 已落 ensure_list_unique_ids · 改造后再跑 verify |
| 9 evidence drawer 真 wire | ✅ partial | step 4 已落 DrillDrawer signal_timeline · grep ALERT_EVIDENCE 0 命中 ✅ |
| 10 ledger 上链 | ❌ 0 接入 | 必加 |
| 11 admin E2E 4 件套 | ⏳ pending | demo 跑通后 |

---

## 7. 我承诺的不破坏项 (no-regression)

- alert.id 派生 (step 5 ensure_list_unique_ids) · 改造后 grep verify
- DrillDrawer signal_timeline 真证据链 (step 4) · 改造后 fixture 必走真 SSE done
- /api/alert/scan 现行 pipeline (Tavily 真接 · evidence_pipeline · cross_matcher) · /demo/run 改造不动 /scan
- RBAC 3 POST 端点 (B.1 fix · scan/batch_scan/demo) · /demo/run 重写后 require_action("alert", "invoke") 保留
- workspace-state-protocol §2 4 gate (started/sessionId/liveData/clientId) · toggle 加在 gate 之外

---

## 8. 立即开干顺序

1. **后端** `/api/alert/demo/run` 重写 + alert-pool loader
2. **后端** decision_ledger 接入
3. **后端** build_alert_provider 改 (skip external · 不切 mock provider)
4. **前端** AlertWorkspace 形态切换 toggle + currentDataSource default
5. **前端** 空状态 + 错误降级 redesign
6. **前端** 信息密度调
7. **集成** unique id no-regression verify
8. **E2E** admin 真号 4 件套

每完一项立即 commit (per CLAUDE.md commit 粒度 = task 粒度).

---

**End audit**
