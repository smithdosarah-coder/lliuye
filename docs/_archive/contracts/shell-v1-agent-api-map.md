# Platform Shell v1 · 6 Agent API 契约 + Demo-Mode Smoke

**日期**: 2026-04-19
**主 CLI HEAD**: `a5886c540b0a7b3ebd745349650dccbb3f2cb86a` (branch `chore/l0-infra`)
**后端端口**: `http://127.0.0.1:8000`（单进程单端口，portal `api_server.py` 合并 6 Agent 路由）
**用途**: 前端 Stage 4 Task B（6 Agent tile 降级守卫）实装依据。演示窗口 T-15h。
**基准命令**: 后端启动 `py -m uvicorn api_server:app --host 127.0.0.1 --port 8000`（需 env `DEEPSEEK_API_KEY` + `TAVILY_API_KEY`，主 CLI 本次实跑已满足）

> **重要**：本文档**只读实跑结论**，不描述还未实装的东西。前端按这张表写降级守卫，不用去翻 `agent_*/` 源码。

---

## 总表（一眼看全）

| Agent | 后端状态 | 后端路由挂载 | Demo-mode 触发 | 前端可接端点数 | 建议降级方式 |
|---|---|---|---|---|---|
| 1 · 获客 `channel` | 🟢 稳 | ✅ `_mount_agent_routes("agent_channel.api")` | POST body `mock:true` → 强制 mock 池（断网可演） | 2（GET scenarios / POST run SSE） | **真 API 优先 → 失败读 `/public/mock/channel_run.json` fixture** |
| 2 · 风控 `riskctrl` | 🟡 可降级 | ❌ 未挂载（`api.py` 不存在，仅有 gradio `app_demo.py`） | 无后端 API | 0 后端 / 1 前端静态 | **只读 `/public/mock/riskctrl_ruleset.json`**（已落盘 113 行 v1.0-readonly-mock） |
| 3 · 授信 `credit` | 🟢 稳 | ✅ `_mount_agent_routes("agent_credit.api")` | 预置 preset（corporate × 3 / retail × 3），LLM 未配可运行但 advising 段会 error | 2（GET presets / POST decision SSE） | **真 API 优先 → 失败读 `/public/mock/credit_decision_corporate.json` + `credit_decision_retail.json` fixture** |
| 4 · 预警 `alert` | 🟡 可降级 | ❌ 未挂载（portal TODO Phase 2） | `demo_mode=True` 内置 `MockSearchProvider`（已 runtime_dump 到 yaml） | 0 后端 / 1 前端静态 | **dashboard stub 直接读 `/public/mock/alert_hitlist.json`**（从 `evaluation/manual/4_20260419.yaml` 转 JSON 即可）。UI 实装靠 agent4 的 `docs/design/alert-dashboard-stub.md` |
| 5 · 合规 `compliance` | 🟡 可降级 | ✅ 挂载，但仅 1 端点且**结果无效**（见详情） | 无 mock 模式 | 1（GET policy_scan，返回空+error 优雅降级） | **disabled tile + tooltip "待 kb_scan 底座 + Phase 2 defer"**；或读 `/public/mock/compliance_policy_scan.json` 静态清单 |
| 6 · 报告 `report` | 🟢 稳 | ✅ `_mount_agent_routes("agent_report.api")` | Query `mock=1&preset=<key>&business_line=<line>` | 7（含 downloads / preset / fill / refine） | **真 API 优先 → 失败使用 `mock=1` 继续走后端 fixture → 再失败用 `/public/mock/report_fill_mock.json`**；必须备 fallback docx（outputs/） |

**颜色注释**：🟢 稳 = 真跑通且返回业务数据；🟡 可降级 = 未挂载 or 依赖不具备，前端必须走 mock；❌ 崩 = 本轮实跑中无此状态。

---

## 逐 Agent 详情

### Agent 1 · 获客（`channel`）

