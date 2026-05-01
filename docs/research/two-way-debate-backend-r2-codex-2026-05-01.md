# 主 CLI + Codex 后端方案辩论 R2 · Codex 互检主 CLI R1

> 2026-05-01 · evidence-based · 不凭印象 · 任务 ID b1fauqi55 · 高 reasoning · ~20 min

## 1. 对主 CLI R1 8 项 verdict

### 1. Agent6 cross-section coherence + historical
**接受 · 但与 Codex R1 material gap graph 不是同一件事**。
- 现有 Agent6 4 维 QC · 其中 financial_consistency 只比对 anchor · 不做跨章节语义/历史一致性 (`agent_report/quality_blocker.py:4-8, 304-314`)
- pending_questions 只作为 done payload 输出 (`agent_report/v16_runner.py:342-350, 400-413`)
- **结论**: 先做 material gap graph · 再做 cross-section coherence

### 2. Agent4 batch analytics + alert clustering
**接受 · 但不替代 Codex R1 信号质量**。
- 已能批量扫描客户 (`agent_alert/customer_scanner.py:76-130`)
- Tavily 默认关闭/缺 key 回 mock (`agent_alert/scan_engine.py:35-61`)
- 证据有 source/confidence (`agent_alert/evidence_pipeline.py:49-79`) · 缺 freshness/replay/cluster
- **结论**: 两条都做 · 信号质量是 batch clustering 的可信前置

### 3. Agent5 政策 RSS + conflict matrix auto
**接受 intake 方向 · 但应接受 Codex R1 更具体 scope**。
- 已有主动政策扫描候选 source_url/fetched_at (`agent_compliance/policy_scanner.py:1-12, 21-76`)
- API 仍主要吃 inline policy_doc + policy_meta (`agent_compliance/api.py:103-107, 241-246`)
- 矩阵已有 hard rule + LLM + N/A (`agent_compliance/scan_engine.py:375-447`)
- **缺**: policy registry / rule version diff / violation reason schema

### 4. Agent3 evidence 链 + 同业对标
**接受 · 加到 decision graph**。
- Agent3 前 4 步确定性 + 最后 AdvisorFormatter 包装 (`decision_engine.py:98-125, advisor_formatter.py:205-244`)
- 同业 gap 已有字段但未纳入可复核链 (`scoring_model_corporate.py:215-240`)
- **结论**: decision graph = feature/rule/阈值/来源/版本 + peer_gap

### 5. Agent2 业务指标双轨
**接受 · 补进 Codex R1 #6/#7**。
- 已给通过率/坏账率/KS panel (`agent_riskctrl/api.py:409-445, 457-465`)
- per-rule FP/TN/FP_rate 已有 (`backtesting.py:203-245`)
- PSI 工具存在 (`agent_riskctrl/metrics.py:59-73`)
- **缺**: 利润影响 / champion-challenger 门禁 / 字段血缘 / 误杀解释

### 6. 数据飞轮真 production
**Phase B 必做 · 但降成 thin production gate · 不先做重 A/B 平台**。
- Phase B charter 明确 `/api/feedback` + 6 agent baseline + few-shot 注入 (`docs/reset/phase-b-charter.md:19-29`)
- evaluation 规则写明改 prompt/逻辑前先跑基线 + blocker_threshold 阻断发布 (`evaluation/README.md:7-10, 32-39`)

### 7. 多租户基础
**反对 Phase B 做"真 isolation + metering"**。
- 当前只有角色 RBAC · 无 tenant_id/org_id (`auth_service/rbac.py:9-15, 41-55`)
- audit DB 默认单路径 (`audit_service/recorder.py:40, 130-138`)
- worker-B2 是商业化 doc · 不是实现多租户 (`docs/reset/phase-b-charter.md:31-40`)
- **结论**: Phase B 出架构与报价假设 · 真多租户 Phase C 或已签 POC 前置

