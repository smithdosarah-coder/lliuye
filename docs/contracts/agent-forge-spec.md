# Agent2 Forge / Riskctrl · Spec for Stage C Worker

> **Source PRD**: `docs/PRD_风控策略运营助手_v1.0.md` (canonical · 单 v1.0 · 无 v2)
> **Workspace route**: `/archive/riskctrl` (canon, 见 CLAUDE.md §7)
> **Backend module**: `agent_riskctrl/api.py` (FastAPI v3.1 · session 9 已挂载) + `rule_engine.py` / `backtesting.py` / `metrics.py` (v1.0 保留 0 改动) + `baseline_ruleset.py` / `llm_judge.py` (Wave 2 8b 新增)
> **Stage C 任务**: 后端补 LLM (现 stub) + DSL 真生成 + 真回测 + panel hoist
> **架构定位**: 自然语言策略配置 + 历史数据回测 + 差错诊断 三场景闭环

---

## 1. Product Positioning

Agent2 是**风控策略运营助手**——支持自然语言配策略、自动回测评估、差错案件诊断 · 让风控运营人员无需编写代码即可完成策略全生命周期管理。

**3 分钟闭环**：策略描述（自然语言）→ DSL 规则生成（LLM）→ 历史数据回测（确定性）→ 指标可视化（KS/PSI/混淆矩阵/F1）→ LLM 分析报告 → 优化建议 → 一键应用 → 新旧策略对比。

**与其他 5 Agent 关系**（PRD §9）：
- 上游消费 Agent6 财务锚点（debt_ratio / annual_revenue 等真实数值）→ 回测真实数据补充
- 上游消费 Agent3 风险标签 → 作为策略规则参考维度
- 下游产 策略命中结果 给 Agent3（命中拒绝规则 → 建议人工复核）
- 下游产 策略阈值配置 给 Agent4（预警判断企业是否接近触发阈值）
- 下游产 策略变更记录 给 Agent5（合规审计策略变更是否经审批）

**Demo 阶段实现**：不做实时 Agent 间调用 · 走预置 JSON · 未来接通走 `AgentBus` 接口 stub。

**非"知识库扫描"范式**：Agent2 不属 Agent1/4/5 的 KB 扫描雷达底座 · 它是 DSL/回测/指标三件套 · 共享 base_agent + demo_ui 即可。

---

## 2. Capabilities (Numbered · Stage C Worker 逐项实装并打 ✓)

