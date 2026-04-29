# Agent5 Compliance · Spec for Stage C Worker

> **Source PRD**: `docs/PRD_合规巡检智能体_v2.0.md` (canonical · v1.0 已废)
> **Workspace route**: `/archive/compliance` (canon, 见 CLAUDE.md §7)
> **Backend module**: `agent_compliance/api.py` (FastAPI v3.1 · 仅 1 endpoint policy_scan · 待 Stage C 扩) + `matrix_matcher.py` 矩阵比对 (核心新建)
> **Stage C 任务**: 政策事件驱动 + 业务矩阵扫 + KB_DEMO 解锁 + panel hoist
> **架构定位**: 知识库扫描雷达 N×M 矩阵 (规则集 × 事件集) · 与 Agent1/4 共享底座

---

## 1. Product Positioning

Agent5 是**知识库驱动的批量合规扫描雷达**——客户上传"监管政策（N 份）+ 内部制度 + 业务数据（M 条）"三类知识库，Agent 把政策拆成规则集、业务拆成事件集，做 N×M 矩阵比对，吐出严重 / 一般 / 观察 三级违规榜单 + 单违规详情（精确到业务单号）+ 整改建议。

**与 v1.0（一对一对比）根本区别**：v1.0 = "上传 1 份政策 + 1 份业务记录 → LLM 对比"（客户问"我有几十份政策 × 几万条台账"产品哑火）· v2.0 = "条款 × 事件 矩阵全扫，定位到具体业务单号"。

**触发源**：Agent5 是**政策事件驱动**（不是 Agent4 的客户行为驱动）· 详见 CLAUDE.md §4 边界。新政策发布 → Agent5 拉取 → 抽规则 → 扫存量业务 → 输出违规清单。

**与 Agent4 的对偶**：
- Agent4 = 双路交叉（外部信号 × 内部规则 · 单客户多维深入）
- Agent5 = 矩阵比对（规则集 × 事件集 · N×M 全扫）
- 共用 `KnowledgeBase` / `Matcher` 接口和雷达视觉范式

**反"伪雷达"3 硬线** (PRD §2.2)：
1. 三类 KB 必须分槽位上传（少于 3 类无法开始扫描）
2. 两阶段抽取必可见（前端展示"N 条规则"+"M 条事件"过程数字）
3. 业务单号必带（每条违规必须指向具体单号 · 不是"某些业务"）

---

## 2. Capabilities (Numbered · Stage C Worker 逐项实装并打 ✓)