1. **后端模块路径**：`agent_channel/`（agent.py / api.py / realtime_stream.py / sources_config.py / prompts.py / scoring.py / product_recommender.py）
2. **API 端点清单**（来自 `agent_channel/api.py`）：
   - `GET /api/channel/scenarios` — 列出预置场景元数据
   - `POST /api/channel/run` — 流式跑 look-alike 搜索（SSE）
3. **Demo-mode 触发方式**：POST body 传 `mock: true` → `run_channel_search_stream(force_mock=True)` 走 mock 池，完全断网可演示。另外，**环境无 `TAVILY_API_KEY` 时自动降级 mock_fallback**（见 api.py:76 注释）。
4. **核心场景实跑命令**（真实走过）：
   ```bash
   # 场景元数据
   curl -s http://127.0.0.1:8000/api/channel/scenarios
   # 强制 mock SSE（前端 DEMO MODE 开关）
   py -c "import json,urllib.request;
   body=json.dumps({'query':'杭州精密制造','provider':'deepseek','top_n':3,'mock':True}).encode('utf-8');
   req=urllib.request.Request('http://127.0.0.1:8000/api/channel/run', data=body, headers={'Content-Type':'application/json'}, method='POST');
   [print(l.decode('utf-8',errors='replace').rstrip()) for l in urllib.request.urlopen(req, timeout=60)]"
   ```
5. **实跑结果**（HTTP 200，SSE）：
   - `GET /scenarios` → `{"scenarios":[{"key":"hangzhou_precision",...},{"key":"shenzhen_tech",...}]}`，2 个场景。
   - `POST /run mock=true` → 13 条 SSE，阶段序列：`parse` → `signal_scan`（`data_source: mock_forced`）→ `aggregate` → `enrich` → 最终候选清单。典型耗时 5-10 s（mock 路径）。
6. **依赖外部服务**：Tavily（默认 provider=tavily；DEEPSEEK_API_KEY 用于 `parse` 阶段意图解析）；mock=true 时全内置 fixture，零外部依赖。
7. **降级路径**：
   - Tavily key 缺失 → 代码自动走 `mock_fallback`，不会 500。
   - DeepSeek 崩 → `parse` 阶段 yield error SSE，前端应 catch `event:error`。
   - 彻底不可用 → 读 `/public/mock/channel_run.json`（见最后 checklist）。
8. **前端可用 fixture schema**（建议主 CLI 补 `web/public/mock/channel_run.json`，schema 对齐实跑 SSE）：
   ```json
   {
     "scenarios": [{"key":"hangzhou_precision","name":"...","desc":"..."}],
     "run_mock_events": [
       {"event":"stage","stage":"parse","status":"done","tags":[{"category":"地区","value":"杭州"}]},
       {"event":"stage","stage":"signal_scan","status":"done","count":8,"data_source":"mock_forced"},
       {"event":"stage","stage":"aggregate","status":"done","total":4},
       {"event":"stage","stage":"enrich","status":"done","count":3},
       {"event":"candidates","items":[/* 企业名 + 信号时间线 + 产品推荐 */]}
     ]
   }
   ```

---

### Agent 2 · 风控（`riskctrl`）

