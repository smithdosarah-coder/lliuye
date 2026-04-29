# Agent6 Report · Spec for Stage C Worker

> **Source PRD**: `docs/PRD_报告生成助手.md` (canonical · 单 v1.0 · 无 v2)
> **Workspace route**: `/archive/report` (canon, 见 CLAUDE.md §7)
> **Backend module**: `agent_report/api.py` (FastAPI v0.1.0 · 已挂载) + 项目根 v16 主管线 10 个 `v16_*.py`
> **Stage C 任务**: 把 Report workspace 升到 PRD-grade · v16 wire + 文件上传 + 字段抽取 + Word 导出 + panel state hoist
> **架构红线**: §3.1 确定性 vs 概率性 不可混 · 财务比率 Python 算 · LLM 只做撰写

---

## 1. Product Positioning

Agent6 是面向银行客户经理的**授信调查报告自动生成助手**——客户经理上传企业原始材料（PDF/Word/Excel/图片）+ 报告模板，系统经 v16 主管线（classifier → generator → QC gate）输出可直接提交审批的 15000+ 字专业 Word 报告。

**质量底线**：报告须可直接送审批，不能仅作草稿。三层信息框架——第一层材料事实（零容错 · Python 精确算）/ 第二层行业上下文（标注来源）/ 第三层分析推断（证据链支撑），不允许混用。

**与 Agent3 边界**：Agent6 = 文书自动化（不出决策意见、不算批不批、不给额度）；报告章节 4 "审批意见"留空，等 Agent3 决策回写（见 `agent-credit-spec.md` § handoff）。

**v16 vs Gradio fallback**：v16 (`v16_pipeline.py` CLI · `agent_report/api.py` API wrapper) 是主管线 · 旧 Gradio `app.py` v9.0 + 引擎 v7.5 单机版仅作客户走访期间 fallback 演示备份，走访后归档 `legacy_gradio/`。

---

## 2. Capabilities (Numbered · Stage C Worker 逐项实装并打 ✓)

- [ ] **C1 多类型材料上传** · PDF (扫描件 OCR) / Word (.docx/.doc) / Excel (.xlsx/.xls 多 sheet 含合并单元格) / 图片 (jpg/png) · 多文件同时拖入 · 后端 `/api/report/fill` multipart 已实装
- [ ] **C2 模板上传** · 客户自定义 .docx 模板 · 默认走 `business_line` 内置模板 (corporate / inclusive / reserved · `BUSINESS_LINE_TEMPLATE_NAMES` 映射)
- [ ] **C3 业务线分流** · `corporate` (narrative 管线) / `inclusive` (V14 骨架管线) / `reserved` · 后端 `business_line` query 参数已实装
- [ ] **C4 v16 三阶段主管线** · `classifier` (5 类槽位识别 · XX 字段 / 复选框 / 示例段落 / 嵌套表格 / 标签字段) → `generator` (KB 优先 + LLM 改写 · Evidence-First 三阶段) → `QC gate` (9 维度评分阻断) · 失败 fail-fast 不进 fallback
- [ ] **C5 知识库自动构建 (`material_kb`)** · 公司基本信息 / 主营业务 / 股东结构 / 上下游关系 / 经营资质 · 6 大类结构化提取
- [ ] **C6 财务事实库 (`truth_financial_data`)** · 直接从 Excel/PDF 提取原始财务数据 · Python 精确算所有比率 (资产负债率 / 流动比率 / 净利润率 / 应收账款周转天数 / EBITDA) · 计算结果作"数字锚点"注入每次 LLM prompt
- [ ] **C7 5 类槽位填写** · XX 字段 (批量提取 KB 映射) · 复选框 (规则推断 + LLM 兜底) · 示例段落 (KB 优先 + LLM 改写) · 嵌套表格 (结构化填充 + 财务数据精确注入) · 标签字段 (分类规则)
- [ ] **C8 Phase C 全文档兜底审查** · 模板指纹（Phase 0 采集）vs 生成报告指纹对比 · 检测高相似度未改写段落 · 自动补充改写
- [ ] **C9 QC 规则引擎 + Blocker** · 假名检测 / 模板区间数字 / 指导语残留 / 行业错配 / 占位符残留 · severity=error 阻断输出 · severity=warning 提示
- [ ] **C10 SSE 5 阶段流** · `ingest` → `extract` → `infer` → `write` → `audit` · 每阶段 progress + message · 真模式 + mock 模式 (mock=1 假进度 + 真 fixture section)
- [ ] **C11 Section 流式渲染** · 每节生成完成立即推 `event: section` · 前端 Draft panel 渐进式渲染 · 4 chapter (`chapter_1_background` / `chapter_2_operation` / `chapter_3_finance` / `chapter_4_conclusion`)
- [ ] **C12 EnterpriseProfile 产出** · `done` 事件含完整 EP (含 `financial_anchors / guarantee_info / related_party_info / existing_credit / request / chapters`) · 供 Agent3 消费 (handoff)
- [ ] **C13 Pending Questions** · 未填字段清单（`pending_tags` 来自 `FormFillAgent`）· 客户经理可补答 · `/api/report/refine` 续跑只重写 external_factor 相关 section
- [ ] **C14 Word 导出 + 安全下载** · 真模式产 docx 落 `outputs/sessions/{session_id}/` · 30min TTL 自动清理 · 下载端点 UUID 白名单 + 目录穿越防护
- [ ] **C15 Handoff 触发器** · "送 Agent3 做决策"按钮 · 把 ReportJSON + EnterpriseProfile 通过 sessionStorage 传 `/archive/credit` (master plan C.2 · 见 `agent-credit-spec.md` Step 1)
- [ ] **C16 审计日志** · DoD L2-12 · 每次 `/fill` `/refine` 落 `data/audit/` · 含 `endpoint / user_id / input_hash / latency_ms / output_status`
- [ ] **C17 LLM 状态灯** · `/api/report/health` 返 `llm_connected: bool` · 前端 health-checker 轮询展示

