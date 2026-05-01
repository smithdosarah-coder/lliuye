# 后端方案 v2.1 final · 主 CLI + Codex 至少 3 轮辩论后

> 2026-05-01 · 痛点驱动 (PM ultrathink "深度考虑产品到底解决了什么痛点") · 不凭印象
> R1 + R2 + R3 三轮辩论完成 · 替代 v2 charter 8 项凭印象 (~17% evidence)
> v2.1 evidence 强度 ~85% (file:line 证据 + 4 角色痛点对照)

## 0. 辩论真实性 verify

| 轮次 | 主 CLI | Codex |
|---|---|---|
| R1 独立 | `two-way-debate-backend-r1-mainCLI-2026-05-01.md` (4 角色 10+ 痛点 + 自审 v2 8 项) | `two-way-debate-backend-r1-codex-2026-05-01.md` (b6b152s2w · 全扫 175 .py file:line evidence + 8 真痛 + POC verdict) |
| R2 互检 | `two-way-debate-backend-r2-mainCLI-2026-05-01.md` (接 Codex 95% · 撤 Agent7 错 · 加补 4 项 scope 外) | `two-way-debate-backend-r2-codex-2026-05-01.md` (b1fauqi55 · 接主 CLI 6.5/8 · 加补 decision ledger · POC 坚持 Agent1 子域) |
| R3 综合 | 本 doc (主 CLI 综合双方 · 13 BE final 清单 + PM 拍板) | n/a (主 CLI 综合 · Codex R2 已表态完整) |

## 1. 痛点根本 (Codex R2 verbatim)

> **银行用户不敢信 · 不敢签 · 不敢追责**

后端真痛不是"缺 ML / embedding / batch analytics" — 这些都是手段。真痛是 4 角色对 AI 输出的**信任 + 可复核 + 可追责**。

## 2. 13 BE 后端 deep work final 清单

### P0 必做 (Phase B-3 后端 sprint · ~10-12.5 周 含并行 ~7-9 周 wall-clock)

| # | BE | 解决谁的什么痛 | 改成啥 (具体) | 工程量 | Evidence |
|---|---|---|---|---|---|
| **BE1** | Agent1 候选证据评分 + 数据源状态 + conversion tracking | RM 痛 1.1.2+3 (look-alike 不准 + 没追踪转化) | 内源已成交客户库 (`customer/`) + similarity 4 维度 explainable + 每候选输出来源/时间/命中字段/可联系性/缺口 + RM 选候选后落 conversion jsonl | 1.5-2 周 | `agent_channel/api.py:121, 134, 197` + `candidate_profile.py:63-88, 136-153` |
| **BE2** | Agent3 decision graph (feature/rule/阈值/来源/版本) + peer_gap (同业对标) | 审贷员痛 1.2.1+4 (AI 评分黑盒 + 缺同业对标) | 每结论挂 feature snapshot/rule hit/阈值/来源段落/版本 · scoring_model_corporate.py 已有 peer_gap 字段未纳可复核链 | 2 周 | `decision_engine.py:98-125, advisor_formatter.py:205-244, scoring_model_corporate.py:215-240` |
| **BE3** | Agent6 material gap graph + section impact + handoff Agent3 + cross-section coherence sanity | RM + 审贷员痛 1.2.3 (报告章节不一致 + 缺材料闭环) | pending_questions 已有但未输出"缺哪份材料影响哪章/哪项评分" · 加 material gap graph + section impact + cross-section coherence (`quality_blocker.py:4-8` financial_consistency 只比对 anchor · 加跨章节语义/历史一致性) | 1.5-2 周 | `v16_runner.py:342-350, 400-413, 485 + quality_blocker.py:304-314` |
| **BE4** | Agent5 policy registry + rule version diff + violation reason schema | 合规官痛 1.3.1+2 (政策版本管理 + 冲突解释签字) | 已有 policy_scanner candidate source_url/fetched_at · API 仍吃 inline · 加 policy registry + rule version diff + violation reason schema (冲突字段/业务原文/条款原文/置信度/复核原因) | 2-2.5 周 | `policy_scanner.py:1-12, 21-76 + api.py:103-107, 241-246 + scan_engine.py:375-447` |
| **BE5** | Agent4 信号质量 (freshness + source confidence + fallback banner + scan replay) | 风险经理痛 (Agent4 缺 key 回 mock 信号不可信) | Tavily 默认关闭/缺 key 回 mock · 已有 evidence_pipeline source/confidence · 加 freshness/replay/cluster | 1 周 | `scan_engine.py:35-61 + evidence_pipeline.py:49-79` |
| **BE6** | Agent2 DSL 上线性 (字段字典 + 单位归一 + 互斥/遮蔽) + 业务指标双轨 (KS/AUC + 通过率/坏账率/利润影响) | 风险经理痛 1.4.1+2 (DSL 写完不知道好不好 + KS/AUC 业务方看不懂) | 已有通过率/坏账率/KS panel + per-rule FP/TN/FP_rate · PSI 工具 · 加字段字典/单位归一/互斥/遮蔽 + 利润影响 + 业务指标双轨 (大白话结论) | 2-2.5 周 | `api.py:409-445, 457-465 + backtesting.py:203-245 + metrics.py:59-73` |