1. **后端模块路径**：`agent_riskctrl/`（agent.py / app_demo.py / backtesting.py / metrics.py / rule_engine.py）
2. **API 端点清单**：**无**。portal `api_server.py` 第 188 行明确 `# TODO Phase 2: _mount_agent_routes("agent_riskctrl.api", "Agent2 RiskCtrl")`。`agent_riskctrl/api.py` 不存在；`app_demo.py` 是 gradio 旧 demo，不对 portal 生效。
3. **Demo-mode 触发方式**：无后端 API；前端只能走 ReadOnly 静态 mock。
4. **核心场景实跑命令**：N/A（后端无路由）；`curl http://127.0.0.1:8000/api/riskctrl/*` 会 404。
5. **实跑结果**：404 Not Found（portal 未挂载）。
6. **依赖外部服务**：无（baseline 已在 `evaluation/runtime/` 有 JSON 产物）。
7. **降级路径**：已有 `web/public/mock/riskctrl_ruleset.json`（113 行 v1.0-readonly-mock，5 条 rule × {conditions / action / priority / backtest(ks/approve_rate/bad_rate/FP/TN)}），**前端直接 fetch 静态 json 即可，不走后端**。
8. **前端可用 fixture**：**已齐**（`web/public/mock/riskctrl_ruleset.json`）。schema 为：
   ```json
   {
     "description": "...",
     "version": "v1.0-readonly-mock",
     "ruleset": {
       "description": "...",
       "rules": [{
         "rule_id": "R001",
         "name": "...",
         "description": "...",
         "conditions": [{"field":"overdue_days_90d","operator":">","value":30}],
         "action": "reject|manual_review|approve",
         "priority": 1,
         "backtest": {"ks":0.31,"approve_rate":0,"bad_rate":0.72,"hit_count":18,"hit_rate":0.12,"FP":4,"TN":110,"FP_rate":0.0351}
       }]
     }
   }
   ```

---

### Agent 3 · 授信（`credit`）

1. **后端模块路径**：`agent_credit/`（agent.py / api.py / approval_engine.py / scoring_model_corporate.py / scoring_model_retail.py / rating_engine.py / rule_engine_v2.py / case_retriever.py / mock_data/）
2. **API 端点清单**（来自 `agent_credit/api.py`）：
   - `GET /api/credit/presets/{segment}` — segment ∈ {corporate, retail}
   - `POST /api/credit/decision` — 流式跑 7 阶段授信 pipeline（SSE）
3. **Demo-mode 触发方式**：不需显式 demo flag，预置 preset（corporate 3 个：`dingsheng_trade` / `ruiheng_precision` / `zhongrui_network`；retail 3 个：`lisi_education` / `wangwu_decoration` / `zhangsan_restaurant`）本身就是 demo fixture。LLM 未配（api_key="dummy" 默认）时 advising 段可能 yield error SSE，但 scoring / rule_check / case_retrieval 段走确定性代码，照样返数据。
4. **核心场景实跑命令**：
   ```bash
   # 对公预置
   curl -s http://127.0.0.1:8000/api/credit/presets/corporate
   # 零售预置
   curl -s http://127.0.0.1:8000/api/credit/presets/retail
   # 决策 SSE
   py -c "import json,urllib.request;
   body=json.dumps({'segment':'corporate','preset_name':'dingsheng_trade','provider':'deepseek'}).encode('utf-8');
   req=urllib.request.Request('http://127.0.0.1:8000/api/credit/decision', data=body, headers={'Content-Type':'application/json'}, method='POST');
   [print(l.decode('utf-8',errors='replace').rstrip()) for l in urllib.request.urlopen(req, timeout=120)]"
   ```
5. **实跑结果**（HTTP 200）：
   - `GET /presets/corporate` → `{"segment":"corporate","presets":["dingsheng_trade","ruiheng_precision","zhongrui_network"]}`
   - `GET /presets/retail` → `{"segment":"retail","presets":["lisi_education","wangwu_decoration","zhangsan_restaurant"]}`
   - `POST /decision corporate/dingsheng_trade` → 13+ 条 SSE：`profile_loaded` → `feature_extracting/done`（debt_ratio 0.8 / revenue_growth -0.18）→ `scoring/done`（composite_score 47 / risk_grade D）→ `rule_checking/done`（命中 corp_rl_001 关联方 / corp_rl_003 负债率）→ `case_retrieving/done`（相似案例 similarity 0.88）→ `advising`。典型耗时 ~30s（含 advising LLM 调用）。
6. **依赖外部服务**：DEEPSEEK_API_KEY（仅 `advising` 阶段用，生成审批意见话术）。scoring / rule_check / case_retriever 是确定性代码，无外部依赖。
7. **降级路径**：
   - DeepSeek 崩 → SSE yield `event:error` 在 advising 阶段；前端显示前 4 段已拿到的结构化结果（feature+score+rules+cases），advising 段切 fallback 文案。
   - 真全崩 → 读 `/public/mock/credit_decision_corporate.json` / `credit_decision_retail.json`。
