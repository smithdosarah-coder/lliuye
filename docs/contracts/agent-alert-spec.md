# Agent4 Alert · Spec for Stage C Worker

> **Source PRD**: `docs/PRD_贷中风险预警助手_v2.0.md` (canonical · v1.0 已废)
> **Workspace route**: `/archive/alert` (canon, 见 CLAUDE.md §7)
> **Backend module**: `agent_alert/api.py` (FastAPI v3.1 · 已挂载 · session 9 一份 endpoint `/scan`) + `customer_scanner.py` 编排 + `cross_matcher.py` 双路交叉
> **Stage C 任务**: KB_DEMO 解锁稳定 (Tavily fallback / 缓存) + 红/黄/绿榜单 + panel hoist + 处置建议
> **架构定位**: 知识库扫描雷达 (KnowledgeBase → ScanTargets → CrossMatcher → HitList) · 与 Agent1/5 共享底座

---

## 1. Product Positioning

Agent4 是**知识库驱动的批量贷中预警扫描雷达**——客户上传"在贷客户池 + 预警规则库 + 内部制度"三类知识库，Agent 批量遍历，对每家客户做"外部信号（裁判文书 / 工商 / 舆情 / 失信）× 内部规则（本行制度 / 限额 / 白黑名单）"双路交叉命中，输出红/黄/绿三级客户榜单 + 单客户证据链 + 处置建议。

**与 v1.0（单查工具）根本区别**：v1.0 = "输一家企业 → 红黄绿信号灯"（客户问"能一次扫完我 1 万家吗"产品哑火）· v2.0 = "上传全量客户池 → 100 家 2 分钟扫完吐分级榜单"（贷后岗每日晨会场景真痛点）。

**触发源**：Agent4 是**客户行为变化驱动**（不是 Agent5 的政策事件驱动）· 详见 CLAUDE.md §4 边界。

**反"伪雷达"3 硬线** (PRD §2.2)：
1. 上传必须是知识库（多文件多类型），不是企业名 / 单文件
2. 扫描必须批量并发观感（进度条 + tick + 榜单实时增长）
3. 输出必须是榜单形态（不是单企业报告）· 客户可在榜单切不同客户看不同证据链

---

## 2. Capabilities (Numbered · Stage C Worker 逐项实装并打 ✓)

- [ ] **C1 三槽位 KB 上传** · 客户名录 (xlsx/csv) · 预警规则库 (json/yaml/xlsx) · 内部制度 (docx/pdf) · 三槽都满才能"开始扫描"
- [ ] **C2 KB 解析与摘要** · `AlertKnowledgeBase.from_uploads()` · 输出"100 家在贷客户 · 20 条规则 · 1 份本行小微信贷风险管理办法（4200 字）"
- [ ] **C3 RuleExtractor (内部制度→规则)** · LLM 抽取 4200 字制度 → ≥15 条 PolicyClause · 字段完整率 100% · 失败 chunk 跳过
- [ ] **C4 CustomerScanner 批量扫描** · `asyncio.Semaphore(8)` 并发 · `on_progress` 回调推 SSE tick · `on_hit` 实时推命中事件 · 100 家 ≤ 2 分钟（缓存 ≤ 10 秒）
- [ ] **C5 双路交叉命中 (CrossMatcher)** · 外部路径: `SearchProvider.query()` + `alert_engine.evaluate_alerts()` (22 条规则保留 v1.0) · 内部路径: 逐 PolicyClause LLM 判定 · 交叉合并 (外+内都中→红 · 仅外或仅内→黄 · 都未中→绿)
- [ ] **C6 处置建议生成 (LLM 批量)** · 仅红/黄灯客户 · `disposition.py` 保留 v1.0 · 批量 prompt 一次返多家话术 · 输出 `DispositionPlan` (紧急度 + 行动 + 责任方 + 时限)
- [ ] **C7 三级榜单 (RiskLedger)** · `red[]` / `yellow[]` / `green[]` · 默认排序"命中规则数 × 级别权重" · 支持切按授信余额排序 · 顶部统计条 `🔴 N 🟡 M 🟢 K`
- [ ] **C8 顶部 Tab 视角切换** · "按客户" / "按规则" / "按部门"（共享 Agent5 矩阵视图概念）· 不同视角不同左栏组织
- [ ] **C9 客户详情面板 (DrillDetail)** · 选中客户 → 中间面板 (画像卡 + 命中规则清单 + 证据链) · 双路来源标注 (color block 外/内)
- [ ] **C10 证据链可追溯** · 外部证据带 URL · 内部证据带条款原文 + 制度文件名 + 第 X 条 · 不依赖任何 hallucinated content
- [ ] **C11 Excel 榜单导出** · 4 sheet (高风险 / 中风险 / 低风险 / 规则清单 / 制度条款) · ≤ 3 秒 · `openpyxl` 本地
- [ ] **C12 PDF 处置单导出 (单客户)** · `reportlab` · 含画像 + 证据链 + 处置建议 · 客户经理可凭证走流程
- [ ] **C13 SSE 三阶段流** · `kb_loaded` → `scanning_progress` (X/Y + 实时 tick) → `done` · 取消按钮中止扫描保留已扫描结果
- [ ] **C14 SearchProvider 抽象** · `MockProvider` (demo_mode=True · 完全 offline) / `TavilyProvider` (生产) / `BaiduNewsProvider` (生产 stub) · 切一行 demo_mode 即可
- [ ] **C15 LLM 缓存** · 预置场景全量缓存到 `mock_data/cache/{scenario_id}/` · 演示重播秒出
- [ ] **C16 失败容忍** · 单家扫描失败重试 1 次 · 仍失败标记 `status: scan_failed` · 不阻断全流程 · 失败家数显示在状态区
- [ ] **C17 交叉命中可解释** · 每条命中明确：硬规则触发？LLM 判定？阈值是多少？实际值是多少？

