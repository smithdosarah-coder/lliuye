# Agent3 Credit · Spec for Stage C Worker

> **Source PRD**: `docs/PRD_授信决策辅助智能体_v2.0.md` (canonical · v1.0 已废)
> **Workspace route**: `/archive/credit` (canon, 见 CLAUDE.md §7)
> **Backend module**: `agent_credit/api.py` (FastAPI v3.1 · 已挂载) + `decision_engine.py` 流水线
> **Stage C 任务**: 后端补 LLM (现 stub)+ 4 维评分 + 红线判定 + panel hoist + Word 导出
> **关键边界**: Agent3 = 决策支持（不写报告）· 上游消费 Agent6 ReportJSON · 决策回写 Agent6 第 4 章

---

## 1. Product Positioning

Agent3 是**授信决策支持引擎（对公 + 对私双板块）**——它不生产授信报告，它消费授信报告（Agent6 ReportJSON + 多源补充）；它不代替审贷会拍板，它把审贷会 1 小时才能看完的材料压缩成 90 秒看懂的决策 Dashboard，把"批 / 不批 / 额度 / 期限 / 利率 / 触发红线"的建议一次性摆桌上。

**双板块**：🏢 对公（企业授信 50-5000 万 · 四维风险评分 · 分钟级）+ 👤 对私（个人/零售 5-500 万 · 评分卡 FICO 式 · 秒级）· 顶部 Tab 切换 · 后端共享 `DecisionEngine` / `RuleEngine` / `CaseRetriever` / `AdvisorFormatter` · 仅 `ScoringModel` 按板块切换。

**与 Agent6 边界**（v2.0 最重要的一条）：
- Agent6 = 文书自动化（写 15000 字报告）· Agent3 = 决策支持（出 Dashboard + 决策卡片）
- Agent3 输入不是企业原始材料，而是 Agent6 的 ReportJSON
- Agent3 决策可一键回写 Agent6 第 4 章"审批意见"
- 不允许同时摆给客户出"两份结论"

**与 Agent1 边界**：Agent1 推线索 + 产品 · Agent3 接 Agent1 handoff 的候选企业（`channel_to_credit_handoff.md` v1.0）做尽调 → 决策。

---

## 2. Capabilities (Numbered · Stage C Worker 逐项实装并打 ✓)