- [ ] **C1 三场景一键启动** · 小微信用贷回测 / 差错案件诊断 / 自然语言配策略 · 预置数据自动加载 ≤ 2 秒
- [ ] **C2 自然语言 → DSL 规则** · LLM (DeepSeek temperature 0.3) 走 `SYSTEM_RULE_PARSER` · 输入"拒绝负债率超过 80% 的企业" → 输出 `{"field": "debt_ratio", "operator": ">", "value": 0.8, "action": "reject"}` · JSON 解析失败重试 1 次
- [ ] **C3 多轮规则追加** · 连续输入"再加一条：成立不满 1 年的也拒绝" → 累积生成完整 RuleSet (priority 自动排序 · 命中即停)
- [ ] **C4 RuleSet 编辑** · DSL 代码块只读/可编辑切换 · 语法高亮 · 用户可手动调整阈值
- [ ] **C5 8 操作符支持** · `>` `<` `>=` `<=` `==` `!=` `in` `not_in` · 严格校验
- [ ] **C6 历史数据加载** · CSV/Excel 多编码自动检测 · 100 条授信数据 (`credit_data.csv`) 字段固定 (`enterprise_id / industry / debt_ratio / annual_revenue / years_established / employee_count / has_mortgage / credit_score / result_label`)
- [ ] **C7 即时回测** · `backtesting.py` `run_backtest()` (v1.0 保留 0 改动) · 100 条数据 + 3 条规则 ≤ 3 秒
- [ ] **C8 指标完整接入 (`metrics.py` 全调用)** · KS 值 / 精确率 / 召回率 / F1 / 混淆矩阵 (TP/FP/TN/FN) / PSI (对比场景) · 输出 `MetricsReport`
- [ ] **C9 6 类图表 (Plotly · `chart_generator.py` 新建)** · 通过/拒绝圆环图 · 规则命中条形图 · KS 曲线 · 混淆矩阵热力图 · 新旧策略对比分组柱状图 · 差错归因堆叠条形图
- [ ] **C10 LLM 分析报告** · 输入 `MetricsReport` + 规则集 + 数据摘要 · 输出 markdown 500-800 字 · 含指标解读 + 策略松紧判断 + 具体优化建议（含数值）
- [ ] **C11 差错诊断** · 50 条 mock 差错案件 (30 误杀 + 20 漏杀) · 逐条回放规则命中过程 · 标记每条差错被哪条规则误判 · 阈值敏感性分析
- [ ] **C12 LLM 优化建议** · `SYSTEM_ERROR_ANALYSIS` · 输出诊断报告 + 优化后的 `RuleSet` JSON (可执行 · 用于 `compare_strategies` 调用)
- [ ] **C13 策略对比** · `compare_strategies(old_rule_set, new_rule_set, data)` (v1.0 保留) · 输出 `ComparisonResult` (delta + improved_metrics + degraded_metrics)
- [ ] **C14 一键应用优化建议** · 修改规则参数立即重测 · 双列对比视图（指标名/旧值/新值/变化量）
- [ ] **C15 PDF 报告导出** · `report_exporter.py` 新建 · 含图表 PNG + LLM 分析文本 · 6 节结构 (摘要 / 规则说明 / 回测结果 / AI 分析 / 附录数据样本)
- [ ] **C16 Wave 2 hardening 接入** · `baseline_ruleset.py` (Stage 8b 新建) · `llm_judge.py` 3 维度 Likert 规则可解释性评判 · `evaluation/manual/agent2_riskctrl.py` adapter (DoD L3 5/10 → 7/10)
- [ ] **C17 SSE 事件流** · 意图分流 → DSL 生成 → 回测执行 → 指标计算 → 图表渲染 → LLM 分析 · 每阶段独立事件 · 流式输出

---

## 3. Input Shape

| 维度 | 形态 |
|---|---|
| **触发源 1** | 风控运营人员在 `/archive/riskctrl` workspace 主动配策略 |
| **触发源 2** | IM `@riskctrl 帮我评估当前小微信用贷策略` |
| **预置场景** | 3 个 · `riskctrl_backtest_01` (小微回测) · `riskctrl_error_01` (差错诊断) · `riskctrl_dsl_01` (自然语言配策略) |
| **CSV 输入** | 100 条 mock 授信 (`demo_data/agent_riskctrl/scenario_backtest/input/credit_data.csv`) · 50 条差错 (`scenario_error/input/error_cases.csv`) |
| **DSL 输入** | 自然语言文本（LLM 解析）· 或直接编辑 JSON |
| **可调参数** | 阈值（field 比较值）· 优先级 priority · action (`reject` / `approve` / `review`) |

---

## 4. Output Shape

### 4.1 UI 渲染 (panel 级 · 见 §7)

- **HeroBanner** · 当前策略名 + 版本 + 数据集摘要
- **DSLEditor** (左上) · 对话输入框 + 预置场景按钮 + DSL JSON 代码块（Monaco 编辑器）· 规则可手动调整
- **MetricsRow** (顶部) · 6 项核心指标卡 (KS / 精确率 / 召回率 / F1 / 通过率 / 拒绝率) · 数值 + 简短解读
- **BacktestPanel** (中间) · 6 类 Plotly 图表网格 · 通过/拒绝圆环图 / 规则命中条形图 / KS 曲线 / 混淆矩阵热力图 / 策略对比 / 差错归因
- **AnalysisPanel** (右侧) · LLM 分析报告 markdown · 流式输出 · 优化建议列表（可一键应用）
- **ComparisonView** · 新旧策略对比 (左旧右新 · 红绿色变化标注)
- **KsAuc** (Wave 2 已挂 · L1-3) · `[data-testid="riskctrl-ks-auc"]` · KS×AUC 双图 · 不许移除
- **ConversationPanel** · IM 风对话气泡