---

## 3. Input Shape

| 维度 | 形态 |
|---|---|
| **触发源 1** | 客户经理 / 贷后岗在 `/archive/alert` workspace 主动发起（晨会扫描 / 月度组合体检） |
| **触发源 2** | IM `@alert 扫描我的小微贷组合` |
| **触发源 3 (定时)** | 后端 cron 每日凌晨自动扫一次 · 结果落 `data/audit/alert_daily/` |
| **KB 文件类型** | 客户名录 xlsx (`customer_id / name / credit_line / outstanding / due_date / industry / region / manager / internal_rating` 必填) · 规则库 json (`AlertRule` schema) · 内部制度 docx/pdf |
| **预置场景** | 2 个 · `micro_credit_100` (小微信贷组合 · 100 家 · 3R+7Y+90G) · `supply_chain_100` (供应链汽车零部件 · 100 家 · 1R+12Y+87G) |
| **可调参数** | `max_concurrency` (默认 8) · `level_weights` (red 3 / yellow 2 / green 1) · `force_mock` (DEMO MODE · 完全 offline) |

---

## 4. Output Shape

### 4.1 UI 渲染 (panel 级 · 见 §7)

- **HeroBanner** · 顶部统计条 (扫描 N 家 · 🔴 X · 🟡 Y · 🟢 Z · 用时 MM:SS)
- **UploadDropZone** · 三槽位上传 (客户名录 / 规则库 / 内部制度) · 每槽位识别预览 · 场景快捷按钮
- **ScanProgress** · 进度条 `已扫 X / Y` + tick 流（时间戳 + 企业名 + 命中等级 + 命中规则 ID）+ 累计 R/Y/G 计数
- **HitList** (左栏) · 三段分组 (🔴 红 / 🟡 黄 / 🟢 绿默认折叠) · 条目 (企业名 + 授信额 + 命中规则数 + 最高级别图标) · 搜索 + 多选批量
- **DrillDetail** (中栏) · 选中客户 (画像卡 + 命中规则清单 + 证据链 · 双路标注 + 趋势小图)
- **DispositionCards** (右栏) · 处置建议卡片列表 · 每卡 (紧急度配色 + 行动描述 + 责任方标签 + 时限) · 勾选 "已执行 / 已忽略" 状态
- **TrafficLight** (Wave 2 已挂 · L1-3 红黄绿) · `[data-testid="alert-traffic-light"]` · 不许移除
- **SignalMap** · 全局信号热力图 · 按行业 × 信号类型分布
- **RuleStatus** · 规则集激活状态 · 命中次数排序
- **ConversationPanel** · IM 风对话气泡

### 4.2 文件导出