8. **前端可用 fixture schema**（建议主 CLI 补 2 个 json）：
   ```json
   {
     "profile_loaded": {"profile_id":"corp_dingsheng_001","company_name":"鼎盛商贸...","financial_anchors":{...}},
     "feature_done": {"financial.debt_ratio":0.8,"financial.revenue_growth":-0.18, "...":"..."},
     "scoring_done": {"composite_score":47,"risk_grade":"D","sub_scores":{"financial":{...}}},
     "rule_done": [{"rule_id":"corp_rl_003","is_hard":true,"can_waive":false,"severity":"high","actual_value":0.8,"threshold":0.75}],
     "case_done": [{"case_id":"case_corp_022","similarity":0.88,"decision":"有条件批准","approved_amount":200,"interest_rate":0.082}],
     "advising_done": {"decision":"...","reason":"...","conditions":["..."]}
   }
   ```

---

### Agent 4 · 预警（`alert`）

1. **后端模块路径**：`agent_alert/`（agent.py / app_demo.py / alert_engine.py / customer_scanner.py / cross_matcher.py / disposition.py / knowledge_base.py / runtime_dump.py / trend_analyzer.py）
2. **API 端点清单**：**无**。portal `api_server.py` 第 187 行 `# TODO Phase 2: _mount_agent_routes("agent_alert.api", "Agent4 Alert")`。`agent_alert/api.py` 不存在。
3. **Demo-mode 触发方式**：`MockSearchProvider(demo_mode=True)`（在 `runtime_dump.py` 里跑）离线生成 HitList。已经有产物：`evaluation/manual/4_20260419.yaml`（894 行，100 个客户，tool_calls: 200/200 成功）。
4. **核心场景实跑命令**：
   ```bash
   # 重跑 dump（可选；yaml 已在仓库）
   py -m agent_alert.runtime_dump --out evaluation/manual/4_20260419.yaml
   ```
5. **实跑结果**：yaml 已存在（git commit `e18028f0d75eb2bfc1c57ffe9465fb01e3a591fb` 快照）：
   - whitelist_entity_ids：100 个 entity
   - customers：每个 `{entity_id, name, grade ∈ {red/yellow/green}, trigger_reasons[], evidence[{type, signal, source, url}], scan_time_ms, status}`
   - 样例 red：LC10001 华联精密制造，裁判文书 + 客户风险标签 + 本行制度交叉命中
   - tool_calls: `{total:200, success:200}`
6. **依赖外部服务**：生产路径是 Tavily + 内部 LedgerProvider；demo 路径完全 offline（MockSearchProvider）。
7. **降级路径**：
   - 后端未挂载 → 前端**只能**静态 mock，无真跑路径。
   - dashboard UI 实装参考 `docs/design/alert-dashboard-stub.md`（agent4 自己出的 spec）。
8. **前端可用 fixture**（建议主 CLI 补 `web/public/mock/alert_hitlist.json`，从 yaml 转 JSON；schema 对齐 runtime_dump）：
   ```json
   {
     "version": "runtime-v1",
     "generated_at": "2026-04-19T09:03:12Z",
     "source": {"agent":"alert","kb_scenario":"demo_data/agent_alert","search_provider":"MockSearchProvider (demo_mode=True)"},
     "summary": {"total": 100, "red": 10, "yellow": 0, "green": 90},
     "customers": [
       {"entity_id":"LC10001","name":"华联精密制造有限公司","grade":"red",
        "trigger_reasons":["cross_hit"],
        "evidence":[{"type":"external","signal":"...","source":"裁判文书网 (2025)沪0115民初12345号","url":"..."}],
        "scan_time_ms": 0.42, "status":"completed"}
     ],
     "tool_calls": {"total":200, "success":200}
   }
   ```

---

### Agent 5 · 合规（`compliance`）