- [ ] **C1 双板块 Tab** · `🏢 对公` / `👤 对私` 顶部切换 · 切换重渲左侧输入区 + 中间 Dashboard + 右侧决策卡片 · `segment` query 参数贯通后端
- [ ] **C2 Agent6→Agent3 handoff 接收** · sessionStorage `enterprise_profile` 触发 applyProfile · 顶部横幅"已从 Agent6 加载 [企业名] 报告（生成于 ...）" · 后端 `/api/credit/handoff/demo/{segment}` 已实装样本
- [ ] **C3 Agent1→Agent3 handoff 接收** · 读 `data/handoff/channel_to_credit/{session_id}/{profile_id}.json` · 严格 UUID4 + schema_version 校验 · 只消费 `enterprise_profile` 子字段（不依赖 `candidate_profile` 绿区字段）
- [ ] **C4 FeatureExtractor (确定性)** · 对公 60+ 特征 5 类 (financial / industry / operational / guarantee / external) · 对私 22 评分卡变量 4 类 (偿债 / 意愿 / 稳定 / 抵押) · 0 LLM 调用
- [ ] **C5 ScoringModel_对公 (确定性)** · 四维风险加权 (财务 0.35 / 行业 0.15 / 经营 0.25 / 担保 0.25) · 复用 v1.0 `risk_classifier.py` (PRESERVES) · 输出 `composite_score (0-100) + risk_grade (A/B/C/D)` · 阈值 (A≥80 / B≥65 / C≥50 / D<50)
- [ ] **C6 ScoringModel_对私 (确定性)** · FICO 式评分卡 300-850 · 4 大类加权 (偿债 0.30 / 意愿 0.25 / 稳定 0.25 / 抵押 0.20) · 等级映射 (优≥800 / 中优 760-799 / 良好 700-759 / 边界 680-699 / 拒<680) · 利率档位 LPR-10BP ~ LPR+50BP
- [ ] **C7 RuleEngineV2 (红线规则引擎)** · 对公 30 条 + 对私 20 条 · JSON 配置可编辑 · 可配置阈值（`risk_appetite_config.py` 风险偏好覆盖默认）· 输出 `RedLineHit[]` (rule_id / severity / is_hard / can_waive / waiver_conditions)
- [ ] **C8 CaseRetriever (确定性)** · 对公 50 条 + 对私 10 条历史案例 · 相似度算法 (对公: 行业 0.3 + 营收 0.2 + 四维评分 0.3 + 申请额度 0.2) · Top-K=5
- [ ] **C9 额度测算 (确定性)** · 对公 4 法取交集 (营收法 / 净资产法 / 现金流法 / 担保法) · 对私 取 min (评分档上限, 抵押 70%, 月收入×20)
- [ ] **C10 AdvisorFormatter (LLM)** · 对公 2 次调用 (决策说明 + 红线解释 · 各 1 次) · 对私 0-1 次（仅边界案例 / 命中红线时） · 输出 `DecisionAdvice` 自然语言
- [ ] **C11 SSE 流水线流式** · 7 阶段 `profile_loaded / feature_extracting / feature_done / scoring / scoring_done / rule_checking / rule_done / case_retrieving / case_done / advising / advising_done / done` · 每阶段独立事件
- [ ] **C12 风险偏好抽屉 (RiskAppetiteConfig)** · 维度权重 slider · 30/20 条红线规则 toggle + 阈值 inline edit · 评分等级门槛 · 保存 `config/risk_appetite_{client_id}.json` · 现场修改 → Dashboard 实时重算
- [ ] **C13 决策回写 Agent6** · 右下角"回写到 Agent6 报告"按钮 · 弹确认框 · POST `/api/report/credit_writeback` · 把 `DecisionAdvice` 写第 4 章"审批意见" · 切回 Agent6 验证
- [ ] **C14 Word 导出决策意见书** · `/api/credit/export_docx` (已实装 · python-docx 本地 · 禁海外 API) · 含 Dashboard 截图 + 决策卡 + 红线明细 + 案例对比
- [ ] **C15 双 Dashboard 差异化** · 对公: 雷达图 + 行业基准条形图 + 案例表格 + 额度测算条形图 · 对私: 评分卡构成 + 征信快照 + 抵押估值 + 评分档位映射表
- [ ] **C16 Risk Radar Preview** (Wave 2 frontend-integration · L1-3 · Q-033 closed sub-signal `FRONTEND-RISK-RADAR-LANDED`) · `[data-testid="risk-radar-preview"]` · 默认 `data-scanned=no` 折叠 · 点 CTA "生成授信辅助" 切 yes
- [ ] **C17 LLM 状态降级** · DeepSeek 崩 → SSE yield error 在 advising 阶段 · 前端展示前 4 段已拿到的结构化结果 (feature+score+rules+cases) · advising 切 fallback 文案

---

## 3. Input Shape

| 维度 | 形态 |
|---|---|
| **触发源 1** | 客户经理在 `/archive/credit` workspace 主动选 preset · IM `@credit 评估鼎盛商贸` 也可触发 |
| **触发源 2 (主)** | Agent6 完成报告后点"送 Agent3 做决策" · sessionStorage `enterprise_profile` + `agent6_report_json` 自动载入 |
| **触发源 3** | Agent1 候选 click "传递给 Agent3" · 从 `data/handoff/channel_to_credit/{session_id}/{profile_id}.json` 读 |
| **预置 preset** | 对公 3 (`dingsheng_trade` / `ruiheng_precision` / `zhongrui_network`) + 对私 3 (`zhangsan_restaurant` / `lisi_education` / `wangwu_decoration`) · 已实装 (`/api/credit/presets/{segment}`) |
| **segment** | `corporate` / `retail` 二选一 · 后端代码切 ScoringModel |
| **风险偏好** | 可选 `appetite_config_id` · 不传走默认 |

