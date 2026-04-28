# Worker A1 (Stage D 第 1 批 · 同时) · shared/kb_scan refactor · Onboarding

> Worker CLI 在 `D:/claude code/work-A1-inventory` (branch
> `feat/inventory-expand-A1`) · 复用 worktree。
> 上批 Stage CF Report frontend (`23857b0`) 已 cherry-pick MERGED (`dc1a024`) ·
> 本批 Stage D.5 启动 · 跟 A2 D.1 auth + A3 D.2 IM WebSocket 同批跑。

## Goal

实装 master plan §D.5 — `shared/kb_scan/` 共享底座 refactor。
**gap #9 (shared/kb_scan/ 共享底座 · 现状各 Agent 各管 · 重复实现) 闭环**。

现状 (各 Agent 自管):
- `agent_alert/scan_engine.py` (Q-040 Alert KB_DEMO unlock)
- `agent_compliance/scan_engine.py` (Stage C.4 政策矩阵)
- `agent_channel/sse_extras.py` 部分 (radar / signals)
- 等等

抽到 `shared/kb_scan/` · 6 Agent 复用 · 类似 `shared/sources/` 已成 pattern。

## Acceptance

- [ ] **必读** `shared/sources/` 现成 pattern (BaseSource 协议 + Router + Degrader · CLAUDE.md §10)
- [ ] **必读** 各 Agent 现 scan_engine / KB scan 实装 (5+ file)
- [ ] **新建** `shared/kb_scan/` module:
  - `base.py` (BaseScanner 协议 · 输入 query/KB · 输出 ScanResult)
  - `router.py` (Agent → Scanner 路由 · 复用 sources_config 模式)
  - `degrader.py` (LLM/Tavily fail fallback · Q-040 教训)
  - `impls/` (per-Agent scanner: alert / compli / channel / etc.)
- [ ] **改造** 6 Agent backend 现各自 scan_engine → import shared/kb_scan/ ·
      surgical edit · 不破坏现有功能
- [ ] **cumulative pytest** 全 6 Agent + shared/ tests 全 PASS (现 ~150 case +
      新加 ≥ 10 shared/kb_scan test)
- [ ] **不动**: agent_*/api.py endpoint surface (URL / params 不变) · web/* (frontend) ·
      其他 shared/* (sources / api_utils 等)
- [ ] commit trailer:
  ```
  Signal: WORKER-A1-STAGE-D5-SHARED-KB-SCAN-DONE
  RECOVER-FROM: 23857b0 (Report frontend done · 本批接续)
  REFACTORED: agent_alert/scan_engine.py, agent_compliance/scan_engine.py, agent_channel/sse_extras.py
  NEW-MODULE: shared/kb_scan/{base.py, router.py, degrader.py, impls/}
  ```

## Boundary

- **改**: 6 Agent backend 现各自 scan / KB module · 改 import 用 shared
- **加**: `shared/kb_scan/{base,router,degrader}.py` + `shared/kb_scan/impls/` ·
  `shared/kb_scan/tests/test_*.py` · `agent_*/sources_config.py` 类似 sources_config
- **不动**: `agent_*/api.py` endpoint URL/params (URL surface 保持稳定 · 内部
  refactor) · `web/*` · `auth_service/` (D.1 worker A2 在改) · `im_service/`
  (D.2 worker A3 在改) · CLAUDE.md · RFC

## Dependencies

- master plan §D.5 (gap #9)
- `shared/sources/` 已成 pattern (CLAUDE.md §10 · `shared/sources/impls/` 6 个源实现)
- 不依赖 D.1 / D.2 (A2/A3 同批 · 各自独立 module)

## Method

1. Read `shared/sources/` 6 file (BaseSource / Router / Degrader / impls)
2. Survey 6 Agent 现 scan_engine / KB scan code:
   - agent_alert/scan_engine.py
   - agent_compliance/scan_engine.py
   - agent_channel/sse_extras.py
   - agent_credit/* (复用 financial_analyzer · 不变)
   - agent_report/v16_runner.py (v16 pipeline · 不变)
   - agent_riskctrl/* (rule_engine · backtesting · 不变)
3. 抽 common surface 设计 BaseScanner 协议
4. router 路由 (Agent → Scanner config)
5. degrader (Tavily 401 / LLM timeout fallback chain)
6. 6 Agent 改 import 用 shared (surgical · 不重写)
7. pytest cumulative · 不 break 任何 case
8. curl 端到端 sanity check

## Trailer protocol

```
Signal: WORKER-A1-STAGE-D5-SHARED-KB-SCAN-DONE
RECOVER-FROM: 23857b0
REFACTORED: <list of agent files>
NEW-MODULE: shared/kb_scan/{base,router,degrader,impls}
```

## On completion

1. `git add shared/kb_scan/ agent_*/` + commit + push origin
2. main CLI auto-patrol → review (cumulative pytest + curl + import diff verify)
   → cherry-pick → push origin

## Estim

5-8 hr (refactor 6 Agent 共享底座 · 谨慎不破坏 · cumulative pytest 必跑)

## NB

- D.5 是系统级 refactor · risk 中 · 必须 surgical 不重写各 Agent 业务逻辑
- 抽出后 6 Agent 共享 fallback chain · Tavily 401 (Q-040) 一处修全 6 Agent 受益
- A2 D.1 + A3 D.2 同批跑 · 你 不 import auth/im · 0 conflict
- 后续 Stage E hardening (audit log · 监控) 会在 shared/kb_scan/ 之上加 hooks
- shared/sources/ 是已成 pattern · 复用思路即可 · 不重新设计 contract