- [ ] **C1 三槽位 KB 上传** · 监管政策 (pdf/docx · 多份) · 内部制度 (docx/pdf) · 业务数据 (xlsx · 多份) · 三槽都满才能扫描
- [ ] **C2 政策事件主动拉取 (`/api/compliance/policy_scan` 已实装)** · 从 gov.cn / pbc / flk_npc / Tavily 拉新政策候选 · 自带 `source_url` + `fetched_at` Evidence-First · Stage C 关键升级：替换 Tavily 泛搜为专业政策源
- [ ] **C3 RuleSetBuilder (政策→规则集)** · 章节切分（沿用 v1.0 `policy_parser.py`）· 每段 LLM 抽取 `RuleItem` (rule_id / article_no / category / condition / threshold / severity_hint / source_text) · 合并去重 · 类别标签
- [ ] **C4 EventExtractor (业务→事件集)** · Excel 直解析（pandas）· 字段映射 `field_dict.json` 100% 准确（不依赖 LLM）· Word 自由文本走 LLM 抽取 · 输出 `EventItem` (event_id / event_type / event_date / fields / raw_record)
- [ ] **C5 MatrixMatcher 两阶段过滤** · **硬规则 fast path** (类别 + event_type 过滤 + threshold 结构化比较 · 90%+ 单元过滤) · **LLM slow path** (硬规则无法判定的模糊单元 · 复用 v1.0 `compliance_checker.check_compliance`)
- [ ] **C6 ViolationRecord 聚合** · 同规则多事件合并 · `defect_classifier` 分级 (severe / normal / observation) · 整改建议 LLM 批量生成
- [ ] **C7 三视角榜单 (Tab 切换)** · "按违规" (默认) / "按条款" (合规审计常用) / "按业务单号" · 不同视角不同左栏组织 (PRD §4.4)
- [ ] **C8 违规详情面板** · 选中违规 → 触发条款（高亮原文）+ 涉及业务单号（多卡片 · click 展开原始记录）+ 证据链 (条款摘录 + 业务摘录 + LLM 判定理由)
- [ ] **C9 整改建议卡片** · 紧急度 (立即 / 7 天 / 30 天 / 90 天) · 责任部门 (零售信贷部 / 法律合规部 / 运营部 / 科技部) · 整改期限 · 严重 15 天 / 一般 30 天 / 观察 90 天
- [ ] **C10 SSE 三阶段流** · `rule_extracting` (`已抽 X / N 政策`) → `event_extracting` (`已处理 X / M 业务文件`) → `matrix_matching` (`已比对 X / N×M 单元`) → `done` 含 ComplianceLedger
- [ ] **C11 Excel 榜单导出** · 5 sheet (严重 / 一般 / 观察 / 规则清单 / 事件清单) · ≤ 3 秒 · openpyxl
- [ ] **C12 Word 整改报告导出** · 封面 + 摘要 + 分级明细 + 整改计划 + 责任分派 + 附录条款原文 · 可直接上合规委员会 · ≤ 5 秒
- [ ] **C13 单违规 PDF 导出** · 单条违规证据链 + 整改建议 + 条款原文 · reportlab
- [ ] **C14 SearchProvider 抽象 (政策源)** · gov_cn / pbc_gov / flk_npc / cbirc (新增银保监 · 替换 Tavily 泛搜) · 切换走 `provider` 参数
- [ ] **C15 LLM 缓存** · 预置场景全量缓存 · 演示重播秒出
- [ ] **C16 误报标记 + Prompt 优化反馈** · 合规人员可在 UI 标"误报" · Demo 阶段记录 · 用于后续 Prompt 调优 (data flywheel · CLAUDE.md §6)
- [ ] **C17 政策矩阵对照** (Wave 2 已挂 · L1-3) · `[data-testid="policy-matrix"]` · 政策条款 vs 业务单号交叉表 · 不许移除

---

## 3. Input Shape

| 维度 | 形态 |
|---|---|
| **触发源 1 (主)** | 政策事件驱动 · 银保监/央行/网信办发新政策 → Agent5 自动拉取 + 推送给合规部 |
| **触发源 2** | 合规部主动巡检 (季度 / 月度 · 在 `/archive/compliance` 选场景) |
| **触发源 3** | IM `@compliance 帮我跑互联网贷款专项合规` |
| **KB 文件类型** | 监管政策 pdf/docx (多份) · 内部制度 docx/pdf · 业务数据 xlsx (多份 · sheet 各异) |
| **预置场景** | 2 个 · `online_loan` (互联网贷款合规 · 2 政策 + 1 制度 + 3 业务 = 100 放款 + 30 合作 + 15 模型) · `aml` (反洗钱合规 · 2 政策 + 1 制度 + 3 业务 = 100 大额 + 200 可疑 + 100 KYC) |
| **政策源 provider** | `gov_cn` / `pbc_gov` / `flk_npc` / `cbirc` (银保监) · 默认 `cbirc` |
| **可调参数** | `query` (搜索关键词) · `limit` (默认 10) · `force_mock` |

---

## 4. Output Shape

### 4.1 UI 渲染 (panel 级 · 见 §7)