---

## 4. Output Shape

### 4.1 UI 渲染 (panel 级 · 见 §7)

#### 4.1.1 对公 Dashboard
- **ProfileSummary** · 左侧画像卡（行业 / 营收 / 员工 / 抵押 + Agent6 报告生成时间戳）
- **RadarScore** · 四维雷达图 (财务/行业/经营/担保) · 实线 = 本企业 · 虚线红 = 警戒线 (60) · 虚线灰 = 行业均值
- **IndustryBench** · 4-6 项行业基准条形图（资产负债率 / 营收增长率 / 应收账款天数 / 净利率） · 标领先/落后
- **CaseTable** · Top5 相似案例 · 列 (企业 / 行业 / 营收 / 申请额 / 评分 / 决策 / 理由)
- **AmountChart** · 4 法测算条形图 (营收 / 净资产 / 现金流 / 担保) + 综合区间 + 申请额标记
- **DecisionLetter** · 右侧决策卡片 (结论 / 风险等级 / 额度 / 期限 / 利率 / 红线 / 豁免 / 案例摘要)

#### 4.1.2 对私 Dashboard
- **ProfileSummary** · 左侧个人画像 (年龄 / 职业 / 月收入 / 抵押)
- **ScorecardBars** · 4 大类评分条形图 + 子项明细
- **CreditSnapshot** · 征信报告摘要卡片 (贷款笔数 / 信用卡 / 查询次数 / 逾期 / 担保)
- **CollateralPanel** · 抵押估值明细 (类型 / 评估值 / 产权 / LTV / 估值来源)
- **GradeMatrix** · 评分档位映射表 · 当前客户高亮一行
- **DecisionLetter** · 右侧决策卡片 (FICO 评分 / 档位 / 决策 / 额度 / 利率档位 / 红线)

#### 4.1.3 共享
- **StageTabs** (`stage-tabs.tsx`) · 7 阶段状态灯
- **RedLinesPanel** · 红线命中列表 · 每条 (rule_id / 严重度 / 实际值 vs 阈值 / 是否可豁免 / 豁免条件)
- **HandoffButtons** · "从 Agent6 加载" / "回写到 Agent6" 两按钮
- **AppetiteDrawer** (右滑) · 风险偏好配置
- **EvidenceTrail** (Wave 2 · 不许移除) · 每个评分维度 / 红线命中回指 ReportJSON 引用
- **ConversationPanel** · IM 风对话气泡

### 4.2 文件导出

| 文件 | 后端端点 | 内容 |
|---|---|---|
| **决策意见书 docx** | `POST /api/credit/export_docx` (已实装) | python-docx 本地 · 含 subject_name + decision + 完整 advice payload · RFC 5987 中文文件名 |
| **handoff JSON (Agent3 → Agent6 回写)** | `POST /api/report/credit_writeback` (Stage C 报告侧新建 · 见 `agent-report-spec.md` §5.2) | session_id + advice → 第 4 章 |

---

## 5. Backend Endpoints

### 5.1 已实装 (api.py v3.1)

| 方法 | 路径 | 请求 | 响应 |
|---|---|---|---|
| GET | `/api/credit/presets/{segment}` | path: `corporate` / `retail` | `{segment, presets: [string]}` |
| GET | `/api/credit/handoff/demo/{segment}` | path | `{segment, profile, preset_name, source_file}` (从 `demo_data/agent_credit/corp_*.json` 或 `retail_*.json` 取首个) |
| POST | `/api/credit/decision` | `{segment, preset_name, provider?, api_key?}` | **SSE** · 7 阶段事件 (见 §5.3) |
| POST | `/api/credit/export_docx` | `{advice: dict}` | docx file |

