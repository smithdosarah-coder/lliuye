# Agent1 Channel · Spec for Stage C Worker

> **Source PRD**: `docs/PRD_全渠道流量匹配智能体_v2.0.md` (canonical · v1.0 已废)
> **Workspace route**: `/archive/channel` (canon, 见 CLAUDE.md §7)
> **Backend module**: `agent_channel/` (api.py 4.0 已挂载)
> **Stage C 任务**: 按本 spec 把 Channel workspace 升到 PRD-grade · 复用为其他 5 Agent 的模板
> **Worker 红线**: 改 `web/` 必带 trailer (`PRESERVES` / `NEW-DOM` / `SMOKE-PASS`) · 见 CLAUDE.md §13

---

## 1. Product Positioning

Agent1 是**知识库驱动的 look-alike 获客引擎**——客户经理上传"已有优质客户名录 + 当前政策 + 行业指引"三类知识库，Agent 抽取"理想客户画像"，扫描外网企业池（Mock 50+ / 生产 Tavily/企查查），输出 Top10 候选企业线索，每条附匹配维度明细 + Top3 产品推荐 + 切入话术 + Word 导出。

**与 v1.0 (单查工具) 的根本区别**：v1.0 = "输一家企业 → 推渠道"（客户一眼识破是查表），v2.0 = "告诉我你现有客户什么样 → 我找一堆像的"（真正银行获客部门诉求）。

**与 Agent3 边界**：Agent1 产线索 + 推荐产品；不做授信决策、不算红线、不出审批意见。线索可一键 handoff 给 Agent3 走授信流程（见 `channel_to_credit_handoff.md`）。

---

## 2. Capabilities (Numbered · Stage C Worker 逐项实装并打 ✓)

- [ ] **C1 KB 多文件上传** · 3 类文件分槽（客户名录 xlsx/csv · 政策文件 docx/pdf · 行业指引 docx/pdf）· 每槽 `gr.File(file_count="multiple")` 等价 · 后端 `/api/channel/upload_kb` 解析存盘 · 返 `{kb_id, summary}`
- [ ] **C2 IdealProfile LLM 抽取** · 后端 `/api/channel/profile` POST `{kb_id}` · LLM (DeepSeek temperature 0.2) 综合"客户统计 + 政策规则 + 行业指引"输出 `IdealProfile` JSON · 含 `target_industries / target_regions / scale_range / revenue_range / must_have_tags / nice_to_have_tags / exclude_tags / policy_context / reasoning`
- [ ] **C3 IdealProfile 字段可编辑** · 前端画像卡每字段 inline-edit · 失焦保存 · 用户确认后才"开始扫描"（master plan B.6b）
- [ ] **C4 外网搜索池** · `SearchProvider` 抽象 · Mock (`MockProvider` 50+ 企业) / 生产 (Tavily / 企查查 stub 留 TODO) · 切换走 `force_mock` flag · `provider.search_companies(query, filters, limit=50)`
- [ ] **C5 Look-alike 匹配打分** · `SimilarityScorer` 两阶段 · 4a 画像相似度 (industry 0.30 / sub_industry 0.15 / region 0.20 / scale 0.15 / tags 0.20) · 4b 样本锚相似度 (从 KB 客户里找最像的 3 家) · 综合 = 0.6×profile_score + 0.4×anchor_score
- [ ] **C6 HitRanker 分级 Top10** · `RiskLevel.RED ≥80` / `YELLOW 65-79` / `GREEN <65` · 默认按"命中规则数 × 级别权重"排序 · 支持切换为按授信余额排序
- [ ] **C7 候选 detail drawer · 匹配维度明细** (master plan B.4b) · 每候选 vs IdealProfile 各维度 chip 列表（如 "营收 5000 万 ✓ 匹配 P50 ±20% / 行业 SaaS ✓ 命中标杆"）· 每 chip 含命中证据来源 (signal id / KB ref)
- [ ] **C8 候选 detail drawer · Top3 产品推荐** (master plan B.4c) · 复用 v1.0 `channel_rules.match_channels()` + `scoring.rank_recommendations()` · 3 张产品卡 (产品名 / 适配评分 / 额度 / 利率档位) · 不做修改 v1.0 代码 (PRESERVES)
- [ ] **C9 候选 detail drawer · 切入话术** · LLM (DeepSeek temperature 0.5) 批量生成 Top10 话术 (1-2 次合并调用) · 80-150 字 · 含客户姓名占位 + 关键卖点 + 政策红利 + 不虚构数字
- [ ] **C10 SSE 实时进度流** · 5 阶段事件 `parse / signal_scan / aggregate / enrich / done` · `signal_scan` 每条 query 独立 tick · 前端 ChannelHero 实时累计候选计数
- [ ] **C11 Word 导出** (master plan B.7 · gap 6 · PRD-v2 必须) · 后端 `/api/channel/export_docx` (python-docx) · 含 IdealProfile 卡 + Top10 候选 + 各候选匹配明细 + 产品推荐 + 话术全套 · 前端 button 直接下载
- [ ] **C12 候选 click → handoff Agent3** · `/api/channel/handoff` 写 `data/handoff/channel_to_credit/{session_id}/{profile_id}.json` · 参 `channel_to_credit_handoff.md` v1.0 契约 · session_id UUID v4 严格校验

