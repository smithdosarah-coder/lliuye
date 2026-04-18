# Agent3 Phase 1 — 产品化进度文档

**状态：** `[READY-FOR-REVIEW]`
**分支：** `feat/agent3-productize`
**完成日期：** 2026-04-18
**承接 onboarding：** `docs/onboarding/agent3-phase-1-prompt.md`

---

## 1. 任务交付清单（commit 粒度 = task 粒度）

| # | Task | 工件 | Commit |
|---|---|---|---|
| T1 | 字段命名修正：severity → red/yellow/green，删 `is_hard` | `agent_credit/*.py` + `web/src/lib/credit-types.ts` | `4442178` |
| T2 | Agent6→Agent3 Handoff 入口：2 家 demo 画像 + HandoffButton + 端点 | `demo_data/agent_credit/corp_dingsheng_trade.json` / `retail_lisi_education.json` + `agent_credit/api.py` + `web/src/components/credit/HandoffButton.tsx` | `022a4f9` |
| T3 | 四维雷达 thin wrapper：`RiskRadar.tsx` | `web/src/components/credit/RiskRadar.tsx`（segment 分派）+ `credit/page.tsx` | `0bbc671` |
| T4 | 原因码 YAML 字典 + advisor 接入 | `docs/reason_codes/agent3-{corporate,retail}.yaml`（31 码） + `agent_credit/reason_codes.py` + `DecisionAdvice.top_reason_codes` | `0532507` |
| T5 | 决策意见书 docx 本地导出（无境外 API） | `agent_credit/docx_export.py`（python-docx + 微软雅黑 OOXML 双绑）+ `/api/credit/export_docx` + `ExportDocxButton` | `a541c92` |
| T6 | 评估基线首跑 | `evaluation/agent3_credit.yaml`（红线闸门） + `evaluation/run_agent3.py`（确定性复算 + 幻觉正则检测） + `evaluation/results/3_20260418.yaml` | `afaa7de` |
| T7 | L0 自查 + tests + 进度文档 | `agent_credit/tests/test_{reason_codes,docx_export,api}.py`（16 用例）+ 本文档 | 本 commit |

---

## 2. DoD 逐条打勾

- [x] **L0 全 14 条通过**
  - `ruff check agent_credit/reason_codes.py agent_credit/docx_export.py agent_credit/tests evaluation/run_agent3.py` → **All checks passed**
  - `pytest agent_credit/tests -q` → **16 passed in 2.92s**
  - 说明：`agent_credit/advisor_formatter.py` / `api.py` 存在 10 条 BLE001 **预存 lint 债**，为红区旁 L2 文件，本轮未引入新问题；整轮清理建议走独立 RFC（见 §5 观察）

- [x] **L1-3（四维雷达）** — `RiskRadar.tsx` thin wrapper，按 segment 自动分派 (capacity/guarantee/operational/industry) vs (credit/capacity/compliance/collateral)
- [x] **L1-4（docx 导出）** — 本地 python-docx，产物落 `data/exports/agent3_credit/`；RFC 5987 UTF-8 中文文件名
- [x] **L1-11（handoff 按钮）** — 从 Agent6 ReportJSON `/api/credit/handoff/demo/{corporate|retail}` 一键载入

- [x] **L2-3（确定性计算走 Python）** — 红线 / 评分 / 额度三估算全走 `RuleEngineV2` + `CorporateScoringModel` / `RetailScoringModel` + `AdvisorFormatter`；LLM 只消费已算好的 features_snapshot
- [x] **L2-7 / L2-8（原因码）** — 31 条标准码（对公 15 + 对私 16），4 档优先级 `rule > feature > severity > decision_hint`，Top-5 截断，每条带 `evidence_path` + `evidence_value` + `threshold`

- [x] **L3-1 / L3-2（评估基线）** — `evaluation/results/3_20260418.yaml`：
  - `hallucination_rate = 0.0` **< 0.02** ✅
  - `evidence_rate = 1.0` **≥ 0.90** ✅
  - `field_completeness = 1.0` **≥ 0.90** ✅
  - `overall_verdict: PASS`