### P0 加补 (Codex R2 加补 · game-changer)

| # | BE | 解决谁的什么痛 | 改成啥 | 工程量 |
|---|---|---|---|---|
| **BE7** | **跨 Agent decision ledger** (统一结论账本) | 4 角色全部 (银行用户不敢信/不敢签/不敢追责 · Codex R2 verbatim) | 候选/报告/授信/合规/预警串成同一客户一条可审计链 · 各 Agent evidence_pipeline 上层加 ledger · 出问题可回溯哪个 Agent 哪步 | 2 周 |

### P1 推 Phase C OR Phase B 末配套

| # | BE | 解决谁的什么痛 | 改成啥 | 工程量 |
|---|---|---|---|---|
| **BE8** | Agent2 回测可信度 (champion/challenger 门禁 + 字段血缘 + 误杀解释) | 风险经理痛 1.4.1 (回测可信度) | 已有窗口/基线/PSI · 加 champion-challenger 门禁 + 字段血缘 + 误杀样本解释 | 2 周 |
| **BE9** | Agent4 跨客户 batch analytics + alert clustering (per handoff schema §6.4) | 风险经理痛 1.4.3 (跨客户模式发现) | customer_scanner 已能批量 · 加跨客户聚合 (≥ 3 客户共同信号) + alert clustering 同类合并 (BE5 信号质量是前置) | 2 周 |

### Enabler (Codex R2 缩 scope)

| # | BE | 改成啥 | 工程量 |
|---|---|---|---|
| **BE10** | 数据飞轮 thin Phase B gate (per Codex R2 缩 scope · 不重 A/B 平台) | `/api/feedback` 接 audit modify + 写 jsonl + 6 Agent baseline 跑通 + blocker_threshold 阻断发布 (per evaluation/README.md) + few-shot 注入 PoC (per phase-b-charter.md) | **1.5 周** (vs 主 CLI 原 3 周 · Codex 缩) |
| **BE11** | 多租户 commercial architecture only (per Codex R2 反对实装) | Phase B 出架构 doc + 报价假设 + tenant_id/org_id 数据模型 spec · **不真实装** isolation/audit/metering | **1 周** (vs 主 CLI 原 3-4 周 · Codex 缩 · 真实装 Phase C 或已签 POC 前置) |

### 个人画像 POC (Codex 坚持 Agent1 子域 · 主 CLI R2 已接受撤 Agent7 错)

| # | BE | 改成啥 | 工程量 |
|---|---|---|---|
| **BE12** | Agent1 `personal_insight` 子域 (复用 `shared/personal_profile.py`) | 复用 personal_profile 标准模型 (身份/职业/收入/征信/流水/抵押 · 已 covered) + 加 CRM 整合/隐性标签/需求预测 + Top3 产品适配 + Agent5 合规红线 + 触达话术 + PII 脱敏 + latency budget · **前端可叫 Agent7 · 后端 NOT 复制 SSE/mock/export/audit/RBAC** | **2.5 周** |
| **BE13** | POC 跨 Agent 拼 (Agent1 + Agent5 + Agent4) | Agent1 画像/推荐/话术 → Agent5 产品合规校验 (matrix + violation reason) → Agent4 触达后预警 + 客户事件回流 · **不造 orchestrator 重平台** | **1.5-2 周** |

## 3. 总 Phase B 工程量

- P0 必做 BE1-BE6: ~10-12.5 周
- P0 加补 BE7 (decision ledger): ~2 周
- P1 推 Phase C OR 配套 BE8-BE9: ~4 周
- Enabler BE10-BE11: ~2.5 周 (Codex 缩后)
- 个人画像 POC BE12-BE13: ~4-4.5 周

**总后端 ~22-25 周 (含并行 ~14-16 周 wall-clock)**

加 v4 前端 (5-6 周 · 含并行 ~4-5 周) · **总 Phase B 真完整版: ~14-18 周 wall-clock** (vs 单前端 v4 5-6 周 · 多 9-12 周 真产品力)

## 4. PM 拍板项 (12 项 · 推荐都 A)