---

## 3. Input Shape

| 维度 | 形态 |
|---|---|
| **触发源** | 客户经理在 `/archive/report` workspace 主动发起 · IM `@report 帮我写鼎盛商贸的报告` 也可触发 |
| **材料文件类型** | PDF (含扫描件) / Word (.docx/.doc) / Excel (.xlsx/.xls 多 sheet) / 图片 (OCR) / TXT · 总大小限制按 ECS 配 (默认 50MB/文件) |
| **模板** | 客户自定义 .docx (含 XX 占位符 / 复选框 / 示例段落 / 嵌套表格) · 默认 `templates_cache/福建普惠授信申报及审查审批意见表2025新版.docx` |
| **预置场景 (mock=1)** | 2 个 · `dingsheng_trade` (corporate 鼎盛商贸) / `zhangsan_restaurant` (inclusive 张三餐饮) · master plan B.1 锚 3-5 个标杆扩到 reserved 板块 |
| **业务线** | `corporate` / `inclusive` / `reserved` · 决定模板 + preset + 评分维度 |
| **mock 标志** | `mock=1` query · 不需上传 · 5 段假进度 + 真 section 输出 |

---

## 4. Output Shape

### 4.1 UI 渲染 (panel 级 · 见 §7)

- **MaterialsPanel** · 已上传文件列表 · 每行 (文件名 / 类型图标 / 解析状态 / 字数/页数) · 拖拽区 + 点击上传 · 业务线下拉
- **FieldsPanel** · 5 类槽位实时识别 · 计数 (XX字段 X / 复选框 Y / 示例段 Z / 表格 N / 标签 M) · 每类点击展开明细
- **DraftPanel** · 4 chapter 渐进渲染 · 每节 streaming 输出 · 不同章节 syntax-highlight (KB 字段绿底 / 财务锚点蓝底 / 占位符红底)
- **PreviewPanel** · 完整 docx 嵌入预览 (前端 mammoth.js) · 段落级标注修订意见
- **PendingQuestionsPanel** · 未填字段清单 · 每条 (id / 字段名 / 推荐答案 / 来源材料引用 / 用户输入框)
- **StatsBadge** · `total_fields / auto_filled / unfilled` 三数 + auto_fill_rate 百分比
- **EvidenceTrail** (Wave 2 已挂 · 不许移除) · 每条 claim 回指证据 · 点击高亮原材料行
- **ConversationPanel** · IM 风对话气泡 · `@report` 触发 · 结果回 thread

### 4.2 文件导出

| 文件 | 后端端点 | 内容 |
|---|---|---|
| **docx 报告** | `GET /api/report/downloads/{session_id}/{filename}` (已实装) | 完整 15000+ 字 · 包含 4 chapter · 第 4 章预留 Agent3 回写 |
| **legacy docx** | `GET /api/report/downloads/legacy/{fname}` (已实装) | mock 模式 fallback docx · 走 `outputs/` 根目录 |
| **EnterpriseProfile JSON** | `done` 事件 payload + `GET /api/report/preset/{key}` (已实装) | 跨 Agent 预填 fallback |

---

## 5. Backend Endpoints

### 5.1 已实装 (api.py v0.1.0 · session 9 实跑通)