1. **后端模块路径**：`agent_compliance/`（agent.py / api.py / compliance_checker.py / defect_classifier.py / event_extractor.py / matrix_matcher.py / policy_parser.py / policy_scanner.py）
2. **API 端点清单**（来自 `agent_compliance/api.py`，只有 1 个）：
   - `GET /api/compliance/policy_scan?query=<>&limit=<n>` — 主动从政策源拉最新候选
3. **Demo-mode 触发方式**：**无显式 demo flag**。端点内部 try/except，失败则返回 `{"policies": [], "error": "..."}` 不崩。
4. **核心场景实跑命令**：
   ```bash
   curl -s "http://127.0.0.1:8000/api/compliance/policy_scan?query=报送制度&limit=3"
   ```
5. **实跑结果**（HTTP 200）：返回 3 条 policies（Tavily 搜索兜底，不是专业政策源）。示例 title 包含《千户集团基础涉税信息报送制度》《中央纪委国家监委驻司法部纪检监察组》《北京市公路交通阻断信息报送制度》——**与信贷业务无关**（Tavily 关键词检索，source_name 都是 "tavily"，`policy_doc: null`）。
6. **依赖外部服务**：Tavily（通过 `shared.sources` 路由 gov_cn / pbc / flk_npc，最终回退到 Tavily 泛搜）。
7. **降级路径**：
   - 端点已内置 `try/except` → 失败返空 list + error，前端不崩。但**返回内容对演示无价值**，UI 上会很尴尬（全是政务网站/纪委文章）。
   - 建议演示当场：**disabled tile + tooltip "Agent5 待 kb_scan 底座 + Phase 2 defer"**；若必须显示，读 `/public/mock/compliance_policy_scan.json` 放 3-5 条金融相关假政策（见 fixture 建议）。
8. **前端可用 fixture schema**（建议主 CLI 补 `web/public/mock/compliance_policy_scan.json`，手写 3-5 条金融政策）：
   ```json
   {
     "policies": [
       {"title":"《商业银行小微企业金融服务监管评价办法》",
        "source_url":"https://www.cbirc.gov.cn/...",
        "fetched_at":"2026-04-19T...",
        "source_name":"cbirc",
        "snippet":"金融监管总局发布... 对商业银行小微企业贷款的风险监管加强..."}
     ],
     "fallback_reason": "policy_scan 端点未接专业政策源，演示使用静态 fixture"
   }
   ```

---

### Agent 6 · 报告（`report`）

1. **后端模块路径**：`agent_report/`（api.py 827 行 / enterprise_profile.py / material_enhancer.py / mock_fixtures.py / session_store.py / sources_config.py），以及上游 `section_generator.py` / `truth_fill.py` / `quality_scorer.py` / `financial_analyzer.py` / `material_kb.py`
2. **API 端点清单**（来自 `agent_report/api.py`）：
   - `GET /api/report/health` — 状态灯，返回 `{status, llm_connected, version}`
   - `POST /api/report/fill?mock={0|1}&preset=<key>&business_line={corporate|inclusive|reserved}` — 5 阶段填报 SSE（multipart/form-data）
   - `POST /api/report/refine` — 基于 session_id 续跑外因 section
   - `GET /api/report/preset/{key}` — 返回 EnterpriseProfile 只读 fixture
   - `GET /api/report/downloads/{session_id}/{filename}` — 真跑 docx 下载（UUID 白名单 + 目录穿越防护）
   - `GET /api/report/downloads/legacy/{fname}` — mock 模式历史 docx
   - `GET /downloads/{fname}` — 兼容老接口
