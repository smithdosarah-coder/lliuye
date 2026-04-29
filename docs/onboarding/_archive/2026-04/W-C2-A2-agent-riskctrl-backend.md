# Worker A2 (Stage C 第 1 批) · Agent2 Forge/Riskctrl backend LLM 真接 · Onboarding

> Worker CLI 在 `D:/claude code/work-A2-contracts` (branch
> `feat/contracts-bootstrap-A2`) · 复用 Stage A+B 同 worktree。
> Stage A (`4e8310b` contracts) + Stage B.6 (`9d75279` KB upload) 已
> MERGED 进 chore/l0-infra (`a660019` + `4f17e22`) · 本批 Stage C 启动。

## Goal

实装 master plan §C.5 — Agent2 Forge/Riskctrl backend 后端补 LLM 真接 (现 stub)。
**gap #8 (Agent2/3 后端 stub) Channel domain 部分闭环**。

## Acceptance

- [ ] `agent_riskctrl/api.py` 真接 LLM (DeepSeek)
- [ ] `POST /api/riskctrl/dsl_gen` body `{strategy_intent, sample_csv_path}` →
      LLM 真生成 DSL JSON (RuleSet pydantic)
- [ ] `POST /api/riskctrl/backtest` body `{ruleset, csv_path}` → 跑
      `backtesting.py` (Q-040 fix MAX_ROWS=50000) + 返 KS / AUC / 通过率 /
      坏账率
- [ ] `POST /api/riskctrl/run` body `{ruleset}` placeholder · 暂不真上线 (只
      返 confirmation)
- [ ] curl 测 dsl_gen + backtest 各一次 · 返真 LLM JSON · sample 进 commit
- [ ] pytest `agent_riskctrl/tests/` 全绿 (复用现 test + 加 LLM mock test)
- [ ] commit trailer:
  ```
  Signal: WORKER-A2-STAGE-C-RISKCTRL-LLM-DONE
  RECOVER-FROM: 9d75279 (Stage B done · 本批接续)
  NEW-LLM-ENDPOINT: /api/riskctrl/dsl_gen, /api/riskctrl/backtest
  ```

## Boundary

- **改**: `agent_riskctrl/api.py` (LLM call 替换 stub) +
  `agent_riskctrl/llm_client.py` (新建 if 需要)
- **加**: `agent_riskctrl/tests/test_llm_dsl_gen.py` ·
  `test_backtest_real.py`
- **不动**: `web/*` · 其他 Agent · `backtesting.py` (Q-040 已 fix · 复用) ·
  CLAUDE.md · RFC

## Dependencies

- master plan §C.5 (gap #8 Agent2 后端 stub)
- `agent-forge-spec.md` (Stage A.5 cherry-pick · `bf5a7f1`)
- `backtesting.py` (Q-040 fix MAX_ROWS=50000)
- DeepSeek client (api_server.py 已配)
- `loans.csv` (data-foundation worker 已 done · 7500 行 fixture)

## Method

1. Read `agent_riskctrl/api.py` + `agent-forge-spec.md`
2. 设计 LLM prompt for DSL 生成 (RuleSet shape)
3. 写 endpoint LLM call + parse JSON → RuleSet pydantic
4. backtest endpoint 调 backtesting.py · 返完整 metrics
5. pytest + curl 验

## Trailer protocol

```
Signal: WORKER-A2-STAGE-C-RISKCTRL-LLM-DONE
RECOVER-FROM: 9d75279
NEW-LLM-ENDPOINT: /api/riskctrl/dsl_gen, /api/riskctrl/backtest
```

## On completion

1. `git add agent_riskctrl/` + commit + push origin
2. main CLI auto-patrol → review (pytest + curl + trailer) → cherry-pick

## Estim

4-5 hr (LLM prompt 调优 · DSL parsing 健壮性主要工作)