| 方法 | 路径 | 请求 | 响应 |
|---|---|---|---|
| GET | `/health` | — | `{status, version}` |
| GET | `/api/report/health` | — | `{status, llm_connected: bool, version}` (前端状态灯) |
| POST | `/api/report/fill` | multipart · query: `mock={0\|1}&preset=<key>&business_line=<line>` · `files: UploadFile[]` · `template_file?: UploadFile` | **SSE** · 5 阶段 + N section + done (见 §5.3) |
| POST | `/api/report/refine` | `{session_id, answers: [{id, value}]}` | **SSE** · write/audit 两阶段 + done (更新 EP + 余下 pending_questions) |
| GET | `/api/report/preset/{key}` | path param · safe regex `[a-zA-Z0-9_\-]{1,64}` | `{preset, enterprise_profile}` |
| GET | `/api/report/downloads/{session_id}/{filename}` | UUID4 white-list session_id · basename filename · 目录穿越防护 | docx file (`Content-Disposition: attachment; filename=...`) |
| GET | `/api/report/downloads/legacy/{fname}` | basename | docx file (mock fallback) |
| GET | `/downloads/{fname}` | basename (兼容老接口) | docx file |

### 5.2 Stage C 新建 / 扩展端点

| 方法 | 路径 | 请求 | 响应 | 备注 |
|---|---|---|---|---|
| POST | `/api/report/upload` | multipart · `files: UploadFile[]` · `business_line` | `{kb_id (uuid), file_summary: [{name, type, size, parsed_chars}]}` | 上传与解析解耦 (现 fill 一把梭 · Stage C 拆出独立 upload) · 落盘 `data/kb/report/{kb_id}/` |
| POST | `/api/report/fill` (扩) | 同 5.1 + `kb_id?: str` (从 upload 拿 · 跳过 ingest) | 同 5.1 | 让前端预上传后再触发 fill 减重传 |
| POST | `/api/report/refine` (扩) | + `section_ids?: str[]` 指定重跑章节 | 同 5.1 | 现 stub 只 external_factor · 扩到任意 section |
| POST | `/api/report/handoff_credit` | `{session_id, segment: "corporate"\|"retail"}` | `{handoff_path, profile_id}` | 写 `data/handoff/report_to_credit/{session_id}.json` · 含 EP + ReportJSON |
| POST | `/api/report/credit_writeback` | `{session_id, advice: DecisionAdvice}` | `{updated, chapter_4_text}` | Agent3 回写决策 → 第 4 章审批意见 |

### 5.3 SSE 事件契约

```jsonc
// event: stage (5 阶段轮播)
{"event": "stage", "stage": "ingest|extract|infer|write|audit", "progress": 0.0-1.0, "message": "..."}

// event: section (流式 section 输出 · 每节生成立即推)
{"event": "section", "section": {"id": "chapter_1_background", "title": "一、企业背景", "content": "..."}}

// event: done
{
  "event": "done",
  "session_id": "uuid-v4",
  "report_docx_url": "/api/report/downloads/{session_id}/{filename}",
  "enterprise_profile": { /* 完整 EP */ },
  "pending_questions": [{ "id": "...", "label": "...", "recommended": "...", "source_ref": "..." }],
  "downstream_handoff": { "agent3_input": "..." },
  "payload": {
    "profile": { /* 同 enterprise_profile */ },
    "sections": [ /* 4 chapters */ ],
    "stats": {"total_fields": 492, "auto_filled": 460, "unfilled": 32},
    "docx_url": "..."
  }
}

// event: error
{"event": "error", "stage": "...", "message": "..."}
```

### 5.4 v16 CLI 入口（演示备份）

```bash
py v16_pipeline.py --source samples/<模板>.docx --material samples
```

不走 API · 直接跑 classifier → generator → QC gate · 产物落项目根 · 客户走访万一 API 崩可秒切。

### 5.5 降级路径

- **DEEPSEEK_API_KEY 未配** → `/api/report/fill?mock=0` 立即返 error · `/health` 返 `llm_connected: false` (UI 状态灯黄) · 前端切 `mock=1`
- **DeepSeek 崩** → `write/audit` 阶段 yield error · 前端切 mock=1 重试 → 仍崩走 `/public/mock/report_fill_mock.json` fixture · 必须备 fallback docx (`outputs/` 根目录)
- **Session TTL** → 30min 后 `outputs/sessions/{session_id}/` 整目录清 · 演示 1 小时窗口内安全

---

## 6. Mock Sessions Structure (≥3)

### 6.1 Top-level shape (`web/lib/mock-sessions.ts` 或 `web/public/mock/report_fill_mock.json`)