3. **Demo-mode 触发方式**：Query `mock=1`，preset 在 `{dingsheng_trade, zhangsan_restaurant}`（业务线自动映射：corporate→dingsheng_trade、inclusive→zhangsan_restaurant）。`mock=1` 不需要上传文件，5 段假进度 + 真 section 输出 + downstream_handoff。
4. **核心场景实跑命令**：
   ```bash
   # 状态灯
   curl -s http://127.0.0.1:8000/api/report/health
   # EnterpriseProfile
   curl -s http://127.0.0.1:8000/api/report/preset/dingsheng_trade
   curl -s http://127.0.0.1:8000/api/report/preset/zhangsan_restaurant
   # mock=1 SSE（不传文件）
   py -c "import urllib.request; req=urllib.request.Request('http://127.0.0.1:8000/api/report/fill?mock=1&preset=dingsheng_trade&business_line=corporate', method='POST');
   [print(l.decode('utf-8',errors='replace').rstrip()) for l in urllib.request.urlopen(req, timeout=60)]"
   ```
5. **实跑结果**（HTTP 200，SSE）：
   - `GET /health` → `{"status":"ok","llm_connected":true,"version":"0.1.0"}`
   - `GET /preset/dingsheng_trade` → 完整 EnterpriseProfile（financial_anchors / guarantee_info / related_party_info / existing_credit / request / chapters）。
   - `GET /preset/zhangsan_restaurant` → 同 schema，business_line=inclusive。
   - `POST /fill mock=1` → 20+ 条 SSE，5 阶段 + 4 section（chapter_1_background / chapter_2_operation / chapter_3_finance / chapter_4_conclusion）+ done 事件（含 session_id + report_docx_url + enterprise_profile + pending_questions + downstream_handoff）。
6. **依赖外部服务**：DEEPSEEK_API_KEY（真模式做 section 生成）；mock=1 完全离线（读 `mock_fixtures._EMBEDDED_STUBS`，内嵌预置 JSON）。
7. **降级路径**：
   - `llm_connected=false` 时前端状态灯变黄，仍可走 mock=1（演示无感）。
   - DeepSeek 崩时，真模式会在 write/audit 段 yield error；前端 catch 后可切 mock=1 重试 → 若再崩读 `/public/mock/report_fill_mock.json`，并**必须备 fallback docx**（`outputs/` 目录随便留一个历史生成的，downloads/legacy 能拿到）。
8. **前端可用 fixture schema**（建议主 CLI 补 `web/public/mock/report_fill_mock.json`，schema 对齐 SSE 事件）：
   ```json
   {
     "stages": [
       {"event":"stage","stage":"ingest","progress":0.2,"message":"..."},
       {"event":"stage","stage":"extract","progress":0.4,"message":"..."},
       {"event":"stage","stage":"infer","progress":0.6,"message":"..."},
       {"event":"stage","stage":"write","progress":0.8,"message":"..."},
       {"event":"stage","stage":"audit","progress":1.0,"message":"..."}
     ],
     "sections": [
       {"id":"chapter_1_background","title":"一、企业背景","content":"..."},
       {"id":"chapter_2_operation","title":"二、经营情况","content":"..."},
       {"id":"chapter_3_finance","title":"三、财务情况","content":"..."},
       {"id":"chapter_4_conclusion","title":"四、结论","content":"(待 Agent3 回填)"}
     ],
     "done": {
       "session_id":"mock-000",
       "report_docx_url":"/downloads/鼎盛商贸_mock.docx",
       "enterprise_profile":{"profile_id":"corp_dingsheng_001","company_name":"鼎盛商贸有限公司","..."},
       "pending_questions":[],
       "downstream_handoff":{"agent3_input":"..."}
     }
   }
   ```

---

## 前端 Stage 4 Task B 降级守卫实装建议

### 统一 worker pseudo-code（照抄模板）

```ts
// web/lib/agent-guarded-fetch.ts
export async function guardedFetch<T>(
  agentKey: 'channel'|'riskctrl'|'credit'|'alert'|'compliance'|'report',
  apiCall: () => Promise<T>,
  mockPath: string,
  timeoutMs = 2000,
): Promise<{ data: T; source: 'live'|'mock'|'disabled' }> {
  // riskctrl / alert 直接走 mock（无后端路由）
  if (agentKey === 'riskctrl' || agentKey === 'alert') {
    return { data: await fetch(mockPath).then(r => r.json()), source: 'mock' };
  }
  try {
    const timeout = new Promise<never>((_, rej) =>
      setTimeout(() => rej(new Error('timeout')), timeoutMs));
    const data = await Promise.race([apiCall(), timeout]);
    return { data, source: 'live' };
  } catch (e) {
    // 所有 5xx / network / timeout 都走 mock
    const fallback = await fetch(mockPath).then(r => r.json());
    return { data: fallback, source: 'mock' };
  }
}
```