| 文件 | 后端端点 | 内容 |
|---|---|---|
| **榜单 Excel** | `POST /api/alert/export_xlsx` (Stage C 新建) | 4 sheet · 全部 R/Y/G 客户 + 命中规则 + 处置建议 |
| **处置单 PDF (单客户)** | `POST /api/alert/export_pdf` (Stage C 新建) | reportlab · 单客户证据链 + 处置 |
| **扫描快照 JSON** | runtime_dump（已实装 `agent_alert.runtime_dump`）| `evaluation/manual/4_*.yaml` (894 行 · 100 客户 · tool_calls 200/200) |

---

## 5. Backend Endpoints

### 5.1 已实装 (api.py v3.1)

| 方法 | 路径 | 请求 | 响应 |
|---|---|---|---|
| GET | `/api/alert/health` | — | `{status, agent: "agent_alert"}` |
| POST | `/api/alert/scan` | `{scenario_key, uploaded_files?, provider?, api_key?}` | **SSE** · stage events + done (见 §5.3) |

### 5.2 Stage C 新建端点

| 方法 | 路径 | 请求 | 响应 | 备注 |
|---|---|---|---|---|
| GET | `/api/alert/scenarios` | — | `{scenarios: [{key, name, desc, customer_count, expected_red, expected_yellow}]}` | 列出预置场景 · 与 Agent1 风格对齐 |
| POST | `/api/alert/upload_kb` | multipart · `kb_type: customers/rules/policy` · `files[]` | `{kb_id, kb_summary}` | 三槽位独立上传 |
| GET | `/api/alert/hitlist/{session_id}` | path | `{red[], yellow[], green[], stats}` | 完整 RiskLedger 拉取（SSE 之外的兜底） |
| GET | `/api/alert/drill/{customer_id}` | path | `{customer, external_signals, internal_hits, evidence_chain, disposition}` | 单客户详情 |
| POST | `/api/alert/export_xlsx` | `{session_id, customer_ids?: string[]}` | xlsx file (`Content-Disposition`) | 全量或选中导出 |
| POST | `/api/alert/export_pdf` | `{session_id, customer_id}` | pdf file | 单客户处置单 |
| POST | `/api/alert/cancel/{session_id}` | path | `{cancelled: true, scanned_so_far: N}` | 中止扫描保留已扫结果 |

### 5.3 SSE 事件契约

```jsonc
// event: stage (KB 装载 + 制度抽取 + 扫描启动)
{"event": "stage", "stage": "kb_loaded", "payload": {"customers": 100, "rules": 20, "policy_clauses": 18}}

// event: hit (扫描中实时推命中 · 前端 tick 流追加)
{"event": "hit", "payload": {"customer_id": "LC10001", "name": "华联精密制造", "level": "red", "matched_rule_ids": ["FIN-002", "LAW-001", "POL-003"], "scan_time_ms": 0.42}}

// event: progress (定期推 · 不阻塞 hit)
{"event": "progress", "payload": {"scanned": 63, "total": 100, "elapsed_seconds": 78}}

// event: done
{
  "event": "done",
  "payload": {
    "session_id": "...",
    "version": "runtime-v1",
    "generated_at": "2026-04-27T...",
    "source": {"agent": "alert", "kb_scenario": "...", "search_provider": "MockSearchProvider (demo_mode=True)"},
    "summary": {"total": 100, "red": 10, "yellow": 0, "green": 90},
    "customers": [
      {
        "entity_id": "LC10001",
        "name": "华联精密制造有限公司",
        "grade": "red",
        "trigger_reasons": ["cross_hit"],
        "external_signals": [{"rule_id": "FIN-002", "title": "净利润转负", "evidence": {...}}],
        "internal_hits": [{"clause_id": "POL-003", "article": "第 14 条", "match_reason": "...", "source_text": "..."}],
        "evidence_chain": [{"source_type": "external", "provider": "tavily", "url": "...", "snippet": "..."}],
        "disposition": {"items": [{"urgency": "立即", "action": "48h 现场核查", "owner": "客户经理", "deadline": "2026-04-29"}]},
        "scan_time_ms": 0.42,
        "status": "completed"
      }
    ],
    "tool_calls": {"total": 200, "success": 200}
  }
}

// event: error
{"event": "error", "message": "...", "traceback": "..."}
```

### 5.4 降级路径

- **后端未挂载 (Phase 1 时段)** → 前端走 `/public/mock/alert_hitlist.json` 静态 fixture（从 `evaluation/manual/4_20260419.yaml` 转 JSON · session 9 已规划）
- **Tavily 限流** → SearchProvider 降级 MockProvider · 单客户标 `data_source: "mock_fallback"`
- **DeepSeek 崩** → CrossMatcher 内部条款 LLM 判定阶段降级（仅外部信号判级）· 黄灯 fallback
- **单客户失败** → 重试 1 次 · 失败标 `status: scan_failed` 不阻断 · 显示在状态区
- **取消** → 2 秒内停止 · 保留已扫描的红/黄客户

