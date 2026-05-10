# Report Phase B.2 Audit · 不可 GO 条件 + 改造 checklist

> 生成: 2026-05-10 · worker: report · 触发: Phase B.2 dispatch (PM 2026-05-10 真意 reframe)
> 方法: grep mock_fixtures / mock_pipeline / scenario / fixtures.ts / NotImplementedError +
>   Read /api/report/* 全端点 + Read v16_runner.py + Read web/src/lib/api/report.ts +
>   Read ReportWorkspace.tsx ReportDemoStrip
> 状态: pre-execution · 等 PM verify 复述后立即干 (此 doc 本身入 commit)

---

## 致命 #1 · /api/report/demo/run 当前是纯 fixture · 不真跑 v16

**位置**: `agent_report/api.py:1032-1144`

**现状**:
- Input: `scenario_id ∈ {easy, medium, hard}` (per dispatch §"禁止用" 简单档)
- 加载 `data/mock/workspace/report/scenarios/<id>.json`
- yield 假 stage events + 预编 sections array
- yield done event w/ `data_source: "mock_forced"` + `mock_pipeline: True`
- **完全不调 v16_runner / fill_stream** · "yield fixture event" 反模式

**改造方向 (主活 A · Step 2)**:

```python
class ReportDemoRunRequest(BaseModel):
    sample_id: str   # "DP001_龙峰精工" | "DP002_..." (data/mock/deep-pillar/<id>/)

@app.post("/api/report/demo/run")
async def report_demo_run(req, _user):
    # 1. 校验 sample dir 存在
    sample_dir = PROJECT_ROOT / "data" / "mock" / "deep-pillar" / req.sample_id
    if not sample_dir.is_dir():
        raise HTTPException(404, ...)

    # 2. 校验 classifier 产物 (per template)
    classified = PROJECT_ROOT / "outputs" / "v16_llm_classified.json"
    if not classified.exists():
        raise HTTPException(503, "DEMO_CLASSIFIER_MISSING · 请 admin pre-run v16_classifier")

    # 3. 校验 LLM key (real path 必需)
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise HTTPException(503, "DEEPSEEK_KEY_MISSING")

    # 4. 调用 fill_stream 真路径 (explicit_mock=False)
    return StreamingResponse(fill_stream(
        report_id=...,
        source_docx=PROJECT_ROOT / "samples" / "经纬测绘_对公成稿A.docx",  # 默认对公模板
        material_dir=sample_dir,                                           # DP001 真材料
        classified_json=classified,                                        # 预跑 cache
        output_dir=PROJECT_ROOT / "outputs",
        explicit_mock=False,                                                # 真 LLM 跑
    ))
```

**符合 PM 真意**: 演示 = 上传 sample (DP001 真材料) → 真后端 (v16_pipeline classifier-cached + generator + QC) → 真返结果。

---

## 致命 #2 · 前端 ReportDemoStrip 3-档难度按钮

**位置**: `web/src/app/archive/report/_components/ReportWorkspace.tsx:1780-1854` · `streamReportDemoRun` consumer line 376-416

**现状**:
- 3 button: 简单 · 材料齐全 / 中等 · 部分缺 / 困难 · QC 阻断
- testid: `report-demo-easy/medium/hard`
- 注释: "Phase A worker-A4 · 反 5 原则 §3.5 难度分层" (现 dispatch 明确禁止)
- 调 `streamReportDemoRun({scenario_id: "easy"})` → POST /api/report/demo/run

**改造方向 (主活 B · Step 3)**:
- 删 ReportDemoStrip 整个 component
- 加 ReportSampleStrip (新名 · 沿原位置):
  - 单 dropdown / 5 button (DP001-DP005 真企业 sample)
  - 旁边一句 "加载示例真材料 → v16 主管线真跑"
- 改 `streamReportDemoRun({sample_id: "DP001_龙峰精工"})`
- testid: `report-sample-DP001` 等

---

## 致命 #3 · TypeScript demo run 接口签名

**位置**: `web/src/lib/api/report.ts:267-328`

**现状**:
```typescript
export type ReportDemoRunRequest = {
  scenario_id: "easy" | "medium" | "hard";
};
```

**改造方向**:
```typescript
export type ReportDemoRunRequest = {
  sample_id: string;  // e.g. "DP001_龙峰精工" · 后端校验 dir 存在
};
```

---

## 待清理 · 数据 fixture 残留

**位置**: `data/mock/workspace/report/scenarios/{easy,medium,hard}.json`

**现状**: 6KB-8KB 简单档预编 sections fixture · dispatch §"禁止用"

**改造方向**: 直接删 (3 文件) + 删 `_REPORT_SCENARIO_DIR` const + 不再 ref

---

## OK · 不需改

| 检查点 | 状态 | 说明 |
|---|---|---|
| `/api/report/v16/fill` real path | ✅ OK | B step 3 已 fail-fast 503 · 走 fill_stream(explicit_mock=False) → real_v16_stream → _run_v16_in_thread → 真 v16_pipeline |
| ModePill / demoModeAvailable | ✅ OK | 此 commit merge upstream/main 已清完 (B.1.3 revert) |
| `mock_pipeline: True` | ⚠ 留 | mock_v16_stream 路径仍标 (作 explicit_mock test path) · `/v16/fill?mock=true` 仅 admin · 不在 demo/run 路径触发 |
| DataSourceBadge 5-enum | ✅ OK | SSOT trust 标 · 真 live 时显 "live" · 假 demo 显 "mock_forced" |
| candidate-identity-contract section.id | ✅ OK | B step 4-5 已 ensure_list_unique_ids · 改造时 carry over |
| EvidenceDrawer 字段级 evidence | ✅ OK | B step 4 已落 · mock_v16_stream + real_v16 都挂 evidences array |
| entity_resolver entity_key | ✅ OK | B step 6 已落 · enterprise_profile.entity_key + handoff_id 派自 entity_key |
| `/v16/inject` ledger 上链 | ✅ OK | per CLAUDE.md §3.7.5 · BE7 default agent=report retention=long(10y) |

---

## 不可 GO 条件 vs 我现状 (dispatch §"不可 GO 条件")

| # | 条件 | 现状 | Step 2+ 后 |
|---|---|---|---|
| 1 | /demo/run yield fixture | ❌ **致命** (line 1032-1144) | ✅ 改 fill_stream 真路径 |
| 2 | fixtures.ts import | ✅ 已删 (B step 1) | ✅ 维持 |
| 3 | ModePill 残留 | ✅ 已删 (此 merge 清) | ✅ 维持 |
| 4 | silent fallback fake | ✅ B step 3 已 fail-fast | ✅ 维持 |
| 5 | NotImplementedError raise | ⚠ section_supplement scaffold (line 1157+ ack only · 不 raise · 留 Phase B-3) | ✅ ack-only 不 raise · OK |
| 6 | channel 单 Tavily 无降级 banner | N/A (channel 主) | N/A |
| 7 | 评分都一样 | N/A (channel 主) | N/A |
| 8 | 47 分 D 级假分残留 | N/A (credit 主) | N/A |
| 9 | 监管条款无 hash | N/A (compliance 主) | N/A |
| 10 | 无 `E2E_EVIDENCE_URL` trailer | ⏳ Step 11 主活 D | ✅ admin 真号 E2E 4 件套 |

---

## §3.5 数据归属 · report 列

| 类型 | 内部 mock 保留 (输入契约) | 外部源 (改真) |
|---|---|---|
| report | `data/mock/deep-pillar/DP001-005/` (真材料 PDF/xlsx/docx · 反 5 原则 §3.5 #3 真实来源锚定 + #4 脱敏再造) | 无 (报告无外搜 · 仅材料解析 + LLM 三阶段 generator) |

**含义**: Step 2 主活 A 把 sample_dir 作 material_dir · 输入侧 mock 保留 · 后端处理全真 (LLM/Tavily/算法不变 per dispatch).

---

## 11 step 推进路线 (本 worker · 自我对照)

| Step | 状态 | Done by |
|---|---|---|
| 0 PM真意复述 | ✅ 12fb6f8 RESUMED commit | Step 0 done |
| 1 PM真意确认 | ✅ Step 0 已 cover | - |
| 2 /demo/run 真跑 backend | ⏳ Task #3 | 主活 A |
| 3 UI 形态切换 | ⏳ Task #4 | 主活 B |
| 4 UI 空状态 / 排版 / 错误态 | ⏳ Task #5 | 主活 C |
| 5 错误降级 typed banner | ⏳ Task #6 | (重叠 4) |
| 6 §3.5 表 (内部保留 · 外部改真) | ✅ 已对齐 (本 doc) | - |
| 7 信息密度 折叠默认改展开 + 主 CTA + 大空白填示例 | ⏳ Task #7 | (前端 redesign) |
| 8 unique id (candidate-identity-contract v1.1) | ✅ B step 5 已落 carry over | - |
| 9 evidence drawer 真 wire | ✅ B step 4 已落 · grep REPORT_EVIDENCE 0 命中 | - |
| 10 ledger 上链 | ✅ /v16/inject 已上链 (BE7) · export_docx/pdf 是否上链待 PM ruling | - |
| 11 admin 真号 E2E 4 件套 | ⏳ Task #9 | 主活 D |

---

## 红线自检 (10 条 stop-the-line · pre-execution)

| # | 红线 | 现 status | Step 2+ 后必须 |
|---|---|---|---|
| 1 | 假 live (silent fallback mock) | ⚠ /demo/run 当前完全假 | ✅ 改 fill_stream(explicit_mock=False) |
| 2 | 假分 (无证据评分) | ✅ B step 4 字段级 evidence | 维持 |
| 3 | 无证据 claim | ✅ EvidenceDrawer 字段级 source · evidence_date | 维持 |
| 4 | v16 stub 冒充真源 | ⚠ data_source=mock_forced 标 · 但 demo/run 是 fixture | demo/run 真跑后 data_source=live |
| 5 | 无决策账本 | ✅ /v16/inject 已上链 · export 待 PM ruling | export 上链 PM ruling |
| 6 | 无源健康 | N/A (channel 主) | - |
| 7 | 评分无回测 | N/A (riskctrl 主) | - |
| 8 | 监管条款无 hash | N/A (compliance 主) | - |
| 9 | 审批/贷后反馈丢链路 | ✅ entity_key + handoff_id 派自 entity_key | 维持 |
| 10 | SSE 展示与落库不一致 | ✅ data_source 同源 · sections 同源 | demo 改真后落 store · session_id UUID4 不再 demo_report_* prefix |