### SSE 降级（channel / credit / report 共用）

```ts
// 流式读，任意 event.type === 'error' 或连接断 → reset + 播放 mock 的 events 序列
async function streamWithFallback(url, mockEvents) {
  try {
    const resp = await fetch(url, {method:'POST', body:...});
    const reader = resp.body!.getReader();
    // ... 解析 SSE, 任意 data.event === 'error' → throw
  } catch {
    // 本地播放 mockEvents，每 300ms 发一条，让 UI 看起来在流
    for (const ev of mockEvents) { emit(ev); await sleep(300); }
  }
}
```

### 全局 error boundary

- **每个 tile 独立 `<AgentTileErrorBoundary>`**，子组件崩不影响壳
- Boundary fallback UI 统一：`<MockCard agent={agentKey} reason="后端异常，已切换到 demo 数据" />`
- Agent5 特殊处理：直接 `<DisabledCard tooltip="Agent5 待 kb_scan 底座 + Phase 2 defer" />`

---

## 红区 + 风险清单（按演示当场爆雷概率降序）

1. **🔴 DeepSeek 限流/崩** → Agent6 报告 `/fill mock=0` 真跑失败、Agent3 `advising` 段失败、Agent1 `parse` 段失败。
   - **治本**：演示默认走 `mock=1`（报告）/ mock 池（channel）。
   - **兜底**：必须有 fallback docx 在 `outputs/` 里（前端 `/downloads/<name>.docx` 直下能拿到）。
2. **🔴 Tavily 限流/崩** → Agent1 `signal_scan` 段空、Agent5 policy_scan 直接空 list。
   - **治本**：前端 `mock: true` POST body 强制走内置 mock 池。
   - **兜底**：`/public/mock/channel_run.json` 内嵌 2 场景完整候选时间线。
3. **🟡 Agent5 结果质量** → policy_scan 返回的是泛政务网站（涉税报送、纪委），非金融监管，演示会尴尬。
   - **治本**：前端 tile disable，tooltip 写"Phase 2 defer"。
   - **或**：用 `/public/mock/compliance_policy_scan.json` 静态 3-5 条金融政策。
4. **🟡 Agent4/Agent2 无后端 API** → 前端若误调 `/api/alert/*` / `/api/riskctrl/*` 一律 404。
   - **治本**：前端这两个 tile 写死静态 fixture 源，不要尝试后端调用。
5. **🟡 Windows curl body 中文乱码** → 实跑 curl 传 JSON body 时遇到 `{"detail":"There was an error parsing the body"}`；浏览器 `fetch(JSON.stringify(body))` 不存在此问题（curl 在 Windows Shell 下 charset 问题）。
   - **治本**：前端不受影响；主 CLI 后续实跑用 `py urllib.request` 代替 curl POST。
6. **🟢 Session 目录 TTL** → `/api/report/fill mock=0` 生成的 session_dir 30min 自动清理，演示期间 1 小时内不重复。

---

## 演示前主 CLI 必做 checklist

### A. 必须补的 mock fixture（主 CLI 后续要写的文件）

- [ ] `web/public/mock/channel_run.json` — 2 场景 + run_mock_events 序列（schema 见 Agent1 第 8 条）
- [ ] `web/public/mock/credit_decision_corporate.json` — dingsheng_trade 决策 SSE 全序列（schema 见 Agent3 第 8 条）
- [ ] `web/public/mock/credit_decision_retail.json` — zhangsan_restaurant 决策 SSE 全序列
- [ ] `web/public/mock/alert_hitlist.json` — 从 `evaluation/manual/4_20260419.yaml` 转 JSON（schema 见 Agent4 第 8 条）
- [ ] `web/public/mock/compliance_policy_scan.json` — 手写 3-5 条金融监管 fixture（或 tile disable）
- [ ] `web/public/mock/report_fill_mock.json` — 5 stages + 4 sections + done（schema 见 Agent6 第 8 条）
- [x] `web/public/mock/riskctrl_ruleset.json` — **已就位**（Phase 1 Task D 落盘）

