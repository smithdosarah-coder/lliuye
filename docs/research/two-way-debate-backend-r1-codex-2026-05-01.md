# 主 CLI + Codex 后端方案辩论 R1 · Codex 独立 (全扫 6 Agent backend audit)

> Codex high reasoning · sandbox read-only · 主 CLI 落盘代写 · 任务 ID b6b152s2w
> 2026-05-01 · 全扫 6 个 agent_*/ ~175 个 .py 文件 · file:line evidence

## 1. Backend Inventory (175 .py)

关键 API 行数: Agent1 599 / Agent3 811 / Agent4 559 / Agent5 438 / Agent6 1074 / Agent2 569
关键核心: realtime_stream.py 1105 / decision_engine.py 114 / scan_engine.py 318/610 / v16_runner.py 482 / backtesting.py 274

- **Agent1 渠道获客**: `/api/channel/run` SSE · mock 强制 demo · 真搜依赖 Tavily 缺 key 直接错而非静默 mock (`agent_channel/api.py:121, 134`) · 产品推荐是规则 + scoring · LLM 只生成话术失败模板兜底 (`agent_channel/product_recommender.py:2, 5, 108`) · demo 走 21 scenario fixture (`agent_channel/api.py:197`)
- **Agent3 授信决策**: `/api/credit/decision` SSE · mock 不调 LLM · decision cache 仅 in-memory 30 分钟 注释写生产应 sqlite (`agent_credit/api.py:6, 14, 110`) · 前 4 步确定性 + 最后 AdvisorFormatter 调 LLM 包装自然语言 (`agent_credit/decision_engine.py:7, 11`) · 企业评分加权阈值 + 零售 FICO 式评分卡 (`scoring_model_corporate.py:5, scoring_model_retail.py:2`)
- **Agent4 贷中预警**: `/api/alert/scan` SSE 持久化 hitlist · demo fixture 不读 KB 不调 LLM (`agent_alert/api.py:5, 6, 392, 439`) · 规则固定 ALERT_RULES 阈值 · Tavily 默认关闭或缺 key 回 mock (`alert_engine.py:46, scan_engine.py:48, 60`) · drill 处置 LLM 优先模板兜底 (`scan_engine.py:184, 219`)
- **Agent5 合规巡检**: `/api/compliance/policy_scan` 政策文本+业务文档 → 抽规则/抽事件/矩阵比对/修订意见持久化 (`api.py:5, scan_engine.py:7, 644`) · 规则抽取 LLM 优先失败启发式 · 单格判定先 hard rule 再 LLM 再 N/A (`scan_engine.py:217, 239, 424`) · demo 21 fixture
- **Agent6 报告生成**: `/api/report/v16/fill` classifier→generator→QC · `/demo/run` 纯 mock SSE · `/upload`+`/refine_section` 已有 (`agent_report/api.py:5, 6, 7, 9`) · 无 classified_json 或无 DeepSeek key 自动 mock (`v16_runner.py:15, 475, 485`) · 真路径含 LLM 改写 + QC 9 维 (`v16_runner.py:299, 13`)
- **Agent2 风控策略**: `/api/riskctrl/dsl_gen` 自然语言→RuleSet JSON · `/backtest` RuleSet+CSV→KS/通过率/坏账率 · mock 预设 RuleSet 不调 LLM (`api.py:5, 6, 12, 168`) · DSL 解析 RuleSet 后确定性 apply · 回测支持 label 自动探测 + per-rule FPR (`rule_engine.py:97, 192, backtesting.py:175, 230`)

**Mock 形态**: 6 个工作台均有 `data/mock/workspace/<agent>/scenarios/*.json` · 共 21 个 scenario · Stage 5a smoke 已验证 6 SSE 真流 · 但 production 仍大量依赖 key/fixture/in-memory/启发式 fallback。

## 2. 4 角色痛点对照

- **RM 客户经理**: Agent1 能找候选 · 但偏"企业 look-alike + 产品话术" · 缺个人客户运营的存量画像/需求预测/任务拆解 · Agent6 真路径缺材料/分类产物就 mock · RM 不知道哪些数据缺口影响结论 (`v16_runner.py:485`)
- **审贷员**: Agent3 评分主体是确定性评分卡 + 红线 · 方向对 · **痛点不是"加 ML"** · 而是 evidence 链和可复核性 · 当前 LLM 只包装理由 · decision cache 还只是 demo 级 in-memory (`decision_engine.py:11, api.py:110`)
- **合规官**: Agent5 已做政策→规则→业务事件→矩阵 · 但政策 KB 实时性依赖 inline 输入或 fallback 搜索 · 冲突检测 hard threshold + LLM/N/A 缺政策版本/引用来源/冲突解释闭环 (`scan_engine.py:424`)
- **风险经理**: Agent2 DSL 能跑 · 但 DSL 主要由 LLM 生成做结构校验 · 回测已从 500 升至 50000 量级 · 仍缺策略上线前的字段血缘/样本窗口/冠军挑战者对照/误杀解释 (`backtesting.py:22, 24, 278`) · Agent4 默认 Tavily 关闭/缺 key 回 mock 线上信号可信度不足 (`scan_engine.py:48`)