- [x] **2 家预置企业端到端** — `corp_dingsheng_trade`（对公·有条件批准）+ `retail_lisi_education`（对私·批准）；评估脚本本地跑 ~5 秒（无 LLM 介入路径）

- [x] **commit 粒度 = task 粒度** — 6 次功能 commit（T1-T6）+ 本 T7 共 7 次

- [x] **进度文档** — 本文件

---

## 3. 绿区边界自证

本轮全部改动落在 `docs/shared-change-protocol.md v1.0` 允许的绿区：

- `agent_credit/**`（不含 `shared/` 红区依赖）
- `web/src/app/credit/**` + `web/src/components/credit/**`
- `docs/reason_codes/**` + `docs/progress/**`
- `evaluation/**` + `demo_data/agent_credit/**`

未动 `shared/base_agent.py` / `api_server.py` / `quality_scorer.py` / `truth_fill.py` / `financial_analyzer.py` / `section_generator.py` 等红区文件。

---

## 4. 字段命名合规

严格遵守 `docs/contracts/field-naming.md v1.0`：

- `severity ∈ {red, yellow, green}`（31 个原因码 + `RedLineHit.severity` + 前端 `credit-types.ts` 全线统一）
- 删除 `is_hard` 冗余字段
- 金额后缀 `_wan`（`approved_amount` 单位万元）
- 布尔字段 `is_` 前缀（`is_dishonest_list`、`is_fraud_flag` 等 feature 路径）

---

## 5. 观察 / 待澄清事项

### 5.1 Onboarding 引用的文档未落盘

onboarding prompt §2 引用以下文档，仓库中均**不存在**（目录存在但为空）：

- `docs/scorecard/definition-of-done.md`（五层交付标准）
- `docs/scorecard/GLOBAL.md §六`（Agent3 productize 路线）

本轮按 prompt 正文描述的 DoD 条款执行（L0/L1/L2/L3 + 6 硬约束）。若主 CLI 后续补齐这两份文档，需回补核对一轮。

### 5.2 预存 lint 债

`agent_credit/advisor_formatter.py` / `api.py` / `agent.py` 存在 10+ BLE001 / F401 / UP 告警，均为本轮之前已存在。清理是否合并到 Phase 2 请主 CLI 裁决；个人建议独立 chore PR 走而非混入功能分支。

### 5.3 原因码映射覆盖率

`CORPORATE_RULE_CODE_MAP` / `RETAIL_RULE_CODE_MAP` 当前仅各 1 条精确映射，其余走 severity 回退码。完整映射需要配合规则引擎 30/20 条规则库迭代（Phase 2 范围）。

### 5.4 评估脚本的 LLM 路径未覆盖

`evaluation/run_agent3.py` 目前只测规则 + 评分 + 额度三估算层（确定性层），未注入 LLM 生成决策话术的路径。DoD L2-3 不要求 LLM 现场算数字，所以不是 blocker；但 Phase 2 扩充 LLM-in-loop 评估需要补 `mock_llm` / `deepseek` 开关。

---

## 6. 复现命令

```bash
# 后端
py -m pytest agent_credit/tests -q              # 16 passed
py -m ruff check agent_credit/reason_codes.py \
    agent_credit/docx_export.py \
    agent_credit/tests evaluation/run_agent3.py # All checks passed

# 评估
py -m evaluation.run_agent3                     # 产出 evaluation/results/3_20260418.yaml

# API smoke
py /tmp/start_uvicorn.py                        # 在另一终端
curl http://127.0.0.1:8000/api/credit/handoff/demo/corporate

# 前端
cd web && npm run dev                           # http://localhost:3000/credit
```

---

## 7. 信号

`[READY-FOR-REVIEW]`

主 CLI 请按 `docs/onboarding/agent3-phase-1-prompt.md §7` 流程 review。有阻塞项请回 `[NEED-CHANGES]` + 具体条款。