### 4.2 文件导出

| 文件 | 后端端点 | 内容 |
|---|---|---|
| **PDF 回测报告** | `POST /api/riskctrl/export_pdf` (Stage C 新建) | 6 节结构 · reportlab/weasyprint · 含全部图表 PNG + LLM 分析 |
| **RuleSet JSON** | `POST /api/riskctrl/export_ruleset` (Stage C 新建) | 当前 RuleSet 完整 JSON · 供 Agent3/4/5 消费 |

---

## 5. Backend Endpoints

### 5.1 已实装 (api.py v3.1 · session 9 真跑通)

| 方法 | 路径 | 请求 | 响应 |
|---|---|---|---|
| GET | `/api/riskctrl/health` | — | `{status, agent: "agent_riskctrl"}` |
| POST | `/api/riskctrl/dsl_gen` | `{rule_text, provider?, api_key?}` | **SSE** · rule_config 流程事件 + done |
| POST | `/api/riskctrl/backtest` | `{instruction, uploaded_files, provider?, api_key?}` | **SSE** · backtest 流程事件 + done |

### 5.2 Stage C 新建端点

| 方法 | 路径 | 请求 | 响应 | 备注 |
|---|---|---|---|---|
| GET | `/api/riskctrl/scenarios` | — | `{scenarios: [{key, name, desc, rule_count, sample_count}]}` | 列预置 3 场景 |
| POST | `/api/riskctrl/run` | `{scenario_key, mode: "backtest"\|"diagnose"\|"dsl_gen"}` | **SSE** · 统一入口 | 替代分散的 dsl_gen / backtest 端点（保留兼容）|
| POST | `/api/riskctrl/error_analysis` | `{instruction, uploaded_files (差错 CSV)}` | **SSE** · error_analysis 流程 | 差错诊断 (PRD §3.2) |
| POST | `/api/riskctrl/compare` | `{old_ruleset, new_ruleset, dataset_path}` | `{comparison_result}` (`ComparisonResult` JSON) | 同步调 v1.0 `compare_strategies()` |
| POST | `/api/riskctrl/export_pdf` | `{session_id, ruleset, metrics}` | pdf file (`Content-Disposition`) | PDF 回测报告 |
| POST | `/api/riskctrl/export_ruleset` | `{ruleset}` | json file | RuleSet JSON 导出（供 Agent3/4/5）|
| GET | `/api/riskctrl/baseline/{ruleset_id}` | path | `BaselineRuleset` JSON | Wave 2 8b 新增 (DoD L3 fix) |
| POST | `/api/riskctrl/llm_judge` | `{ruleset, dimension: "interpretability"\|"coverage"\|"sensitivity"}` | `{score: 1-5 Likert, reasons: [...]}` | Wave 2 8b 新增 |

### 5.3 SSE 事件契约