---

## 3. Input Shape

| 维度 | 形态 |
|---|---|
| **触发源** | 客户经理在 `/archive/channel` workspace 主动发起 · IM `@channel 帮我找浙江制造业小微` 也可触发 (D.4 · IM tool calling) |
| **KB 文件类型** | xlsx/csv (客户名录 · 至少 `company_name`+`industry` 两列) · docx/pdf (政策文件) · docx/pdf (行业指引) · 任意组合 ≥1 类 |
| **预置场景** | 2 个 (master plan B.1 扩到 3-5 个) · `hangzhou_precision` (浙江制造业 look-alike) / `shenzhen_tech` (深圳科创 look-alike) · 客户经理免上传一键启动 |
| **Query 形态** | LLM 自动生成 3-5 条 query (region × industry × must_have_tags 笛卡尔积截断) · 不需用户填 |
| **可调参数** | `top_n` (默认 8 · UI 可调 5-20) · `red_threshold / yellow_threshold` (默认 80/65 · 风险偏好抽屉调) · `force_mock` (DEMO MODE 开关) |

---

## 4. Output Shape

### 4.1 UI 渲染 (panel 级 · 见 §7)

- **HeroBanner** · IdealProfile 卡 (12 维特征 chip 网格 · `reasoning` 段落) · "开始扫描" CTA
- **FunnelStrip** · 5 阶段进度 (KB 装载 → 画像抽取 → 外网搜索 → 匹配打分 → 产品推荐) · 每阶段实时数字
- **ScoreRadar** · IdealProfile 8 维雷达图 (本企业 vs 行业均值 vs 风险阈值) · 候选 click 后切到该候选的 derive radar
- **CandidatesPanel** · Top10 卡片列表 · 排名徽章 + 分级色 (红/黄/绿) + 总分 + 企业名 + 行业/地域/规模/营收 · 4 操作按钮 (查看证据 / 加入跟进 / handoff Agent3 / 详情 drawer)
- **SignalTimeline** · 选中候选的信号事件流 · 按日期倒序 · 每条 chip (类型 / 描述 / 来源 URL / 时间)
- **DetailDrawer** (右抽屉) · §2-C7/C8/C9 三块 · 匹配维度明细 + Top3 产品 + 切入话术
- **ConversationPanel** · IM 风对话气泡 · `@channel` 可触发本 Agent · 结果回 thread

### 4.2 文件导出

| 文件 | 后端端点 | 内容 |
|---|---|---|
| **xlsx (候选清单)** | `POST /api/channel/export_xlsx` (已实装) | 12 列 (`enterprise_name` / `unified_social_credit_code` / `business_line` / `match_score` / `signal_count` / `signal_types` / `approved_amount_yuan` / `source_urls` / `region` / `industry` / `recommended_products` / `data_sources`) |
| **docx (Word 报告)** | `POST /api/channel/export_docx` (Stage C 新建) | IdealProfile 卡 + Top10 候选 + 匹配明细 + 产品推荐 + 话术 + 证据链 · python-docx 本地生成（合规：禁境外 API） |
| **handoff JSON** | `POST /api/channel/handoff` (已实装) | 写本地 `data/handoff/channel_to_credit/{session_id}/{profile_id}.json` · Agent3 按 profile_id 拉取 |

---

## 5. Backend Endpoints

### 5.1 已实装 (api.py v4.0 · session 9)