```typescript
type ReportMockSession = {
  session_id: string;             // "session-dingsheng-001"
  preset_key: string;             // "dingsheng_trade" / "zhangsan_restaurant" / "reserved_*"
  business_line: "corporate" | "inclusive" | "reserved";
  display_name: string;           // 下拉切换显示
  enterprise_profile: EnterpriseProfile;
  stages: SSEStageEvent[];        // 5 阶段事件序列
  sections: ReportSection[];      // 4 chapter
  stats: { total_fields: number; auto_filled: number; unfilled: number };
  pending_questions: PendingQuestion[];
  downstream_handoff: { agent3_input: string };
  docx_url: string;
};
```

### 6.2 三个标杆 session 数据要点

| session_id | preset | 业务线 | 企业类型 | 章节字数 | 演示卖点 |
|---|---|---|---|---|---|
| `session-dingsheng-001` | `dingsheng_trade` | corporate | 商贸（2.8 亿营收 · 87 员工） | 15000+ | 财务锚点 · 关联交易触发红线 · 应收账款周转 140d |
| `session-zhangsan-001` | `zhangsan_restaurant` | inclusive | 餐饮个体户（家常菜馆 · 4 年） | 8000+ | 普惠骨架管线 · 抵押估值 · 评分卡式数据 |
| `session-zhongrui-001` | `zhongrui_network` | corporate | 互联网/SaaS（3 亿营收 · 6 年） | 16000+ | 90 文件 158MB 真材料 dry-run（Q-040 锚定 · 客户走访 baseline） |

### 6.3 单个 chapter 数据契约

```typescript
type ReportSection = {
  id: "chapter_1_background" | "chapter_2_operation" | "chapter_3_finance" | "chapter_4_conclusion";
  title: string;                  // "一、企业背景"
  content: string;                // markdown 含锚点高亮 · 4000+ 字
  evidence_refs: EvidenceRef[];   // 每段 claim 回指证据
  word_count: number;
  status: "pending" | "writing" | "done" | "qc_blocked";
  qc_issues: QCIssue[];           // 该节命中的 QC 问题
};

type EnterpriseProfile = {
  profile_id: string;
  company_name: string;
  unified_credit_code: string;
  industry: string;
  establishment_date: string;
  registered_capital: string;
  region: string;
  main_business: string;
  controller_name: string;
  controller_share_pct: number;
  business_line: "corporate" | "inclusive" | "reserved";
  financial_anchors: { /* revenue_latest / net_profit / total_assets / debt_ratio / ... */ };
  guarantee_info: { /* 担保安排 */ };
  related_party_info: { /* 关联方 */ };
  existing_credit: { /* 现有授信 */ };
  request: { /* 申请额度/期限/用途 */ };
  chapters: { [section_id: string]: string };
  source_materials: string[];
  generated_at: string;
};
```

---

## 7. Panel Architecture (`/archive/report/_components/`)

| Panel 组件 | 数据源 (props) | 切 session 重渲 | 续跑联动 |
|---|---|---|---|
| `ReportHero.tsx` | `enterprise_profile.company_name` + business_line + stats | ✓ | — |
| `MaterialsPanel.tsx` | uploaded files + parse status | ✓ | — |
| `FieldsPanel.tsx` | 5 类槽位计数 + drill 明细 | ✓ | — |
| `DraftPanel.tsx` | sections (流式追加) | ✓ | ✓ |
| `PreviewPanel.tsx` | docx_url (mammoth.js 嵌入) | ✓ | ✓ |
| `PendingQuestionsPanel.tsx` | pending_questions + onAnswer callback | ✓ | ✓ (refine 触发) |
| `StatsBadge.tsx` | stats | ✓ | ✓ |
| `EvidenceTrail.tsx` (Wave 2 · 不许移除) | evidence_refs | ✓ | — |
| `HandoffButton.tsx` | session_id · onClick → `/archive/credit` 跳转 | — | — |
| `ConversationPanel.tsx` | thread (复用 dispatch) | — | — |

### 7.1 Panel state hoist (master plan C.2)

`ReportWorkspace.tsx` 持有：

```typescript
const [selectedSessionId, setSelectedSessionId] = useState<string>(MOCK_SESSIONS[0].session_id);
const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);
const [livePayload, setLivePayload] = useState<LiveReportPayload | null>(null);
const [mode, setMode] = useState<"mock" | "live">("mock");
const [pendingAnswers, setPendingAnswers] = useState<Record<string, string>>({});
```

各 panel props 化 · 删 import 全局常量。

### 7.2 路由 + 红线

- ✅ 唯一入口 `/archive/report`
- ❌ 禁顶层 `/credit-report` (legacy)
- v16 + Gradio 双跑期：v16 走 API · Gradio 8002 旁路（仅走访紧急 fallback）