### 5.2 Stage C 新建 / 扩展端点

| 方法 | 路径 | 请求 | 响应 | 备注 |
|---|---|---|---|---|
| POST | `/api/credit/decision` (扩) | + `enterprise_profile?: dict` (从 sessionStorage 透传) + `appetite_config?: dict` | 同 5.1 | 不仅消费 preset · 也可消费 Agent6/Agent1 实时透传 EP |
| POST | `/api/credit/handoff/import` | `{handoff_path: str}` (Agent1 来源) · 严格 UUID4 + schema_version 校验 | `{enterprise_profile, candidate_profile_meta}` | Agent1 → Agent3 入口 |
| POST | `/api/credit/handoff/from_report` | `{session_id (Agent6)}` | `{enterprise_profile, ready_for_decision: bool}` | Agent6 → Agent3 显式入口（替代 sessionStorage 隐式传） |
| POST | `/api/credit/writeback_to_report` | `{session_id, advice: DecisionAdvice}` | `{updated, chapter_4_text, target_section_id}` | 主 CLI 拍板：在 Agent3 侧而非 Agent6 侧实装 (避免 Agent6 红区) |
| GET | `/api/credit/red_line_rules/{segment}` | path | `{rules: [...]}` | 读 `mock_data/red_line_rules_{segment}.json` · 风险偏好抽屉用 |
| POST | `/api/credit/red_line_rules/{segment}` | `{rules: [...]}` | `{saved, config_id}` | 保存自定义偏好 |

### 5.3 SSE 事件契约（已实装 + Stage C 扩字段）

```jsonc
// event: profile_loaded
{"event": "profile_loaded", "profile": {"profile_id": "corp_dingsheng_001", "company_name": "...", "financial_anchors": {...}}}

// event: stage (Stage C 标准化)
{"event": "stage", "stage": "feature_extracting|feature_done|scoring|scoring_done|rule_checking|rule_done|case_retrieving|case_done|advising|advising_done", "payload": {...}}

// 各 stage payload 示例
// feature_done
{"financial.debt_ratio": 0.45, "financial.revenue_growth": 0.22, /* 60+ 特征 */}

// scoring_done
{"composite_score": 70, "risk_grade": "B", "sub_scores": {"financial": 72, "industry": 65, "operational": 78, "guarantee": 82}}

// rule_done
[{"rule_id": "corp_rl_001", "rule_name": "关联交易占比", "is_hard": false, "can_waive": true, "severity": "medium", "actual_value": 0.32, "threshold": 0.30, "waiver_conditions": ["关联交易审计说明"]}]

// case_done
[{"case_id": "case_corp_022", "company_name": "启明软件", "similarity": 0.92, "decision": "批", "approved_amount": 400, "interest_rate": 0.062}]

// advising_done
{"decision": "有条件批准", "approved_amount": 300, "approved_term": 36, "interest_rate": 0.065, "rate_benchmark": "LPR+85BP", "risk_grade": "B", "composite_score": 70, "conditions": ["关联交易审计说明", "季度应收账款账龄表"], "red_line_explanations": [...], "decision_reason": "..."}

// event: done
{"event": "done"}

// event: error
{"event": "error", "message": "...", "traceback": "..."}
```

### 5.4 降级路径

- **DeepSeek 缺 key (api_key="dummy")** → scoring/rule/case 段确定性走 · advising 段 yield error · 前端展示前 4 段结构化结果 + 模板化 fallback advice
- **Agent6 ReportJSON 缺字段** → FeatureExtractor 跳过 · 该维度评分置 N/A 标灰 · 不阻断
- **Agent1 handoff JSON schema_version 不匹配** → 400 + 明确 error code · 前端引导用户重发

---

## 6. Mock Sessions Structure (≥3 per segment · 共 6+)

### 6.1 Top-level shape

