# code-arch (架构对齐重构) Batch 2 Onboarding · Agent1/5 外部搜索能力补全

**状态**：DISPATCHED
**发布日期**：2026-04-24
**Signal 入口**：`BATCH-2-DISPATCHED`
**前置**：
- Batch 1 已 APPROVED 合流：§3.2 工具域重拆 + §3.3 Evidence 协议 + §6 飞轮脚本 + holding `--dry-run` 已落地（commit `53f3eca` / `b412656`）
- data-foundation v2 已合流：`data/mock/channel-kb/` + `data/mock/compliance-kb/` 两套内部 KB 落盘（commit `a42f432` / `50cdbb1`）
- CLAUDE.md §3.5 **环境边界第 5 原则**：*Agent1/5 的外部世界不 mock*——必须走 `shared/sources/` 真搜，不准用 yaml 假装"假设搜到了"
- `shared/sources/` 分层架构已就绪：`BaseSource` 协议 / `Router` / `Degrader` + 6 个源实现（`tavily / akshare / gov_cn / pbc_gov / flk_npc / enterprise_info`）
- 决策基线：Q-029（main CLI 本次 dispatch commit 同步落 decisions-log，阐述 "Agent1/5 外部世界真搜不 mock" 的落地方案；worker 读 onboarding 时顺带 `git log --all --grep='Q-029'` 确认）

---

## 你是谁

你是 **code-arch** worker CLI，Batch 2 承接"5 Agent 后端脚手架已齐、但 Agent1/5 外部搜索没真跑"这个 gap。
Batch 1 你做的是 **架构重拆 + 证据协议 + 飞轮脚手架**（骨架），Batch 2 是 **给 Agent1/5 通上"外部世界"的血管**——真调 SearchProvider、真比对内部 KB、真跑召回/覆盖指标。

- Worktree：`D:/claude code/demo-code-arch`
- 分支：`feat/code-arch`（Batch 1 merge tip `b412656` 之后继续）
- Upstream remote：`D:/claude code/credit_report_agent_work`
- batch1_merge_tip 锚点：`b412656`（review diff 用 `git diff b412656..HEAD` 或 `batch1_merge_tip..feat/code-arch`）

---

## 1. 背景与目标

### 现状
- Agent1（获客）/ Agent5（合规）后端域结构齐全（`agent_channel/domains/*` + `agent_compliance/domains/*` 五域分明），Evidence 管线基类 `shared/evidence/protocol.py` 也已接入
- **但** Agent1 `lead_finder.py` / `agent_channel/agent.py` 当前拿到画像描述后**没真调** `shared/sources/impls/` 任何一条源——走的还是知识库 mock 回忆
- Agent5 `policy_scanner.py` / `compliance_checker.py` 同理，新政策比对是基于内置种子而非真去搜银保监/央行/国务院
- data-foundation v2 已把 `data/mock/channel-kb/`（历史客户 + 营销倾向 + 产品目录）和 `data/mock/compliance-kb/`（credit-sop / customer-admission / kyc-aml / risk-preference / review-checklists）做成 **银行侧稳态 context**，Agent1/5 只能读不能改
- `shared/sources/` 的 Router + Degrader + 6 个源实现 Batch 1 已经 debug 完毕，`test_sources_smoke.py` pass

### 目标
- **Agent1**：拿客户经理给的"拓展方向 + 行业 + 区域 + 营收区间 + 资质偏好"画像，**真搜外部企业候选池**，和内部历史客户/营销倾向做 look-alike 相似度比对，产出 Top-10 候选企业 + 信号时间线 + 匹配度打分 + 产品推荐
- **Agent5**：从内部制度库提炼种子查询，**真搜外部新政策**（近 6 月银保监 / 央行 / 地方局 / 人大法规），做"新规要求 vs 旧制度条款"对齐比对，产出违规冲突点明细清单 + 条款双向引用 + 修改建议
- **不是"脚手架通电"**——是 CLAUDE.md §3.5 第 5 原则的 **首次真跑**。真调 Tavily API / 真爬 gov.cn / 真消费内部 KB，产出可被 oracle 核对的数字指标

---