- **HeroBanner** · 顶部统计条 (N 条规则 × M 条事件 · 🔴 严重 X · 🟡 一般 Y · 🟢 观察 Z · 用时 MM:SS)
- **UploadDropZone** · 三槽位上传 + 场景快捷按钮
- **ScanStageTimeline** · 三段式时间轴 (规则抽取 / 事件抽取 / 矩阵比对) · 每段独立进度条
- **PolicyDiff** (Wave 2 · 政策矩阵对照) · 政策条款 vs 业务单号交叉表
- **MatrixScan** · 矩阵单元格热力图 · 90% 灰色 (硬规则 fast path 通过) · 红/黄/绿色块 (硬规则触发) · 蓝色块 (LLM slow path)
- **ViolationList** (左栏) · 三段分组 (🔴 严重 / 🟡 一般 / 🟢 观察) · 顶部 Tab 三视角切换 (按违规 / 按条款 / 按业务单号)
- **ViolationDetail** (中栏) · 选中违规 (摘要 + 触发条款原文 + 涉及业务单号卡片 + 证据链)
- **RevisionDraft** (右栏) · 整改建议卡片 (紧急度配色 + 责任部门标签 + 期限) + "导出整改单 PDF"
- **PolicyTicker** (Wave 2 已挂 · 政策事件流) · 不许移除
- **EvidenceTrail** (Wave 2) · 不许移除
- **ConversationPanel** · IM 风对话气泡

### 4.2 文件导出

| 文件 | 后端端点 | 内容 |
|---|---|---|
| **榜单 Excel** | `POST /api/compliance/export_xlsx` (Stage C 新建) | 5 sheet (严重/一般/观察/规则/事件) |
| **整改报告 Word** | `POST /api/compliance/export_docx` (Stage C 新建) | 完整报告（封面 + 摘要 + 明细 + 计划 + 责任 + 附录）· 可直接上委员会 |
| **单违规 PDF** | `POST /api/compliance/export_pdf` (Stage C 新建) | 证据链 + 整改 + 条款原文 |

---

## 5. Backend Endpoints

### 5.1 已实装 (api.py v3.1)

| 方法 | 路径 | 请求 | 响应 |
|---|---|---|---|
| GET | `/api/compliance/policy_scan?query=&limit=` | query | `{policies: [{title, source_url, fetched_at, source_name, snippet, policy_doc?}], _qc_placeholder_hits?: []}` |

⚠️ **当前已知问题**（shell-v1-agent-api-map.md §5）：返回 Tavily 泛搜结果（涉税报送 / 纪委文章），与信贷业务无关 · Stage C 必修：`shared/sources/router.py` 加 cbirc/银保监优先 · query="互联网贷款"应返金融监管文档。

### 5.2 Stage C 新建端点

| 方法 | 路径 | 请求 | 响应 | 备注 |
|---|---|---|---|---|
| GET | `/api/compliance/scenarios` | — | `{scenarios: [{key, name, desc, policy_count, event_count}]}` | 列预置场景 |
| POST | `/api/compliance/upload_kb` | multipart · `kb_type: policies/internal/business` · `files[]` | `{kb_id, kb_summary}` | 三槽位独立上传 |
| POST | `/api/compliance/matrix_check` | `{kb_id, scenario_key?, force_mock?}` | **SSE** · 三阶段事件 + done (见 §5.3) | 矩阵比对核心入口 |
| POST | `/api/compliance/policy_scan` (扩) | + `provider?: "cbirc"\|"gov_cn"\|"pbc"` (默认 cbirc) | 同 5.1 | 优先级路由修复 |
| GET | `/api/compliance/violations/{session_id}` | path | `{severe[], normal[], observation[], stats}` | 完整 ComplianceLedger 拉取 |
| GET | `/api/compliance/violation/{violation_id}` | path | `{rule, events, evidence_chain, recommendation, responsible_depts, deadline}` | 单违规详情 |
| POST | `/api/compliance/export_xlsx` | `{session_id}` | xlsx file | 5 sheet |
| POST | `/api/compliance/export_docx` | `{session_id}` | docx file | Word 整改报告 |
| POST | `/api/compliance/export_pdf` | `{session_id, violation_id}` | pdf file | 单违规整改单 |
| POST | `/api/compliance/mark_false_positive` | `{session_id, violation_id, reason}` | `{recorded: true}` | 误报标记 (data flywheel) |

### 5.3 SSE 事件契约