---

## 6. Mock Sessions Structure (≥3)

### 6.1 Top-level shape

```typescript
type AlertMockSession = {
  session_id: string;
  scenario_key: string;
  display_name: string;
  generated_at: string;
  source: { agent: "alert"; kb_scenario: string; search_provider: string };
  summary: { total: number; red: number; yellow: number; green: number };
  customers: AlertCustomer[];
  tool_calls: { total: number; success: number };
};
```

### 6.2 三个标杆 session

| session_id | scenario | 客户数 | R/Y/G | 演示卖点 |
|---|---|---|---|---|
| `alert-micro-001` | micro_credit_100 | 100 | 3/7/90 | 小微贷红灯华联精密制造 · 三路命中 (财务恶化 + 涉诉 + 关联方重整) |
| `alert-supply-001` | supply_chain_100 | 100 | 1/12/87 | 供应链汽车零部件 · 行业景气下行传染 · 应收账款周转恶化 |
| `alert-real-estate-001` | real_estate_50 (新增 · master plan B.1 锚) | 50 | 5/10/35 | 房地产开发贷 · 政策收紧场景 · 监管处罚红线 |

### 6.3 单客户数据契约

```typescript
type AlertCustomer = {
  entity_id: string;              // "LC10001"
  name: string;
  credit_line_yuan: number;       // 授信额（元，不带"万"字符串）
  outstanding_yuan: number;
  due_date: string;
  industry: string;
  region: string;
  manager: string;
  internal_rating: string;
  grade: "red" | "yellow" | "green";
  trigger_reasons: string[];      // ["cross_hit", "external_only", "internal_only"]
  external_signals: Array<{
    rule_id: string;
    rule_name: string;
    severity: "high" | "medium" | "low";
    evidence: { source: string; url?: string; snippet: string };
  }>;
  internal_hits: Array<{
    clause_id: string;
    article: string;              // "第 14 条"
    source_document: string;      // "本行小微信贷风险管理办法"
    match_reason: string;
    source_text: string;
    confidence: number;           // 0-1
  }>;
  evidence_chain: Array<{
    source_type: "external" | "internal";
    provider: string;
    title: string;
    snippet: string;
    url: string;
    timestamp: string;
  }>;
  disposition: {
    items: Array<{
      urgency: "立即" | "高优" | "常规";
      action: string;
      owner: "客户经理" | "风险管理部" | "法务部" | "合规部";
      deadline: string;
    }>;
  };
  scan_time_ms: number;
  status: "completed" | "scan_failed" | "skipped";
};
```

---

## 7. Panel Architecture (`/archive/alert/_components/`)

| Panel 组件 | 数据源 (props) | 切 session 重渲 | 客户 click 联动 |
|---|---|---|---|
| `AlertHero.tsx` | `summary` + `tool_calls` + duration | ✓ | — |
| `UploadDropZone.tsx` | upload state | ✓ | — |
| `ScanProgress.tsx` | progress + tick stream | ✓ | — |
| `HitListPanel.tsx` | `red[] / yellow[] / green[]` · `onSelect(customer_id)` | ✓ | — |
| `DrillDetailPanel.tsx` | selected customer | ✓ | ✓ (主) |
| `DispositionCards.tsx` | selected customer.disposition | ✓ | ✓ |
| `TrafficLight.tsx` (Wave 2 · 不许移除) | summary | ✓ | — |
| `SignalMap.tsx` | aggregate signals 全局热力 | ✓ | — |
| `RuleStatus.tsx` | rule activation stats | ✓ | — |
| `ConversationPanel.tsx` | thread | — | — |

### 7.1 Panel state hoist (master plan C.3)

```typescript
const [selectedSessionId, setSelectedSessionId] = useState(MOCK_SESSIONS[0].session_id);
const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null);
const [scanProgress, setScanProgress] = useState<{ scanned: number; total: number } | null>(null);
const [hitTicks, setHitTicks] = useState<HitTickEvent[]>([]);
const [livePayload, setLivePayload] = useState<RiskLedger | null>(null);
const [mode, setMode] = useState<"mock" | "live">("mock");
const [view, setView] = useState<"by_customer" | "by_rule" | "by_dept">("by_customer");
```