```jsonc
// event: stage (rule_config 流程)
{"event": "stage", "payload": {"phase": "intent_detection", "intent": "strategy_config", "confidence": 0.95}}
{"event": "stage", "payload": {"phase": "dsl_generation", "rule": {...}, "operator": ">", "value": 0.8}}

// event: stage (backtest 流程)
{"event": "stage", "payload": {"phase": "data_loaded", "rows": 100, "fields": 11}}
{"event": "stage", "payload": {"phase": "rule_applied", "rule_id": "R001", "hits": 23}}
{"event": "stage", "payload": {"phase": "metrics_computed", "metrics": {"ks": 0.42, "precision": 0.83, "recall": 0.76, "f1": 0.79, "confusion_matrix": {"TP": 19, "FP": 4, "TN": 70, "FN": 7}}}}

// event: stage (error_analysis 流程)
{"event": "stage", "payload": {"phase": "error_attribution", "rule_id": "R001", "false_positive": 18, "false_negative": 2}}

// event: chart (流式推 6 类图表生成)
{"event": "chart", "payload": {"chart_type": "ks_curve", "plotly_json": {...}}}

// event: analysis (LLM 流式输出 markdown)
{"event": "analysis", "payload": {"chunk": "策略整体精确率 83.2%..."}}

// event: done
{
  "event": "done",
  "payload": {
    "session_id": "...",
    "ruleset": {"name": "...", "version": "...", "rules": [...]},
    "metrics": MetricsReport,
    "charts": {"approval_rejection_donut": "...", "rule_hit_distribution": "...", "ks_curve": "...", "confusion_matrix": "...", "error_attribution": "..."},
    "analysis": "...",
    "optimization_suggestion": {"new_ruleset": {...}, "expected_delta": {...}}
  }
}
```

### 5.4 降级路径

- **DeepSeek 缺 key (api_key="dummy")** → DSL 生成阶段 yield error · 前端走预置 RuleSet (`/public/mock/riskctrl_ruleset.json` · 113 行 v1.0-readonly-mock) · 回测/指标走确定性
- **CSV 解析失败** → Toast 提示具体编码问题 · 不阻断 · 走预置数据
- **后端整体未挂 (Phase 1 时段)** → 前端纯走 `/public/mock/riskctrl_ruleset.json` · ReadOnly mode · 不调后端

---

## 6. Mock Sessions Structure (≥3)

### 6.1 Top-level shape

```typescript
type RiskctrlMockSession = {
  session_id: string;
  scenario_key: string;
  display_name: string;
  mode: "backtest" | "diagnose" | "dsl_gen";
  ruleset: RuleSet;
  metrics?: MetricsReport;
  charts?: ChartCollection;
  analysis?: string;
  optimization_suggestion?: { new_ruleset: RuleSet; expected_delta: Record<string, number> };
};
```

### 6.2 三个标杆 session

| session_id | scenario | mode | 演示卖点 |
|---|---|---|---|
| `riskctrl-backtest-001` | riskctrl_backtest_01 | backtest | 100 条小微贷 + 3 条规则 → KS 0.42 / 精确率 83% / 召回率 76% · 圆环图 + 命中分布 + KS 曲线 |
| `riskctrl-error-002` | riskctrl_error_01 | diagnose | 50 条差错 (30 误杀+20 漏杀) → 归因表 R001 贡献 18 误杀 → LLM 建议阈值 70%→75% → 对比新策略减 12 误杀增 2 漏杀 |
| `riskctrl-dsl-003` | riskctrl_dsl_01 | dsl_gen | "拒绝负债率>80%" → DSL → 即时回测 → 多轮追加 "成立不满 1 年的也拒绝" → 完整 RuleSet 3 条 |

### 6.3 数据契约

```typescript
type RuleCondition = {
  field: string;                  // "debt_ratio"
  operator: ">" | "<" | ">=" | "<=" | "==" | "!=" | "in" | "not_in";
  value: any;
};

type StrategyRule = {
  name: string;                   // "高负债率拒绝"
  conditions: RuleCondition[];    // AND 关系
  action: "reject" | "approve" | "review";
  priority: number;               // 数值越小优先级越高 · 命中即停
};

type RuleSet = {
  name: string;
  version: string;
  description: string;
  rules: StrategyRule[];          // 按 priority 排序
};

type MetricsReport = {
  total_samples: number;
  pass_count: number;
  reject_count: number;
  pass_rate: number;
  reject_rate: number;
  rule_hits: Record<string, number>;
  ks_value: number;
  precision: number;
  recall: number;
  f1_score: number;
  confusion_matrix: { TP: number; FP: number; TN: number; FN: number };
  psi_value?: number;             // 仅对比场景
};

type ComparisonResult = {
  old_metrics: MetricsReport;
  new_metrics: MetricsReport;
  delta: Record<string, number>;  // {pass_rate: +0.05, precision: -0.02}
  improved_metrics: string[];
  degraded_metrics: string[];
};
```