| 方法 | 路径 | 请求体 | 响应 |
|---|---|---|---|
| GET | `/api/channel/scenarios` | — | `{scenarios: [{key, name, desc}]}` |
| POST | `/api/channel/run` | `{query: str, provider: "deepseek", api_key, top_n: 8, mock: bool}` | **SSE** · 5 阶段事件 (见 §5.3) |
| POST | `/api/channel/export_xlsx` | `{session_id, candidates: [...], business_line: "corporate"}` | `application/vnd.openxmlformats-...sheet` (xlsx 字节) · `Content-Disposition: attachment; filename="agent1_candidates_{session_id}.xlsx"` |
| POST | `/api/channel/handoff` | `{session_id (UUIDv4 必), candidates: [...], business_line}` | `{session_id, profile_ids: [...], paths: [...], count, schema_version: "1.0"}` |

### 5.2 Stage C 新建端点

| 方法 | 路径 | 请求体 | 响应 |
|---|---|---|---|
| POST | `/api/channel/upload_kb` | multipart/form-data · `kb_type: customers/policy/industry` · `files[]` | `{kb_id (uuid), kb_summary: "127 客户/18 规则/4200 字"}` · 落盘 `data/kb/channel/{kb_id}/` |
| POST | `/api/channel/profile` | `{kb_id}` | `{ideal_profile: IdealProfile JSON}` · LLM 1 次调用 (`PROFILE_EXTRACT_PROMPT` · DeepSeek temperature 0.2) |
| POST | `/api/channel/export_docx` | `{session_id, ideal_profile, candidates: [...含完整 hit.extras]}` | `application/vnd.openxmlformats-...document` (docx 字节) · 含全报告结构 |
| POST | `/api/channel/run` (扩字段) | 同 5.1 · 但请求加 `kb_id?: str` (有则消费 KB profile, 否则走 query 兜底) | 同 5.1 · 但 done 事件 payload 扩字段 (见 §5.3) |

### 5.3 SSE 事件契约 (master plan B.5)

```jsonc
// event: stage
{"event": "stage", "stage": "parse|signal_scan|aggregate|enrich", "status": "running|done", "progress": 0.6, "message": "正在搜索 query 2/4: 浙江 发明专利..."}

// event: candidate (Stage C 新增 · 流式吐 Top10 逐张)
{"event": "candidate", "rank": 1, "level": "red", "score": 91, "company_name": "杭州精工智造有限公司", "match_dimensions": [...], "products": [...], "pitch": "..."}

// event: done (Stage C 扩字段 · master plan B.5)
{
  "event": "done",
  "session_id": "uuid-v4",
  "ideal_profile": { /* 12 维 IdealProfile · live mode 真后端值 */ },
  "candidates": [ /* Top10 完整 hit list · 含 extras.match_dimensions / recommended_products / pitch_script */ ],
  "radar": { /* IdealProfile 8 维雷达数据 */ },
  "signals": [ /* 全部信号事件 flat list · 按 candidate 分组 */ ],
  "funnel": { "kb_loaded": true, "profile_extracted": true, "candidates_searched": 65, "candidates_matched": 50, "top_10_enriched": 10 },
  "match_dimensions": { "<candidate_id>": [...] },
  "product_recommendations": { "<candidate_id>": [...] },
  "pitch_scripts": { "<candidate_id>": "..." }
}

// event: error
{"event": "error", "stage": "...", "message": "...", "traceback": "..."}
```

### 5.4 降级路径 (Tavily 限流 / DeepSeek 崩)

- **Tavily 缺 key** → 后端 `realtime_stream` 自动 `mock_fallback` · 不 500 · `data_source: "mock_fallback"` 标在 SSE
- **`mock: true`** → 强制 mock 池 · 完全断网可演示 · 演示 default
- **DeepSeek 崩** → `parse` 阶段 yield error SSE · 前端 catch 切 `/public/mock/channel_run.json` fixture

---

## 6. Mock Sessions Structure (≥3 · master plan B.1 锚 3-5 个标杆企业)

### 6.1 Top-level shape (`web/lib/mock-sessions.ts` 或 `web/public/mock/channel_run.json`)

