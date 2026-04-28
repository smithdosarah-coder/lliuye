# Worker A3 (Stage E.2 第 1 批) · Monitoring + Alerting · Onboarding

> Worker CLI 在 `D:/claude code/work-A3-prd` (branch `feat/prd-summaries-A3`) ·
> 复用 worktree。
> 上批 Stage D.2 frontend (`14d64e1` → 9ca83b7) 已 cherry-pick MERGED ·
> 本批 Stage E.2 启动 (24/7 ops 必修)。

## Goal

实装 master plan §E.2 — Prometheus metrics + Sentry error tracking + alerting ·
**production 24/7 ops 必修** · 服务异常 / LLM down / Tavily 401 自动告警。

## Acceptance

- [ ] **新建** `monitoring_service/` module:
  - `metrics.py` (Prometheus exporter · FastAPI middleware)
  - `sentry_init.py` (Sentry SDK · DSN 走 .env)
  - `alerts.py` (alert rules · LLM down 5min / error rate > 5% / 503 burst)
  - `health.py` (extended /health · 各 Agent + LLM provider + Tavily + DB · 状态返)
  - `tests/test_*.py`
- [ ] **GET `/metrics`** Prometheus exposition format · 含:
  - http_requests_total · http_request_duration_seconds (histogram)
  - llm_calls_total / llm_errors_total · llm_call_duration_seconds
  - im_ws_connections_active · audit_log_writes_total
- [ ] **Sentry SDK** mount 到 api_server.py · 自动 catch unhandled exception ·
      capture http 5xx · DSN env: `SENTRY_DSN` (缺时 silent skip)
- [ ] **GET `/health/extended`** · 验各 component:
  - DeepSeek API ping (chat with "ok" 返 ok)
  - Tavily API ping (1 query 验 401 / quota)
  - sqlite DB (audit + im threads)
  - 6 Agent endpoint (HEAD ping)
- [ ] **alerts.py** 规则文件 (后续 cron / external 监控读):
  - llm_provider_down (5min 0 success)
  - high_error_rate (5xx > 5% in 5min)
  - tavily_401_burst (10 fail in 1min)
- [ ] curl 测 /metrics + /health/extended · sample 进 commit body
- [ ] pytest `monitoring_service/tests/` ≥ 8 case
- [ ] commit trailer:
  ```
  Signal: WORKER-A3-STAGE-E2-MONITORING-ALERTING-DONE
  RECOVER-FROM: 14d64e1 (D.2 frontend done · 本批接续)
  NEW-MODULE: monitoring_service/{metrics,sentry_init,alerts,health,tests}
  NEW-ENDPOINT: GET /metrics, GET /health/extended
  ```

## Boundary

- **改**: `api_server.py` (mount Prometheus middleware + Sentry init + /health/extended)
- **加**: `monitoring_service/*` + `requirements.txt` (prometheus_client + sentry_sdk)
- **不动**: 业务 module · web/* · CLAUDE.md · RFC

## Method

1. prometheus_client lib · FastAPI middleware export /metrics
2. Sentry SDK init (env DSN) · auto-instrument FastAPI
3. /health/extended 各 component ping (LLM 1 turn · Tavily 1 query · sqlite SELECT 1)
4. alerts.py 规则 (yaml or json · 后续 alertmanager 读)
5. pytest mock metrics + sentry · 8+ case

## Estim

8-12 hr (Prometheus + Sentry + extended health + alert rules + 测试)