---

## 7. Panel Architecture (`/archive/riskctrl/_components/`)

| Panel 组件 | 数据源 (props) | 切 session 重渲 | 模式联动 |
|---|---|---|---|
| `RiskctrlHero.tsx` | ruleset name + version + dataset summary | ✓ | ✓ |
| `DSLEditor.tsx` | ruleset (Monaco editor) + onChange | ✓ | ✓ |
| `MetricsRow.tsx` | metrics (6 卡) | ✓ | — |
| `BacktestPanel.tsx` | charts (6 类) | ✓ | — |
| `AnalysisPanel.tsx` | analysis markdown + optimization_suggestion | ✓ | — |
| `ComparisonView.tsx` | old + new metrics + delta | — | (diagnose 模式) |
| `KsAucPanel.tsx` (Wave 2 · 不许移除) | ks_curve + auc_value | ✓ | — |
| `ScenarioPicker.tsx` | 3 个场景按钮 | — | ✓ |
| `ConversationPanel.tsx` | thread | — | — |

### 7.1 Panel state hoist

```typescript
const [selectedSessionId, setSelectedSessionId] = useState(MOCK_SESSIONS[0].session_id);
const [mode, setMode] = useState<"backtest" | "diagnose" | "dsl_gen">("backtest");
const [ruleset, setRuleset] = useState<RuleSet>(MOCK_SESSIONS[0].ruleset);
const [livePayload, setLivePayload] = useState<RiskctrlPayload | null>(null);
const [comparison, setComparison] = useState<ComparisonResult | null>(null);
const [dataSourceMode, setDataSourceMode] = useState<"mock" | "live">("mock");
```

### 7.2 路由 + 红线

- ✅ 唯一入口 `/archive/riskctrl`
- ❌ 禁顶层 `/riskctrl` (legacy)
- 三 mode 切换走 query `?mode=backtest`（不是新路由）

---

## 8. Regression Risks

| ID | Feature | Selector | 验证 spec |
|---|---|---|---|
| F-ks-auc | KsAuc (Wave 2 · L1-3) | `[data-testid="riskctrl-ks-auc"]` | `web/tests/riskctrl-ks-auc.spec.ts` |
| F-evidence-trail | EvidenceTrail (Wave 2) | `[data-testid="evidence-trail"]` | `web/tests/evidence-trail.spec.ts` |

**v1.0 资产 PRESERVE (PRD §5.1 · 0 改动)**：
- `agent.py` (意图检测分流)
- `rule_engine.py` (RuleCondition / StrategyRule / RuleSet 三层模型 · 8 操作符 · 命中即停)
- `backtesting.py` (CSV/Excel 多编码自动检测 · 数据摘要 · 回测执行 · `compare_strategies()`)
- `metrics.py` (KS / PSI / 混淆矩阵 / 精确率 / 召回率 / F1)
- `prompts.py` (SYSTEM_RULE_PARSER + SYSTEM_BACKTEST_ANALYSIS + SYSTEM_ERROR_ANALYSIS)