### 8. Agent1 内源 + conversion tracking
**接受 · 与 Codex R1 合并**。
- Agent1 当前 live 缺 Tavily 会早失败 (`agent_channel/api.py:121-142`)
- 已有 customer_list KB 上传 (`api.py:578-599`)
- CandidateProfile 含 source_urls/data_sources/product/pitch (`candidate_profile.py:63-88, 136-153`)
- Top3 产品和 pitch (`product_recommender.py:85-108, sse_extras.py:537-610`)
- **缺**: 内源成交库 / conversion jsonl / 数据源状态评分

## 2. 个人画像 POC verdict

**坚持不新建后端 Agent7**。
- 主 CLI "Agent1 是 toB look-alike 不 fit toC" 不成立: Agent1 已有产品目录/Top3 推荐/批量话术/客户清单 KB (`product_recommender.py:25-108, sse_extras.py:537-610, api.py:578-599`)
- 现有 `shared/personal_profile.py` 已定义个人画像标准模型 (虽注释为 Agent3 对私载体 · `shared/personal_profile.py:2-6, 14-31`) · 可复用为 Agent1 `personal_insight` 输入模型
- **前端可叫 Agent7 · 后端不要复制 SSE/mock/export/audit/RBAC**

跨 Agent POC 应展开:
- Agent1 做画像/产品/话术
- Agent5 做产品合规校验 (matrix + violation reason)
- Agent4 做触达后预警和客户事件回流
- **不要先造 orchestrator 重平台**

## 3. R2 加补

### POC 评分 4 维覆盖度

| 维度 | 现状覆盖 | 缺口 |
|---|---|---|
| 客户画像 35% | personal_profile 覆盖身份/职业/收入/征信/流水/抵押 | CRM 整合 / 隐性标签 / 需求预测 |
| 产品适配 25% | Agent1 Top3 + pitch 覆盖一半 | toC 产品库 / 适当性 / Agent5 合规红线 |
| 经营策略 20% | pitch 有 | 任务拆解 / KPI / 转化追踪 |
| 性能 20% | 6 Agent SSE/audit 基础 | PII 脱敏 / latency budget / eval baseline |

### 新增真痛: **跨 Agent decision ledger**

现在各 Agent 有 evidence_pipeline · 但**没有统一"结论账本"把候选/报告/授信/合规/预警串成同一客户的一条可审计链**。

这个比新 ML / Agent7 更接近 PM "到底解决什么痛点":
- **银行用户不敢信** (单 Agent evidence 不够 · 需要跨 Agent 一致性)
- **不敢签** (审贷员/合规官签字要看完整链)
- **不敢追责** (出问题没法回溯哪个 Agent 哪步出错)

## 4. R2 verdict

**接受主 CLI R1 6.5/8**:
- 接受 6: Agent6 / Agent4 / Agent5 / Agent3 / Agent2 / Agent1
- 数据飞轮接受但缩成 Phase B gate (0.5)
- 多租户实现反对 · Phase B 只做商业化 doc (0.5 反对)

**主 CLI 应接受 Codex R1 7/8**:
- 尤其 Agent1 子域 / Agent3 decision graph / Agent5 policy version / Agent2 champion-challenger / Agent4 signal quality / Agent6 material gap
- 只把同业对标和业务指标双轨补进 Codex 清单

**Phase B 后端 deep work 去重清单**:
1. Agent1 candidate/source/conversion
2. Agent6 material gap + coherence
3. Agent3 decision graph + peer_gap
4. Agent5 policy registry/version diff/reason schema + scanner
5. Agent2 DSL gate/backtest/business metrics
6. Agent4 signal quality + clustering
7. B1 feedback baseline gate (不重平台)
8. B2 multi-tenant **commercial architecture only** (不实装)

**+ 加补 9. 跨 Agent decision ledger** (统一结论账本)

**个人画像 POC**: 后端放 Agent1 `personal_insight` 子域 · 复用 `shared.personal_profile` · 联 Agent5/Agent4 · 不建纯 Agent7。