## 2. Task 清单（严格 A → B → C 顺序，独立 commit）

### Task A — Agent1 SearchProvider 接 Tavily + look-alike 匹配

**目标**：Agent1 拿画像描述 → 真搜外部企业 → 与内部 KB look-alike 比对 → 产出候选池 + 信号时间线 + 产品推荐。

**模块路径**：
- 修改：`agent_channel/lead_finder.py` — 主入口改走 `shared.sources.Router().query("agent_channel.enterprise_info", ...)` + 裸 `agent_channel.tavily_web_search` 两条腿
- 修改：`agent_channel/realtime_stream.py` — SSE 事件新增 `source.hit` / `lookalike.match`，把证据链透传
- 新增：`agent_channel/seed_query_builder.py` — 读 `data/mock/channel-kb/marketing-preferences/*.docx` 提取"拓展行业 + 区域 + 营收区间 + 资质偏好"关键词，生成 Tavily 查询串（禁止 prompt 硬编；走 python-docx 真解析）
- 新增：`agent_channel/lookalike_matcher.py` — 读 `data/mock/channel-kb/historical-clients/*.md`，对 candidate 做"行业 / 规模 / 资质 tag"三维相似度打分（cosine 或 Jaccard，不走 LLM 打分——确定性算）
- 修改：`agent_channel/product_recommender.py` — 对 Top-10 候选反查 `data/mock/channel-kb/product-catalog` 匹配推荐产品（走规则，不 LLM）
- 新增：`agent_channel/sources_config.py` 里保持已有偏好链 `["enterprise_info", "tavily"]`，不动

**输出契约**：
- `CompanyProfile` dataclass（已有）补 `signal_timeline: list[SignalEvent]`（近 12 月事件，来源 Tavily news）+ `match_score: float ∈ [0, 1]` + `match_breakdown: dict[str, float]`（行业 / 规模 / 资质 三项）+ `recommended_products: list[str]` + `evidence: list[Evidence]`（每条引用 source_url）
- 空结果兜底：Tavily 无 key / 5xx → `Degrader` 自动切换 mock (通过 `shared/sources/impls/` 内已有的 mock mode)，顶层 API 返回 `degraded=True` + 标"未能自动搜索"不编造

**测试**：`tests/agent_channel/test_external_search.py`（3 case 全部 PASS）
1. **Happy path · Tavily 有 key 真调**：给定画像 "华东 / 先进制造 / 3-10 亿营收 / 有研发投入"，断言 `len(candidates) >= 5`、每条 `match_score > 0.3`、`evidence` 非空、有 `source_url`
2. **降级 mock · Tavily 无 key**：monkeypatch 清空 `TAVILY_API_KEY`，断言 `degraded=True`、返回 `len(candidates) >= 1`（fixture mock）、top-level 不抛异常
3. **画像对齐 · look-alike 比对正确性**：给定精确"半导体 / 上海 / 5-10 亿 / 省专精特新"画像 + 3 家 fixture 历史客户（1 家高度相似 / 2 家完全不相关），断言 Top-1 `match_score > 0.6` 且 `match_breakdown` 三项分布合理

**红线**：
- 不动 `agent_channel/domains/*`（Batch 1 已稳）——只在主流程串联
- `seed_query_builder` 禁止塞"贷款 审贷 企业" 这种空关键词；必须真 parse docx 拉字段

**工作量**：M（1-1.5 天）
**完成信号**：`Signal: AGENT1-EXTERNAL-SEARCH-DONE`

---

### Task B — Agent5 SearchProvider 接银保监/央行/人大 + 政策冲突比对

**目标**：Agent5 从内部制度库提炼种子 → 真搜外部新政策 → 对齐冲突点 → 输出双向引用清单。