### 7.2 路由 + 红线

- ✅ 唯一入口 `/archive/alert`
- ❌ 禁顶层 `/alert` (legacy)

---

## 8. Regression Risks

| ID | Feature | Selector | 验证 spec |
|---|---|---|---|
| F-traffic-light | TrafficLight (Wave 2 · L1-3) | `[data-testid="alert-traffic-light"]` | `web/tests/alert-traffic-light.spec.ts` |
| F-evidence-trail | EvidenceTrail (Wave 2) | `[data-testid="evidence-trail"]` | `web/tests/evidence-trail.spec.ts` |
| F-conversation-panel | ConversationPanel (Wave 2 · alert codex fusion 已合) | `[data-testid="conversation-panel"]` | `web/tests/conversation-panel.spec.ts` |

**v1.0 资产 PRESERVE**：
- `alert_engine.py` (22 条规则 + 红黄绿分级) · 0 改动
- `disposition.py` (LLM + 模板处置建议) · 批量调用复用
- `trend_analyzer.py` (财务趋势) · 可选补充信号
- `prompts.py` (SYSTEM_RISK_SCAN / SYSTEM_TREND / SYSTEM_DISPOSITION) · 保留 + 追加批量

**红区禁触**（共享 kb_scan/）：
- `shared/kb_scan/models.py` 改 `CompanyProfile` / `IdealProfile` / `HitItem` schema → RFC
- `shared/kb_scan/knowledge_base.py` 改 `KnowledgeBase` Protocol → RFC
- `shared/kb_scan/matcher.py` 改 `Matcher` Protocol → RFC
- 黄区 `shared/sources/impls/*.py` 追加新 source 自由

---

## 9. LLM 调用预算 (PRD §7.2)

| 调用点 | 频次 | 模型 | Temp |
|---|---|---|---|
| **管理制度条款抽取** | 1（全量制度一次性）| DeepSeek-chat | 0.2 |
| **单客户风险扫描** | 100/session（每客户 1 次）| DeepSeek-chat | 0.3 |
| **内部条款命中判定** | 100/session（批量判定 · 每客户全部条款一次）| DeepSeek-chat | 0.2 |
| **批量处置建议** | ~10/session（仅 R/Y · 5/批合并）| DeepSeek-chat | 0.5 |

**Demo 总预算**：100 家 ~211 次 LLM · 缓存命中后 ~10 次

**性能 SLA (PRD §10.1)**：
- 100 家扫描 P95 ≤ 2 分钟
- 单客户详情切换 ≤ 500ms
- Excel 导出 100 家 ≤ 3 秒
- 内存峰值 ≤ 512MB

---

## 10. Acceptance for Stage C

- [ ] 17 个 capability (§2 C1-C17) 全 ✓
- [ ] 7 个新端点 (§5.2) 真跑通
- [ ] 10 个 panel (§7) 全 props 化
- [ ] 3 个 mock session (§6) 落 `web/lib/mock-sessions.ts` (含从 `evaluation/manual/4_*.yaml` 转 JSON)
- [ ] 5 个 Playwright smoke pass (alert-mock-switch / alert-live-scan / alert-drill-detail / alert-export-xlsx / alert-cancel-mid-scan)
- [ ] features-inventory.md F-traffic-light / F-alert-* entries
- [ ] commit trailer 必含 `PRESERVES: F-traffic-light, F-evidence-trail, F-conversation-panel`
- [ ] tsc --noEmit 0 error · ECS deploy verify 通

---

## 11. References

- 上游 PRD: `docs/PRD_贷中风险预警助手_v2.0.md`
- API map: `docs/contracts/shell-v1-agent-api-map.md` § Agent 4
- Agent5 spec (共享 kb_scan 范式): `docs/contracts/agent-compli-spec.md`
- 字段命名: `docs/contracts/field-naming.md`
- 共享变更协议: `docs/contracts/shared-change-protocol.md`
- Master plan: `docs/contracts/master-execution-plan-2026-04-27.md` § Stage C.3
- runtime_dump 产物: `evaluation/manual/4_20260419.yaml` (894 行 · 100 客户 baseline)
- alert dashboard stub: `docs/design/alert-dashboard-stub.md` (UI 实装参考)
- Workspace state: `docs/contracts/workspace-state-protocol.md` (待 A2 worker)