```jsonc
// event: stage (三阶段)
{"event": "stage", "stage": "rule_extracting", "payload": {"extracted": 38, "total_policies": 2, "current": "商业银行互联网贷款管理办法.pdf"}}
{"event": "stage", "stage": "event_extracting", "payload": {"extracted": 130, "total_files": 3, "current": "loans_q4.xlsx"}}
{"event": "stage", "stage": "matrix_matching", "payload": {"compared": 6780, "total": 9860, "hard_filtered": 6500, "llm_judged": 280}}

// event: hit (实时违规命中 tick · slow path)
{"event": "hit", "payload": {"violation_id": "VIO-003", "rule_id": "POLICY2-ART3", "event_ids": ["COOP202510007"], "severity": "critical"}}

// event: done
{
  "event": "done",
  "payload": {
    "session_id": "...",
    "summary": {"rule_count": 68, "event_count": 145, "severe": 5, "normal": 8, "observation": 12, "duration_seconds": 158},
    "violations": [
      {
        "violation_id": "VIO-003",
        "severity": "critical",
        "rule": {
          "rule_id": "POLICY2-ART3",
          "source": "《关于进一步规范商业银行互联网贷款业务的通知》",
          "article_no": "第 3 条",
          "category": "出资比例",
          "condition": "单笔贷款中商业银行出资比例不得低于 30%",
          "source_text": "..."
        },
        "events": [
          {"event_id": "COOP202510007", "event_type": "联合贷款", "fields": {"total": 5000000, "bank_share": 750000, "ratio": 0.15}, "raw_record": {...}},
          {"event_id": "COOP202511003", "event_type": "联合贷款", "fields": {"total": 2000000, "bank_share": 440000, "ratio": 0.22}, "raw_record": {...}}
        ],
        "evidence_chain": [...],
        "recommendation": "立即暂停上述 2 笔合作方新增放款 / 重新议定出资比例至 ≥ 30% / 7 日内对 2025 年所有联合贷款合同做出资比例专项复核",
        "responsible_depts": ["零售信贷部", "法律合规部"],
        "deadline": "2026-05-12"
      }
    ]
  }
}

// event: error
{"event": "error", "stage": "...", "message": "...", "traceback": "..."}
```

### 5.4 降级路径

- **政策源 (gov_cn/pbc/cbirc) 全崩** → 走 Tavily 兜底 + 标 `data_source: "fallback_tavily"` · 前端 tile 黄色提示
- **DeepSeek 崩** → 矩阵 LLM slow path 失败 · 仅硬规则 fast path 通过 · 输出 partial ledger 标灰
- **政策 PDF 扫描件 OCR 质量差** → 预处理 OCR 置信度检查 · 低置信度给警告 · 该政策跳过
- **业务字段名称不统一** → field_dict.json 兜底 · 失败给字段映射向导 (Stage C 后续)

---

## 6. Mock Sessions Structure (≥3)

### 6.1 Top-level shape

```typescript
type ComplianceMockSession = {
  session_id: string;
  scenario_key: string;
  display_name: string;
  generated_at: string;
  summary: {
    rule_count: number;
    event_count: number;
    severe: number;
    normal: number;
    observation: number;
    duration_seconds: number;
  };
  rules_preview: RuleItem[];      // 前 5 条规则展示
  events_preview: EventItem[];    // 前 5 条事件展示
  violations: ViolationRecord[];
};
```

### 6.2 三个标杆 session

| session_id | scenario | 矩阵规模 | 严重/一般/观察 | 演示卖点 |
|---|---|---|---|---|
| `compli-online-loan-001` | online_loan | 68 × 145 ≈ 9860 单元 | 5/8/12 | 联合贷款出资比例 15% < 30% 红线 (硬规则秒检) · 风控模型未独立验证 (LLM 判定) |
| `compli-aml-001` | aml | 52 × 400 ≈ 20800 单元 | 3/7/8 | 大额交易 T+N 时效自动算 · 可疑交易关闭未复核 (流程类硬规则) |
| `compli-data-protect-001` (新增 · 数据安全合规) | data_protection | 40 × 200 ≈ 8000 单元 | 2/6/10 | 个人信息保护法 + 数据出境 · KYC 数据保留期超限 |