## 3. 真痛 → 后端 Deep Work (8 项)

1. **P0 RM 客户结果可信度** — Agent1 增加候选证据聚合 + 数据源状态评分 · 现 run 依赖 Tavily 或 mock (`api.py:134, 197`) · 改为每候选输出来源/时间/命中字段/可联系性/缺口 · **1.5 周**
2. **P0 审贷员 evidence 链** — Agent3 将评分/红线/案例/LLM 理由统一成可追溯 decision graph · 现前 4 步确定性 + 最后 LLM 包装 (`decision_engine.py:95, advisor_formatter.py:205`) · 改为每结论挂 feature snapshot/rule hit/阈值/来源段落/版本 · **2 周**
3. **P0 Agent6 缺材料闭环** — pending_questions 已有 · 但 RM/审贷员缺"缺哪份材料会影响哪章/哪项评分" · 现 pending 只随 v16 summary 出 (`v16_runner.py:342, 377`) · 改为 material gap graph + section impact + handoff Agent3 · **1.5 周**
4. **P0 合规政策版本链** — Agent5 给每条规则加政策版本/来源 URL/有效期/替代关系 · 现 inline policy_meta 可选但非强约束 (`api.py:106, scan_engine.py:708`) · 改为 policy registry + rule version diff · **2 周**
5. **P1 矩阵冲突解释** — Agent5 单格 hard/LLM/N/A 不够让合规官签字 (`scan_engine.py:424`) · 改为 violation reason schema (冲突字段/业务原文/条款原文/置信度/需人工复核原因) · **1 周**
6. **P1 风控 DSL 可上线性** — Agent2 DSL 解析后直接 apply (`rule_engine.py:97, 192`) · 增加字段字典校验/单位归一/样本覆盖率/规则互斥/遮蔽检查 · **1.5 周**
7. **P1 回测可信度** — Agent2 已有 label 和 per-rule FPR · 缺窗口/基线/稳定性报告 (`backtesting.py:175, 230, 278`) · 加 champion/challenger/PSI/分月指标/误杀样本解释 · **2 周**
8. **P1 预警线上信号质量** — Agent4 缺 key 回 mock 会伤风险经理信任 (`scan_engine.py:48, 60`) · 增加 external signal freshness/source confidence/fallback banner 入库/scan replay · **1 周**

## 4. 个人画像 POC 放哪

现 6 Agent **最贴的是 Agent1 · 不是 Agent3**:
- Agent1 已有产品推荐 + 产品目录 + 批量话术 + Top3 推荐 + pitch (`product_recommender.py:2, 25, 108, sse_extras.py:540, 592`)
- Agent3 是授信决策 · 虽有 retail FICO · 但核心是批准/拒绝/额度 · 不是 toC 经营运营 (`scoring_model_retail.py:2, advisor_formatter.py:141`)

**推荐**: 不要塞 Agent3 · 优先在 Agent1 下新增 `personal_insight` 子域 · 必要时前端命名 Agent7。

工程量:
- Agent1 增量约 **2.5 周** (画像标签 / 产品适配 / 合规红线 / 触达话术 / PII 脱敏 / latency / 抗幻觉)
- 新建 Agent7 约 **4 周以上** · 还要重复 SSE / mock / 导出 / 审计 / 权限

跨 Agent 拼接 (POC 最终加分): Agent1 画像/推荐/话术 + Agent5 产品合规校验 + Agent4 触达后预警 · 但 orchestrator 不应先做成重平台。

## 5. Codex R1 Verdict

后端真痛不是"缺 ML" · 而是**四角色不敢信**:
- RM 缺候选/材料缺口闭环
- 审贷员缺可复核 evidence graph
- 合规官缺政策版本链与冲突解释
- 风险经理缺 DSL 上线校验/稳定回测/预警信号质量

建议 P0 三项: Agent1 候选证据评分 + Agent3 decision graph + Agent6 material gap graph
P1 五项: 进 Phase C

个人画像 POC 放 Agent1 子域 + 联 Agent5 合规 + 不建纯 Agent7。总工程量约 **12.5 周** · POC 最小闭环 **2.5 周**。