---

## 8. Regression Risks

| ID | Feature | Selector | 验证 spec |
|---|---|---|---|
| F-007 | Materials drag-drop upload | `[data-testid="materials-dropzone"]` | `web/tests/report-upload.spec.ts` |
| F-008 | StatsBadge auto-fill rate | `[data-testid="stats-badge"]` | `web/tests/report-stats.spec.ts` |
| F-evidence-trail | EvidenceTrail (Wave 2) | `[data-testid="evidence-trail"]` | `web/tests/evidence-trail.spec.ts` |
| F-highlight-card | Highlight card (Wave 2) | `[data-testid="highlight-card"]` | `web/tests/highlight-card.spec.ts` |
| F-unfilled-marker | "未能自动填写" marker | `[data-testid="unfilled-marker"]` | `web/tests/unfilled-marker.spec.ts` |

**红区禁触**（CLAUDE.md §3 · `shared-change-protocol.md`）：
- `financial_analyzer.py` (确定性财务计算) → RFC
- `quality_check.py` / `quality_scorer.py` (QC 9 维度评分) → RFC
- `truth_fill.py` (结构化预填) → RFC
- `section_generator.py` (Evidence-First 三阶段) → RFC
- `material_kb.py` (材料解析与 KB 构建) → RFC
- `agent_report/enterprise_profile.py` (handoff 协议) → RFC
- `v16_*.py` 项目根 10 文件改 LLM 抽象层 → 已有 RFC `docs/contracts/rfc/20260418-v16-llm-abstraction-upgrade.md`

**反结果导向 5 原则**（CLAUDE.md §3.5 · 数据归属）：
- 内部 mock = 客户提交材料包（文件夹 + pdf/xlsx/docx/扫描件混合）· 真实消费形态
- 不可 pre-extracted yaml · 含命名混乱 / 扫描件 / 多年跨度 / 数字合理矛盾
- 绝不含答案字段 (difficulty / match_score)

---

## 9. LLM 调用预算

| 调用点 | 频次 | 模型 | Temp | 备注 |
|---|---|---|---|---|
| **Section 撰写** | 4 chapter × N 段 (约 15-30 次) | DeepSeek-chat | 0.3 | 注入财务锚点 + KB · 必须输出 markdown |
| **Phase C 改写** | 命中残留段每段 1 次 | DeepSeek-chat | 0.3 | 模板兜底审查 |
| **复选框推断** | 每复选框 1 次（规则失败时）| DeepSeek-chat | 0.2 | 多数走规则 · LLM 兜底 |
| **续跑 refine** | 重跑 section × N | DeepSeek-chat | 0.3 | 仅 external_factor 相关 |

**真模式 Demo 总预算**：≤50 次 LLM 调用（含 Phase C） · `mock=1` 完全 0 调用

---

## 10. Acceptance for Stage C

- [ ] 17 个 capability (§2 C1-C17) 全 ✓
- [ ] 5 个新/扩端点 (§5.2) 真跑通 · curl 验返
- [ ] 10 个 panel (§7) 全 props 化
- [ ] 3 个 mock session (§6) 落 `web/lib/mock-sessions.ts`
- [ ] 5 个 Playwright smoke pass (report-upload / report-fill-mock / report-fill-real / report-refine / report-handoff-credit)
- [ ] features-inventory.md F-007/F-008 + F-report-* entries
- [ ] commit trailer 必含 `PRESERVES` (列 §8 · 至少 EvidenceTrail / HighlightCard / UnfilledMarker)
- [ ] tsc --noEmit 0 error · ECS deploy verify 通

---

## 11. References

- 上游 PRD: `docs/PRD_报告生成助手.md`
- v16 RFC: `docs/contracts/rfc/20260418-v16-llm-abstraction-upgrade.md`
- Evaluation RFC: `docs/contracts/rfc/20260418-evaluation-runner.md`
- API map: `docs/contracts/shell-v1-agent-api-map.md` § Agent 6
- Handoff (Report → Credit): `docs/contracts/agent-credit-spec.md` § 11
- Handoff (Channel → Credit): `docs/contracts/channel_to_credit_handoff.md`
- 字段命名: `docs/contracts/field-naming.md`
- 共享变更协议: `docs/contracts/shared-change-protocol.md`
- Master plan: `docs/contracts/master-execution-plan-2026-04-27.md` § Stage C.1
- Workspace state: `docs/contracts/workspace-state-protocol.md` v1.1 (Phase A worker-A1 ratified · 4 useState gate + AgentSession shape 见 §10)