```typescript
type CreditMockSession = {
  session_id: string;
  segment: "corporate" | "retail";
  preset_name: string;
  display_name: string;
  source: "agent6_handoff" | "agent1_handoff" | "manual_select";
  enterprise_profile: EnterpriseProfile | PersonalProfile;
  features: FeatureMap;           // 60+ 对公 / 22+ 对私
  scoring_result: ScoringResult;
  rule_hits: RedLineHit[];
  case_matches: CaseMatch[];
  advice: DecisionAdvice;
};
```

### 6.2 6 个标杆 session

| session_id | segment | preset | 演示卖点 |
|---|---|---|---|
| `corp-dingsheng-001` | corporate | `dingsheng_trade` | D 级 · 高负债率 0.8 · 关联方 + 负债率双红线 · 批拒边界 |
| `corp-ruiheng-002` | corporate | `ruiheng_precision` | A 级 · 精密制造 · 营收增长 22% · 全部维度领先 · 直接批 300 万 |
| `corp-zhongrui-003` | corporate | `zhongrui_network` | B 级 · 互联网 SaaS · 关联交易 32% (软红线 · 可豁免) · 应收账款 140d · 有条件批 (Q-040 中锐网络真材料 dry-run baseline) |
| `retail-zhangsan-001` | retail | `zhangsan_restaurant` | 720 良好 · 餐饮个体户 · 抵押充足 · 批 50 万 · LPR+20BP |
| `retail-lisi-002` | retail | `lisi_education` | 695 边界 · 教培行业（监管收紧）· 触发对私红线 · 人工复核 |
| `retail-wangwu-003` | retail | `wangwu_decoration` | 810 优 · 装修工头 · 房产抵押 · 批 200 万 · LPR-10BP |

### 6.3 数据契约

```typescript
type ScoringResult = {
  composite_score: number;        // 0-100 (对公) / 300-850 (对私)
  risk_grade: string;             // A/B/C/D (对公) / 优/中优/良好/边界/拒绝 (对私)
  sub_scores: Record<string, number>;
  industry_peer_percentiles?: Record<string, number>; // 仅对公
};

type RedLineHit = {
  rule_id: string;
  rule_name: string;
  threshold: number;
  actual_value: number;
  severity: "high" | "medium" | "low";
  is_hard: boolean;               // 命中必拒
  can_waive: boolean;
  waiver_conditions: string[];
  description: string;
};

type CaseMatch = {
  case_id: string;
  company_name: string;
  similarity: number;             // 0-1
  features_summary: Record<string, any>;
  decision: "批" | "有条件批" | "拒";
  approved_amount: number;
  approved_term: number;
  interest_rate: number;
  decision_reason: string;
  hit_red_lines: string[];
};

type DecisionAdvice = {
  decision: "批准" | "有条件批准" | "拒绝";
  approved_amount: number;        // 万元
  approved_term: number;          // 月
  interest_rate: number;          // 小数 (0.065 = 6.5%)
  rate_benchmark: string;         // "LPR+85BP"
  risk_grade: string;
  composite_score: number;
  conditions: string[];
  red_line_explanations: Array<{
    rule_id: string;
    explanation: string;
    severity: string;
    can_waive: boolean;
  }>;
  decision_reason: string;        // LLM 自然语言
  similar_cases_summary: string;
};
```

---

## 7. Panel Architecture (`/archive/credit/_components/`)