```typescript
type ChannelMockSession = {
  session_id: string;            // "session-hangzhou-001"
  scenario_key: string;          // "hangzhou_precision" / "shenzhen_tech" / "ningbo_supply_chain"
  display_name: string;          // 下拉切换显示
  ideal_profile: IdealProfile;   // 12 维画像
  funnel: FunnelMetrics;         // 5 阶段数字
  radar: RadarData;              // 8 维雷达
  candidates: Candidate[];       // Top10 完整
  signals: SignalEvent[];        // 全部信号 flat
};
```

### 6.2 三个标杆 session 数据要点

| session_id | 行业聚焦 | 区域 | 客户名录规模 | Top10 红/黄/绿 | 演示卖点 |
|---|---|---|---|---|---|
| `session-hangzhou-001` | 浙江制造业（精密机械 + 智能制造）| 杭州/宁波/温州/绍兴 | 30 家 | 5R/4Y/1G | 专精特新政策匹配 · 发明专利硬约束 |
| `session-shenzhen-002` | 长三角/珠三角科创 | 深圳/上海/苏州 | 25 家 | 6R/3Y/1G | 国家高新认定 + 融资轮次 A+ |
| `session-ningbo-003` | 汽车供应链上下游 | 浙江/江苏 | 40 家 (汽车零部件) | 3R/5Y/2G | 行业景气下行交叉 + 核心客户传染 |

### 6.3 单个 candidate 数据契约 (Stage C 严守 · 不可缺字段)

```typescript
type Candidate = {
  rank: number;                   // 1..10
  candidate_id: string;           // "cand_hzpr_001"
  level: "red" | "yellow" | "green";
  score: number;                  // 综合 0-100
  profile_score: number;          // 4a 画像相似度
  anchor_score: number;           // 4b 样本锚相似度
  company_name: string;
  unified_credit_code: string;
  industry: string;
  sub_industry: string;
  region: string;
  scale: "微型" | "小型" | "中型" | "大型";
  revenue_yuan: number;           // 不带单位字符串
  employee_count: number;
  match_dimensions: MatchDimension[]; // ≥4 chip
  reasons: string[];              // 匹配理由 3-5 条
  recommended_products: ProductRec[]; // 必 ≥3
  pitch_script: string;           // 必非空 · 60-150 字
  signals: SignalEvent[];         // 该候选的信号子集
  evidence: Evidence;             // 样本锚 + 命中规则 + 数据来源
  top3_anchors: string[];         // 已有客户名 · ["宁波华联轴承", ...]
};

type MatchDimension = {
  dim: "industry" | "region" | "scale" | "tags" | "revenue" | "stage" | "qualifications";
  label: string;                  // "行业 SaaS"
  matched: boolean;
  evidence_source: string;        // signal_id 或 KB ref
  display: string;                // "✓ 命中标杆 / 行业分 95"
};
```

---

## 7. Panel Architecture (`/archive/channel/_components/`)

| Panel 组件 | 数据源 (props) | 切 session 重渲 | 候选 click 联动 |
|---|---|---|---|
| `ChannelHero.tsx` | `idealProfile` + `funnel` + `kb_summary` | ✓ | — |
| `FunnelStrip.tsx` | `funnel` | ✓ | — |
| `ScoreRadar.tsx` | `radar` (默认 IdealProfile · candidate click 切 derive radar) | ✓ | ✓ |
| `CandidatesPanel.tsx` | `candidates` (Top10) · `onSelect(candidateId)` | ✓ | — |
| `SignalTimelinePanel.tsx` | `signals` filtered by selected candidate · 默认全部 | ✓ | ✓ |
| `CandidateDetailDrawer.tsx` (新增 master plan B.4/B.4b/B.4c) | selected candidate `match_dimensions` / `recommended_products` / `pitch_script` / `evidence` | — | ✓ (主) |
| `ConversationPanel.tsx` | thread (复用 dispatch IM ConversationPanel) | — | — |

### 7.1 Panel state hoist (master plan B.2)

`ChannelWorkspace.tsx` 持有：

```typescript
const [selectedSessionId, setSelectedSessionId] = useState<string>(MOCK_SESSIONS[0].session_id);
const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
const [drawerOpen, setDrawerOpen] = useState(false);
const [livePayload, setLivePayload] = useState<LiveChannelPayload | null>(null); // 真 SSE done 数据
const [mode, setMode] = useState<"mock" | "live">("mock");
```

各 panel 通过 props 接 state · **禁止 import `CHANNEL_SESSION` 全局常量**（已在 master plan #3 列为 gap，Stage C 必清）。