### 6.3 数据契约

```typescript
type RuleItem = {
  rule_id: string;                // "POLICY1-ART6" / "INTERNAL-ART12"
  source: string;                 // 来源文件名
  article_no: string;             // "第 6 条"
  category: "期限" | "额度" | "流程" | "披露" | "时效" | "身份识别" | "其他";
  condition: string;              // 自然语言触发条件
  threshold: Record<string, any>; // 结构化阈值 {"duration_months": 12} / {"ratio": 0.30}
  severity_hint: "critical" | "major" | "minor";
  source_text: string;
};

type EventItem = {
  event_id: string;               // "LN20251108" / "COOP202510007"
  event_type: string;             // "放款" / "联合贷款" / "风控模型上线" / "大额交易"
  event_date: string;
  subject_id: string;
  fields: Record<string, any>;
  raw_record: Record<string, any>;
  source_file: string;
};

type ViolationRecord = {
  violation_id: string;           // "VIO-001"
  severity: "critical" | "major" | "minor";
  rule: RuleItem;
  events: EventItem[];            // 涉及的所有业务事件
  evidence_chain: EvidenceItem[];
  recommendation: string;         // LLM 生成的整改建议
  responsible_depts: string[];
  deadline: string;
};

type EvidenceItem = {
  source_type: "external" | "internal";
  provider: string;
  title: string;
  snippet: string;
  url?: string;
  timestamp?: string;
};
```

---

## 7. Panel Architecture (`/archive/compliance/_components/`)

| Panel 组件 | 数据源 (props) | 切 session 重渲 | 违规 click 联动 |
|---|---|---|---|
| `ComplianceHero.tsx` | `summary` | ✓ | — |
| `UploadDropZone.tsx` | upload state | ✓ | — |
| `ScanStageTimeline.tsx` | three stages progress | ✓ | — |
| `PolicyDiff.tsx` (Wave 2 · 政策矩阵) | rules vs events 交叉表 | ✓ | — |
| `MatrixScan.tsx` | matrix cells heatmap | ✓ | — |
| `ViolationListPanel.tsx` | `severe[] / normal[] / observation[]` · view mode · onSelect | ✓ | — |
| `ViolationDetailPanel.tsx` | selected violation | ✓ | ✓ (主) |
| `RevisionDraftPanel.tsx` | selected violation.recommendation | ✓ | ✓ |
| `PolicyTicker.tsx` (Wave 2 · 政策事件流) | latest policies (`/policy_scan`) | ✓ | — |
| `EvidenceTrail.tsx` (Wave 2 · 不许移除) | evidence_chain | ✓ | ✓ |
| `ConversationPanel.tsx` | thread | — | — |

### 7.1 Panel state hoist

```typescript
const [selectedSessionId, setSelectedSessionId] = useState(MOCK_SESSIONS[0].session_id);
const [selectedViolationId, setSelectedViolationId] = useState<string | null>(null);
const [view, setView] = useState<"by_violation" | "by_clause" | "by_event">("by_violation");
const [livePayload, setLivePayload] = useState<ComplianceLedger | null>(null);
const [scanProgress, setScanProgress] = useState<ScanProgressState | null>(null);
const [mode, setMode] = useState<"mock" | "live">("mock");
```

### 7.2 路由 + 红线

- ✅ 唯一入口 `/archive/compliance`
- ❌ 禁顶层 `/compliance` (legacy)

---

## 8. Regression Risks

| ID | Feature | Selector | 验证 spec |
|---|---|---|---|
| F-policy-matrix | PolicyMatrix (Wave 2 · L1-3) | `[data-testid="policy-matrix"]` | `web/tests/policy-matrix.spec.ts` |
| F-policy-ticker | PolicyTicker (Wave 2 · compliance codex fusion 已合) | `[data-testid="policy-ticker"]` | `web/tests/policy-ticker.spec.ts` |
| F-evidence-trail | EvidenceTrail (Wave 2) | `[data-testid="evidence-trail"]` | `web/tests/evidence-trail.spec.ts` |