| # | 提案 | 选项 | 推荐 | 理由 |
|---|---|---|---|---|
| 1 | 接受痛点根本判断 (银行用户不敢信/不敢签/不敢追责) | A 接受 / B 不 | **A** | Codex evidence-based 提 + 主 CLI 4 角色痛对应 |
| 2 | BE1-BE6 P0 必做 | A 全做 / B 砍部分 | **A** | 4 角色全 cover · 都有 file:line evidence |
| 3 | BE7 跨 Agent decision ledger 加补 | A 接受 P0 / B 推 Phase C | **A** | game-changer · Codex 加补 · 解 4 角色不敢信根本 |
| 4 | BE8-BE9 (回测 + batch analytics) Phase B 还是 Phase C | A Phase B 末配套 / B 推 Phase C | **A** | BE9 与 BE5 信号质量配套 (BE5 P0 + BE9 P1 同 sprint) · BE8 配 BE6 Agent2 工作 |
| 5 | BE10 数据飞轮缩 Phase B gate (Codex 反对重平台 1.5 周) | A 接 Codex 缩 / B 主 CLI 原 3 周 | **A** | Codex 务实 · evaluation README 已有 baseline 规则 · 不重做 |
| 6 | BE11 多租户改 commercial architecture only (Codex 反对实装 1 周) | A 接 Codex / B 主 CLI 原 3-4 周 | **A** | Codex 务实 · 没真客户买之前不需 isolation · Phase B 出架构 + 报价假设 |
| 7 | 个人画像 POC = Agent1 子域 (撤 Agent7 主 CLI 错) | A 接 Codex / B 新建 Agent7 | **A** | Codex evidence-based + 复用 shared/personal_profile · 主 CLI 凭印象错诚实承认 |
| 8 | BE13 跨 Agent POC 拼 (Agent1 + Agent5 + Agent4 · 不造 orchestrator) | A 接 Codex 拼 / B 不做 | **A** | POC 加分项 + 不重平台 |
| 9 | 撤 v2 charter 凭印象 3 项 (ML / embedding / ML rule mining) | A 撤 / B 保 | **A** | 都是手段不是目的 · evidence 弱 |
| 10 | 加 worker-B4 系列 (BE1-BE9 后端 deep work) 并行 worker-B3 (v4 前端 5-6 周) | A 加 / B 串行 | **A** | 节省 wall-clock 时间 |
| 11 | Phase B 总工程量 ~14-18 周 wall-clock 接受 | A 接受 / B 砍 | **A** | 真产品力差异 · 银行客户能买 |
| 12 | 退回点 git tag `phase-a-exit-bugfix-2026-05-01` 是 Phase B ship 不满意时 baseline | A 接受 / B 不留 | **A** | 已落 (per Phase A 真 exit milestone) |

## 5. 不做的边界 (产品特色保护红线 · 双方共识)

- ❌ 真 ML 模型 (logistic/GBDT/embedding) — 都是手段不是目的 · 真痛是 evidence 链
- ❌ 全 6 Agent 一步 modal 化 (per v4 已撤)
- ❌ 5 角色含产品经理/部门领导 (per v4 不做)
- ❌ 投贷联动 / 五融生态 (per v4 不做)
- ❌ 全屏渐变全撤 (per v4 折中)
- ❌ Agent7 新建后端 (Codex evidence-based 反对 · Agent1 子域足够 + 前端可叫 Agent7)
- ❌ 多租户 Phase B 真实装 (Codex 反对 · Phase C 或已签 POC 前置)
- ❌ 数据飞轮 Phase B 重 A/B 平台 (Codex 反对 · thin gate)

## 6. 退回点 (后续 Phase B ship 不满意时用)

```bash
cd "D:/claude code/credit_report_agent_work"
git fetch --all --tags
git reset --hard phase-a-exit-bugfix-2026-05-01
git push origin main --force-with-lease  # ⚠️ destructive · PM 必须明确同意
bash scripts/deploy_to_ecs.sh
```

## 7. PM 拍板后落地

PM 同意 12 项 (or 部分调) → 主 CLI 立即:
1. 写 `docs/reset/phase-b-charter.md` v2 (覆盖 v1 · 含 Stream 1 v4 前端 + Stream 2 BE1-BE13 后端 + Stream 3 enabler)
2. 写 `docs/handoff/decisions-log.md` Q-NNN entry "后端方案 v2.1 ratify · 13 BE + 痛点驱动 + 个人画像 Agent1 子域"
3. commit + push
4. Phase B 启动 (派 worker-B1 / worker-B3 / worker-B4-{credit/report/alert/compliance/channel/riskctrl} · per multi-cli-mesh skill)

## 8. Sign-off

- R1 主 CLI (产品 PM 4 角色痛点) ✅ commit
- R1 Codex (b6b152s2w · 全扫 175 .py file:line) ✅ commit
- R2 主 CLI (95% 接受 Codex + 撤 3 错) ✅ commit
- R2 Codex (6.5/8 接受主 CLI + 加补 decision ledger) ✅ 本 commit 含
- R3 主 CLI 综合 (本 doc · 13 BE final + 12 PM 拍板项) ✅ 本 commit