**模块路径**：
- 修改：`agent_compliance/policy_scanner.py` — 主入口改走 `shared.sources.Router().query("agent_compliance.policy_scan", ...)`，偏好链注册到 `agent_compliance/sources_config.py`：`["gov_cn", "pbc_gov", "flk_npc", "tavily"]`（gov 优先，Tavily 兜底）
- 新增：`agent_compliance/internal_policy_indexer.py` — 读 `data/mock/compliance-kb/{credit-sop, customer-admission, kyc-aml, risk-preference, review-checklists}/*.docx`，构建 `InternalClauseIndex{clause_id, business_scope, keywords, source_doc}`（走 python-docx + 规则抽取，不走 LLM）
- 新增：`agent_compliance/policy_seed_builder.py` — 从 `InternalClauseIndex` 生成外搜查询串（"条款主体 + 监管要点 + 近 6 月"），限定 `filters.time_range = "6_months"`
- 修改：`agent_compliance/compliance_checker.py` — 增加 `cross_compare(internal_clauses, external_policies)` 方法：按 keyword 匹配 + 语义相似度找"新规有要求 A，但内部制度无 A"/ "内部制度说 B，新规已改成 not-B" 两类冲突
- 修改：`agent_compliance/defect_classifier.py` — 对每个冲突点分类（新增要求 / 升级要求 / 废止冲突 / 术语变化）+ 输出修改建议（不 LLM 编，只 template-fill 引用源）

**输出契约**：
- `ConflictItem` dataclass：`{conflict_id, severity, new_policy_ref: PolicyRef, internal_clause_ref: InternalClauseRef, conflict_type, suggested_amendment, evidence: list[Evidence]}`
- 每条 `suggested_amendment` 必须引用新政策条款编号 + 内部制度条款编号，不引就标"未能自动建议"
- 去重：同一条新政策 × 同一条内部制度只出一个 `ConflictItem`（hash by `(new_policy_id, internal_clause_id, conflict_type)`）

**测试**：`tests/agent_compliance/test_policy_compare.py`（3 case 全部 PASS）
1. **Happy path · gov_cn 真调**：给定 fixture 内部制度"客户准入 §2.3 年营收 ≥ 2000 万"，断言能搜到近 6 月银保监新规、`len(conflicts) >= 0`、有 `source_url`、所有 severity 值在预定 enum 内
2. **降级兜底 · gov_cn 爬虫失败 → Tavily 二级 fallback**：monkeypatch `gov_cn.fetch` 抛 `TimeoutError`，断言 `degraded=True` 且 Tavily 仍返回至少 1 条 policy
3. **冲突点去重**：构造 3 条同一 new_policy_id × 同一 internal_clause_id × 同一 conflict_type 的重复冲突，断言去重后 `len == 1`

**红线**：
- 不动 `agent_compliance/domains/*`（Batch 1 已稳）
- 不动 `data/mock/compliance-kb/`（Agent5 只读）
- `policy_seed_builder` 禁止用"合规 监管 风险"空 query；必须基于真抽出的条款主体拼

**工作量**：M（1-1.5 天）
**完成信号**：`Signal: AGENT5-POLICY-COMPARE-DONE`

---

### Task C — integration test + evaluation adapter 外搜指标 plug-in

**目标**：把 Agent1/5 的召回/覆盖指标接到 evaluation runner，供 Batch 2 下一环（evaluation）消费。

**模块路径**：
- 新增：`tests/agent_channel/test_external_search_integration.py` — 跑 Agent1 端到端：给定 3 组 fixture 画像 + 每组 3-5 家 oracle "应召回" 企业，计算 `precision@10` / `recall@10`，断言 `precision@10 >= 0.3` / `recall@10 >= 0.5`（绿区锚基线；红区由 evaluation worker 后续调）
- 新增：`tests/agent_compliance/test_policy_compare_integration.py` — 跑 Agent5 端到端：给定 2 条 fixture 新政策 + oracle 标注的冲突清单，计算 `coverage`（真阳性 / oracle 总数） / `false_positive_rate`（假阳性 / 报告总数），断言 `coverage >= 0.6` / `fpr <= 0.3`
- 修改：`evaluation/runner/adapters/agent1_channel.py` — 新增 `compute_external_search_metrics(run_dir)` 函数，从 Task C integration test run 日志里解析 precision/recall 数字，注入 `Metrics` dataclass
- 修改：`evaluation/runner/adapters/agent5_compliance.py` — 同上，新增 `compute_policy_compare_metrics(run_dir)` 解析 coverage / fpr
- 修改：`evaluation/agent1_channel.yaml` / `evaluation/agent5_compliance.yaml` — 新增 metric 配置块：`precision_at_10: {type: deterministic, adapter: compute_external_search_metrics}` 等