### B. 回跑验证

- [ ] 后端启动：`py -m uvicorn api_server:app --port 8000`
- [ ] 6 tile 顺序开一遍，每个 tile 断网再开一遍，确保都有兜底 UI
- [ ] DeepSeek 关 key 重启后端，Agent6 `/fill mock=1`、Agent3 `/decision` 仍能展示前 4 段结构化结果
- [ ] Tavily 关 key 重启后端，Agent1 `/run mock=true` 仍能完整跑 5 段

### C. 前端 demo-mode 总开关

- [ ] 建议加 `NEXT_PUBLIC_DEMO_MODE=offline` env：为 true 时所有 tile 直接走 mock fixture（演示彻底离线），默认 false 走真 API + 降级
- [ ] Masthead persona（王哲·客户经理·华东）旁边加一个不显眼的 🔌 指示灯，鼠标悬停显示当前是 live / mock / offline

### D. 演示路径推荐（低风险 → 高风险）

1. **今日 view** → **对话 view**（纯前端）
2. **AI 助手 → Agent6 报告（mock=1）**（最稳，全离线）
3. **Agent3 授信 → dingsheng_trade**（scoring+rule+case 确定性段稳）
4. **Agent1 获客 → mock=true**（strcase 完整 5 段）
5. **Agent2 风控 ReadOnly**（纯 mock json）
6. **Agent4 预警 dashboard stub**（纯 mock json）
7. **Agent5 合规**（disabled tile / defer tooltip）

---

## 附录 · 实跑命令 copy-paste（主 CLI 本轮已验证）

```bash
# 启动
cd "D:/claude code/credit_report_agent_work"
py -m uvicorn api_server:app --host 127.0.0.1 --port 8000

# Health
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/api/report/health

# Agent1
curl -s http://127.0.0.1:8000/api/channel/scenarios

# Agent3
curl -s http://127.0.0.1:8000/api/credit/presets/corporate
curl -s http://127.0.0.1:8000/api/credit/presets/retail

# Agent5
curl -s "http://127.0.0.1:8000/api/compliance/policy_scan?query=报送制度&limit=3"

# Agent6
curl -s http://127.0.0.1:8000/api/report/preset/dingsheng_trade
curl -s http://127.0.0.1:8000/api/report/preset/zhangsan_restaurant

# SSE（Windows 下用 python 代替 curl，避免 body 乱码）
py -c "import json,urllib.request; body=json.dumps({'query':'杭州精密制造','provider':'deepseek','top_n':3,'mock':True}).encode(); req=urllib.request.Request('http://127.0.0.1:8000/api/channel/run', data=body, headers={'Content-Type':'application/json'}, method='POST'); [print(l.decode('utf-8',errors='replace').rstrip()) for l in urllib.request.urlopen(req, timeout=60)]"

py -c "import json,urllib.request; body=json.dumps({'segment':'corporate','preset_name':'dingsheng_trade','provider':'deepseek'}).encode(); req=urllib.request.Request('http://127.0.0.1:8000/api/credit/decision', data=body, headers={'Content-Type':'application/json'}, method='POST'); [print(l.decode('utf-8',errors='replace').rstrip()) for l in urllib.request.urlopen(req, timeout=120)]"

py -c "import urllib.request; req=urllib.request.Request('http://127.0.0.1:8000/api/report/fill?mock=1&preset=dingsheng_trade&business_line=corporate', method='POST'); [print(l.decode('utf-8',errors='replace').rstrip()) for l in urllib.request.urlopen(req, timeout=60)]"
```