| Panel 组件 | 板块 | 数据源 (props) | 切 segment 重渲 |
|---|---|---|---|
| `ProfileSummary.tsx` | both | `enterprise_profile` / `personal_profile` | ✓ |
| `StageTabs.tsx` | both | `stage` (7 阶段状态灯) | — |
| `RadarScore.tsx` | corporate | `scoring_result.sub_scores` (4 维) | ✓ |
| `IndustryBench.tsx` | corporate | `feature_map` 财务比率 + `industry_baselines` | ✓ |
| `CaseTable.tsx` | corporate | `case_matches` Top 5 | ✓ |
| `AmountChart.tsx` | corporate | `amount_calculations` (4 法 + 综合) | ✓ |
| `ScorecardBars.tsx` | retail | `scoring_result.sub_scores` (4 大类) | ✓ |
| `CreditSnapshot.tsx` | retail | `personal_profile.credit_report` | ✓ |
| `CollateralPanel.tsx` | retail | `personal_profile.collateral` | ✓ |
| `GradeMatrix.tsx` | retail | `scoring_result.fico_score` 高亮一行 | ✓ |
| `RedLinesPanel.tsx` | both | `rule_hits` | ✓ |
| `DecisionLetter.tsx` | both | `advice` | ✓ |
| `RiskRadarPreview.tsx` (Wave 2 · L1-3 · Q-033 closed) | both | `risk_radar_data` · `[data-scanned]` gate | ✓ |
| `HandoffButtons.tsx` | both | session_id + segment + advice | — |
| `AppetiteDrawer.tsx` | both | rules + weights · onSave callback | ✓ |
| `EvidenceTrail.tsx` (Wave 2 · 不许移除) | both | evidence refs | ✓ |
| `ConversationPanel.tsx` | both | thread | — |

### 7.1 Panel state hoist

```typescript
const [segment, setSegment] = useState<"corporate" | "retail">("corporate");
const [presetName, setPresetName] = useState<string>("dingsheng_trade");
const [profile, setProfile] = useState<EnterpriseProfile | PersonalProfile | null>(null);
const [livePayload, setLivePayload] = useState<DecisionPipelineResult | null>(null);
const [appetiteConfig, setAppetiteConfig] = useState<RiskAppetiteConfig>(defaultAppetite);
const [appetiteOpen, setAppetiteOpen] = useState(false);
const [scanned, setScanned] = useState(false);  // RiskRadarPreview gate (Q-039 lesson)
```

### 7.2 路由 + 红线

- ✅ 唯一入口 `/archive/credit`
- ❌ 禁顶层 `/credit` (legacy)
- 板块切换走 query param `?segment=corporate`（不是新路由）

---

## 8. Regression Risks

| ID | Feature | Selector | 验证 spec |
|---|---|---|---|
| F-risk-radar | RiskRadarPreview (Wave 2 · Q-033) | `[data-testid="risk-radar-preview"]` | `web/tests/risk-radar.spec.ts` (Q-039 fix · 必带 CTA gate trigger) |
| F-evidence-trail | EvidenceTrail (Wave 2) | `[data-testid="evidence-trail"]` | `web/tests/evidence-trail.spec.ts` |
| F-highlight-card | HighlightCard (Wave 2) | `[data-testid="highlight-card"]` | `web/tests/highlight-card.spec.ts` |
| F-unfilled-marker | UnfilledMarker (Wave 2) | `[data-testid="unfilled-marker"]` | `web/tests/unfilled-marker.spec.ts` |

**v1.0 资产 PRESERVE**：
- `risk_classifier.py` (5 维风险分类 · 改造为对公 4 维)
- `rating_engine.py` (A-E 评级映射)
- `approval_engine.py` (规则骨架被 RuleEngineV2 复用)
- v1.0 第 5.4 节四维评分公式 (分段线性插值)
- v1.0 第 5.5 节四种额度测算方法 (营收/净资产/现金流/担保)

**红区禁触**：
- `shared/enterprise_profile.py` 改字段 → RFC（破坏 handoff 协议）
- `agent_report/enterprise_profile.py` (authoritative) 同上
- `shared/report_handoff.py` → RFC

**v2.0 明确作废 (PRD §2.3)**：
- v1.0 三栏式布局
- v1.0 接口 2 (独立 Agent 输出给外部审批系统) → 改为 Agent3 → Agent6 回写

---

## 9. LLM 调用预算

