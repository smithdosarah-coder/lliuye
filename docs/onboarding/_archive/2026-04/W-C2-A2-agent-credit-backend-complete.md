# Worker A2 (Stage C 第 2 批) · Agent3 Credit backend complete · Onboarding

> Worker CLI 在 `D:/claude code/work-A2-contracts` (branch
> `feat/contracts-bootstrap-A2`) · 复用 Stage A+B+C 同 worktree。
> 上批 Stage C.5 Riskctrl LLM (`c69f021`) 已 cherry-pick MERGED (`cb8bff1`) ·
> 本批 Stage C.2 启动。

## Goal

实装 master plan §C.2 — Agent3 Credit backend 完整 production-grade:
- LLM 真接 4 维评分 (对公 / 普惠 / 对私 三板块)
- 红线判定 (deterministic + LLM 双层)
- 决策建议书 Word 导出
- **gap #6 (Credit Workspace) backend** + **gap #8 (Agent3 stub)** + **gap #12 (Credit Word)** 闭环

## Acceptance

- [ ] `POST /api/credit/decision` SSE 流式 · body `{stage_tab: "corporate" | "small_business" | "retail", report_json: {...}, materials: [...]}` · 返 4 维 score + 红线 + 案例召回
- [ ] `GET /api/credit/presets` · 返各 stage_tab 默认评分维度 + 红线规则
- [ ] `POST /api/credit/export_docx` body `{decision_id}` · 返决策建议书 .docx
- [ ] LLM 真接: 4 维评分用 DeepSeek prompt 真生成 · 不是硬编 stub
- [ ] 红线: deterministic 计算 (财务红线) + LLM 红线 (业务红线) 双层
- [ ] curl 测 3 endpoint × 3 stage_tab = 9 case · sample 进 commit body
- [ ] pytest `agent_credit/tests/` ≥ 9 case (3 stage × 3 path · mock LLM + 真 financial_analyzer)
- [ ] commit trailer:
  ```
  Signal: WORKER-A2-STAGE-C2-CREDIT-BACKEND-DONE
  RECOVER-FROM: c69f021 (Stage C.5 done · 本批接续)
  NEW-ENDPOINT: POST /api/credit/{decision,export_docx}, GET /api/credit/presets
  ```

## Boundary

- **改**: `agent_credit/api.py` (LLM 真接 + 4 维 + 红线) + `agent_credit/word_export.py` (新)
- **加**: `agent_credit/tests/test_decision_corporate.py` · `test_decision_small_business.py` ·
  `test_decision_retail.py` · `test_redlines.py` · `test_export_docx.py`
- **不动**: `financial_analyzer.py` (确定性计算复用) · `web/*` · 其他 Agent · CLAUDE.md · RFC

## Dependencies

- master plan §C.2 (gap #6 + #8 + #12)
- agent-credit-spec.md (Stage A.5 cherry-pick · `bf5a7f1`)
- financial_analyzer.py (§3.1 确定性计算层 · 复用)
- DeepSeek client (api_server.py 已配)
- python-docx (Channel A1 docx 模式可参考 · 5e7f53a)

## Method

1. Read `agent_credit/api.py` + `agent-credit-spec.md` + `financial_analyzer.py`
2. 设计 LLM prompt for 4 维评分 (经营财务 / 风险偏好 / 还款能力 / 行业前景 · 3 stage_tab 各异)
3. 红线规则: deterministic (财务比率红线 · 走 financial_analyzer) + LLM 业务红线 (负面信息 / 关联交易)
4. word_export 复用 Channel docx 模式 · 决策建议书 schema
5. pytest 9 case + curl 验

## Trailer protocol

```
Signal: WORKER-A2-STAGE-C2-CREDIT-BACKEND-DONE
RECOVER-FROM: c69f021
NEW-ENDPOINT: POST /api/credit/decision (SSE), /api/credit/export_docx, GET /api/credit/presets
```

## On completion

1. `git add agent_credit/` + commit + push origin
2. main CLI auto-patrol → review (curl + pytest + Word + trailer) → cherry-pick → push

## Estim

5-7 hr (4 维 prompt 调优 · 红线规则 · Word · 9 case 测试)

## NB

- 4 维评分必须**说人话** · 不是黑盒分数 · 含 reasoning_text + 证据链
- 红线判定: 触发即 reject · LLM 不能复原(否则用户被绕过)
- 对公 / 普惠 / 对私三板块**评分维度可不同** (per agent-credit-spec.md)