**v1.0 资产 PRESERVE**：
- `policy_parser.py` (政策解析 · 章节切分能力被 RuleSetBuilder 复用)
- `compliance_checker.py` (合规对比 · 作为 MatrixMatcher LLM slow path 单元判定器)
- `defect_classifier.py` (缺陷分级逻辑保留)
- `prompts.py` (SYSTEM_POLICY_PARSE / SYSTEM_COMPLIANCE_CHECK 保留 · 新增 SYSTEM_EVENT_EXTRACT / SYSTEM_MATRIX_JUDGE / SYSTEM_RECOMMENDATION_BATCH)

**红区禁触**（共享 kb_scan/）：
- `shared/kb_scan/models.py` 改 `RuleItem` / `EventItem` schema → RFC（Agent4/5 共用）
- `shared/kb_scan/matcher.py` 改 `Matcher` Protocol → RFC
- 黄区 `shared/sources/impls/*.py` 加 cbirc / gov_cn 实现自由

---

## 9. LLM 调用预算 (PRD §7.2)

| 调用点 | 频次 | 模型 | Temp |
|---|---|---|---|
| **政策分段抽取** | 每政策 ~10 章 = 10 次 | DeepSeek-chat | 0.2 |
| **内部制度抽取** | 每制度 ~5 章 = 5 次 | DeepSeek-chat | 0.2 |
| **业务文本事件抽取** | 仅 Word 自由文本 ~2 次 (Excel 直解) | DeepSeek-chat | 0.2 |
| **矩阵单元格判定** | 硬规则过滤后 ~300 模糊单元 · 批量 (10/批) ~30 次 | DeepSeek-chat | 0.2 |
| **批量整改建议** | 25 条违规 · 批量 (5/批) ~5 次 | DeepSeek-chat | 0.5 |

**Demo 总预算**：场景 1 ~47 次 LLM (缓存命中后 ~5 次)

**性能 SLA (PRD §10.1)**：
- 68 × 145 矩阵 P95 ≤ 3 分钟
- 榜单视角切换 ≤ 500ms
- 矩阵规模上限 200 条规则 × 1000 条事件 (LLM ≤ 100 次)

---

## 10. Acceptance for Stage C

- [ ] 17 个 capability (§2 C1-C17) 全 ✓
- [ ] 9 个新/扩端点 (§5.2) 真跑通
- [ ] 11 个 panel (§7) 全 props 化 · 三视角切换无状态污染
- [ ] 3 个 mock session (§6) 落 `web/lib/mock-sessions.ts`
- [ ] 5 个 Playwright smoke pass (compli-mock-switch / compli-live-scan / compli-violation-drill / compli-export-docx / compli-policy-scan-cbirc)
- [ ] features-inventory.md F-policy-matrix / F-policy-ticker / F-compli-* entries
- [ ] commit trailer 必含 `PRESERVES: F-policy-matrix, F-policy-ticker, F-evidence-trail`
- [ ] 政策源 cbirc 替换 Tavily 默认（修 shell-v1-agent-api-map.md §5 已知问题）
- [ ] tsc --noEmit 0 error · ECS deploy verify 通

---

## 11. References

- 上游 PRD: `docs/PRD_合规巡检智能体_v2.0.md`
- API map: `docs/contracts/shell-v1-agent-api-map.md` § Agent 5
- Agent4 spec (共享 kb_scan 范式): `docs/contracts/agent-alert-spec.md`
- 字段命名: `docs/contracts/field-naming.md`
- 共享变更协议: `docs/contracts/shared-change-protocol.md`
- Master plan: `docs/contracts/master-execution-plan-2026-04-27.md` § Stage C.4
- Workspace state: `docs/contracts/workspace-state-protocol.md` v1.1 (Phase A worker-A1 ratified · 4 useState gate + AgentSession shape 见 §10)