**Wave 2 8b 新增 (PRESERVES)**：
- `agent_riskctrl/baseline_ruleset.py` (Wave 2 8b · DoD L3 fix)
- `agent_riskctrl/llm_judge.py` (Wave 2 8b · 3 维度 Likert · Q-038 决策留原位 不抽 shared/)
- `agent_riskctrl/backtesting.py` 追加 22 行 (KS sidecar dual-path · DoD L3 fix)
- `agent_riskctrl/output_validator.py` (placeholder guard soft_clean)
- `evaluation/manual/agent2_riskctrl.py` (adapter)
- `MAX_ROWS=50000` (Q-040 fix · 不可改回 500)

**红区禁触**：
- `shared/base_agent.py` 改签名 → RFC
- `agent_riskctrl/rule_engine.py` schema 改动 → RFC（Agent3/4/5 都消费 RuleSet JSON）
- `agent_riskctrl/metrics.py` 算法核心 → RFC

---

## 9. LLM 调用预算 (PRD §7)

| 调用点 | 频次 | 模型 | Temp |
|---|---|---|---|
| **意图检测** | 1/输入 (预置场景跳过) | DeepSeek-chat | 0.3 |
| **DSL 生成** | 1/规则 (多轮追加 N 条 = N 次) | DeepSeek-chat | 0.3 |
| **回测分析报告** | 1/session | DeepSeek-chat | 0.5 (流式) |
| **差错诊断 + 优化建议** | 1/session | DeepSeek-chat | 0.5 (流式) |
| **LLM Judge (Wave 2 8b)** | 1/dimension × 3 = 3 次 | DeepSeek-chat | 0.2 |

**Demo 总预算**：单场景 ≤ 5 次 LLM (含 LLM Judge 3 次)

**性能 SLA (PRD §10.2)**：
- 100 条 + 3 规则回测 ≤ 3 秒
- 6 类图表渲染 ≤ 2 秒
- LLM 首 token ≤ 2 秒 / 完整 ≤ 8 秒
- PDF 生成 ≤ 5 秒

---

## 10. Acceptance for Stage C

- [ ] 17 个 capability (§2 C1-C17) 全 ✓
- [ ] 8 个新端点 (§5.2) 真跑通
- [ ] 9 个 panel (§7) 全 props 化 · 三模式切换无状态污染
- [ ] 3 个 mock session (§6) 落 `web/lib/mock-sessions.ts`
- [ ] 5 个 Playwright smoke pass (riskctrl-mock-switch / riskctrl-backtest-flow / riskctrl-dsl-gen / riskctrl-error-diagnose / riskctrl-export-pdf)
- [ ] features-inventory.md F-ks-auc / F-riskctrl-* entries
- [ ] commit trailer 必含 `PRESERVES: F-ks-auc, F-evidence-trail` + Wave 2 8b 文件 (baseline_ruleset.py / llm_judge.py / backtesting.py +22 / output_validator.py)
- [ ] tsc --noEmit 0 error · ECS deploy verify 通

---

## 11. References

- 上游 PRD: `docs/PRD_风控策略运营助手_v1.0.md`
- API map: `docs/contracts/shell-v1-agent-api-map.md` § Agent 2
- 字段命名: `docs/contracts/field-naming.md`
- 共享变更协议: `docs/contracts/shared-change-protocol.md`
- Master plan: `docs/contracts/master-execution-plan-2026-04-27.md` § Stage C.5
- Q-038 (CA-B3-8 llm_judge.py 留原位 · CA-B3-12 ruff 跳): `docs/handoff/decisions-log.md` Q-038
- Q-040 (MAX_ROWS=500→50000 fix · Wave 5 mock-realism-upgrade 立项): `docs/handoff/decisions-log.md` Q-040
- Wave 2 8b onboarding: `docs/onboarding/batch-3-code-arch-agent2-hardening.md`
- ReadOnly mock: `web/public/mock/riskctrl_ruleset.json` (113 行 v1.0-readonly-mock · 5 条 rule × 完整 backtest 字段)
- Workspace state: `docs/contracts/workspace-state-protocol.md` v1.1 (Phase A worker-A1 ratified · 4 useState gate + AgentSession shape 见 §10)