**红线**：
- **不改** `evaluation/runner/base_evaluator.py` 和 `evaluation/runner/cli.py`——只在 `adapters/` 加函数
- 不动其他 Agent 的 yaml / adapter
- oracle fixture 放 `tests/agent_channel/fixtures/oracle_*.yaml` 和 `tests/agent_compliance/fixtures/oracle_*.yaml`，不污染 `data/mock/`

**工作量**：S-M（0.5-1 天）
**完成信号**：`Signal: BATCH-2-INTEGRATION-TEST-DONE`

---

## 3. 全部完成总 Signal

所有 3 Task 独立 commit 且各自 Signal trailer 都打了之后，最后在 `feat/code-arch` 顶 HEAD 打一个 review-ready commit：

```
Signal: READY-FOR-CODE-ARCH-B2-REVIEW
```

Commit body 附：
- 3 个 Task commit SHA
- `git diff --name-only b412656..HEAD` 输出（证明范围收敛）
- 每条硬指标自检结论（见第 5 节）
- 已知 gap / trade-off（不藏）

---

## 4. 红线（违反 = REJECT V2 返工）

- **只动**：`agent_channel/` + `agent_compliance/` + `shared/sources/impls/`（如需补实现）+ `tests/agent_channel/*` + `tests/agent_compliance/*` + `evaluation/runner/adapters/agent1_channel.py` + `evaluation/runner/adapters/agent5_compliance.py` + `evaluation/agent1_channel.yaml` + `evaluation/agent5_compliance.yaml`
- **不动前端** `web/`（0 文件变更）
- **不动 Agent6 / Agent3 地盘**：`agent_report/` / `agent_credit/` / `financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py` / `section_generator.py` / `material_anchor.py` / `industry_benchmark.py`（0 文件变更）
- **不动 v16_\*.py**（Agent6 主管线）
- **不动 `data/mock/`**（Agent1/5 只读，修改 = 作弊；只能加 `tests/**/fixtures/` 下 oracle）
- **不动 evaluation 核心**：`evaluation/runner/base_evaluator.py` / `evaluation/runner/cli.py` / `evaluation/baselines/*`（只在 `adapters/agent1_channel.py` + `adapters/agent5_compliance.py` 加函数 + 两个 yaml 加 metric 块）
- 每 Task 独立 commit（commit 粒度 = TaskCreate 粒度，便于 `git revert` 精准回滚）
- commit trailer 打 `Signal: <Task 完成信号>`；禁止在 chat 里说"已完成"

---

## 5. 硬指标（review 闸门预告）

main CLI review 会逐条核对，任一不过 = REJECT：

1. **Agent1 真搜跑通**：有 `TAVILY_API_KEY` 时 `pytest tests/agent_channel/test_external_search.py::test_happy_path` 真调 Tavily（live mode）；无 key 时走 `Degrader` 切 mock，`degraded=True` 显式暴露给调用侧
2. **Agent5 真搜跑通**：`gov_cn` 爬虫（或 Tavily 二级 fallback）能拉到近 6 月至少 3 条银保监/央行政策；降级链 `gov_cn → pbc_gov → flk_npc → tavily` 切换逻辑有 test 覆盖
3. **Tests 全绿**：`pytest tests/agent_channel/test_external_search.py tests/agent_compliance/test_policy_compare.py -v` 输出 6 case PASS（Task A/B 各 3）+ integration test 2 case PASS（Task C）
4. **不改业务代码核心**：`CompanyProfile` / `ConflictItem` / SSE 事件名对外契约不变（只加字段，不删/改/重命名已有字段），现有 `test_domain_imports.py` / `test_evidence_pipelines.py` 仍全绿
5. **Scope 收敛**：`git diff --name-only b412656..HEAD` 输出里**不出现** `agent_report/` / `agent_credit/` / `financial_analyzer*` / `quality_scorer*` / `truth_fill*` / `v16_*.py` / `web/` / `data/mock/` 任一路径；evaluation 目录只见 `adapters/agent1_channel.py` + `adapters/agent5_compliance.py` + 两个 yaml