### 7.2 路由约束 (CLAUDE.md §7 红线)

- ✅ 唯一入口 `/archive/channel` (canon)
- ❌ 禁止重新引入顶层 `/channel` (legacy 已清)
- ❌ 禁止复活 Letterpress / crimson tokens

---

## 8. Regression Risks (Stage C Worker 必读 · trailer 必列 PRESERVES)

`docs/features-inventory.md` 中以下 features 不可破坏：

| ID | Feature | Selector | 验证 spec |
|---|---|---|---|
| F-001 | Black-hole login shader (Gargantua R3F) | `[data-testid="login-shader"]` | `web/tests/login.spec.ts` |
| F-005 | QueryBar 自由搜索 (LLM 解析意图) | `[data-testid="channel-querybar"]` | `web/tests/channel-querybar.spec.ts` |
| F-006 | ScoreRadar 8 维雷达 | `[data-testid="score-radar"]` | `web/tests/score-radar.spec.ts` |
| F-channel-* | (Stage A.3 worker A1 扩展中) | (待 A1 完成后并入此表) | (待补) |

**已知 v1.0 资产 PRESERVE (PRD §11 验收 A4)**：
- `agent_channel/channel_rules.py` (CHANNEL_CATALOG · 13 子渠道) · **0 修改**
- `agent_channel/scoring.py` (5 维评分 · 政策加分 · 地域加分) · **0 修改**
- `EvidenceTrail` 组件 (Wave 2 frontend-integration 已挂) · 不许移除

**红区禁触**（见 `shared-change-protocol.md`）：
- `shared/base_agent.py` / `shared/api_utils.py` / `shared/enterprise_profile.py` 改签名 → RFC
- `shared/sources/router.py` / `shared/sources/base.py` 改 Protocol → RFC
- 黄区追加新 source / 新 method 自由

---

## 9. LLM 调用预算 (PRD §7 + 演示成本控制)

| 调用点 | 频次 | 模型 | Temp | 备注 |
|---|---|---|---|---|
| **画像抽取** | 1/session | DeepSeek-chat | 0.2 | 必须 JSON 输出 · 失败 3 次重试后规则兜底 |
| **规则抽取** (政策→规则) | N/政策文件 | DeepSeek-chat | 0.2 | 可选 · 无政策跳过 |
| **切入话术** | Top10 合并 1-2 调用 | DeepSeek-chat | 0.5 | 批量 prompt 一次返 10 段话术 |
| **意图解析** (QueryBar) | 1/query | DeepSeek-chat | 0.3 | F-005 已实装 · 不重复 |

**Demo 总预算**：≤15 次 LLM 调用 / session （含话术合并优化后 ≤5 次）

---

## 10. Acceptance for Stage C

- [ ] 12 个 capability (§2 C1-C12) 全 ✓
- [ ] 4 个新端点 (§5.2) 真跑通 · curl 验返 LLM reply (DEEPSEEK_API_KEY 已配)
- [ ] 7 个 panel (§7) 全 props 化 · 删 import `CHANNEL_SESSION` 全局
- [ ] 3 个 mock session (§6) 落 `web/lib/mock-sessions.ts`
- [ ] 5 个 Playwright smoke pass (channel-mock-switch / channel-live-search / candidate-detail-drawer / channel-upload-kb-profile / channel-export-docx)
- [ ] features-inventory.md 加 F-channel-* entries (待 A1 worker 完成 base set 后追加)
- [ ] commit trailer 必含 `PRESERVES` (列 §8 features) · `NEW-DOM` (新 testid) · `SMOKE-PASS` (跑通的 spec)
- [ ] tsc --noEmit 0 error · ECS deploy verify 通

---

## 11. References

- 上游 PRD: `docs/PRD_全渠道流量匹配智能体_v2.0.md`
- 上下游契约: `docs/contracts/channel_to_credit_handoff.md` (Agent1 → Agent3 handoff v1.0)
- API map: `docs/contracts/shell-v1-agent-api-map.md` § Agent 1
- 字段命名: `docs/contracts/field-naming.md`
- 共享变更协议: `docs/contracts/shared-change-protocol.md`
- Master plan: `docs/contracts/master-execution-plan-2026-04-27.md` § Stage B + Stage C.1
- Workspace state: `docs/contracts/workspace-state-protocol.md` (Stage A.4 worker A2 产出 · 待并入)