| 板块 | 调用点 | 频次 | 模型 | Temp |
|---|---|---|---|---|
| 对公 | 决策说明 (decision_reason) | 1/session | DeepSeek-chat | 0.3 |
| 对公 | 红线解释 (red_line_explanations) | 1/session 批量 | DeepSeek-chat | 0.3 |
| 对私 | 决策说明 (仅边界 / 红线命中) | 0-1/session | DeepSeek-chat | 0.3 |
| 共享 | 案例对比解读 (可选) | 0/1/session | DeepSeek-chat | 0.3 |

**Demo 总预算**：对公 ≤2 次 · 对私 ≤1 次 · 演示成本 < 0.10 元/session

**演示量化指标 (PRD §3.3)**：
- 对公端到端决策耗时 < 2 分钟（点击 → Dashboard 完整）
- 对私端到端决策耗时 < 10 秒
- Agent6 → Agent3 串联耗时 < 3 秒
- 决策回写耗时 < 2 秒

---

## 10. Acceptance for Stage C

- [ ] 17 个 capability (§2 C1-C17) 全 ✓
- [ ] 6 个新/扩端点 (§5.2) 真跑通
- [ ] 17 个 panel (§7) 全 props 化 · 双板块切换无状态污染
- [ ] 6 个 mock session (§6) 落 `web/lib/mock-sessions.ts`
- [ ] 5 个 Playwright smoke pass (credit-segment-switch / credit-corporate-decision / credit-retail-decision / credit-handoff-from-report / credit-writeback-to-report)
- [ ] features-inventory.md F-risk-radar PRESERVES (Q-039 lesson · spec 必带 CTA trigger)
- [ ] commit trailer 必含 `PRESERVES: F-risk-radar, F-evidence-trail, F-highlight-card, F-unfilled-marker`
- [ ] tsc --noEmit 0 error · ECS deploy verify 通

---

## 11. Handoff Contracts (上下游)

### 11.1 Agent6 → Agent3 (主链路)

**触发**：Agent6 完成报告 → 用户点"送 Agent3 做决策"

**载体**：sessionStorage `enterprise_profile` + `agent6_report_json` (master plan C.2 · 当前隐式传) · Stage C 显式化为 `POST /api/credit/handoff/from_report`

**消费点**：Agent3 `applyProfile()` → `FeatureExtractor.extract(profile, segment="corporate")`

**回写**：Agent3 决策完成 → `POST /api/credit/writeback_to_report` → Agent6 第 4 章

### 11.2 Agent1 → Agent3 (次链路)

**触发**：Agent1 候选卡 click "传递给 Agent3"

**载体**：本地文件 `data/handoff/channel_to_credit/{session_id}/{profile_id}.json`

**契约版本**：v1.0 (`channel_to_credit_handoff.md`)

**消费点**：Agent3 读 `enterprise_profile` 子字段 (UUID4 校验 · schema_version 检查)

### 11.3 Agent3 输出（无下游 Agent · 仅人审）

`DecisionAdvice` JSON · 客户经理读 + 审贷会用 + Agent6 第 4 章回写

---

## 12. References

- 上游 PRD: `docs/PRD_授信决策辅助智能体_v2.0.md`
- Agent6 spec: `docs/contracts/agent-report-spec.md`
- Channel→Credit handoff: `docs/contracts/channel_to_credit_handoff.md` v1.0
- API map: `docs/contracts/shell-v1-agent-api-map.md` § Agent 3
- 字段命名: `docs/contracts/field-naming.md`
- 共享变更协议: `docs/contracts/shared-change-protocol.md`
- Master plan: `docs/contracts/master-execution-plan-2026-04-27.md` § Stage C.2
- Q-033 RiskRadar 路由: `docs/handoff/decisions-log.md` Q-033
- Q-039 spec verify lesson: `docs/handoff/decisions-log.md` Q-039
- Workspace state: `docs/contracts/workspace-state-protocol.md` (待 A2 worker)