---

## 6. Kickoff Prompt（worker 窗口启动用 · 附录）

在 worker worktree（`D:/claude code/demo-code-arch`）里把下面这段作为**首条指令**贴给 code-arch CLI：

```
你是 code-arch worker。Batch 2 · Agent1/5 外部搜索能力补全。

[ACK step]
先用一句话 ACK 你已进入 Batch 2 + 理解你要做的事，禁止直接写代码。

[强制前置]
1. cd 到 worktree root (`D:/claude code/demo-code-arch`)
2. git fetch upstream && git status（确认干净 + 在 feat/code-arch 上）
3. 读决策：git log --all --oneline --grep='Q-029' — 读完 Q-029/A-029 全文
4. 读 onboarding：docs/onboarding/batch-2-code-arch-external-search.md（整篇）
5. 读 §3.5 环境边界：git show 40f653f -- CLAUDE.md 或 grep '§3\.5\|env-boundary' CLAUDE.md
6. 读现状：ls shared/sources/impls/ && ls agent_channel/domains/ && ls agent_compliance/domains/ && ls data/mock/channel-kb/ && ls data/mock/compliance-kb/
7. 跑 test_sources_smoke.py 确认环境 OK

[执行顺序]
严格 Task A → B → C 顺序，不并行，每 Task 独立 commit：
- Task A: Agent1 SearchProvider 接 Tavily + look-alike → commit → trailer `Signal: AGENT1-EXTERNAL-SEARCH-DONE`
- Task B: Agent5 SearchProvider 接银保监/央行 + 冲突比对 → commit → trailer `Signal: AGENT5-POLICY-COMPARE-DONE`
- Task C: integration test + evaluation adapter plug-in → commit → trailer `Signal: BATCH-2-INTEGRATION-TEST-DONE`

每 Task 完成前必须：
(a) `pytest tests/<agent>/<test>.py -v` 绿
(b) `git diff --name-only b412656..HEAD` 自查 scope 收敛（红线第 1 条）
(c) commit message 用英文，简洁说明 why + 影响面

[红线]
- 只动 agent_channel/ + agent_compliance/ + shared/sources/impls/ + tests/ + evaluation/runner/adapters/{agent1_channel,agent5_compliance}.py + evaluation/{agent1_channel,agent5_compliance}.yaml
- 不动 web/ / agent_report/ / agent_credit/ / financial_analyzer* / quality_scorer* / truth_fill* / v16_* / data/mock/
- 不动 evaluation/runner/base_evaluator.py / cli.py
- CompanyProfile / ConflictItem 对外 schema 只加字段不删改

[中途不请示]
Blocker 定义：环境不可达（Tavily key 缺 + gov_cn 双路全挂）/ 数据契约冲突 / 红线真被逼触碰。非 blocker 一律不请示，一口气跑到底。

[最终]
3 Task Signal 都打完之后，在 feat/code-arch 顶 HEAD 加一个 review-ready commit：
  Signal: READY-FOR-CODE-ARCH-B2-REVIEW
  body 附 3 commit SHA + git diff --name-only b412656..HEAD + 硬指标自检结论

开干.
```

---

## 7. 参考与交叉引用

- CLAUDE.md §3 架构原则 / §3.2 工具域 / §3.3 Evidence / §3.5 环境边界
- Batch 1 onboarding：`docs/onboarding/code-arch-phase-1.md`（域重拆 / Evidence 基类的结构基础）
- data-foundation v2 onboarding：`docs/onboarding/data-foundation-phase-1-v2.md`（channel-kb / compliance-kb 的产出形态）
- decisions-log：`docs/handoff/decisions-log.md` Q-028（REJECT-V2 形态错复盘）+ Q-029（本批次决策基线）
- 源架构 smoke test：`test_sources_smoke.py`
- Router/Degrader 契约：`shared/sources/base.py` + `shared/sources/router.py` + `shared/sources/degrader.py`
