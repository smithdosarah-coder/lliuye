# Worker A1 (Stage E.2 第 1 批) · Test Coverage Expansion · Onboarding

> Worker CLI 在 `D:/claude code/work-A1-inventory` (branch
> `feat/inventory-expand-A1`) · 复用 worktree。
> 上批 Stage E.1 audit log (`81a9540` → c51a07f) 已 cherry-pick MERGED ·
> 本批 Stage E.4 启动 (production hardening 测试加固)。

## Goal

实装 master plan §E.4 — pytest test coverage 现 ~150 → 500+ case ·
**banking production 必修** · 不允许 critical path 测试不全。

范围:
- **6 Agent backend** 每 Agent +30-50 case (业务边界 · 错误路径 · 大输入 · LLM fallback)
- **auth_service** +20 case (5 user × bcrypt edge / JWT exp / cookie tamper / RBAC matrix)
- **im_service** +20 case (WebSocket lifecycle / reconnect / typing / persistence)
- **audit_service** 现 25 → 40 case (decorator 边界 · cost calc · query pagination)
- **shared/kb_scan** 现 1 → 30 case (BaseScanner / Router / Degrader / 6 Agent integration)
- **integration tests** (跨 module · 端到端 path 不依赖 LLM key)

## Acceptance

- [ ] pytest cumulative 全 module 跑 ≥ 500 PASS · 0 FAIL
- [ ] coverage report (pytest-cov) ≥ 80% (critical path · `agent_*/api.py` ·
      `auth_service/*` · `im_service/*` · `audit_service/*` · `shared/kb_scan/*`)
- [ ] 不动现有 case (PRESERVES) · 仅 expand
- [ ] commit trailer:
  ```
  Signal: WORKER-A1-STAGE-E4-TEST-COVERAGE-DONE
  RECOVER-FROM: 81a9540 (E.1 audit done · 本批接续)
  TESTS-ADDED: ≥350 case
  COVERAGE: critical path ≥ 80%
  ```

## Boundary

- **加**: 各 module `tests/` 内新 file (test_<scenario>_edge.py · test_<flow>_integration.py)
- **不动**: 业务逻辑 module 本体 (agent_*/api.py · auth_service/* · im_service/* · audit_service/* · shared/kb_scan/*) · web/* · CLAUDE.md · RFC

## Method

1. 跑现有 pytest 跨 module · 拿 coverage baseline
2. 找未覆盖 critical path (业务边界 · 错误 fallback · LLM timeout · cookie tamper)
3. 写 case 不破 happy path
4. integration 测端到端 (不依赖外部 LLM key · 用 fixture mock)
5. coverage report 验 ≥ 80%

## Estim

8-12 hr (大量 case · 测各 module 边界)
